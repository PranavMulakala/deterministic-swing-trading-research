"""Backtest of pre-declared test #26: in-the-money covered calls with roll-downs on SPY
(plan: output/ITM_COVERED_CALLS_TEST_PLAN_20261007.md). Research only; no orders. Dollars only: no SPY comparison line.

  PYTHONPATH=src:. .venv/bin/python -m research.itm_covered_calls_test_v1.backtest

Own whole SPY shares (bought on day one with all cash). With no call open, sell one call per 100 shares: expiration
closest to 40 days (30-50), the lowest strike below SPY whose annualized return if called away is at least 10%, at the
bid minus $0.03 a contract. Settle at intrinsic value at expiration, or the day before an ex-date when the call's time
value is below the dividend. Roll down for a net credit when SPY closes below the strike with 7+ days left. No new
call (including a roll) is sold on the trading day before an ex-date. Databento OPRA closing snapshots 2016-2025; SPY
from put-call parity (test #10's helpers); dividends and T-bill interest as in test #25.
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
from research.covered_calls_test_v1.backtest import DIVIDENDS, dividends, drawdown_pct

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/itm-covered-calls-test-results.json"
START, FEE, SLIP = 100_000.0, 0.03, 0.01
FIRST, LAST, MAIN = date(2016, 1, 4), date(2025, 12, 31), "2020-01-02"
HALVES = (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2025", "2023-01-01", "2025-12-31"))
CALL_DTE, PUT_DTE, ROLL_MIN_DAYS, DROP = (30, 50, 40), (45, 65, 50), 7, -0.03
VARIANTS = {"main_itm_roll": {}, "no_roll": {"roll": False}, "ann5": {"ann": 0.05}, "ann20": {"ann": 0.20},
            "iv_band": {"iv_band": (0.25, 0.45)}, "collar_on_drops": {"collar": True}, "mid_fill": {"fill": "mid"},
            "shares_only": {"calls": False}}


def pick_expiration(quotes, day, typ, dte):
    """The expiration closest to dte[2] days within dte[0]-dte[1] that has quotes of this type (ties: later)."""
    lo, hi, target = dte
    exps = {k[0] for k in quotes if k[1] == typ and lo <= (k[0] - day).days <= hi}
    return min(exps, key=lambda e: (abs((e - day).days - target), -e.toordinal())) if exps else None


def annualized_if_called(spot, strike, bid, days):
    """Return if called away on the money put in (SPY - bid), annualized: (strike - cost) / cost x 365 / days."""
    cost = spot - bid
    return (strike - cost) / cost * 365 / days if cost > 0 and days > 0 else -math.inf


def pick_call(quotes, day, spot, ann=0.10, dte=CALL_DTE):
    """(expiration, strike, bid, ask): the lowest strike below SPY, with a bid, whose annualized return if called away
    is at least `ann`; None if no strike qualifies."""
    if spot is None:
        return None
    exp = pick_expiration(quotes, day, "C", dte)
    if exp is None:
        return None
    days = (exp - day).days
    for strike, (bid, ask) in sorted((k[2], q) for k, q in quotes.items() if k[0] == exp and k[1] == "C" and k[2] < spot and q[0] > 0):
        if annualized_if_called(spot, strike, bid, days) >= ann - 1e-12:
            return exp, strike, bid, ask
    return None


def pick_put(quotes, day, spot):
    """(expiration, strike, bid, ask): expiration closest to 50 days (45-65), the strike nearest SPY (ties: higher)."""
    exp = pick_expiration(quotes, day, "P", PUT_DTE)
    if exp is None:
        return None
    strike, (bid, ask) = min(((k[2], q) for k, q in quotes.items() if k[0] == exp and k[1] == "P"),
                             key=lambda x: (abs(x[0] - spot), -x[0]))
    return exp, strike, bid, ask


def implied_vol(quotes, day, spot):
    """~30-day at-the-money volatility from the straddle: (call mid + put mid) / (0.8 x SPY x sqrt(days / 365))."""
    pairs = [(e, k) for (e, typ, k) in quotes if typ == "C" and (e - day).days >= 1 and (e, "P", k) in quotes]
    if not pairs or spot is None:
        return None
    exp = min({e for e, _ in pairs}, key=lambda e: (abs((e - day).days - 30), -e.toordinal()))
    k = min((k for e, k in pairs if e == exp), key=lambda k: (abs(k - spot), -k))
    c, p = quotes[(exp, "C", k)], quotes[(exp, "P", k)]
    return ((c[0] + c[1]) / 2 + (p[0] + p[1]) / 2) / (0.8 * spot * math.sqrt((exp - day).days / 365))


class Account:
    def __init__(self, ann=0.10, dte=CALL_DTE, fill="bid", calls=True, roll=True, iv_band=None, collar=False):
        self.ann, self.dte, self.fill, self.calls, self.roll, self.iv_band, self.collar = ann, dte, fill, calls, roll, iv_band, collar
        self.cash, self.shares, self.open, self.put = START, 0, None, None
        self.trades, self.put_trades, self.curve = [], [], []
        self.prev, self.last_spot, self.prev_spot, self.stats = None, None, None, Counter()

    def sell_price(self, bid, ask):
        return bid if self.fill == "bid" else (bid + ask) / 2

    def buy_price(self, bid, ask):
        return ask if self.fill == "bid" else (bid + ask) / 2

    def equity(self, spot):
        value = self.cash + self.shares * spot
        if self.open:
            value -= self.open["mark"] * 100 * self.open["n"]
        if self.put:
            value += self.put["mark"] * 100 * self.put["n"]
        return value

    def pay(self, owe, spot):
        if owe > self.cash:
            sell = min(self.shares, math.ceil((owe - self.cash) / spot))
            self.shares -= sell
            self.cash += sell * spot
            self.stats["shares_sold_to_cover"] += sell
        self.cash -= owe

    def open_call(self, day, pick):
        exp, strike, bid, ask = pick
        price, n = self.sell_price(bid, ask), self.shares // 100
        if n < 1 or price * 100 <= FEE:
            return False
        credit = n * (price * 100 - FEE)
        self.cash += credit
        self.open = {"day": day, "exp": exp, "strike": strike, "n": n, "price": price, "credit": credit, "mark": (bid + ask) / 2}
        return True

    def close_call(self, old, day, spot, cost, how):
        self.pay(cost, spot)
        self.stats["closed_" + how] += 1
        self.trades.append({"entry_day": old["day"].isoformat(), "expiration": old["exp"].isoformat(), "strike": old["strike"],
                            "n": old["n"], "price": old["price"], "credit": old["credit"], "close_day": day.isoformat(),
                            "closed": how, "spot_at_close": spot, "close_cost": cost, "pnl": old["credit"] - cost})

    def step(self, day, close, spot, r, dividend=0.0, pre_ex_dividend=0.0):
        """One trading day. `dividend`: paid today (ex-date). `pre_ex_dividend`: tomorrow's (in the data) ex-date amount."""
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
            old, self.open = self.open, None
            owe = max(spot - old["strike"], 0.0) * 100 * old["n"]
            self.close_call(old, day, spot, owe, "assigned_at_expiry" if owe > 0 else "expired")
        if self.put and day >= self.put["exp"]:
            p, self.put = self.put, None
            value = max(p["strike"] - spot, 0.0) * 100 * p["n"]
            self.cash += value
            self.put_trades.append({"entry_day": p["day"].isoformat(), "expiration": p["exp"].isoformat(), "strike": p["strike"],
                                    "n": p["n"], "cost": p["cost"], "value_at_expiry": value, "pnl": value - p["cost"]})
        if self.open and pre_ex_dividend > 0:
            q = close.get((self.open["exp"], "C", self.open["strike"]))
            intrinsic = max(spot - self.open["strike"], 0.0)
            if q is None:
                self.stats["early_exercise_no_quote"] += 1
            elif intrinsic > 0 and (q[0] + q[1]) / 2 - intrinsic < pre_ex_dividend:
                old, self.open = self.open, None
                self.close_call(old, day, spot, intrinsic * 100 * old["n"], "early_exercise")
        if (self.calls and self.roll and self.open and spot < self.open["strike"]
                and (self.open["exp"] - day).days >= ROLL_MIN_DAYS):
            q = close.get((self.open["exp"], "C", self.open["strike"]))
            new = pick_call(close, day, spot, self.ann, self.dte) if q else None
            if pre_ex_dividend > 0:
                self.stats["roll_skipped_day_before_exdate"] += 1
            elif q is None:
                self.stats["roll_skipped_no_quote"] += 1
            elif new is None or self.sell_price(new[2], new[3]) <= self.buy_price(*q):
                self.stats["roll_skipped_no_credit_or_call"] += 1
            else:
                old, self.open = self.open, None
                if self.open_call(day, new):
                    self.close_call(old, day, spot, old["n"] * (self.buy_price(*q) * 100 + FEE), "rolled")
                else:
                    self.open = old
        if self.collar and self.put is None and self.prev_spot and spot / self.prev_spot - 1 <= DROP + 1e-12 and self.shares >= 100:
            pick = pick_put(close, day, spot)
            if pick is None:
                self.stats["no_put_found"] += 1
            else:
                exp, strike, bid, ask = pick
                n = self.shares // 100
                cost = n * (self.buy_price(bid, ask) * 100 + FEE)
                self.pay(cost, spot)
                self.put = {"day": day, "exp": exp, "strike": strike, "n": n, "cost": cost, "mark": (bid + ask) / 2}
        if self.calls and self.open is None and self.shares >= 100:
            if pre_ex_dividend > 0:
                self.stats["no_sale_day_before_exdate"] += 1
            elif self.iv_band and not (self.iv_band[0] <= (implied_vol(close, day, spot) or 0.0) <= self.iv_band[1]):
                self.stats["no_sale_iv_outside_band"] += 1
            else:
                pick = pick_call(close, day, spot, self.ann, self.dte)
                if pick is None or not self.open_call(day, pick):
                    self.stats["no_call_found"] += 1
        for pos, typ in ((self.open, "C"), (self.put, "P")):
            if pos:
                q = close.get((pos["exp"], typ, pos["strike"]))
                if q:
                    pos["mark"] = (q[0] + q[1]) / 2
        self.prev_spot = spot
        self.curve.append((day.isoformat(), self.equity(spot)))


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
           "calls_winning_pct": round(100 * sum(t["pnl"] > 0 for t in acct.trades) / max(len(acct.trades), 1), 1),
           "closed_by": dict(Counter(t["closed"] for t in acct.trades)),
           "premium_collected": round(sum(t["credit"] for t in acct.trades), 2),
           "paid_to_close": round(sum(t["close_cost"] for t in acct.trades), 2),
           "worst_call": round(min((t["pnl"] for t in acct.trades), default=0), 2),
           "best_call": round(max((t["pnl"] for t in acct.trades), default=0), 2),
           "puts_bought": len(acct.put_trades), "put_pnl_total": round(sum(t["pnl"] for t in acct.put_trades), 2),
           "halves_profit_dollars": {n: change(a, b) for n, a, b in halves},
           "stats": {k: round(v, 2) for k, v in acct.stats.items()}}
    out["checks"] = {"C1_calls_earn_their_keep": out["call_pnl_total"] > 0 and (out["call_profit_factor"] or 0) >= 1.3,
                     "C2_both_halves_profitable": all(v > 0 for v in out["halves_profit_dollars"].values()),
                     "C3_drawdown_within_25": out["max_drawdown_pct"] >= -25.0}
    out["passes"] = all(out["checks"].values())
    return out


def pre_ex_dates(days, divs):
    """{last data day before each ex-date: dividend}. If the ex-date itself has no file, the dividend is not credited
    (as in test #25), but the day before still counts."""
    out = {}
    for ex, rate in divs.items():
        before = [d for d in days if d.isoformat() < ex]
        if before:
            out[before[-1].isoformat()] = rate
    return out


def run(days, accounts, rates, divs):
    pre = pre_ex_dates(days, divs)
    for n, day in enumerate(days, 1):
        close = load_day(DATA / str(day.year) / f"{day.isoformat()}.csv.gz").get("close", {})
        r = rates.get(day.strftime("%Y-%m"), 0.0)
        spot = parity_spot(close, day, r, 0)
        for a in accounts:
            a.step(day, close, spot, r, divs.get(day.isoformat(), 0.0), pre.get(day.isoformat(), 0.0))
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
    m = res["main_itm_roll"]
    verdict = ("PASS" if st["checks"]["C1_calls_earn_their_keep"] else "PASS (post-COVID only)") if m["passes"] else "FAIL"
    by_year = {}
    for t in main_accts["main_itm_roll"].trades:
        by_year[t["entry_day"][:4]] = by_year.get(t["entry_day"][:4], 0) + t["pnl"]
    out = {"plan": "output/ITM_COVERED_CALLS_TEST_PLAN_20261007.md", "verdict": verdict, "main": m, "stress_2016_2019": st,
           "info": {k: v for k, v in res.items() if k != "main_itm_roll"},
           "main_call_pnl_by_year": {y: round(v) for y, v in sorted(by_year.items())},
           "main_trades": main_accts["main_itm_roll"].trades, "stress_trades": stress.trades,
           "collar_put_trades": main_accts["collar_on_drops"].put_trades,
           "main_curve": [[d, round(v, 2)] for d, v in main_accts["main_itm_roll"].curve],
           "shares_only_curve": [[d, round(v, 2)] for d, v in main_accts["shares_only"].curve]}
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
    write_manifest(OUT, code=["research/itm_covered_calls_test_v1/backtest.py", "research/covered_calls_test_v1/backtest.py",
                              "research/spy_put_spread_backtest_v1/backtest.py"],
                   data=[str(DATA / str(d.year) / f"{d.isoformat()}.csv.gz") for d in days] + [str(DIVIDENDS)],
                   params={"variants": {k: {x: str(y) for x, y in v.items()} for k, v in VARIANTS.items()}, "fee": FEE,
                           "call_dte": CALL_DTE, "put_dte": PUT_DTE, "roll_min_days": ROLL_MIN_DAYS, "drop": DROP})
    show = lambda r: {k: r[k] for k in ("final", "max_drawdown_pct", "calls_sold", "call_pnl_total", "call_profit_factor",
                                        "calls_winning_pct", "closed_by", "premium_collected", "put_pnl_total",
                                        "halves_profit_dollars", "checks")} | {
        x: r["scorecard"][x] for x in ("profit", "avg_per_week", "weeks_at_or_above_1000", "weeks", "worst_week", "worst_month", "worst_drop_dollars")}
    print(json.dumps({"verdict": verdict, "main": show(m), "stress": show(st), "by_year": out["main_call_pnl_by_year"],
                      "info": {k: show(v) for k, v in out["info"].items()}}, indent=1))


if __name__ == "__main__":
    main()
