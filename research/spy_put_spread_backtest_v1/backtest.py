"""Historical replay of the approved SPY bull put spread rules (research/spy_put_spread_v1/PROTOCOL.md).

Input: outputs/spy_options_data/YYYY/YYYY-MM-DD.csv.gz from fetch_databento.py, with Databento OPRA consolidated
best bid/ask for the SPY chain at 10:30 ET ("t1030") and the session close ("close"). SPY's price comes from
put-call parity in the same snapshot; implied volatility and delta come from Black-Scholes with dividend yield
1.5% and the monthly 3-month T-bill rate. No trading or network access.

Each day, in the live bot's order:
- 10:30: a resting profit-take fills if the cost to close is at or below its limit.
- Exit if the prior session's SPY close is below (short strike - credit), or 5 or fewer sessions remain.
- Mondays only, when flat and not exited that day: the trend, volatility and credit filters, then entry.
- Close: the profit-take check again, and a mark-to-market of equity.
Two fill scenarios: "mid" (enter/exit at mid) and "natural" (credit = short bid - long ask; cost to close =
short ask - long bid). The profit-take fills at its limit when the scenario's cost to close reaches it.
Fees: $0.03 per contract per leg per trade.

  PYTHONPATH=src:. .venv/bin/python -m research.spy_put_spread_backtest_v1.backtest --output output/spy-put-spread-backtest.json
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/spy_options_data"
HERE = Path(__file__).resolve().parent
Q = 0.015
WIDTH, TARGET_DELTA, MIN_CREDIT, RISK, MAX_CONTRACTS = 5.0, 0.20, 0.75, 0.02, 5
IV_RV_MIN, DTE_MIN, DTE_MAX, DTE_TARGET, TIME_EXIT_SESSIONS = 1.2, 21, 35, 30, 5
FEE_PER_LEG, START_EQUITY = 0.03, 100_000.0


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs_put(s, k, t, r, sigma, q=Q):
    if t <= 0 or sigma <= 0:
        return max(k - s, 0.0), (-1.0 if k > s else 0.0)
    d1 = (math.log(s / k) + (r - q + sigma * sigma / 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    price = k * math.exp(-r * t) * norm_cdf(-d2) - s * math.exp(-q * t) * norm_cdf(-d1)
    return price, -math.exp(-q * t) * norm_cdf(-d1)


def implied_vol(price, s, k, t, r, q=Q):
    intrinsic = max(k * math.exp(-r * t) - s * math.exp(-q * t), 0.0)
    if t <= 0 or price <= intrinsic + 1e-6:
        return None
    lo, hi = 0.005, 4.0
    if bs_put(s, k, t, r, hi, q)[0] < price:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if bs_put(s, k, t, r, mid, q)[0] > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def load_rates(path=HERE / "tbill_3m_monthly.csv"):
    return {row["month"]: float(row["rate_pct"]) / 100 for row in csv.DictReader(path.open())}


def load_day(path):
    """{window: {(expiration, type, strike): (bid, ask)}} keeping only two-sided quotes."""
    snap = defaultdict(dict)
    with gzip.open(path, "rt") as handle:
        for row in csv.DictReader(handle):
            bid, ask = float(row["bid"]), float(row["ask"])
            if bid > 0 and ask >= bid:
                snap[row["window"]][(date.fromisoformat(row["expiration"]), row["type"], float(row["strike"]))] = (bid, ask)
    return snap


def parity_spot(quotes, day, r, hours_left):
    """SPY from put-call parity at the nearest expiration at least 1 day out (median of 3 near-the-money strikes)."""
    expirations = sorted({k[0] for k in quotes if (k[0] - day).days >= 1})
    for expiration in expirations[:3]:
        t = ((expiration - day).days + hours_left / 24) / 365
        pairs = []
        for (e, typ, strike), (bid, ask) in quotes.items():
            if e == expiration and typ == "C" and (e, "P", strike) in quotes:
                pb, pa = quotes[(e, "P", strike)]
                pairs.append((abs((bid + ask) / 2 - (pb + pa) / 2), strike, (bid + ask) / 2 - (pb + pa) / 2))
        if len(pairs) >= 3:
            pairs.sort()
            spots = [(diff + k * math.exp(-r * t)) * math.exp(Q * t) for _, k, diff in pairs[:3]]
            return statistics.median(spots)
    return None


def mid(q):
    return (q[0] + q[1]) / 2


def floor_cents(x):
    return math.floor(x * 100 + 1e-9) / 100


APPROVED = {"short_delta": TARGET_DELTA, "width": WIDTH, "long_delta": None, "min_credit": MIN_CREDIT}
# Pre-declared on Sept 28 after the approved rule proved almost never to trade (median credit $0.40-0.67):
# the smallest fix, and the structure of the FlashAlpha study that motivated the volatility filter.
VARIANTS = {"approved_5wide_min075": APPROVED,
            "5wide_min050": {**APPROVED, "min_credit": 0.50},
            "delta25_10_nomin": {"short_delta": 0.25, "width": None, "long_delta": 0.10, "min_credit": 0.0}}


class Replay:
    def __init__(self, days, calendar, rates, scenario, use_vol_filter=True, rules=None, name="approved_5wide_min075"):
        self.days, self.calendar, self.rates = days, calendar, rates
        self.scenario, self.use_vol_filter = scenario, use_vol_filter
        self.rules, self.name = rules or APPROVED, name
        self.cash, self.position, self.trades, self.marks = START_EQUITY, None, [], []
        self.stats, self.closes = Counter(), []

    def rate(self, day):
        return self.rates.get(day.strftime("%Y-%m"), 0.0)

    def close_cost(self, quotes):
        p = self.position
        short, long = quotes.get(p["short_key"]), quotes.get(p["long_key"])
        if short is None or long is None:
            return None
        return mid(short) - mid(long) if self.scenario == "mid" else short[1] - long[0]

    def exit(self, day, cost, reason):
        p = self.position
        fees = FEE_PER_LEG * 2 * p["qty"]
        self.cash -= cost * 100 * p["qty"] + fees
        pnl = (p["credit"] - cost) * 100 * p["qty"] - p["entry_fees"] - fees
        self.trades.append({**{k: v for k, v in p.items() if not k.endswith("_key")}, "exit_date": day.isoformat(),
                            "exit_cost": round(cost, 4), "reason": reason, "pnl": round(pnl, 2)})
        self.position = None

    def check_profit_take(self, day, quotes):
        if self.position:
            cost = self.close_cost(quotes)
            if cost is not None and cost <= self.position["tp_limit"]:
                self.exit(day, self.position["tp_limit"], "profit_take")

    def sessions_left(self, day, expiration):
        return sum(1 for d in self.calendar if day < d <= expiration)

    def entry(self, day, quotes, spot):
        self.stats["mondays_evaluated"] += 1
        closes = self.closes
        if len(closes) < 51:
            self.stats["skip_history"] += 1
            return
        r = self.rate(day)
        last = closes[-1]
        sma50 = sum(closes[-50:]) / 50
        rets = [math.log(b / a) for a, b in zip(closes[-21:], closes[-20:])]
        rv20 = statistics.stdev(rets) * math.sqrt(252)
        expirations = sorted({k[0] for k in quotes if k[1] == "P" and DTE_MIN <= (k[0] - day).days <= DTE_MAX})
        if not expirations:
            self.stats["skip_no_expiration"] += 1
            return
        expiration = min(expirations, key=lambda e: (abs((e - day).days - DTE_TARGET), e))
        t = ((expiration - day).days + 5.5 / 24) / 365
        chain = {k[2]: v for k, v in quotes.items() if k[0] == expiration and k[1] == "P"}
        atm_strike = min(chain, key=lambda k: abs(k - spot))
        atm_iv = implied_vol(mid(chain[atm_strike]), spot, atm_strike, t, r)
        trend_ok = last > sma50
        vol_ok = atm_iv is not None and atm_iv >= IV_RV_MIN * rv20
        self.stats["trend_ok"] += trend_ok
        self.stats["vol_ok"] += vol_ok
        if not trend_ok or (self.use_vol_filter and not vol_ok):
            self.stats["skip_filters"] += 1
            return
        rules = self.rules
        deltas = {}
        for strike, q in chain.items():
            if strike < spot:
                iv = implied_vol(mid(q), spot, strike, t, r)
                if iv is not None:
                    deltas[strike] = bs_put(spot, strike, t, r, iv)[1]
        shorts = [(abs(abs(d) - rules["short_delta"]), -k, k, d) for k, d in deltas.items()
                  if rules["width"] is None or k - rules["width"] in chain]
        if not shorts:
            self.stats["skip_no_candidates"] += 1
            return
        _, _, short_k, delta = min(shorts)
        if rules["width"] is not None:
            long_k = short_k - rules["width"]
        else:
            longs = [(abs(abs(d) - rules["long_delta"]), k) for k, d in deltas.items() if k < short_k]
            if not longs:
                self.stats["skip_no_candidates"] += 1
                return
            long_k = min(longs)[1]
        width = short_k - long_k
        short, long = chain[short_k], chain[long_k]
        mid_credit = floor_cents(mid(short) - mid(long))
        if mid_credit < rules["min_credit"] or mid_credit <= 0 or mid_credit >= width:
            self.stats["skip_credit"] += 1
            return
        equity = self.equity_mark(quotes) if self.position else self.cash
        qty = min(MAX_CONTRACTS, int(equity * RISK // ((width - mid_credit) * 100)))
        credit = mid_credit if self.scenario == "mid" else round(short[0] - long[1], 2)
        if qty < 1 or credit <= 0:
            self.stats["skip_size_or_fill"] += 1
            return
        fees = FEE_PER_LEG * 2 * qty
        self.cash += credit * 100 * qty - fees
        self.position = {"entry_date": day.isoformat(), "expiration": expiration.isoformat(), "short": short_k,
                         "long": long_k, "width": width, "delta": round(delta, 3), "qty": qty, "credit": credit,
                         "mid_credit": mid_credit, "breakeven": short_k - credit, "tp_limit": floor_cents(credit / 2),
                         "max_loss": round((width - credit) * 100 * qty, 2),
                         "entry_fees": fees, "spot": round(spot, 2), "atm_iv": round(atm_iv or 0, 4),
                         "rv20": round(rv20, 4), "short_key": (expiration, "P", short_k),
                         "long_key": (expiration, "P", long_k)}
        self.stats["entries"] += 1

    def equity_mark(self, quotes):
        if not self.position:
            return self.cash
        p = self.position
        short, long = quotes.get(p["short_key"]), quotes.get(p["long_key"])
        value = (mid(short) - mid(long)) if short and long else p.get("last_value", p["width"] / 2)
        p["last_value"] = value
        return self.cash - value * 100 * p["qty"]

    def step(self, day, morning, close, morning_spot, close_spot):
        """One trading day, in the live bot's order. Only a break-even or time exit blocks a same-day entry."""
        exited = False
        if self.position and day >= date.fromisoformat(self.position["expiration"]):
            spot = morning_spot or (self.closes[-1] if self.closes else None)
            if spot is not None:  # Safeguard only: missing quotes kept the time exit from firing.
                self.exit(day, min(self.position["width"], max(0.0, self.position["short"] - spot)), "expired_settlement")
                self.stats["expired_settlement"] += 1
        if self.position and morning:
            self.check_profit_take(day, morning)
            if self.position:
                expiration = date.fromisoformat(self.position["expiration"])
                reason = ("breakeven" if self.closes and self.closes[-1] < self.position["breakeven"]
                          else "time" if self.sessions_left(day, expiration) <= TIME_EXIT_SESSIONS else None)
                cost = self.close_cost(morning) if reason else None
                if reason and cost is not None:
                    self.exit(day, cost, reason)
                    exited = True
                elif reason:
                    self.stats["exit_deferred_missing_quote"] += 1
        if day.weekday() == 0 and not self.position and not exited and morning and morning_spot:
            self.entry(day, morning, morning_spot)
        elif day.weekday() == 0 and exited:
            self.stats["no_same_day_reentry"] += 1
        if close:
            self.check_profit_take(day, close)
            if close_spot is not None:
                self.closes.append(close_spot)
            self.marks.append((day.isoformat(), round(self.equity_mark(close), 2)))

    def report(self, holdout_from=None):
        pnls = [t["pnl"] for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        periods = {}
        if holdout_from:
            for label, keep in (("development", lambda t: t["entry_date"] < holdout_from),
                                ("holdout", lambda t: t["entry_date"] >= holdout_from)):
                chosen = [t for t in self.trades if keep(t)]
                periods[label] = period_stats(chosen)
        peak, drawdown, worst = START_EQUITY, 0.0, None
        for day, equity in self.marks:
            peak = max(peak, equity)
            if equity / peak - 1 < drawdown:
                drawdown, worst = equity / peak - 1, day
        years = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "wins": 0})
        for t in self.trades:
            y = years[t["exit_date"][:4]]
            y["trades"] += 1
            y["pnl"] = round(y["pnl"] + t["pnl"], 2)
            y["wins"] += t["pnl"] > 0
        final = self.marks[-1][1] if self.marks else START_EQUITY
        span_years = max((date.fromisoformat(self.marks[-1][0]) - date.fromisoformat(self.marks[0][0])).days / 365.25, 1e-9) if self.marks else 1
        return {"variant": self.name, "rules": self.rules, "scenario": self.scenario, "vol_filter": self.use_vol_filter,
                "first_day": self.marks[0][0] if self.marks else None, "last_day": self.marks[-1][0] if self.marks else None,
                "trades_per_year": round(len(pnls) / span_years, 2), "periods": periods,
                "avg_return_on_risk_pct": period_stats(self.trades)["avg_return_on_risk_pct"],
                "trades": len(pnls), "win_rate": round(len(wins) / len(pnls), 3) if pnls else None,
                "avg_win": round(statistics.mean(wins), 2) if wins else None,
                "avg_loss": round(statistics.mean(losses), 2) if losses else None,
                "worst_trade": min(pnls) if pnls else None, "best_trade": max(pnls) if pnls else None,
                "total_pnl": round(sum(pnls), 2), "final_equity": final,
                "cagr_pct": round(((final / START_EQUITY) ** (1 / span_years) - 1) * 100, 2),
                "max_drawdown_pct": round(drawdown * 100, 2), "max_drawdown_day": worst,
                "exit_reasons": dict(Counter(t["reason"] for t in self.trades)), "by_year": dict(sorted(years.items())),
                "filter_stats": dict(self.stats), "open_position_at_end": bool(self.position), "trade_list": self.trades}


def period_stats(trades):
    pnls = [t["pnl"] for t in trades]
    rors = [t["pnl"] / t["max_loss"] * 100 for t in trades if t.get("max_loss")]
    wins = [p for p in pnls if p > 0]
    return {"trades": len(pnls), "win_rate": round(len(wins) / len(pnls), 3) if pnls else None,
            "total_pnl": round(sum(pnls), 2), "avg_pnl": round(statistics.mean(pnls), 2) if pnls else None,
            "worst_trade": min(pnls) if pnls else None,
            "avg_return_on_risk_pct": round(statistics.mean(rors), 2) if rors else None,
            "exit_reasons": dict(Counter(t["reason"] for t in trades))}


def available_days():
    return sorted(date.fromisoformat(p.name[:10]) for p in DATA.glob("*/*.csv.gz"))


def calendar_days(first, last):
    from research.lite_volume_rebound_v1.refresh import client_from_local_keys
    rows = client_from_local_keys()._request("GET", "/v2/calendar", query={"start": first.isoformat(), "end": last.isoformat()})
    return [date.fromisoformat(r["date"]) for r in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--through", type=date.fromisoformat, help="ignore data after this date (e.g. while downloading)")
    parser.add_argument("--holdout-from", help="report trades entered on/after this date (YYYY-MM-DD) separately")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    days = [d for d in available_days() if args.through is None or d <= args.through]
    calendar = calendar_days(days[0], date(days[-1].year + 1, 3, 31))
    missing = [d for d in calendar if days[0] <= d <= days[-1] and d not in set(days)]
    rates = load_rates()
    replays = [Replay(days, calendar, rates, scenario, vol, rules, name) for name, rules in VARIANTS.items()
               for vol in (True, False) for scenario in ("mid", "natural")]
    spots = []
    for day in days:  # Each day's file is read once and fed to all four scenarios.
        snap = load_day(DATA / str(day.year) / f"{day.isoformat()}.csv.gz")
        morning, close = snap.get("t1030", {}), snap.get("close", {})
        r = rates.get(day.strftime("%Y-%m"), 0.0)
        morning_spot, close_spot = parity_spot(morning, day, r, 5.5), parity_spot(close, day, r, 0)
        spots.append(close_spot)
        for replay in replays:
            replay.step(day, morning, close, morning_spot, close_spot)
    results = [replay.report(args.holdout_from) for replay in replays]
    spots = [s for s in (spots[0], spots[-1])]
    out = {"status": "HISTORICAL_REPLAY_NOT_LIVE_EVIDENCE", "data_days": len(days), "first": days[0].isoformat(),
           "last": days[-1].isoformat(), "calendar_days_missing_data": [d.isoformat() for d in missing],
           "spy_price_change_pct_no_dividends": round((spots[1] / spots[0] - 1) * 100, 2) if all(spots) else None,
           "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, default=str) + "\n")
    for res in results:
        print(json.dumps({k: res[k] for k in ("variant", "scenario", "vol_filter", "trades", "trades_per_year", "win_rate",
                                               "avg_win", "avg_loss", "worst_trade", "total_pnl",
                                               "avg_return_on_risk_pct", "max_drawdown_pct")}))


if __name__ == "__main__":
    main()
