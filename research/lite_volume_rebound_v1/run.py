"""Deterministic offline LITE volume/rebound replay. Never connects to a broker."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from research.lite_funded_comparison_v1.run import D, ROOT, inputs

HERE = Path(__file__).resolve().parent
STARTING_CASH = D("10000")
SHARES = D("5")
WARMUP_SESSIONS = 20
COST_BPS = (0, 10, 25, 50)


def decision(bars, previous_20):
    """Return a 10:00 buy limit using only the six completed morning bars."""
    if len(previous_20) != WARMUP_SESSIONS:
        return None
    opening = D(bars[0].o)
    morning = bars[:6]
    if min(D(bar.l) for bar in morning) > opening * D("0.99"):
        return None
    if not D(morning[-3].c) < D(morning[-2].c) < D(morning[-1].c) < opening:
        return None
    prior_volumes = [sum((D(bar.v) for bar in prior[:6]), D(0)) for prior in previous_20]
    morning_volume = sum((D(bar.v) for bar in morning), D(0))
    baseline = sum(prior_volumes, D(0)) / WARMUP_SESSIONS
    if baseline <= 0 or morning_volume < D("1.5") * baseline:
        return None
    # The final completed close is known at 10:00 and remains below the open.
    return {"limit": D(morning[-1].c), "morning_volume": morning_volume,
            "prior_20_mean_volume": baseline}


def simulate(all_days, eligible_dates=None, cost_bps=10):
    """One cash-funded position; independent scenario begins flat."""
    if cost_bps not in COST_BPS or not all_days:
        raise ValueError("Invalid scenario")
    ordered = sorted(all_days)
    eligible = set(ordered if eligible_dates is None else eligible_dates)
    if not eligible or not eligible.issubset(all_days):
        raise ValueError("Invalid eligible dates")
    cost = D(cost_bps) / D(10000)
    cash = STARTING_CASH
    position = None
    counts = Counter()
    trades, daily, decisions = [], [], []
    for day_index, day in enumerate(ordered):
        if day not in eligible:
            continue
        bars = all_days[day]
        if len(bars) != 78:
            raise ValueError("Incomplete regular session")
        prior = [all_days[key] for key in ordered[max(0, day_index - WARMUP_SESSIONS):day_index]]
        candidate = decision(bars, prior)
        if candidate:
            counts["qualified_days"] += 1
            decisions.append({"date": day, "limit": str(candidate["limit"]),
                              "morning_volume": str(candidate["morning_volume"]),
                              "prior_20_mean_volume": str(candidate["prior_20_mean_volume"])})
        exited_today = False
        for index, bar in enumerate(bars):
            if position is not None and (day != position["entry_date"] or index > 6):
                position["lowest_later_low"] = min(position["lowest_later_low"], D(bar.l))
                # At/through the target is only a bar-based possible fill. Use
                # the target, even after a gap, rather than claiming price improvement.
                if D(bar.h) >= position["target"]:
                    exit_price = position["target"] * (1 - cost)
                    proceeds = SHARES * exit_price
                    cash += proceeds
                    trades.append({"entry_date": position["entry_date"], "exit_date": day,
                                   "exit_bar_index": index, "entry_price_with_cost": str(position["entry_price"]),
                                   "target": str(position["target"]), "net_exit_price": str(exit_price),
                                   "pnl": str(proceeds - position["debit"]),
                                   "lowest_later_low": str(position["lowest_later_low"])})
                    position = None
                    exited_today = True
            if index == 6 and candidate:
                if position is not None or exited_today:
                    counts["skipped_occupied"] += 1
                    continue
                limit = candidate["limit"]
                # Limit expires after this single next bar. A low through the
                # limit is a possible fill, not proof of queue execution.
                if D(bar.l) > limit:
                    counts["unfilled_limit"] += 1
                    continue
                fill_proxy = min(D(bar.o), limit)
                entry_price = fill_proxy * (1 + cost)
                target = D(bars[0].o)
                if target * (1 - cost) <= entry_price:
                    counts["skipped_not_net_profitable"] += 1
                    continue
                debit = SHARES * entry_price
                if debit > cash:
                    counts["skipped_cash"] += 1
                    continue
                cash -= debit
                position = {"entry_date": day, "target": target,
                            "entry_price": entry_price, "debit": debit,
                            "lowest_later_low": fill_proxy}
                counts["entries"] += 1
        mark = SHARES * D(bars[-1].c) * (1 - cost) if position else D(0)
        daily.append({"date": day, "cash": str(cash), "equity": str(cash + mark),
                      "holding": position is not None})
    peak = STARTING_CASH
    worst_drawdown = D(0)
    for row in daily:
        equity = D(row["equity"])
        peak = max(peak, equity)
        worst_drawdown = min(worst_drawdown, (equity / peak - 1) * 100)
    unresolved = None
    if position:
        estimated_value = SHARES * D(all_days[daily[-1]["date"]][-1].c) * (1 - cost)
        unresolved = {"entry_date": position["entry_date"], "target": str(position["target"]),
                      "entry_price_with_cost": str(position["entry_price"]),
                      "debit": str(position["debit"]), "estimated_exit_value": str(estimated_value),
                      "marked_pnl": str(estimated_value - position["debit"]),
                      "lowest_later_low": str(position["lowest_later_low"])}
    excursions = [((D(row["lowest_later_low"]) / D(row["entry_price_with_cost"])) - 1) * 100
                  for row in trades + ([unresolved] if unresolved else [])]
    return {"cost_bps_per_side": cost_bps, "first_session": daily[0]["date"],
            "last_session": daily[-1]["date"], "session_count": len(daily),
            "qualified_days": counts["qualified_days"],
            "skipped_occupied": counts["skipped_occupied"],
            "unfilled_limit": counts["unfilled_limit"],
            "skipped_not_net_profitable": counts["skipped_not_net_profitable"],
            "skipped_cash": counts["skipped_cash"], "entries": counts["entries"],
            "closed_trades": len(trades), "unresolved_positions": int(bool(unresolved)),
            "ending_marked_equity": daily[-1]["equity"],
            "net_marked_pnl": str(D(daily[-1]["equity"]) - STARTING_CASH),
            "worst_daily_drawdown_pct": str(worst_drawdown),
            "worst_observed_later_low_vs_entry_pct": str(min(excursions, default=D(0))),
            "unresolved": unresolved, "trades": trades, "decisions": decisions, "daily": daily}


def run():
    loaded, hashes = inputs()
    all_days = loaded["LITE"]
    cutoff = max(all_days)
    recent_start = (date.fromisoformat(cutoff) - timedelta(days=90)).isoformat()
    recent_dates = {day for day in all_days if day >= recent_start}
    return {"status": "OFFLINE_DEVELOPMENT_NOT_PAPER_OR_LIVE_ORDER_EVIDENCE",
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "protocol_sha256": hashlib.sha256((HERE / "PROTOCOL.md").read_bytes()).hexdigest(),
            "source_hashes": hashes, "data_through": cutoff,
            "recent_window_start": recent_start,
            "scenarios": [{"sample": sample, **simulate(all_days, dates, cost)}
                          for sample, dates in (("full", None), ("recent_90_calendar_days", recent_dates))
                          for cost in COST_BPS]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output path already exists")
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(args.output)
