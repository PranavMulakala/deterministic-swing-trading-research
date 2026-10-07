"""Independent recount for test #23 (RFK), written separately from backtest.py.

1. Signals and their exits for 10 random stocks with any main-rule signal, recomputed with plain loops.
2. The main account re-chained from the logged trades (cash in, cash out) to the final value.

  PYTHONPATH=src:. .venv/bin/python -m research.rfk_test_v1.verify
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
DAILY = ROOT / "outputs/orb_play_data/daily"


def read(p):
    return json.loads(gzip.decompress(p.read_bytes()))


def recount(b):
    raw, x, dates = b["raw"], b["split"], b["date"]
    found = []
    for f in range(61, len(x) - 1):
        dollars = [raw[i][3] * raw[i][4] for i in range(f - 60, f)]
        if raw[f - 1][3] <= 10 or sum(dollars) / 60 < 50e6:
            continue
        o, h, l, c = x[f][:4]
        if not (c < o and h > l and (c - l) / (h - l) <= 0.25):
            continue
        lows = [x[i][2] for i in range(f - 20, f)]
        floor = min(lows)
        if max(x[i][1] for i in range(f - 20, f)) / floor - 1 > 0.25 or l >= floor:
            continue
        clear = 0
        for j in range(f - 20, f - 2):
            if j < 2:
                continue
            if x[j][2] < x[j - 1][2] and x[j][2] < x[j - 2][2] and x[j][2] <= x[j + 1][2] and x[j][2] <= x[j + 2][2] \
                    and x[j][2] <= floor * 1.02:
                clear += 1
        if clear < 2 or x[f + 1][3] <= h:
            continue
        entry, stop = x[f + 1][3], l
        if entry - stop <= 0 or (entry - stop) / entry > 0.20:
            continue
        target = entry + (entry - stop)
        exit_ = None
        for i in range(f + 2, min(f + 21, len(x) - 1) + 1):
            oo, hh, ll, cc = x[i][:4]
            if oo <= stop:
                exit_ = (dates[i], oo)
            elif oo >= target:
                exit_ = (dates[i], oo)
            elif ll <= stop:
                exit_ = (dates[i], stop)
            elif hh >= target:
                exit_ = (dates[i], target)
            elif i == f + 21:
                exit_ = (dates[i], cc)
            if exit_:
                break
        if exit_ is None:
            last = min(f + 21, len(x) - 1)
            exit_ = (dates[last], x[last][3])
        found.append((dates[f + 1], round(entry, 6), round(stop, 6), exit_[0], round(exit_[1], 6)))
    return found


def main():
    detail = read(ROOT / "outputs/orb_play_data/rfk_detail.json.gz")
    sigs = detail["signals_main"]
    by_sym = {}
    for s in sigs:
        by_sym.setdefault(s["symbol"], []).append((s["date"], round(s["entry"], 6), round(s["stop"], 6),
                                                   s["exit_date"], round(s["exit"], 6)))
    rng = random.Random(23)
    report, ok = {}, True
    for sym in sorted(rng.sample(sorted(by_sym), 10)):
        mine = recount(read(DAILY / f"{sym}.json.gz"))
        same = mine == by_sym[sym]
        ok &= same
        report[sym] = {"match": same, "signals": len(mine)}
        if not same:
            report[sym].update({"independent": mine[:5], "backtest": by_sym[sym][:5]})
    cash = 100_000.0
    for t in detail["trades_main"]:
        cash += t["shares"] * (t["exit"] * 0.999 - t["entry"] * 1.001)
    curve = detail["curve_main"]
    open_value = curve[-1][1] - cash
    report["account"] = {"closed_trades_cash": round(cash), "backtest_final": round(curve[-1][1]),
                         "difference_is_open_positions_marked": round(open_value)}
    print(json.dumps({"all_signals_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
