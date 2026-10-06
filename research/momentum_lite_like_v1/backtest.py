"""Backtest of pre-declared test #17 (output/LITE_LIKE_MOMENTUM_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.momentum_lite_like_v1.backtest

Each month-end close: LITE-like stocks = 60-day average dollar volume >= $300M and 60-day average absolute daily move
>= 4%; hold the 5 with the highest positive 6-month return, equal weight, empty slots in SMH; trade at the next open
with 0.1% per side on traded dollars. Compared with holding SMH from the same open. Research only; no orders.
"""
from __future__ import annotations

import bisect
from collections import Counter
from datetime import date
import gzip
import json
from pathlib import Path

from research.breakout_test_v1.backtest import DATA, load
from research.momentum_lite_like_v1.fetch_etfs import ETFS, path_for
from research.provenance_v1.provenance import write_manifest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/lite-like-momentum-test-results.json"
START_CASH = 100_000.0
MIN_DVOL, MIN_MOVE, VOL_WIN, MOM, TOP_N, COST, FILL = 300e6, 0.04, 60, 126, 5, 0.001, "SMH"
MAIN_START, STRESS_START, END = "2020-01-02", "2016-10-03", "2026-09-28"
HALVES = (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2026", "2023-01-01", "2026-12-31"))


def prefix(xs):
    out = [0.0]
    for x in xs:
        out.append(out[-1] + x)
    return out


def prepare(b):
    """Index by date plus prefix sums of dollar volume and absolute daily moves (for fast 60-day averages)."""
    c, v = b["close"], b["volume"]
    moves = [0.0] + [abs(c[i] / c[i - 1] - 1) for i in range(1, len(c))]
    return {**b, "_idx": {d: i for i, d in enumerate(b["date"])}, "_dv": prefix([x * y for x, y in zip(c, v)]),
            "_mv": prefix(moves)}


def metrics_at(b, i, mom=MOM, skip=0):
    """(60-day avg dollar volume, 60-day avg absolute daily move, momentum return) at index i, or None if too short."""
    if i < max(VOL_WIN, mom + skip):
        return None
    dvol = (b["_dv"][i + 1] - b["_dv"][i + 1 - VOL_WIN]) / VOL_WIN
    move = (b["_mv"][i + 1] - b["_mv"][i + 1 - VOL_WIN]) / VOL_WIN
    return dvol, move, b["close"][i - skip] / b["close"][i - skip - mom] - 1


def picks_at(stocks, day, n=TOP_N, mom=MOM, skip=0, need_positive=True):
    """The n strongest LITE-like stocks at this close: [(symbol, momentum)], strongest first."""
    rows = []
    for s, b in stocks.items():
        i = b["_idx"].get(day)
        m = metrics_at(b, i, mom, skip) if i is not None else None
        if m and m[0] >= MIN_DVOL and m[1] >= MIN_MOVE and (m[2] > 0 or not need_positive):
            rows.append((-m[2], s))
    rows.sort()
    return [(s, -r) for r, s in rows[:n]]


def price(b, d, field):
    """That day's open/close, or the last close before it if the stock didn't trade that day."""
    i = b["_idx"].get(d)
    if i is not None:
        return b[field][i]
    j = bisect.bisect_left(b["date"], d) - 1
    return b["close"][j] if j >= 0 else None


def simulate(stocks, allp, calendar, start, end, n=TOP_N, cost=COST, mom=MOM, skip=0, need_positive=True):
    """Daily equity from the open of `start` to the close of `end`, rebalancing on each month's first trading day."""
    days = [d for d in calendar if start <= d <= end]
    prior = [d for d in calendar if d < start]
    shares, cash, curve, log = {}, START_CASH, [], []
    for k, d in enumerate(days):
        if k == 0 or d[:7] != days[k - 1][:7]:
            form = days[k - 1] if k else prior[-1]
            chosen = [(s, r) for s, r in picks_at(stocks, form, n, mom, skip, need_positive) if d in allp[s]["_idx"]]
            weights = {s: 1 / n for s, _ in chosen}
            if len(chosen) < n:
                weights[FILL] = (n - len(chosen)) / n
            value = cash + sum(q * price(allp[s], d, "open") for s, q in shares.items())

            def targets(v):
                tgt = {s: w * v / price(allp[s], d, "open") for s, w in weights.items()}
                traded = sum(abs(tgt.get(s, 0.0) - shares.get(s, 0.0)) * price(allp[s], d, "open")
                             for s in set(tgt) | set(shares))
                return tgt, traded

            tgt, traded = targets(value)
            tgt, traded = targets(value - cost * traded)      # stay fully invested net of the fees
            fee = cost * traded
            cash = value - fee - sum(q * price(allp[s], d, "open") for s, q in tgt.items())
            shares = tgt
            log.append({"day": d, "formation": form, "picks": [[s, round(r, 4)] for s, r in chosen],
                        "smh_weight": round(weights.get(FILL, 0.0), 2), "value_at_open": round(value, 2),
                        "turnover": round(traded / value, 4), "fee": round(fee, 2)})
        curve.append((d, cash + sum(q * price(allp[s], d, "close") for s, q in shares.items())))
    return curve, log


def buy_and_hold(b, calendar, start, end, cost=COST):
    days = [d for d in calendar if start <= d <= end]
    q = START_CASH * (1 - cost) / price(b, days[0], "open")
    return [(d, q * price(b, d, "close")) for d in days]


def stats(curve):
    vals = [v for _, v in curve]
    peak, dd = START_CASH, 0.0
    for v in vals:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    years = (date.fromisoformat(curve[-1][0]) - date.fromisoformat(curve[0][0])).days / 365.25
    cagr = (vals[-1] / START_CASH) ** (1 / years) - 1
    return {"final": round(vals[-1]), "total_pct": round(100 * (vals[-1] / START_CASH - 1), 1),
            "cagr_pct": round(100 * cagr, 2), "max_drawdown_pct": round(100 * dd, 1),
            "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None}


def period_returns(curve, periods):
    value, dates, out = dict(curve), [d for d, _ in curve], {}
    for name, a, b in periods:
        inside = [d for d in dates if a <= d <= b]
        if not inside:
            continue
        before = [d for d in dates if d < inside[0]]
        out[name] = round(100 * (value[inside[-1]] / (value[before[-1]] if before else START_CASH) - 1), 1)
    return out


def years_of(curve):
    ys = sorted({d[:4] for d, _ in curve})
    return [(y, f"{y}-01-01", f"{y}-12-31") for y in ys]


def month_end_returns(curve):
    out, last, prev = [], {}, None
    for d, v in curve:
        last[d[:7]] = v
    for m in sorted(last):
        if prev is not None:
            out.append((m, last[m] / prev - 1))
        prev = last[m]
    return out


def evaluate(stocks, allp, calendar, start, **kw):
    curve, log = simulate(stocks, allp, calendar, start, END, **kw)
    smh = buy_and_hold(allp["SMH"], calendar, start, END)
    s, b = stats(curve), stats(smh)
    halves_s, halves_b = period_returns(curve, HALVES), period_returns(smh, HALVES)
    checks = {"1_cagr_above_smh": s["cagr_pct"] > b["cagr_pct"],
              "2_cagr_over_dd_above_smh": (s["cagr_over_dd"] or -9) > (b["cagr_over_dd"] or -9),
              "3_beats_smh_in_both_halves": all(halves_s.get(h, -1e9) > halves_b.get(h, 1e9) for h, _, _ in HALVES)}
    ms, mb = dict(month_end_returns(curve)), dict(month_end_returns(smh))
    common = [m for m in ms if m in mb]
    held = Counter(p[0] for e in log for p in e["picks"])
    return {"strategy": s, "smh": b, "halves": {"strategy": halves_s, "smh": halves_b}, "checks": checks,
            "passes": all(checks.values()),
            "years": {"strategy": period_returns(curve, years_of(curve)), "smh": period_returns(smh, years_of(smh))},
            "months_beating_smh_pct": round(100 * sum(ms[m] > mb[m] for m in common) / max(len(common), 1)),
            "worst_month_pct": round(100 * min(ms.values()), 1) if ms else None,
            "months_with_smh_slots": sum(e["smh_weight"] > 0 for e in log), "months": len(log),
            "avg_turnover_pct": round(100 * sum(e["turnover"] for e in log) / max(len(log), 1), 1),
            "most_held": held.most_common(15)}, curve, log


def main():
    stocks = {}
    for path in sorted(DATA.glob("*.csv.gz")):
        s = path.name[:-7]
        if s != "SPY":
            stocks[s] = prepare(load(s))
    etfs = {}
    for s in ETFS:
        with gzip.open(path_for(s), "rt") as f:
            etfs[s] = prepare(json.load(f))
    allp = {**stocks, **etfs}
    calendar = etfs["SPY"]["date"]
    main_res, curve, log = evaluate(stocks, allp, calendar, MAIN_START)
    stress, _, _ = evaluate(stocks, allp, calendar, STRESS_START)
    if main_res["passes"]:
        label = "PASS (robust)" if stress["strategy"]["cagr_over_dd"] >= stress["smh"]["cagr_over_dd"] else "PASS (post-COVID only)"
    else:
        label = "FAIL"
    bench = {s: stats(buy_and_hold(etfs[s], calendar, MAIN_START, END)) for s in ("SPY", "QQQ")}
    variants = {}
    for name, kw in (("top_3", {"n": 3}), ("momentum_12_1", {"mom": 231, "skip": 21}),
                     ("no_positive_filter", {"need_positive": False}), ("costs_0.25pct", {"cost": 0.0025})):
        res, _, _ = evaluate(stocks, allp, calendar, MAIN_START, **kw)
        variants[name] = {k: res[k] for k in ("strategy", "halves", "checks", "passes", "months_with_smh_slots")}
    out = {"plan": "output/LITE_LIKE_MOMENTUM_TEST_PLAN_20261005.md", "verdict": label, "main": main_res,
           "stress_since_2016": {k: stress[k] for k in ("strategy", "smh", "checks", "months_with_smh_slots", "months")},
           "benchmarks_main": bench, "variants": variants, "log_main": log,
           "curve_main": [[d, round(v, 2)] for d, v in curve]}
    OUT.write_text(json.dumps(out, default=str) + "\n")
    write_manifest(OUT, code=["research/momentum_lite_like_v1/backtest.py", "research/momentum_lite_like_v1/fetch_etfs.py"],
                   data=[str(DATA / f"{s}.csv.gz") for s in sorted(stocks)] + [str(path_for(s)) for s in ETFS],
                   params={"min_dvol": MIN_DVOL, "min_move": MIN_MOVE, "vol_win": VOL_WIN, "mom": MOM, "top_n": TOP_N,
                           "cost": COST, "start": MAIN_START, "end": END})
    show = {k: main_res[k] for k in ("strategy", "smh", "halves", "checks", "months_beating_smh_pct", "worst_month_pct",
                                     "months_with_smh_slots", "months", "avg_turnover_pct", "most_held")}
    print(json.dumps({"verdict": label, **show, "years": main_res["years"], "benchmarks": bench,
                      "stress": out["stress_since_2016"], "variants": {k: {"strategy": v["strategy"], "passes": v["passes"]}
                                                                      for k, v in variants.items()}}, indent=1))


if __name__ == "__main__":
    main()
