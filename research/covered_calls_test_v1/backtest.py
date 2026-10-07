"""Backtest of pre-declared test #25: covered calls on SPY (plan: output/COVERED_CALLS_TEST_PLAN_20261007.md).
Research only; no orders. Dollars only: no SPY comparison line (owner's instruction).

  PYTHONPATH=src:. .venv/bin/python -m research.covered_calls_test_v1.backtest

Own whole SPY shares (bought on day one with all cash), and on each sell day sell one call per 100 shares: the expiration
closest to 30 days (21-45), the first strike at or above SPY x 1.02, at the bid minus $0.03 a contract. On expiration
the call is settled at intrinsic value from cash (selling shares if cash runs short). Dividends on ex-dates, T-bill
interest on cash. Databento OPRA closing snapshots 2016-2025; SPY from put-call parity (test #10's helpers).
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import json
import math
from pathlib import Path

from research.provenance_v1.provenance import write_manifest
from research.scorecard_v1.scorecard import scorecard
from research.spy_put_spread_backtest_v1.backtest import DATA, available_days, load_day, load_rates, parity_spot

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/covered-calls-test-results.json"
DIVIDENDS = ROOT / "output/spy-dividends-alpaca-2016-2025.json"
START, FEE, SLIP = 100_000.0, 0.03, 0.01
FIRST, LAST, MAIN = date(2016, 1, 4), date(2025, 12, 31), "2020-01-02"
HALVES = (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2025", "2023-01-01", "2025-12-31"))
MONTHLY, WEEKLY = (21, 45, 30), (4, 11, 7)
VARIANTS = {"main_otm2_30d": {}, "atm_30d": {"atm": True}, "otm5_30d": {"otm": 0.05},
            "weekly_otm1": {"otm": 0.01, "dte": WEEKLY}, "mid_fill": {"fill": "mid"}, "shares_only": {"calls": False}}


def pick_call(quotes, day, spot, otm=0.02, dte=MONTHLY, atm=False):
    """(expiration, strike, bid, ask): expiration closest to dte[2] days within dte[0]-dte[1] (ties: later); strike =
    the first at or above spot x (1 + otm), or the nearest to spot when atm (ties: higher); bid must be above zero."""
    lo, hi, target = dte
    exps = sorted({k[0] for k in quotes if k[1] == "C" and lo <= (k[0] - day).days <= hi})
    if not exps or spot is None:
        return None
    exp = min(exps, key=lambda e: (abs((e - day).days - target), -e.toordinal()))
    strikes = sorted((k[2], q) for k, q in quotes.items() if k[0] == exp and k[1] == "C" and q[0] > 0)
    if atm:
        chosen = min(strikes, key=lambda x: (abs(x[0] - spot), -x[0])) if strikes else None
    else:
        chosen = next((s for s in strikes if s[0] >= spot * (1 + otm) - 1e-9), None)
    if chosen is None:
        return None
    strike, (bid, ask) = chosen
    return exp, strike, bid, ask


class Account:
    def __init__(self, otm=0.02, dte=MONTHLY, atm=False, fill="bid", calls=True):
        self.otm, self.dte, self.atm, self.fill, self.calls = otm, dte, atm, fill, calls
        self.cash, self.shares, self.open, self.trades, self.curve = START, 0, None, [], []
        self.prev, self.last_spot, self.stats = None, None, Counter()

    def equity(self, spot):
        short = self.open["mark"] * 100 * self.open["n"] if self.open else 0.0
        return self.cash + self.shares * spot - short

    def step(self, day, close, spot, r, dividend=0.0):
        if self.prev is not None:
            self.cash += self.cash * r * (day - self.prev).days / 365
        self.prev = day
        if dividend and self.shares:
            self.cash += dividend * self.shares
            self.stats["dividends"] += dividend * self.shares
        if spot is None:
            self.stats["missing_spot_days"] += 1
            if self.last_spot is not None:
                self.curve.append((day.isoformat(), self.equity(self.last_spot)))
            return
        self.last_spot = spot
        if self.shares == 0 and not self.curve:
            self.shares = math.floor(self.cash / (spot + SLIP))
            self.cash -= self.shares * (spot + SLIP)
        if self.open and day >= self.open["exp"]:
            p, self.open = self.open, None
            value = max(spot - p["strike"], 0.0)
            owe = value * 100 * p["n"]
            if owe > self.cash:
                sell = min(self.shares, math.ceil((owe - self.cash) / spot))
                self.shares -= sell
                self.cash += sell * spot
                self.stats["shares_sold_to_cover"] += sell
            self.cash -= owe
            self.trades.append({"entry_day": p["day"].isoformat(), "expiration": p["exp"].isoformat(), "strike": p["strike"], "settle_day": day.isoformat(),
                                "n": p["n"], "price": p["price"], "credit": p["credit"], "spot_at_expiry": spot,
                                "paid_at_expiry": owe, "pnl": p["credit"] - owe})
        if self.calls and self.open is None and self.shares >= 100:
            pick = pick_call(close, day, spot, self.otm, self.dte, self.atm)
            if pick is None:
                self.stats["no_call_found"] += 1
            else:
                exp, strike, bid, ask = pick
                price = bid if self.fill == "bid" else (bid + ask) / 2
                n = self.shares // 100
                if price * 100 > FEE:
                    credit = n * (price * 100 - FEE)
                    self.cash += credit
                    self.open = {"day": day, "exp": exp, "strike": strike, "n": n, "price": price, "credit": credit,
                                 "mark": (bid + ask) / 2}
        if self.open:
            q = close.get((self.open["exp"], "C", self.open["strike"]))
            if q:
                self.open["mark"] = (q[0] + q[1]) / 2
        self.curve.append((day.isoformat(), self.equity(spot)))


def drawdown_pct(values):
    peak, worst = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return round(100 * worst, 1)


def summarize(acct, halves=HALVES):
    card = scorecard(acct.curve, START)
    gains = sum(t["pnl"] for t in acct.trades if t["pnl"] > 0)
    losses = -sum(t["pnl"] for t in acct.trades if t["pnl"] <= 0)
    value = dict(acct.curve)
    dates = [d for d, _ in acct.curve]

    def change(a, b):
        inside = [d for d in dates if a <= d <= b]
        before = [d for d in dates if d < inside[0]]
        return round(value[inside[-1]] - (value[before[-1]] if before else START), 2)

    out = {"scorecard": card, "final": round(acct.curve[-1][1], 2), "max_drawdown_pct": drawdown_pct([START] + [v for _, v in acct.curve]),
           "calls_sold": len(acct.trades), "call_pnl_total": round(gains - losses, 2),
           "call_profit_factor": round(gains / losses, 3) if losses else None,
           "calls_expired_worthless_pct": round(100 * sum(t["paid_at_expiry"] == 0 for t in acct.trades) / max(len(acct.trades), 1), 1),
           "premium_collected": round(sum(t["credit"] for t in acct.trades), 2),
           "paid_back_at_expiry": round(sum(t["paid_at_expiry"] for t in acct.trades), 2),
           "worst_call": round(min((t["pnl"] for t in acct.trades), default=0), 2),
           "halves_profit_dollars": {n: change(a, b) for n, a, b in halves},
           "stats": {k: round(v, 2) for k, v in acct.stats.items()}}
    out["checks"] = {"C1_calls_earn_their_keep": out["call_pnl_total"] > 0 and (out["call_profit_factor"] or 0) >= 1.3,
                     "C2_both_halves_profitable": all(v > 0 for v in out["halves_profit_dollars"].values()),
                     "C3_drawdown_within_25": out["max_drawdown_pct"] >= -25.0}
    out["passes"] = all(out["checks"].values())
    return out


def dividends():
    if not DIVIDENDS.exists():
        from research.forward_watch_v1.watch import get
        r = get("https://data.alpaca.markets/v1/corporate-actions?symbols=SPY&types=cash_dividend"
                "&start=2016-01-01&end=2025-12-31&limit=1000")
        rows = [{"ex_date": x["ex_date"], "rate": x["rate"]} for x in r["corporate_actions"]["cash_dividends"]]
        DIVIDENDS.write_text(json.dumps(sorted(rows, key=lambda x: x["ex_date"]), indent=1) + "\n")
    return {x["ex_date"]: x["rate"] for x in json.loads(DIVIDENDS.read_text())}


def run(days, accounts, rates, divs):
    for n, day in enumerate(days, 1):
        close = load_day(DATA / str(day.year) / f"{day.isoformat()}.csv.gz").get("close", {})
        r = rates.get(day.strftime("%Y-%m"), 0.0)
        spot = parity_spot(close, day, r, 0)
        for a in accounts:
            a.step(day, close, spot, r, divs.get(day.isoformat(), 0.0))
        if n % 500 == 0:
            print(json.dumps({"days": n, "of": len(days)}), flush=True)


def main():
    days = [d for d in available_days() if FIRST <= d <= LAST]
    rates, divs = load_rates(), dividends()
    main_accts = {v: Account(**kw) for v, kw in VARIANTS.items()}
    stress = Account()
    run([d for d in days if d.isoformat() >= MAIN], list(main_accts.values()), rates, divs)
    run([d for d in days if d.isoformat() < MAIN], [stress], rates, divs)
    res = {v: summarize(a) for v, a in main_accts.items()}
    st = summarize(stress, (("2016-2017", "2016-01-01", "2017-12-31"), ("2018-2019", "2018-01-01", "2019-12-31")))
    m = res["main_otm2_30d"]
    verdict = ("PASS" if st["checks"]["C1_calls_earn_their_keep"] else "PASS (post-COVID only)") if m["passes"] else "FAIL"
    by_year = {}
    for t in main_accts["main_otm2_30d"].trades:
        by_year[t["entry_day"][:4]] = by_year.get(t["entry_day"][:4], 0) + t["pnl"]
    out = {"plan": "output/COVERED_CALLS_TEST_PLAN_20261007.md", "verdict": verdict, "main": m, "stress_2016_2019": st,
           "info": {k: v for k, v in res.items() if k != "main_otm2_30d"},
           "main_call_pnl_by_year": {y: round(v) for y, v in sorted(by_year.items())},
           "main_trades": main_accts["main_otm2_30d"].trades,
           "main_curve": [[d, round(v, 2)] for d, v in main_accts["main_otm2_30d"].curve],
           "shares_only_curve": [[d, round(v, 2)] for d, v in main_accts["shares_only"].curve]}
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
    write_manifest(OUT, code=["research/covered_calls_test_v1/backtest.py", "research/spy_put_spread_backtest_v1/backtest.py"],
                   data=[str(DATA / str(d.year) / f"{d.isoformat()}.csv.gz") for d in days] + [str(DIVIDENDS)],
                   params={"variants": {k: {x: str(y) for x, y in v.items()} for k, v in VARIANTS.items()}, "fee": FEE})
    show = lambda r: {k: r[k] for k in ("final", "max_drawdown_pct", "calls_sold", "call_pnl_total", "call_profit_factor",
                                        "calls_expired_worthless_pct", "premium_collected", "halves_profit_dollars", "checks")} | {
        x: r["scorecard"][x] for x in ("profit", "avg_per_week", "weeks_at_or_above_1000", "weeks", "worst_week", "worst_month", "worst_drop_dollars")}
    print(json.dumps({"verdict": verdict, "main": show(m), "stress": show(st), "by_year": out["main_call_pnl_by_year"],
                      "info": {k: show(v) for k, v in out["info"].items()}}, indent=1))


if __name__ == "__main__":
    main()
