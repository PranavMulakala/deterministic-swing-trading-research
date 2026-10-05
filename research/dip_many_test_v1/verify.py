"""Independent recount for test #15: for 5 random stocks of the main universe, recompute every signal and +2% exit
from the raw cached 30-minute bars with separately written code (unconstrained, one position per stock), and compare
trade count, still-open count and summed % with the backtest's per-stock results.

  PYTHONPATH=src:. .venv/bin/python -m research.dip_many_test_v1.verify
"""
from __future__ import annotations

import gzip
import json
import random

from research.dip_many_test_v1.fetch import HERE, path_for


def recount(symbol):
    with gzip.open(path_for(symbol), "rt") as f:
        rows = json.load(f)
    by_day = {}
    for d, m, o, h, l, c in rows:
        by_day.setdefault(d, []).append((m, o, h, l, c))
    trades, holding = [], None
    for d in sorted(by_day):
        bars = sorted(by_day[d])
        if holding:
            target = holding * 1.02
            if bars[0][1] >= target:
                trades.append((bars[0][1] * 0.9995 / holding - 1, False))
                holding = None
            elif any(b[2] >= target for b in bars):
                trades.append((target * 0.9995 / holding - 1, False))
                holding = None
        if not holding and bars[0][0] == 570:
            m, o, h, l, c = bars[0]
            if l <= o * 0.99 and c < o:
                holding = c * 1.001
                if any(b[2] >= holding * 1.02 for b in bars if b[0] >= 600):
                    trades.append((holding * 1.02 * 0.9995 / holding - 1, False))
                    holding = None
        last = bars[-1][4]
    if holding:
        trades.append((last / holding - 1, True))
    return {"trades": len(trades), "stuck_at_end": sum(o for _, o in trades), "sum_pct": round(100 * sum(p for p, _ in trades), 1)}


def main():
    u = json.loads((HERE / "universe.json").read_text())
    res = json.load(open("output/dip-many-test-results.json"))["main_hindsight_free"]["per_stock"]
    random.seed(15)
    picks = random.sample(sorted(res), 5)
    report = {}
    for s in picks:
        mine, theirs = recount(s), res[s]
        report[s] = {"independent": mine, "backtest": {k: theirs[k] for k in ("trades", "stuck_at_end", "sum_pct")},
                     "match": mine["trades"] == theirs["trades"] and mine["stuck_at_end"] == theirs["stuck_at_end"]
                     and abs(mine["sum_pct"] - theirs["sum_pct"]) <= 0.2}
    print(json.dumps({"all_match": all(v["match"] for v in report.values()), **report}, indent=1))


if __name__ == "__main__":
    main()
