"""Offline paired forward-trial runner with no network, model, or execution surface."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
import gc
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import statistics
from typing import Any

from .binding import (
    CORE_MANIFEST_SHA256, PROFILE_MANIFEST_SHA256, BindingError, verify_frozen_bindings,
)
from .context import ContextResult, evaluate_context
from .receipts import (
    ArchiveReceipt, ReceiptError, aware_utc, canonical_json, decimal_string, plain_object, sha256_json,
)


PACKAGE_VERSION = "3.0.0"
ORDERS_ENABLED = False
NETWORK_ENABLED = False
MODEL_CALLS_ENABLED = False
BROKER_ENABLED = False
DEPLOY_ENABLED = False
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class TrialError(ValueError):
    pass


@dataclass(frozen=True)
class RunOutcome:
    receipt: dict[str, Any]
    replay: bool


@dataclass(frozen=True)
class TrialRuntime:
    root: Path
    ledgers: dict[str, Any]
    engines: dict[str, Any]
    journal: "DecisionJournal"
    config: dict[str, Any]

    def checkpoint_and_close(self) -> None:
        """Cleanly checkpoint package-owned WALs before a deliberate reopen."""
        # The frozen core uses short-lived sqlite connection context managers;
        # collect their finalized objects before checkpointing their WAL files.
        gc.collect()
        paths = [Path(ledger.path) for ledger in self.ledgers.values()] + [self.journal.path]
        for path in paths:
            connection = sqlite3.connect(str(path), timeout=10, isolation_level=None)
            try:
                row = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                if row is None or row[0] != 0:
                    raise TrialError(f"could not checkpoint state file: {path.name}")
            finally:
                connection.close()
        gc.collect()


def load_config() -> dict[str, Any]:
    from .freeze import verify as verify_self
    freeze_errors = verify_self()
    if freeze_errors:
        raise TrialError("forward-trial freeze verification failed: " + "; ".join(freeze_errors))
    path = Path(__file__).with_name("config.json")
    try:
        raw = plain_object(json.loads(path.read_text(encoding="utf-8")), "config")
    except (OSError, UnicodeError, json.JSONDecodeError, ReceiptError) as exc:
        raise TrialError("invalid forward-trial configuration") from exc
    expected = {
        "schema_version", "package_version", "mode", "orders_enabled", "network_enabled",
        "lifecycle", "model_calls_enabled", "broker_enabled", "deploy_enabled", "frozen_bindings", "arms",
        "stock_universe", "option_underlyings", "market_context_symbols", "archive", "context_gate",
    }
    if set(raw) != expected or raw["schema_version"] != "1.0" or raw["package_version"] != PACKAGE_VERSION:
        raise TrialError("configuration schema/version mismatch")
    if raw["mode"] != "PAPER_ONLY_NO_ORDER":
        raise TrialError("configuration is not paper-only")
    if raw["lifecycle"] != "ENTRY_GATE_ONLY_BLOCKED":
        raise TrialError("this version must remain an entry-gate-only blocked observer")
    for capability in ("orders_enabled", "network_enabled", "model_calls_enabled", "broker_enabled", "deploy_enabled"):
        if raw[capability] is not False:
            raise TrialError(f"{capability} must remain literal false")
    bindings = plain_object(raw["frozen_bindings"], "frozen_bindings")
    if bindings != {
        "agentic_portfolio_v1_manifest_sha256": CORE_MANIFEST_SHA256,
        "agentic_portfolio_paper_10000_v1_manifest_sha256": PROFILE_MANIFEST_SHA256,
    }:
        raise TrialError("configuration frozen bindings differ from code pins")
    arms = plain_object(raw["arms"], "arms")
    expected_arms = {"price_stock", "context_stock", "price_options", "context_options"}
    if set(arms) != expected_arms:
        raise TrialError("exactly four isolated arms are required")
    account_ids: set[str] = set()
    for name, value in arms.items():
        account = plain_object(value, f"arms.{name}")
        if set(account) != {"account_id", "initial_cash"} or account["initial_cash"] != "10000.00":
            raise TrialError("every arm must be a distinct fixed $10,000 simulation")
        if not isinstance(account["account_id"], str) or not account["account_id"].strip():
            raise TrialError("virtual account IDs must be non-empty")
        account_ids.add(account["account_id"])
    if len(account_ids) != 4:
        raise TrialError("virtual account IDs must be unique")
    if raw["stock_universe"] != ["AAOI", "CIEN", "COHR", "FN", "LITE"]:
        raise TrialError("stock universe drift")
    if raw["option_underlyings"] != ["QQQ", "SPY"]:
        raise TrialError("option universe drift")
    if raw["market_context_symbols"] != ["DIA", "IWM", "QQQ", "SPY", "XLK"]:
        raise TrialError("market context universe drift")
    return json.loads(canonical_json(raw))


def _safe_state_root(root: Path) -> Path:
    candidate = Path(root)
    if candidate.exists():
        if candidate.is_symlink() or not candidate.is_dir():
            raise TrialError("state root must be a real directory")
    else:
        parent = candidate.parent
        if parent.is_symlink() or not parent.is_dir():
            raise TrialError("state parent must be a real existing directory")
        candidate.mkdir(mode=0o700)
    return candidate.resolve()


def _safe_file(path: Path) -> None:
    if path.exists():
        stat = path.lstat()
        if path.is_symlink() or not path.is_file() or stat.st_nlink != 1:
            raise TrialError(f"unsafe state file: {path.name}")


def _load_core(repo_root: Path) -> tuple[Any, Any, Any, Any]:
    verify_frozen_bindings(repo_root)
    # Imports occur only after the complete byte-level binding check succeeds.
    from research.agentic_portfolio_v1.evidence import EvidencePacket
    from research.agentic_portfolio_v1.options import OptionShadowEngine
    from research.agentic_portfolio_v1.risk import RiskLedger, RiskPolicy
    from research.agentic_portfolio_v1.stock import StockSwingEngine
    return EvidencePacket, RiskLedger, RiskPolicy, (StockSwingEngine, OptionShadowEngine)


class DecisionJournal:
    """Durable request idempotency. PENDING is a fail-closed crash marker."""

    def __init__(self, path: Path):
        _safe_file(path)
        self.path = path
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS decisions(
                account_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                request_hash TEXT NOT NULL, status TEXT NOT NULL,
                receipt_json TEXT, created_at TEXT NOT NULL, completed_at TEXT,
                PRIMARY KEY(account_id,idempotency_key),
                CHECK(status IN ('PENDING','COMPLETE'))
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    @staticmethod
    def _validate_key(account_id: str, key: str, request_hash: str) -> None:
        if not isinstance(account_id, str) or not account_id.strip():
            raise TrialError("account_id must be non-empty")
        if not isinstance(key, str) or not key.strip() or len(key) > 200:
            raise TrialError("idempotency key must be bounded and non-empty")
        if not isinstance(request_hash, str) or not _HEX64.fullmatch(request_hash):
            raise TrialError("request hash must be SHA-256")

    @staticmethod
    def _parse_stored(
        value: Any, *, expected_account: str | None = None, expected_request_hash: str | None = None,
    ) -> dict[str, Any]:
        try:
            receipt = plain_object(json.loads(value), "stored receipt")
        except (TypeError, json.JSONDecodeError, ReceiptError) as exc:
            raise TrialError("stored receipt is malformed") from exc
        supplied = receipt.get("receipt_hash")
        if not isinstance(supplied, str) or not _HEX64.fullmatch(supplied):
            raise TrialError("stored receipt hash is malformed")
        unsigned = {key: item for key, item in receipt.items() if key != "receipt_hash"}
        if sha256_json(unsigned) != supplied:
            raise TrialError("stored receipt hash mismatch")
        expected_fields = {
            "schema_version", "package_version", "mode", "lifecycle", "arm", "virtual_account",
            "strategy", "strategy_version", "decision_at", "action", "reasons", "source_receipts",
            "macro_event_id", "details", "frozen_bindings", "paper_only", "no_order",
            "orders_enabled", "request_hash", "receipt_hash",
        }
        if set(receipt) != expected_fields:
            raise TrialError("stored receipt fields do not match the frozen schema")
        literals = {
            "schema_version": "1.0", "package_version": PACKAGE_VERSION,
            "mode": "PAPER_ONLY_NO_ORDER", "lifecycle": "ENTRY_GATE_ONLY_BLOCKED",
            "paper_only": True, "no_order": True, "orders_enabled": False,
        }
        if any(type(receipt[key]) is not type(expected) or receipt[key] != expected
               for key, expected in literals.items()):
            raise TrialError("stored receipt safety identity is invalid")
        if receipt["arm"] not in {"price_stock", "context_stock", "price_options", "context_options"}:
            raise TrialError("stored receipt arm is invalid")
        for field in ("virtual_account", "strategy", "strategy_version"):
            if not isinstance(receipt[field], str) or not receipt[field].strip():
                raise TrialError(f"stored receipt {field} is invalid")
        if expected_account is not None and receipt["virtual_account"] != expected_account:
            raise TrialError("stored receipt account does not match its journal row")
        if receipt["action"] not in {"PAPER_ENTRY_INTENT", "ABSTAIN", "BLOCKED_DATA"}:
            raise TrialError("stored receipt action is invalid")
        if type(receipt["reasons"]) is not list or any(not isinstance(reason, str) for reason in receipt["reasons"]):
            raise TrialError("stored receipt reasons are invalid")
        plain_object(receipt["details"], "stored receipt details")
        aware_utc(receipt["decision_at"], "stored receipt decision_at")
        request_hash = receipt["request_hash"]
        if not isinstance(request_hash, str) or not _HEX64.fullmatch(request_hash):
            raise TrialError("stored receipt request hash is invalid")
        if expected_request_hash is not None and request_hash != expected_request_hash:
            raise TrialError("stored receipt request hash does not match its journal row")
        if receipt["frozen_bindings"] != {
            "agentic_portfolio_v1_manifest_sha256": CORE_MANIFEST_SHA256,
            "agentic_portfolio_paper_10000_v1_manifest_sha256": PROFILE_MANIFEST_SHA256,
        }:
            raise TrialError("stored receipt frozen bindings are invalid")
        if receipt["macro_event_id"] is not None and not isinstance(receipt["macro_event_id"], str):
            raise TrialError("stored receipt macro_event_id is invalid")
        sources = receipt["source_receipts"]
        if type(sources) is not list:
            raise TrialError("stored receipt provenance is invalid")
        source_fields = {
            "receipt_id", "kind", "provider", "observed_at", "retrieved_at", "archived_at", "receipt_hash",
        }
        for source in sources:
            if type(source) is not dict or set(source) != source_fields:
                raise TrialError("stored receipt provenance fields are invalid")
            if not isinstance(source["receipt_hash"], str) or not _HEX64.fullmatch(source["receipt_hash"]):
                raise TrialError("stored source receipt hash is invalid")
            observed = aware_utc(source["observed_at"], "stored source observed_at")
            retrieved = aware_utc(source["retrieved_at"], "stored source retrieved_at")
            archived = aware_utc(source["archived_at"], "stored source archived_at")
            if observed > retrieved or retrieved > archived:
                raise TrialError("stored source chronology is invalid")
        return receipt

    def begin_many(
        self, requests: list[tuple[str, str, str]], now: datetime,
    ) -> dict[str, tuple[str, dict[str, Any] | None]]:
        point = aware_utc(now, "decision_at").isoformat()
        if len({(a, k) for a, k, _ in requests}) != len(requests):
            raise TrialError("duplicate request identity in one admission")
        for account, key, request_hash in requests:
            self._validate_key(account, key, request_hash)
        outcome: dict[str, tuple[str, dict[str, Any] | None]] = {}
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            for account, key, request_hash in requests:
                row = db.execute(
                    "SELECT request_hash,status,receipt_json FROM decisions WHERE account_id=? AND idempotency_key=?",
                    (account, key),
                ).fetchone()
                if row is None:
                    continue
                if row["request_hash"] != request_hash:
                    raise TrialError("conflicting idempotency-key reuse")
                if row["status"] == "COMPLETE":
                    outcome[account] = (
                        "COMPLETE", self._parse_stored(
                            row["receipt_json"], expected_account=account,
                            expected_request_hash=request_hash,
                        ),
                    )
                elif row["status"] == "PENDING" and row["receipt_json"] is None:
                    outcome[account] = ("PENDING", None)
                else:
                    raise TrialError("journal state is invalid")
            for account, key, request_hash in requests:
                if account not in outcome:
                    db.execute(
                        "INSERT INTO decisions VALUES (?,?,?,?,?,?,?)",
                        (account, key, request_hash, "PENDING", None, point, None),
                    )
                    outcome[account] = ("NEW", None)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return outcome

    def complete(
        self, account_id: str, key: str, request_hash: str,
        receipt: dict[str, Any], now: datetime,
    ) -> None:
        self._validate_key(account_id, key, request_hash)
        parsed = self._parse_stored(
            canonical_json(receipt), expected_account=account_id,
            expected_request_hash=request_hash,
        )
        point = aware_utc(now, "decision_at").isoformat()
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT request_hash,status,receipt_json FROM decisions WHERE account_id=? AND idempotency_key=?",
                (account_id, key),
            ).fetchone()
            if row is None or row["request_hash"] != request_hash:
                raise TrialError("missing or conflicting pending request")
            if row["status"] == "COMPLETE":
                if self._parse_stored(
                    row["receipt_json"], expected_account=account_id,
                    expected_request_hash=request_hash,
                ) != parsed:
                    raise TrialError("completed receipt replay conflicts")
            elif row["status"] == "PENDING" and row["receipt_json"] is None:
                db.execute(
                    "UPDATE decisions SET status='COMPLETE',receipt_json=?,completed_at=? WHERE account_id=? AND idempotency_key=?",
                    (canonical_json(parsed), point, account_id, key),
                )
            else:
                raise TrialError("journal state is invalid")
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def _preflight_journal(path: Path, account_ids: set[str], profile: Any) -> str:
    identity = profile._ledger_identity(path)
    if identity is None:
        return "ABSENT"
    profile._require_no_sqlite_sidecars(path)
    before = profile._content_signature(path)
    if before[2] == 0:
        if profile._content_signature(path) != before:
            raise TrialError("empty decision journal changed during preflight")
        return "EMPTY"
    connection: sqlite3.Connection | None = None
    failure: TrialError | None = None
    try:
        connection = sqlite3.connect(path.absolute().as_uri() + "?mode=ro&immutable=1", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        if [row[0] for row in connection.execute("PRAGMA integrity_check")] != ["ok"]:
            raise TrialError("decision journal failed SQLite integrity_check")
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if tables != {"decisions"}:
            raise TrialError("decision journal table set is incompatible")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(decisions)")}
        if columns != {
            "account_id", "idempotency_key", "request_hash", "status", "receipt_json",
            "created_at", "completed_at",
        }:
            raise TrialError("decision journal columns are incompatible")
        for row in connection.execute("SELECT * FROM decisions"):
            if row["account_id"] not in account_ids:
                raise TrialError("decision journal contains a foreign virtual account")
            DecisionJournal._validate_key(row["account_id"], row["idempotency_key"], row["request_hash"])
            aware_utc(row["created_at"], "journal.created_at")
            if row["status"] == "PENDING":
                if row["receipt_json"] is not None or row["completed_at"] is not None:
                    raise TrialError("pending decision journal row is malformed")
            elif row["status"] == "COMPLETE":
                DecisionJournal._parse_stored(
                    row["receipt_json"], expected_account=row["account_id"],
                    expected_request_hash=row["request_hash"],
                )
                aware_utc(row["completed_at"], "journal.completed_at")
            else:
                raise TrialError("decision journal status is invalid")
    except (sqlite3.Error, OSError, TypeError, ValueError, KeyError) as exc:
        if isinstance(exc, TrialError):
            failure = exc
        else:
            failure = TrialError("decision journal is not a compatible database")
            failure.__cause__ = exc
    finally:
        if connection is not None:
            connection.close()
    profile._require_no_sqlite_sidecars(path)
    if profile._content_signature(path) != before:
        raise TrialError("decision journal changed during read-only preflight")
    if failure is not None:
        raise failure
    return "COMPATIBLE"


def build_trial(state_root: Path, repo_root: Path | None = None) -> TrialRuntime:
    """Open four physically separate $10k paper ledgers after frozen-binding verification."""
    config = load_config()
    repo = Path(__file__).resolve().parents[2] if repo_root is None else Path(repo_root).resolve()
    EvidencePacket, RiskLedger, RiskPolicy, engines = _load_core(repo)
    del EvidencePacket
    from research.agentic_portfolio_paper_10000_v1 import profile as frozen_profile
    root = _safe_state_root(Path(state_root))
    paths = {name: root / f"{name}.sqlite" for name in config["arms"]}
    journal_path = root / "decision_journal.sqlite"
    all_paths = {**paths, "decision_journal": journal_path}
    before = frozen_profile._ledger_snapshot(all_paths)
    frozen_profile._require_distinct_ledgers(before)
    identities = {name: identity for name, identity in before.items() if identity is not None}
    policy = RiskPolicy()
    policy_hash = frozen_profile._core_policy_hash(RiskLedger, policy)
    # Preflight every existing peer read-only before any constructor or file creation.
    for name, path in paths.items():
        frozen_profile._preflight_existing_ledger(
            path, expected_account_id=config["arms"][name]["account_id"],
            expected_policy_hash=policy_hash, RiskLedger=RiskLedger, policy=policy,
        )
    _preflight_journal(
        journal_path, {config["arms"][name]["account_id"] for name in paths}, frozen_profile,
    )
    after_preflight = frozen_profile._ledger_snapshot(all_paths)
    frozen_profile._require_distinct_ledgers(after_preflight)
    frozen_profile._require_identities_unchanged(identities, after_preflight)
    ledgers: dict[str, Any] = {}

    def construct(name: str) -> Any:
        account = config["arms"][name]
        return RiskLedger(str(paths[name]), account["account_id"], Decimal("10000.00"), policy)

    # Open compatible existing ledgers only after the entire peer set passed.
    for name in paths:
        if before[name] is None:
            continue
        current = frozen_profile._ledger_snapshot(all_paths)
        frozen_profile._require_distinct_ledgers(current)
        frozen_profile._require_identities_unchanged(identities, current)
        ledgers[name] = construct(name)

    # Exclusively claim every absent name, checking all identities around each step.
    for name, path in all_paths.items():
        if before[name] is not None:
            continue
        current = frozen_profile._ledger_snapshot(all_paths)
        frozen_profile._require_distinct_ledgers(current)
        frozen_profile._require_identities_unchanged(identities, current)
        if current[name] is not None:
            raise TrialError(f"state path appeared during initialization: {name}")
        identities[name] = frozen_profile._create_empty_ledger_file(path)

    for name in paths:
        if name not in ledgers:
            ledgers[name] = construct(name)
    current = frozen_profile._ledger_snapshot(all_paths)
    frozen_profile._require_distinct_ledgers(current)
    frozen_profile._require_identities_unchanged(identities, current)
    StockSwingEngine, OptionShadowEngine = engines
    engine_map = {
        "price_stock": StockSwingEngine(ledgers["price_stock"]),
        "context_stock": StockSwingEngine(ledgers["context_stock"]),
        "price_options": OptionShadowEngine(ledgers["price_options"], mode="baseline"),
        "context_options": OptionShadowEngine(ledgers["context_options"], mode="baseline"),
    }
    journal = DecisionJournal(journal_path)
    final = frozen_profile._ledger_snapshot(all_paths)
    frozen_profile._require_distinct_ledgers(final)
    frozen_profile._require_identities_unchanged(identities, final)
    return TrialRuntime(root, ledgers, engine_map, journal, config)


def _require_receipt(value: Any, kind: str, cutoff: datetime, max_age: timedelta) -> ArchiveReceipt:
    if not isinstance(value, ArchiveReceipt):
        raise ReceiptError(f"{kind} receipt is missing")
    if value.kind != kind:
        raise ReceiptError(f"expected {kind} receipt")
    value.validate_at(cutoff, max_age=max_age)
    return value


def _raw_hash(value: Any) -> str | None:
    if isinstance(value, ArchiveReceipt):
        return value.receipt_hash
    return None


def _validate_hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ReceiptError(f"{field} must bind a raw archived source with SHA-256")
    return value


def _stock_packet(runtime: TrialRuntime, receipt: ArchiveReceipt, cutoff: datetime) -> Any:
    item = _require_receipt(receipt, "STOCK_PRICE_INPUT", cutoff, timedelta(minutes=5))
    expected = {
        "symbol", "price", "next_ask", "entry_limit", "dollar_volumes_20", "atr14",
        "session_return", "session_vwap", "sma50", "earnings_sessions_away",
        "daily_history_complete", "daily_history_hash", "earnings_calendar_hash",
    }
    if set(item.payload) != expected:
        raise ReceiptError("stock input is incomplete; all frozen fields are required")
    data = item.payload
    symbol = data["symbol"]
    if symbol not in runtime.config["stock_universe"]:
        raise ReceiptError("stock symbol lies outside the frozen universe")
    if data["daily_history_complete"] is not True:
        raise ReceiptError("daily history completeness is not proven")
    _validate_hash(data["daily_history_hash"], "daily_history_hash")
    _validate_hash(data["earnings_calendar_hash"], "earnings_calendar_hash")
    numeric = ("price", "next_ask", "entry_limit", "atr14", "session_return", "session_vwap", "sma50")
    for field in numeric:
        decimal_string(data[field], field)
    volumes = data["dollar_volumes_20"]
    if type(volumes) is not list or len(volumes) != 20:
        raise ReceiptError("dollar_volumes_20 must contain exactly 20 archived values")
    for index, value in enumerate(volumes):
        decimal_string(value, f"dollar_volumes_20[{index}]")
    earnings = data["earnings_sessions_away"]
    if type(earnings) is not int or earnings < 0:
        raise ReceiptError("earnings_sessions_away must be a known nonnegative integer")
    verify_frozen_bindings(Path(__file__).resolve().parents[2])
    from research.agentic_portfolio_v1.evidence import EvidencePacket
    from research.agentic_portfolio_v1.stock import STRATEGY, VERSION
    core_data = {key: data[key] for key in numeric}
    core_data["dollar_volumes_20"] = list(volumes)
    core_data["earnings_sessions_away"] = earnings
    # Frozen control constants disable context; they do not assert neutral real-world news.
    core_data.update({
        "hard_adverse_news": False, "thesis_broken": False,
        "thesis": "frozen technical forward-trial candidate",
        "invalidation": "frozen engine review and thesis-break rules",
    })
    return EvidencePacket.build(
        kind="stock_entry", strategy=STRATEGY, version=VERSION, symbol=symbol,
        source=f"archived:{item.provider}:{item.receipt_id}", feature_as_of=item.observed_at,
        observed_at=item.observed_at, retrieved_at=item.archived_at, data=core_data,
    )


def _option_packet(runtime: TrialRuntime, receipt: ArchiveReceipt, cutoff: datetime) -> Any:
    item = _require_receipt(receipt, "OPTION_CHAIN_INPUT", cutoff, timedelta(seconds=30))
    expected = {
        "symbol", "underlying_price", "bid", "ask", "open_interest", "volume", "expiration",
        "strike", "right", "trend_3bar_bps", "chain_complete", "chain_snapshot_hash", "selection_rule",
    }
    if set(item.payload) != expected:
        raise ReceiptError("option input is incomplete; the frozen selected-chain fields are required")
    data = item.payload
    symbol = data["symbol"]
    if symbol not in runtime.config["option_underlyings"]:
        raise ReceiptError("option underlying lies outside the frozen universe")
    if data["chain_complete"] is not True:
        raise ReceiptError("option-chain completeness is not proven")
    _validate_hash(data["chain_snapshot_hash"], "chain_snapshot_hash")
    if data["selection_rule"] != "frozen_nearest_atm_liquid_v1":
        raise ReceiptError("option selection rule differs from the frozen adapter")
    for field in ("underlying_price", "bid", "ask", "strike", "trend_3bar_bps"):
        decimal_string(data[field], field)
    for field in ("open_interest", "volume"):
        if type(data[field]) is not int or data[field] < 0:
            raise ReceiptError(f"{field} must be a nonnegative integer")
    try:
        date.fromisoformat(data["expiration"])
    except (TypeError, ValueError) as exc:
        raise ReceiptError("expiration must be YYYY-MM-DD") from exc
    if data["right"] not in {"CALL", "PUT"}:
        raise ReceiptError("right must be CALL or PUT")
    verify_frozen_bindings(Path(__file__).resolve().parents[2])
    from research.agentic_portfolio_v1.evidence import EvidencePacket
    from research.agentic_portfolio_v1.options import STRATEGY, VERSION
    core_fields = {
        "underlying_price", "bid", "ask", "open_interest", "volume", "expiration",
        "strike", "right", "trend_3bar_bps",
    }
    return EvidencePacket.build(
        kind="option_entry", strategy=STRATEGY, version=VERSION, symbol=symbol,
        source=f"archived:{item.provider}:{item.receipt_id}", feature_as_of=item.observed_at,
        observed_at=item.observed_at, retrieved_at=item.archived_at,
        data={key: data[key] for key in core_fields},
    )


def _stock_screen(packet: Any, decision_at: datetime) -> tuple[bool, tuple[str, ...]]:
    """Mirror the frozen technical filter without mutating a treatment ledger."""
    verify_frozen_bindings(Path(__file__).resolve().parents[2])
    from research.agentic_portfolio_v1.stock import StockSwingEngine
    data = StockSwingEngine._validate_features(packet, decision_at)
    px = Decimal(str(data["price"]))
    ask = Decimal(str(data["next_ask"]))
    limit_px = Decimal(str(data["entry_limit"]))
    atr = Decimal(str(data["atr14"]))
    session_return = Decimal(str(data["session_return"]))
    vwap = Decimal(str(data["session_vwap"]))
    sma50 = Decimal(str(data["sma50"]))
    volumes = [Decimal(str(value)) for value in data["dollar_volumes_20"]]
    failures: list[str] = []
    if px < Decimal("10"):
        failures.append("price below $10")
    if Decimal(str(statistics.median(volumes))) < Decimal("50000000"):
        failures.append("20-day median dollar volume below $50m")
    if px <= 0 or not Decimal("0.03") <= atr / px <= Decimal("0.10"):
        failures.append("ATR14/price outside 3%-10%")
    if not Decimal("-0.10") <= session_return <= Decimal("-0.02"):
        failures.append("session return outside -10% to -2%")
    if px < vwap:
        failures.append("close did not reclaim session VWAP")
    if px < sma50:
        failures.append("close below SMA50")
    if data["earnings_sessions_away"] <= 3:
        failures.append("earnings within three sessions")
    if ask <= 0 or limit_px <= 0 or ask > limit_px:
        failures.append("next executable ask is absent or above limit")
    return not failures, tuple(failures)


def _option_screen(packet: Any, decision_at: datetime) -> tuple[bool, tuple[str, ...]]:
    verify_frozen_bindings(Path(__file__).resolve().parents[2])
    from research.agentic_portfolio_v1.options import OptionShadowEngine
    data = OptionShadowEngine._validate(packet, decision_at)
    trend = Decimal(str(data["trend_3bar_bps"]))
    action = "CALL" if trend >= Decimal("30") else "PUT" if trend <= Decimal("-30") else "ABSTAIN"
    if action == "ABSTAIN":
        return False, ("deterministic three-bar baseline abstained",)
    if action != data["right"]:
        return False, ("signal and listed contract right conflict",)
    return True, ("frozen deterministic option candidate exists",)


def _source_rows(receipts: tuple[ArchiveReceipt | None, ...]) -> list[dict[str, Any]]:
    return [
        {
            "receipt_id": item.receipt_id, "kind": item.kind, "provider": item.provider,
            "observed_at": item.observed_at.isoformat(), "retrieved_at": item.retrieved_at.isoformat(),
            "archived_at": item.archived_at.isoformat(), "receipt_hash": item.receipt_hash,
        }
        for item in receipts if isinstance(item, ArchiveReceipt)
    ]


def _make_receipt(
    *, arm: str, account_id: str, strategy: str, strategy_version: str,
    cutoff: datetime, action: str, reasons: tuple[str, ...],
    source_receipts: tuple[ArchiveReceipt | None, ...], details: dict[str, Any] | None = None,
    macro_event_id: str | None = None,
) -> dict[str, Any]:
    if action not in {"PAPER_ENTRY_INTENT", "ABSTAIN", "BLOCKED_DATA"}:
        raise TrialError("unsupported forward-trial action")
    unsigned = {
        "schema_version": "1.0", "package_version": PACKAGE_VERSION,
        "mode": "PAPER_ONLY_NO_ORDER", "arm": arm, "virtual_account": account_id,
        "lifecycle": "ENTRY_GATE_ONLY_BLOCKED",
        "strategy": strategy, "strategy_version": strategy_version,
        "decision_at": aware_utc(cutoff, "decision_at").isoformat(), "action": action,
        "reasons": list(reasons), "source_receipts": _source_rows(source_receipts),
        "macro_event_id": macro_event_id,
        "details": json.loads(canonical_json(details or {})),
        "frozen_bindings": {
            "agentic_portfolio_v1_manifest_sha256": CORE_MANIFEST_SHA256,
            "agentic_portfolio_paper_10000_v1_manifest_sha256": PROFILE_MANIFEST_SHA256,
        },
        "paper_only": True, "no_order": True, "orders_enabled": False,
        "request_hash": None,
    }
    return {**unsigned, "receipt_hash": sha256_json(unsigned)}


def _bind_request(receipt: dict[str, Any], request_hash: str) -> dict[str, Any]:
    if not isinstance(request_hash, str) or not _HEX64.fullmatch(request_hash):
        raise TrialError("request hash must be SHA-256")
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if unsigned.get("request_hash") is not None:
        raise TrialError("decision receipt is already request-bound")
    unsigned["request_hash"] = request_hash
    return {**unsigned, "receipt_hash": sha256_json(unsigned)}


def _core_receipt(
    *, arm: str, decision: Any, cutoff: datetime,
    source_receipts: tuple[ArchiveReceipt | None, ...], context: ContextResult | None = None,
) -> dict[str, Any]:
    details = {
        "core_details": decision.details,
        "core_evidence_hash": decision.evidence_hash,
        "price_only_control_constants": (
            {"hard_adverse_news": False, "thesis_broken": False}
            if arm.startswith("price_") else {}
        ),
        "context_gate": (
            {"action": context.action, "reasons": list(context.reasons)} if context else None
        ),
    }
    return _make_receipt(
        arm=arm, account_id=decision.virtual_account, strategy=decision.strategy,
        strategy_version=decision.version, cutoff=cutoff, action=decision.action,
        reasons=tuple(decision.reasons), source_receipts=source_receipts,
        details=details, macro_event_id=getattr(context, "macro_event_id", None),
    )


def _fingerprint(receipt: ArchiveReceipt | None) -> Any:
    if receipt is None:
        return None
    if not isinstance(receipt, ArchiveReceipt):
        return {"invalid_type": type(receipt).__name__}
    return {"declared_hash": receipt.receipt_hash, "actual_object_hash": sha256_json(receipt.as_dict())}


def _request_hash(
    *, operation: str, arm: str, account_id: str, key: str, cutoff: datetime,
    receipts: tuple[ArchiveReceipt | None, ...],
) -> str:
    macro_hash = hashlib.sha256(Path(__file__).with_name("macro_calendar.json").read_bytes()).hexdigest()
    return sha256_json({
        "schema_version": "1.0", "package_version": PACKAGE_VERSION,
        "operation": operation, "arm": arm, "account_id": account_id,
        "idempotency_key": key, "decision_at": aware_utc(cutoff, "decision_at").isoformat(),
        "receipts": [_fingerprint(item) for item in receipts],
        "macro_calendar_sha256": macro_hash if arm.startswith("context_") else None,
    })


class ForwardTrialRunner:
    """Evaluates a control/treatment pair and emits only paper decision receipts."""

    def __init__(self, runtime: TrialRuntime):
        self.runtime = runtime

    def _admit(
        self, *, operation: str, key: str, cutoff: datetime,
        price_receipt: ArchiveReceipt | None, market_receipt: ArchiveReceipt | None,
        news_receipt: ArchiveReceipt | None, arm_names: tuple[str, str],
    ) -> tuple[dict[str, str], dict[str, tuple[str, dict[str, Any] | None]]]:
        if not isinstance(key, str) or not key.strip() or len(key) > 180:
            raise TrialError("idempotency_key must be bounded and non-empty")
        point = aware_utc(cutoff, "decision_at")
        hashes: dict[str, str] = {}
        requests: list[tuple[str, str, str]] = []
        for arm in arm_names:
            account_id = self.runtime.config["arms"][arm]["account_id"]
            inputs = ((price_receipt,) if arm.startswith("price_")
                      else (price_receipt, market_receipt, news_receipt))
            hashes[arm] = _request_hash(
                operation=operation, arm=arm, account_id=account_id, key=key,
                cutoff=point, receipts=inputs,
            )
            requests.append((account_id, key, hashes[arm]))
        return hashes, self.runtime.journal.begin_many(requests, point)

    def _finish(
        self, *, arm: str, key: str, request_hash: str, cutoff: datetime,
        state: tuple[str, dict[str, Any] | None], receipt: dict[str, Any] | None,
    ) -> RunOutcome:
        status, stored = state
        if status == "COMPLETE":
            assert stored is not None
            return RunOutcome(stored, True)
        if status == "PENDING":
            account_id = self.runtime.config["arms"][arm]["account_id"]
            blocked = _make_receipt(
                arm=arm, account_id=account_id, strategy="forward_trial_recovery",
                strategy_version=PACKAGE_VERSION, cutoff=cutoff, action="BLOCKED_DATA",
                reasons=("prior request is PENDING; inspect durable paper state before retry",),
                source_receipts=(), details={"pending_request_hash": request_hash},
            )
            return RunOutcome(blocked, True)
        if receipt is None:
            raise TrialError("new journal request lacks a result")
        account_id = self.runtime.config["arms"][arm]["account_id"]
        bound = _bind_request(receipt, request_hash)
        self.runtime.journal.complete(account_id, key, request_hash, bound, cutoff)
        return RunOutcome(bound, False)

    def evaluate_stock_pair(
        self, *, price_receipt: ArchiveReceipt | None, decision_at: datetime,
        idempotency_key: str, market_receipt: ArchiveReceipt | None = None,
        news_receipt: ArchiveReceipt | None = None,
    ) -> dict[str, RunOutcome]:
        point = aware_utc(decision_at, "decision_at")
        arms = ("price_stock", "context_stock")
        hashes, admitted = self._admit(
            operation="STOCK_ENTRY", key=idempotency_key, cutoff=point,
            price_receipt=price_receipt, market_receipt=market_receipt,
            news_receipt=news_receipt, arm_names=arms,
        )
        computed: dict[str, dict[str, Any]] = {}
        packet: Any = None
        input_error: str | None = None
        try:
            packet = _stock_packet(self.runtime, price_receipt, point)  # type: ignore[arg-type]
            candidate, screen_reasons = _stock_screen(packet, point)
        except (ReceiptError, BindingError, TrialError, TypeError, ValueError, KeyError, ArithmeticError) as exc:
            candidate, screen_reasons, input_error = False, (), str(exc)
        for arm in arms:
            if admitted[self.runtime.config["arms"][arm]["account_id"]][0] != "NEW":
                continue
            account_id = self.runtime.config["arms"][arm]["account_id"]
            sources = ((price_receipt,) if arm == "price_stock"
                       else (price_receipt, market_receipt, news_receipt))
            if input_error is not None:
                computed[arm] = _make_receipt(
                    arm=arm, account_id=account_id, strategy="stock_swing_net10_v1",
                    strategy_version="1.0.0", cutoff=point, action="BLOCKED_DATA",
                    reasons=(f"required stock input unavailable: {input_error}",),
                    source_receipts=sources,
                )
            elif arm == "price_stock":
                decision = self.runtime.engines[arm].evaluate_entry(
                    packet, point, f"forward:{arm}:{idempotency_key}",
                )
                computed[arm] = _core_receipt(
                    arm=arm, decision=decision, cutoff=point, source_receipts=sources,
                )
            elif not candidate:
                computed[arm] = _make_receipt(
                    arm=arm, account_id=account_id, strategy="stock_swing_net10_v1",
                    strategy_version="1.0.0", cutoff=point, action="ABSTAIN",
                    reasons=("context cannot originate a trade", *screen_reasons),
                    source_receipts=sources,
                )
            else:
                gate = evaluate_context(
                    baseline_action="PAPER_ENTRY_INTENT", target_symbol=packet.symbol,
                    cutoff=point, market_receipt=market_receipt, news_receipt=news_receipt,
                )
                if gate.action == "ALLOW_EXISTING_CANDIDATE":
                    decision = self.runtime.engines[arm].evaluate_entry(
                        packet, point, f"forward:{arm}:{idempotency_key}",
                    )
                    computed[arm] = _core_receipt(
                        arm=arm, decision=decision, cutoff=point, source_receipts=sources, context=gate,
                    )
                else:
                    computed[arm] = _make_receipt(
                        arm=arm, account_id=account_id, strategy="stock_swing_net10_v1",
                        strategy_version="1.0.0", cutoff=point, action=gate.action,
                        reasons=gate.reasons, source_receipts=sources,
                        details={"context_gate": {"action": gate.action, "reasons": list(gate.reasons)}},
                        macro_event_id=gate.macro_event_id,
                    )
        return {
            arm: self._finish(
                arm=arm, key=idempotency_key, request_hash=hashes[arm], cutoff=point,
                state=admitted[self.runtime.config["arms"][arm]["account_id"]],
                receipt=computed.get(arm),
            ) for arm in arms
        }

    def evaluate_option_pair(
        self, *, chain_receipt: ArchiveReceipt | None, decision_at: datetime,
        idempotency_key: str, market_receipt: ArchiveReceipt | None = None,
        news_receipt: ArchiveReceipt | None = None,
    ) -> dict[str, RunOutcome]:
        point = aware_utc(decision_at, "decision_at")
        arms = ("price_options", "context_options")
        hashes, admitted = self._admit(
            operation="OPTION_ENTRY", key=idempotency_key, cutoff=point,
            price_receipt=chain_receipt, market_receipt=market_receipt,
            news_receipt=news_receipt, arm_names=arms,
        )
        computed: dict[str, dict[str, Any]] = {}
        packet: Any = None
        input_error: str | None = None
        try:
            packet = _option_packet(self.runtime, chain_receipt, point)  # type: ignore[arg-type]
            candidate, screen_reasons = _option_screen(packet, point)
        except (ReceiptError, BindingError, TrialError, TypeError, ValueError, KeyError, ArithmeticError) as exc:
            candidate, screen_reasons, input_error = False, (), str(exc)
        for arm in arms:
            if admitted[self.runtime.config["arms"][arm]["account_id"]][0] != "NEW":
                continue
            account_id = self.runtime.config["arms"][arm]["account_id"]
            sources = ((chain_receipt,) if arm == "price_options"
                       else (chain_receipt, market_receipt, news_receipt))
            if input_error is not None:
                computed[arm] = _make_receipt(
                    arm=arm, account_id=account_id, strategy="long_option_shadow_v2",
                    strategy_version="2.0.0", cutoff=point, action="BLOCKED_DATA",
                    reasons=(f"required option-chain input unavailable: {input_error}",),
                    source_receipts=sources,
                )
            elif arm == "price_options":
                decision = self.runtime.engines[arm].evaluate_entry(
                    packet, point, f"forward:{arm}:{idempotency_key}",
                )
                computed[arm] = _core_receipt(
                    arm=arm, decision=decision, cutoff=point, source_receipts=sources,
                )
            elif not candidate:
                computed[arm] = _make_receipt(
                    arm=arm, account_id=account_id, strategy="long_option_shadow_v2",
                    strategy_version="2.0.0", cutoff=point, action="ABSTAIN",
                    reasons=("context cannot originate a trade", *screen_reasons),
                    source_receipts=sources,
                )
            else:
                gate = evaluate_context(
                    baseline_action="PAPER_ENTRY_INTENT", target_symbol=packet.symbol,
                    cutoff=point, market_receipt=market_receipt, news_receipt=news_receipt,
                )
                if gate.action == "ALLOW_EXISTING_CANDIDATE":
                    decision = self.runtime.engines[arm].evaluate_entry(
                        packet, point, f"forward:{arm}:{idempotency_key}",
                    )
                    computed[arm] = _core_receipt(
                        arm=arm, decision=decision, cutoff=point, source_receipts=sources, context=gate,
                    )
                else:
                    computed[arm] = _make_receipt(
                        arm=arm, account_id=account_id, strategy="long_option_shadow_v2",
                        strategy_version="2.0.0", cutoff=point, action=gate.action,
                        reasons=gate.reasons, source_receipts=sources,
                        details={"context_gate": {"action": gate.action, "reasons": list(gate.reasons)}},
                        macro_event_id=gate.macro_event_id,
                    )
        return {
            arm: self._finish(
                arm=arm, key=idempotency_key, request_hash=hashes[arm], cutoff=point,
                state=admitted[self.runtime.config["arms"][arm]["account_id"]],
                receipt=computed.get(arm),
            ) for arm in arms
        }
