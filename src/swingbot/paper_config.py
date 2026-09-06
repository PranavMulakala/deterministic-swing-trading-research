from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


PAPER_TRADING_BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_DATA_BASE_URL = "https://data.alpaca.markets"
FROZEN_STRATEGY_CONFIG_SHA256 = (
    "215d907b4d87f009d461a59fe3ff060a424cf00020fc77f2d6dfcdf138c7bd27"
)
FROZEN_STRATEGY_VALUE_SHA256 = (
    "b1c6237d44bd50e22672b60e2d0316193c66a3646f32c06a717ffd92c4bee434"
)
QUOTE_FUTURE_TOLERANCE_SECONDS = 2
CANCEL_VERIFICATION_ATTEMPTS = 5
CANCEL_VERIFICATION_INTERVAL_SECONDS = 0.25


class PaperConfigError(ValueError):
    pass


def load_paper_config(path: str | Path, strategy_path: str | Path) -> dict[str, Any]:
    paper = json.loads(Path(path).read_text(encoding="utf-8"))
    strategy_bytes = Path(strategy_path).read_bytes()
    _validate(paper, hashlib.sha256(strategy_bytes).hexdigest())
    return paper


def _validate(config: dict[str, Any], strategy_digest: str) -> None:
    if config.get("schema_version") != 1:
        raise PaperConfigError("unsupported paper config schema")
    if strategy_digest != FROZEN_STRATEGY_CONFIG_SHA256:
        raise PaperConfigError("paper workflow requires the exact frozen v1 strategy bytes")
    if config.get("strategy_config_sha256") != FROZEN_STRATEGY_CONFIG_SHA256:
        raise PaperConfigError("paper workflow is not bound to the frozen strategy config")

    broker = config.get("broker", {})
    if broker.get("provider") != "alpaca":
        raise PaperConfigError("broker provider must remain alpaca")
    if broker.get("trading_base_url") != PAPER_TRADING_BASE_URL:
        raise PaperConfigError("only the exact Alpaca paper trading endpoint is allowed")
    if broker.get("data_base_url") != ALPACA_DATA_BASE_URL:
        raise PaperConfigError("unexpected Alpaca market-data endpoint")
    if broker.get("paper_only") is not True:
        raise PaperConfigError("paper_only must be true")
    if broker.get("market_data_feed") != "iex":
        raise PaperConfigError("paper v1 market_data_feed must remain iex")
    if broker.get("historical_adjustment") != "all":
        raise PaperConfigError("daily bars must request all corporate-action adjustments")
    if broker.get("request_timeout_seconds") != 20:
        raise PaperConfigError("broker request timeout must remain 20 seconds")

    account = config.get("account", {})
    try:
        initial_equity = Decimal(str(account.get("initial_equity", "")))
        initial_tolerance = Decimal(str(account.get("initial_equity_tolerance", "")))
    except InvalidOperation:
        raise PaperConfigError("paper account equity settings must be numeric") from None
    if initial_equity != Decimal("500"):
        raise PaperConfigError("paper account must begin at exactly $500")
    if initial_tolerance != Decimal("0.01"):
        raise PaperConfigError("paper account binding tolerance must remain one cent")
    if account.get("currency") != "USD":
        raise PaperConfigError("paper account currency must be USD")
    if account.get("long_only") is not True or account.get("cash_only") is not True:
        raise PaperConfigError("paper workflow must remain long-only and cash-only")

    execution = config.get("execution", {})
    exact = {
        "entry_order_class": "oto",
        "entry_order_type": "market",
        "time_in_force": "gtc",
        "extended_hours": False,
        "default_kill_switch": True,
        "approval_ttl_seconds": 120,
        "quote_max_age_seconds": 30,
        "quote_future_tolerance_seconds": QUOTE_FUTURE_TOLERANCE_SECONDS,
        "max_requote_drift_bps": 10,
        "max_quote_spread_bps": 100,
        "market_fill_buffer_bps": 25,
        "cancel_verification_attempts": CANCEL_VERIFICATION_ATTEMPTS,
        "cancel_verification_interval_seconds": CANCEL_VERIFICATION_INTERVAL_SECONDS,
        "exit_cancel_cutoff_seconds_before_close": 60,
    }
    for key, expected in exact.items():
        if execution.get(key) != expected:
            raise PaperConfigError(f"execution.{key} must be {expected!r}")
    if execution.get("runtime_enable_phrase") != "I_UNDERSTAND_PAPER_ONLY":
        raise PaperConfigError("runtime enable phrase may not be weakened")
    if execution.get("fractional_swing_orders") != (
        "prohibited_because_alpaca_fractional_orders_are_day_only"
    ):
        raise PaperConfigError("fractional GTC swing orders may not be enabled on Alpaca")

    monitoring = config.get("monitoring", {})
    if monitoring.get("poll_seconds") != 15:
        raise PaperConfigError("monitor polling interval must remain 15 seconds")
    terminal = set(monitoring.get("order_terminal_statuses", []))
    working = set(monitoring.get("order_working_statuses", []))
    if terminal != {"filled", "canceled", "expired", "rejected", "replaced"}:
        raise PaperConfigError("terminal order statuses are incomplete or unexpected")
    expected_working = {
        "accepted", "accepted_for_bidding", "calculated", "done_for_day", "held",
        "new", "partially_filled", "pending_cancel", "pending_new", "pending_replace",
        "stopped", "suspended",
    }
    if working != expected_working:
        raise PaperConfigError("working order statuses are incomplete or unexpected")
    if terminal & working:
        raise PaperConfigError("order status classes overlap")
