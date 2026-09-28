"""Pure gate for an explicitly authorized, one-off PAPER profit-sale fallback.

This module never sends orders. No authorization is installed by default.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from research.alpaca_stock_paper_v1.guard import PAPER_ENDPOINT


@dataclass(frozen=True)
class ProfitFallback:
    instruction_id: str
    paper_position_id: str
    quantity_cap: Decimal
    minimum_bid: Decimal
    authorized_at: datetime
    valid_from: datetime
    expires_at: datetime
    wait_after_email: timedelta
    explicitly_confirmed: bool


@dataclass(frozen=True)
class Observation:
    endpoint: str
    paper_position_id: str
    held_quantity: Decimal
    bid: Decimal
    quote_at: datetime
    quote_feed: str
    market_open: bool
    email_accepted_at: datetime | None
    response_checked_at: datetime | None
    inbound_response_monitor_healthy: bool
    owner_responded: bool


def _aware(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def check(fallback: ProfitFallback | None, observation: Observation, now: datetime):
    """Return (eligible, reasons); silence without a recorded opt-in always fails."""
    if fallback is None:
        return False, ("no_explicit_fallback",)
    reasons = []
    times = (fallback.authorized_at, fallback.valid_from, fallback.expires_at,
             observation.quote_at, observation.email_accepted_at,
             observation.response_checked_at, now)
    if any(not _aware(t) for t in times):
        return False, ("missing_or_naive_time",)
    if not fallback.instruction_id or not fallback.explicitly_confirmed:
        reasons.append("not_confirmed")
    if (fallback.authorized_at > fallback.valid_from or
        not fallback.valid_from <= now < fallback.expires_at or
        fallback.wait_after_email <= timedelta(0)):
        reasons.append("invalid_or_expired_instruction")
    if observation.endpoint != PAPER_ENDPOINT or observation.paper_position_id != fallback.paper_position_id:
        reasons.append("wrong_paper_position")
    if not isinstance(fallback.quantity_cap, Decimal) or not fallback.quantity_cap.is_finite() or fallback.quantity_cap <= 0:
        reasons.append("invalid_quantity_cap")
    if not isinstance(observation.held_quantity, Decimal) or not observation.held_quantity.is_finite() or observation.held_quantity <= 0:
        reasons.append("no_verified_holding")
    elif isinstance(fallback.quantity_cap, Decimal) and observation.held_quantity > fallback.quantity_cap:
        reasons.append("quantity_exceeds_authorization")
    if (not isinstance(fallback.minimum_bid, Decimal) or not fallback.minimum_bid.is_finite() or
        fallback.minimum_bid <= 0 or not isinstance(observation.bid, Decimal) or
        not observation.bid.is_finite() or observation.bid < fallback.minimum_bid):
        reasons.append("target_bid_not_verified")
    if (observation.quote_feed != "iex" or
        not timedelta(0) <= now-observation.quote_at <= timedelta(seconds=2)):
        reasons.append("stale_or_wrong_feed")
    if observation.market_open is not True:
        reasons.append("market_closed")
    if (not fallback.valid_from <= observation.email_accepted_at <= now or
        now-observation.email_accepted_at < fallback.wait_after_email):
        reasons.append("email_not_accepted_or_wait_incomplete")
    if (observation.inbound_response_monitor_healthy is not True or
        not timedelta(0) <= now-observation.response_checked_at <= timedelta(seconds=30)):
        reasons.append("response_status_unverified")
    if observation.owner_responded is not False:
        reasons.append("owner_response_present_or_unknown")
    return not reasons, tuple(reasons)
