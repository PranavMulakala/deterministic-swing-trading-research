"""Independent re-computation for test #8. Writes the short side out explicitly (no mirroring) and works from
pandas-free per-day loops over the raw bars, then checks that every trade in output/crt-sweep-test-results.json
is reproduced: same date, entry time, entry, stop, target, exit and reason, and the same total P&L.

  PYTHONPATH=src:. .venv/bin/python -m research.crt_sweep_test_v1.verify
"""
from __future__ import annotations

import json
import math

from research.crt_sweep_test_v1.backtest import RISK, SLIP, START_EQUITY, load
from research.crt_sweep_test_v1.fetch import SYMBOLS


def hhmm(m):
    return f"{m // 60}:{m % 60:02d}"


def trades_for_day(day, side):
    c15 = {}
    for b in day:
        k = (b["m"] - 570) // 15
        if k not in c15:
            c15[k] = {"start": 570 + 15 * k, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"]}
        else:
            c15[k]["h"], c15[k]["l"], c15[k]["c"] = max(c15[k]["h"], b["h"]), min(c15[k]["l"], b["l"]), b["c"]
    out, busy_until = [], -1
    for k in sorted(c15):
        if k + 1 not in c15:
            continue
        a, b2 = c15[k], c15[k + 1]
        end = b2["start"] + 15
        if end < busy_until:
            continue
        if side == "long":
            ok = b2["l"] < a["l"] and a["l"] <= b2["c"] <= a["h"] and b2["h"] <= a["h"]
            line = b2["h"]
        else:
            ok = b2["h"] > a["h"] and a["l"] <= b2["c"] <= a["h"] and b2["l"] >= a["l"]
            line = b2["l"]
        if not ok:
            continue
        sig = None
        for i, bar in enumerate(day):
            if end <= bar["m"] < end + 30 and bar["m"] <= 925:
                if (side == "long" and bar["c"] > line) or (side == "short" and bar["c"] < line):
                    sig = i
                    break
        if sig is None:
            continue
        entry = day[sig]["c"]
        stop = day[sig]["l"] if side == "long" else day[sig]["h"]
        target = a["h"] if side == "long" else a["l"]
        if side == "long" and not (target > entry > stop):
            continue
        if side == "short" and not (target < entry < stop):
            continue
        exit_px, reason, ex = day[-1]["c"], "close", len(day) - 1
        for j in range(sig + 1, len(day)):
            bar = day[j]
            s_hit = bar["l"] <= stop if side == "long" else bar["h"] >= stop
            t_hit = bar["h"] >= target if side == "long" else bar["l"] <= target
            if s_hit or t_hit:
                ex = j
                if s_hit and t_hit:
                    exit_px, reason = stop, "stop_same_bar"
                elif s_hit:
                    exit_px, reason = stop, "stop"
                else:
                    exit_px, reason = target, "target"
                break
        out.append({"entry_time": hhmm(day[sig]["m"]), "entry": entry, "stop": stop, "target": target,
                    "exit": exit_px, "reason": reason})
        busy_until = day[ex]["m"] + 5
    return out


def replay(days, side):
    equity, trades = START_EQUITY, []
    for date, day in days.items():
        for t in trades_for_day(day, side):
            if side == "long":
                fill, out = t["entry"] * (1 + SLIP), t["exit"] * (1 - SLIP)
                risk = fill - t["stop"]
            else:
                fill, out = t["entry"] * (1 - SLIP), t["exit"] * (1 + SLIP)
                risk = t["stop"] - fill
            shares = math.floor(min(RISK * equity / risk, equity / fill)) if risk > 0 else 0
            if shares < 1:
                continue
            pnl = shares * ((out - fill) if side == "long" else (fill - out))
            equity += pnl
            trades.append({**t, "date": date, "pnl": pnl})
    return trades, equity


def main():
    results = json.loads(open("output/crt-sweep-test-results.json").read())["results"]
    report = {}
    for symbol in SYMBOLS:
        days = load(symbol)
        for side in ("long", "short"):
            mine, final = replay(days, side)
            theirs = results[symbol][side]["trade_list"]
            mismatches = 0
            for x, y in zip(mine, theirs):
                same = (x["date"] == y["date"] and x["entry_time"] == y["entry_time"] and x["reason"] == y["reason"]
                        and all(abs(round(x[k], 4) - y[k]) < 1e-6 for k in ("entry", "stop", "target", "exit")))
                mismatches += not same
            report[f"{symbol}_{side}"] = {"trades_mine": len(mine), "trades_backtest": len(theirs),
                                          "field_mismatches": mismatches, "final_equity_mine": round(final),
                                          "final_equity_backtest": results[symbol][side]["final_equity"]}
    ok = all(v["trades_mine"] == v["trades_backtest"] and v["field_mismatches"] == 0
             and abs(v["final_equity_mine"] - v["final_equity_backtest"]) <= 1 for v in report.values())
    print(json.dumps({"independent_check_matches": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
