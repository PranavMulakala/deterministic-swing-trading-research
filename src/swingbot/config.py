from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    raw = config_path.read_bytes()
    config = json.loads(raw)
    validate_config(config)
    return config


def config_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_config(config: dict[str, Any]) -> None:
    account = config["account"]
    risk = config["risk"]
    strategy = config["strategy"]

    if not account.get("paper_only", False):
        raise ConfigError("v1 must be paper-only")
    if account.get("execution_enabled", True):
        raise ConfigError("milestone 1 broker execution must remain disabled")
    if not account.get("long_only", False) or not account.get("cash_only", False):
        raise ConfigError("v1 must be long-only and cash-only")
    if float(account["initial_equity"]) != 500.0:
        raise ConfigError("v1 initial equity must be exactly $500")
    if float(risk["max_planned_loss_pct"]) != 0.005:
        raise ConfigError("v1 per-trade planned-loss limit must be 0.5%")
    if float(risk["max_aggregate_open_risk_pct"]) != 0.03:
        raise ConfigError("v1 aggregate planned-risk limit must be 3%")
    if int(strategy["time_stop_trading_days"]) != 20:
        raise ConfigError("v1 time stop must be 20 trading days")
    universe = config.get("universe", [])
    if not 10 <= len(universe) <= 20 or len(universe) != len(set(universe)):
        raise ConfigError("universe must contain 10-20 unique symbols")
    forbidden = {"TQQQ", "SQQQ", "UPRO", "SPXU", "SOXL", "SOXS", "UVXY"}
    if forbidden.intersection(universe):
        raise ConfigError("leveraged/inverse ETFs are prohibited")

