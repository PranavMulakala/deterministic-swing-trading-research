"""Independent recount for test #17, written separately from backtest.py (own parsing, plain loops, dollar accounting).

1. Picks: for 6 random month-ends, recompute the LITE-like set and the 5 strongest from the raw files.
2. Value path: re-run the logged picks with dollar holdings, solving each rebalance's fee exactly; the value at every
   rebalance and at the end must match the backtest within 0.5%.
3. SMH buy-and-hold final value.

  PYTHONPATH=src:. .venv/bin/python -m research.momentum_lite_like_v1.verify
"""
from __future__ import annotations

import csv
import gzip
import io
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
DAILY = ROOT / "outputs/breakout_data"
ETF_DIR = ROOT / "outputs/momentum_lite_like_data"


def read_stock(path):
    rows = list(csv.DictReader(io.StringIO(gzip.decompress(path.read_bytes()).decode())))
    return {r["date"]: (float(r["open"]), float(r["close"]), float(r["volume"])) for r in rows}, [r["date"] for r in rows]


def read_etf(sym):
    with gzip.open(ETF_DIR / f"{sym}_daily.json.gz", "rt") as f:
        b = json.load(f)
    return {d: (o, c, v) for d, o, c, v in zip(b["date"], b["open"], b["close"], b["volume"])}, b["date"]


def strongest(universe, day, n=5):
    found = []
    for sym, (rows, dates) in universe.items():
        if day not in rows:
            continue
        k = dates.index(day)
        if k < 126:
            continue
        closes = [rows[dates[j]][1] for j in range(k - 126, k + 1)]
        last60 = range(k - 59, k + 1)
        dollar = sum(rows[dates[j]][1] * rows[dates[j]][2] for j in last60) / 60
        swing = sum(abs(rows[dates[j]][1] / rows[dates[j - 1]][1] - 1) for j in last60) / 60
        gain = closes[-1] / closes[0] - 1
        if dollar >= 300e6 and swing >= 0.04 and gain > 0:
            found.append((gain, sym))
    found.sort(key=lambda t: (-t[0], t[1]))
    return [s for _, s in found[:n]]


def px(series, day, which):
    rows, dates = series
    if day in rows:
        return rows[day][0 if which == "open" else 1]
    earlier = [d for d in dates if d < day]
    return rows[earlier[-1]][1]


def main():
    res = json.loads((ROOT / "output/lite-like-momentum-test-results.json").read_text())
    log, curve = res["log_main"], res["curve_main"]
    universe = {p.name[:-7]: read_stock(p) for p in sorted(DAILY.glob("*.csv.gz")) if p.name[:-7] != "SPY"}
    smh = read_etf("SMH")
    rng = random.Random(17)
    report, ok = {}, True
    for e in rng.sample(log, 6):
        mine = strongest(universe, e["formation"])
        theirs = [p[0] for p in e["picks"]]
        match = mine == theirs
        ok &= match
        report[f"picks {e['formation']}"] = {"match": match, "independent": mine, "backtest": theirs}
    series = lambda sym: smh if sym == "SMH" else universe[sym]
    held, held_open, worst = {}, {}, 0.0                    # dollars per symbol at the last rebalance open
    for e in log:
        day = e["day"]
        now = {s: held[s] * px(series(s), day, "open") / held_open[s] for s in held}
        total = sum(now.values()) if held else 100_000.0
        weights = {p[0]: 0.2 for p in e["picks"]}
        if e["smh_weight"]:
            weights["SMH"] = weights.get("SMH", 0.0) + e["smh_weight"]
        net = total
        for _ in range(50):                                   # exact fee: net = total - 0.1% x |target - holding|
            net = total - 0.001 * sum(abs(weights.get(s, 0.0) * net - now.get(s, 0.0)) for s in set(weights) | set(now))
        worst = max(worst, abs(total / e["value_at_open"] - 1))
        held = {s: w * net for s, w in weights.items()}
        held_open = {s: px(series(s), day, "open") for s in held}
    end_day = curve[-1][0]
    final = sum(h / held_open[s] * px(series(s), end_day, "close") for s, h in held.items())
    worst = max(worst, abs(final / curve[-1][1] - 1))
    path_ok = worst <= 0.005
    ok &= path_ok
    report["value path"] = {"match": path_ok, "max_relative_gap_pct": round(100 * worst, 4),
                            "independent_final": round(final), "backtest_final": round(curve[-1][1])}
    first = log[0]["day"]
    smh_final = 100_000 * 0.999 * px(smh, end_day, "close") / px(smh, first, "open")
    smh_ok = abs(smh_final - res["main"]["smh"]["final"]) <= 1.0
    ok &= smh_ok
    report["SMH buy and hold"] = {"match": smh_ok, "independent": round(smh_final), "backtest": res["main"]["smh"]["final"]}
    print(json.dumps({"all_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
