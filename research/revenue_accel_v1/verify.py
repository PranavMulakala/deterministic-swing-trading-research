"""Independent recount for test #20, written separately from backtest.py and revenue.py (own parsing, plain loops).

1. Picks: for 4 random month-ends, rebuild every company's quarterly revenue straight from the saved SEC frame files,
   apply the plan's fingerprint and the $20M dollar-volume rule from the raw price files, and compare the flagged count
   and the top 20 with the backtest's log.
2. Value path: re-run the logged picks with dollar holdings, solving each rebalance's fee exactly; the value at every
   rebalance and at the end must match the backtest within 0.5%.
3. SPY buy-and-hold final value.

  PYTHONPATH=src:. .venv/bin/python -m research.revenue_accel_v1.verify
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
import gzip
import io
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
DAILY = ROOT / "outputs/breakout_data"
SPY_FILE = ROOT / "outputs/momentum_lite_like_data/SPY_daily.json.gz"
SEC = ROOT / "outputs/revenue_accel_data"
TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax"]


def read_stock(path):
    rows = list(csv.DictReader(io.StringIO(gzip.decompress(path.read_bytes()).decode())))
    return {r["date"]: (float(r["open"]), float(r["close"]), float(r["volume"])) for r in rows}, [r["date"] for r in rows]


def day(s):
    return date.fromisoformat(s)


def shift(label, quarters):
    n = int(label[:4]) * 4 + int(label[5]) - 1 + quarters
    return "%dQ%d" % (n // 4, n % 4 + 1)


def revenue_by_tag():
    """{cik: {tag index: {label: (end, value)}}} from the raw frame files, with each fiscal year's missing quarter."""
    out = {}
    for k, tag in enumerate(TAGS):
        quarterly, yearly = {}, {}
        for f in sorted((SEC / "frames").glob(f"{tag}_CY*.json.gz")):
            period = f.name[len(tag) + 3:-8]                                # "2024Q3" or "2024"
            for cik, start, end, val in json.loads(gzip.decompress(f.read_bytes())):
                if not start:
                    continue
                if "Q" in period:
                    quarterly.setdefault(int(cik), []).append((period, start, end, float(val)))
                else:
                    yearly.setdefault(int(cik), []).append((start, end, float(val)))
        for cik, rows in quarterly.items():
            mine = out.setdefault(cik, {}).setdefault(k, {})
            for period, start, end, val in rows:
                if period not in mine:
                    mine[period] = (end, val)
            for ys, ye, total in yearly.get(cik, []):
                parts = [r for r in rows if day(r[1]) >= day(ys) - timedelta(10) and day(r[2]) <= day(ye) + timedelta(10)]
                if len(parts) != 3:
                    continue
                rest, last = total - sum(r[3] for r in parts), max(day(r[2]) for r in parts)
                if rest <= 0 or last >= day(ye):
                    continue
                first = last + timedelta(1)
                mid = first + (day(ye) - first) / 2
                label = "%dQ%d" % (mid.year, (mid.month - 1) // 3 + 1)
                if label not in mine:
                    mine[label] = (ye, rest)
    return out


def numbers(tags, as_of):
    """(revenue, g0, g1, g2) for the latest quarter known 90 days before `as_of`, or None."""
    cut = day(as_of) - timedelta(90)
    usable = {k: {lab: v for lab, (end, v) in s.items() if day(end) <= cut} for k, s in tags.items()}
    labels = sorted({lab for s in usable.values() for lab in s})
    if not labels:
        return None
    q0 = labels[-1]
    end0 = next(tags[k][q0][0] for k in sorted(tags) if q0 in usable[k])
    if (day(as_of) - day(end0)).days > 200:
        return None
    result = []
    for back in (0, 1, 2):
        lab = shift(q0, -back)
        ago = shift(lab, -4)
        found = None
        for k in sorted(usable):
            if lab in usable[k] and ago in usable[k]:
                found = (usable[k][lab], usable[k][ago])
                break
        if not found or found[0] <= 0 or found[1] <= 0:
            return None
        result.append(found)
    return (result[0][0],) + tuple(a / b - 1 for a, b in result)


def flagged_at(as_of, revenue, universe, tickers):
    hits = []
    for cik, sym in tickers.items():
        rows, dates = universe[sym]
        if as_of not in rows:
            continue
        k = dates.index(as_of)
        if k < 59 or sum(rows[dates[j]][1] * rows[dates[j]][2] for j in range(k - 59, k + 1)) / 60 < 20e6:
            continue
        fp = numbers(revenue.get(cik, {}), as_of)
        if fp and fp[0] >= 50e6 and fp[1] >= 0.25 and fp[1] - fp[2] >= 0.10 and fp[2] >= fp[3]:
            hits.append((-(fp[1] - fp[2]), sym))
    hits.sort()
    return [s for _, s in hits]


def px(series, d, which):
    rows, dates = series
    if d in rows:
        return rows[d][0 if which == "open" else 1]
    return rows[[x for x in dates if x < d][-1]][1]


def main():
    res = json.loads((ROOT / "output/revenue-acceleration-test-results.json").read_text())
    log, curve = res["log_main"], res["curve_main"]
    universe = {p.name[:-7]: read_stock(p) for p in sorted(DAILY.glob("*.csv.gz")) if p.name[:-7] != "SPY"}
    with gzip.open(SPY_FILE, "rt") as f:
        b = json.load(f)
    spy = ({d: (o, c, v) for d, o, c, v in zip(b["date"], b["open"], b["close"], b["volume"])}, b["date"])
    listing = json.loads(gzip.decompress((SEC / "company_tickers.json.gz").read_bytes()))
    tickers, taken = {}, set()
    for key in sorted(listing, key=int):
        sym = listing[key]["ticker"].upper().replace("-", ".")
        cik = int(listing[key]["cik_str"])
        if sym in universe and cik not in tickers and sym not in taken:
            tickers[cik] = sym
            taken.add(sym)
    revenue = revenue_by_tag()
    rng = random.Random(20)
    report, ok = {"companies_mapped": {"independent": len(tickers), "backtest": res["companies_mapped"]}}, True
    ok &= len(tickers) == res["companies_mapped"]
    for e in sorted(rng.sample(log, 4), key=lambda e: e["day"]):
        mine = flagged_at(e["formation"], revenue, universe, tickers)
        theirs = [p[0] for p in e["picks"]]
        bought = [s for s in mine[:20] if s not in e["skipped_no_bar"]]   # a pick with no bar at the open went to SPY
        match = bought == theirs and set(mine[:20]) == set(theirs + e["skipped_no_bar"]) and len(mine) == e["flagged"]
        ok &= match
        report[f"picks {e['formation']}"] = {"match": match, "flagged": [len(mine), e["flagged"]],
                                             "independent_top": mine[:20], "backtest_top": theirs}
    series = lambda sym: spy if sym == "SPY" else universe[sym]
    held, held_open, worst = {}, {}, 0.0
    for e in log:
        d = e["day"]
        now = {s: held[s] * px(series(s), d, "open") / held_open[s] for s in held}
        total = sum(now.values()) if held else 100_000.0
        weights = {p[0]: 0.05 for p in e["picks"]}
        if e["spy_weight"]:
            weights["SPY"] = weights.get("SPY", 0.0) + e["spy_weight"]
        net = total
        for _ in range(50):                                   # exact fee: net = total - 0.1% x |target - holding|
            net = total - 0.001 * sum(abs(weights.get(s, 0.0) * net - now.get(s, 0.0)) for s in set(weights) | set(now))
        worst = max(worst, abs(total / e["value_at_open"] - 1))
        held = {s: w * net for s, w in weights.items()}
        held_open = {s: px(series(s), d, "open") for s in held}
    end_day = curve[-1][0]
    final = sum(h / held_open[s] * px(series(s), end_day, "close") for s, h in held.items())
    worst = max(worst, abs(final / curve[-1][1] - 1))
    path_ok = worst <= 0.005
    ok &= path_ok
    report["value path"] = {"match": path_ok, "max_relative_gap_pct": round(100 * worst, 4),
                            "independent_final": round(final), "backtest_final": round(curve[-1][1])}
    first = log[0]["day"]
    spy_final = 100_000 * 0.999 * px(spy, end_day, "close") / px(spy, first, "open")
    spy_ok = abs(spy_final - res["main"]["spy"]["final"]) <= 1.0
    ok &= spy_ok
    report["SPY buy and hold"] = {"match": spy_ok, "independent": round(spy_final), "backtest": res["main"]["spy"]["final"]}
    print(json.dumps({"all_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
