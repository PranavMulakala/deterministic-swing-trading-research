"""Independent recount for test #26, written separately from backtest.py (own CSV parsing, parity math and picks).

1. For 12 random main-version calls: rebuild SPY from put-call parity at the sale-day close, re-pick the call (expiration
   closest to 40 days within 30-50, ties later; the lowest strike below SPY whose annualized return if called away at
   the bid is at least 10%), check the bid it was sold at, and recompute what it cost to close (intrinsic at
   expiration or early exercise; the ask + $0.03 on a roll).
2. For every roll: SPY closed below the old strike, 7+ days were left, and the new call's bid was above the old ask.
3. For every early exercise: the next data day is an ex-date and the call's time value was below that dividend.
4. The trade list adds up to the reported call P&L.

  PYTHONPATH=src:. .venv/bin/python -m research.itm_covered_calls_test_v1.verify
"""
from __future__ import annotations

import csv
from datetime import date
from functools import lru_cache
import gzip
import io
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/spy_options_data"
RATES = ROOT / "research/spy_put_spread_backtest_v1/tbill_3m_monthly.csv"
DIVS = ROOT / "output/spy-dividends-alpaca-2016-2025.json"


@lru_cache(maxsize=None)
def chain(day):
    text = gzip.decompress((DATA / str(day.year) / f"{day.isoformat()}.csv.gz").read_bytes()).decode()
    q = {}
    for row in csv.DictReader(io.StringIO(text)):
        bid, ask = float(row["bid"]), float(row["ask"])
        if row["window"] == "close" and bid > 0 and ask >= bid:
            q[(date.fromisoformat(row["expiration"]), row["type"], float(row["strike"]))] = (bid, ask)
    return q


def spot(day, rates):
    q, r = chain(day), rates.get(day.strftime("%Y-%m"), 0.0)
    for e in sorted({e for e, _, _ in q if (e - day).days >= 1})[:3]:
        t = (e - day).days / 365
        rows = sorted((abs(((b + a) - sum(q[(e, "P", k)])) / 2), k, ((b + a) - sum(q[(e, "P", k)])) / 2)
                      for (ee, typ, k), (b, a) in q.items() if ee == e and typ == "C" and (e, "P", k) in q)
        if len(rows) >= 3:
            return sorted((d + k * math.exp(-r * t)) * math.exp(0.015 * t) for _, k, d in rows[:3])[1]
    return None


def repick(day, s):
    q = chain(day)
    exps = sorted({e for e, typ, _ in q if typ == "C" and 30 <= (e - day).days <= 50})
    best = min(exps, key=lambda e: (abs((e - day).days - 40), -e.toordinal()))
    n = (best - day).days
    for k in sorted(k for (e, typ, k) in q if e == best and typ == "C" and k < s):
        bid = q[(best, "C", k)][0]
        if (k - (s - bid)) / (s - bid) * 365 / n >= 0.10 - 1e-12:
            return best, k, bid
    return None


def main():
    res = json.loads((ROOT / "output/itm-covered-calls-test-results.json").read_text())
    trades = res["main_trades"]
    rates = {row["month"]: float(row["rate_pct"]) / 100 for row in csv.DictReader(RATES.open())}
    divs = {x["ex_date"]: x["rate"] for x in json.loads(DIVS.read_text())}
    days = sorted(date.fromisoformat(p.name[:10]) for p in DATA.glob("*/*.csv.gz"))
    report, ok = {}, True

    for t in sorted(random.Random(26).sample(trades, 12), key=lambda t: t["entry_day"]):
        d0, d1 = date.fromisoformat(t["entry_day"]), date.fromisoformat(t["close_day"])
        exp, k, bid = repick(d0, spot(d0, rates))
        s1 = spot(d1, rates)
        if t["closed"] == "rolled":
            cost = t["n"] * (chain(d1)[(exp, "C", k)][1] * 100 + 0.03)
        else:
            cost = max(s1 - k, 0.0) * 100 * t["n"]
        same = (exp.isoformat(), k, bid) == (t["expiration"], t["strike"], t["price"]) and abs(cost - t["close_cost"]) < 1
        ok &= same
        report[t["entry_day"]] = {"match": same, "closed": t["closed"], "strike": k, "bid": bid, "close_cost": round(cost, 2),
                                  "backtest": [t["strike"], t["price"], round(t["close_cost"], 2)]}

    opened = {t["entry_day"]: t for t in trades}
    rolls_ok, n_rolls = True, 0
    for t in trades:
        if t["closed"] != "rolled":
            continue
        n_rolls += 1
        d1, exp = date.fromisoformat(t["close_day"]), date.fromisoformat(t["expiration"])
        old_ask = chain(d1)[(exp, "C", t["strike"])][1]
        new = opened.get(t["close_day"])
        good = spot(d1, rates) < t["strike"] and (exp - d1).days >= 7 and new is not None and new["price"] > old_ask
        rolls_ok &= good
    ok &= rolls_ok
    report["every_roll_follows_the_rule"] = {"match": rolls_ok, "rolls": n_rolls}

    early_ok, n_early = True, 0
    for t in trades:
        if t["closed"] != "early_exercise":
            continue
        n_early += 1
        d1, exp = date.fromisoformat(t["close_day"]), date.fromisoformat(t["expiration"])
        nxt = min((d for d in days if d > d1), default=None)
        ex = min((date.fromisoformat(x) for x in divs if date.fromisoformat(x) > d1), default=None)
        b, a = chain(d1)[(exp, "C", t["strike"])]
        s1 = spot(d1, rates)
        good = ex is not None and nxt is not None and ex <= nxt and s1 > t["strike"] and (b + a) / 2 - (s1 - t["strike"]) < divs[ex.isoformat()]
        early_ok &= good
    ok &= early_ok
    report["every_early_exercise_follows_the_rule"] = {"match": early_ok, "early_exercises": n_early}

    total = round(sum(t["pnl"] for t in trades), 2)
    sums = abs(total - res["main"]["call_pnl_total"]) <= 1
    ok &= sums
    report["trade_list_total"] = {"match": sums, "sum": total, "reported": res["main"]["call_pnl_total"]}
    print(json.dumps({"all_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
