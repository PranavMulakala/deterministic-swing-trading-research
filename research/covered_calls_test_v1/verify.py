"""Independent recount for test #25, written separately from backtest.py (own CSV parsing and parity math).

For 12 random main-version calls: rebuild SPY from put-call parity at the sale-day close, re-pick the call (expiration
closest to 30 days within 21-45, first strike at or above SPY x 1.02 with a bid), check the bid it was sold at, and
recompute what was paid at expiration. Also checks that the trade list adds up to the reported call P&L.

  PYTHONPATH=src:. .venv/bin/python -m research.covered_calls_test_v1.verify
"""
from __future__ import annotations

import csv
from datetime import date
import gzip
import io
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/spy_options_data"
RATES = ROOT / "research/spy_put_spread_backtest_v1/tbill_3m_monthly.csv"


def chain(day):
    text = gzip.decompress((DATA / str(day.year) / f"{day.isoformat()}.csv.gz").read_bytes()).decode()
    q = {}
    for row in csv.DictReader(io.StringIO(text)):
        bid, ask = float(row["bid"]), float(row["ask"])
        if row["window"] == "close" and bid > 0 and ask >= bid:
            q[(date.fromisoformat(row["expiration"]), row["type"], float(row["strike"]))] = (bid, ask)
    return q


def spot(q, day, r):
    for e in sorted({e for e, _, _ in q if (e - day).days >= 1})[:3]:
        t = (e - day).days / 365
        rows = sorted((abs(((b + a) - sum(q[(e, "P", k)])) / 2), k, ((b + a) - sum(q[(e, "P", k)])) / 2)
                      for (ee, typ, k), (b, a) in q.items() if ee == e and typ == "C" and (e, "P", k) in q)
        if len(rows) >= 3:
            return sorted((d + k * math.exp(-r * t)) * math.exp(0.015 * t) for _, k, d in rows[:3])[1]
    return None


def main():
    res = json.loads((ROOT / "output/covered-calls-test-results.json").read_text())
    trades = res["main_trades"]
    rates = {row["month"]: float(row["rate_pct"]) / 100 for row in csv.DictReader(RATES.open())}
    report, ok = {}, True
    for t in sorted(random.Random(25).sample(trades, 12), key=lambda t: t["entry_day"]):
        d0 = date.fromisoformat(t["entry_day"])
        q = chain(d0)
        s = spot(q, d0, rates.get(d0.strftime("%Y-%m"), 0.0))
        exps = [e for e in sorted({e for e, typ, _ in q if typ == "C"}) if 21 <= (e - d0).days <= 45]
        best = min(exps, key=lambda e: (abs((e - d0).days - 30), -e.toordinal()))
        k, (bid, _) = min(((k, v) for (e, typ, k), v in q.items() if e == best and typ == "C" and v[0] > 0
                           and k >= s * 1.02 - 1e-9), key=lambda x: x[0])
        d1 = date.fromisoformat(t["settle_day"])
        s1 = spot(chain(d1), d1, rates.get(d1.strftime("%Y-%m"), 0.0))
        paid = max(s1 - k, 0.0) * 100 * t["n"]
        same = (best.isoformat(), k, bid) == (t["expiration"], t["strike"], t["price"]) and abs(paid - t["paid_at_expiry"]) < 1
        ok &= same
        report[t["entry_day"]] = {"match": same, "strike": k, "bid": bid, "paid": round(paid, 2),
                                  "backtest": [t["strike"], t["price"], round(t["paid_at_expiry"], 2)]}
    total = round(sum(t["pnl"] for t in trades), 2)
    sums = abs(total - res["main"]["call_pnl_total"]) <= 1
    ok &= sums
    report["trade_list_total"] = {"match": sums, "sum": total, "reported": res["main"]["call_pnl_total"]}
    print(json.dumps({"all_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
