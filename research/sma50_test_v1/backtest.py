"""Backtest of the pre-declared 50-day SMA rule on SPY (output/SMA50_TEST_PLAN_20260930.md). Research only.

  PYTHONPATH=src:. .venv/bin/python -m research.sma50_test_v1.backtest

Reads outputs/breakout_data/SPY.csv.gz and writes output/sma50-test-results.json.
The trade loop (simulate) and the daily-factor calculation (replay) are written separately and must agree (plan check 2).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path

from research.breakout_test_v1.backtest import HALVES, load, sma

ROOT = Path(__file__).resolve().parents[2]
START_EQUITY, COST, LENGTH = 100_000.0, 0.001, 50
ROUGH_PATCHES = (("late 2018", "2018-09-20", "2018-12-31"), ("early 2020", "2020-02-19", "2020-04-30"),
                 ("2022", "2022-01-03", "2022-12-30"))


def signals(close, length=LENGTH):
    """Rules 1-4: +1 = be long after this close, -1 = be flat, 0 = no change (warm-up, or close == SMA)."""
    avg = sma(close, length)
    return [0 if a is None or c == a else (1 if c > a else -1) for c, a in zip(close, avg)]


def simulate(bars, length=LENGTH, cost=COST, start=START_EQUITY):
    """Rules 2-6, trade by trade. Returns (trades, curve); the first curve day is the first possible fill day."""
    o, c, d = bars["open"], bars["close"], bars["date"]
    want = signals(c, length)
    first = length  # day after the 50th bar
    cash, shares, pending, entry = start, 0.0, want[first - 1], None
    trades, curve = [], []
    for t in range(first, len(c)):
        if pending == 1 and shares == 0:
            shares, entry = cash / (o[t] * (1 + cost)), {"entry_date": d[t], "entry_price": o[t], "cost_basis": cash}
            cash = 0.0
        elif pending == -1 and shares > 0:
            cash, shares = shares * o[t] * (1 - cost), 0.0
            trades.append(close_trade(entry, d[t], o[t], cash))
        held = shares > 0
        if t == len(c) - 1 and held:  # still open on the last day: close at the close for the statistics
            cash, shares = shares * c[t] * (1 - cost), 0.0
            trades.append({**close_trade(entry, d[t], c[t], cash), "open_at_end": True})
        curve.append((d[t], cash + shares * c[t], held))
        pending = want[t]
    return trades, curve


def close_trade(entry, day, price, proceeds):
    pnl = proceeds - entry["cost_basis"]
    return {**{k: entry[k] for k in ("entry_date", "entry_price")}, "exit_date": day, "exit_price": price,
            "pnl": pnl, "return_pct": 100 * pnl / entry["cost_basis"]}


def replay(bars, length=LENGTH, cost=COST, start=START_EQUITY):
    """Plan check 2: the same rule as daily growth factors, with its own SMA and position series."""
    o, c = bars["open"], bars["close"]
    avg = [None] * (length - 1) + [sum(c[i - length + 1:i + 1]) / length for i in range(length - 1, len(c))]
    held, value = False, start
    for t in range(length, len(c)):
        a = avg[t - 1]
        target = held if c[t - 1] == a else c[t - 1] > a
        if target and not held:
            value *= c[t] / (o[t] * (1 + cost))
        elif held and not target:
            value *= o[t] * (1 - cost) / c[t - 1]
        elif held:
            value *= c[t] / c[t - 1]
        held = target
    return value * (1 - cost) if held else value


def buy_hold(bars, first=LENGTH, cost=COST, start=START_EQUITY):
    shares = start / (bars["open"][first] * (1 + cost))
    curve = [(d, shares * x, True) for d, x in zip(bars["date"][first:], bars["close"][first:])]
    curve[-1] = (curve[-1][0], curve[-1][1] * (1 - cost), True)
    return curve


def max_drawdown(curve, a="0000", b="9999"):
    peak, worst = None, 0.0
    for d, value, _ in curve:
        if a <= d <= b:
            peak = value if peak is None else max(peak, value)
            worst = min(worst, value / peak - 1)
    return worst


def value_on(curve, day):
    """Account value at the last close on or before `day`."""
    return [v for d, v, _ in curve if d <= day][-1]


def stats(curve, start=START_EQUITY):
    final, first, last = curve[-1][1], curve[0][0], curve[-1][0]
    years = (date.fromisoformat(last) - date.fromisoformat(first)).days / 365.25
    cagr = (final / start) ** (1 / years) - 1
    dd = max_drawdown(curve)
    end_2020 = value_on(curve, "2020-12-31")
    by_year, prev = {}, start
    for y in sorted({d[:4] for d, _, _ in curve}):
        v = value_on(curve, f"{y}-12-31")
        by_year[y], prev = round(100 * (v / prev - 1), 1), v
    return {"final_value": round(final), "total_return_pct": round(100 * (final / start - 1), 1),
            "cagr_pct": round(100 * cagr, 2), "max_drawdown_pct": round(100 * dd, 1),
            "cagr_per_drawdown": round(cagr / abs(dd), 3) if dd else None,
            "halves_pnl_usd": {HALVES[0][0]: round(end_2020 - start), HALVES[1][0]: round(final - end_2020)},
            "year_return_pct": by_year,
            "rough_patch_drawdown_pct": {n: round(100 * max_drawdown(curve, a, b), 1) for n, a, b in ROUGH_PATCHES},
            "pct_days_invested": round(100 * sum(1 for *_, h in curve if h) / len(curve), 1)}


def summarize(trades, curve, bench):
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gain, loss = sum(t["pnl"] for t in wins), -sum(t["pnl"] for t in losses)
    rule, hold = stats(curve), stats(bench)
    years = (date.fromisoformat(curve[-1][0]) - date.fromisoformat(curve[0][0])).days / 365.25
    rule.update({"trades": len(trades), "trades_per_year": round(len(trades) / years, 1),
                 "win_rate_pct": round(100 * len(wins) / len(trades), 1) if trades else 0.0,
                 "profit_factor": round(gain / loss, 2) if loss else None,
                 "avg_win_usd": round(gain / len(wins)) if wins else 0, "avg_loss_usd": round(loss / len(losses)) if losses else 0,
                 "avg_win_pct": round(sum(t["return_pct"] for t in wins) / max(len(wins), 1), 2),
                 "avg_loss_pct": round(sum(t["return_pct"] for t in losses) / max(len(losses), 1), 2)})
    a = {"1_profit_factor_at_least_1.3": (rule["profit_factor"] or 0) >= 1.3,
         "2_profitable_in_both_halves": all(v > 0 for v in rule["halves_pnl_usd"].values()),
         "3_max_drawdown_at_most_25pct": rule["max_drawdown_pct"] >= -25.0}
    b = {"1_drawdown_at_least_5_points_smaller": rule["max_drawdown_pct"] - hold["max_drawdown_pct"] >= 5.0,
         "2_better_cagr_per_drawdown": (rule["cagr_per_drawdown"] or 0) > (hold["cagr_per_drawdown"] or 0)}
    return {"rule": rule, "buy_hold": hold, "verdict_a": {**a, "passes": all(a.values())},
            "verdict_b": {**b, "passes": all(b.values())}}


def data_consistency(spy):
    """Plan check 3: reproduce the pullback test's SPY buy-and-hold figure over its own date range."""
    path = ROOT / "output/pullback-test-results.json"
    old = json.loads(path.read_text())["long"]
    first = old["equity_curve"][0][0]
    close = dict(zip(spy["date"], spy["close"]))
    ours = round((close[spy["date"][-1]] / close[first] - 1) * 100, 1)
    return {"from": first, "ours_pct": ours, "pullback_test_pct": old["spy_buy_hold_return_pct"],
            "passes": ours == old["spy_buy_hold_return_pct"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/sma50-test-results.json")
    args = parser.parse_args()
    spy = load("SPY")
    trades, curve = simulate(spy)
    bench = buy_hold(spy)
    second = replay(spy)
    checks = {"2_two_calculations_agree": {"trade_loop": round(curve[-1][1], 2), "daily_factors": round(second, 2),
                                           "passes": abs(curve[-1][1] - second) <= 1.0},
              "3_data_consistency": data_consistency(spy)}
    result = {"plan": "output/SMA50_TEST_PLAN_20260930.md", "first_day": curve[0][0], "last_day": curve[-1][0],
              "engine_checks": checks, **summarize(trades, curve, bench)}
    (ROOT / args.output).write_text(json.dumps({**result, "trade_list": trades,
                                                "equity_curve": [[d, round(v, 2), h] for d, v, h in curve]}, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
