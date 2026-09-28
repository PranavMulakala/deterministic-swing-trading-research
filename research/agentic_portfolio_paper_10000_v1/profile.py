"""Strict, offline profile around the frozen agentic_portfolio_v1 engines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
from typing import Any
from zoneinfo import ZoneInfo

from . import (
    BROKER_ENABLED,
    DEPLOY_ENABLED,
    MODEL_CALLS_ENABLED,
    NETWORK_ENABLED,
    ORDERS_ENABLED,
)


ROOT = Path(__file__).resolve().parent
CORE_ROOT = ROOT.parent / "agentic_portfolio_v1"
CORE_FREEZE_SHA256 = "e6d3961f98830ef46850f194ae77f7486714faac685bd6acd77a8a496ecf488d"
SCHEDULED_SESSION_DATES = (
    "2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18",
    "2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24",
    "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30",
    "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06",
    "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12",
    "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16",
    "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22",
    "2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28",
    "2026-10-29", "2026-10-30",
)
REQUIRED_LEDGER_COLUMNS = {
    "accounts": {
        "account_id", "initial_cash_cents", "policy_hash", "cash_cents", "high_water_cents",
        "realized_pnl_cents", "daily_loss_date", "daily_loss_cents", "kill_switch",
        "integrity_latched", "integrity_reason", "last_account_time", "last_trading_date",
    },
    "marks": {"account_id", "symbol", "price", "observed_at"},
    "positions": {
        "account_id", "strategy", "strategy_version", "symbol", "asset_type", "quantity",
        "basis_cents", "multiplier", "contractual_loss_cents", "opened_at", "reservation_id",
    },
    "reservations": {
        "account_id", "reservation_id", "idempotency_key", "strategy", "strategy_version",
        "symbol", "asset_type", "reserved_quantity", "notional_cents",
        "contractual_loss_cents", "remaining_cents", "created_at", "expires_at", "status",
        "evidence_hash", "policy_hash", "request_hash", "payload_hash",
    },
    "intent_days": {"account_id", "strategy", "intent_date", "reservation_id"},
    "cash_events": {
        "account_id", "event_seq", "external_event_id", "delta_cents", "kind", "created_at",
    },
    "fill_events": {
        "account_id", "event_id", "payload_hash", "payload_json", "receipt_json",
        "reservation_id", "strategy", "symbol", "asset_type", "quantity", "basis_delta_cents",
        "contractual_loss_delta_cents", "reservation_consumed_cents", "multiplier", "filled_at",
    },
    "close_events": {
        "account_id", "event_id", "payload_hash", "payload_json", "receipt_json", "strategy",
        "symbol", "asset_type", "quantity", "basis_delta_cents", "contractual_loss_delta_cents",
        "proceeds_cents", "realized_pnl_cents", "closed_at",
    },
    "reservation_events": {
        "account_id", "event_id", "payload_hash", "payload_json", "receipt_json",
        "reservation_id", "event_type", "occurred_at",
    },
    "journal_events": {"event_seq", "account_id", "event_kind", "event_id", "occurred_at"},
}


class ProfileValidationError(ValueError):
    """The fixed profile, freeze binding, or review input is invalid."""


def _exact_keys(value: Any, expected: set[str], field: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ProfileValidationError(f"{field} must be an object")
    if set(value) != expected:
        raise ProfileValidationError(f"{field} fields do not match the frozen schema")
    return value


def _literal(value: Any, expected: Any, field: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise ProfileValidationError(f"{field} must remain {expected!r}")


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProfileValidationError(f"{field} must be a nonnegative integer")
    return value


def _real_directory(path: Path) -> None:
    """Create a missing state root, then reject links and non-directories."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            pass
        except OSError as exc:
            raise ProfileValidationError("state_root could not be created") from exc
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise ProfileValidationError("state_root changed while it was created") from exc
    except OSError as exc:
        raise ProfileValidationError("state_root could not be inspected") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ProfileValidationError("state_root must be a real directory")


def _ledger_identity(path: Path) -> tuple[int, int] | None:
    """Return a regular file's device/inode without following a symlink."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ProfileValidationError(f"ledger path could not be inspected: {path.name}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ProfileValidationError(f"ledger path must be a regular non-symlink file: {path.name}")
    return metadata.st_dev, metadata.st_ino


def _ledger_snapshot(paths: dict[str, Path]) -> dict[str, tuple[int, int] | None]:
    return {name: _ledger_identity(path) for name, path in paths.items()}


def _require_distinct_ledgers(snapshot: dict[str, tuple[int, int] | None]) -> None:
    identities = [identity for identity in snapshot.values() if identity is not None]
    if len(identities) != len(set(identities)):
        raise ProfileValidationError("stock and option ledgers must not share an inode or hardlink")


def _require_identities_unchanged(
    expected: dict[str, tuple[int, int]], current: dict[str, tuple[int, int] | None],
) -> None:
    for name, identity in expected.items():
        if current[name] != identity:
            raise ProfileValidationError(f"ledger path changed during initialization: {name}")


def _create_empty_ledger_file(path: Path) -> tuple[int, int]:
    """Claim a missing ledger name exclusively and without following a symlink."""
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise ProfileValidationError(f"ledger path appeared during initialization: {path.name}") from exc
    except OSError as exc:
        raise ProfileValidationError(f"ledger path could not be created safely: {path.name}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ProfileValidationError(f"created ledger path is not a regular file: {path.name}")
        return metadata.st_dev, metadata.st_ino
    finally:
        os.close(descriptor)


def _content_signature(path: Path) -> tuple[int, int, int, int, str]:
    """Hash one regular file through a no-follow descriptor without writing it."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ProfileValidationError(f"ledger file could not be opened read-only: {path.name}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ProfileValidationError(f"ledger path must be a regular non-symlink file: {path.name}")
        digest = hashlib.sha256()
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            digest.update(block)
        after = os.fstat(descriptor)
        before_signature = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        after_signature = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if after_signature != before_signature:
            raise ProfileValidationError(f"ledger changed while it was read: {path.name}")
        return (*after_signature, digest.hexdigest())
    finally:
        os.close(descriptor)


def _require_no_sqlite_sidecars(path: Path) -> None:
    for suffix in ("-journal", "-shm", "-wal"):
        sidecar = path.parent / f"{path.name}{suffix}"
        try:
            sidecar.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ProfileValidationError(f"SQLite sidecar could not be inspected: {sidecar.name}") from exc
        raise ProfileValidationError(f"existing ledger has an unresolved SQLite sidecar: {sidecar.name}")


def _core_policy_hash(RiskLedger: type[Any], policy: Any) -> str:
    probe = object.__new__(RiskLedger)
    probe.policy = policy
    identity = RiskLedger._policy_identity(probe)
    encoded = json.dumps(
        identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_account_clock(account: sqlite3.Row, path: Path) -> None:
    for field in ("initial_cash_cents", "cash_cents", "high_water_cents", "realized_pnl_cents", "daily_loss_cents"):
        if isinstance(account[field], bool) or not isinstance(account[field], int):
            raise ProfileValidationError(f"existing ledger account.{field} must be an integer: {path.name}")
    if account["cash_cents"] < 0 or account["high_water_cents"] < 0 or account["daily_loss_cents"] < 0:
        raise ProfileValidationError(f"existing ledger contains a negative account balance: {path.name}")
    if account["kill_switch"] not in (0, 1) or account["integrity_latched"] not in (0, 1):
        raise ProfileValidationError(f"existing ledger contains an invalid account flag: {path.name}")
    if account["integrity_latched"] != 0 or account["integrity_reason"] is not None:
        raise ProfileValidationError(f"existing ledger has a durable integrity latch: {path.name}")
    for field in ("daily_loss_date", "last_trading_date"):
        if account[field] is not None:
            try:
                date.fromisoformat(account[field])
            except (TypeError, ValueError) as exc:
                raise ProfileValidationError(f"existing ledger account.{field} is invalid: {path.name}") from exc
    last_time = account["last_account_time"]
    if last_time is not None:
        try:
            parsed = datetime.fromisoformat(last_time)
        except (TypeError, ValueError) as exc:
            raise ProfileValidationError(f"existing ledger last_account_time is invalid: {path.name}") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ProfileValidationError(f"existing ledger last_account_time is timezone-naive: {path.name}")
        if account["last_trading_date"] != parsed.astimezone(ZoneInfo("UTC")).date().isoformat():
            raise ProfileValidationError(f"existing ledger account clock fields conflict: {path.name}")


def _preflight_existing_ledger(
    path: Path, *, expected_account_id: str, expected_policy_hash: str,
    RiskLedger: type[Any], policy: Any,
) -> str:
    """Read-only preflight; never invoke RiskLedger.__init__ or create sidecars."""
    identity = _ledger_identity(path)
    if identity is None:
        return "ABSENT"
    _require_no_sqlite_sidecars(path)
    before = _content_signature(path)
    if before[2] == 0:
        _require_no_sqlite_sidecars(path)
        if _content_signature(path) != before:
            raise ProfileValidationError(f"empty ledger changed during preflight: {path.name}")
        return "EMPTY"

    connection: sqlite3.Connection | None = None
    failure: ProfileValidationError | None = None
    try:
        uri = path.absolute().as_uri() + "?mode=ro&immutable=1"
        connection = sqlite3.connect(uri, uri=True, timeout=1, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        if connection.execute("PRAGMA query_only").fetchone()[0] != 1:
            raise ProfileValidationError(f"existing ledger did not enter query-only mode: {path.name}")
        if connection.execute("PRAGMA user_version").fetchone()[0] != 0:
            raise ProfileValidationError(f"existing ledger user_version is not the core v1 value: {path.name}")
        integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            raise ProfileValidationError(f"existing ledger failed SQLite integrity_check: {path.name}")
        actual_tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if actual_tables != set(REQUIRED_LEDGER_COLUMNS):
            raise ProfileValidationError(f"existing ledger table set differs from core v1: {path.name}")
        for table, expected_columns in REQUIRED_LEDGER_COLUMNS.items():
            actual_columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
            if actual_columns != expected_columns:
                raise ProfileValidationError(f"existing ledger columns differ for {table}: {path.name}")
        accounts = list(connection.execute("SELECT * FROM accounts"))
        if len(accounts) != 1 or accounts[0]["account_id"] != expected_account_id:
            raise ProfileValidationError(f"existing ledger account identity differs: {path.name}")
        account = accounts[0]
        if account["initial_cash_cents"] != 1_000_000:
            raise ProfileValidationError(f"existing ledger initial cash is not 1000000 cents: {path.name}")
        if account["policy_hash"] != expected_policy_hash:
            raise ProfileValidationError(f"existing ledger core policy hash differs: {path.name}")
        _validate_account_clock(account, path)
        for table in REQUIRED_LEDGER_COLUMNS:
            account_ids = {row[0] for row in connection.execute(f"SELECT DISTINCT account_id FROM {table}")}
            if account_ids - {expected_account_id}:
                raise ProfileValidationError(f"existing ledger contains a foreign account in {table}: {path.name}")

        # Reuse the exact core chronological reconciliation code without invoking
        # the constructor that configures WAL and starts a write transaction.
        probe = object.__new__(RiskLedger)
        probe.account_id = expected_account_id
        probe.policy = policy
        probe._policy_hash = expected_policy_hash
        reconciliation_errors = RiskLedger._reconciliation_errors(probe, connection)
        if reconciliation_errors:
            raise ProfileValidationError(
                f"existing ledger core reconciliation failed: {path.name}: "
                + "; ".join(reconciliation_errors)
            )
    except ProfileValidationError as exc:
        failure = exc
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        failure = ProfileValidationError(f"existing ledger is not a compatible core v1 database: {path.name}")
        failure.__cause__ = exc
    finally:
        if connection is not None:
            connection.close()

    _require_no_sqlite_sidecars(path)
    after = _content_signature(path)
    if after != before:
        raise ProfileValidationError(f"existing ledger changed during read-only preflight: {path.name}")
    if failure is not None:
        raise failure
    return "COMPATIBLE"


def verify_core_binding(core_root: Path = CORE_ROOT) -> str:
    """Verify the exact bound core manifest and every file before importing it."""
    root = Path(core_root)
    freeze_path = root / "FREEZE.json"
    if freeze_path.is_symlink() or not freeze_path.is_file():
        raise ProfileValidationError("bound core FREEZE.json is missing or is a symlink")
    raw = freeze_path.read_bytes()
    actual_freeze_hash = hashlib.sha256(raw).hexdigest()
    if actual_freeze_hash != CORE_FREEZE_SHA256:
        raise ProfileValidationError("bound core FREEZE.json SHA-256 differs from the pinned value")
    try:
        manifest = json.loads(raw)
        _exact_keys(
            manifest,
            {"schema_version", "package_version", "frozen_at", "change_policy", "hash_algorithm", "files"},
            "core manifest",
        )
        _literal(manifest["schema_version"], "1.0", "core manifest.schema_version")
        _literal(manifest["package_version"], "agentic_portfolio_v1", "core manifest.package_version")
        _literal(manifest["hash_algorithm"], "sha256", "core manifest.hash_algorithm")
        files = manifest["files"]
        if type(files) is not dict or not files:
            raise ProfileValidationError("core manifest.files must be a non-empty object")
        if not all(
            isinstance(name, str) and Path(name).name == name
            and isinstance(digest, str) and len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest)
            for name, digest in files.items()
        ):
            raise ProfileValidationError("core manifest contains an invalid file entry")
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ProfileValidationError("bound core manifest is invalid") from exc

    actual_runtime = {
        path.name for path in root.iterdir()
        if path.is_file() and path.name != "FREEZE.json" and not path.name.startswith("test_")
    }
    if actual_runtime != set(files):
        raise ProfileValidationError("bound core runtime file set differs from its manifest")
    for name, expected_hash in sorted(files.items()):
        target = root / name
        if target.is_symlink() or not target.is_file():
            raise ProfileValidationError(f"bound core file is missing or is a symlink: {name}")
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected_hash:
            raise ProfileValidationError(f"bound core manifest hash differs for {name}")
    return actual_freeze_hash


def _validate_config(raw: Any) -> dict[str, Any]:
    config = _exact_keys(
        raw,
        {
            "schema_version", "profile", "mode", "capabilities", "core_binding",
            "virtual_accounts", "risk_policy", "trial", "news_external_factors",
        },
        "config",
    )
    for field, expected in (
        ("schema_version", "1.0"),
        ("profile", "agentic_portfolio_paper_10000_v1"),
        ("mode", "PAPER_ONLY_NO_ORDER"),
    ):
        _literal(config[field], expected, field)

    capabilities = _exact_keys(
        config["capabilities"],
        {"orders_enabled", "model_calls_enabled", "network_enabled", "broker_enabled", "deploy_enabled"},
        "capabilities",
    )
    constants = {
        "orders_enabled": ORDERS_ENABLED,
        "model_calls_enabled": MODEL_CALLS_ENABLED,
        "network_enabled": NETWORK_ENABLED,
        "broker_enabled": BROKER_ENABLED,
        "deploy_enabled": DEPLOY_ENABLED,
    }
    for field, constant in constants.items():
        _literal(capabilities[field], False, f"capabilities.{field}")
        if constant is not False:
            raise ProfileValidationError(f"immutable capability constant is not false: {field}")

    binding = _exact_keys(
        config["core_binding"],
        {"package", "freeze_sha256", "manifest_verification_required"},
        "core_binding",
    )
    _literal(binding["package"], "research.agentic_portfolio_v1", "core_binding.package")
    _literal(binding["freeze_sha256"], CORE_FREEZE_SHA256, "core_binding.freeze_sha256")
    _literal(binding["manifest_verification_required"], True, "core_binding.manifest_verification_required")

    accounts = _exact_keys(
        config["virtual_accounts"],
        {"stock_swing", "long_options", "total_simulated_bookkeeping", "shared_pool"},
        "virtual_accounts",
    )
    account_literals = {
        "stock_swing": {
            "account_id": "paper-10000-stock-swing-v1", "initial_cash": "10000.00",
            "ledger": "separate", "engine": "StockSwingEngine",
        },
        "long_options": {
            "account_id": "paper-10000-long-options-v1", "initial_cash": "10000.00",
            "ledger": "separate", "engine": "OptionShadowEngine",
        },
    }
    for account_name, expected in account_literals.items():
        account = _exact_keys(accounts[account_name], set(expected), f"virtual_accounts.{account_name}")
        for field, value in expected.items():
            _literal(account[field], value, f"virtual_accounts.{account_name}.{field}")
    _literal(accounts["total_simulated_bookkeeping"], "20000.00", "virtual_accounts.total_simulated_bookkeeping")
    _literal(accounts["shared_pool"], False, "virtual_accounts.shared_pool")

    risk = _exact_keys(
        config["risk_policy"],
        {
            "source", "max_equity_position", "max_total_deployed", "min_cash_reserve",
            "max_total_option_contractual_loss", "daily_realized_loss_pause",
            "high_water_drawdown_pause",
        },
        "risk_policy",
    )
    expected_risk = {
        "source": "research.agentic_portfolio_v1.risk.RiskPolicy",
        "max_equity_position": "0.20", "max_total_deployed": "0.50",
        "min_cash_reserve": "0.50", "max_total_option_contractual_loss": "0.05",
        "daily_realized_loss_pause": "0.02", "high_water_drawdown_pause": "0.05",
    }
    for field, value in expected_risk.items():
        _literal(risk[field], value, f"risk_policy.{field}")

    trial = _exact_keys(
        config["trial"],
        {
            "timezone", "start_date", "first_checkpoint_at", "scheduled_final_review_at",
            "scheduled_nyse_sessions", "minimum_completed_eligible_market_sessions",
            "minimum_closed_trades_per_strategy", "scheduled_session_dates", "calendar_source",
            "calendar_source_url", "actual_session_completeness_must_be_verified",
            "review_is_proof_or_promotion",
        },
        "trial",
    )
    trial_literals = {
        "timezone": "America/New_York",
        "start_date": "2026-09-15",
        "first_checkpoint_at": "2026-10-26T16:30:00-04:00",
        "scheduled_final_review_at": "2026-10-30T16:30:00-04:00",
        "scheduled_nyse_sessions": 34,
        "minimum_completed_eligible_market_sessions": 30,
        "minimum_closed_trades_per_strategy": 20,
        "calendar_source": "NYSE published 2026 holidays and trading hours",
        "calendar_source_url": "https://www.nyse.com/markets/hours-calendars",
        "actual_session_completeness_must_be_verified": True,
        "review_is_proof_or_promotion": False,
    }
    for field, value in trial_literals.items():
        _literal(trial[field], value, f"trial.{field}")
    if type(trial["scheduled_session_dates"]) is not list or tuple(trial["scheduled_session_dates"]) != SCHEDULED_SESSION_DATES:
        raise ProfileValidationError("trial.scheduled_session_dates differs from the frozen calendar declaration")
    parsed_dates = tuple(date.fromisoformat(value) for value in trial["scheduled_session_dates"])
    if len(parsed_dates) != 34 or parsed_dates[29] != date(2026, 10, 26):
        raise ProfileValidationError("trial calendar must contain 34 dates with session 30 on 2026-10-26")

    news = _exact_keys(
        config["news_external_factors"],
        {
            "collector_records_direct_news_metadata", "collector_records_sector_news_metadata",
            "collector_performs_sentiment_scoring", "engines_consume_collector_news_metadata",
            "stock_engine_consumes_supplied_hard_adverse_news_boolean",
            "options_engine_consumes_news_or_sentiment", "comprehensive_news_integration",
            "fundamentals_integration", "analyst_ratings_integration", "macro_interpretation",
            "sentiment_integration",
        },
        "news_external_factors",
    )
    expected_news = {
        "collector_records_direct_news_metadata": True,
        "collector_records_sector_news_metadata": True,
        "collector_performs_sentiment_scoring": False,
        "engines_consume_collector_news_metadata": False,
        "stock_engine_consumes_supplied_hard_adverse_news_boolean": True,
        "options_engine_consumes_news_or_sentiment": False,
        "comprehensive_news_integration": False,
        "fundamentals_integration": False,
        "analyst_ratings_integration": False,
        "macro_interpretation": False,
        "sentiment_integration": False,
    }
    for field, value in expected_news.items():
        _literal(news[field], value, f"news_external_factors.{field}")
    return config


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load only the exact frozen profile after verifying both freeze boundaries."""
    from .freeze import verify as verify_profile_freeze

    profile_errors = verify_profile_freeze()
    if profile_errors:
        raise ProfileValidationError("profile freeze verification failed: " + ", ".join(profile_errors))
    verify_core_binding()
    target = Path(path) if path is not None else ROOT / "config.json"
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProfileValidationError("profile config is unreadable or invalid JSON") from exc
    return _validate_config(raw)


def _load_core_types() -> tuple[type[Any], type[Any], type[Any], type[Any]]:
    """Import executable core classes only after exact independent verification."""
    verify_core_binding()
    from research.agentic_portfolio_v1.options import OptionShadowEngine
    from research.agentic_portfolio_v1.risk import RiskLedger, RiskPolicy
    from research.agentic_portfolio_v1.stock import StockSwingEngine

    return RiskLedger, RiskPolicy, StockSwingEngine, OptionShadowEngine


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def derived_dollar_limits() -> dict[str, str]:
    """Derive dollar limits from the imported shared policy and $10,000 base."""
    config = load_config()
    _, RiskPolicy, _, _ = _load_core_types()
    policy = RiskPolicy()
    expected = config["risk_policy"]
    actual = {
        "max_equity_position": str(policy.max_equity_position),
        "max_total_deployed": str(policy.max_total_deployed),
        "min_cash_reserve": str(policy.min_cash_reserve),
        "max_total_option_contractual_loss": str(policy.max_total_option_loss),
        "daily_realized_loss_pause": str(policy.daily_realized_loss_pause),
        "high_water_drawdown_pause": str(policy.high_water_drawdown_pause),
    }
    for field, value in actual.items():
        if value != expected[field]:
            raise ProfileValidationError(f"imported core risk policy differs for {field}")
    initial = Decimal(config["virtual_accounts"]["stock_swing"]["initial_cash"])
    return {
        "max_stock_position": _money(initial * policy.max_equity_position),
        "max_total_deployed": _money(initial * policy.max_total_deployed),
        "minimum_cash_reserve": _money(initial * policy.min_cash_reserve),
        "max_option_contractual_loss": _money(initial * policy.max_total_option_loss),
        "daily_realized_loss_halt": _money(initial * policy.daily_realized_loss_pause),
        "high_water_drawdown_halt": _money(initial * policy.high_water_drawdown_pause),
    }


@dataclass(frozen=True)
class TrialRuntime:
    stock_ledger: Any
    options_ledger: Any
    stock_engine: Any
    options_engine: Any
    stock_ledger_path: Path
    options_ledger_path: Path


def build_trial(state_root: Path) -> TrialRuntime:
    """Instantiate two physically and financially isolated simulated accounts."""
    config = load_config()
    root = Path(state_root)
    _real_directory(root)
    paths = {
        "stock_swing": root / "stock_swing.sqlite",
        "long_options": root / "long_options.sqlite",
    }

    # Inspect both names before opening either database. In particular, reject a
    # pre-existing hardlink alias without letting SQLite modify either inode.
    initial = _ledger_snapshot(paths)
    _require_distinct_ledgers(initial)
    expected_identities = {
        name: identity for name, identity in initial.items() if identity is not None
    }

    RiskLedger, RiskPolicy, StockSwingEngine, OptionShadowEngine = _load_core_types()
    accounts = config["virtual_accounts"]
    policy = RiskPolicy()
    expected_policy_hash = _core_policy_hash(RiskLedger, policy)
    preflight_results = {}
    for name in ("stock_swing", "long_options"):
        account = accounts[name]
        preflight_results[name] = _preflight_existing_ledger(
            paths[name], expected_account_id=account["account_id"],
            expected_policy_hash=expected_policy_hash, RiskLedger=RiskLedger, policy=policy,
        )
    after_preflight = _ledger_snapshot(paths)
    _require_distinct_ledgers(after_preflight)
    _require_identities_unchanged(expected_identities, after_preflight)
    ledgers: dict[str, Any] = {}

    def construct(name: str) -> Any:
        account = accounts[name]
        return RiskLedger(
            str(paths[name]), account["account_id"], Decimal(account["initial_cash"]), policy,
        )

    # Both sides passed the non-mutating preflight. Constructors may now validate
    # compatible databases or initialize accepted zero-byte placeholders.
    for name in ("stock_swing", "long_options"):
        if initial[name] is None:
            continue
        before = _ledger_snapshot(paths)
        _require_distinct_ledgers(before)
        _require_identities_unchanged(expected_identities, before)
        ledgers[name] = construct(name)
        after = _ledger_snapshot(paths)
        _require_distinct_ledgers(after)
        _require_identities_unchanged(expected_identities, after)

    # Exclusively claim missing names before SQLite opens them. Recheck all
    # device/inode identities around each step to fail closed on path replacement.
    for name in ("stock_swing", "long_options"):
        if initial[name] is not None:
            continue
        before = _ledger_snapshot(paths)
        _require_distinct_ledgers(before)
        _require_identities_unchanged(expected_identities, before)
        if before[name] is not None:
            raise ProfileValidationError(f"ledger path appeared during initialization: {name}")
        identity = _create_empty_ledger_file(paths[name])
        expected_identities[name] = identity
        after = _ledger_snapshot(paths)
        _require_distinct_ledgers(after)
        _require_identities_unchanged(expected_identities, after)

    for name in ("stock_swing", "long_options"):
        if name in ledgers:
            continue
        before = _ledger_snapshot(paths)
        _require_distinct_ledgers(before)
        _require_identities_unchanged(expected_identities, before)
        ledgers[name] = construct(name)
        after = _ledger_snapshot(paths)
        _require_distinct_ledgers(after)
        _require_identities_unchanged(expected_identities, after)

    stock_ledger = ledgers["stock_swing"]
    options_ledger = ledgers["long_options"]
    return TrialRuntime(
        stock_ledger=stock_ledger,
        options_ledger=options_ledger,
        stock_engine=StockSwingEngine(stock_ledger),
        options_engine=OptionShadowEngine(options_ledger, mode="baseline"),
        stock_ledger_path=paths["stock_swing"],
        options_ledger_path=paths["long_options"],
    )


def maximum_elapsed_scheduled_sessions(as_of: datetime) -> int:
    """Count listed sessions whose 16:00 New York close is strictly before as_of."""
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ProfileValidationError("as_of must be a timezone-aware datetime")
    local_as_of = as_of.astimezone(ZoneInfo("America/New_York"))
    completed = 0
    for value in SCHEDULED_SESSION_DATES:
        session_date = date.fromisoformat(value)
        scheduled_close = datetime.combine(
            session_date, time(16, 0), tzinfo=ZoneInfo("America/New_York"),
        )
        if local_as_of > scheduled_close:
            completed += 1
    return completed


def review_assessment(
    *, completed_eligible_market_sessions: int, stock_closed_trades: int,
    options_closed_trades: int, actual_session_completeness_verified: bool,
    as_of: datetime,
) -> dict[str, Any]:
    """Apply evidence gates; eligibility is never profitability proof or promotion."""
    config = load_config()
    trial = config["trial"]
    completed = _nonnegative_int(completed_eligible_market_sessions, "completed_eligible_market_sessions")
    stock_trades = _nonnegative_int(stock_closed_trades, "stock_closed_trades")
    option_trades = _nonnegative_int(options_closed_trades, "options_closed_trades")
    if type(actual_session_completeness_verified) is not bool:
        raise ProfileValidationError("actual_session_completeness_verified must be boolean")
    maximum_elapsed = maximum_elapsed_scheduled_sessions(as_of)
    local_as_of = as_of.astimezone(ZoneInfo(trial["timezone"]))
    if completed > trial["scheduled_nyse_sessions"]:
        raise ProfileValidationError("completed eligible market sessions exceed the 34-session trial calendar")
    if completed > maximum_elapsed:
        raise ProfileValidationError(
            "completed eligible market sessions exceed the maximum scheduled sessions elapsed as of the supplied time"
        )
    checkpoint = datetime.fromisoformat(trial["first_checkpoint_at"])
    final_review = datetime.fromisoformat(trial["scheduled_final_review_at"])
    session_gate = actual_session_completeness_verified and completed >= trial["minimum_completed_eligible_market_sessions"]
    stock_gate = stock_trades >= trial["minimum_closed_trades_per_strategy"]
    option_gate = option_trades >= trial["minimum_closed_trades_per_strategy"]
    evidence_gate = session_gate and stock_gate and option_gate
    if local_as_of < checkpoint:
        status = "CONTINUE_PAPER_TRIAL_BEFORE_FIRST_CHECKPOINT"
    elif local_as_of < final_review:
        status = "ELIGIBLE_FOR_INITIAL_REVIEW_NOT_PROOF" if evidence_gate else "CONTINUE_PAPER_TRIAL_INCOMPLETE_EVIDENCE"
    else:
        status = "ELIGIBLE_FOR_SCHEDULED_FINAL_REVIEW_NOT_PROOF" if evidence_gate else "CONTINUE_PAPER_TRIAL_INCOMPLETE_EVIDENCE"
    return {
        "status": status,
        "as_of_new_york": local_as_of.isoformat(),
        "completed_eligible_market_sessions": completed,
        "maximum_elapsed_scheduled_sessions": maximum_elapsed,
        "elapsed_session_semantics": (
            "a listed session counts only when as_of is strictly after 16:00 America/New_York; "
            "at or before scheduled close the current date does not count"
        ),
        "actual_session_completeness_verified": actual_session_completeness_verified,
        "stock_closed_trades": stock_trades,
        "options_closed_trades": option_trades,
        "session_gate_met": session_gate,
        "stock_trade_gate_met": stock_gate,
        "options_trade_gate_met": option_gate,
        "all_initial_review_evidence_gates_met": evidence_gate,
        "proof_of_profitability": False,
        "promotion_or_live_readiness": False,
    }


def offline_summary(state_root: Path, *, as_of: datetime) -> dict[str, Any]:
    """Create the temporary ledgers and report the fixed paper-trial boundary."""
    config = load_config()
    runtime = build_trial(state_root)
    return {
        "profile": config["profile"],
        "mode": config["mode"],
        "capabilities": dict(config["capabilities"]),
        "simulated_bookkeeping": {
            "stock_swing_initial_cash": config["virtual_accounts"]["stock_swing"]["initial_cash"],
            "long_options_initial_cash": config["virtual_accounts"]["long_options"]["initial_cash"],
            "total": config["virtual_accounts"]["total_simulated_bookkeeping"],
            "shared_pool": False,
            "stock_ledger": str(runtime.stock_ledger_path),
            "options_ledger": str(runtime.options_ledger_path),
        },
        "initial_snapshots": {
            "stock_swing": runtime.stock_ledger.snapshot(as_of),
            "long_options": runtime.options_ledger.snapshot(as_of),
        },
        "dollar_limits_per_account": derived_dollar_limits(),
        "trial": dict(config["trial"]),
        "news_external_factors": dict(config["news_external_factors"]),
        "claims": {
            "profitability_proven": False,
            "live_ready": False,
            "comprehensive_sentiment_or_external_factor_integration": False,
        },
    }
