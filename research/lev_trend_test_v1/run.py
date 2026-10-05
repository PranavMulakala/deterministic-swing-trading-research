"""Pre-declared test #14: 2x leverage only above the 200-day average vs holding the market
(output/LEVERAGE_TREND_TEST_PLAN_20261005.md). Research only.

  PYTHONPATH=src:. .venv/bin/python -m research.lev_trend_test_v1.run

Main data: Ken French daily factors 1926-2026 (market total return = Mkt-RF + RF; cash = RF).
Real-fund check: Alpaca SPY/SSO/QQQ/QLD 2016-2025.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from research.provenance_v1.provenance import write_manifest

ROOT = Path(__file__).resolve().parents[2]
FRENCH = ROOT / "outputs/lev_trend_data/F-F_Research_Data_Factors_daily.csv"
OUT = ROOT / "output/lev-trend-test-results.json"
SMA_DAYS, SWITCH_COST, SPREAD = 200, 0.001, 0.005
COSTS = {1: 0.0, 2: 0.0090, 3: 0.0095}   # yearly fund expense by leverage (1x = the raw market, like the benchmark)
HALVES = (("1927-1975", "19270101", "19751231"), ("1976-2026", "19760101", "20261231"))
WORST_YEARS = ("1929", "1930", "1931", "1932", "1937", "1973", "1974", "1987", "2000", "2001", "2002", "2008",
               "2020", "2022")


def load_french(path=FRENCH):
    dates, mkt, rf = [], [], []
    for line in path.read_text().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 5 and len(parts[0]) == 8 and parts[0].isdigit():
            dates.append(parts[0])
            mkt.append((float(parts[1]) + float(parts[4])) / 100)
            rf.append(float(parts[4]) / 100)
    return dates, mkt, rf


def lev_return(m, cash, lev):
    """Daily return of a daily-rebalanced lev x fund: lev*m - (lev-1)*(cash + spread/252) - expense/252."""
    return lev * m - (lev - 1) * (cash + SPREAD / 252) - COSTS[lev] / 252


def signals(levels, n=SMA_DAYS):
    """signal[t] = True if levels[t] > mean(levels[t-n+1..t]); None until n values exist."""
    out, total = [], 0.0
    for t, v in enumerate(levels):
        total += v
        if t >= n:
            total -= levels[t - n]
        out.append(None if t < n - 1 else v > total / n)
    return out


def run_strategy(mkt, rf, sig, lev, filtered, start):
    """Equity curve from index `start` (the day after the first signal). Position for day t uses sig[t-1]."""
    equity, curve, switches, invested_days, prev_pos = 1.0, [], 0, 0, None
    for t in range(start, len(mkt)):
        pos = (sig[t - 1] if filtered else True)
        if prev_pos is not None and pos != prev_pos:
            equity *= 1 - SWITCH_COST
            switches += 1
        prev_pos = pos
        r = lev_return(mkt[t], rf[t], lev) if pos else rf[t]
        invested_days += bool(pos)
        equity *= 1 + r
        curve.append(equity)
    return curve, switches, invested_days


def stats(dates, curve, start_value=1.0):
    d0, d1 = date(int(dates[0][:4]), int(dates[0][4:6]), int(dates[0][6:])), \
        date(int(dates[-1][:4]), int(dates[-1][4:6]), int(dates[-1][6:]))
    years = (d1 - d0).days / 365.25
    total = curve[-1] / start_value
    peak, dd, trough_date = start_value, 0.0, None
    for d, v in zip(dates, curve):
        peak = max(peak, v)
        if v / peak - 1 < dd:
            dd, trough_date = v / peak - 1, d
    cagr = total ** (1 / years) - 1
    return {"from": dates[0], "to": dates[-1], "growth_of_1": round(total, 2), "cagr_pct": round(cagr * 100, 2),
            "max_drawdown_pct": round(dd * 100, 1), "worst_drop_bottom": trough_date,
            "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None}


def sub_stats(dates, curve, a, b):
    idx = [i for i, d in enumerate(dates) if a <= d <= b]
    if not idx:
        return None
    base = curve[idx[0] - 1] if idx[0] > 0 else 1.0
    return stats([dates[i] for i in idx], [curve[i] for i in idx], base)


def calendar_returns(dates, curve):
    out, prev_end, cur_year, last = {}, 1.0, dates[0][:4], 1.0
    for d, v in zip(dates, curve):
        if d[:4] != cur_year:
            out[cur_year] = round((last / prev_end - 1) * 100, 1)
            prev_end, cur_year = last, d[:4]
        last = v
    out[cur_year] = round((last / prev_end - 1) * 100, 1)
    return out


def real_fund_check(rf_by_date):
    from research.lite_buy_timing_v1.run import bars
    from research.lite_paper_bot_v1.bot import credentials
    key, secret = credentials()
    px = {}
    for sym in ("SPY", "SSO", "QQQ", "QLD"):
        rows = bars(sym, "1Day", "2016-01-01T00:00:00Z", "2026-01-01T00:00:00Z", key, secret, adjustment="all")
        px[sym] = {r["t"][:10].replace("-", ""): r["c"] for r in rows}
    days = sorted(set.intersection(*(set(v) for v in px.values())) & set(rf_by_date))
    ret = {s: [px[s][days[i]] / px[s][days[i - 1]] - 1 for i in range(1, len(days))] for s in px}
    rf = [rf_by_date[d] for d in days[1:]]
    dd = days[1:]
    sim = [1.0]
    for m, c in zip(ret["SPY"], rf):
        sim.append(sim[-1] * (1 + lev_return(m, c, 2)))
    actual_sso = [px["SSO"][d] / px["SSO"][days[0]] for d in days]
    sim_stats, sso_stats = stats(days, sim), stats(days, actual_sso)
    # QQQ version on real funds: QLD when QQQ > its 200-day SMA (signal lagged a day), else T-bills
    qqq_levels = [px["QQQ"][d] for d in days]
    sig = signals(qqq_levels)
    start = SMA_DAYS
    eq, curve, prev, switches = 1.0, [], None, 0
    for t in range(start, len(days)):
        pos = sig[t - 1]
        if prev is not None and pos != prev:
            eq *= 1 - SWITCH_COST
            switches += 1
        prev = pos
        eq *= 1 + (px["QLD"][days[t]] / px["QLD"][days[t - 1]] - 1 if pos else rf_by_date[days[t]])
        curve.append(eq)
    window = days[start:]
    hold = {s: [px[s][d] / px[s][days[start - 1]] for d in window] for s in ("QQQ", "QLD", "SPY")}
    return {"simulated_2x_spy_vs_actual_SSO": {"simulated": sim_stats, "actual_SSO": sso_stats,
                                               "cagr_gap_pts": round(sim_stats["cagr_pct"] - sso_stats["cagr_pct"], 2)},
            "qqq_version_real_funds": {"QLD_above_200d_else_tbills": {**stats(window, curve), "switches": switches},
                                       "hold_QQQ": stats(window, hold["QQQ"]), "hold_QLD": stats(window, hold["QLD"]),
                                       "hold_SPY": stats(window, hold["SPY"])}}


def main():
    dates, mkt, rf = load_french()
    levels, lv = [], 1.0
    for m in mkt:
        lv *= 1 + m
        levels.append(lv)
    sig = signals(levels)
    start = SMA_DAYS            # first day whose position can use a signal (sig[SMA_DAYS-1] exists)
    dd = dates[start:]
    years = (date(int(dd[-1][:4]), int(dd[-1][4:6]), int(dd[-1][6:])) -
             date(int(dd[0][:4]), int(dd[0][4:6]), int(dd[0][6:]))).days / 365.25
    variants = {"market_1x_hold": (1, False), "main_2x_above_200d": (2, True), "hold_2x": (2, False),
                "info_1x_above_200d": (1, True), "info_3x_above_200d": (3, True), "info_hold_3x": (3, False)}
    results, curves = {}, {}
    for name, (lev, filt) in variants.items():
        curve, switches, inv = run_strategy(mkt, rf, sig, lev, filt, start)
        curves[name] = curve
        r = stats(dd, curve)
        r.update({"switches_per_year": round(switches / years, 2), "time_invested_pct": round(100 * inv / len(dd), 1),
                  "halves": {h: sub_stats(dd, curve, a, b) for h, a, b in HALVES},
                  "since_1990": sub_stats(dd, curve, "19900101", "20261231"),
                  "since_2000": sub_stats(dd, curve, "20000101", "20261231"),
                  "decades_cagr_pct": {f"{y}s": (sub_stats(dd, curve, f"{y}0101", f"{y + 9}1231") or {}).get("cagr_pct")
                                       for y in range(1920, 2030, 10)}})
        cal = calendar_returns(dd, curve)
        r["worst_years_pct"] = {y: cal.get(y) for y in WORST_YEARS}
        results[name] = r
    m, b = results["main_2x_above_200d"], results["market_1x_hold"]
    checks = {"1_cagr_at_least_2pts_higher": m["cagr_pct"] >= b["cagr_pct"] + 2,
              "2_worst_drop_no_worse": m["max_drawdown_pct"] >= b["max_drawdown_pct"],
              "3_cagr_over_dd_higher": (m["cagr_over_dd"] or -9) > (b["cagr_over_dd"] or 9),
              "4_higher_cagr_both_halves": all(m["halves"][h]["cagr_pct"] > b["halves"][h]["cagr_pct"] for h, _, _ in HALVES)}
    out = {"plan": "output/LEVERAGE_TREND_TEST_PLAN_20261005.md", "data": "Ken French daily factors (CRSP 202608)",
           "first_day": dd[0], "last_day": dd[-1], "years": round(years, 2), "results": results,
           "checks": checks, "verdict_pass": all(checks.values()),
           "real_fund_check": real_fund_check(dict(zip(dates, rf)))}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    write_manifest(OUT, code=["research/lev_trend_test_v1/run.py"], data=[str(FRENCH)],
                   params={"sma": SMA_DAYS, "switch_cost": SWITCH_COST, "spread": SPREAD, "costs": COSTS})
    print(json.dumps({k: v for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    main()
