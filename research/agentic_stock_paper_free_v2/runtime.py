"""Offline stock-only paper lifecycle consuming a hash-bound provider cycle."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any

from research.agentic_portfolio_paper_10000_v1.profile import verify_core_binding
from research.agentic_portfolio_v1.evidence import EvidencePacket
from research.agentic_portfolio_v1.risk import RiskLedger, RiskPolicy
from research.agentic_portfolio_v1.stock import STRATEGY, StockSwingEngine


HEX64 = re.compile(r"^[0-9a-f]{64}$")
PACKAGE_ROOT = Path(__file__).resolve().parent


class RuntimeBlocked(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_config() -> dict[str, Any]:
    from .freeze import verify
    errors = verify()
    if errors:
        raise RuntimeBlocked("free stock runtime freeze verification failed: " + "; ".join(errors))
    value = json.loads((PACKAGE_ROOT / "config.json").read_text())
    false_fields = ("orders_enabled", "broker_enabled", "model_calls_enabled", "network_enabled")
    if value.get("mode") != "PAPER_ONLY_NO_ORDER" or any(value.get(field) is not False for field in false_fields):
        raise RuntimeBlocked("runtime safety capabilities changed")
    if value.get("initial_cash") != "10000.00":
        raise RuntimeBlocked("runtime account capital changed")
    verify_core_binding()
    return value


def aware(value: Any, field: str) -> datetime:
    try:
        point = datetime.fromisoformat(value) if isinstance(value, str) else value
    except ValueError as exc:
        raise RuntimeBlocked(f"{field} must be ISO-8601") from exc
    if not isinstance(point, datetime) or point.tzinfo is None or point.utcoffset() is None:
        raise RuntimeBlocked(f"{field} must be timezone-aware")
    return point.astimezone(timezone.utc)


def _exact(value: Any, fields: set[str], name: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise RuntimeBlocked(f"{name} fields do not match the contract")
    return value


def _packet(raw: Any, decision_at: datetime, kind: str, max_age: timedelta) -> EvidencePacket:
    if type(raw) is not dict:
        raise RuntimeBlocked(f"{kind} packet must be an object")
    try:
        packet = EvidencePacket.from_dict(raw)
        packet.validate_at(decision_at, max_age)
    except Exception as exc:
        raise RuntimeBlocked(f"invalid or stale {kind} packet: {exc}") from exc
    if packet.kind != kind:
        raise RuntimeBlocked(f"expected {kind} packet")
    return packet


def validate_cycle(raw: Any) -> tuple[dict[str, Any], datetime, list[EvidencePacket], list[EvidencePacket]]:
    config = load_config()
    cycle = _exact(raw, {
        "schema_version", "cycle_id", "decision_at", "completed_session_date", "coverage",
        "stock_entries", "stock_management", "cycle_hash",
    }, "cycle")
    if cycle["schema_version"] != "1.0" or not isinstance(cycle["cycle_id"], str) or not cycle["cycle_id"]:
        raise RuntimeBlocked("invalid cycle identity")
    supplied = cycle["cycle_hash"]
    unsigned = {key: value for key, value in cycle.items() if key != "cycle_hash"}
    if not isinstance(supplied, str) or supplied != sha256_bytes(canonical(unsigned).encode()):
        raise RuntimeBlocked("cycle hash mismatch")
    point = aware(cycle["decision_at"], "decision_at")
    coverage = _exact(cycle["coverage"], {
        "source_mode", "stock_history_sessions", "stock_symbols", "stock_observed_at",
        "earnings_calendar_through", "news_lookback_seconds", "context_complete", "receipt_hashes",
    }, "coverage")
    if coverage["source_mode"] != config["source_mode"]:
        raise RuntimeBlocked("stock data source mode differs from the frozen free profile")
    if coverage["stock_symbols"] != config["stock_symbols"]:
        raise RuntimeBlocked("stock universe is incomplete")
    history = coverage["stock_history_sessions"]
    if type(history) is not dict or sorted(history) != config["stock_symbols"]:
        raise RuntimeBlocked("point-in-time history coverage is incomplete")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < config["minimum_history_sessions"] for value in history.values()):
        raise RuntimeBlocked("fewer than 50 point-in-time history sessions")
    if coverage["context_complete"] is not True or coverage["news_lookback_seconds"] < 86400:
        raise RuntimeBlocked("24-hour bounded direct-news context is incomplete")
    stock_at = aware(coverage["stock_observed_at"], "stock_observed_at")
    if point - stock_at < timedelta(0) or (point - stock_at).total_seconds() > config["stock_max_age_seconds"]:
        raise RuntimeBlocked("stock coverage is older than five minutes")
    try:
        through = datetime.fromisoformat(coverage["earnings_calendar_through"]).date()
    except (TypeError, ValueError) as exc:
        raise RuntimeBlocked("earnings calendar horizon is invalid") from exc
    if through < (point + timedelta(days=config["earnings_horizon_days"])).date():
        raise RuntimeBlocked("earnings calendar does not cover the required horizon")
    receipts = coverage["receipt_hashes"]
    if type(receipts) is not dict or sorted(receipts) != sorted(config["required_receipts"]):
        raise RuntimeBlocked("required source receipts are missing")
    if any(not isinstance(value, str) or not HEX64.fullmatch(value) for value in receipts.values()):
        raise RuntimeBlocked("source receipt hashes must be SHA-256 values")
    for field in ("stock_entries", "stock_management"):
        if type(cycle[field]) is not list:
            raise RuntimeBlocked(f"{field} must be a list")
    max_age = timedelta(seconds=config["stock_max_age_seconds"])
    entries = [_packet(value, point, "stock_entry", max_age) for value in cycle["stock_entries"]]
    management = [_packet(value, point, "stock_management", max_age) for value in cycle["stock_management"]]
    if sorted(packet.symbol for packet in entries) != config["stock_symbols"]:
        raise RuntimeBlocked("one fresh stock-entry packet per frozen symbol is required")
    if sorted(packet.symbol for packet in management) != config["stock_symbols"]:
        raise RuntimeBlocked("one fresh management packet per frozen symbol is required")
    if any(isinstance(packet.data.get("earnings_sessions_away"), bool) or not isinstance(packet.data.get("earnings_sessions_away"), int) for packet in entries):
        raise RuntimeBlocked("earnings distance must be known for every stock")
    session = cycle["completed_session_date"]
    if session is not None:
        try:
            session_date = datetime.fromisoformat(session).date()
        except (TypeError, ValueError) as exc:
            raise RuntimeBlocked("completed_session_date must be an ISO date") from exc
        if session_date > point.date():
            raise RuntimeBlocked("completed session cannot be in the future")
    return cycle, point, entries, management


class Journal:
    def __init__(self, path: Path):
        self.path = path
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS cycles(
              cycle_id TEXT PRIMARY KEY, input_hash TEXT NOT NULL, status TEXT NOT NULL,
              output_json TEXT, created_at TEXT NOT NULL, completed_at TEXT,
              CHECK(status IN ('PENDING','COMPLETE'))
            );
            CREATE TABLE IF NOT EXISTS stock_metadata(
              symbol TEXT PRIMARY KEY, thesis TEXT NOT NULL, invalidation TEXT NOT NULL,
              evidence_hash TEXT NOT NULL, opened_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS completed_sessions(
              session_date TEXT PRIMARY KEY, cycle_id TEXT NOT NULL
            );
            """)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def begin(self, cycle_id: str, digest: str, now: datetime) -> dict[str, Any] | None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            pending = db.execute("SELECT cycle_id FROM cycles WHERE status='PENDING'").fetchone()
            row = db.execute("SELECT * FROM cycles WHERE cycle_id=?", (cycle_id,)).fetchone()
            if row:
                if row["input_hash"] != digest:
                    raise RuntimeBlocked("cycle_id reused with different input")
                if row["status"] == "PENDING":
                    raise RuntimeBlocked("pending cycle requires owner inspection")
                return json.loads(row["output_json"])
            if pending:
                raise RuntimeBlocked("an earlier pending cycle requires owner inspection")
            db.execute("INSERT INTO cycles VALUES(?,?,?,?,?,?)", (cycle_id, digest, "PENDING", None, now.isoformat(), None))
            db.commit()
        return None

    def complete(self, cycle_id: str, output: dict[str, Any], now: datetime, session: str | None) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM cycles WHERE cycle_id=?", (cycle_id,)).fetchone()
            if row is None or row["status"] != "PENDING":
                raise RuntimeBlocked("cycle journal completion mismatch")
            db.execute("UPDATE cycles SET status='COMPLETE',output_json=?,completed_at=? WHERE cycle_id=?", (canonical(output), now.isoformat(), cycle_id))
            if session is not None:
                db.execute("INSERT OR IGNORE INTO completed_sessions VALUES(?,?)", (session, cycle_id))
            db.commit()

    def save_stock(self, symbol: str, thesis: str, invalidation: str, evidence_hash: str, opened_at: datetime) -> None:
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO stock_metadata VALUES(?,?,?,?,?)", (symbol, thesis, invalidation, evidence_hash, opened_at.isoformat()))

    def stock(self, symbol: str) -> sqlite3.Row | None:
        with self.connect() as db:
            return db.execute("SELECT * FROM stock_metadata WHERE symbol=?", (symbol,)).fetchone()

    def remove_stock(self, symbol: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM stock_metadata WHERE symbol=?", (symbol,))

    def completed_sessions(self) -> int:
        with self.connect() as db:
            return int(db.execute("SELECT count(*) FROM completed_sessions").fetchone()[0])

    def has_session(self, session: str | None) -> bool:
        if session is None:
            return False
        with self.connect() as db:
            return db.execute("SELECT 1 FROM completed_sessions WHERE session_date=?", (session,)).fetchone() is not None


def _close_count(path: Path) -> int:
    with sqlite3.connect(str(path)) as db:
        return int(db.execute("SELECT count(*) FROM close_events").fetchone()[0])


def _stock_exit_cost(quantity: Decimal, price: Decimal) -> Decimal:
    return quantity * price * Decimal("0.001")


def _checkpoint(paths: list[Path]) -> None:
    gc.collect()
    for path in paths:
        connection = sqlite3.connect(str(path), timeout=10, isolation_level=None)
        try:
            row = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if row is None or row[0] != 0:
                raise RuntimeBlocked(f"could not checkpoint {path.name}")
            mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()
            if mode is None or str(mode[0]).lower() != "delete":
                raise RuntimeBlocked(f"could not close WAL mode for {path.name}")
        finally:
            connection.close()
    gc.collect()


def process_cycle(cycle_raw: dict[str, Any], state_root: Path) -> dict[str, Any]:
    config = load_config()
    cycle, point, entries, management = validate_cycle(cycle_raw)
    root = Path(state_root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeBlocked("state root must be a real directory")
    ledger_path = root / "stock.sqlite"
    journal = Journal(root / "runtime.sqlite")
    replay = journal.begin(cycle["cycle_id"], cycle["cycle_hash"], point)
    if replay is not None:
        _checkpoint([journal.path])
        return {**replay, "replay": True}
    ledger = RiskLedger(str(ledger_path), config["account_id"], Decimal(config["initial_cash"]), RiskPolicy())
    engine = StockSwingEngine(ledger)
    events: list[dict[str, Any]] = []
    management_by_symbol = {packet.symbol: packet for packet in management}
    positions = [position for position in ledger.open_positions() if position["strategy"] == STRATEGY]
    had_positions = bool(positions)
    for position in positions:
        packet = management_by_symbol[position["symbol"]]
        price = Decimal(str(packet.data["price"]))
        ledger.set_mark(position["symbol"], price, point, asset_type="EQUITY")
        meta = journal.stock(position["symbol"])
        if meta is None:
            raise RuntimeBlocked("stock plan metadata is missing")
        plan = engine.plan_from_fills(
            symbol=position["symbol"], opened_at=datetime.fromisoformat(meta["opened_at"]),
            thesis=meta["thesis"], invalidation=meta["invalidation"], evidence_hash=meta["evidence_hash"],
        )
        decision = engine.evaluate_position(plan, packet, sessions_held=0, decision_at=point)
        event = {"phase": "management", "symbol": position["symbol"], "action": decision.action, "reasons": list(decision.reasons)}
        if decision.action == "PAPER_EXIT_INTENT":
            receipt = ledger.close_position(
                strategy=STRATEGY, symbol=position["symbol"], quantity=Decimal(position["quantity"]),
                price=price, costs=_stock_exit_cost(Decimal(position["quantity"]), price), closed_at=point,
                reason=decision.reasons[0], event_id=f"{cycle['cycle_id']}:stock-close:{position['symbol']}",
            )
            event["close"] = receipt
            journal.remove_stock(position["symbol"])
        events.append(event)
    if not had_positions and not ledger.open_positions():
        for packet in entries:
            decision = engine.evaluate_entry(packet, point, f"{cycle['cycle_id']}:stock:{packet.symbol}")
            event = {"phase": "entry", "symbol": packet.symbol, "action": decision.action, "reasons": list(decision.reasons)}
            if decision.action == "PAPER_ENTRY_INTENT":
                quantity = Decimal(decision.details["quantity"])
                price = Decimal(decision.details["modeled_entry_price"])
                debit = Decimal(decision.details["modeled_entry_debit"])
                reservation = decision.details["reservation"]
                fill = ledger.record_fill(
                    reservation_id=reservation["reservation_id"], quantity=quantity, price=price,
                    costs=debit - quantity * price, filled_at=point,
                    event_id=f"{cycle['cycle_id']}:stock-fill:{packet.symbol}",
                )
                ledger.set_mark(packet.symbol, price, point, asset_type="EQUITY")
                journal.save_stock(packet.symbol, packet.data["thesis"], packet.data["invalidation"], packet.evidence_hash, point)
                event["fill"] = fill
                events.append(event)
                break
            events.append(event)
    session = cycle["completed_session_date"]
    completed = journal.completed_sessions() + (1 if session is not None and not journal.has_session(session) else 0)
    closed = _close_count(ledger_path)
    review = {
        "completed_sessions": completed,
        "closed_trades": closed,
        "minimum_completed_sessions": config["review"]["minimum_completed_sessions"],
        "minimum_closed_trades": config["review"]["minimum_closed_trades"],
        "eligible_for_review_not_proof": completed >= config["review"]["minimum_completed_sessions"] and closed >= config["review"]["minimum_closed_trades"],
        "promotion_enabled": False,
        "proof_of_profitability": False,
    }
    output = {
        "schema_version": "1.0", "mode": "PAPER_ONLY_NO_ORDER", "source_mode": config["source_mode"],
        "status": "PAPER_STOCK_CYCLE_COMPLETE", "cycle_id": cycle["cycle_id"], "decision_at": point.isoformat(),
        "orders_enabled": False, "broker_enabled": False, "events": events,
        "stock_account": ledger.snapshot(point), "review": review, "replay": False,
    }
    journal.complete(cycle["cycle_id"], output, point, session)
    _checkpoint([ledger_path, journal.path])
    return output


def blocked_status(reason: str, *, checked_at: datetime | None = None) -> dict[str, Any]:
    point = (checked_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "schema_version": "1.0", "mode": "PAPER_ONLY_NO_ORDER", "status": "BLOCKED_DATA",
        "checked_at": point.isoformat(), "reason": reason[:300], "orders_enabled": False,
        "broker_enabled": False, "completed_session_counted": False,
    }


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix(path.suffix + ".tmp")
    raw = (canonical(value) + "\n").encode()
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temp, path)
