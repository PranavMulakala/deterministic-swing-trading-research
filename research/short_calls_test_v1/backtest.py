"""Backtest of pre-declared test #24: buy a short-dated SPY call every week (plan:
output/SHORT_DATED_SPY_CALLS_TEST_PLAN_20261006.md). Research only; no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.short_calls_test_v1.backtest

Databento OPRA snapshots (10:30 and close) for 2016-2025, SPY from put-call parity, T-bill interest on idle cash
(the helpers from tests #1 and #10). Every week's first trading day, at the close: buy the call expiring closest to
7 days out (4-11), at the strike closest to SPY, paying the ask plus $0.03 a contract, spending 2% of the account;
hold to expiration and settle at intrinsic value.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import gzip
import json
import math
from pathlib import Path
import statistics

from research.provenance_v1.provenance import write_manifest
from research.spy_put_spread_backtest_v1.backtest import DATA, available_days, load_day, load_rates, parity_spot

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/short-dated-calls-test-results.json"
SPY_FILE = ROOT / "outputs/orb_play_data/SPY_all.json.gz"
START, FEE, DTE_MIN, DTE_MAX, DTE_TARGET = 100_000.0, 0.03, 4, 11, 7
FIRST, LAST, MAIN = date(2016, 1, 4), date(2025, 12, 31), "2020-01-02"
HALVES = (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2025", "2023-01-01", "2025-12-31"))
VARIANTS = {"main_atm_ask_2pct": {}, "otm_1_5pct": {"otm": 0.015}, "mid_fills": {"fill": "mid"},
            "spend_5pct": {"spend": 0.05}, "spend_10pct": {"spend": 0.10}, "sell_at_plus_100pct": {"take_profit": 1.0},
            "flat_1000_a_week": {"flat": 1000.0}}


def pick_call(quotes, day, spot, otm=0.0):
    """(expiration, strike, bid, ask) for the expiration closest to 7 days (4-11, ties later) and the strike closest
    to spot * (1 + otm) (ties: the higher strike)."""
    exps = sorted({k[0] for k in quotes if k[1] == "C" and DTE_MIN <= (k[0] - day).days <= DTE_MAX})
    if not exps or spot is None:
        return None
    exp = min(exps, key=lambda e: (abs((e - day).days - DTE_TARGET), -e.toordinal()))
    goal = spot * (1 + otm)
    strikes = [(k[2], q) for k, q in quotes.items() if k[0] == exp and k[1] == "C" and q[1] > 0]
    if not strikes:
        return None
    strike, (bid, ask) = min(strikes, key=lambda x: (abs(x[0] - goal), -x[0]))
    return exp, strike, bid, ask


class Account:
    def __init__(self, otm=0.0, fill="ask", spend=0.02, take_profit=None, flat=None):
        self.otm, self.fill, self.spend, self.take_profit, self.flat = otm, fill, spend, take_profit, flat
        self.cash, self.open, self.trades, self.curve, self.prev, self.week = START, [], [], [], None, None
        self.stats = Counter()

    def equity(self):
        return self.cash + sum(p["mark"] * 100 * p["n"] for p in self.open)

    def close_out(self, p, day, value, why):
        proceeds = value * 100 * p["n"]
        self.cash += proceeds
        self.trades.append({"entry_day": p["day"].isoformat(), "exit_day": day.isoformat(), "expiration": p["exp"].isoformat(),
                            "strike": p["strike"], "n": p["n"], "price": p["price"], "cost": p["cost"],
                            "exit_value": value, "pnl": proceeds - p["cost"], "why": why})

    def step(self, day, close, spot, r):
        if self.prev is not None:
            self.cash += self.cash * r * (day - self.prev).days / 365
        self.prev = day
        for p in list(self.open):
            if day >= p["exp"]:
                if spot is None:
                    self.stats["settle_waited_missing_spot"] += 1
                    continue
                self.open.remove(p)
                self.close_out(p, day, max(spot - p["strike"], 0.0), "expired")
            elif self.take_profit is not None:
                q = close.get((p["exp"], "C", p["strike"]))
                if q and q[0] >= p["price"] * (1 + self.take_profit):
                    self.open.remove(p)
                    self.close_out(p, day, q[0], "take_profit")
        week = day.isocalendar()[:2]
        if week != self.week:
            self.week = week
            pick = pick_call(close, day, spot, self.otm)
            if pick is None:
                self.stats["entry_skipped_no_quote"] += 1
            else:
                exp, strike, bid, ask = pick
                price = ask if self.fill == "ask" else (bid + ask) / 2
                budget = self.flat if self.flat is not None else self.spend * self.equity()
                n = math.floor(min(budget, self.cash) / (price * 100 + FEE)) if price > 0 else 0
                if n >= 1:
                    cost = n * (price * 100 + FEE)
                    self.cash -= cost
                    self.open.append({"day": day, "exp": exp, "strike": strike, "n": n, "price": price, "cost": cost,
                                      "mark": price})
                else:
                    self.stats["entry_skipped_too_small"] += 1
        for p in self.open:
            q = close.get((p["exp"], "C", p["strike"]))
            if q:
                p["mark"] = (q[0] + q[1]) / 2
        self.curve.append((day.isoformat(), self.equity()))


def drawdown(values):
    peak, worst = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst


def summarize(acct, spy, lo, hi, halves=HALVES):
    curve = [(d, v) for d, v in acct.curve if lo <= d <= hi]
    base = next((v for d, v in reversed(acct.curve) if d < lo), START)
    vals = [v for _, v in curve]
    years = len(vals) / 252
    cagr = (vals[-1] / base) ** (1 / years) - 1
    dd = drawdown([base] + vals)
    trades = [t for t in acct.trades if lo <= t["entry_day"] <= hi]
    gains = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    losses = -sum(t["pnl"] for t in trades if t["pnl"] <= 0)
    rets = [t["pnl"] / t["cost"] for t in trades]
    value, dates = dict(acct.curve), [d for d, _ in acct.curve]

    def change(a, b):
        inside = [d for d in dates if a <= d <= b]
        before = [d for d in dates if d < inside[0]]
        return round(100 * (value[inside[-1]] / (value[before[-1]] if before else START) - 1), 1)

    sc = [spy[d] for d, _ in curve if d in spy]
    s_cagr = (sc[-1] / sc[0]) ** (1 / (len(sc) / 252)) - 1
    s_dd = drawdown(sc)
    out = {"start_value": round(base), "final": round(vals[-1]), "growth_pct": round(100 * (vals[-1] / base - 1), 1),
           "cagr_pct": round(100 * cagr, 2), "max_drawdown_pct": round(100 * dd, 1),
           "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None,
           "calls_bought": len(trades), "expired_worthless_pct": round(100 * sum(t["exit_value"] == 0 for t in trades) / max(len(trades), 1), 1),
           "winners_pct": round(100 * sum(t["pnl"] > 0 for t in trades) / max(len(trades), 1), 1),
           "avg_return_per_call_pct": round(100 * statistics.mean(rets), 1) if rets else None,
           "median_return_per_call_pct": round(100 * statistics.median(rets), 1) if rets else None,
           "best_call_pct": round(100 * max(rets), 1) if rets else None,
           "total_call_pnl": round(gains - losses), "profit_factor": round(gains / losses, 3) if losses else None,
           "halves_return_pct": {n: change(a, b) for n, a, b in halves},
           "spy": {"final_on_same_start": round(base * sc[-1] / sc[0]), "cagr_pct": round(100 * s_cagr, 2),
                   "max_drawdown_pct": round(100 * s_dd, 1), "cagr_over_dd": round(s_cagr / abs(s_dd), 3)}}
    out["checks"] = {"A1_profit_factor_1.3": (out["profit_factor"] or 0) >= 1.3,
                     "A2_both_halves_profitable": all(v > 0 for v in out["halves_return_pct"].values()),
                     "A3_drawdown_within_25": out["max_drawdown_pct"] >= -25.0,
                     "B1_drawdown_5pts_smaller_than_spy": out["max_drawdown_pct"] >= out["spy"]["max_drawdown_pct"] + 5,
                     "B2_cagr_over_dd_beats_spy": (out["cagr_over_dd"] or -9) > out["spy"]["cagr_over_dd"]}
    out["passes"] = all(out["checks"].values())
    return out


def main():
    days = [d for d in available_days() if FIRST <= d <= LAST]
    rates = load_rates()
    main_accts = {v: Account(**kw) for v, kw in VARIANTS.items()}
    stress = Account()
    for n, day in enumerate(days, 1):
        snap = load_day(DATA / str(day.year) / f"{day.isoformat()}.csv.gz")
        close = snap.get("close", {})
        r = rates.get(day.strftime("%Y-%m"), 0.0)
        spot = parity_spot(close, day, r, 0)
        if day.isoformat() < MAIN:
            stress.step(day, close, spot, r)
        else:
            for a in main_accts.values():
                a.step(day, close, spot, r)
        if n % 500 == 0:
            print(json.dumps({"days": n, "of": len(days)}), flush=True)
    with gzip.open(SPY_FILE, "rt") as f:
        b = json.load(f)
    spy = {d: x[3] for d, x in zip(b["date"], b["bars"])}
    res = {v: summarize(a, spy, MAIN, LAST.isoformat()) for v, a in main_accts.items()}
    st = summarize(stress, spy, FIRST.isoformat(), "2019-12-31", (("2016-2017", "2016-01-01", "2017-12-31"),
                                                                  ("2018-2019", "2018-01-01", "2019-12-31")))
    m = res["main_atm_ask_2pct"]
    verdict = ("PASS (robust)" if st["checks"]["B2_cagr_over_dd_beats_spy"] else "PASS (post-COVID only)") if m["passes"] else "FAIL"
    by_year = {}
    for t in main_accts["main_atm_ask_2pct"].trades:
        by_year[t["entry_day"][:4]] = by_year.get(t["entry_day"][:4], 0) + t["pnl"]
    out = {"plan": "output/SHORT_DATED_SPY_CALLS_TEST_PLAN_20261006.md", "verdict": verdict, "main": m,
           "stress_2016_2019": st, "info": {k: v for k, v in res.items() if k != "main_atm_ask_2pct"},
           "main_call_pnl_by_year": {y: round(v) for y, v in sorted(by_year.items())},
           "stats": {v: dict(a.stats) for v, a in main_accts.items()},
           "main_trades": main_accts["main_atm_ask_2pct"].trades,
           "main_curve": [[d, round(v, 2)] for d, v in main_accts["main_atm_ask_2pct"].curve]}
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
    write_manifest(OUT, code=["research/short_calls_test_v1/backtest.py", "research/spy_put_spread_backtest_v1/backtest.py"],
                   data=[str(DATA / str(d.year) / f"{d.isoformat()}.csv.gz") for d in days] + [str(SPY_FILE)],
                   params={"variants": VARIANTS, "fee": FEE, "dte": [DTE_MIN, DTE_MAX, DTE_TARGET]})
    print(json.dumps({k: out[k] for k in ("verdict", "main", "main_call_pnl_by_year")}, indent=1))
    print(json.dumps({"stress": {k: st[k] for k in ("final", "cagr_pct", "max_drawdown_pct", "calls_bought", "expired_worthless_pct", "avg_return_per_call_pct", "spy")},
                      "info": {k: {x: v[x] for x in ("final", "cagr_pct", "max_drawdown_pct", "expired_worthless_pct",
                                                     "avg_return_per_call_pct", "total_call_pnl", "profit_factor")}
                               for k, v in out["info"].items()}}, indent=1))


if __name__ == "__main__":
    main()
