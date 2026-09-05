from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Bar:
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Signal:
    symbol: str
    signal_date: date
    atr: float
    close: float
    sma20: float
    sma200: float
    rsi2: float
    reason: str
    invalidation: str


@dataclass
class Position:
    symbol: str
    signal_date: date
    entry_date: date
    entry_reference: float
    entry_fill: float
    entry_fee: float
    quantity: float
    initial_quantity: float
    stop_reference: float
    planned_stop_fill: float
    planned_loss: float
    risk_limit: float
    initial_equity: float
    reason: str
    invalidation: str
    holding_days: int = 0


@dataclass(frozen=True)
class Trade:
    symbol: str
    signal_date: date
    entry_date: date
    exit_signal_date: date | None
    exit_date: date
    entry_reference: float
    exit_reference: float
    entry_fill: float
    exit_fill: float
    quantity: float
    entry_fee: float
    exit_fee: float
    modeled_execution_cost: float
    pnl: float
    return_pct_on_equity: float
    planned_loss: float
    planned_risk_pct: float
    risk_limit: float
    holding_days: int
    exit_reason: str
    qualification: str
    invalidation: str


@dataclass
class BacktestResult:
    split: str
    start_date: date
    end_date: date
    initial_equity: float
    final_equity: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[dict[str, object]] = field(default_factory=list)
    exposure_curve: list[dict[str, object]] = field(default_factory=list)
    events: list[dict[str, object]] = field(default_factory=list)
