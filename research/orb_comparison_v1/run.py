"""Run the frozen development comparison offline and retain every result."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
from statistics import mean

from . import engine as e
from . import verify as v


def percentile(values, fraction):
    values = sorted(values)
    index = (len(values)-1)*fraction
    left = int(index)
    right = min(left+1, len(values)-1)
    return values[left]+(index-left)*(values[right]-values[left])


def paired(a, b, spec):
    if not a["complete"] or not b["complete"]:
        return {"status": "unavailable_unresolved_primary_ledger", "net_return_difference": None, "mean_daily_difference_ci": None}
    if [r["day"] for r in a["daily"]] != [r["day"] for r in b["daily"]]:
        raise ValueError("Unpaired daily observations")
    difference = [float(y["return"]-x["return"]) for x, y in zip(a["daily"], b["daily"])]
    cfg = spec["uncertainty"]
    size = cfg["paired_block_bootstrap_sessions"]
    if len(difference) < size:
        return {"status": "too_few_sessions", "net_return_difference": b["net_return"]-a["net_return"], "mean_daily_difference_ci": None}
    rng = random.Random(cfg["seed"])
    samples = []
    for _ in range(cfg["resamples"]):
        sample = []
        while len(sample) < len(difference):
            first = rng.randrange(len(difference)-size+1)
            sample.extend(difference[first:first+size])
        samples.append(mean(sample[:len(difference)]))
    alpha = (1-cfg["confidence_level"])/2
    return {"status": "computed_development_only", "net_return_difference": b["net_return"]-a["net_return"],
            "mean_daily_difference": mean(difference), "mean_daily_difference_ci": [percentile(samples, alpha), percentile(samples, 1-alpha)]}


def stats(run):
    trades = run["trades"]
    pnl = [t["pnl"] for t in trades]
    wins, losses = [x for x in pnl if x > 0], [x for x in pnl if x < 0]
    groups = {}
    for label in ("symbol", "month"):
        out = defaultdict(lambda: {"trades": 0, "pnl": e.ZERO})
        for t in trades:
            key = t["symbol"] if label == "symbol" else t["entry_time"].strftime("%Y-%m")
            out[key]["trades"] += 1
            out[key]["pnl"] += t["pnl"]
        groups[label] = dict(out)
    return {"complete": run["complete"], "trades": len(pnl), "terminal_equity": run["terminal_equity"], "net_return": run["net_return"],
            "completed_trade_expectancy": sum(pnl, e.ZERO)/len(pnl) if pnl else None,
            "completed_trade_win_rate": len(wins)/len(pnl) if pnl else None,
            "average_winner": sum(wins, e.ZERO)/len(wins) if wins else None,
            "average_loser": sum(losses, e.ZERO)/len(losses) if losses else None,
            "worst_completed_trade": min(pnl) if pnl else None, "drawdown_observed": run["observed_marked_drawdown"],
            "cash_occupancy_observed": run["mean_deployed_dollars_observed"]/run["initial_cash"],
            "position_minutes_observed": run["position_minutes_observed"], "groups": groups,
            "status_counts": run["status_counts"], "unresolved": run["unresolved"], "halt_count": run["halt_count"]}


def audit_ledger(run, spec=None):
    cash, receivables, positions = run["initial_cash"], e.ZERO, {}
    risks = {}
    last_stamp = None
    last_exit_day = None
    for event in run["events"]:
        stamp = event["time"]
        if last_stamp is not None and stamp < last_stamp: raise AssertionError("Noncausal event sequence")
        last_stamp = stamp
        if event["type"] == "settle":
            if event["amount"] != receivables: raise AssertionError("Settlement mismatch")
            if last_exit_day is not None and stamp.date() <= last_exit_day: raise AssertionError("Same-day settlement")
            cash += receivables
            receivables = e.ZERO
        elif event["type"] == "entry":
            symbol = event["symbol"]
            if symbol in positions or type(event["qty"]) is not int or event["qty"] <= 0:
                raise AssertionError("Invalid position creation")
            cost = event["qty"]*event["entry"]+event["entry_fee"]
            if cost != event["cost"]: raise AssertionError("Entry accounting mismatch")
            cash -= cost
            positions[symbol] = event["qty"]
            risks[symbol] = event["planned_risk"]
            if spec is not None:
                cfg = spec["portfolio"]
                slip = e.D(run["slippage_bps"])/10000
                fee = e.D(spec["bar_proxy"]["additional_fee_bps_per_side"])/10000
                stop_fill = event["stop"]*(1-slip)
                expected_risk = event["qty"]*(event["entry"]-stop_fill+fee*(event["entry"]+stop_fill))
                if expected_risk != event["planned_risk"]: raise AssertionError("Planned risk mismatch")
                if event["planned_risk"] > event["entry_equity"]*e.D(cfg["risk_fraction_per_entry"]):
                    raise AssertionError("Per-entry risk exceeded")
                if sum(risks.values(), e.ZERO) > event["entry_equity"]*e.D(cfg["max_aggregate_planned_risk_fraction"]):
                    raise AssertionError("Aggregate risk exceeded")
                if len(positions) > cfg["max_positions"]: raise AssertionError("Position cap exceeded")
        elif event["type"] == "exit":
            if positions.pop(event["symbol"]) != event["qty"]: raise AssertionError("Exit quantity mismatch")
            risks.pop(event["symbol"])
            last_exit_day = stamp.date()
            proceeds = event["qty"]*event["price"]-event["fee"]
            if proceeds != event["proceeds"]: raise AssertionError("Exit accounting mismatch")
            receivables += proceeds
        else:
            raise AssertionError("Unknown event")
        if cash < 0: raise AssertionError("Cash reuse or leverage")
    if cash != run["settled_cash"] or receivables != run["unsettled_cash"]:
        raise AssertionError("Ending cash differs from replay")
    if positions != {p["symbol"]: p["qty"] for p in run["open_positions"]}:
        raise AssertionError("Open position mismatch")
    if run["complete"] and (positions or abs(cash+receivables-run["terminal_equity"]) > e.D("1e-20")):
        raise AssertionError("Terminal accounting mismatch")
    return {"status": "passed", "events_replayed": len(run["events"]), "closed_trades": len(run["trades"]),
            "open_positions_preserved": len(positions)}


def run_all(folder, output):
    root = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=False)
    spec, sessions, bars, coverage = e.load(folder)
    action_pin = json.loads((root/"RUN_INPUTS.json").read_text())
    action_path = folder/action_pin["path_relative_to_frozen_data"]
    if v.sha(action_path) != action_pin["sha256"]: raise ValueError("Action snapshot changed")
    actions = e.action_dates(json.loads(action_path.read_text()), spec["symbols"])
    prepared = e.prepare(spec, sessions, bars, actions)
    matched = {d for d in prepared if all(e.full(bars[s, m][d], *sessions[d], m) for s in spec["symbols"] for m in (1, 5))}
    results, summaries, comparisons, audits = {}, {}, {}, {}
    costs = [spec["bar_proxy"]["primary_slippage_bps_per_side"], spec["bar_proxy"]["stress_slippage_bps_per_side"]]
    for bps in costs:
        scenarios = [("primary", None, None), ("matched_complete_days_diagnostic", None, matched)]
        scenarios += [(f"omit_{s}", [x for x in spec["symbols"] if x != s], None) for s in spec["symbols"]]
        for scenario, symbols, allowed in scenarios:
            pair = []
            for arm in ("A", "B"):
                key = f"{scenario}_{bps}bps_{arm}"
                result = e.replay(spec, sessions, bars, prepared, arm, bps, symbols, allowed)
                audits[key] = audit_ledger(result, spec)
                results[key] = result
                summaries[key] = stats(result)
                pair.append(result)
            comparisons[f"{scenario}_{bps}bps"] = paired(*pair, spec) if scenario == "primary" else {
                "status": "computed" if all(x["complete"] for x in pair) else "unavailable_unresolved_ledger",
                "net_return_difference": pair[1]["net_return"]-pair[0]["net_return"] if all(x["complete"] for x in pair) else None}
    reasons = []
    for bps in costs:
        contrast = comparisons[f"primary_{bps}bps"]
        if contrast["net_return_difference"] is None: reasons.append(f"{bps}bps_primary_unresolved")
        elif contrast["net_return_difference"] <= 0: reasons.append(f"{bps}bps_no_positive_portfolio_improvement")
        ci = contrast["mean_daily_difference_ci"]
        if ci is None or ci[0] <= 0: reasons.append(f"{bps}bps_uncertainty_not_favorable")
        for s in spec["symbols"]:
            diff = comparisons[f"omit_{s}_{bps}bps"]["net_return_difference"]
            if diff is None or diff <= 0: reasons.append(f"{bps}bps_omit_{s}_not_robust")
        for arm in ("A", "B"):
            if any(k.startswith("unknown") for k in results[f"primary_{bps}bps_{arm}"]["status_counts"]):
                reasons.append(f"{bps}bps_{arm}_unknown_pattern")
    controls = {}
    eval_days = list(prepared)
    calendar_days = list(sessions)
    previous_day = calendar_days[calendar_days.index(eval_days[0])-1]
    for symbol in spec["controls"]:
        daily_returns = []
        for day in eval_days:
            ordered = [bars[symbol,5][day][t] for t in sorted(bars[symbol,5][day])]
            daily_returns.append(e.D(ordered[-1]["c"])/e.D(ordered[0]["o"])-1)
        last_close = e.daily(bars[symbol,5][eval_days[-1]])["close"]
        previous_close = e.daily(bars[symbol,5][previous_day])["close"]
        controls[symbol] = {"raw_close_price_return":last_close/previous_close-1,
                            "mean_regular_session_open_to_close_return":sum(daily_returns,e.ZERO)/len(daily_returns),
                            "label":"descriptive_raw_price_control_not_total_return_or_costed_portfolio"}
    report = {"verdict": "DEVELOPMENT_CRITERIA_MET_NOT_EXECUTION_READY" if not reasons else "NOT_ESTABLISHED",
              "reasons": reasons, "comparison": comparisons, "summaries": summaries, "ledger_audits": audits,
              "matched_complete_days": sorted(matched), "matched_excluded_days": [d for d in prepared if d not in matched],
              "action_evidence": action_pin["evidence_level"], "coverage": {k: coverage[k] for k in ("calendar_sessions", "evaluation_sessions", "warmup_sessions")},
              "provenance": {"freeze_sha256": v.sha(root/"FREEZE.json"), "data_manifest_sha256": v.sha(folder/"manifest.json"),
                             "actions_sha256": v.sha(action_path), "engine_sha256": v.sha(root/"engine.py"),
                             "runner_sha256": v.sha(__file__), "notes_sha256": v.sha(root/"IMPLEMENTATION_NOTES.md")},
              "controls": controls, "execution_quality": "quotes_halts_partial_fills_and_receipt_latency_unvalidated", "news_used": False}
    for name, value in (("results.json", results), ("prepared.json", prepared), ("report.json", report)):
        with (output/name).open("x") as handle:
            json.dump(value, handle, default=e.encode, indent=2, allow_nan=False)
            handle.write("\n")
    print(json.dumps({"verdict": report["verdict"], "reasons": reasons,
                      "primary": {k: v for k,v in summaries.items() if k.startswith("primary")},
                      "matched_days": len(matched)}, default=e.encode, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parent/"runs/sip-20260907-02")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_all(args.data, args.output)
