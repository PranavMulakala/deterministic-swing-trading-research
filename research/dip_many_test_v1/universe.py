"""Test #15 universe: the 100 most volatile big stocks as of Dec 31, 2021 (output/DIP_RULE_MANY_STOCKS_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.dip_many_test_v1.universe

Uses only daily bars dated on or before 2021-12-31 from outputs/breakout_data. Writes research/dip_many_test_v1/universe.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from research.breakout_test_v1.backtest import DATA, load

HERE = Path(__file__).resolve().parent
CUTOFF, MIN_PRICE, MIN_DOLLAR_VOL, TOP_N, LOOKBACK = "2021-12-31", 20.0, 200_000_000.0, 100, 60
HINDSIGHT = ["MU", "SNDK", "WDC", "STX", "DELL", "INTC", "TER", "MRVL", "COHR", "CIEN", "HPE", "LITE"]


def candidate(symbol):
    bars = load(symbol)
    idx = [i for i, d in enumerate(bars["date"]) if d <= CUTOFF]
    if len(idx) < LOOKBACK + 1:
        return None
    t = idx[-1]
    if bars["date"][t] < "2021-12-20":          # not trading at the cutoff
        return None
    c, h, l, v = bars["close"], bars["high"], bars["low"], bars["volume"]
    window = range(t - LOOKBACK + 1, t + 1)
    dollar = sum(c[i] * v[i] for i in window) / LOOKBACK
    rng = sum((h[i] - l[i]) / c[i - 1] for i in window) / LOOKBACK
    if c[t] < MIN_PRICE or dollar < MIN_DOLLAR_VOL:
        return None
    return {"symbol": symbol, "close": round(c[t], 2), "dollar_vol_m": round(dollar / 1e6), "avg_range_pct": round(100 * rng, 2)}


def main():
    symbols = json.loads((DATA / "universe.json").read_text())
    rows = []
    for s in symbols:
        if (DATA / f"{s}.csv.gz").exists() and s != "SPY":
            r = candidate(s)
            if r:
                rows.append(r)
    rows.sort(key=lambda r: -r["avg_range_pct"])
    top = rows[:TOP_N]
    out = {"cutoff": CUTOFF, "eligible": len(rows), "rule": f"price>={MIN_PRICE}, 60d $vol>={MIN_DOLLAR_VOL/1e6:.0f}M, "
           f"top {TOP_N} by 60d avg daily range", "main": top, "hindsight": HINDSIGHT}
    (HERE / "universe.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"eligible": len(rows), "top_range_pct": [top[0]["avg_range_pct"], top[-1]["avg_range_pct"]],
                      "symbols": [r["symbol"] for r in top]}))


if __name__ == "__main__":
    main()
