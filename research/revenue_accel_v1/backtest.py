"""Backtest of pre-declared test #20, the LITE business fingerprint (output/REVENUE_ACCELERATION_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.revenue_accel_v1.backtest

At each month-end close, using only revenue known 90 days after each quarter ended: flag companies whose latest
quarter's revenue is >= $50M, grew >= 25% year over year, and sped up (growth >= 10 points faster than the quarter
before, which was itself at least as fast as the one before); 60-day average dollar volume >= $20M. Hold the 20 with
the biggest speed-up, equal weight, empty slots in SPY; trade at the next open with 0.1% per side. Research only.
Growth always compares a quarter with its year-ago quarter under the same revenue tag, and the latest quarter must have
ended within 200 days (both fixed before any result; see the plan's corrections).
"""
from __future__ import annotations

import bisect
from collections import Counter
from datetime import date
import gzip
import json
from pathlib import Path

from research.breakout_test_v1.backtest import DATA, load
from research.momentum_lite_like_v1.fetch_etfs import ETFS, path_for as etf_path
from research.provenance_v1.provenance import write_manifest
from research.revenue_accel_v1.fetch_frames import CONCEPTS, OUT as RAW, QUARTERS, YEARS, path_for as frame_path
from research.revenue_accel_v1.revenue import fingerprint, flagged, load_frames, quarterly

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/revenue-acceleration-test-results.json"
START_CASH, TOP_N, COST, FILL, LAG, MIN_DVOL = 100_000.0, 20, 0.001, "SPY", 90, 20e6
MAIN_START, STRESS_START, END = "2020-01-02", "2017-01-03", "2026-09-28"
HALVES = (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2026", "2023-01-01", "2026-12-31"))
CASES = ("LITE", "MU", "SNDK")


def prepare(b):
    pdv = [0.0]
    for c, v in zip(b["close"], b["volume"]):
        pdv.append(pdv[-1] + c * v)
    return {**b, "_idx": {d: i for i, d in enumerate(b["date"])}, "_pdv": pdv}


def company_tickers(symbols, rows=None):
    """{cik: ticker} for companies whose SEC ticker (BRK-B -> BRK.B) has a price file; SEC's first listed ticker wins."""
    if rows is None:
        with gzip.open(RAW / "company_tickers.json.gz", "rt") as f:
            rows = json.load(f)
    out, used = {}, set()
    for _, r in sorted(rows.items(), key=lambda kv: int(kv[0])):
        t, cik = r["ticker"].upper().replace("-", "."), int(r["cik_str"])
        if t in symbols and cik not in out and t not in used:
            out[cik] = t
            used.add(t)
    return out


def ranked(day, stocks, quarters, tickers, lag=LAG, need_accel=True, run_filter=False):
    """Every company flagged at this month-end close, best first: [(ticker, score, fingerprint)]."""
    rows = []
    for cik, t in tickers.items():
        b = stocks.get(t)
        i = b["_idx"].get(day) if b else None
        if i is None or i < 59 or (b["_pdv"][i + 1] - b["_pdv"][i - 59]) / 60 < MIN_DVOL:
            continue
        fp = fingerprint(quarters.get(cik, []), day, lag)
        if not flagged(fp, need_accel=need_accel):
            continue
        if run_filter and (i < 252 or b["close"][i] / b["close"][i - 252] - 1 >= 1.0):
            continue
        score = fp[1] - fp[2] if need_accel else fp[1]
        rows.append((-score, t, fp))
    rows.sort(key=lambda r: (r[0], r[1]))
    return [(t, -s, fp) for s, t, fp in rows]


def picks_at(day, stocks, quarters, tickers, n=TOP_N, **kw):
    """(the top n of `ranked`, number flagged)."""
    rows = ranked(day, stocks, quarters, tickers, **kw)
    return rows[:n], len(rows)


def price(b, d, field):
    i = b["_idx"].get(d)
    if i is not None:
        return b[field][i]
    k = bisect.bisect_left(b["date"], d) - 1                   # no bar that day: the last close before it
    return b["close"][k] if k >= 0 else None


def simulate(allp, calendar, start, end, choose, n=TOP_N, cost=COST):
    """Daily equity from the open of `start`; on each month's first trading day, buy `choose(previous close day)`."""
    days = [d for d in calendar if start <= d <= end]
    prior = [d for d in calendar if d < start]
    shares, cash, curve, log = {}, START_CASH, [], []
    for k, d in enumerate(days):
        if k == 0 or d[:7] != days[k - 1][:7]:
            form = days[k - 1] if k else prior[-1]
            top, n_flagged = choose(form)
            chosen = [c for c in top if d in allp[c[0]]["_idx"]]       # no bar at this open: its slot goes to SPY
            weights = {t: 1 / n for t, _, _ in chosen}
            if len(chosen) < n:
                weights[FILL] = weights.get(FILL, 0.0) + (n - len(chosen)) / n
            value = cash + sum(q * price(allp[s], d, "open") for s, q in shares.items())

            def targets(v):
                tgt = {s: w * v / price(allp[s], d, "open") for s, w in weights.items()}
                traded = sum(abs(tgt.get(s, 0.0) - shares.get(s, 0.0)) * price(allp[s], d, "open")
                             for s in set(tgt) | set(shares))
                return tgt, traded

            tgt, traded = targets(value)
            tgt, traded = targets(value - cost * traded)
            fee = cost * traded
            cash = value - fee - sum(q * price(allp[s], d, "open") for s, q in tgt.items())
            shares = tgt
            log.append({"day": d, "formation": form, "flagged": n_flagged,
                        "picks": [[t, round(s, 4), [round(x, 4) for x in fp]] for t, s, fp in chosen],
                        "skipped_no_bar": [c[0] for c in top if c not in chosen],
                        "spy_weight": round(weights.get(FILL, 0.0), 2), "value_at_open": round(value, 2),
                        "turnover": round(traded / value, 4), "fee": round(fee, 2)})
        curve.append((d, cash + sum(q * price(allp[s], d, "close") for s, q in shares.items())))
    return curve, log


def next_day(calendar, d):
    return calendar[bisect.bisect_right(calendar, d)]


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
        if inside:
            before = [d for d in dates if d < inside[0]]
            out[name] = round(100 * (value[inside[-1]] / (value[before[-1]] if before else START_CASH) - 1), 1)
    return out


def years_of(curve):
    return [(y, f"{y}-01-01", f"{y}-12-31") for y in sorted({d[:4] for d, _ in curve})]


def evaluate(allp, calendar, start, choose, n=TOP_N):
    curve, log = simulate(allp, calendar, start, END, choose, n)
    spy = buy_and_hold(allp["SPY"], calendar, start, END)
    s, b = stats(curve), stats(spy)
    hs, hb = period_returns(curve, HALVES), period_returns(spy, HALVES)
    checks = {"1_cagr_above_spy": s["cagr_pct"] > b["cagr_pct"],
              "2_cagr_over_dd_above_spy": (s["cagr_over_dd"] or -9) > (b["cagr_over_dd"] or -9),
              "3_beats_spy_in_both_halves": all(hs.get(h, -1e9) > hb.get(h, 1e9) for h, _, _ in HALVES)}
    held = Counter(p[0] for e in log for p in e["picks"])
    skipped = sum(len(e["skipped_no_bar"]) for e in log)
    return {"strategy": s, "spy": b, "halves": {"strategy": hs, "spy": hb}, "checks": checks, "passes": all(checks.values()),
            "years": {"strategy": period_returns(curve, years_of(curve)), "spy": period_returns(spy, years_of(spy))},
            "months": len(log), "months_with_spy_slots": sum(e["spy_weight"] > 0 for e in log),
            "avg_flagged": round(sum(e["flagged"] for e in log) / max(len(log), 1), 1),
            "flagged_range": [min(e["flagged"] for e in log), max(e["flagged"] for e in log)],
            "avg_turnover_pct": round(100 * sum(e["turnover"] for e in log) / max(len(log), 1), 1),
            "picks_skipped_no_bar": skipped, "distinct_stocks_held": len(held), "most_held": held.most_common(15)}, curve, log


def main():
    stocks = {}
    for path in sorted(DATA.glob("*.csv.gz")):
        s = path.name[:-7]
        if s != "SPY":
            stocks[s] = prepare(load(s))
    etfs = {}
    for s in ETFS:
        with gzip.open(etf_path(s), "rt") as f:
            etfs[s] = prepare(json.load(f))
    allp = {**stocks, **etfs}
    calendar = etfs["SPY"]["date"]
    quarters = quarterly(load_frames())
    tickers = company_tickers(set(stocks))

    def chooser(**kw):
        return lambda day: picks_at(day, stocks, quarters, tickers, **kw)

    main_res, curve, log = evaluate(allp, calendar, MAIN_START, chooser())
    stress, _, _ = evaluate(allp, calendar, STRESS_START, chooser())
    if main_res["passes"]:
        verdict = "PASS (robust)" if stress["strategy"]["cagr_over_dd"] > stress["spy"]["cagr_over_dd"] else "PASS (post-COVID only)"
    else:
        verdict = "FAIL"
    bench = {s: stats(buy_and_hold(etfs[s], calendar, MAIN_START, END)) for s in ("SMH", "QQQ")}
    info = {}
    for name, kw, n in (("top_10", {"n": 10}, 10), ("no_speed_up_rule", {"need_accel": False}, TOP_N),
                        ("hasnt_run_yet_filter", {"run_filter": True}, TOP_N), ("lag_60_days", {"lag": 60}, TOP_N)):
        res, _, _ = evaluate(allp, calendar, MAIN_START, chooser(**kw), n)
        info[name] = {k: res[k] for k in ("strategy", "halves", "checks", "passes", "avg_flagged", "months_with_spy_slots")}
    cases = {t: [] for t in CASES}
    for e in log:
        for rank, (t, score, fp) in enumerate(ranked(e["formation"], stocks, quarters, tickers), 1):
            if t in cases:
                cases[t].append({"formation": e["formation"], "rank": rank, "held": rank <= TOP_N,
                                 "growth_pct": round(100 * fp[1], 1), "speed_up_pts": round(100 * score, 1)})
    cases = {t: {"months_flagged": len(v), "months_held": sum(x["held"] for x in v),
                 "first_flag": v[0] if v else None, "flags": v,
                 "price_first_flag_open": price(stocks[t], next_day(calendar, v[0]["formation"]), "open") if v else None,
                 "price_end": price(stocks[t], END, "close")} for t, v in cases.items()}
    out = {"plan": "output/REVENUE_ACCELERATION_TEST_PLAN_20261005.md", "verdict": verdict, "main": main_res,
           "stress_since_2017": {k: stress[k] for k in ("strategy", "spy", "checks", "months_with_spy_slots", "months")},
           "benchmarks_main": bench, "info": info, "cases": cases, "companies_mapped": len(tickers),
           "log_main": log, "curve_main": [[d, round(v, 2)] for d, v in curve]}
    OUT.write_text(json.dumps(out, default=str) + "\n")
    frames = [str(frame_path(c, p)) for c in CONCEPTS for p in QUARTERS + YEARS if frame_path(c, p).exists()]
    write_manifest(OUT, code=["research/revenue_accel_v1/backtest.py", "research/revenue_accel_v1/revenue.py",
                              "research/revenue_accel_v1/fetch_frames.py"],
                   data=frames + [str(RAW / "company_tickers.json.gz")] + [str(DATA / f"{s}.csv.gz") for s in sorted(stocks)]
                   + [str(etf_path(s)) for s in ETFS],
                   params={"top_n": TOP_N, "lag": LAG, "max_age_days": 200, "min_dvol": MIN_DVOL, "cost": COST,
                           "start": MAIN_START, "stress_start": STRESS_START, "end": END})
    show = {k: main_res[k] for k in ("strategy", "spy", "halves", "checks", "months_with_spy_slots", "avg_flagged",
                                     "flagged_range", "avg_turnover_pct", "picks_skipped_no_bar", "distinct_stocks_held",
                                     "most_held")}
    brief = {t: {k: v for k, v in c.items() if k != "flags"} for t, c in cases.items()}
    print(json.dumps({"verdict": verdict, **show, "years": main_res["years"], "benchmarks": bench,
                      "stress": out["stress_since_2017"], "cases": brief, "companies_mapped": len(tickers),
                      "info": {k: {"strategy": v["strategy"], "passes": v["passes"], "avg_flagged": v["avg_flagged"]}
                               for k, v in info.items()}}, indent=1, default=str))


if __name__ == "__main__":
    main()
