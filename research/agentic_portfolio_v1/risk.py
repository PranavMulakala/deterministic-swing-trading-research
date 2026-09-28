"""Durable SQLite risk gate shared by isolated virtual accounts."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import json
import sqlite3
from typing import Any, Iterator

from .common import ValidationError, aware_datetime, canonical_json, decimal_value, sha256_json


class RiskRejected(RuntimeError):
    """A paper intent failed an account-wide risk invariant."""


class IdempotencyConflict(RiskRejected):
    """An idempotency key was reused with different immutable input."""


class _DurableIntegrityRejection(RiskRejected):
    """Internal signal: commit the integrity latch, then reject admission."""


@dataclass(frozen=True)
class RiskPolicy:
    max_equity_position: Decimal = Decimal("0.20")
    max_total_deployed: Decimal = Decimal("0.50")
    min_cash_reserve: Decimal = Decimal("0.50")
    max_total_option_loss: Decimal = Decimal("0.05")
    daily_realized_loss_pause: Decimal = Decimal("0.02")
    high_water_drawdown_pause: Decimal = Decimal("0.05")
    max_mark_age: timedelta = timedelta(minutes=5)
    reservation_ttl: timedelta = timedelta(minutes=10)

    def __post_init__(self) -> None:
        for name in (
            "max_equity_position", "max_total_deployed", "min_cash_reserve",
            "max_total_option_loss", "daily_realized_loss_pause", "high_water_drawdown_pause",
        ):
            value = decimal_value(getattr(self, name), field=name, positive=True)
            if value > 1:
                raise ValidationError(f"{name} must be <= 1")
        if not isinstance(self.max_mark_age, timedelta) or self.max_mark_age <= timedelta(0):
            raise ValidationError("max_mark_age must be a positive timedelta")
        if not isinstance(self.reservation_ttl, timedelta) or self.reservation_ttl <= timedelta(0):
            raise ValidationError("reservation_ttl must be a positive timedelta")


def _money_cents(value: Any, *, field: str, allow_zero: bool, rounding: str) -> int:
    amount = decimal_value(value, field=field, positive=not allow_zero, nonnegative=allow_zero)
    mode = ROUND_CEILING if rounding == "debit" else ROUND_FLOOR
    cents = (amount * 100).to_integral_value(rounding=mode)
    if cents > Decimal("9000000000000000"):
        raise ValidationError(f"{field} is too large")
    return int(cents)


def _debit_cents(value: Any, *, field: str, allow_zero: bool = False) -> int:
    """Round cash outflows and risk upward, never understating them."""
    return _money_cents(value, field=field, allow_zero=allow_zero, rounding="debit")


def _credit_cents(value: Any, *, field: str, allow_zero: bool = False) -> int:
    """Round cash inflows and marked value downward, never creating phantom cents."""
    return _money_cents(value, field=field, allow_zero=allow_zero, rounding="credit")


class RiskLedger:
    """One ledger instance is bound to one virtual account using UTC dates."""

    _REPAIR_ACK = "I_HAVE_REPAIRED_AND_RECONCILED_OFFLINE"

    def __init__(self, path: str, account_id: str, initial_cash: Decimal, policy: RiskPolicy | None = None):
        if not isinstance(account_id, str) or not account_id.strip():
            raise ValidationError("account_id must be non-empty")
        self.path = path
        self.account_id = account_id
        self.policy = policy or RiskPolicy()
        self._policy_hash = sha256_json(self._policy_identity())
        self._initial_cents = _debit_cents(initial_cash, field="initial_cash")
        self._initialize()

    def _policy_identity(self) -> dict[str, str]:
        return {
            "max_equity_position": str(self.policy.max_equity_position),
            "max_total_deployed": str(self.policy.max_total_deployed),
            "min_cash_reserve": str(self.policy.min_cash_reserve),
            "max_total_option_loss": str(self.policy.max_total_option_loss),
            "daily_realized_loss_pause": str(self.policy.daily_realized_loss_pause),
            "high_water_drawdown_pause": str(self.policy.high_water_drawdown_pause),
            "max_mark_age_seconds": str(self.policy.max_mark_age.total_seconds()),
            "reservation_ttl_seconds": str(self.policy.reservation_ttl.total_seconds()),
        }

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except _DurableIntegrityRejection:
            # The only mutation before this signal is the integrity latch. It must
            # survive rejection of the attempted operation and process restart.
            conn.commit()
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._transaction() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts(
                  account_id TEXT PRIMARY KEY, initial_cash_cents INTEGER NOT NULL,
                  policy_hash TEXT NOT NULL,
                  cash_cents INTEGER NOT NULL, high_water_cents INTEGER NOT NULL,
                  realized_pnl_cents INTEGER NOT NULL DEFAULT 0,
                  daily_loss_date TEXT, daily_loss_cents INTEGER NOT NULL DEFAULT 0,
                  kill_switch INTEGER NOT NULL DEFAULT 0 CHECK(kill_switch IN (0,1)),
                  integrity_latched INTEGER NOT NULL DEFAULT 0 CHECK(integrity_latched IN (0,1)),
                  integrity_reason TEXT, last_account_time TEXT, last_trading_date TEXT
                );
                CREATE TABLE IF NOT EXISTS marks(
                  account_id TEXT NOT NULL, symbol TEXT NOT NULL, price TEXT NOT NULL,
                  observed_at TEXT NOT NULL, PRIMARY KEY(account_id,symbol)
                );
                CREATE TABLE IF NOT EXISTS positions(
                  account_id TEXT NOT NULL, strategy TEXT NOT NULL, strategy_version TEXT NOT NULL,
                  symbol TEXT NOT NULL,
                  asset_type TEXT NOT NULL CHECK(asset_type IN ('EQUITY','OPTION')),
                  quantity TEXT NOT NULL, basis_cents INTEGER NOT NULL, multiplier INTEGER NOT NULL,
                  contractual_loss_cents INTEGER NOT NULL DEFAULT 0,
                  opened_at TEXT NOT NULL, reservation_id TEXT NOT NULL,
                  PRIMARY KEY(account_id,strategy,symbol)
                );
                CREATE TABLE IF NOT EXISTS reservations(
                  account_id TEXT NOT NULL, reservation_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                  strategy TEXT NOT NULL, strategy_version TEXT NOT NULL,
                  symbol TEXT NOT NULL, asset_type TEXT NOT NULL,
                  reserved_quantity TEXT NOT NULL,
                  notional_cents INTEGER NOT NULL, contractual_loss_cents INTEGER NOT NULL,
                  remaining_cents INTEGER NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                  status TEXT NOT NULL, evidence_hash TEXT, policy_hash TEXT NOT NULL,
                  request_hash TEXT NOT NULL, payload_hash TEXT NOT NULL,
                  PRIMARY KEY(account_id,reservation_id), UNIQUE(account_id,idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS intent_days(
                  account_id TEXT NOT NULL, strategy TEXT NOT NULL, intent_date TEXT NOT NULL,
                  reservation_id TEXT NOT NULL, PRIMARY KEY(account_id,strategy,intent_date)
                );
                CREATE TABLE IF NOT EXISTS cash_events(
                  account_id TEXT NOT NULL, event_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                  external_event_id TEXT NOT NULL, delta_cents INTEGER NOT NULL,
                  kind TEXT NOT NULL, created_at TEXT NOT NULL,
                  UNIQUE(account_id,external_event_id)
                );
                CREATE TABLE IF NOT EXISTS fill_events(
                  account_id TEXT NOT NULL, event_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
                  payload_json TEXT NOT NULL, receipt_json TEXT NOT NULL,
                  reservation_id TEXT NOT NULL, strategy TEXT NOT NULL, symbol TEXT NOT NULL,
                  asset_type TEXT NOT NULL, quantity TEXT NOT NULL, basis_delta_cents INTEGER NOT NULL,
                  contractual_loss_delta_cents INTEGER NOT NULL,
                  reservation_consumed_cents INTEGER NOT NULL, multiplier INTEGER NOT NULL,
                  filled_at TEXT NOT NULL, PRIMARY KEY(account_id,event_id)
                );
                CREATE TABLE IF NOT EXISTS close_events(
                  account_id TEXT NOT NULL, event_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
                  payload_json TEXT NOT NULL, receipt_json TEXT NOT NULL,
                  strategy TEXT NOT NULL, symbol TEXT NOT NULL, asset_type TEXT NOT NULL,
                  quantity TEXT NOT NULL, basis_delta_cents INTEGER NOT NULL,
                  contractual_loss_delta_cents INTEGER NOT NULL, proceeds_cents INTEGER NOT NULL,
                  realized_pnl_cents INTEGER NOT NULL, closed_at TEXT NOT NULL,
                  PRIMARY KEY(account_id,event_id)
                );
                CREATE TABLE IF NOT EXISTS reservation_events(
                  account_id TEXT NOT NULL, event_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
                  payload_json TEXT NOT NULL, receipt_json TEXT NOT NULL,
                  reservation_id TEXT NOT NULL, event_type TEXT NOT NULL,
                  occurred_at TEXT NOT NULL, PRIMARY KEY(account_id,event_id)
                );
                CREATE TABLE IF NOT EXISTS journal_events(
                  event_seq INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT NOT NULL,
                  event_kind TEXT NOT NULL, event_id TEXT NOT NULL, occurred_at TEXT NOT NULL,
                  UNIQUE(account_id,event_kind,event_id)
                );
                """
            )
            required_account_columns = {
                "account_id", "initial_cash_cents", "cash_cents", "high_water_cents",
                "policy_hash",
                "realized_pnl_cents", "daily_loss_date", "daily_loss_cents", "kill_switch",
                "integrity_latched", "integrity_reason", "last_account_time", "last_trading_date",
            }
            actual_account_columns = {row["name"] for row in conn.execute("PRAGMA table_info(accounts)")}
            if actual_account_columns != required_account_columns:
                raise ValidationError("incompatible risk ledger schema; use a new v1 database")
            required_reservation_columns = {
                "account_id", "reservation_id", "idempotency_key", "strategy", "strategy_version",
                "symbol", "asset_type",
                "reserved_quantity", "notional_cents", "contractual_loss_cents", "remaining_cents",
                "created_at", "expires_at", "status", "evidence_hash", "policy_hash",
                "request_hash", "payload_hash",
            }
            actual_reservation_columns = {row["name"] for row in conn.execute("PRAGMA table_info(reservations)")}
            if actual_reservation_columns != required_reservation_columns:
                raise ValidationError("incompatible risk ledger schema; use a new v1 database")
            required_position_columns = {
                "account_id", "strategy", "strategy_version", "symbol", "asset_type", "quantity",
                "basis_cents", "multiplier", "contractual_loss_cents", "opened_at", "reservation_id",
            }
            actual_position_columns = {row["name"] for row in conn.execute("PRAGMA table_info(positions)")}
            if actual_position_columns != required_position_columns:
                raise ValidationError("incompatible risk ledger schema; use a new v1 database")
            row = conn.execute(
                "SELECT initial_cash_cents,policy_hash FROM accounts WHERE account_id=?", (self.account_id,)
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO accounts(account_id,initial_cash_cents,policy_hash,cash_cents,high_water_cents) "
                    "VALUES(?,?,?,?,?)",
                    (self.account_id, self._initial_cents, self._policy_hash,
                     self._initial_cents, self._initial_cents),
                )
            elif row["initial_cash_cents"] != self._initial_cents:
                raise ValidationError("existing ledger initial cash does not match")
            elif row["policy_hash"] != self._policy_hash:
                raise ValidationError("existing ledger risk policy does not match")

    def _account(self, conn: sqlite3.Connection) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM accounts WHERE account_id=?", (self.account_id,)).fetchone()
        if row is None:
            raise RiskRejected("virtual account missing")
        return row

    def _advance_clock(self, conn: sqlite3.Connection, timestamp: datetime) -> sqlite3.Row:
        account = self._account(conn)
        if account["last_account_time"] is not None:
            prior = aware_datetime(account["last_account_time"], field="last_account_time")
            if timestamp < prior:
                raise RiskRejected("backdated account request rejected")
        trading_date = timestamp.date().isoformat()
        if account["last_trading_date"] is not None and trading_date < account["last_trading_date"]:
            raise RiskRejected("backdated UTC trading date rejected")
        if account["last_account_time"] is None or timestamp > aware_datetime(account["last_account_time"]):
            conn.execute(
                "UPDATE accounts SET last_account_time=?,last_trading_date=? WHERE account_id=?",
                (timestamp.isoformat(), trading_date, self.account_id),
            )
        return self._account(conn)

    def _guard_integrity(self, conn: sqlite3.Connection) -> sqlite3.Row:
        account = self._account(conn)
        if account["integrity_latched"]:
            raise RiskRejected("durable integrity pause latched; explicit repair required")
        return account

    def _admit_integrity(self, conn: sqlite3.Connection) -> sqlite3.Row:
        """Atomically prove materialized state before any state-changing admission."""
        try:
            errors = self._reconciliation_errors(conn)
        except Exception as exc:
            errors = [f"reconciliation failed closed: {type(exc).__name__}: {exc}"]
        if errors:
            reason = "; ".join(errors)
            conn.execute(
                "UPDATE accounts SET integrity_latched=1,integrity_reason=? WHERE account_id=?",
                (reason, self.account_id),
            )
            raise _DurableIntegrityRejection("durable integrity pause latched: " + reason)
        return self._guard_integrity(conn)

    def set_kill_switch(self, enabled: bool) -> None:
        if type(enabled) is not bool:
            raise ValidationError("kill switch value must be boolean")
        with self._transaction() as conn:
            self._admit_integrity(conn)
            conn.execute("UPDATE accounts SET kill_switch=? WHERE account_id=?", (int(enabled), self.account_id))

    def kill_switch_enabled(self) -> bool:
        with self._connect() as conn:
            return bool(self._account(conn)["kill_switch"])

    def set_mark(self, symbol: str, price: Decimal, observed_at: datetime, *, asset_type: str | None = None) -> None:
        if not isinstance(symbol, str) or not symbol or symbol != symbol.upper():
            raise ValidationError("symbol must be uppercase")
        if asset_type not in {None, "EQUITY", "OPTION"}:
            raise ValidationError("asset_type must be EQUITY or OPTION")
        px = decimal_value(price, field="mark", nonnegative=True)
        timestamp = aware_datetime(observed_at, field="observed_at")
        with self._transaction() as conn:
            self._admit_integrity(conn)
            self._advance_clock(conn, timestamp)
            stored_types = {row[0] for row in conn.execute(
                "SELECT DISTINCT asset_type FROM positions WHERE account_id=? AND symbol=?",
                (self.account_id, symbol),
            )}
            effective_type = asset_type or (next(iter(stored_types)) if len(stored_types) == 1 else None)
            if px == 0 and effective_type != "OPTION":
                raise ValidationError("zero mark is allowed only for a known option")
            if stored_types and effective_type not in stored_types:
                raise ValidationError("mark asset type conflicts with open position")
            conn.execute(
                "INSERT INTO marks(account_id,symbol,price,observed_at) VALUES(?,?,?,?) "
                "ON CONFLICT(account_id,symbol) DO UPDATE SET price=excluded.price,observed_at=excluded.observed_at",
                (self.account_id, symbol, str(px), timestamp.isoformat()),
            )

    def _roll_day(self, conn: sqlite3.Connection, now: datetime) -> sqlite3.Row:
        row = self._account(conn)
        today = now.date().isoformat()
        if row["daily_loss_date"] is None or row["daily_loss_date"] < today:
            conn.execute(
                "UPDATE accounts SET daily_loss_date=?,daily_loss_cents=0 WHERE account_id=?",
                (today, self.account_id),
            )
            row = self._account(conn)
        elif row["daily_loss_date"] > today:
            raise RiskRejected("backdated UTC daily-loss request rejected")
        return row

    def _valuation(self, conn: sqlite3.Connection, now: datetime) -> tuple[int, int]:
        account = self._account(conn)
        cash = int(account["cash_cents"])
        deployed = 0
        for position in conn.execute("SELECT * FROM positions WHERE account_id=?", (self.account_id,)):
            mark = conn.execute(
                "SELECT price,observed_at FROM marks WHERE account_id=? AND symbol=?",
                (self.account_id, position["symbol"]),
            ).fetchone()
            if mark is None:
                raise RiskRejected(f"missing mark for {position['symbol']}")
            marked_at = aware_datetime(mark["observed_at"], field="mark.observed_at")
            if now - marked_at < timedelta(0) or now - marked_at > self.policy.max_mark_age:
                raise RiskRejected(f"stale mark for {position['symbol']}")
            value = Decimal(position["quantity"]) * Decimal(position["multiplier"]) * Decimal(mark["price"])
            deployed += _credit_cents(value, field="position_value", allow_zero=True)
        return cash + deployed, deployed

    def snapshot(self, now: datetime) -> dict[str, Any]:
        timestamp = aware_datetime(now, field="now")
        with self._transaction() as conn:
            self._admit_integrity(conn)
            self._advance_clock(conn, timestamp)
            account = self._roll_day(conn, timestamp)
            equity, deployed = self._valuation(conn, timestamp)
            high_water = max(int(account["high_water_cents"]), equity)
            conn.execute("UPDATE accounts SET high_water_cents=? WHERE account_id=?", (high_water, self.account_id))
            pending = conn.execute(
                "SELECT COALESCE(SUM(remaining_cents),0) FROM reservations WHERE account_id=? AND status IN ('OPEN','PARTIAL')",
                (self.account_id,),
            ).fetchone()[0]
            account = self._account(conn)
            return {
                "account_id": self.account_id, "equity_cents": equity,
                "cash_cents": int(account["cash_cents"]), "deployed_cents": deployed,
                "pending_cents": int(pending), "high_water_cents": high_water,
                "daily_loss_cents": int(account["daily_loss_cents"]),
                "kill_switch": bool(account["kill_switch"]),
                "integrity_latched": bool(account["integrity_latched"]),
                "last_account_time": account["last_account_time"], "trading_date_basis": "UTC",
            }

    def has_position(self, strategy: str, symbol: str) -> bool:
        with self._connect() as conn:
            return conn.execute(
                "SELECT 1 FROM positions WHERE account_id=? AND strategy=? AND symbol=?",
                (self.account_id, strategy, symbol),
            ).fetchone() is not None

    def open_positions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM positions WHERE account_id=? ORDER BY strategy,symbol", (self.account_id,)
            )]

    def has_active_reservation(self, *, asset_type: str, excluding_idempotency_key: str | None = None) -> bool:
        if asset_type not in {"EQUITY", "OPTION"}:
            raise ValidationError("invalid asset_type")
        query = (
            "SELECT 1 FROM reservations WHERE account_id=? AND asset_type=? "
            "AND status IN ('OPEN','PARTIAL')"
        )
        params: list[Any] = [self.account_id, asset_type]
        if excluding_idempotency_key is not None:
            query += " AND idempotency_key<>?"
            params.append(excluding_idempotency_key)
        with self._connect() as conn:
            return conn.execute(query, params).fetchone() is not None

    def reserve(
        self, *, idempotency_key: str, strategy: str, symbol: str, asset_type: str,
        notional: Decimal, contractual_loss: Decimal, now: datetime,
        quantity: Decimal | None = None, evidence_hash: str | None = None,
        strategy_version: str = "UNVERSIONED",
    ) -> dict[str, Any]:
        timestamp = aware_datetime(now, field="now")
        for field, value in (
            ("idempotency_key", idempotency_key), ("strategy", strategy),
            ("strategy_version", strategy_version), ("symbol", symbol),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{field} must be non-empty")
        if symbol != symbol.upper() or asset_type not in {"EQUITY", "OPTION"}:
            raise ValidationError("invalid symbol or asset_type")
        if evidence_hash is not None and (
            not isinstance(evidence_hash, str) or len(evidence_hash) != 64
            or any(char not in "0123456789abcdef" for char in evidence_hash)
        ):
            raise ValidationError("evidence_hash must be a lowercase SHA-256 hash")
        notional_cents = _debit_cents(notional, field="notional")
        loss_cents = _debit_cents(contractual_loss, field="contractual_loss", allow_zero=True)
        if asset_type == "OPTION":
            reserved_quantity = Decimal("1") if quantity is None else decimal_value(quantity, field="quantity", positive=True)
            if reserved_quantity != 1 or reserved_quantity != reserved_quantity.to_integral_value():
                raise RiskRejected("long-option reservation must be exactly one whole contract")
            if loss_cents <= 0 or loss_cents < notional_cents:
                raise RiskRejected("long-option contractual loss must be positive and at least reserved notional")
        else:
            reserved_quantity = Decimal("0") if quantity is None else decimal_value(quantity, field="quantity", positive=True)
        request_identity = {
            "account_id": self.account_id, "idempotency_key": idempotency_key,
            "strategy": strategy, "strategy_version": strategy_version, "symbol": symbol,
            "asset_type": asset_type, "reserved_quantity": str(reserved_quantity), "notional_cents": notional_cents,
            "contractual_loss_cents": loss_cents, "evidence_hash": evidence_hash,
            "policy_hash": self._policy_hash,
        }
        request_hash = sha256_json(request_identity)
        reservation_id = sha256_json({"account": self.account_id, "request_hash": request_hash})[:32]
        with self._transaction() as conn:
            self._admit_integrity(conn)
            prior = conn.execute(
                "SELECT * FROM reservations WHERE account_id=? AND idempotency_key=?",
                (self.account_id, idempotency_key),
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise IdempotencyConflict("idempotency key reused with different input")
                return self._reservation_dict(prior, replay=True)
            self._advance_clock(conn, timestamp)
            account = self._roll_day(conn, timestamp)
            self._guard_integrity(conn)
            if account["kill_switch"]:
                raise RiskRejected("global kill switch enabled")
            equity, deployed = self._valuation(conn, timestamp)
            if equity <= 0:
                raise RiskRejected("account equity is not positive")
            high_water = max(int(account["high_water_cents"]), equity)
            conn.execute("UPDATE accounts SET high_water_cents=? WHERE account_id=?", (high_water, self.account_id))
            if int(account["daily_loss_cents"]) >= int(Decimal(self._initial_cents) * self.policy.daily_realized_loss_pause):
                raise RiskRejected("daily realized-loss pause")
            if high_water - equity >= int(Decimal(high_water) * self.policy.high_water_drawdown_pause):
                raise RiskRejected("high-water drawdown pause")
            if conn.execute(
                "SELECT 1 FROM intent_days WHERE account_id=? AND strategy=? AND intent_date=?",
                (self.account_id, strategy, timestamp.date().isoformat()),
            ).fetchone():
                raise RiskRejected("strategy already opened a new intent today")
            pending = int(conn.execute(
                "SELECT COALESCE(SUM(remaining_cents),0) FROM reservations WHERE account_id=? AND status IN ('OPEN','PARTIAL')",
                (self.account_id,),
            ).fetchone()[0])
            if asset_type == "EQUITY":
                symbol_exposure = int(conn.execute(
                    "SELECT COALESCE(SUM(remaining_cents),0) FROM reservations WHERE account_id=? AND symbol=? "
                    "AND asset_type='EQUITY' AND status IN ('OPEN','PARTIAL')",
                    (self.account_id, symbol),
                ).fetchone()[0])
                for position in conn.execute(
                    "SELECT p.quantity,p.multiplier,m.price FROM positions p JOIN marks m "
                    "ON m.account_id=p.account_id AND m.symbol=p.symbol "
                    "WHERE p.account_id=? AND p.symbol=? AND p.asset_type='EQUITY'",
                    (self.account_id, symbol),
                ):
                    symbol_exposure += _credit_cents(
                        Decimal(position["quantity"]) * Decimal(position["multiplier"]) * Decimal(position["price"]),
                        field="symbol_exposure", allow_zero=True,
                    )
                if symbol_exposure + notional_cents > int(Decimal(equity) * self.policy.max_equity_position):
                    raise RiskRejected("aggregate equity symbol exposure exceeds 20%")
            if asset_type == "OPTION":
                option_risk = int(conn.execute(
                    "SELECT COALESCE(SUM(contractual_loss_cents),0) FROM positions "
                    "WHERE account_id=? AND asset_type='OPTION'", (self.account_id,),
                ).fetchone()[0])
                option_risk += int(conn.execute(
                    "SELECT COALESCE(SUM(contractual_loss_cents),0) FROM reservations "
                    "WHERE account_id=? AND asset_type='OPTION' AND status IN ('OPEN','PARTIAL')",
                    (self.account_id,),
                ).fetchone()[0])
                if option_risk + loss_cents > int(Decimal(equity) * self.policy.max_total_option_loss):
                    raise RiskRejected("total option contractual loss exceeds 5%")
            if deployed + pending + notional_cents > int(Decimal(equity) * self.policy.max_total_deployed):
                raise RiskRejected("total deployed capital would exceed 50%")
            if int(account["cash_cents"]) - pending - notional_cents < int(Decimal(equity) * self.policy.min_cash_reserve):
                raise RiskRejected("50% cash reserve would be violated")
            expires = timestamp + self.policy.reservation_ttl
            durable_payload = {
                **request_identity, "reservation_id": reservation_id,
                "created_at": timestamp.isoformat(), "expires_at": expires.isoformat(),
            }
            payload_hash = sha256_json(durable_payload)
            conn.execute(
                "INSERT INTO reservations(account_id,reservation_id,idempotency_key,strategy,strategy_version,symbol,asset_type,"
                "reserved_quantity,notional_cents,contractual_loss_cents,remaining_cents,created_at,expires_at,status,"
                "evidence_hash,policy_hash,request_hash,payload_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (self.account_id, reservation_id, idempotency_key, strategy, strategy_version, symbol, asset_type,
                 str(reserved_quantity), notional_cents, loss_cents, notional_cents, timestamp.isoformat(), expires.isoformat(),
                 "OPEN", evidence_hash, self._policy_hash, request_hash, payload_hash),
            )
            conn.execute(
                "INSERT INTO intent_days VALUES(?,?,?,?)",
                (self.account_id, strategy, timestamp.date().isoformat(), reservation_id),
            )
            row = conn.execute(
                "SELECT * FROM reservations WHERE account_id=? AND reservation_id=?",
                (self.account_id, reservation_id),
            ).fetchone()
            receipt = self._reservation_dict(row, replay=False)
            event_id = f"reserve:{reservation_id}"
            event_payload = {"event_type": "CREATE", **durable_payload}
            conn.execute(
                "INSERT INTO reservation_events VALUES(?,?,?,?,?,?,?,?)",
                (self.account_id, event_id, sha256_json(event_payload), canonical_json(event_payload),
                 canonical_json(receipt), reservation_id, "CREATE", timestamp.isoformat()),
            )
            conn.execute(
                "INSERT INTO journal_events(account_id,event_kind,event_id,occurred_at) VALUES(?,?,?,?)",
                (self.account_id, "RESERVATION", event_id, timestamp.isoformat()),
            )
            return receipt

    @staticmethod
    def _reservation_dict(row: sqlite3.Row, *, replay: bool) -> dict[str, Any]:
        return {
            "reservation_id": row["reservation_id"], "status": row["status"],
            "remaining_cents": int(row["remaining_cents"]), "expires_at": row["expires_at"],
            "reserved_quantity": row["reserved_quantity"], "replay": replay,
        }

    def release(
        self, reservation_id: str, *, released_at: datetime | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        with self._transaction() as conn:
            self._admit_integrity(conn)
            row = conn.execute(
                "SELECT * FROM reservations WHERE account_id=? AND reservation_id=?",
                (self.account_id, reservation_id),
            ).fetchone()
            if row is None:
                raise ValidationError("unknown reservation")
            if released_at is None:
                fallback = self._account(conn)["last_account_time"] or row["created_at"]
                timestamp = aware_datetime(fallback, field="released_at")
            else:
                timestamp = aware_datetime(released_at, field="released_at")
            request_payload = {
                "account_id": self.account_id, "reservation_id": reservation_id,
                "event_type": "RELEASE",
                "occurred_at": timestamp.isoformat(),
            }
            key = self._event_identity("reservation", event_id, request_payload)
            prior = conn.execute(
                "SELECT payload_hash,payload_json,receipt_json FROM reservation_events WHERE account_id=? AND event_id=?",
                (self.account_id, key),
            ).fetchone()
            if prior:
                stored_payload = json.loads(prior["payload_json"])
                if any(stored_payload.get(field) != value for field, value in request_payload.items()):
                    raise IdempotencyConflict("reservation event_id reused with different input")
                return {**json.loads(prior["receipt_json"]), "replay": True}
            if released_at is None and event_id is None and row["status"] == "RELEASED":
                prior = conn.execute(
                    "SELECT receipt_json FROM reservation_events WHERE account_id=? AND reservation_id=? "
                    "AND event_type='RELEASE' ORDER BY rowid LIMIT 1",
                    (self.account_id, reservation_id),
                ).fetchone()
                if prior:
                    return {**json.loads(prior["receipt_json"]), "replay": True}
            self._advance_clock(conn, timestamp)
            if row["status"] not in {"OPEN", "PARTIAL"}:
                raise RiskRejected("reservation is not active")
            payload = {
                **request_payload, "strategy": row["strategy"],
                "strategy_version": row["strategy_version"], "symbol": row["symbol"],
                "asset_type": row["asset_type"], "prior_status": row["status"],
                "prior_remaining_cents": int(row["remaining_cents"]),
                "reservation_payload_hash": row["payload_hash"],
            }
            payload_hash = sha256_json(payload)
            conn.execute(
                "UPDATE reservations SET status='RELEASED',remaining_cents=0 WHERE account_id=? AND reservation_id=?",
                (self.account_id, reservation_id),
            )
            receipt = {"event_id": key, "reservation_id": reservation_id, "status": "RELEASED", "replay": False}
            conn.execute(
                "INSERT INTO reservation_events VALUES(?,?,?,?,?,?,?,?)",
                (self.account_id, key, payload_hash, canonical_json(payload), canonical_json(receipt),
                 reservation_id, "RELEASE", timestamp.isoformat()),
            )
            conn.execute(
                "INSERT INTO journal_events(account_id,event_kind,event_id,occurred_at) VALUES(?,?,?,?)",
                (self.account_id, "RESERVATION", key, timestamp.isoformat()),
            )
            return receipt

    def expire_reservations(self, now: datetime) -> int:
        timestamp = aware_datetime(now, field="now")
        with self._transaction() as conn:
            self._admit_integrity(conn)
            self._advance_clock(conn, timestamp)
            rows = list(conn.execute(
                "SELECT * FROM reservations WHERE account_id=? AND status IN ('OPEN','PARTIAL') AND expires_at<=? "
                "ORDER BY reservation_id",
                (self.account_id, timestamp.isoformat()),
            ))
            for row in rows:
                payload = {
                    "account_id": self.account_id, "reservation_id": row["reservation_id"],
                    "event_type": "EXPIRE", "occurred_at": timestamp.isoformat(),
                    "strategy": row["strategy"], "strategy_version": row["strategy_version"],
                    "symbol": row["symbol"], "asset_type": row["asset_type"],
                    "prior_status": row["status"],
                    "prior_remaining_cents": int(row["remaining_cents"]),
                    "reservation_payload_hash": row["payload_hash"],
                }
                key = self._event_identity("reservation", None, payload)
                payload_hash = sha256_json(payload)
                conn.execute(
                    "UPDATE reservations SET status='EXPIRED',remaining_cents=0 "
                    "WHERE account_id=? AND reservation_id=?",
                    (self.account_id, row["reservation_id"]),
                )
                receipt = {
                    "event_id": key, "reservation_id": row["reservation_id"],
                    "status": "EXPIRED", "replay": False,
                }
                conn.execute(
                    "INSERT INTO reservation_events VALUES(?,?,?,?,?,?,?,?)",
                    (self.account_id, key, payload_hash, canonical_json(payload), canonical_json(receipt),
                     row["reservation_id"], "EXPIRE", timestamp.isoformat()),
                )
                conn.execute(
                    "INSERT INTO journal_events(account_id,event_kind,event_id,occurred_at) VALUES(?,?,?,?)",
                    (self.account_id, "RESERVATION", key, timestamp.isoformat()),
                )
            return len(rows)

    @staticmethod
    def _event_identity(prefix: str, supplied: str | None, payload: dict[str, Any]) -> str:
        if supplied is None:
            return f"auto-{prefix}-{sha256_json(payload)}"
        if not isinstance(supplied, str) or not supplied.strip():
            raise ValidationError("event_id must be a non-empty string")
        return supplied

    def record_fill(
        self, *, reservation_id: str, quantity: Decimal, price: Decimal,
        costs: Decimal, filled_at: datetime, event_id: str | None = None,
    ) -> dict[str, Any]:
        qty = decimal_value(quantity, field="quantity", positive=True)
        px = decimal_value(price, field="price", positive=True)
        fees = decimal_value(costs, field="costs", nonnegative=True)
        timestamp = aware_datetime(filled_at, field="filled_at")
        payload = {
            "reservation_id": reservation_id, "quantity": str(qty), "price": str(px),
            "costs": str(fees), "filled_at": timestamp.isoformat(),
        }
        key = self._event_identity("fill", event_id, payload)
        payload_hash = sha256_json(payload)
        with self._transaction() as conn:
            self._admit_integrity(conn)
            prior = conn.execute(
                "SELECT payload_hash,receipt_json FROM fill_events WHERE account_id=? AND event_id=?",
                (self.account_id, key),
            ).fetchone()
            if prior:
                if prior["payload_hash"] != payload_hash:
                    raise IdempotencyConflict("fill event_id reused with different input")
                return {**json.loads(prior["receipt_json"]), "replay": True}
            self._advance_clock(conn, timestamp)
            account = self._guard_integrity(conn)
            if account["kill_switch"]:
                raise RiskRejected("global kill switch enabled")
            reservation = conn.execute(
                "SELECT * FROM reservations WHERE account_id=? AND reservation_id=?",
                (self.account_id, reservation_id),
            ).fetchone()
            if reservation is None or reservation["status"] not in {"OPEN", "PARTIAL"}:
                raise RiskRejected("reservation is not open")
            if timestamp < aware_datetime(reservation["created_at"]):
                raise RiskRejected("fill predates reservation")
            if aware_datetime(reservation["expires_at"]) <= timestamp:
                raise RiskRejected("reservation expired before fill")
            is_option = reservation["asset_type"] == "OPTION"
            if is_option and (qty != 1 or qty != qty.to_integral_value() or Decimal(reservation["reserved_quantity"]) != 1):
                raise RiskRejected("option fill must be exactly one whole reserved contract")
            previously_filled = sum(
                (Decimal(row[0]) for row in conn.execute(
                    "SELECT quantity FROM fill_events WHERE account_id=? AND reservation_id=?",
                    (self.account_id, reservation_id),
                )),
                Decimal("0"),
            )
            reserved_quantity = Decimal(reservation["reserved_quantity"])
            if reserved_quantity > 0 and previously_filled + qty > reserved_quantity:
                raise RiskRejected("fill quantity exceeds reserved quantity")
            multiplier = 100 if is_option else 1
            debit_cents = _debit_cents(qty * px * multiplier + fees, field="fill_debit")
            if debit_cents > int(reservation["remaining_cents"]):
                raise RiskRejected("fill exceeds reserved amount")
            if debit_cents > int(account["cash_cents"]):
                raise RiskRejected("insufficient virtual cash")
            existing = conn.execute(
                "SELECT * FROM positions WHERE account_id=? AND strategy=? AND symbol=?",
                (self.account_id, reservation["strategy"], reservation["symbol"]),
            ).fetchone()
            if is_option and existing is not None:
                raise RiskRejected("option position already filled")
            if existing is not None and existing["reservation_id"] != reservation_id:
                raise RiskRejected("adding a different reservation to an open position is prohibited")
            if existing is not None and existing["strategy_version"] != reservation["strategy_version"]:
                raise RiskRejected("position strategy version conflicts with its reservation")
            contractual_delta = debit_cents if is_option else 0
            if existing:
                new_qty = Decimal(existing["quantity"]) + qty
                new_basis = int(existing["basis_cents"]) + debit_cents
                new_contractual_loss = int(existing["contractual_loss_cents"]) + contractual_delta
                conn.execute(
                    "UPDATE positions SET quantity=?,basis_cents=?,contractual_loss_cents=? "
                    "WHERE account_id=? AND strategy=? AND symbol=?",
                    (str(new_qty), new_basis, new_contractual_loss, self.account_id,
                     reservation["strategy"], reservation["symbol"]),
                )
            else:
                new_qty, new_basis, new_contractual_loss = qty, debit_cents, contractual_delta
                conn.execute(
                    "INSERT INTO positions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (self.account_id, reservation["strategy"], reservation["strategy_version"],
                     reservation["symbol"], reservation["asset_type"],
                     str(qty), debit_cents, multiplier,
                     contractual_delta,
                     timestamp.isoformat(), reservation_id),
                )
            consumed = int(reservation["remaining_cents"]) if is_option else debit_cents
            remaining = int(reservation["remaining_cents"]) - consumed
            status = "FILLED" if remaining == 0 else "PARTIAL"
            conn.execute(
                "UPDATE reservations SET remaining_cents=?,status=? WHERE account_id=? AND reservation_id=?",
                (remaining, status, self.account_id, reservation_id),
            )
            conn.execute("UPDATE accounts SET cash_cents=cash_cents-? WHERE account_id=?", (debit_cents, self.account_id))
            receipt = {
                "event_id": key, "payload_hash": payload_hash, "quantity": str(new_qty),
                "basis_cents": new_basis, "remaining_cents": remaining, "status": status, "replay": False,
            }
            conn.execute(
                "INSERT INTO fill_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (self.account_id, key, payload_hash, canonical_json(payload), canonical_json(receipt),
                 reservation_id, reservation["strategy"], reservation["symbol"], reservation["asset_type"],
                 str(qty), debit_cents, contractual_delta, consumed, multiplier, timestamp.isoformat()),
            )
            conn.execute(
                "INSERT INTO cash_events(account_id,external_event_id,delta_cents,kind,created_at) VALUES(?,?,?,?,?)",
                (self.account_id, f"FILL:{key}", -debit_cents, "FILL", timestamp.isoformat()),
            )
            conn.execute(
                "INSERT INTO journal_events(account_id,event_kind,event_id,occurred_at) VALUES(?,?,?,?)",
                (self.account_id, "FILL", key, timestamp.isoformat()),
            )
            return receipt

    def close_position(
        self, *, strategy: str, symbol: str, quantity: Decimal, price: Decimal,
        costs: Decimal, closed_at: datetime, reason: str, event_id: str | None = None,
    ) -> dict[str, Any]:
        qty = decimal_value(quantity, field="quantity", positive=True)
        px = decimal_value(price, field="price", nonnegative=True)
        fees = decimal_value(costs, field="costs", nonnegative=True)
        timestamp = aware_datetime(closed_at, field="closed_at")
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError("close reason is required")
        payload = {
            "strategy": strategy, "symbol": symbol, "quantity": str(qty), "price": str(px),
            "costs": str(fees), "closed_at": timestamp.isoformat(), "reason": reason,
        }
        key = self._event_identity("close", event_id, payload)
        payload_hash = sha256_json(payload)
        with self._transaction() as conn:
            self._admit_integrity(conn)
            prior = conn.execute(
                "SELECT payload_hash,receipt_json FROM close_events WHERE account_id=? AND event_id=?",
                (self.account_id, key),
            ).fetchone()
            if prior:
                if prior["payload_hash"] != payload_hash:
                    raise IdempotencyConflict("close event_id reused with different input")
                return {**json.loads(prior["receipt_json"]), "replay": True}
            self._advance_clock(conn, timestamp)
            self._guard_integrity(conn)
            account = self._roll_day(conn, timestamp)
            position = conn.execute(
                "SELECT * FROM positions WHERE account_id=? AND strategy=? AND symbol=?",
                (self.account_id, strategy, symbol),
            ).fetchone()
            if position is None or qty > Decimal(position["quantity"]):
                raise RiskRejected("close quantity exceeds open position")
            if timestamp < aware_datetime(position["opened_at"]):
                raise RiskRejected("close predates position")
            if position["asset_type"] == "EQUITY" and px <= 0:
                raise ValidationError("equity close price must be positive")
            if position["asset_type"] == "OPTION" and qty != qty.to_integral_value():
                raise RiskRejected("option close quantity must be whole contracts")
            total_qty = Decimal(position["quantity"])
            basis_closed = int((Decimal(position["basis_cents"]) * qty / total_qty).to_integral_value(rounding=ROUND_CEILING))
            if qty < total_qty:
                basis_closed = min(basis_closed, int(position["basis_cents"]) - 1)
            contractual_closed = (
                int((Decimal(position["contractual_loss_cents"]) * qty / total_qty).to_integral_value(rounding=ROUND_CEILING))
                if position["asset_type"] == "OPTION" else 0
            )
            proceeds_cents = _credit_cents(
                qty * px * int(position["multiplier"]) - fees, field="net_proceeds", allow_zero=True
            )
            realized = proceeds_cents - basis_closed
            remaining_qty = total_qty - qty
            remaining_basis = int(position["basis_cents"]) - basis_closed
            remaining_contractual_loss = int(position["contractual_loss_cents"]) - contractual_closed
            if remaining_qty == 0:
                conn.execute(
                    "DELETE FROM positions WHERE account_id=? AND strategy=? AND symbol=?",
                    (self.account_id, strategy, symbol),
                )
            else:
                conn.execute(
                    "UPDATE positions SET quantity=?,basis_cents=?,contractual_loss_cents=? "
                    "WHERE account_id=? AND strategy=? AND symbol=?",
                    (str(remaining_qty), remaining_basis, remaining_contractual_loss,
                     self.account_id, strategy, symbol),
                )
            loss = max(0, -realized)
            conn.execute(
                "UPDATE accounts SET cash_cents=cash_cents+?,realized_pnl_cents=realized_pnl_cents+?,"
                "daily_loss_cents=daily_loss_cents+? WHERE account_id=?",
                (proceeds_cents, realized, loss, self.account_id),
            )
            receipt = {
                "event_id": key, "payload_hash": payload_hash, "net_proceeds_cents": proceeds_cents,
                "realized_pnl_cents": realized, "remaining_quantity": str(remaining_qty), "replay": False,
            }
            conn.execute(
                "INSERT INTO close_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (self.account_id, key, payload_hash, canonical_json(payload), canonical_json(receipt),
                 strategy, symbol, position["asset_type"], str(qty), basis_closed,
                 contractual_closed, proceeds_cents, realized, timestamp.isoformat()),
            )
            conn.execute(
                "INSERT INTO cash_events(account_id,external_event_id,delta_cents,kind,created_at) VALUES(?,?,?,?,?)",
                (self.account_id, f"CLOSE:{key}", proceeds_cents, f"CLOSE:{reason}", timestamp.isoformat()),
            )
            conn.execute(
                "INSERT INTO journal_events(account_id,event_kind,event_id,occurred_at) VALUES(?,?,?,?)",
                (self.account_id, "CLOSE", key, timestamp.isoformat()),
            )
            return receipt

    def get_position(self, strategy: str, symbol: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM positions WHERE account_id=? AND strategy=? AND symbol=?",
                (self.account_id, strategy, symbol),
            ).fetchone()
            return dict(row) if row else None

    def get_open_stock_entry_state(
        self, strategy: str, symbol: str, *, strategy_version: str,
    ) -> dict[str, Any]:
        """Return reconciled economic identity for the current equity position."""
        if not isinstance(strategy_version, str) or not strategy_version.strip():
            raise ValidationError("strategy_version must be non-empty")
        with self._transaction() as conn:
            self._admit_integrity(conn)
            position = conn.execute(
                "SELECT * FROM positions WHERE account_id=? AND strategy=? AND symbol=?",
                (self.account_id, strategy, symbol),
            ).fetchone()
            if position is None or position["asset_type"] != "EQUITY" or Decimal(position["quantity"]) <= 0:
                raise RiskRejected("open stock position is missing")
            reservation = conn.execute(
                "SELECT * FROM reservations WHERE account_id=? AND reservation_id=?",
                (self.account_id, position["reservation_id"]),
            ).fetchone()
            if (
                reservation is None or reservation["strategy"] != strategy
                or reservation["symbol"] != symbol or reservation["asset_type"] != "EQUITY"
                or reservation["strategy_version"] != strategy_version
                or position["strategy_version"] != strategy_version
            ):
                raise RiskRejected("stock position origin strategy/version is missing or conflicting")
            latest_fill = conn.execute(
                "SELECT f.filled_at FROM fill_events f JOIN journal_events j "
                "ON j.account_id=f.account_id AND j.event_kind='FILL' AND j.event_id=f.event_id "
                "WHERE f.account_id=? AND f.reservation_id=? ORDER BY j.event_seq DESC LIMIT 1",
                (self.account_id, reservation["reservation_id"]),
            ).fetchone()
            if latest_fill is None:
                raise RiskRejected("stock position has no durable fill event")
            evidence_hash = reservation["evidence_hash"] or reservation["payload_hash"]
            return {
                "symbol": symbol, "quantity": position["quantity"],
                "basis_cents": int(position["basis_cents"]), "opened_at": position["opened_at"],
                "last_fill_at": latest_fill["filled_at"],
                "evidence_hash": evidence_hash,
                "external_evidence_bound": reservation["evidence_hash"] is not None,
                "strategy_version": reservation["strategy_version"],
                "reservation_id": reservation["reservation_id"],
            }

    def get_open_option_entry_state(
        self, strategy: str, symbol: str, *, strategy_version: str,
    ) -> dict[str, Any]:
        """Return verified entry economics for the currently open option lot."""
        if not isinstance(strategy_version, str) or not strategy_version.strip():
            raise ValidationError("strategy_version must be non-empty")
        with self._transaction() as conn:
            self._admit_integrity(conn)
            position = conn.execute(
                "SELECT * FROM positions WHERE account_id=? AND strategy=? AND symbol=?",
                (self.account_id, strategy, symbol),
            ).fetchone()
            if position is None or position["asset_type"] != "OPTION" or Decimal(position["quantity"]) != 1:
                raise RiskRejected("exact one-contract option position is not open")
            if position["strategy_version"] != strategy_version:
                raise RiskRejected("option position origin strategy version conflicts with this engine")
            fill = conn.execute(
                "SELECT f.*,j.event_seq FROM fill_events f JOIN journal_events j "
                "ON j.account_id=f.account_id AND j.event_kind='FILL' AND j.event_id=f.event_id "
                "WHERE f.account_id=? AND f.strategy=? AND f.symbol=? ORDER BY j.event_seq DESC LIMIT 1",
                (self.account_id, strategy, symbol),
            ).fetchone()
            if fill is None or fill["filled_at"] != position["opened_at"]:
                raise RiskRejected("durable option entry event is missing")
            reservation = conn.execute(
                "SELECT * FROM reservations WHERE account_id=? AND reservation_id=?",
                (self.account_id, fill["reservation_id"]),
            ).fetchone()
            if (
                reservation is None or not reservation["evidence_hash"]
                or reservation["reservation_id"] != position["reservation_id"]
                or reservation["strategy"] != strategy or reservation["symbol"] != symbol
                or reservation["asset_type"] != "OPTION"
                or reservation["strategy_version"] != strategy_version
            ):
                raise RiskRejected("durable option entry strategy/version/evidence binding is missing")
            payload = json.loads(fill["payload_json"])
            return {
                "contract": symbol,
                "entry_premium": str(decimal_value(payload["price"], field="entry.price", positive=True)),
                "entry_costs": str(decimal_value(payload["costs"], field="entry.costs", nonnegative=True)),
                "entry_debit_cents": int(fill["basis_delta_cents"]),
                "opened_at": fill["filled_at"],
                "evidence_hash": reservation["evidence_hash"],
                "quantity": position["quantity"],
                "strategy_version": reservation["strategy_version"],
                "reservation_id": reservation["reservation_id"],
            }

    def reconcile(self) -> dict[str, Any]:
        with self._transaction() as conn:
            try:
                errors = self._reconciliation_errors(conn)
            except Exception as exc:
                errors = [f"reconciliation failed closed: {type(exc).__name__}: {exc}"]
            if errors:
                conn.execute(
                    "UPDATE accounts SET integrity_latched=1,integrity_reason=? WHERE account_id=?",
                    ("; ".join(errors), self.account_id),
                )
            account = self._account(conn)
            if account["integrity_latched"] and not errors:
                errors = ["integrity pause remains latched pending explicit verified repair"]
            return {
                "ok": not errors and not bool(account["integrity_latched"]),
                "errors": errors,
                "cash_cents": int(account["cash_cents"]),
                "integrity_latched": bool(account["integrity_latched"]),
            }

    def _reconciliation_errors(self, conn: sqlite3.Connection) -> list[str]:
        """Chronologically replay immutable events without trusting materialized economics."""
        account = self._account(conn)
        errors: list[str] = []
        positions: dict[tuple[str, str], dict[str, Any]] = {}
        reservations: dict[str, dict[str, Any]] = {}
        expected_cash_events: dict[str, int] = {}
        realized_total = 0
        current_day_loss = 0

        if account["policy_hash"] != self._policy_hash:
            errors.append("account policy hash does not match the active frozen policy")

        reservation_rows = {
            row["reservation_id"]: row
            for row in conn.execute("SELECT * FROM reservations WHERE account_id=?", (self.account_id,))
        }
        for reservation_id, row in reservation_rows.items():
            try:
                request_identity = {
                    "account_id": self.account_id, "idempotency_key": row["idempotency_key"],
                    "strategy": row["strategy"], "strategy_version": row["strategy_version"],
                    "symbol": row["symbol"], "asset_type": row["asset_type"],
                    "reserved_quantity": row["reserved_quantity"],
                    "notional_cents": int(row["notional_cents"]),
                    "contractual_loss_cents": int(row["contractual_loss_cents"]),
                    "evidence_hash": row["evidence_hash"], "policy_hash": row["policy_hash"],
                }
                request_hash = sha256_json(request_identity)
                if request_hash != row["request_hash"]:
                    raise ValueError("reservation request hash mismatch")
                created = aware_datetime(row["created_at"], field="reservation.created_at")
                expires = aware_datetime(row["expires_at"], field="reservation.expires_at")
                if expires <= created:
                    raise ValueError("reservation expiry is not after creation")
                durable_payload = {
                    **request_identity, "reservation_id": reservation_id,
                    "created_at": row["created_at"], "expires_at": row["expires_at"],
                }
                if sha256_json(durable_payload) != row["payload_hash"]:
                    raise ValueError("reservation durable payload hash mismatch")
                if row["policy_hash"] != self._policy_hash:
                    raise ValueError("reservation policy hash mismatch")
                reserved_quantity = decimal_value(row["reserved_quantity"], field="reserved_quantity", nonnegative=True)
                notional = int(row["notional_cents"])
                loss = int(row["contractual_loss_cents"])
                if notional <= 0 or loss < 0:
                    raise ValueError("reservation economics are invalid")
                if row["asset_type"] == "OPTION" and (reserved_quantity != 1 or loss < notional):
                    raise ValueError("option reservation quantity/loss is invalid")
                reservations[reservation_id] = {
                    "row": row, "durable_payload": durable_payload, "status": None,
                    "remaining_cents": None, "filled_quantity": Decimal("0"),
                    "created_at": created, "expires_at": expires,
                    "reserved_quantity": reserved_quantity, "notional_cents": notional,
                }
            except Exception as exc:
                errors.append(f"reservation {reservation_id} is invalid: {exc}")

        journal_rows = list(conn.execute(
            "SELECT * FROM journal_events WHERE account_id=? ORDER BY event_seq", (self.account_id,)
        ))
        referenced: dict[str, set[str]] = {"FILL": set(), "CLOSE": set(), "RESERVATION": set()}
        prior_time: datetime | None = None
        for journal in journal_rows:
            kind, event_id = journal["event_kind"], journal["event_id"]
            try:
                occurred = aware_datetime(journal["occurred_at"], field="journal.occurred_at")
                if prior_time is not None and occurred < prior_time:
                    raise ValueError("journal time regressed")
                prior_time = occurred
                if kind not in referenced or event_id in referenced[kind]:
                    raise ValueError("unknown or duplicate journal event")
                referenced[kind].add(event_id)

                if kind == "FILL":
                    row = conn.execute(
                        "SELECT * FROM fill_events WHERE account_id=? AND event_id=?", (self.account_id, event_id)
                    ).fetchone()
                    if row is None or row["filled_at"] != journal["occurred_at"]:
                        raise ValueError("missing fill or journal timestamp mismatch")
                    payload = json.loads(row["payload_json"])
                    if sha256_json(payload) != row["payload_hash"]:
                        raise ValueError("fill payload hash mismatch")
                    reservation = reservations.get(row["reservation_id"])
                    if reservation is None or reservation["status"] not in {"OPEN", "PARTIAL"}:
                        raise ValueError("fill has no active reservation")
                    reservation_row = reservation["row"]
                    if not reservation["created_at"] <= occurred < reservation["expires_at"]:
                        raise ValueError("fill time is outside reservation lifetime")
                    if (
                        payload.get("reservation_id") != row["reservation_id"]
                        or payload.get("quantity") != row["quantity"]
                        or payload.get("filled_at") != row["filled_at"]
                        or row["strategy"] != reservation_row["strategy"]
                        or row["symbol"] != reservation_row["symbol"]
                        or row["asset_type"] != reservation_row["asset_type"]
                    ):
                        raise ValueError("fill identity mismatch")
                    quantity = decimal_value(row["quantity"], field="fill.quantity", positive=True)
                    multiplier = 100 if row["asset_type"] == "OPTION" else 1
                    if int(row["multiplier"]) != multiplier:
                        raise ValueError("fill multiplier mismatch")
                    if row["asset_type"] == "OPTION" and quantity != 1:
                        raise ValueError("option fill is not exactly one contract")
                    if reservation["reserved_quantity"] > 0 and reservation["filled_quantity"] + quantity > reservation["reserved_quantity"]:
                        raise ValueError("fill exceeds reserved quantity")
                    basis_delta = _debit_cents(
                        quantity * decimal_value(payload.get("price"), field="fill.price", positive=True) * multiplier
                        + decimal_value(payload.get("costs"), field="fill.costs", nonnegative=True),
                        field="fill.debit",
                    )
                    consumed = reservation["remaining_cents"] if row["asset_type"] == "OPTION" else basis_delta
                    if consumed <= 0 or consumed > reservation["remaining_cents"]:
                        raise ValueError("invalid reservation consumption")
                    contractual_delta = basis_delta if row["asset_type"] == "OPTION" else 0
                    if (
                        int(row["basis_delta_cents"]) != basis_delta
                        or int(row["contractual_loss_delta_cents"]) != contractual_delta
                        or int(row["reservation_consumed_cents"]) != consumed
                    ):
                        raise ValueError("stored fill economics differ from replay")
                    reservation["filled_quantity"] += quantity
                    reservation["remaining_cents"] -= consumed
                    reservation["status"] = "FILLED" if reservation["remaining_cents"] == 0 else "PARTIAL"
                    key = (row["strategy"], row["symbol"])
                    state = positions.get(key)
                    if row["asset_type"] == "OPTION" and state is not None:
                        raise ValueError("duplicate option position fill")
                    if state is None:
                        state = positions[key] = {
                            "asset_type": row["asset_type"], "multiplier": multiplier,
                            "strategy_version": reservation_row["strategy_version"],
                            "quantity": Decimal("0"), "basis_cents": 0, "contractual_loss_cents": 0,
                            "opened_at": row["filled_at"], "entry_event_id": event_id,
                            "reservation_id": row["reservation_id"],
                        }
                    if (
                        state["asset_type"] != row["asset_type"] or state["multiplier"] != multiplier
                        or state["strategy_version"] != reservation_row["strategy_version"]
                        or state["reservation_id"] != row["reservation_id"]
                    ):
                        raise ValueError("position type conflict")
                    state["quantity"] += quantity
                    state["basis_cents"] += basis_delta
                    state["contractual_loss_cents"] += contractual_delta
                    expected_cash_events[f"FILL:{event_id}"] = -basis_delta
                    receipt = json.loads(row["receipt_json"])
                    expected_receipt = {
                        "event_id": event_id, "payload_hash": row["payload_hash"],
                        "quantity": str(state["quantity"]), "basis_cents": state["basis_cents"],
                        "remaining_cents": reservation["remaining_cents"],
                        "status": reservation["status"], "replay": False,
                    }
                    if receipt != expected_receipt:
                        raise ValueError("fill receipt differs from replay")

                elif kind == "CLOSE":
                    row = conn.execute(
                        "SELECT * FROM close_events WHERE account_id=? AND event_id=?", (self.account_id, event_id)
                    ).fetchone()
                    if row is None or row["closed_at"] != journal["occurred_at"]:
                        raise ValueError("missing close or journal timestamp mismatch")
                    payload = json.loads(row["payload_json"])
                    if sha256_json(payload) != row["payload_hash"]:
                        raise ValueError("close payload hash mismatch")
                    if (
                        payload.get("strategy") != row["strategy"] or payload.get("symbol") != row["symbol"]
                        or payload.get("quantity") != row["quantity"] or payload.get("closed_at") != row["closed_at"]
                    ):
                        raise ValueError("close identity mismatch")
                    key = (row["strategy"], row["symbol"])
                    state = positions.get(key)
                    quantity = decimal_value(row["quantity"], field="close.quantity", positive=True)
                    if state is None or state["asset_type"] != row["asset_type"] or quantity > state["quantity"]:
                        raise ValueError("close exceeds chronologically replayed position")
                    if occurred < aware_datetime(state["opened_at"], field="position.opened_at"):
                        raise ValueError("close predates replayed position")
                    basis_closed = int(
                        (Decimal(state["basis_cents"]) * quantity / state["quantity"]).to_integral_value(rounding=ROUND_CEILING)
                    )
                    if quantity < state["quantity"]:
                        basis_closed = min(basis_closed, state["basis_cents"] - 1)
                    contractual_closed = (
                        int((Decimal(state["contractual_loss_cents"]) * quantity / state["quantity"]).to_integral_value(rounding=ROUND_CEILING))
                        if state["asset_type"] == "OPTION" else 0
                    )
                    proceeds = _credit_cents(
                        quantity * decimal_value(payload.get("price"), field="close.price", nonnegative=True)
                        * state["multiplier"] - decimal_value(payload.get("costs"), field="close.costs", nonnegative=True),
                        field="close.proceeds", allow_zero=True,
                    )
                    realized = proceeds - basis_closed
                    if (
                        int(row["basis_delta_cents"]) != basis_closed
                        or int(row["contractual_loss_delta_cents"]) != contractual_closed
                        or int(row["proceeds_cents"]) != proceeds
                        or int(row["realized_pnl_cents"]) != realized
                    ):
                        raise ValueError("stored close economics differ from chronological replay")
                    state["quantity"] -= quantity
                    state["basis_cents"] -= basis_closed
                    state["contractual_loss_cents"] -= contractual_closed
                    replay_remaining_quantity = state["quantity"]
                    if state["quantity"] == 0:
                        del positions[key]
                    expected_cash_events[f"CLOSE:{event_id}"] = proceeds
                    realized_total += realized
                    if account["daily_loss_date"] == occurred.date().isoformat():
                        current_day_loss += max(0, -realized)
                    receipt = json.loads(row["receipt_json"])
                    expected_receipt = {
                        "event_id": event_id, "payload_hash": row["payload_hash"],
                        "net_proceeds_cents": proceeds, "realized_pnl_cents": realized,
                        "remaining_quantity": str(replay_remaining_quantity),
                        "replay": False,
                    }
                    if receipt != expected_receipt:
                        raise ValueError("close receipt differs from replay")

                else:
                    row = conn.execute(
                        "SELECT * FROM reservation_events WHERE account_id=? AND event_id=?",
                        (self.account_id, event_id),
                    ).fetchone()
                    if row is None or row["occurred_at"] != journal["occurred_at"]:
                        raise ValueError("missing reservation transition or journal timestamp mismatch")
                    payload = json.loads(row["payload_json"])
                    if sha256_json(payload) != row["payload_hash"]:
                        raise ValueError("reservation event payload hash mismatch")
                    reservation = reservations.get(row["reservation_id"])
                    if reservation is None or payload.get("reservation_id") != row["reservation_id"]:
                        raise ValueError("reservation event identity mismatch")
                    if row["event_type"] == "CREATE":
                        expected_payload = {"event_type": "CREATE", **reservation["durable_payload"]}
                        if (
                            payload != expected_payload or occurred != reservation["created_at"]
                            or reservation["status"] is not None
                        ):
                            raise ValueError("reservation creation event differs from durable reservation")
                        reservation["status"] = "OPEN"
                        reservation["remaining_cents"] = reservation["notional_cents"]
                    else:
                        expected_payload = {
                            "account_id": self.account_id, "reservation_id": row["reservation_id"],
                            "event_type": row["event_type"], "occurred_at": row["occurred_at"],
                            "strategy": reservation["row"]["strategy"],
                            "strategy_version": reservation["row"]["strategy_version"],
                            "symbol": reservation["row"]["symbol"],
                            "asset_type": reservation["row"]["asset_type"],
                            "prior_status": reservation["status"],
                            "prior_remaining_cents": reservation["remaining_cents"],
                            "reservation_payload_hash": reservation["row"]["payload_hash"],
                        }
                        if (
                            payload != expected_payload or reservation["status"] not in {"OPEN", "PARTIAL"}
                        ):
                            raise ValueError("reservation transition identity/state mismatch")
                    if row["event_type"] == "EXPIRE":
                        if occurred < reservation["expires_at"]:
                            raise ValueError("reservation expired before its deadline")
                        reservation["status"] = "EXPIRED"
                    elif row["event_type"] == "RELEASE":
                        reservation["status"] = "RELEASED"
                    elif row["event_type"] != "CREATE":
                        raise ValueError("unknown reservation transition")
                    if row["event_type"] in {"EXPIRE", "RELEASE"}:
                        reservation["remaining_cents"] = 0
                    receipt = json.loads(row["receipt_json"])
                    expected_receipt = (
                        {
                            "reservation_id": row["reservation_id"], "status": "OPEN",
                            "remaining_cents": reservation["notional_cents"],
                            "expires_at": reservation["row"]["expires_at"],
                            "reserved_quantity": reservation["row"]["reserved_quantity"],
                            "replay": False,
                        }
                        if row["event_type"] == "CREATE"
                        else {
                            "event_id": event_id, "reservation_id": row["reservation_id"],
                            "status": reservation["status"], "replay": False,
                        }
                    )
                    if receipt != expected_receipt:
                        raise ValueError("reservation event receipt differs from replay")
            except Exception as exc:
                errors.append(f"invalid journal event {kind}:{event_id}: {exc}")

        table_events = {
            "FILL": {row[0] for row in conn.execute("SELECT event_id FROM fill_events WHERE account_id=?", (self.account_id,))},
            "CLOSE": {row[0] for row in conn.execute("SELECT event_id FROM close_events WHERE account_id=?", (self.account_id,))},
            "RESERVATION": {row[0] for row in conn.execute("SELECT event_id FROM reservation_events WHERE account_id=?", (self.account_id,))},
        }
        for kind in table_events:
            if referenced[kind] != table_events[kind]:
                errors.append(f"{kind.lower()} event table and chronological journal differ")

        actual_cash_events = {
            row["external_event_id"]: int(row["delta_cents"])
            for row in conn.execute("SELECT * FROM cash_events WHERE account_id=?", (self.account_id,))
        }
        if actual_cash_events != expected_cash_events:
            errors.append("cash event journal does not match chronological replay")
        expected_cash = int(account["initial_cash_cents"]) + sum(expected_cash_events.values())
        if int(account["cash_cents"]) != expected_cash:
            errors.append("cash does not reconcile to durable events")
        if int(account["realized_pnl_cents"]) != realized_total:
            errors.append("realized P&L does not reconcile to replayed closes")
        if int(account["daily_loss_cents"]) != current_day_loss:
            errors.append("daily loss does not reconcile to current UTC-date replayed closes")

        actual_positions = {
            (row["strategy"], row["symbol"]): row
            for row in conn.execute("SELECT * FROM positions WHERE account_id=?", (self.account_id,))
        }
        if set(actual_positions) != set(positions):
            errors.append("position identities do not reconcile to chronological replay")
        for key in set(actual_positions) & set(positions):
            row, state = actual_positions[key], positions[key]
            try:
                if state["quantity"] <= 0 or state["basis_cents"] <= 0 or state["contractual_loss_cents"] < 0:
                    raise ValueError("replayed position is invalid")
                if (
                    Decimal(row["quantity"]) != state["quantity"] or int(row["basis_cents"]) != state["basis_cents"]
                    or int(row["contractual_loss_cents"]) != state["contractual_loss_cents"]
                    or row["asset_type"] != state["asset_type"] or row["strategy_version"] != state["strategy_version"]
                    or int(row["multiplier"]) != state["multiplier"]
                    or row["opened_at"] != state["opened_at"]
                    or row["reservation_id"] != state["reservation_id"]
                ):
                    raise ValueError("position quantity/basis/risk/time mismatch")
            except Exception as exc:
                errors.append(f"position {key[1]} does not reconcile: {exc}")

        for reservation_id, derived in reservations.items():
            row = derived["row"]
            if int(row["remaining_cents"]) != derived["remaining_cents"] or row["status"] != derived["status"]:
                errors.append(f"reservation {reservation_id} remaining/status differs from replay")
        expected_intents = {
            (row["strategy"], aware_datetime(row["created_at"], field="created_at").date().isoformat()): row["reservation_id"]
            for row in reservation_rows.values()
        }
        actual_intents = {
            (row["strategy"], row["intent_date"]): row["reservation_id"]
            for row in conn.execute("SELECT * FROM intent_days WHERE account_id=?", (self.account_id,))
        }
        if actual_intents != expected_intents:
            errors.append("intent-day materialization differs from reservations")
        return errors

    def clear_integrity_latch_after_repair(self, *, acknowledgement: str, now: datetime) -> None:
        """Explicitly clear a latch only after external repair and a clean event replay."""
        if acknowledgement != self._REPAIR_ACK:
            raise RiskRejected("exact repair acknowledgement is required")
        timestamp = aware_datetime(now, field="now")
        with self._transaction() as conn:
            if not self._account(conn)["integrity_latched"]:
                raise RiskRejected("integrity pause is not latched")
            self._advance_clock(conn, timestamp)
            errors = self._reconciliation_errors(conn)
            if errors:
                raise RiskRejected("repair is incomplete: " + "; ".join(errors))
            conn.execute(
                "UPDATE accounts SET integrity_latched=0,integrity_reason=NULL WHERE account_id=?",
                (self.account_id,),
            )
