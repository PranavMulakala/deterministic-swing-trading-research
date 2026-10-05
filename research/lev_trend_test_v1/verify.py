"""Independent recomputation for test #14 (separately written: own CSV parse with the csv module, deque-based moving
average, explicit position array). Must reproduce the main strategy's and the benchmark's growth and worst drop.

  PYTHONPATH=src:. .venv/bin/python -m research.lev_trend_test_v1.verify
"""
from __future__ import annotations

from collections import deque
import csv
import json

PATH = "outputs/lev_trend_data/F-F_Research_Data_Factors_daily.csv"


def main():
    rows = []
    with open(PATH) as handle:
        for rec in csv.reader(handle):
            if len(rec) == 5 and rec[0].strip().isdigit() and len(rec[0].strip()) == 8:
                rows.append((rec[0].strip(), float(rec[1]) / 100 + float(rec[4]) / 100, float(rec[4]) / 100))
    level, window, above = 1.0, deque(), []
    for _, m, _ in rows:
        level *= 1 + m
        window.append(level)
        if len(window) > 200:
            window.popleft()
        above.append(level > sum(window) / 200 if len(window) == 200 else None)
    eq_main = eq_mkt = 1.0
    peak_main = peak_mkt = 1.0
    dd_main = dd_mkt = 0.0
    held = None
    for i in range(200, len(rows)):
        _, m, rf = rows[i]
        want = above[i - 1]
        if held is not None and want != held:
            eq_main *= 0.999
        held = want
        if want:
            eq_main *= 1 + (2 * m - (rf + 0.005 / 252) - 0.009 / 252)
        else:
            eq_main *= 1 + rf
        eq_mkt *= 1 + m
        peak_main, peak_mkt = max(peak_main, eq_main), max(peak_mkt, eq_mkt)
        dd_main, dd_mkt = min(dd_main, eq_main / peak_main - 1), min(dd_mkt, eq_mkt / peak_mkt - 1)
    res = json.load(open("output/lev-trend-test-results.json"))["results"]
    mine = {"main_growth": round(eq_main, 2), "main_dd": round(dd_main * 100, 1),
            "market_growth": round(eq_mkt, 2), "market_dd": round(dd_mkt * 100, 1)}
    theirs = {"main_growth": res["main_2x_above_200d"]["growth_of_1"], "main_dd": res["main_2x_above_200d"]["max_drawdown_pct"],
              "market_growth": res["market_1x_hold"]["growth_of_1"], "market_dd": res["market_1x_hold"]["max_drawdown_pct"]}
    ok = all(abs(mine[k] - theirs[k]) <= max(0.01 * abs(theirs[k]), 0.1) for k in mine)
    print(json.dumps({"independent": mine, "backtest": theirs, "match": ok}, indent=1))


if __name__ == "__main__":
    main()
