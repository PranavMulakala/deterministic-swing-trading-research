"""Dollars-first scorecard (owner's request, Oct 7, 2026): how a strategy feels week to week in money, with "what doing
nothing (SPY) would have made" as one line at the bottom instead of the headline.

  from research.scorecard_v1.scorecard import scorecard, spy_curve
  card = scorecard(curve, spy=spy_curve(curve))      # curve: [(YYYY-MM-DD, account value)], daily

Pure functions; no network.
"""
from __future__ import annotations

from datetime import date
import gzip
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPY_FILE = ROOT / "outputs/orb_play_data/SPY_all.json.gz"          # dividend-adjusted daily SPY, 2015-11 to 2026-10-02
GOAL = 1000.0


def _period_changes(curve, start_value, key):
    """Profit per period (the last value of each period minus the last value of the one before)."""
    ends = {}
    for d, v in curve:
        ends[key(d)] = (d, v)
    out, prev = [], start_value
    for k in sorted(ends):
        d, v = ends[k]
        out.append((k, d, v - prev))
        prev = v
    return out


def week_of(d):
    y, w, _ = date.fromisoformat(d).isocalendar()
    return f"{y}-W{w:02d}"


def month_of(d):
    return d[:7]


def scorecard(curve, start_value=None, spy=None, goal=GOAL):
    """Money first: total profit, profit per week, how many weeks reached the goal, the worst week and month, the worst
    drop from a high, plus the same numbers for `spy` (a curve over the same dates) if given."""
    if not curve:
        return None
    start = curve[0][1] if start_value is None else start_value
    weeks = _period_changes(curve, start, week_of)
    months = _period_changes(curve, start, month_of)
    w = [p for _, _, p in weeks]
    m = [p for _, _, p in months]
    peak, peak_day, worst, worst_from, worst_to = start, curve[0][0], 0.0, None, None
    for d, v in curve:
        if v > peak:
            peak, peak_day = v, d
        if v - peak < worst:
            worst, worst_from, worst_to = v - peak, peak_day, d
    streak = longest = 0
    for p in w:
        streak = streak + 1 if p < 0 else 0
        longest = max(longest, streak)
    worst_week = min(weeks, key=lambda x: x[2])
    worst_month = min(months, key=lambda x: x[2])
    card = {"from": curve[0][0], "to": curve[-1][0], "start": round(start), "end": round(curve[-1][1]),
            "profit": round(curve[-1][1] - start), "weeks": len(w),
            "avg_per_week": round(statistics.mean(w)), "median_week": round(statistics.median(w)),
            "weeks_up_pct": round(100 * sum(p > 0 for p in w) / len(w), 1),
            f"weeks_at_or_above_{int(goal)}": sum(p >= goal for p in w),
            f"weeks_at_or_above_{int(goal)}_pct": round(100 * sum(p >= goal for p in w) / len(w), 1),
            f"weeks_losing_{int(goal)}_or_more": sum(p <= -goal for p in w),
            "best_week": round(max(w)), "worst_week": round(worst_week[2]), "worst_week_ending": worst_week[1],
            "best_month": round(max(m)), "worst_month": round(worst_month[2]), "worst_month_is": worst_month[0],
            "months_up_pct": round(100 * sum(p > 0 for p in m) / len(m), 1),
            "worst_drop_dollars": round(worst), "worst_drop_from": worst_from, "worst_drop_to": worst_to,
            "longest_losing_weeks_in_a_row": longest}
    if spy:
        s = scorecard(spy, start, goal=goal)
        card["spy_same_dates"] = {k: s[k] for k in ("end", "profit", "avg_per_week", "weeks_up_pct",
                                                    f"weeks_at_or_above_{int(goal)}", "worst_week", "worst_month",
                                                    "worst_drop_dollars")}
    return card


def load_spy():
    with gzip.open(SPY_FILE, "rt") as f:
        b = json.load(f)
    return dict(zip(b["date"], (x[3] for x in b["bars"])))


def spy_curve(curve, start_value=None, spy=None):
    """SPY bought with the same starting money at the first day's close, valued on the strategy's dates."""
    spy = spy or load_spy()
    start = curve[0][1] if start_value is None else start_value
    days = [d for d, _ in curve if d in spy]
    if not days:
        return None
    base = spy[days[0]]
    return [(d, start * spy[d] / base) for d in days]
