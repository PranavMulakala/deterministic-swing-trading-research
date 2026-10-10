"""Backtest of pre-declared test #29: the Reddit "wheel" (0.25-0.45 delta, under 14 days, close at 75% captured) on
AVGO, CRM, AMZN, META, CBOE, Jan 2, 2020 - Oct 9, 2026, vs holding the same five stocks.
Plan (the spec): output/WHEEL_TEST_PLAN_20261010.md. Research only; no orders. Dollars first.

The simulation is pure: it asks a data provider for closes, the 15:45 stock price, the 15:45-15:46 option chain,
one contract's minute quotes, splits, dividends and T-bill rates. research/wheel_test_v1/data.py supplies those from
Alpaca / Databento / FRED on demand (cost-guarded, cached); the unit tests use a fake provider.

  PYTHONPATH=src:. .venv/bin/python -m research.wheel_test_v1.backtest     # full run (buys Databento data, guarded)
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date, time as dtime
import json
import math
from pathlib import Path
import statistics

from research.cc_spy_test_v1.backtest import bs_call, call_iv
from research.spy_put_spread_backtest_v1.backtest import bs_put, implied_vol

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/wheel-test-results.json"
PLAN = "output/WHEEL_TEST_PLAN_20261010.md"
TICKERS = ("AVGO", "CRM", "AMZN", "META", "CBOE")
START, END = date(2020, 1, 2), date(2026, 10, 9)
SLEEVE, FEE = 40_000.0, 0.03
DECIDE = dtime(15, 45)
HOURS_LEFT = 0.25           # 15:45 -> 16:00 close, for the time to expiration
EXP_BAND, EXP_TARGET, EXP_FALLBACK = (4, 13), 7, (4, 45)
TAKE = 0.25                 # buy back when the ask is at or below 25% of the sale price (75% captured)
EPS = 1e-9
HALVES = (("2020-2022", date(2020, 1, 1), date(2022, 12, 31)), ("2023-2026", date(2023, 1, 1), END))


@dataclass(frozen=True)
class Rules:
    target: float = 0.35
    band: tuple = (0.25, 0.45)
    early_close: bool = True
    basis_floor: bool = False
    whole: bool = False


VERSIONS = OrderedDict([
    ("main", Rules()),
    ("delta_25", Rules(target=0.25, band=(0.20, 0.30))),
    ("delta_45", Rules(target=0.45, band=(0.40, 0.50))),
    ("hold_to_expiry", Rules(early_close=False)),
    ("basis_floor", Rules(basis_floor=True)),
    ("whole_contracts", Rules(whole=True)),
])


# ---------------------------------------------------------------- picks

def choose_expiration(expirations, day):
    """Closest to 7 calendar days within 4-13 days (ties: the later one); if none, the nearest within 4-45 days.
    Returns (expiration, used_fallback) or (None, False)."""
    exps = sorted(set(expirations))
    band = [e for e in exps if EXP_BAND[0] <= (e - day).days <= EXP_BAND[1]]
    if band:
        return min(band, key=lambda e: (abs((e - day).days - EXP_TARGET), -e.toordinal())), False
    wide = [e for e in exps if EXP_FALLBACK[0] <= (e - day).days <= EXP_FALLBACK[1]]
    return (wide[0], True) if wide else (None, False)


def bs_delta(kind, spot, strike, t, r, price):
    """Black-Scholes delta from the option's own implied vol (no dividends). (delta, iv) or (None, None)."""
    if kind == "P":
        iv = implied_vol(price, spot, strike, t, r, q=0.0)
        return (None, None) if iv is None else (bs_put(spot, strike, t, r, iv, q=0.0)[1], iv)
    iv = call_iv(price, spot, strike, t, r, q=0.0)
    return (None, None) if iv is None else (bs_call(spot, strike, t, r, iv, q=0.0)[1], iv)


def pick_contract(chain, day, kind, spot, r, rules, floor=None):
    """chain: {(expiration, 'P'/'C', strike): (bid, ask)} at 15:45. Put: strike below the stock; call: above it (and
    >= floor if given). Bid > 0. |delta| closest to the target, within the band (inclusive). Returns (pick, None) or
    (None, reason)."""
    quoted = {k: q for k, q in chain.items() if k[1] == kind and q[0] > 0 and q[1] >= q[0]}
    exp, fallback = choose_expiration({k[0] for k in quoted}, day)
    if exp is None:
        return None, "no_expiration_4_to_45_days"
    t = ((exp - day).days + HOURS_LEFT / 24) / 365
    lo, hi = rules.band
    best = None
    for (e, _, strike), (bid, ask) in quoted.items():
        if e != exp:
            continue
        if kind == "P" and not strike < spot:
            continue
        if kind == "C" and (not strike > spot or (floor is not None and strike < floor - EPS)):
            continue
        delta, iv = bs_delta(kind, spot, strike, t, r, (bid + ask) / 2)
        if delta is None or not lo - EPS <= abs(delta) <= hi + EPS:
            continue
        key = (abs(abs(delta) - rules.target), -strike if kind == "P" else strike)  # exact tie: further from the stock
        if best is None or key < best[0]:
            best = (key, {"kind": kind, "expiration": exp, "strike": strike, "bid": bid, "ask": ask,
                          "delta": delta, "iv": iv, "fallback": fallback})
    return (best[1], None) if best else (None, "no_strike_in_delta_band")


def contracts_for(rules, kind, cash, shares, strike):
    """Fractional (main): put collateral = all the sleeve's cash, call covers all shares. Whole: rounded down."""
    n = cash / (strike * 100) if kind == "P" else shares / 100
    return math.floor(n + EPS) if rules.whole else n


def settle(kind, strike, close):
    """Expiration on the official close: put assigned if close < strike, call called away if close > strike."""
    if kind == "P" and close < strike:
        return "assigned"
    if kind == "C" and close > strike:
        return "called_away"
    return "expired_worthless"


def first_buyback(quotes, sale_price):
    """Index of the first minute whose ask is > 0 and <= 25% of the sale price, else None."""
    limit = TAKE * sale_price + EPS
    for i, (_, _, ask) in enumerate(quotes):
        if 0 < ask <= limit:
            return i
    return None


# ---------------------------------------------------------------- one sleeve

class Sleeve:
    def __init__(self, ticker, rules, provider, days):
        self.ticker, self.rules, self.p, self.days = ticker, rules, provider, days
        self.index = {d: i for i, d in enumerate(days)}
        self.cash, self.shares, self.basis = SLEEVE, 0.0, None
        self.opt, self.resell_from = None, days[0]
        self.trades, self.curve, self.skips, self.flags = [], [], Counter(), Counter()
        self.interest = self.dividends = 0.0
        self.split_ratio = {d: r for d, r in provider.splits(ticker).items() if days[0] < d <= days[-1]}
        self.divs = provider.dividends(ticker)
        self.split_eve = {}
        for ex in self.split_ratio:
            if ex not in self.index:
                raise ValueError(f"{ticker} split ex-date {ex} is not a trading day")
            self.split_eve[days[self.index[ex] - 1]] = ex
        both = set(self.split_ratio) & set(self.divs)
        if both:
            raise ValueError(f"{ticker}: split and dividend share an ex-date {sorted(both)}")

    def next_day(self, d):
        i = self.index[d] + 1
        return self.days[i] if i < len(self.days) else None

    def settle_day(self, expiration):
        """The expiration date if it is a trading day, else the last trading day before it."""
        if expiration in self.index:
            return expiration
        self.flags["expiration_not_a_trading_day"] += 1
        return max(d for d in self.days if d <= expiration)

    def window_end(self, sale_day, expiration):
        """(last day the contract is held, why): expiration, the trading day before a split, or the test's end."""
        if expiration > self.days[-1]:
            last, why = self.days[-1], "end_of_test"
        else:
            last, why = self.settle_day(expiration), "expiration"
        for ex in sorted(self.split_ratio):
            if sale_day < ex <= last:
                return self.days[self.index[ex] - 1], "split"
        return last, why

    def run(self):
        prev = None
        for d in self.days:
            if prev is not None:
                earned = self.cash * self.p.rate(prev) * (d - prev).days / 365
                self.cash += earned
                self.interest += earned
            prev = d
            amount = self.divs.get(d)
            if amount and self.shares > EPS:   # shares held at the prior close
                credit = self.shares * amount
                self.cash += credit
                self.dividends += credit
            ratio = self.split_ratio.get(d)
            if ratio:
                if self.opt is not None:
                    raise AssertionError(f"{self.ticker}: option open on split ex-date {d}")
                self.shares *= ratio
                self.basis = self.basis / ratio if self.basis is not None else None
            close = self.p.close(self.ticker, d)
            if self.opt is not None:
                self.manage(d, close)
            if self.opt is None and self.resell_from is not None and d >= self.resell_from and d not in self.split_eve:
                if self.sell(d):
                    self.manage(d, close)
            liability = self.opt["n"] * 100 * self.opt["mark"] if self.opt else 0.0
            self.curve.append((d, self.cash + self.shares * close - liability))
        if self.opt is not None:
            self.record(self.days[-1], "open_at_end", self.opt["mark"], None, close_cash=0.0, fee=False,
                        liability=self.opt["n"] * 100 * self.opt["mark"])
        return self

    # -- selling at 15:45
    def sell(self, d):
        spot = self.p.spot(self.ticker, d)
        if spot is None:
            self.skips["no_1545_stock_price"] += 1
            return False
        kind = "C" if self.shares > EPS else "P"
        if kind == "P" and self.rules.whole and math.floor(self.cash / (0.70 * spot * 100) + EPS) < 1:
            self.skips["cannot_afford_one_contract"] += 1  # no strike in the saved +-30% range is affordable
            return False
        if kind == "C" and self.rules.whole and math.floor(self.shares / 100 + EPS) < 1:
            self.skips["fewer_than_100_shares"] += 1
            return False
        chain = self.p.chain(self.ticker, d, spot)
        if not chain:
            self.skips["no_chain_quotes"] += 1
            return False
        floor = self.basis if (kind == "C" and self.rules.basis_floor) else None
        pick, why = pick_contract(chain, d, kind, spot, self.p.rate(d), self.rules, floor)
        if pick is None:
            self.skips[why] += 1
            return False
        n = contracts_for(self.rules, kind, self.cash, self.shares, pick["strike"])
        if n <= 0:
            self.skips["cannot_afford_one_contract"] += 1
            return False
        last, why_end = self.window_end(d, pick["expiration"])
        quotes = self.p.quotes(self.ticker, kind, pick["expiration"], pick["strike"], d, last)
        premium, fees = n * 100 * pick["bid"], n * FEE
        self.cash += premium - fees
        self.opt = {**pick, "n": n, "sale_day": d, "spot": spot, "sale_price": pick["bid"], "premium": premium,
                    "sale_fees": fees, "last_day": last, "end_reason": why_end, "quotes": quotes, "qi": 0,
                    "mark": (pick["bid"] + pick["ask"]) / 2, "mark_day": d}
        if not quotes:
            self.flags["contract_with_no_quotes"] += 1
        return True

    # -- the open contract on day d (minutes after the sale, then expiration / split eve)
    def manage(self, d, close):
        o = self.opt
        quotes = o["quotes"]
        while o["qi"] < len(quotes) and quotes[o["qi"]][0].date() <= d:
            ts, bid, ask = quotes[o["qi"]]
            o["qi"] += 1
            if ts.date() < d:
                continue
            if self.rules.early_close and 0 < ask <= TAKE * o["sale_price"] + EPS:
                self.record(d, "closed_early_75pct", ask, ts)
                self.resell_from = d if ts.time() < DECIDE else self.next_day(d)
                return
            if ask > 0 and ask >= bid:
                o["mark"], o["mark_day"] = (bid + ask) / 2, d
        if d != o["last_day"] or o["end_reason"] == "end_of_test":
            return
        if o["end_reason"] == "split":
            if o["mark_day"] != d:
                self.flags["split_close_used_stale_mid"] += 1
            self.record(d, "closed_before_split_at_mid", o["mark"], None)
            self.resell_from = self.next_day(d)
            return
        how = settle(o["kind"], o["strike"], close)
        n, k = o["n"], o["strike"]
        share_cash = 0.0
        if how == "assigned":
            share_cash = -n * 100 * k
            self.shares += n * 100
            self.basis = k
        elif how == "called_away":
            share_cash = n * 100 * k
            self.shares -= n * 100
            if abs(self.shares) < 1e-7:
                self.shares, self.basis = 0.0, None
        self.cash += share_cash
        self.record(d, how, 0.0, None, close_cash=0.0, fee=False, share_cash=share_cash, settle_close=close)
        self.resell_from = self.next_day(d)

    def record(self, d, how, price, ts, close_cash=None, fee=True, share_cash=0.0, settle_close=None, liability=0.0):
        o = self.opt
        n = o["n"]
        cost = n * 100 * price if close_cash is None else close_cash
        fees = n * FEE if fee else 0.0
        self.cash -= cost + fees
        self.trades.append({
            "ticker": self.ticker, "kind": o["kind"], "sale_day": o["sale_day"].isoformat(),
            "expiration": o["expiration"].isoformat(), "strike": o["strike"], "spot_1545": o["spot"],
            "delta": round(o["delta"], 4), "iv": round(o["iv"], 4), "fallback_expiration": o["fallback"],
            "contracts": n, "sale_bid": o["bid"], "sale_ask": o["ask"], "premium": o["premium"],
            "sale_fees": o["sale_fees"], "end_day": d.isoformat(), "how": how, "close_price": price,
            "close_minute": ts.isoformat() if ts is not None else None, "close_cost": cost, "close_fees": fees,
            "open_liability": liability, "share_cash": share_cash, "settle_close": settle_close,
            "option_pnl": o["premium"] - o["sale_fees"] - cost - fees - liability,
            "shares_after": self.shares, "cash_after": self.cash})
        self.opt = None


# ---------------------------------------------------------------- holding the same stock

def hold(ticker, provider, days):
    """$40,000 at the Jan 2, 2020 15:45 price (fractional), dividends to cash earning T-bills, splits applied."""
    spot = provider.spot(ticker, days[0])
    shares, cash, interest, dividends, curve, prev = SLEEVE / spot, 0.0, 0.0, 0.0, [], None
    splits, divs = provider.splits(ticker), provider.dividends(ticker)
    for d in days:
        if prev is not None:
            earned = cash * provider.rate(prev) * (d - prev).days / 365
            cash += earned
            interest += earned
        prev = d
        if d in divs and d != days[0]:
            cash += shares * divs[d]
            dividends += shares * divs[d]
        if d in splits and d != days[0]:
            shares *= splits[d]
        curve.append((d, cash + shares * provider.close(ticker, d)))
    share_pnl = shares * provider.close(ticker, days[-1]) - SLEEVE
    return {"curve": curve, "shares_end": shares, "entry_price": spot, "dividends": dividends, "interest": interest,
            "share_pnl": share_pnl, "final_value": curve[-1][1]}


# ---------------------------------------------------------------- reporting (dollars first)

def drawdown(values):
    peak, worst_pct, worst_usd = values[0], 0.0, 0.0
    for v in values:
        peak = max(peak, v)
        worst_pct = min(worst_pct, v / peak - 1)
        worst_usd = min(worst_usd, v - peak)
    return worst_pct, worst_usd


def period_changes(curve, start_value, key):
    ends = OrderedDict()
    for d, v in curve:
        ends[key(d)] = (d, v)
    out, prev = [], start_value
    for k, (d, v) in ends.items():
        out.append((k, d, v - prev))
        prev = v
    return out


def dollar_summary(curve, start_value):
    values = [v for _, v in curve]
    weeks = period_changes(curve, start_value, lambda d: tuple(d.isocalendar()[:2]))
    months = period_changes(curve, start_value, lambda d: d.strftime("%Y-%m"))
    w = [x[2] for x in weeks]
    dd_pct, dd_usd = drawdown([start_value] + values)
    worst_w, worst_m = min(weeks, key=lambda x: x[2]), min(months, key=lambda x: x[2])
    value_on = dict(curve)
    def pnl_between(a, b):
        inside = [d for d, _ in curve if a <= d <= b]
        if not inside:
            return None
        before = [d for d, _ in curve if d < inside[0]]
        return round(value_on[inside[-1]] - (value_on[before[-1]] if before else start_value), 2)

    halves = {name: pnl_between(a, b) for name, a, b in HALVES}
    years = sorted({d.year for d, _ in curve})
    by_year = {str(y): pnl_between(date(y, 1, 1), date(y, 12, 31)) for y in years}
    return {"start_value": round(start_value, 2), "final_value": round(values[-1], 2),
            "total_pnl": round(values[-1] - start_value, 2), "weeks": len(w),
            "avg_per_week": round(statistics.mean(w), 2), "median_per_week": round(statistics.median(w), 2),
            "share_of_weeks_at_least_1000_pct": round(100 * sum(x >= 1000 for x in w) / len(w), 1),
            "share_of_weeks_losing_pct": round(100 * sum(x < 0 for x in w) / len(w), 1),
            "worst_week": {"week_ending": worst_w[1].isoformat(), "usd": round(worst_w[2], 2)},
            "best_week": {"week_ending": max(weeks, key=lambda x: x[2])[1].isoformat(),
                          "usd": round(max(w), 2)},
            "worst_month": {"month": worst_m[0], "usd": round(worst_m[2], 2)},
            "worst_drop_from_high_pct": round(100 * dd_pct, 2), "worst_drop_from_high_usd": round(dd_usd, 2),
            "pnl_by_half": halves, "pnl_by_year": by_year}


def sum_curves(curves):
    days = [d for d, _ in curves[0]]
    for c in curves:
        if [d for d, _ in c] != days:
            raise AssertionError("curves cover different days")
    return [(d, sum(c[i][1] for c in curves)) for i, d in enumerate(days)]


def sleeve_report(s, provider):
    """Per-stock dollars, hit rates, and the checks that every contract is recorded and the trades add up."""
    t = s.trades
    end, close = s.days[-1], provider.close(s.ticker, s.days[-1])
    final = s.curve[-1][1]
    opened = len(t)
    closed = sum(x["how"] != "open_at_end" for x in t)
    assert opened == closed + (1 if t and t[-1]["how"] == "open_at_end" else 0), "unrecorded contract"
    assert all(x["how"] != "open_at_end" for x in t[:-1]), "open_at_end must be last"
    option_net = sum(x["option_pnl"] for x in t)
    share_pnl = sum(x["share_cash"] for x in t) + s.shares * close
    from_trades = SLEEVE + option_net + share_pnl + s.dividends + s.interest
    assert abs(from_trades - final) < 1e-6 * max(1.0, abs(final)), f"{s.ticker}: trades {from_trades} != value {final}"
    later = {}
    for x in t:
        if x["how"] == "called_away":
            d = date.fromisoformat(x["end_day"])
            factor = math.prod(r for ex, r in s.split_ratio.items() if d < ex <= end)
            later[id(x)] = close * factor
    counts = Counter(x["how"] for x in t)
    n = max(len(t), 1)
    return {
        "final_value": round(final, 2), "total_pnl": round(final - SLEEVE, 2),
        "premiums_collected": round(sum(x["premium"] for x in t), 2),
        "sale_fees": round(sum(x["sale_fees"] for x in t), 2),
        "buybacks_incl_fees": round(sum(x["close_cost"] + x["close_fees"] for x in t), 2),
        "open_option_at_mid": round(sum(x["open_liability"] for x in t), 2),
        "option_net": round(option_net, 2), "share_pnl": round(share_pnl, 2),
        "dividends": round(s.dividends, 2), "interest": round(s.interest, 2),
        "contracts_sold": len(t), "puts_sold": sum(x["kind"] == "P" for x in t),
        "calls_sold": sum(x["kind"] == "C" for x in t),
        "times_assigned": counts["assigned"], "times_called_away": counts["called_away"],
        "given_up_when_called_away_vs_expiration_close": round(sum(
            (x["settle_close"] - x["strike"]) * x["contracts"] * 100 for x in t if x["how"] == "called_away"), 2),
        "given_up_when_called_away_vs_oct9_2026_price": round(sum(
            max(later[id(x)] - x["strike"], 0.0) * x["contracts"] * 100 for x in t if x["how"] == "called_away"), 2),
        "outcomes": dict(counts),
        "hit_rates_pct": {k: round(100 * counts[k] / n, 1) for k in
                          ("closed_early_75pct", "expired_worthless", "assigned", "called_away",
                           "closed_before_split_at_mid", "open_at_end")},
        "fallback_expirations": sum(x["fallback_expiration"] for x in t),
        "shares_at_end": s.shares, "cash_at_end": round(s.cash, 2),
        "skipped_days": dict(s.skips), "flags": dict(s.flags),
        "median_delta": statistics.median(abs(x["delta"]) for x in t) if t else None,
        "median_days_to_expiration": statistics.median(
            (date.fromisoformat(x["expiration"]) - date.fromisoformat(x["sale_day"])).days for x in t) if t else None,
    }


def combine(per_stock):
    keys = ("premiums_collected", "sale_fees", "buybacks_incl_fees", "open_option_at_mid", "option_net", "share_pnl",
            "dividends", "interest", "contracts_sold", "times_assigned", "times_called_away",
            "given_up_when_called_away_vs_expiration_close", "given_up_when_called_away_vs_oct9_2026_price",
            "fallback_expirations")
    out = {k: round(sum(v[k] for v in per_stock.values()), 2) for k in keys}
    counts = Counter()
    for v in per_stock.values():
        counts.update(v["outcomes"])
    n = max(sum(counts.values()), 1)
    out["outcomes"] = dict(counts)
    out["hit_rates_pct"] = {k: round(100 * counts[k] / n, 1) for k in
                            ("closed_early_75pct", "expired_worthless", "assigned", "called_away",
                             "closed_before_split_at_mid", "open_at_end")}
    out["premiums_minus_buybacks_and_fees"] = round(out["premiums_collected"] - out["sale_fees"]
                                                    - out["buybacks_incl_fees"], 2)
    return out


def run_version(name, provider, days, tickers=TICKERS, workers=5):
    rules = VERSIONS[name]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        sleeves = list(pool.map(lambda tk: Sleeve(tk, rules, provider, days).run(), tickers))
    per_stock = {s.ticker: sleeve_report(s, provider) for s in sleeves}
    curve = sum_curves([s.curve for s in sleeves])
    summary = {**dollar_summary(curve, SLEEVE * len(tickers)), **combine(per_stock)}
    return {"rules": asdict(rules), "summary": summary, "per_stock": per_stock,
            "trades": [x for s in sleeves for x in s.trades], "curve": [[d.isoformat(), round(v, 2)] for d, v in curve]}


def run_holding(provider, days, tickers=TICKERS):
    held = {t: hold(t, provider, days) for t in tickers}
    curve = sum_curves([h["curve"] for h in held.values()])
    per_stock = {t: {"final_value": round(h["final_value"], 2), "total_pnl": round(h["final_value"] - SLEEVE, 2),
                     "share_pnl": round(h["share_pnl"], 2), "dividends": round(h["dividends"], 2),
                     "interest": round(h["interest"], 2), "entry_price_1545": h["entry_price"],
                     "shares_at_end": h["shares_end"]} for t, h in held.items()}
    return {"summary": dollar_summary(curve, SLEEVE * len(tickers)), "per_stock": per_stock,
            "curve": [[d.isoformat(), round(v, 2)] for d, v in curve]}


def checks(main, holding):
    s, h = main["summary"], holding["summary"]
    c = {"C1_final_value_at_least_holding": s["final_value"] >= h["final_value"],
         "C2_profitable_in_both_halves": all(v is not None and v > 0 for v in s["pnl_by_half"].values()),
         "C3_worst_drop_at_most_25pct": s["worst_drop_from_high_pct"] >= -25.0}
    return c, ("PASS" if all(c.values()) else "FAIL")


def main():
    from research.provenance_v1.provenance import write_manifest
    from research.wheel_test_v1.data import DATA, Provider
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default=str(OUT))
    ap.add_argument("--versions", default=",".join(VERSIONS))
    args = ap.parse_args()
    provider = Provider()
    days = provider.trading_days(START, END)
    names = args.versions.split(",")
    results = {}
    if "main" in names:  # main first, so the $40 hard stop can only ever cut an information version short
        results["main"] = run_version("main", provider, days)
        print(json.dumps({"version_done": "main", "databento_spent_total": round(provider.db.spent, 4)}), flush=True)
    rest = [n for n in names if n != "main"]
    if rest:
        with ThreadPoolExecutor(max_workers=len(rest)) as pool:  # the info versions together; they share the cache
            results.update(zip(rest, pool.map(lambda n: run_version(n, provider, days), rest)))
        print(json.dumps({"versions_done": rest, "databento_spent_total": round(provider.db.spent, 4)}), flush=True)
    holding = run_holding(provider, days)
    out = {"plan": PLAN, "first": days[0].isoformat(), "last": days[-1].isoformat(), "trading_days": len(days),
           "holding_same_five": holding, "versions": results}
    if "main" in results:
        out["checks"], out["verdict"] = checks(results["main"], holding)
    out["databento_spent_total_dollars"] = round(provider.db.spent, 4)
    Path(args.output).write_text(json.dumps(out, indent=1, default=str) + "\n")
    data_files = sorted(str(p) for p in DATA.rglob("*") if p.is_file() and not p.name.endswith(".tmp")
                        and p.name not in ("databento_ledger.csv", "databento_spent.json"))
    write_manifest(args.output, code=["research/wheel_test_v1/backtest.py", "research/wheel_test_v1/data.py",
                                      "research/spy_put_spread_backtest_v1/backtest.py",
                                      "research/cc_spy_test_v1/backtest.py"],
                   data=data_files + ["research/spy_put_spread_backtest_v1/tbill_3m_monthly.csv"],
                   params={"versions": {k: asdict(v) for k, v in VERSIONS.items()}, "fee": FEE, "sleeve": SLEEVE,
                           "start": START.isoformat(), "end": END.isoformat(), "take": TAKE,
                           "expiration_band": EXP_BAND, "expiration_fallback": EXP_FALLBACK})


if __name__ == "__main__":
    main()
