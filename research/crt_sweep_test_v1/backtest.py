"""Backtest of pre-declared test #8, the 15-minute sweep-and-reclaim (output/CRT_SWEEP_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.crt_sweep_test_v1.backtest

Reads the bars saved by research/crt_sweep_test_v1/fetch.py and writes output/crt-sweep-test-results.json.
Research only. The short side reuses the long code on mirrored prices (high <-> -low, close -> -close), so every
rule is written once; slippage is added on absolute price so it points the right way in both mirrors.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import gzip
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

from research.crt_sweep_test_v1.fetch import SYMBOLS, path_for
from research.provenance_v1.provenance import same_bar_ambiguity, write_manifest

NY = ZoneInfo("America/New_York")
START_EQUITY, SLIP, RISK, MAX_WEIGHT = 100_000.0, 0.0001, 0.01, 1.0
OPEN_MIN, CLOSE_MIN, EXPIRY, LAST_SIGNAL_START = 570, 960, 30, 925  # 9:30, 16:00, 30 min, 15:25
HALVES = (("2016-2020", "2016-01-01", "2020-12-31"), ("2021-2026", "2021-01-01", "2026-12-31"))


def load(symbol):
    """{date: [{'m': minute-of-day start, 'o','h','l','c'}...]} for regular-session 5-minute bars."""
    with gzip.open(path_for(symbol), "rt") as handle:
        rows = json.load(handle)
    days = defaultdict(list)
    for r in rows:
        t = datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(NY)
        m = t.hour * 60 + t.minute
        if OPEN_MIN <= m < CLOSE_MIN:
            days[t.date().isoformat()].append({"m": m, "o": r["o"], "h": r["h"], "l": r["l"], "c": r["c"]})
    return dict(sorted(days.items()))


def mirror(day):
    return [{"m": b["m"], "o": -b["o"], "h": -b["l"], "l": -b["h"], "c": -b["c"]} for b in day]


def candles15(day):
    groups = defaultdict(list)
    for b in day:
        groups[(b["m"] - OPEN_MIN) // 15].append(b)
    return {k: {"start": OPEN_MIN + 15 * k, "o": g[0]["o"], "h": max(x["h"] for x in g), "l": min(x["l"] for x in g),
                "c": g[-1]["c"]} for k, g in groups.items()}


def day_trades(day, same_bar="stop"):
    """Long rules 1-7 on one day of (possibly mirrored) bars. Returns trades in mirrored space."""
    candles, trades, free_at = candles15(day), [], 0
    for k in sorted(candles):
        c1, c2 = candles[k], candles.get(k + 1)
        if c2 is None:
            continue
        c2_end = c2["start"] + 15
        if c2_end < free_at:
            continue
        if not (c2["l"] < c1["l"] and c1["l"] <= c2["c"] <= c1["h"] and c2["h"] <= c1["h"]):
            continue
        line = c2["h"]
        window = [i for i, b in enumerate(day) if c2_end <= b["m"] < c2_end + EXPIRY and b["m"] <= LAST_SIGNAL_START]
        signal = next((i for i in window if day[i]["c"] > line), None)
        if signal is None:
            continue
        entry, stop, target = day[signal]["c"], day[signal]["l"], c1["h"]
        if not (target > entry and stop < entry):
            continue
        after = day[signal + 1:]
        exit_px, reason, exit_i = None, None, None
        for j, b in enumerate(after):
            hit_stop, hit_target = b["l"] <= stop, b["h"] >= target
            if hit_stop and hit_target:
                exit_px, reason = (stop, "stop_same_bar") if same_bar == "stop" else (target, "target_same_bar")
            elif hit_stop:
                exit_px, reason = stop, "stop"
            elif hit_target:
                exit_px, reason = target, "target"
            if reason:
                exit_i = signal + 1 + j
                break
        if reason is None:
            exit_i = len(day) - 1
            exit_px, reason = day[exit_i]["c"], "close"
        trades.append({"c1_start": c1["start"], "entry_m": day[signal]["m"], "exit_m": day[exit_i]["m"],
                       "entry": entry, "stop": stop, "target": target, "exit": exit_px, "reason": reason,
                       "bars_after": [{"h": b["h"], "l": b["l"], "c": b["c"]} for b in after]})
        free_at = day[exit_i]["m"] + 5
    return trades


def up(x, frac):
    return x + frac * abs(x)


def down(x, frac):
    return x - frac * abs(x)


def simulate(days, side, slip=SLIP, same_bar="stop"):
    sign, equity, trades, curve = (1 if side == "long" else -1), START_EQUITY, [], []
    for date, day in days.items():
        bars = day if side == "long" else mirror(day)
        for t in day_trades(bars, same_bar):
            fill, out = up(t["entry"], slip), down(t["exit"], slip)
            risk = fill - t["stop"]
            shares = math.floor(min(RISK * equity / risk, MAX_WEIGHT * equity / abs(fill))) if risk > 0 else 0
            if shares < 1:
                continue
            pnl = shares * (out - fill)
            equity += pnl
            trades.append({"date": date, "side": side, "entry_time": f"{t['entry_m'] // 60}:{t['entry_m'] % 60:02d}",
                           "exit_time": f"{t['exit_m'] // 60}:{t['exit_m'] % 60:02d}", "shares": shares,
                           "entry": round(sign * t["entry"], 4), "stop": round(sign * t["stop"], 4),
                           "target": round(sign * t["target"], 4), "exit": round(sign * t["exit"], 4),
                           "reason": t["reason"], "pnl": pnl, "r_multiple": pnl / (shares * risk),
                           "_amb": {"stop": t["stop"], "target": t["target"], "bars": t["bars_after"]}})
        curve.append((date, equity))
    return trades, curve


def drawdown(values):
    peak, worst = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst


def benchmark(spy_days):
    closes = [(d, bars[-1]["c"]) for d, bars in spy_days.items()]
    years = len(closes) / 252
    total = closes[-1][1] / closes[0][1]
    cagr = total ** (1 / years) - 1
    dd = drawdown([c for _, c in closes])
    return {"total_return_pct": round((total - 1) * 100, 1), "cagr_pct": round(cagr * 100, 2),
            "max_drawdown_pct": round(dd * 100, 1), "cagr_over_dd": round(cagr / abs(dd), 3)}


def summarize(trades, curve, bench):
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gain, loss = sum(t["pnl"] for t in wins), -sum(t["pnl"] for t in losses)
    value = dict(curve)
    dates = [d for d, _ in curve]
    years = len(dates) / 252
    final = curve[-1][1]
    cagr = (final / START_EQUITY) ** (1 / years) - 1
    dd = drawdown([START_EQUITY] + [e for _, e in curve])

    def change(a, b):
        inside = [d for d in dates if a <= d <= b]
        before = [d for d in dates if d < inside[0]]
        return value[inside[-1]] / (value[before[-1]] if before else START_EQUITY) - 1

    halves = {name: round(change(a, b) * 100, 1) for name, a, b in HALVES}
    by_year = defaultdict(float)
    for t in trades:
        by_year[t["date"][:4]] += t["pnl"]
    targets = sum(1 for t in trades if t["reason"].startswith("target"))
    result = {
        "trades": len(trades), "trades_per_year": round(len(trades) / years, 1),
        "target_hit_rate_pct": round(100 * targets / max(len(trades), 1), 1),
        "win_rate_pct": round(100 * len(wins) / max(len(trades), 1), 1),
        "avg_win_usd": round(gain / max(len(wins), 1)), "avg_loss_usd": round(loss / max(len(losses), 1)),
        "avg_r_multiple": round(sum(t["r_multiple"] for t in trades) / max(len(trades), 1), 3),
        "exit_reasons": dict(Counter(t["reason"] for t in trades)),
        "profit_factor": round(gain / loss, 3) if loss else None,
        "final_equity": round(final), "total_return_pct": round((final / START_EQUITY - 1) * 100, 1),
        "cagr_pct": round(cagr * 100, 2), "max_drawdown_pct": round(dd * 100, 1),
        "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None, "halves_return_pct": halves,
        "pnl_by_year": {y: round(v) for y, v in sorted(by_year.items())},
        "same_bar_ambiguity": same_bar_ambiguity([t["_amb"] for t in trades]),
    }
    checks = {"A1_profit_factor_at_least_1.3": (result["profit_factor"] or 0) >= 1.3,
              "A2_profitable_in_both_halves": all(v > 0 for v in halves.values()),
              "A3_max_drawdown_at_most_25pct": result["max_drawdown_pct"] >= -25.0,
              "B1_drawdown_5pts_smaller_than_spy": result["max_drawdown_pct"] >= bench["max_drawdown_pct"] + 5,
              "B2_cagr_over_dd_beats_spy": (result["cagr_over_dd"] or -9) > bench["cagr_over_dd"]}
    result["checks"] = checks
    result["passes"] = all(checks.values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/crt-sweep-test-results.json")
    args = parser.parse_args()
    data = {s: load(s) for s in SYMBOLS}
    bench = benchmark(data["SPY"])
    out = {"plan": "output/CRT_SWEEP_TEST_PLAN_20261005.md", "spy_buy_hold": bench, "results": {}}
    for symbol in SYMBOLS:
        days = data[symbol]
        out["results"][symbol] = {"days": len(days), "first_day": next(iter(days)), "last_day": list(days)[-1]}
        for side in ("long", "short"):
            trades, curve = simulate(days, side)
            main_result = summarize(trades, curve, bench)
            gross = summarize(*simulate(days, side, slip=0.0), bench)
            target_first = summarize(*simulate(days, side, same_bar="target"), bench)
            main_result["before_costs"] = {k: gross[k] for k in ("profit_factor", "total_return_pct", "win_rate_pct")}
            main_result["same_bar_counted_as_target"] = {k: target_first[k] for k in
                                                         ("profit_factor", "total_return_pct", "target_hit_rate_pct")}
            main_result["trade_list"] = [{k: v for k, v in t.items() if k != "_amb"} for t in trades]
            out["results"][symbol][side] = main_result
    out["verdict_pass"] = all(out["results"][s]["long"]["passes"] for s in SYMBOLS)
    Path(args.output).write_text(json.dumps(out, indent=1) + "\n")
    write_manifest(args.output, code=["research/crt_sweep_test_v1/backtest.py", "research/crt_sweep_test_v1/fetch.py"],
                   data=[str(path_for(s)) for s in SYMBOLS], params={"slip": SLIP, "risk": RISK, "expiry_min": EXPIRY})
    headline = {s: {side: {k: v for k, v in out["results"][s][side].items() if k != "trade_list"}
                    for side in ("long", "short")} for s in SYMBOLS}
    print(json.dumps({"spy_buy_hold": bench, "verdict_pass": out["verdict_pass"], **headline}, indent=1))


if __name__ == "__main__":
    main()
