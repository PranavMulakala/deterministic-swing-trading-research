from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timezone


@dataclass(frozen=True)
class RiskPolicy:
    max_planned_loss_pct: float
    max_aggregate_open_risk_pct: float
    daily_loss_halt_pct: float
    quote_max_age_seconds: int
    fractional_precision: int = 6


@dataclass(frozen=True)
class RiskDecision:
    accepted: bool
    reason: str


@dataclass
class RiskState:
    open_risk_by_symbol: dict[str, float] = field(default_factory=dict)
    accepted_order_ids: set[str] = field(default_factory=set)
    current_day: date | None = None
    start_of_day_equity: float = 0.0
    daily_realized_pnl: float = 0.0
    kill_switch_active: bool = False


class RiskManager:
    """The sole authority for sizing and admitting entry orders."""

    def __init__(self, policy: RiskPolicy):
        self.policy = policy
        self.state = RiskState()

    def start_day(self, day: date, equity: float) -> None:
        if self.state.current_day != day:
            self.state.current_day = day
            self.state.start_of_day_equity = equity
            self.state.daily_realized_pnl = 0.0

    def set_kill_switch(self, active: bool) -> None:
        self.state.kill_switch_active = active

    def calculate_quantity(
        self,
        equity: float,
        available_cash: float,
        entry_fill: float,
        stop_fill: float,
    ) -> tuple[float, float, float]:
        risk_per_share = entry_fill - stop_fill
        if equity <= 0 or available_cash <= 0 or risk_per_share <= 0 or entry_fill <= 0:
            return 0.0, 0.0, 0.0
        risk_limit = equity * self.policy.max_planned_loss_pct
        by_risk = risk_limit / risk_per_share
        by_cash = available_cash / entry_fill
        raw_qty = min(by_risk, by_cash)
        scale = 10**self.policy.fractional_precision
        qty = math.floor(raw_qty * scale) / scale
        planned_loss = qty * risk_per_share
        return qty, planned_loss, risk_limit

    def authorize_entry(
        self,
        *,
        order_id: str,
        symbol: str,
        equity: float,
        planned_loss: float,
        quote_timestamp: datetime,
        decision_timestamp: datetime,
    ) -> RiskDecision:
        if self.state.kill_switch_active:
            return RiskDecision(False, "global_kill_switch_active")
        if order_id in self.state.accepted_order_ids:
            return RiskDecision(False, "duplicate_order_id")
        if symbol in self.state.open_risk_by_symbol:
            return RiskDecision(False, "position_already_open")
        if quote_timestamp.tzinfo is None or decision_timestamp.tzinfo is None:
            return RiskDecision(False, "timestamp_must_be_timezone_aware")
        age = (decision_timestamp - quote_timestamp).total_seconds()
        if age < 0 or age > self.policy.quote_max_age_seconds:
            return RiskDecision(False, "stale_quote")
        if self.state.start_of_day_equity > 0:
            daily_limit = self.state.start_of_day_equity * self.policy.daily_loss_halt_pct
            if self.state.daily_realized_pnl <= -daily_limit:
                return RiskDecision(False, "daily_loss_halt")
        per_trade_limit = equity * self.policy.max_planned_loss_pct
        tolerance = 1e-8
        if planned_loss <= 0:
            return RiskDecision(False, "non_positive_planned_loss")
        if planned_loss > per_trade_limit + tolerance:
            return RiskDecision(False, "per_trade_risk_limit")
        aggregate = sum(self.state.open_risk_by_symbol.values()) + planned_loss
        if aggregate > equity * self.policy.max_aggregate_open_risk_pct + tolerance:
            return RiskDecision(False, "aggregate_open_risk_limit")
        self.state.accepted_order_ids.add(order_id)
        self.state.open_risk_by_symbol[symbol] = planned_loss
        return RiskDecision(True, "accepted")

    def close_position(self, symbol: str, realized_pnl: float) -> None:
        self.state.open_risk_by_symbol.pop(symbol, None)
        self.state.daily_realized_pnl += realized_pnl


def utc_bar_timestamp(day: date) -> datetime:
    """Deterministic timestamp used for historical risk checks."""
    return datetime(day.year, day.month, day.day, 16, 0, tzinfo=timezone.utc)
