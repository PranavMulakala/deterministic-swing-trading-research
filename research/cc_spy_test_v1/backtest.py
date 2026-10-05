"""Backtest of pre-declared test #13: monthly SPY covered calls vs holding SPY (output/COVERED_CALL_SPY_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.cc_spy_test_v1.backtest

Reuses the OPRA snapshots and helpers of test #10 (research/csp_spy_test_v1, research/spy_put_spread_backtest_v1).
Dividends: shares x previous raw close x (adjusted return - raw return), from the dividend-adjusted SPY closes on disk
and Alpaca raw daily closes (cached in outputs/cc_spy_data/). Research only.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
import math
from pathlib import Path

from research.breakout_test_v1.backtest import load as load_daily
from research.csp_spy_test_v1.backtest import FIRST, LAST, drawdown, halves, stats_for
from research.provenance_v1.provenance import write_manifest
from research.spy_put_spread_backtest_v1.backtest import (DATA, Q, available_days, load_day, load_rates, norm_cdf,
                                                          parity_spot)

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "outputs/cc_spy_data"
START_EQUITY, FEE, SLIP, DTE_MIN, DTE_MAX, DTE_TARGET = 100_000.0, 0.03, 0.0001, 21, 45, 30
VARIANTS = {"main_delta30_bid": (0.30, "bid", True), "info_delta30_mid": (0.30, "mid", True),
            "info_delta20_bid": (0.20, "bid", True), "info_atm_delta50_bid": (0.50, "bid", False)}
SHOCKS = {"covid_removed": [("2020-02-20", "2020-04-30")],
          "all_big_shocks_removed": [("2020-02-20", "2020-04-30"), ("2018-02-01", "2018-02-28"),
                                     ("2024-07-31", "2024-08-15"), ("2025-04-02", "2025-04-30")]}


def bs_call(s, k, t, r, sigma, q=Q):
    if t <= 0 or sigma <= 0:
        return max(s - k, 0.0), (1.0 if s > k else 0.0)
    d1 = (math.log(s / k) + (r - q + sigma * sigma / 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    return s * math.exp(-q * t) * norm_cdf(d1) - k * math.exp(-r * t) * norm_cdf(d2), math.exp(-q * t) * norm_cdf(d1)


def call_iv(price, s, k, t, r, q=Q):
    intrinsic = max(s * math.exp(-q * t) - k * math.exp(-r * t), 0.0)
    if t <= 0 or price <= intrinsic + 1e-6:
        return None
    lo, hi = 0.005, 4.0
    if bs_call(s, k, t, r, hi, q)[0] < price:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if bs_call(s, k, t, r, mid, q)[0] > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def pick_call(quotes, day, spot, r, target_delta, above_spot=True):
    expirations = sorted({k[0] for k in quotes if k[1] == "C" and DTE_MIN <= (k[0] - day).days <= DTE_MAX})
    if not expirations or spot is None:
        return None
    expiration = min(expirations, key=lambda e: (abs((e - day).days - DTE_TARGET), e))
    t = ((expiration - day).days + 5.5 / 24) / 365
    best = None
    for (e, typ, strike), (bid, ask) in quotes.items():
        if e != expiration or typ != "C" or (above_spot and strike <= spot) or bid <= 0:
            continue
        iv = call_iv((bid + ask) / 2, spot, strike, t, r)
        if iv is None:
            continue
        delta = bs_call(spot, strike, t, r, iv)[1]
        key = (abs(delta - target_delta), strike)
        if best is None or key < best[0]:
            best = (key, (expiration, strike, bid, ask, delta))
    return best[1] if best else None


def lots_for(cash, price):
    return math.floor(cash / (100 * price * (1 + SLIP)))


class Account:
    def __init__(self, target_delta, fill, above_spot):
        self.target_delta, self.fill, self.above_spot = target_delta, fill, above_spot
        self.cash, self.shares, self.call, self.prev_day, self.last_spot = START_EQUITY, 0, None, None, None
        self.trades, self.buys, self.curve, self.cycle_marks = [], [], [], []
        self.interest = self.dividends = 0.0
        self.stats = Counter()

    def step(self, day, morning, close, m_spot, c_spot, r, div_per_share):
        if self.prev_day is not None:
            earned = self.cash * r * (day - self.prev_day).days / 365
            self.cash += earned
            self.interest += earned
        self.prev_day = day
        if self.shares and div_per_share:
            self.cash += self.shares * div_per_share
            self.dividends += self.shares * div_per_share
        c = self.call
        if c and day >= c["expiration"]:
            if c_spot is None:
                self.stats["settle_waited_missing_spot"] += 1
            else:
                called = c_spot > c["strike"]
                if called:
                    self.cash += c["strike"] * 100 * c["contracts"]
                    self.shares -= 100 * c["contracts"]
                self.trades.append({**{k: (v.isoformat() if isinstance(v, date) else v) for k, v in c.items() if k != "mark"},
                                    "settle_day": day.isoformat(), "settle_spot": round(c_spot, 4), "called_away": called,
                                    "upside_given_up": round(max(c_spot - c["strike"], 0) * 100 * c["contracts"], 2)})
                self.call = None
        elif not c and m_spot is not None:
            n = lots_for(self.cash, m_spot)
            if n >= 1:
                price = m_spot * (1 + SLIP)
                self.cash -= n * 100 * price
                self.shares += n * 100
                self.buys.append({"day": day.isoformat(), "shares": n * 100, "price": round(price, 4)})
            if self.shares >= 100:
                pick = pick_call(morning, day, m_spot, r, self.target_delta, self.above_spot)
                if pick is None:
                    self.stats["sell_skipped_no_quote"] += 1
                else:
                    expiration, strike, bid, ask, delta = pick
                    contracts = self.shares // 100
                    price = bid if self.fill == "bid" else (bid + ask) / 2
                    premium, fees = price * 100 * contracts, FEE * contracts
                    self.cash += premium - fees
                    self.call = {"entry_day": day, "expiration": expiration, "strike": strike, "contracts": contracts,
                                 "sale_price": price, "delta": round(delta, 3), "entry_spot": round(m_spot, 4),
                                 "premium": round(premium, 2), "fees": round(fees, 2), "mark": price}
                    self.cycle_marks.append(day.isoformat())
        if c_spot is not None:
            self.last_spot = c_spot
        c = self.call
        if c:
            q = close.get((c["expiration"], "C", c["strike"]))
            if q:
                c["mark"] = (q[0] + q[1]) / 2
            elif self.last_spot is not None and day >= c["expiration"]:
                c["mark"] = max(self.last_spot - c["strike"], 0.0)
        spot = self.last_spot or m_spot or 0.0
        equity = self.shares * spot + self.cash - (c["mark"] * 100 * c["contracts"] if c else 0.0)
        self.curve.append((day.isoformat(), equity))


def zero_windows(curve, windows):
    """Rebuild a value curve with daily returns set to 0 inside the given [start, end] date windows."""
    out, value, prev = [], curve[0][1], curve[0][1]
    for d, v in curve:
        ret = v / prev - 1 if prev else 0.0
        prev = v
        if any(a <= d <= b for a, b in windows):
            ret = 0.0
        value *= 1 + ret
        out.append((d, value))
    return out


def cycle_profit_factor(acct):
    value = dict(acct.curve)
    marks = acct.cycle_marks + [acct.curve[-1][0]]
    pnls = [value[b] - value[a] for a, b in zip(marks, marks[1:])]
    gains, losses = sum(p for p in pnls if p > 0), -sum(p for p in pnls if p <= 0)
    return (round(gains / losses, 2) if losses else None), pnls


def report(acct, bench_curve, years):
    curve = [("start", START_EQUITY)] + acct.curve
    s = stats_for(curve, years)
    bench = stats_for(bench_curve, years)
    pf, pnls = cycle_profit_factor(acct)
    trades = acct.trades
    by_year = defaultdict(float)
    vals = dict(acct.curve)
    for y in sorted({d[:4] for d, _ in acct.curve}):
        ys = [d for d, _ in acct.curve if d[:4] == y]
        prev = [d for d, _ in acct.curve if d < ys[0]]
        by_year[y] = round((vals[ys[-1]] / (vals[prev[-1]] if prev else START_EQUITY) - 1) * 100, 1)
    result = {**s, "final_equity": round(acct.curve[-1][1]), "cycles": len(pnls), "cycle_profit_factor": pf,
              "calls_sold": len(trades) + (1 if acct.call else 0),
              "called_away_pct": round(100 * sum(t["called_away"] for t in trades) / max(len(trades), 1), 1),
              "premium_collected_usd": round(sum(t["premium"] - t["fees"] for t in trades)),
              "upside_given_up_usd": round(sum(t["upside_given_up"] for t in trades)),
              "dividends_usd": round(acct.dividends), "interest_usd": round(acct.interest),
              "halves_return_pct": halves(acct.curve), "return_by_year_pct": dict(by_year),
              "best_cycle_usd": round(max(pnls)), "worst_cycle_usd": round(min(pnls)),
              "median_delta": sorted(t["delta"] for t in trades)[len(trades) // 2] if trades else None,
              "median_otm_pct": sorted(round((t["strike"] / t["entry_spot"] - 1) * 100, 2) for t in trades)[len(trades) // 2]
              if trades else None, "stats": dict(acct.stats)}
    checks = {"A1_cycle_profit_factor_at_least_1.3": (pf or 0) >= 1.3,
              "A2_profitable_in_both_halves": all(v > 0 for v in result["halves_return_pct"].values()),
              "A3_max_drawdown_at_most_25pct": result["max_drawdown_pct"] >= -25.0,
              "B1_drawdown_5pts_smaller_than_spy": result["max_drawdown_pct"] >= bench["max_drawdown_pct"] + 5,
              "B2_cagr_over_dd_beats_spy": (result["cagr_over_dd"] or -9) > bench["cagr_over_dd"]}
    result["checks"], result["passes"] = checks, all(checks.values())
    result["shock_views"] = {}
    for name, windows in SHOCKS.items():
        strat = stats_for([("start", START_EQUITY)] + zero_windows(acct.curve, windows), years)
        spy = stats_for(zero_windows(bench_curve, windows), years)
        result["shock_views"][name] = {"strategy": strat, "spy": spy}
    result["trade_list"], result["buy_list"] = trades, acct.buys
    return result


def raw_spy_closes():
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "spy_raw_daily_2015-12_2026-01.json"
    if path.exists():
        return json.loads(path.read_text())
    from research.lite_buy_timing_v1.run import bars
    from research.lite_paper_bot_v1.bot import credentials
    key, secret = credentials()
    rows = bars("SPY", "1Day", "2015-12-01T00:00:00Z", "2026-01-05T00:00:00Z", key, secret, adjustment="raw")
    out = {r["t"][:10]: r["c"] for r in rows}
    path.write_text(json.dumps(out))
    return out


def dividends_per_share(days):
    spy = load_daily("SPY")
    adj = dict(zip(spy["date"], spy["close"]))
    raw = raw_spy_closes()
    out, prev = {}, None
    for d in days:
        iso = d.isoformat()
        if prev and iso in adj and prev in adj and iso in raw and prev in raw:
            gap = adj[iso] / adj[prev] - raw[iso] / raw[prev]
            if gap > 0.0005:  # ex-dividend day (SPY pays quarterly, ~0.3-0.5% each)
                out[iso] = gap * raw[prev]
        prev = iso
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/cc-spy-test-results.json")
    args = parser.parse_args()
    days = [d for d in available_days() if FIRST <= d <= LAST]
    rates = load_rates()
    divs = dividends_per_share(days)
    accounts = {name: Account(*v) for name, v in VARIANTS.items()}
    for n, day in enumerate(days, 1):
        snap = load_day(DATA / str(day.year) / f"{day.isoformat()}.csv.gz")
        morning, close = snap.get("t1030", {}), snap.get("close", {})
        r = rates.get(day.strftime("%Y-%m"), 0.0)
        m_spot, c_spot = parity_spot(morning, day, r, 5.5), parity_spot(close, day, r, 0)
        for acct in accounts.values():
            acct.step(day, morning, close, m_spot, c_spot, r, divs.get(day.isoformat(), 0.0))
        if n % 500 == 0:
            print(json.dumps({"days": n, "of": len(days)}), flush=True)
    spy = load_daily("SPY")
    window = [(d, c) for d, c in zip(spy["date"], spy["close"]) if days[0].isoformat() <= d <= days[-1].isoformat()]
    years = len(days) / 252
    out = {"plan": "output/COVERED_CALL_SPY_TEST_PLAN_20261005.md", "first": days[0].isoformat(),
           "last": days[-1].isoformat(), "data_days": len(days), "dividend_days": len(divs),
           "dividends_per_share_total": round(sum(divs.values()), 2), "spy_with_dividends": stats_for(window, years),
           "results": {name: report(acct, window, years) for name, acct in accounts.items()}}
    out["verdict_pass"] = out["results"]["main_delta30_bid"]["passes"]
    Path(args.output).write_text(json.dumps(out, indent=1, default=str) + "\n")
    write_manifest(args.output, code=["research/cc_spy_test_v1/backtest.py", "research/csp_spy_test_v1/backtest.py"],
                   data=[str(DATA / str(d.year) / f"{d.isoformat()}.csv.gz") for d in days] +
                   ["outputs/breakout_data/SPY.csv.gz", str(CACHE / "spy_raw_daily_2015-12_2026-01.json")],
                   params={"variants": VARIANTS, "shocks": SHOCKS, "fee": FEE, "slip": SLIP})
    print(json.dumps({"spy_with_dividends": out["spy_with_dividends"], "verdict_pass": out["verdict_pass"],
                      "dividend_days": out["dividend_days"], "dividends_per_share_total": out["dividends_per_share_total"],
                      **{k: {x: y for x, y in v.items() if x not in ("trade_list", "buy_list")}
                         for k, v in out["results"].items()}}, indent=1))


if __name__ == "__main__":
    main()
