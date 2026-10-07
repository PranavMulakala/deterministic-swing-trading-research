"""Independent recount for test #24, written separately from backtest.py (own CSV parsing and parity math).

For 12 random main-variant trades: rebuild SPY from put-call parity at the entry-day close, re-pick the call (expiration
closest to 7 days, strike nearest SPY), check the ask paid, and recompute the expiration value. Also checks that the
trade list adds up to the reported call P&L.

  PYTHONPATH=src:. .venv/bin/python -m research.short_calls_test_v1.verify
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
        if row["window"] != "close":
            continue
        bid, ask = float(row["bid"]), float(row["ask"])
        if bid > 0 and ask >= bid:
            q[(date.fromisoformat(row["expiration"]), row["type"], float(row["strike"]))] = (bid, ask)
    return q


def spot(q, day, r):
    exps = sorted({e for e, _, _ in q if (e - day).days >= 1})
    for e in exps[:3]:
        t = (e - day).days / 365
        rows = []
        for (ee, typ, k), (b, a) in q.items():
            if ee == e and typ == "C" and (e, "P", k) in q:
                pb, pa = q[(e, "P", k)]
                diff = (b + a) / 2 - (pb + pa) / 2
                rows.append((abs(diff), k, diff))
        if len(rows) >= 3:
            rows.sort()
            vals = sorted((d + k * math.exp(-r * t)) * math.exp(0.015 * t) for _, k, d in rows[:3])
            return vals[1]
    return None


def main():
    res = json.loads((ROOT / "output/short-dated-calls-test-results.json").read_text())
    trades = res["main_trades"]
    rates = {row["month"]: float(row["rate_pct"]) / 100 for row in csv.DictReader(RATES.open())}
    rng = random.Random(24)
    report, ok = {}, True
    for t in sorted(rng.sample(trades, 12), key=lambda t: t["entry_day"]):
        d0 = date.fromisoformat(t["entry_day"])
        q = chain(d0)
        s = spot(q, d0, rates.get(d0.strftime("%Y-%m"), 0.0))
        exps = [e for e in sorted({e for e, typ, _ in q if typ == "C"}) if 4 <= (e - d0).days <= 11]
        best = min(exps, key=lambda e: (abs((e - d0).days - 7), -e.toordinal()))
        ks = [(k, v) for (e, typ, k), v in q.items() if e == best and typ == "C" and v[1] > 0]
        k, (bid, ask) = min(ks, key=lambda x: (abs(x[0] - s), -x[0]))
        d1 = date.fromisoformat(t["exit_day"])
        s1 = spot(chain(d1), d1, rates.get(d1.strftime("%Y-%m"), 0.0))
        value = max(s1 - k, 0.0)
        same = (best.isoformat(), k, ask) == (t["expiration"], t["strike"], t["price"]) and abs(value - t["exit_value"]) < 0.01
        ok &= same
        report[t["entry_day"]] = {"match": same, "strike": k, "ask": ask, "value_at_expiry": round(value, 3),
                                  "backtest": [t["strike"], t["price"], round(t["exit_value"], 3)]}
    total = round(sum(t["pnl"] for t in trades))
    sums = abs(total - res["main"]["total_call_pnl"]) <= 1
    ok &= sums
    report["trade_list_total"] = {"match": sums, "sum": total, "reported": res["main"]["total_call_pnl"]}
    print(json.dumps({"all_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
