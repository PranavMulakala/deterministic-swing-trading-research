"""Backtest of pre-declared test #10: monthly SPY cash-secured puts vs holding SPY (output/CSP_SPY_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.csp_spy_test_v1.backtest

Reuses the Databento OPRA snapshots and helpers from the Sept 28 spread test (research/spy_put_spread_backtest_v1).
Each day's file is read once and fed to every variant. Research only; no network access.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from research.breakout_test_v1.backtest import load as load_daily
from research.provenance_v1.provenance import write_manifest
from research.spy_put_spread_backtest_v1.backtest import (DATA, available_days, bs_put, implied_vol, load_day,
                                                          load_rates, parity_spot)

FIRST, LAST = date(2016, 1, 4), date(2025, 12, 31)
START_EQUITY, FEE, DTE_MIN, DTE_MAX, DTE_TARGET = 100_000.0, 0.03, 21, 45, 30
HALVES = (("2016-2020", "2016-01-01", "2020-12-31"), ("2021-2025", "2021-01-01", "2025-12-31"))
VARIANTS = {"main_delta30_bid": (0.30, "bid", True), "info_delta30_mid": (0.30, "mid", True),
            "info_atm_delta50_bid": (0.50, "bid", False), "info_delta20_bid": (0.20, "bid", True)}


def pick_put(quotes, day, spot, r, target_delta, below_spot=True):
    """(expiration, strike, bid, ask, delta) for the 21-45 DTE expiration closest to 30 days and the put whose
    Black-Scholes delta (from its own mid implied vol) is closest to -target_delta."""
    expirations = sorted({k[0] for k in quotes if k[1] == "P" and DTE_MIN <= (k[0] - day).days <= DTE_MAX})
    if not expirations or spot is None:
        return None
    expiration = min(expirations, key=lambda e: (abs((e - day).days - DTE_TARGET), e))
    t = ((expiration - day).days + 5.5 / 24) / 365
    best = None
    for (e, typ, strike), (bid, ask) in quotes.items():
        if e != expiration or typ != "P" or (below_spot and strike >= spot) or bid <= 0:
            continue
        iv = implied_vol((bid + ask) / 2, spot, strike, t, r)
        if iv is None:
            continue
        delta = bs_put(spot, strike, t, r, iv)[1]
        key = (abs(abs(delta) - target_delta), -strike)
        if best is None or key < best[0]:
            best = (key, (expiration, strike, bid, ask, delta))
    return best[1] if best else None


def contracts_for(cash, strike):
    return math.floor(cash / (strike * 100))


def settlement_loss(strike, spot, contracts):
    return max(strike - spot, 0.0) * 100 * contracts


class Account:
    def __init__(self, target_delta, fill, below_spot):
        self.target_delta, self.fill, self.below_spot = target_delta, fill, below_spot
        self.cash, self.pos, self.need_entry, self.prev_day = START_EQUITY, None, True, None
        self.trades, self.curve, self.interest, self.stats = [], [], 0.0, Counter()

    def step(self, day, morning, close, m_spot, c_spot, r):
        if self.prev_day is not None:
            earned = self.cash * r * (day - self.prev_day).days / 365
            self.cash += earned
            self.interest += earned
        self.prev_day = day
        p = self.pos
        if p and day >= p["expiration"]:
            if c_spot is None:
                self.stats["settle_waited_missing_spot"] += 1
            else:
                if day > p["expiration"]:
                    self.stats["settled_after_expiration_day_missing"] += 1
                loss = settlement_loss(p["strike"], c_spot, p["contracts"])
                self.cash -= loss
                pnl = p["premium"] - p["fees"] - loss
                self.trades.append({**{k: (v.isoformat() if isinstance(v, date) else v) for k, v in p.items()
                                       if k != "mark"},
                                    "settle_day": day.isoformat(), "settle_spot": round(c_spot, 4),
                                    "loss": round(loss, 2), "pnl": round(pnl, 2), "expired_worthless": loss == 0})
                self.pos, self.need_entry = None, True
        elif self.need_entry and not p:
            pick = pick_put(morning, day, m_spot, r, self.target_delta, self.below_spot)
            if pick is None:
                self.stats["entry_skipped_no_quote"] += 1
            else:
                expiration, strike, bid, ask, delta = pick
                n = contracts_for(self.cash, strike)
                price = bid if self.fill == "bid" else (bid + ask) / 2
                if n >= 1:
                    premium, fees = price * 100 * n, FEE * n
                    self.cash += premium - fees
                    self.pos = {"entry_day": day, "expiration": expiration, "strike": strike, "contracts": n,
                                "sale_price": price, "delta": round(delta, 3), "entry_spot": round(m_spot, 4),
                                "premium": round(premium, 2), "fees": round(fees, 2), "mark": price}
                    self.need_entry = False
        p = self.pos
        if p:
            q = close.get((p["expiration"], "P", p["strike"]))
            if q:
                p["mark"] = (q[0] + q[1]) / 2
            elif c_spot is not None and day >= p["expiration"]:
                p["mark"] = max(p["strike"] - c_spot, 0.0)
        equity = self.cash - (p["mark"] * 100 * p["contracts"] if p else 0.0)
        self.curve.append((day.isoformat(), equity))


def drawdown(values):
    peak, worst = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst


def stats_for(curve, years):
    vals = [v for _, v in curve]
    total = vals[-1] / vals[0]
    cagr = total ** (1 / years) - 1
    dd = drawdown(vals)
    return {"total_return_pct": round((total - 1) * 100, 1), "cagr_pct": round(cagr * 100, 2),
            "max_drawdown_pct": round(dd * 100, 1), "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None}


def halves(curve):
    value = dict(curve)
    dates = [d for d, _ in curve]
    out = {}
    for name, a, b in HALVES:
        inside = [d for d in dates if a <= d <= b]
        before = [d for d in dates if d < inside[0]]
        out[name] = round((value[inside[-1]] / (value[before[-1]] if before else START_EQUITY) - 1) * 100, 1)
    return out


def report(acct, bench, years):
    trades = acct.trades
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [-t["pnl"] for t in trades if t["pnl"] <= 0]
    curve = [("start", START_EQUITY)] + acct.curve
    s = stats_for(curve, years)
    by_year = defaultdict(float)
    for t in trades:
        by_year[t["settle_day"][:4]] += t["pnl"]
    result = {
        **s, "final_equity": round(acct.curve[-1][1]), "trades": len(trades),
        "expired_worthless_pct": round(100 * sum(t["expired_worthless"] for t in trades) / max(len(trades), 1), 1),
        "win_rate_pct": round(100 * len(wins) / max(len(trades), 1), 1),
        "avg_win_usd": round(sum(wins) / max(len(wins), 1)), "avg_loss_usd": round(sum(losses) / max(len(losses), 1)),
        "profit_factor": round(sum(wins) / sum(losses), 2) if losses else None,
        "worst_trade": min(trades, key=lambda t: t["pnl"]) if trades else None,
        "premium_pnl_usd": round(sum(t["pnl"] for t in trades)), "interest_usd": round(acct.interest),
        "halves_return_pct": halves(acct.curve), "pnl_by_settle_year": {y: round(v) for y, v in sorted(by_year.items())},
        "median_delta": sorted(t["delta"] for t in trades)[len(trades) // 2] if trades else None,
        "median_otm_pct": sorted(round((1 - t["strike"] / t["entry_spot"]) * 100, 2) for t in trades)[len(trades) // 2]
        if trades else None,
        "stats": dict(acct.stats),
    }
    checks = {"A1_profit_factor_at_least_1.3": (result["profit_factor"] or 0) >= 1.3,
              "A2_profitable_in_both_halves": all(v > 0 for v in result["halves_return_pct"].values()),
              "A3_max_drawdown_at_most_25pct": result["max_drawdown_pct"] >= -25.0,
              "B1_drawdown_5pts_smaller_than_spy": result["max_drawdown_pct"] >= bench["max_drawdown_pct"] + 5,
              "B2_cagr_over_dd_beats_spy": (result["cagr_over_dd"] or -9) > bench["cagr_over_dd"]}
    result["checks"], result["passes"] = checks, all(checks.values())
    result["trade_list"] = trades
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/csp-spy-test-results.json")
    args = parser.parse_args()
    days = [d for d in available_days() if FIRST <= d <= LAST]
    rates = load_rates()
    accounts = {name: Account(*v) for name, v in VARIANTS.items()}
    for n, day in enumerate(days, 1):
        snap = load_day(DATA / str(day.year) / f"{day.isoformat()}.csv.gz")
        morning, close = snap.get("t1030", {}), snap.get("close", {})
        r = rates.get(day.strftime("%Y-%m"), 0.0)
        m_spot, c_spot = parity_spot(morning, day, r, 5.5), parity_spot(close, day, r, 0)
        for acct in accounts.values():
            acct.step(day, morning, close, m_spot, c_spot, r)
        if n % 250 == 0:
            print(json.dumps({"days": n, "of": len(days), "at": day.isoformat()}), flush=True)
    spy = load_daily("SPY")
    window = [(d, c) for d, c in zip(spy["date"], spy["close"]) if days[0].isoformat() <= d <= days[-1].isoformat()]
    years = len(days) / 252
    bench = stats_for(window, years)
    out = {"plan": "output/CSP_SPY_TEST_PLAN_20261005.md", "first": days[0].isoformat(), "last": days[-1].isoformat(),
           "data_days": len(days), "spy_with_dividends": bench,
           "results": {name: report(acct, bench, years) for name, acct in accounts.items()}}
    out["verdict_pass"] = out["results"]["main_delta30_bid"]["passes"]
    Path(args.output).write_text(json.dumps(out, indent=1, default=str) + "\n")
    data_files = [str(DATA / str(d.year) / f"{d.isoformat()}.csv.gz") for d in days]
    write_manifest(args.output, code=["research/csp_spy_test_v1/backtest.py",
                                      "research/spy_put_spread_backtest_v1/backtest.py"],
                   data=data_files + ["outputs/breakout_data/SPY.csv.gz",
                                      "research/spy_put_spread_backtest_v1/tbill_3m_monthly.csv"],
                   params={"variants": VARIANTS, "fee": FEE, "dte": [DTE_MIN, DTE_MAX, DTE_TARGET]})
    print(json.dumps({"spy_with_dividends": bench, "verdict_pass": out["verdict_pass"],
                      **{k: {x: y for x, y in v.items() if x not in ("trade_list", "worst_trade")}
                         for k, v in out["results"].items()}}, indent=1))


if __name__ == "__main__":
    main()
