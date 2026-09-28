"""Offline MNQ paper/shadow evidence comparison. Never places or authorizes orders."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / "mnq_feasibility_v1"
TICK = Decimal("0.25")
POINT_VALUE = Decimal("2")
NEW_YORK = ZoneInfo("America/New_York")
STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})$")
EXECUTION_MODEL = {
    "version": "mnq_feasibility_v1_bbo_market_exit_v1",
    "entry_delay_ns": 1000000000,
    "entry_wait_ns": 1000000000,
    "exit_delay_ns": 100000000,
    "entry_reference": "BUY_ASK_SELL_BID",
    "exit_trigger": "LIQUIDATION_SIDE_BBO",
    "exit_order": "MARKET_AFTER_TRIGGER_DELAY",
    "target_order": "MARKET_AFTER_TRIGGER_DELAY",
}
REMAINING = [
    "Broker paper environment and export provenance need independent verification.",
    "Replay must use the same complete market stream, contract, clock and frozen rules as paper.",
    "Frozen-engine execution provenance, stop/target prices, planned-risk sizing, and intratrade loss/drawdown pauses are not established by this record contract.",
    "Actual broker fees, margin and platform costs must be verified.",
    "Protective-order, disconnect, duplicate-submit, restart and pause behavior need broker paper tests.",
    "Historical edge and its uncertainty on reserved data remain a separate research requirement.",
    "A concrete live loss budget and explicit user approval are required; this tool cannot authorize trading.",
]


class EvidenceError(ValueError):
    pass


def stamp(value):
    """Require an explicit offset and preserve nanoseconds (no float timestamps)."""
    if not isinstance(value, str) or not (m := STAMP.fullmatch(value)):
        raise EvidenceError("timestamp_requires_RFC3339_offset_and_at_most_9_fraction_digits")
    try:
        dt = datetime.fromisoformat(m[1] + m[3].replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid_timestamp") from exc
    delta = dt.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 10**9 + int((m[2] or "").ljust(9, "0"))


def money(value, *, positive=False, tick=False, signed=False):
    if not isinstance(value, str):
        raise EvidenceError("prices_and_fees_must_be_decimal_strings")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise EvidenceError("invalid_decimal") from exc
    if not result.is_finite() or (not signed and result < 0) or (positive and result <= 0):
        raise EvidenceError("invalid_nonnegative_decimal")
    if tick and result % TICK:
        raise EvidenceError("off_tick_price")
    return result


def integer(value, *, positive=False):
    if type(value) is not int or (positive and value <= 0):
        raise EvidenceError("quantity_must_be_whole_contracts")
    return value


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def frozen_fingerprint():
    pins = json.loads((FROZEN / "runs/pre-import-frozen-files.json").read_text())
    hashes = {name: digest(FROZEN / name) for name in ("engine.py", "config.json", "PROTOCOL.md")}
    if any(pins[name] != value for name, value in hashes.items()):
        raise EvidenceError("frozen_research_files_changed")
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def unique(records, key):
    result = {}
    if not isinstance(records, list):
        raise EvidenceError(f"{key}_records_must_be_list")
    for row in records:
        identity = row[key]
        if not isinstance(identity, str) or not identity:
            raise EvidenceError(f"invalid_{key}")
        if identity in result:
            raise EvidenceError(f"duplicate_{key}:{identity}")
        result[identity] = row
    return result


def base_report():
    return {
        "schema_version": 1,
        "comparator_sha256": digest(Path(__file__)),
        "live_readiness": "NOT_READY",
        "live_trial_authorized": False,
        "orders_enabled": False,
        "comparison_status": "EVIDENCE_BLOCKED",
        "evidence_authenticity": "NOT_INDEPENDENTLY_VERIFIED",
        "blockers": [], "differences": [], "matches": [],
        "remaining_requirements": REMAINING,
        "limits": [
            "Hashes prove file identity, not that the exporter or broker produced truthful records.",
            "A reconciliation pass is not proof of profitable trading or execution readiness.",
            "Only completed flat-to-flat windows are supported. Open exposure blocks comparison.",
            "No fill, price, fee, position or missing order is imputed.",
            "No numerical acceptance tolerance has been approved; all nonzero differences require review.",
        ],
    }


def compare(paper=None, simulation=None, *, paper_root=None, simulation_root=None):
    report = base_report()
    if paper is None:
        report["blockers"].append("MISSING_ACTUAL_BROKER_PAPER_RECORDS")
    if simulation is None:
        report["blockers"].append("MISSING_CORRESPONDING_SHADOW_SIMULATION")
    if report["blockers"]:
        return report
    if not isinstance(paper, dict) or not isinstance(simulation, dict):
        report["blockers"].append("INVALID_EVIDENCE:BUNDLES_MUST_BE_OBJECTS")
        return report
    try:
        _compare(paper, simulation, paper_root, simulation_root, report)
    except (EvidenceError, KeyError, TypeError, OSError, InvalidOperation) as exc:
        report["blockers"].append(f"INVALID_EVIDENCE:{type(exc).__name__}:{exc}")
    if not report["blockers"]:
        report["comparison_status"] = "DIFFERENCES_REQUIRE_REVIEW" if report["differences"] else "RECONCILED_FOR_REVIEW"
    if paper.get("evidence_kind") == "SYNTHETIC_FIXTURE" or simulation.get("evidence_kind") == "SYNTHETIC_FIXTURE":
        report["comparison_status"] = "SYNTHETIC_FIXTURE_ONLY"
    return report


def _compare(paper, sim, paper_root, sim_root, report):
    def check(condition, reason):
        if not condition:
            report["blockers"].append(reason)

    fingerprint = frozen_fingerprint()
    report["expected_strategy_fingerprint"] = fingerprint
    retained_sources = {}

    def source_reference(value, label):
        return isinstance(value, str) and bool(value.strip()) and value in retained_sources.get(label, set())

    def local_time(ns):
        return datetime.fromtimestamp(ns // 10**9, timezone.utc).astimezone(NEW_YORK)

    def entry_window(ns):
        local = local_time(ns)
        return (9, 45) <= (local.hour, local.minute) < (11, 30)

    for label, bundle, root, kind in (("paper", paper, paper_root, "BROKER_PAPER_EXPORT"),
                                      ("simulation", sim, sim_root, "FORWARD_SHADOW_SIMULATION")):
        check(type(bundle["schema_version"]) is int and bundle["schema_version"] == 1, f"{label}:UNSUPPORTED_SCHEMA")
        check(bundle["evidence_kind"] == kind, f"{label}:NOT_ACTUAL_PAIRED_FORWARD_EVIDENCE")
        check(bundle["strategy_fingerprint"] == fingerprint, f"{label}:FROZEN_RULES_MISMATCH")
        check(bundle["execution_model"] == EXECUTION_MODEL, f"{label}:EXECUTION_MODEL_OR_TRIGGER_MISMATCH")
        check(bundle["symbol"] == paper["symbol"], f"{label}:CONTRACT_MISMATCH")
        check(bool(re.fullmatch(r"MNQ[HMUZ]\d{1,2}", bundle["symbol"])), f"{label}:NOT_AN_OUTRIGHT_MNQ_CONTRACT")
        start, end = stamp(bundle["window"]["start"]), stamp(bundle["window"]["end"])
        check(start < end, f"{label}:INVALID_WINDOW")
        check(stamp(bundle["exported_at"]) >= end, f"{label}:EXPORT_PRECEDES_WINDOW_END")
        check(bundle["complete"] is True, f"{label}:INCOMPLETE_EXPORT")
        check(bool(bundle["source_files"]), f"{label}:SOURCE_FILES_MISSING")
        seen_sources = set()
        retained_sources[label] = set()
        for source in bundle["source_files"]:
            if not isinstance(source["path"], str) or not source["path"].strip():
                raise EvidenceError(f"{label}:source_path_must_be_nonempty_string")
            path = Path(source["path"])
            if root is None or path.is_absolute() or ".." in path.parts:
                raise EvidenceError(f"{label}:source_paths_must_be_relative_to_bundle")
            resolved = (Path(root) / path).resolve()
            if not resolved.is_relative_to(Path(root).resolve()) or resolved in seen_sources:
                raise EvidenceError(f"{label}:invalid_or_duplicate_source_path")
            seen_sources.add(resolved)
            matches = digest(resolved) == source["sha256"]
            check(matches, f"{label}:SOURCE_HASH_MISMATCH:{path}")
            if matches:
                retained_sources[label].add(str(path))
        check(source_reference(bundle["execution_model_source"], label), f"{label}:EXECUTION_MODEL_PROVENANCE_MISSING_OR_NOT_RETAINED")
    start, end = stamp(paper["window"]["start"]), stamp(paper["window"]["end"])
    check((start, end) == (stamp(sim["window"]["start"]), stamp(sim["window"]["end"])), "WINDOW_MISMATCH")
    check(paper["account_mode"] == "PAPER", "NOT_A_PAPER_ACCOUNT")
    check(bool(paper["broker"]) and bool(paper["account_alias"]), "BROKER_OR_ACCOUNT_IDENTITY_MISSING")
    check(sim["clock_basis"] == "EXCHANGE_EVENT_UTC", "SIMULATION_CLOCK_DIFFERS_FROM_FROZEN_ENGINE")
    check(paper["clock_alignment_verified"] is True and source_reference(paper["clock_alignment_source"], "paper"), "UNVERIFIED_CLOCK_ALIGNMENT")
    check(sim["market_data_complete"] is True, "INCOMPLETE_SIMULATION_MARKET_STREAM")
    check(paper["fees_complete"] is True, "INCOMPLETE_FEES")

    signals = unique(sim["signals"], "signal_id")
    paper_decisions = unique(paper["decisions"], "signal_id")
    check(set(signals) == set(paper_decisions), "SIGNAL_SET_MISMATCH")
    orders = unique(paper["orders"], "order_id")
    fills = unique(paper["fills"], "fill_id")
    positions = unique(paper["positions"], "snapshot_id")
    check(bool(signals), "NO_SIGNALS_TO_COMPARE")
    check(bool(fills), "NO_BROKER_PAPER_FILLS_TO_COMPARE")
    by_order, by_signal, chronological = defaultdict(list), defaultdict(list), []

    for identity, order in orders.items():
        signal_id, leg = order["signal_id"], order["leg"]
        check(signal_id in signals, f"UNMATCHED_PAPER_ORDER:{identity}")
        check(order["symbol"] == paper["symbol"], f"ORDER_CONTRACT_MISMATCH:{identity}")
        if leg not in ("ENTRY", "EXIT") or order["side"] not in ("BUY", "SELL"):
            raise EvidenceError(f"unsupported_order_leg_or_side:{identity}")
        check(order["order_type"] == "MARKET", f"ORDER_EXECUTION_SEMANTICS_MISMATCH:{identity}")
        qty = integer(order["quantity"], positive=True)
        check(qty == 1, f"MAX_ONE_CONTRACT_VIOLATION:{identity}")
        submitted, quote = stamp(order["submitted_at"]), stamp(order["reference_quote_at"])
        received = stamp(order["reference_quote_received_at"])
        check(start <= submitted <= end, f"ORDER_OUTSIDE_WINDOW:{identity}")
        check(quote <= received <= submitted, f"QUOTE_RECEIPT_CLOCK_ORDER_INVALID:{identity}")
        check(0 <= submitted - quote <= 10**9, f"STALE_OR_FUTURE_REFERENCE_QUOTE:{identity}")
        if leg == "EXIT":
            trigger = stamp(order["trigger_at"])
            check(start <= trigger and submitted - trigger >= EXECUTION_MODEL["exit_delay_ns"], f"EXIT_TRIGGER_DELAY_MISMATCH:{identity}")
            check(order["trigger_basis"] == "LIQUIDATION_SIDE_BBO", f"EXIT_TRIGGER_BASIS_MISMATCH:{identity}")
        else:
            check(order["trigger_at"] is None and order["trigger_basis"] == "SIGNAL_CONFIRMATION", f"ENTRY_TRIGGER_BASIS_MISMATCH:{identity}")
        received_ack = stamp(order["acknowledgement_received_at"]) if order["acknowledgement_received_at"] is not None else None
        check(received_ack is not None and submitted <= received_ack <= end, f"ACKNOWLEDGEMENT_RECEIPT_MISSING_OR_INVALID:{identity}")
        # A fill can occur before an acknowledgement message reaches the client.
        # Optional broker acknowledgement-event time is retained as a separate domain.
        if order["broker_acknowledged_at"] is not None:
            broker_ack = stamp(order["broker_acknowledged_at"])
            check(received_ack is not None and submitted <= broker_ack <= received_ack,
                  f"BROKER_ACKNOWLEDGEMENT_CLOCK_ORDER_INVALID:{identity}")
        check(order["status"] in ("FILLED", "CANCELED", "REJECTED"), f"UNRESOLVED_ORDER:{identity}:{order['status']}")
        by_signal[signal_id].append(order)
    for identity, fill in fills.items():
        if fill["order_id"] not in orders:
            check(False, f"ORPHAN_FILL:{identity}")
            continue
        order = orders[fill["order_id"]]
        at = stamp(fill["at"])
        qty = integer(fill["quantity"], positive=True)
        price = money(fill["price"], positive=True, tick=True)
        fee = money(fill["fee_usd"]) if fill["fee_usd"] is not None else None
        check(fee is not None, f"MISSING_FILL_FEE:{identity}")
        check(fill["fee_source"] in ("BROKER_EXPORT", "VERIFIED_FEE_SCHEDULE"), f"UNVERIFIED_FILL_FEE:{identity}")
        check(source_reference(fill["fee_source_reference"], "paper"), f"FILL_FEE_SOURCE_NOT_RETAINED:{identity}")
        check(stamp(order["submitted_at"]) <= at <= end, f"FILL_TIME_INVALID:{identity}")
        by_order[fill["order_id"]].append((at, qty, price, fee))
        chronological.append((at, 1 if order["side"] == "BUY" else -1, qty, identity))
    for identity, order in orders.items():
        quantity = sum(f[1] for f in by_order[identity])
        recorded = integer(order["filled_quantity"])
        check(0 <= recorded <= order["quantity"], f"ORDER_FILL_QUANTITY_INVALID:{identity}")
        check(quantity == recorded, f"FILL_LEDGER_MISMATCH:{identity}")
        check(order["status"] != "FILLED" or quantity == order["quantity"], f"MISSING_OR_PARTIAL_FILL:{identity}")
        check(order["status"] != "REJECTED" or quantity == 0, f"REJECTED_ORDER_HAS_FILLS:{identity}")
    daily_entries = defaultdict(int)
    for identity, order in orders.items():
        if order["leg"] == "ENTRY" and by_order[identity]:
            day = local_time(min(fill[0] for fill in by_order[identity])).date().isoformat()
            daily_entries[day] += 1
    for day, count in daily_entries.items():
        check(count <= 2, f"PAPER_DAILY_ENTRY_LIMIT_EXCEEDED:{day}")

    ledger_position = 0
    check(len({row[0] for row in chronological}) == len(chronological), "AMBIGUOUS_FILL_ORDER_AT_SHARED_TIMESTAMP")
    for at, direction, qty, identity in sorted(chronological):
        order = orders[fills[identity]["order_id"]]
        if order["leg"] == "ENTRY":
            check(ledger_position == 0, f"ENTRY_WHILE_POSITION_OPEN:{identity}")
        else:
            check(ledger_position * direction < 0 and qty <= abs(ledger_position), f"EXIT_DOES_NOT_CLOSE_EXISTING_POSITION:{identity}")
        ledger_position += direction * qty
        check(abs(ledger_position) <= 1, f"EXCESS_POSITION_EXPOSURE:{identity}")
    check(ledger_position == 0, "UNRESOLVED_END_POSITION_FROM_FILLS")
    snapshots = sorted(((stamp(p["at"]), integer(p["quantity"]), p) for p in positions.values()), key=lambda row: (row[0], row[2]["snapshot_id"]))
    check(len({s[0] for s in snapshots}) == len(snapshots), "DUPLICATE_POSITION_SNAPSHOT_TIME")
    check(bool(snapshots) and snapshots[0][0] == start, "MISSING_START_POSITION_SNAPSHOT")
    check(bool(snapshots) and snapshots[-1][0] == end, "MISSING_OR_STALE_END_POSITION_SNAPSHOT")
    for at, qty, p in snapshots:
        check(p["symbol"] == paper["symbol"], f"POSITION_CONTRACT_MISMATCH:{p['snapshot_id']}")
        check(start <= at <= end, f"POSITION_OUTSIDE_WINDOW:{p['snapshot_id']}")
        expected = sum(direction * count for ts, direction, count, _ in chronological if ts <= at)
        check(qty == expected, f"POSITION_FILL_LEDGER_MISMATCH:{p['snapshot_id']}")
    if snapshots:
        check(snapshots[0][1] == snapshots[-1][1] == 0, "WINDOW_NOT_FLAT_TO_FLAT")

    # Reconcile the broker's flat-to-flat cash ledger independently of matching simulation.
    # Missing fee or unsettled/unknown cash data must not be filled with a plug adjustment.
    cash_snapshots = unique(paper["cash_snapshots"], "snapshot_id")
    cash_flows = unique(paper["cash_flows"], "flow_id")
    cash = sorted((stamp(row["at"]), money(row["cash_usd"]), row["currency"])
                  for row in cash_snapshots.values())
    check(len(cash) == 2 and cash[0][0] == start and cash[-1][0] == end, "MISSING_EXACT_START_END_CASH_SNAPSHOTS")
    check(all(row[2] == "USD" for row in cash), "CASH_CURRENCY_NOT_USD")
    check(paper["cash_ledger_complete"] is True, "INCOMPLETE_OR_UNSETTLED_CASH_LEDGER")
    net_flows = Decimal("0")
    for identity, flow in cash_flows.items():
        at, amount = stamp(flow["at"]), money(flow["amount_usd"], signed=True)
        check(start < at <= end and flow["currency"] == "USD", f"CASH_FLOW_SCOPE_OR_CURRENCY_INVALID:{identity}")
        check(flow["kind"] in ("DEPOSIT", "WITHDRAWAL", "INTEREST", "NON_TRADE_ACCOUNT_FEE"), f"UNCLASSIFIED_CASH_FLOW:{identity}")
        if flow["kind"] in ("DEPOSIT", "INTEREST"):
            check(amount >= 0, f"CASH_FLOW_SIGN_INVALID:{identity}")
        if flow["kind"] in ("WITHDRAWAL", "NON_TRADE_ACCOUNT_FEE"):
            check(amount <= 0, f"CASH_FLOW_SIGN_INVALID:{identity}")
        check(source_reference(flow["source_reference"], "paper"), f"CASH_FLOW_SOURCE_MISSING_OR_NOT_RETAINED:{identity}")
        net_flows += amount
    known_fees = all(fill["fee_usd"] is not None for fill in fills.values())
    valid_fills = len(chronological) == len(fills)
    if len(cash) == 2 and known_fees and valid_fills and ledger_position == 0:
        gross = sum((-direction * qty * money(fills[identity]["price"], positive=True, tick=True) * POINT_VALUE
                     for _, direction, qty, identity in chronological), Decimal("0"))
        fees = sum((money(fill["fee_usd"]) for fill in fills.values()), Decimal("0"))
        expected_cash = cash[0][1] + gross - fees + net_flows
        report["cash_reconciliation"] = {
            "opening_cash_usd": str(cash[0][1]), "closing_cash_usd": str(cash[-1][1]),
            "gross_pnl_from_all_paper_fills_usd": str(gross), "fill_fees_usd": str(fees),
            "non_trade_cash_flows_usd": str(net_flows), "expected_closing_cash_usd": str(expected_cash),
            "unexplained_cash_difference_usd": str(cash[-1][1] - expected_cash),
        }
        check(cash[-1][1] == expected_cash, "CASH_LEDGER_MISMATCH")
        # Realized equity is only a lower bound on loss/drawdown while exposed.
        # A loss pause already breached on this observable bound must still block
        # the next entry; it cannot be excused by absent intratrade quotes.
        check((local_time(start).hour, local_time(start).minute) <= (9, 30),
              "DAY_START_CASH_NOT_ESTABLISHED_FOR_PAUSE_AUDIT")
        equity = peak = cash[0][1]
        day_start, current_day, daily_halt, account_halt = equity, None, False, False
        open_entry = None
        for at, direction, qty, identity in sorted(chronological):
            day = local_time(at).date().isoformat()
            if day != current_day:
                day_start, current_day, daily_halt = equity, day, False
            order = orders[fills[identity]["order_id"]]
            price = money(fills[identity]["price"], positive=True, tick=True)
            fee = money(fills[identity]["fee_usd"])
            if order["leg"] == "ENTRY":
                check(not daily_halt, f"ENTRY_AFTER_OBSERVED_DAILY_LOSS_PAUSE:{identity}")
                check(not account_halt, f"ENTRY_AFTER_OBSERVED_ACCOUNT_DRAWDOWN_PAUSE:{identity}")
                open_entry = (direction, price, qty)
                equity -= fee
            elif open_entry is not None:
                side, entry_price, entry_qty = open_entry
                equity += side * (price - entry_price) * POINT_VALUE * entry_qty - fee
                open_entry = None
            peak = max(peak, equity)
            daily_halt = daily_halt or equity <= day_start * Decimal("0.995")
            account_halt = account_halt or equity <= peak * Decimal("0.95")
        report["observed_cash_pause_audit"] = {
            "basis": "REALIZED_TRADING_EQUITY_EXCLUDING_NON_TRADE_CASH_FLOWS",
            "intratrade_marked_equity_and_full_pause_fidelity_established": False,
            "ending_trading_equity_usd": str(equity),
            "observed_account_pause_latched": account_halt,
        }
    else:
        check(False, "CASH_RECONCILIATION_NOT_ASSESSABLE")

    simulated_daily_entries = defaultdict(int)
    for identity, signal in signals.items():
        direction = integer(signal["direction"])
        if direction not in (-1, 1) or signal["decision"] not in ("ENTER", "SKIP"):
            raise EvidenceError(f"invalid_signal_direction_or_decision:{identity}")
        signal_time = stamp(signal["at"])
        check(start <= signal_time <= end, f"SIGNAL_OUTSIDE_WINDOW:{identity}")
        check(entry_window(signal_time), f"SIGNAL_OUTSIDE_FROZEN_ENTRY_WINDOW:{identity}")
        check(bool(signal["reason"]), f"MISSING_DECISION_REASON:{identity}")
        if identity in paper_decisions:
            decision = paper_decisions[identity]
            check(stamp(decision["at"]) == signal_time and integer(decision["direction"]) == direction,
                  f"SIGNAL_DETECTION_MISMATCH:{identity}")
            check(decision["decision"] == signal["decision"] and decision["reason"] == signal["reason"],
                  f"SIGNAL_DECISION_MISMATCH:{identity}")
        actual = by_signal[identity]
        for order in actual:
            check(stamp(order["submitted_at"]) >= signal_time, f"ORDER_PRECEDES_SIGNAL:{order['order_id']}")
            if order["leg"] == "ENTRY":
                age = stamp(order["reference_quote_at"]) - signal_time
                check(10**9 <= age <= 2 * 10**9, f"ENTRY_QUOTE_OUTSIDE_FROZEN_WINDOW:{order['order_id']}")
                check(entry_window(stamp(order["reference_quote_at"])), f"ENTRY_QUOTE_OUTSIDE_FROZEN_SESSION_WINDOW:{order['order_id']}")
            expected_side = "BUY" if direction * (1 if order["leg"] == "ENTRY" else -1) == 1 else "SELL"
            check(order["side"] == expected_side, f"ORDER_SIDE_MISMATCH:{order['order_id']}")
        if signal["decision"] == "SKIP":
            check(not actual, f"PAPER_ORDER_FOR_SKIPPED_SIGNAL:{identity}")
            check(signal["entry"] is None and signal["exit"] is None, f"SKIP_HAS_SIMULATED_FILLS:{identity}")
            continue
        day = local_time(signal_time).date().isoformat()
        simulated_daily_entries[day] += 1
        expected, observed = {}, {}
        for leg in ("ENTRY", "EXIT"):
            simfill = signal[leg.lower()]
            if simfill is None:
                check(False, f"MISSING_SIMULATED_{leg}:{identity}")
                continue
            expected[leg] = (stamp(simfill["at"]), money(simfill["price"], positive=True, tick=True), money(simfill["fee_usd"]))
            check(integer(simfill["quantity"], positive=True) == 1, f"SIMULATED_QUANTITY_NOT_ONE:{identity}:{leg}")
            check(signal_time <= expected[leg][0] <= end, f"SIMULATED_FILL_TIME_INVALID:{identity}:{leg}")
            leg_orders = [order for order in actual if order["leg"] == leg]
            # Canonical v1 has one entry and one exit order. Replacements are evidence to review, never silently coalesced.
            check(len(leg_orders) == 1, f"MISSING_OR_MULTIPLE_{leg}_ORDERS:{identity}")
            actual_fills = [fill for order in leg_orders for fill in by_order[order["order_id"]]]
            if sum(fill[1] for fill in actual_fills) != 1 or any(f[3] is None for f in actual_fills):
                check(False, f"MISSING_INCOMPLETE_OR_EXTRA_{leg}_FILLS:{identity}")
                continue
            observed[leg] = (max(fill[0] for fill in actual_fills),
                             sum(fill[1] * fill[2] for fill in actual_fills),
                             sum(fill[3] for fill in actual_fills))
        if len(observed) != 2 or len(expected) != 2:
            continue
        check(expected["EXIT"][0] > expected["ENTRY"][0], f"SIMULATED_EXIT_NOT_AFTER_ENTRY:{identity}")
        check(observed["EXIT"][0] > observed["ENTRY"][0], f"PAPER_EXIT_NOT_AFTER_ENTRY:{identity}")
        for order in actual:
            if order["leg"] == "EXIT":
                check(stamp(order["trigger_at"]) > observed["ENTRY"][0], f"EXIT_TRIGGER_NOT_AFTER_ENTRY_FILL:{identity}")
        values = {
            "signal_id": identity,
            "entry_adverse_difference_ticks": str(direction * (observed["ENTRY"][1] - expected["ENTRY"][1]) / TICK),
            "exit_adverse_difference_ticks": str(direction * (expected["EXIT"][1] - observed["EXIT"][1]) / TICK),
            "entry_time_difference_ms": str(Decimal(observed["ENTRY"][0] - expected["ENTRY"][0]) / 10**6),
            "exit_time_difference_ms": str(Decimal(observed["EXIT"][0] - expected["EXIT"][0]) / 10**6),
            "paper_fees_usd": str(sum(x[2] for x in observed.values())),
            "simulation_fees_usd": str(sum(x[2] for x in expected.values())),
        }
        for label, fills_ in (("paper", observed), ("simulation", expected)):
            values[f"{label}_net_pnl_usd"] = str(direction * (fills_["EXIT"][1] - fills_["ENTRY"][1]) * POINT_VALUE - sum(x[2] for x in fills_.values()))
        values["fee_difference_usd"] = str(Decimal(values["paper_fees_usd"]) - Decimal(values["simulation_fees_usd"]))
        values["net_pnl_difference_usd"] = str(Decimal(values["paper_net_pnl_usd"]) - Decimal(values["simulation_net_pnl_usd"]))
        report["matches"].append(values)
        if any(Decimal(value) != 0 for key, value in values.items() if "difference" in key):
            report["differences"].append(values)
    for day, count in simulated_daily_entries.items():
        check(count <= 2, f"SIMULATION_DAILY_ENTRY_LIMIT_EXCEEDED:{day}")
    check(bool(report["matches"]), "NO_COMPLETE_MATCHED_ROUND_TRIPS")
    report["counts"] = {"simulation_signals": len(signals), "paper_orders": len(orders),
                        "paper_fills": len(fills), "matched_round_trips": len(report["matches"])}
    report["blockers"] = sorted(set(report["blockers"]))


def read_json(path):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise EvidenceError(f"duplicate_json_key:{key}")
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=object_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(EvidenceError(f"nonfinite_json:{value}")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", type=Path)
    parser.add_argument("--simulation", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="New report file; existing files are never overwritten.")
    args = parser.parse_args()
    try:
        paper = read_json(args.paper) if args.paper else None
        sim = read_json(args.simulation) if args.simulation else None
        report = compare(paper, sim, paper_root=args.paper.parent if args.paper else None,
                         simulation_root=args.simulation.parent if args.simulation else None)
    except (ValueError, OSError) as exc:
        report = base_report()
        report["blockers"] = [f"INPUT_READ_FAILED:{type(exc).__name__}:{exc}"]
    report["created_at"] = datetime.now(timezone.utc).isoformat()
    report["inputs"] = {label: {"file": path.name, "sha256": digest(path)} if path and path.is_file() else None
                        for label, path in (("paper", args.paper), ("simulation", args.simulation))}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"comparison_status": report["comparison_status"], "live_readiness": "NOT_READY",
                      "blocker_count": len(report["blockers"]), "report": str(args.out)}))
    return 0 if report["comparison_status"] == "RECONCILED_FOR_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
