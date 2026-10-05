"""Backtest of pre-declared test #9, the 1-hour CRT (output/CRT_1H_TEST_PLAN_20261005.md). Research only.

  PYTHONPATH=src:. .venv/bin/python -m research.crt_1h_test_v1.backtest

Reuses test #8's data (outputs/crt_sweep_data/), loader, sizing and summary; only the candle size, entry window,
stop and target differ. Writes output/crt-1h-test-results.json and its provenance manifest.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics

from research.crt_sweep_test_v1.backtest import (MAX_WEIGHT, RISK, SLIP, START_EQUITY, benchmark, down, load,
                                                 mirror, summarize, up)
from research.crt_sweep_test_v1.fetch import SYMBOLS, path_for
from research.provenance_v1.provenance import write_manifest

OPEN_MIN, HOUR, WINDOW, LAST_SIGNAL_START = 570, 60, 60, 925  # 9:30-aligned hours, 60-min entry window, 15:25


def candles60(day):
    """Full 9:30-aligned hourly candles only (the bar starting at start+55 must exist)."""
    groups = defaultdict(list)
    for b in day:
        groups[(b["m"] - OPEN_MIN) // HOUR].append(b)
    out = {}
    for k, g in groups.items():
        start = OPEN_MIN + HOUR * k
        if g[-1]["m"] == start + HOUR - 5 and start + HOUR <= 960:
            out[k] = {"start": start, "o": g[0]["o"], "h": max(x["h"] for x in g), "l": min(x["l"] for x in g),
                      "c": g[-1]["c"]}
    return out


def day_trades(day, same_bar="stop"):
    candles, trades, free_at = candles60(day), [], 0
    for k in sorted(candles):
        c1, c2 = candles[k], candles.get(k + 1)
        if c2 is None:
            continue
        c2_end = c2["start"] + HOUR
        if c2_end < free_at:
            continue
        if not (c2["l"] < c1["l"] and c1["l"] <= c2["c"] <= c1["h"] and c2["h"] <= c1["h"]):
            continue
        window = [i for i, b in enumerate(day) if c2_end <= b["m"] < c2_end + WINDOW and b["m"] <= LAST_SIGNAL_START]
        signal = next((i for i in window if day[i]["c"] > c2["h"]), None)
        if signal is None:
            continue
        entry, stop, target = day[signal]["c"], c2["l"], c1["h"]
        if not (target > entry > stop):
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
        trades.append({"entry_m": day[signal]["m"], "exit_m": day[exit_i]["m"], "entry": entry, "stop": stop,
                       "target": target, "exit": exit_px, "reason": reason,
                       "bars_after": [{"h": b["h"], "l": b["l"], "c": b["c"]} for b in after]})
        free_at = day[exit_i]["m"] + 5
    return trades


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


def distances(trades):
    tg = [abs(t["target"] - t["entry"]) / t["entry"] * 100 for t in trades]
    st = [abs(t["entry"] - t["stop"]) / t["entry"] * 100 for t in trades]
    return {"median_target_pct": round(statistics.median(tg), 3), "median_stop_pct": round(statistics.median(st), 3),
            "median_reward_to_risk": round(statistics.median(a / b for a, b in zip(tg, st) if b > 0), 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/crt-1h-test-results.json")
    args = parser.parse_args()
    data = {s: load(s) for s in SYMBOLS}
    bench = benchmark(data["SPY"])
    out = {"plan": "output/CRT_1H_TEST_PLAN_20261005.md", "spy_buy_hold": bench, "results": {}}
    for symbol in SYMBOLS:
        days = data[symbol]
        out["results"][symbol] = {}
        for side in ("long", "short"):
            trades, curve = simulate(days, side)
            r = summarize(trades, curve, bench)
            gross = summarize(*simulate(days, side, slip=0.0), bench)
            target_first = summarize(*simulate(days, side, same_bar="target"), bench)
            r["before_costs"] = {k: gross[k] for k in ("profit_factor", "total_return_pct", "win_rate_pct")}
            r["same_bar_counted_as_target"] = {k: target_first[k] for k in
                                               ("profit_factor", "total_return_pct", "target_hit_rate_pct")}
            r["distances"] = distances(trades) if trades else None
            r["trade_list"] = [{k: v for k, v in t.items() if k != "_amb"} for t in trades]
            out["results"][symbol][side] = r
    out["verdict_pass"] = all(out["results"][s]["long"]["passes"] for s in SYMBOLS)
    Path(args.output).write_text(json.dumps(out, indent=1) + "\n")
    write_manifest(args.output, code=["research/crt_1h_test_v1/backtest.py", "research/crt_sweep_test_v1/backtest.py"],
                   data=[str(path_for(s)) for s in SYMBOLS], params={"slip": SLIP, "risk": RISK, "window_min": WINDOW})
    headline = {s: {side: {k: v for k, v in out["results"][s][side].items() if k != "trade_list"}
                    for side in ("long", "short")} for s in SYMBOLS}
    print(json.dumps({"spy_buy_hold": bench, "verdict_pass": out["verdict_pass"], **headline}, indent=1))


if __name__ == "__main__":
    main()
