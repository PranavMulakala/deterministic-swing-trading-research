"""Pure offline assessment of an UNAPPROVED MNQ trial-budget proposal.

No network, broker SDK, order submission, credentials, or persistent state.
Passing the arithmetic means only that the supplied snapshot fits this proposal.
It never establishes broker enforcement, strategy readiness, or authorization.
See TRIAL_BUDGET_EVALUATOR.md for the exact accounting/input contract.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Mapping


PROPOSAL_PATH = Path(__file__).with_name("trial_budget_proposal.json")
ZERO = Decimal("0")


def number(value: Any, name: str, *, nullable: bool = False,
           nonnegative: bool = False) -> Decimal | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{name} must be a finite number" + (" or null" if nullable else ""))
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    if nonnegative and result < ZERO:
        raise ValueError(f"{name} must be nonnegative")
    return result


def count(value: Any, name: str, *, signed: bool = False) -> int:
    if type(value) is not int or (not signed and value < 0):
        raise ValueError(f"{name} must be a {'signed' if signed else 'nonnegative'} integer")
    return value


def flag(value: Any, name: str, *, nullable: bool = True) -> bool | None:
    if type(value) is bool or (nullable and value is None):
        return value
    raise ValueError(f"{name} must be boolean" + (" or null" if nullable else ""))


def dollars(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def load_proposal() -> dict[str, Any]:
    """Reject edited policies instead of letting this utility become a live switch."""
    proposal = json.loads(PROPOSAL_PATH.read_text(), parse_float=Decimal)
    expected = {
        "schema_version": 1,
        "proposal_id": "mnq_limited_live_budget_v1",
        "status": "NOT_APPROVED", "orders_enabled": False,
        "live_authorized": False,
        "purpose": "OFFLINE_REVIEW_ONLY_NOT_BROKER_ENFORCEMENT",
        "instrument_root": "MNQ",
        "trade_risk_cap_usd": Decimal("12.5"),
        "trade_risk_fraction": Decimal("0.0025"),
        "daily_loss_cap_usd": 25,
        "daily_loss_fraction": Decimal("0.005"),
        "total_nonreplenishing_loss_allowance_usd": 50,
        "high_water_drawdown_fraction": Decimal("0.05"),
        "max_contracts": 1, "max_entry_attempts_per_day": 2,
        "review_after_completed_round_trips": 5,
        "review_after_completed_sessions": 5,
        "loss_limits_are_guarantees": False,
    }
    if proposal != expected or any(type(proposal[k]) is not type(expected[k]) for k in expected):
        raise ValueError("Proposal changed: this evaluator supports only the unapproved v1 proposal")
    return proposal


@dataclass(frozen=True)
class Snapshot:
    day_start_equity_usd: Any
    marked_equity_usd: Any
    high_water_equity_usd: Any
    closed_trade_net_pnls_usd: list[Any]
    position_contracts: Any
    open_position_gross_pnl_usd: Any
    open_position_paid_entry_fees_usd: Any
    open_position_unpaid_exit_fee_reserve_usd: Any
    entry_attempts_today: Any
    completed_sessions: Any
    pending_entry_contracts: Any
    instrument_root: Any
    data_fresh: Any
    broker_position_known: Any
    broker_connection_healthy: Any
    equity_reconciled: Any
    protective_exit_confirmed: Any
    prior_pause_latched: Any
    operator_available: Any
    candidate_contracts: Any
    candidate_planned_loss_usd: Any
    candidate_costs_verified: Any


def assess(snapshot: Snapshot | Mapping[str, Any]) -> dict[str, Any]:
    policy = load_proposal()
    if isinstance(snapshot, Mapping):
        try:
            snapshot = Snapshot(**snapshot)
        except TypeError as error:
            raise ValueError(f"Invalid snapshot fields: {error}") from error
    if not isinstance(snapshot, Snapshot):
        raise ValueError("snapshot must be Snapshot or an exact field mapping")
    raw = asdict(snapshot)
    values = {
        name: number(raw[name], name, nullable=True)
        for name in ("day_start_equity_usd", "marked_equity_usd", "high_water_equity_usd")
    }
    for name in ("open_position_gross_pnl_usd", "open_position_paid_entry_fees_usd",
                 "open_position_unpaid_exit_fee_reserve_usd", "candidate_planned_loss_usd"):
        values[name] = number(raw[name], name, nullable=True,
                              nonnegative=name != "open_position_gross_pnl_usd")
    if type(snapshot.closed_trade_net_pnls_usd) is not list:
        raise ValueError("closed_trade_net_pnls_usd must be a complete list")
    closed = [number(value, f"closed_trade_net_pnls_usd[{i}]")
              for i, value in enumerate(snapshot.closed_trade_net_pnls_usd)]
    position = count(snapshot.position_contracts, "position_contracts", signed=True)
    attempts = count(snapshot.entry_attempts_today, "entry_attempts_today")
    sessions = count(snapshot.completed_sessions, "completed_sessions")
    pending = count(snapshot.pending_entry_contracts, "pending_entry_contracts")
    candidate_contracts = count(snapshot.candidate_contracts, "candidate_contracts")
    if type(snapshot.instrument_root) is not str:
        raise ValueError("instrument_root must be a string")
    flags = {name: flag(raw[name], name) for name in (
        "data_fresh", "broker_position_known", "broker_connection_healthy",
        "equity_reconciled", "protective_exit_confirmed", "operator_available",
        "candidate_costs_verified")}
    flag(snapshot.prior_pause_latched, "prior_pause_latched", nullable=False)

    pauses: list[str] = []
    entry_blocks: list[str] = []
    for name, reason in (
        ("data_fresh", "STALE_OR_UNKNOWN_DATA"),
        ("broker_position_known", "UNKNOWN_BROKER_POSITION"),
        ("broker_connection_healthy", "BROKER_CONNECTION_UNAVAILABLE_OR_UNKNOWN"),
        ("equity_reconciled", "EQUITY_NOT_RECONCILED"),
        ("operator_available", "OPERATOR_UNAVAILABLE_OR_UNKNOWN"),
    ):
        if flags[name] is not True:
            pauses.append(reason)
    if snapshot.prior_pause_latched:
        pauses.append("PREVIOUS_PAUSE_REQUIRES_REVIEW")
    if snapshot.instrument_root != policy["instrument_root"]:
        pauses.append("INSTRUMENT_OUTSIDE_PROPOSAL")
    if abs(position) > policy["max_contracts"] or abs(position) + pending > policy["max_contracts"]:
        pauses.append("EXCESS_OR_DUPLICATE_EXPOSURE")
    if position:
        entry_blocks.append("POSITION_ALREADY_OPEN")
        if flags["protective_exit_confirmed"] is not True:
            pauses.append("PROTECTIVE_EXIT_UNCONFIRMED_OR_FAILED")
    if pending:
        entry_blocks.append("ENTRY_ALREADY_PENDING_RECONCILE_FIRST")
    if attempts >= policy["max_entry_attempts_per_day"]:
        # The legitimate second trade keeps its normal protection/exits. An
        # admission ceiling is not a reason to flatten an existing position.
        entry_blocks.append("DAILY_ENTRY_ATTEMPT_LIMIT")
    if attempts > policy["max_entry_attempts_per_day"]:
        pauses.append("DAILY_ENTRY_ATTEMPT_LIMIT_EXCEEDED")
    if len(closed) >= policy["review_after_completed_round_trips"]:
        pauses.append("COMPLETED_ROUND_TRIP_REVIEW_BOUNDARY")
    if sessions >= policy["review_after_completed_sessions"]:
        pauses.append("COMPLETED_SESSION_REVIEW_BOUNDARY")
    for name in ("day_start_equity_usd", "marked_equity_usd", "high_water_equity_usd"):
        if values[name] is None or values[name] <= ZERO:
            pauses.append(f"UNKNOWN_OR_NONPOSITIVE_{name.upper()}")

    day_equity = values["day_start_equity_usd"]
    marked_equity = values["marked_equity_usd"]
    high_water = values["high_water_equity_usd"]
    if high_water is not None and marked_equity is not None and high_water < marked_equity:
        pauses.append("HIGH_WATER_BELOW_CURRENT_EQUITY")
    if high_water is not None and day_equity is not None and high_water < day_equity:
        pauses.append("HIGH_WATER_BELOW_DAY_START_EQUITY")
    open_gross = values["open_position_gross_pnl_usd"]
    entry_fees = values["open_position_paid_entry_fees_usd"]
    exit_reserve = values["open_position_unpaid_exit_fee_reserve_usd"]
    if not position:
        if any(value != ZERO for value in (open_gross, entry_fees, exit_reserve)):
            raise ValueError("Flat position requires explicit zero open P&L, entry fees, and exit reserve")
    elif any(value is None for value in (open_gross, entry_fees, exit_reserve)):
        pauses.append("OPEN_POSITION_ACCOUNTING_UNKNOWN")

    trade_cap = daily_cap = daily_loss = daily_remaining = drawdown = None
    if day_equity is not None and day_equity > ZERO:
        trade_cap = min(Decimal(str(policy["trade_risk_cap_usd"])),
                        day_equity * policy["trade_risk_fraction"])
        daily_cap = min(Decimal(str(policy["daily_loss_cap_usd"])),
                        day_equity * policy["daily_loss_fraction"])
        if marked_equity is not None and exit_reserve is not None:
            # marked_equity already includes paid entry fees and all realized P&L.
            daily_loss = max(ZERO, day_equity - marked_equity + exit_reserve)
            daily_remaining = max(ZERO, daily_cap - daily_loss)
            if daily_loss >= daily_cap:
                pauses.append("DAILY_LOSS_LIMIT_REACHED_OR_EXCEEDED")
    if high_water is not None and high_water > ZERO and marked_equity is not None:
        # Preserve the original marked-equity high-water definition; do not add a
        # reserve to this baseline drawdown calculation.
        drawdown = max(ZERO, high_water - marked_equity) / high_water
        if drawdown >= policy["high_water_drawdown_fraction"]:
            pauses.append("FROZEN_HIGH_WATER_DRAWDOWN_LIMIT")

    closed_loss = sum((max(ZERO, -pnl) for pnl in closed), ZERO)
    open_loss = total_used = total_remaining = None
    if all(value is not None for value in (open_gross, entry_fees, exit_reserve)):
        open_loss = max(ZERO, -(open_gross - entry_fees - exit_reserve))
        total_used = closed_loss + open_loss
        total_remaining = max(ZERO, Decimal(str(policy[
            "total_nonreplenishing_loss_allowance_usd"])) - total_used)
        if total_used >= Decimal(str(policy["total_nonreplenishing_loss_allowance_usd"])):
            pauses.append("TOTAL_NONREPLENISHING_LOSS_LIMIT_REACHED_OR_EXCEEDED")

    if candidate_contracts != 1:
        entry_blocks.append("CANDIDATE_MUST_BE_EXACTLY_ONE_MNQ")
    if flags["candidate_costs_verified"] is not True:
        entry_blocks.append("CANDIDATE_COSTS_UNVERIFIED")
    candidate_loss = values["candidate_planned_loss_usd"]
    if candidate_loss is None or candidate_loss <= ZERO:
        entry_blocks.append("POSITIVE_CANDIDATE_PLANNED_LOSS_REQUIRED")
    else:
        for limit, reason in (
            (trade_cap, "CANDIDATE_EXCEEDS_TRADE_RISK_CAP"),
            (daily_remaining, "CANDIDATE_EXCEEDS_REMAINING_DAILY_ALLOWANCE"),
            (total_remaining, "CANDIDATE_EXCEEDS_REMAINING_TOTAL_ALLOWANCE"),
        ):
            if limit is None:
                entry_blocks.append(f"{reason}_UNKNOWN")
            elif candidate_loss > limit:
                entry_blocks.append(reason)

    return {
        "assessment": "OFFLINE_PROPOSAL_EVALUATION_ONLY",
        "proposal_id": policy["proposal_id"], "proposal_status": "NOT_APPROVED",
        "orders_enabled": False, "live_authorized": False,
        "entry_fits_proposed_limits": not pauses and not entry_blocks,
        "pause_required_by_proposal": bool(pauses),
        "pause_reasons": pauses, "entry_block_reasons": entry_blocks,
        "metrics_usd": {
            "trade_risk_cap": dollars(trade_cap), "daily_loss_cap": dollars(daily_cap),
            "daily_loss_including_unpaid_exit_fee_reserve": dollars(daily_loss),
            "remaining_daily_allowance": dollars(daily_remaining),
            "closed_nonreplenishing_losses": dollars(closed_loss),
            "open_loss_including_entry_fees_and_exit_reserve": dollars(open_loss),
            "total_nonreplenishing_allowance_used": dollars(total_used),
            "remaining_total_allowance": dollars(total_remaining),
        },
        "high_water_drawdown_fraction": dollars(drawdown),
        "completed_round_trips": len(closed), "completed_sessions": sessions,
        "entry_attempts_today": attempts,
        "limits_are_guaranteed": False,
        "not_assessed": ["strategy_edge", "held_out_evidence", "broker_margin",
                         "actual_fee_accuracy", "market_data_entitlement",
                         "snapshot_truth_or_freshness", "native_protection_enforcement",
                         "live_approval"],
        "state_persisted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Local JSON snapshot; no credentials needed")
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.snapshot.read_text(), parse_float=Decimal)
        result = assess(snapshot)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Invalid offline snapshot: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
