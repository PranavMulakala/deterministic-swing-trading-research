"""Test #16 candidate days (output/EP_EARNINGS_GAP_TEST_PLAN_20261005.md): which (stock, day) pairs need 5-minute bars.

  PYTHONPATH=src:. .venv/bin/python -m research.ep_test_v1.candidates

A SUPERSET of anything the rule can trade, used only to choose downloads (no returns are computed here):
open >= 1.10 x previous close, 20-day average dollar volume >= $20M, full-day volume >= 0.8 x the 20-day average
(the rule itself needs 9:30-10:00 volume >= 1.0 x, which implies full-day >= 1.0 x; 0.8 leaves margin for feed
differences between daily and intraday volume). Daily bars from outputs/breakout_data (SIP, adjustment=all).
Writes outputs/ep_data/candidates.json.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

from research.breakout_test_v1.backtest import DATA, load

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs/ep_data"
START, GAP, MIN_ADV_USD, PREFILTER_VOL, LOOKBACK = "2016-02-01", 1.10, 20e6, 0.8, 20


def symbols():
    return [s for s in json.loads((DATA / "universe.json").read_text()) if s != "SPY" and (DATA / f"{s}.csv.gz").exists()]


def candidate_days(bars):
    d, o, c, v = bars["date"], bars["open"], bars["close"], bars["volume"]
    out = []
    for i in range(LOOKBACK, len(d)):
        if d[i] < START or c[i - 1] <= 0:
            continue
        adv = sum(v[i - LOOKBACK:i]) / LOOKBACK
        adv_usd = sum(c[j] * v[j] for j in range(i - LOOKBACK, i)) / LOOKBACK
        if adv_usd >= MIN_ADV_USD and o[i] >= GAP * c[i - 1] and v[i] >= PREFILTER_VOL * adv:
            out.append(d[i])
    return out


def main():
    by_date = defaultdict(list)
    for s in symbols():
        for day in candidate_days(load(s)):
            by_date[day].append(s)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {"rule": "open>=1.10*prev close, 20d $vol>=20M, day vol>=0.8*20d avg (download superset only)",
           "by_date": {k: sorted(v) for k, v in sorted(by_date.items())}}
    (OUT_DIR / "candidates.json").write_text(json.dumps(out) + "\n")
    n = sum(len(v) for v in by_date.values())
    print(json.dumps({"candidate_days": n, "dates": len(by_date), "stocks": len({s for v in by_date.values() for s in v})}))


if __name__ == "__main__":
    main()
