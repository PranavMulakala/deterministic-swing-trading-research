"""Pure, fail-closed paper entry preflight. No credentials or broker I/O."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
import hashlib
from zoneinfo import ZoneInfo

PAPER_ENDPOINT = "https://paper-api.alpaca.markets"
NY = ZoneInfo("America/New_York")
D = lambda value: Decimal(str(value))


@dataclass(frozen=True)
class Account:
    endpoint: str
    observed_at: datetime
    cash: Decimal
    buying_power: Decimal
    positions: int
    open_orders: int
    market_open: bool


@dataclass(frozen=True)
class Quote:
    observed_at: datetime
    bid: Decimal
    ask: Decimal
    feed: str


@dataclass(frozen=True)
class Intent:
    strategy_version: str
    symbol: str
    decision_at: datetime
    quantity: Decimal
    limit_price: Decimal


@dataclass(frozen=True)
class Policy:
    approved_strategy_versions: frozenset[str] = frozenset()
    experimental_cash_available: Decimal = Decimal("0")
    reserved_pending_debit: Decimal = Decimal("0")
    max_position_debit: Decimal = Decimal("1000")
    max_experiment_allocation: Decimal = Decimal("4000")
    cost_bps_buffer: Decimal = Decimal("25")


def _aware(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _valid_money(value):
    return isinstance(value, Decimal) and value.is_finite() and value >= 0


def preflight(account: Account, quote: Quote, intent: Intent, policy: Policy,
              now: datetime, used_order_ids: frozenset[str] = frozenset()):
    """Return (allowed, reasons, client_order_id); never calls a broker."""
    reasons = []
    if not _aware(now) or any(not _aware(t) for t in (account.observed_at, quote.observed_at, intent.decision_at)):
        return False, ("naive_time",), None
    if account.endpoint != PAPER_ENDPOINT:
        reasons.append("wrong_endpoint")
    if account.market_open is not True:
        reasons.append("market_not_open")
    if not intent.strategy_version or intent.strategy_version not in policy.approved_strategy_versions:
        reasons.append("strategy_not_approved")
    if intent.symbol != "LITE":
        reasons.append("symbol_not_approved")
    local = now.astimezone(NY)
    if local.weekday() >= 5 or not (time(9, 30) <= local.time() < time(16)):
        reasons.append("outside_regular_hours")
    for observed, max_age, label in ((account.observed_at, timedelta(seconds=5), "account"),
                                     (quote.observed_at, timedelta(seconds=2), "quote"),
                                     (intent.decision_at, timedelta(seconds=10), "decision")):
        age = now - observed
        if age < timedelta(0) or age > max_age:
            reasons.append(f"stale_{label}")
    if quote.feed != "iex":
        reasons.append("unexpected_feed")
    if any(not _valid_money(v) for v in (
        account.cash, account.buying_power, quote.bid, quote.ask, intent.quantity,
        intent.limit_price, policy.experimental_cash_available,
        policy.reserved_pending_debit, policy.max_position_debit,
        policy.max_experiment_allocation, policy.cost_bps_buffer
    )):
        reasons.append("invalid_amount")
    else:
        if quote.bid <= 0 or quote.ask <= 0 or quote.bid > quote.ask:
            reasons.append("invalid_quote")
        if intent.quantity <= 0 or intent.limit_price <= 0:
            reasons.append("invalid_intent")
        if quote.ask > intent.limit_price:
            reasons.append("ask_above_limit")
        if policy.experimental_cash_available > policy.max_experiment_allocation:
            reasons.append("allocation_exceeds_cap")
        if policy.reserved_pending_debit > policy.experimental_cash_available:
            reasons.append("pending_exceeds_cash")
        debit = intent.quantity * intent.limit_price * (1 + policy.cost_bps_buffer / D(10000))
        if debit > policy.max_position_debit:
            reasons.append("position_cap")
        if debit + policy.reserved_pending_debit > policy.experimental_cash_available:
            reasons.append("experimental_cash")
        if debit + policy.reserved_pending_debit > account.cash:
            reasons.append("broker_cash")
    if account.positions != 0 or account.open_orders != 0:
        reasons.append("existing_exposure")
    key = f"{intent.strategy_version}|{intent.symbol}|{intent.decision_at.isoformat()}"
    order_id = "stockpaper-" + hashlib.sha256(key.encode()).hexdigest()[:32]
    if order_id in used_order_ids:
        reasons.append("duplicate_decision")
    return not reasons, tuple(reasons), order_id
