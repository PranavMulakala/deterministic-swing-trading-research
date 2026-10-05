"""Independent re-computation for test #9 (explicit short side, no mirroring). Must reproduce every trade in
output/crt-1h-test-results.json.

  PYTHONPATH=src:. .venv/bin/python -m research.crt_1h_test_v1.verify
"""
from __future__ import annotations

import json
import math

from research.crt_sweep_test_v1.backtest import RISK, SLIP, START_EQUITY, load
from research.crt_sweep_test_v1.fetch import SYMBOLS


def hourly(day):
    c = {}
    for b in day:
        k = (b["m"] - 570) // 60
        if k not in c:
            c[k] = {"start": 570 + 60 * k, "h": b["h"], "l": b["l"], "c": b["c"], "last": b["m"]}
        else:
            c[k].update(h=max(c[k]["h"], b["h"]), l=min(c[k]["l"], b["l"]), c=b["c"], last=b["m"])
    return {k: v for k, v in c.items() if v["last"] == v["start"] + 55 and v["start"] + 60 <= 960}


def trades_for_day(day, side):
    c, out, busy = hourly(day), [], -1
    for k in sorted(c):
        if k + 1 not in c:
            continue
        a, b = c[k], c[k + 1]
        end = b["start"] + 60
        if end < busy:
            continue
        if side == "long":
            ok, line, stop, target = b["l"] < a["l"] and a["l"] <= b["c"] <= a["h"] and b["h"] <= a["h"], b["h"], b["l"], a["h"]
        else:
            ok, line, stop, target = b["h"] > a["h"] and a["l"] <= b["c"] <= a["h"] and b["l"] >= a["l"], b["l"], b["h"], a["l"]
        if not ok:
            continue
        sig = next((i for i, x in enumerate(day) if end <= x["m"] < end + 60 and x["m"] <= 925
                    and (x["c"] > line if side == "long" else x["c"] < line)), None)
        if sig is None:
            continue
        entry = day[sig]["c"]
        if not ((target > entry > stop) if side == "long" else (target < entry < stop)):
            continue
        exit_px, reason, ex = day[-1]["c"], "close", len(day) - 1
        for j in range(sig + 1, len(day)):
            x = day[j]
            s_hit = x["l"] <= stop if side == "long" else x["h"] >= stop
            t_hit = x["h"] >= target if side == "long" else x["l"] <= target
            if s_hit or t_hit:
                ex = j
                exit_px, reason = (stop, "stop_same_bar") if s_hit and t_hit else ((stop, "stop") if s_hit else (target, "target"))
                break
        out.append({"entry_time": f"{day[sig]['m'] // 60}:{day[sig]['m'] % 60:02d}", "entry": entry, "stop": stop,
                    "target": target, "exit": exit_px, "reason": reason})
        busy = day[ex]["m"] + 5
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
            equity += shares * ((out - fill) if side == "long" else (fill - out))
            trades.append({**t, "date": date})
    return trades, equity


def main():
    results = json.loads(open("output/crt-1h-test-results.json").read())["results"]
    report = {}
    for symbol in SYMBOLS:
        days = load(symbol)
        for side in ("long", "short"):
            mine, final = replay(days, side)
            theirs = results[symbol][side]["trade_list"]
            bad = sum(not (x["date"] == y["date"] and x["entry_time"] == y["entry_time"] and x["reason"] == y["reason"]
                           and all(abs(round(x[k], 4) - y[k]) < 1e-6 for k in ("entry", "stop", "target", "exit")))
                      for x, y in zip(mine, theirs))
            report[f"{symbol}_{side}"] = {"trades_mine": len(mine), "trades_backtest": len(theirs),
                                          "field_mismatches": bad, "final_equity_mine": round(final),
                                          "final_equity_backtest": results[symbol][side]["final_equity"]}
    ok = all(v["trades_mine"] == v["trades_backtest"] and v["field_mismatches"] == 0
             and abs(v["final_equity_mine"] - v["final_equity_backtest"]) <= 1 for v in report.values())
    print(json.dumps({"independent_check_matches": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
