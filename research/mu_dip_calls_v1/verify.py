"""Independent recount for test #27, written separately from backtest.py (own file parsing and rules).

For 12 random main trades: re-read the 10:00 chain file, re-pick the call (expiration closest to 7 days within 4-11,
ties later; strike nearest MU's 10:00 price, ties higher), check the ask paid; re-read that contract's quote file and
find the first minute with bid >= 2x the ask, else the intrinsic value at the expiration-day close; recompute the
$1,000-stake P&L. Also checks that the main trade list adds up to the reported total.

  PYTHONPATH=src:. .venv/bin/python -m research.mu_dip_calls_v1.verify
"""
from __future__ import annotations

import csv
from datetime import date
import gzip
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/mu_dip_calls_data"


def rows(path):
    with gzip.open(path, "rt") as f:
        return list(csv.DictReader(f))


def main():
    res = json.loads((ROOT / "output/mu-dip-weekly-calls-test-results.json").read_text())
    meta = json.loads((DATA / "days.json").read_text())
    report, ok = {}, True
    for t in sorted(random.Random(2027).sample(res["main_trades"], min(12, len(res["main_trades"]))), key=lambda t: t["day"]):
        d0 = date.fromisoformat(t["day"])
        spot = meta["days"][t["day"]]["spot10"]
        calls = [(date.fromisoformat(r["expiration"]), float(r["strike"]), float(r["bid"]), float(r["ask"]))
                 for r in rows(DATA / "chain" / f"{t['day']}.csv.gz")]
        calls = [c for c in calls if c[2] > 0 and c[3] > 0 and 4 <= (c[0] - d0).days <= 11]
        best_gap = min(abs((c[0] - d0).days - 7) for c in calls)
        exp = max(c[0] for c in calls if abs((c[0] - d0).days - 7) == best_gap)
        same_exp = [c for c in calls if c[0] == exp]
        best_k = min(abs(c[1] - spot) for c in same_exp)
        k = max(c[1] for c in same_exp if abs(c[1] - spot) == best_k)
        ask = next(c[3] for c in same_exp if c[1] == k)
        sym = f"MU{exp:%y%m%d}C{round(k * 1000):08d}"
        hold = rows(DATA / "hold" / f"{t['day']}_{sym}.csv.gz")
        hit = next((float(r["bid"]) for r in hold if float(r["bid"]) >= 2 * ask), None)
        if hit is not None:
            n = 1000 / (ask * 100 + 0.03)
            pnl = n * (hit * 100 - 0.03) - 1000
        else:
            n = 1000 / (ask * 100 + 0.03)
            pnl = n * max(meta["closes"][exp.isoformat()] - k, 0) * 100 - 1000
        same = exp.isoformat() == t["expiration"] and k == t["strike"] and ask == t["entry_ask"] and abs(pnl - t["pnl"]) < 0.05
        ok &= same
        report[t["day"]] = {"match": same, "strike": k, "expiration": exp.isoformat(), "ask": ask, "pnl": round(pnl, 2),
                            "backtest": [t["strike"], t["expiration"], t["entry_ask"], t["pnl"]]}
    total = round(sum(t["pnl"] for t in res["main_trades"]), 2)
    sums = abs(total - res["main"]["total_pnl"]) < 0.5
    ok &= sums
    report["trade_list_total"] = {"match": sums, "sum": total, "reported": res["main"]["total_pnl"]}
    print(json.dumps({"all_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
