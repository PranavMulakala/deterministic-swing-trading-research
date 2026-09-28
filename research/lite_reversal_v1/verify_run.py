"""Separate Decimal ledger/fill replay; deliberately does not import the engine.

Usage: .venv/bin/python -m research.lite_reversal_v1.verify_run RUN_DIRECTORY
"""
from datetime import datetime, timedelta
from decimal import Decimal as D, ROUND_FLOOR
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
NY = ZoneInfo("America/New_York")


def equal(actual, expected, label):
    if abs(D(actual) - D(expected)) > D("0.0000001"):
        raise ValueError(f"Independent replay mismatch: {label}")


def verify(directory: Path):
    raw = (directory / "results.json").read_bytes()
    result = json.loads(raw, parse_float=D)
    provenance = result["provenance"]
    paths = {"config": HERE / "config.json", "engine": HERE / "experiment.py",
             "spec": HERE / "SPEC.md", "snapshot": HERE.parent / "lite_2026" / "snapshot.json"}
    for name, path in paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != provenance[f"{name}_sha256"]:
            raise ValueError(f"Provenance mismatch: {name}")
    cfg = json.loads(paths["config"].read_text(), parse_float=D)
    snapshot = json.loads(paths["snapshot"].read_text(), parse_float=D)
    by_time = {datetime.fromisoformat(row["t"].replace("Z", "+00:00")).astimezone(NY):row
               for row in snapshot["intraday"]["LITE"]}
    sessions_checked = trades_checked = 0
    for run in result["runs"]:
        cash = cfg["initial_cash"]
        cost = D(run["cost_bps_per_side"]) / 10000
        trades = {t["date"]:t for t in run["trades"]}
        if len(trades) != len(run["trades"]):
            raise ValueError("Duplicate trade")
        for day in run["daily_ledger"]:
            sessions_checked += 1
            t = trades.get(day["date"])
            if t is None:
                equal(day["pnl"], 0, "no-trade P&L")
                equal(day["equity"], cash, "no-trade equity")
                if day["status"] == "filled":
                    raise ValueError("Missing trade")
                continue
            trades_checked += 1
            equal(t["equity_before"], cash, "cash before trade")
            q, stop, target = t["quantity"], t["stop"], t["target"]
            entry_time = datetime.fromisoformat(t["entry_time"])
            signal_time = datetime.fromisoformat(t["signal_time"])
            if entry_time != signal_time or entry_time.date().isoformat() != day["date"]:
                raise ValueError("Entry/signal timing mismatch")
            signal_bar = by_time[signal_time - timedelta(minutes=5)]
            s, target_net = stop*(1-cost), target*(1-cost)
            cap = min(signal_bar["c"]*(1+cfg["maximum_entry_gap_fraction"]),
                      (target_net+cfg["minimum_reward_risk"]*s)/(1+cfg["minimum_reward_risk"]))
            equal(t["entry_cap"], cap, "entry cap from completed signal bar")
            raw_entry = by_time[entry_time]["o"]
            equal(t["raw_entry"], raw_entry, "next bar open")
            if not stop < raw_entry < target or raw_entry*(1+cost) > cap + D("0.0000001"):
                raise ValueError("Non-executable modeled entry")
            scale = D(1) if run["share_mode"] == "whole" else D(1000000)
            expected_q = (min(cash/cap, cash*cfg["risk_fraction"]/(cap-s))*scale).to_integral_value(rounding=ROUND_FLOOR)/scale
            equal(q, expected_q, "pre-entry share sizing")
            equal(t["planned_risk"], q*(cap-s), "planned risk")
            debit = q*raw_entry*(1+cost)
            if debit > cash + D("0.0000001"):
                raise ValueError("Cash exceeded")
            when = entry_time
            while True:
                bar = by_time[when]
                penetration = target*(1+D(cfg["target_penetration_bps"])/10000)
                ambiguous = False
                if bar["o"] <= stop:
                    raw_exit, reason = bar["o"], "gap_stop"
                elif when.hour == 15 and when.minute == 55:
                    raw_exit, reason = bar["o"], "time"
                elif bar["o"] > penetration:
                    raw_exit, reason = target, "gap_target"
                elif bar["l"] <= stop:
                    raw_exit, reason = stop, "stop"
                    ambiguous = bar["h"] > penetration
                elif bar["h"] > penetration:
                    raw_exit, reason = target, "target"
                else:
                    when += timedelta(minutes=5)
                    continue
                break
            if when != datetime.fromisoformat(t["exit_bar_time"]) or reason != t["reason"] or ambiguous != t["ambiguous_stop_target"]:
                raise ValueError("First eligible exit mismatch")
            equal(t["raw_exit"], raw_exit, "exit reference")
            credit = q*raw_exit*(1-cost)
            pnl = credit-debit
            equal(t["entry_debit"], debit, "debit")
            equal(t["exit_credit"], credit, "credit")
            equal(t["pnl"], pnl, "net P&L")
            equal(t["modeled_costs"], q*cost*(raw_entry+raw_exit), "costs")
            equal(t["r_multiple"], pnl/(q*(cap-s)), "R multiple")
            cash += pnl
            equal(t["equity_after"], cash, "equity after trade")
            equal(day["pnl"], pnl, "daily P&L")
            equal(day["equity"], cash, "daily equity")
        equal(run["summary"]["final_cash"], cash, "terminal cash")
    return dict(status="PASS", method="separate Decimal ledger and first-eligible-exit replay",
                scenarios=len(result["runs"]), daily_rows=sessions_checked, trades=trades_checked,
                results_sha256=hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1])), indent=2))
