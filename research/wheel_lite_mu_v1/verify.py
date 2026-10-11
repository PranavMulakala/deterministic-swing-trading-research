"""Independent verifier for pre-declared test #32, the weekly wheel on LITE and MU
(plan: output/WHEEL_LITE_MU_TEST_PLAN_20261010.md; inherited conventions: output/WHEEL_TEST_PLAN_20261010.md).
Written from the plans and test #29's independent verifier (research/wheel_test_v1/verify.py), WITHOUT reading
research/wheel_test_v1/backtest.py, research/wheel_lite_mu_v1/backtest.py or their tests.

Judgment calls (test #29 verifier's, plus #32's settings):
- 15:45 decision on any trading day with no open option and a 15:45 SIP price (half days: no price, no sale); no new
  sale on the last day (Oct 9, 2026).
- Expiration: among expirations with a two-sided quote of the right type, closest to 7 calendar days within 4-13 (ties
  go to the later one), else the nearest within 4-45 (a "fallback").
- Strike: put strictly below / call strictly above the 15:45 price, bid > 0, Black-Scholes delta from the mid's implied
  vol (q = 0, the T-bill rate, t = (calendar days + 15 min) / 365), |delta| in 0.25-0.35 inclusive, closest to 0.30
  (ties: the strike further from the price). Calls must ALSO have strike >= the assignment (put) strike; the floor
  filters the band first, and if nothing in the band qualifies nothing is sold that day.
- Fractional size: puts = cash / (strike x 100) (cash before the premium); calls = shares / 100.
- Sale at the bid minus $0.03 a contract. Buyback: the first minute after the 15:45 sale minute (through 16:00) with
  0 < ask <= 50% of the sale bid, at ask + $0.03 a contract; before 15:45 -> sell again at 15:45 that day, otherwise
  the next trading day.
- Expiration judged on the official close: put assigned if close < strike, call away if close > strike; else worthless.
- Dividends credited on the ex-date for shares held; cash (incl. put collateral) earns the monthly T-bill rate x
  calendar days / 365, credited each trading day (the rate of the day's month by default; --rate-prev uses the previous
  trading day's month, the engine's convention, found after the first run: it removes the cent-level size differences); account value = cash + shares x close - open option x last mid.
- Neither stock split 2020-2026 (asserted from the cached corporate actions).

1. Full independent replay of the MAIN version for both $100,000 accounts from the cached raw files. Before the results
   JSON exists it stops at the first contract whose quote file is not cached (the run's frontier).
2. 12 random main-version contracts (random.Random(3232), 6 per stock), recomputed standalone (pick, sale price,
   buyback/expiry outcome, P&L), the call floor taken from the preceding assigned put in the same contract list.
3. Each account's final value and the holding comparison ($100,000 of each stock at the Jan 2, 2020 15:45 price,
   dividends to cash earning T-bills, valued at the Oct 9, 2026 close).
4. With output/wheel-lite-mu-test-results.json: every main contract compared field by field with the replay, account
   final values within $1, holding values within $1.

Only cached files are read; nothing is fetched or bought. Prints a JSON summary; exits non-zero on any mismatch.

  PYTHONPATH=src:. .venv/bin/python -m research.wheel_lite_mu_v1.verify [--rate-prev]

First run vs the results (Oct 11): 0 substantive contract differences on MU; 1 on LITE (2025-08-28 put), because this
file first stopped the buyback scan at 15:59 while the engine (and the plan's "through 16:00" window) includes the
16:00:00 quote. Fixed here to 16:00. With --rate-prev every contract and both final values match exactly.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime, time as dtime, timedelta, timezone
import gzip
import json
from pathlib import Path
import random
import sys
from zoneinfo import ZoneInfo

from research.cc_spy_test_v1.backtest import bs_call, call_iv
from research.spy_put_spread_backtest_v1.backtest import bs_put, implied_vol, load_rates as load_shared_rates

NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/wheel_lite_mu_data"
RESULTS = ROOT / "output/wheel-lite-mu-test-results.json"
TICKERS = ("LITE", "MU")
FIRST, LAST = date(2020, 1, 2), date(2026, 10, 9)
ACCOUNT = 100_000.0
FEE = 0.03
TARGET, BAND = 0.30, (0.25, 0.35)
TAKE = 0.50
DECIDE = dtime(15, 45)
LAST_MINUTE = dtime(16, 0)   # the plan's quote window runs "through 16:00" (test #29 plan, Data)
RATE_FROM_PREV = "--rate-prev" in sys.argv  # diagnostic: accrue at the previous trading day's month rate
PRICE_TOL = 0.005
INFO_VERSIONS = ("no_basis_floor", "delta_20", "hold_to_expiry", "skip_earnings", "whole_contracts")
EPS = 1e-9


# ------------------------------------------------------------------ raw files (own readers)

def daily(ticker):
    return {date.fromisoformat(d): float(c) for d, c in json.loads((DATA / f"daily_{ticker}.json").read_text()).items()}


def spot1545(day, ticker):
    p = DATA / "spot1545" / f"{day.isoformat()}.json"
    if not p.exists():
        return "missing"
    return json.loads(p.read_text()).get(ticker)


def chain_file(ticker, day):
    p = DATA / "chain" / ticker / f"{day.isoformat()}.csv.gz"
    if not p.exists():
        return None
    with gzip.open(p, "rt") as f:
        return [(date.fromisoformat(r["expiration"]), r["type"], float(r["strike"]), float(r["bid"]), float(r["ask"]))
                for r in csv.DictReader(f)]


def osi_compact(ticker, exp, kind, strike):
    return f"{ticker}{exp:%y%m%d}{kind}{round(strike * 1000):08d}"


def quote_files(ticker, sale_day, exp, kind, strike):
    return sorted((DATA / "quotes" / ticker).glob(f"{sale_day.isoformat()}_{osi_compact(ticker, exp, kind, strike)}_*.csv.gz"))


def read_quotes(path):
    """{date: [(NY datetime, bid, ask)]} sorted by time, minutes through 16:00 (the plan's window)."""
    by_day = defaultdict(list)
    with gzip.open(path, "rt") as f:
        for r in csv.DictReader(f):
            if not r["ts"]:
                continue
            ts = datetime.strptime(r["ts"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(NY)
            if ts.time() <= LAST_MINUTE:
                by_day[ts.date()].append((ts, float(r["bid"]), float(r["ask"])))
    for v in by_day.values():
        v.sort(key=lambda x: x[0])
    return dict(by_day)


def corporate_actions():
    ca = json.loads((DATA / "corporate_actions.json").read_text())
    splits = [s for s in ca["forward_splits"] if s["symbol"] in TICKERS]
    divs = defaultdict(lambda: defaultdict(float))
    for d in ca["cash_dividends"]:
        divs[d["symbol"]][date.fromisoformat(d["ex_date"])] += float(d["rate"])
    return splits, divs


def rates():
    r = load_shared_rates()
    last_shared = max(r)
    with (DATA / "tb3ms.csv").open() as f:
        rows = list(csv.reader(f))[1:]
    for row in rows:
        if len(row) >= 2 and row[1] not in ("", ".") and row[0][:7] > last_shared:
            r[row[0][:7]] = float(row[1]) / 100
    return r


RATES = rates()


def rate_on(day):
    key = day.strftime("%Y-%m")
    if key in RATES:
        return RATES[key]
    return RATES[max(m for m in RATES if m <= key)]


def interest(cash, prev, day):
    return cash * rate_on(prev if RATE_FROM_PREV else day) * (day - prev).days / 365


# ------------------------------------------------------------------ independent rules

def pick_contract(day, kind, spot, chain, floor=None):
    """Expiration + strike from the 15:45 chain. Returns a dict, or a reason string."""
    two_sided = sorted({e for e, k, s, b, a in chain if k == kind and b > 0 and a > 0})
    dtes = {e: (e - day).days for e in two_sided}
    near = [e for e in two_sided if 4 <= dtes[e] <= 13]
    fallback = False
    if near:
        exp = min(near, key=lambda e: (abs(dtes[e] - 7), -dtes[e]))
    else:
        far = [e for e in two_sided if 4 <= dtes[e] <= 45]
        if not far:
            return "no expiration"
        exp, fallback = min(far, key=lambda e: dtes[e]), True
    t = (dtes[exp] + 15 / 1440) / 365
    r = rate_on(day)
    best, in_band_below_floor = None, 0
    for e, k, strike, bid, ask in chain:
        if e != exp or k != kind or bid <= 0:
            continue
        if (kind == "P" and not strike < spot) or (kind == "C" and not strike > spot):
            continue
        mid = (bid + ask) / 2
        if kind == "P":
            iv = implied_vol(mid, spot, strike, t, r, q=0.0)
            delta = None if iv is None else bs_put(spot, strike, t, r, iv, q=0.0)[1]
        else:
            iv = call_iv(mid, spot, strike, t, r, q=0.0)
            delta = None if iv is None else bs_call(spot, strike, t, r, iv, q=0.0)[1]
        if delta is None:
            continue
        a = abs(delta)
        if not BAND[0] - EPS <= a <= BAND[1] + EPS:
            continue
        if kind == "C" and floor is not None and strike < floor - EPS:
            in_band_below_floor += 1
            continue
        key = (abs(a - TARGET), -abs(strike - spot))
        if best is None or key < best[0]:
            best = (key, {"expiration": exp, "strike": strike, "bid": bid, "ask": ask, "delta": delta, "iv": iv,
                          "fallback": fallback})
    if best:
        return best[1]
    return "no call at/above the floor in band" if in_band_below_floor else "no strike in band"


def find_buyback(quotes, sale_day, sale_bid, day):
    """First minute on `day` after the 15:45 sale minute with 0 < ask <= 50% of the sale bid."""
    trig = TAKE * sale_bid
    sale_min = datetime.combine(sale_day, DECIDE, NY)
    for ts, b, a in quotes.get(day, ()):
        if ts > sale_min and a > 0 and a <= trig + EPS:
            return ts, a
    return None


def last_mid(quotes, day):
    days = [d for d in quotes if d <= day and quotes[d]]
    if not days:
        return None
    ts, b, a = quotes[max(days)][-1]
    return (b + a) / 2


def life_end(exp, trading_days):
    """Last trading day of the option's life: expiration (or the trading day before it), or the test's end."""
    return LAST if exp > LAST else max(d for d in trading_days if d <= exp)


# ------------------------------------------------------------------ full account replay

def simulate_account(ticker, closes, trading_days, divs, stop_at_frontier=True):
    cash, shares, basis, opt = ACCOUNT, 0.0, None, None
    next_sale, prev, value, frontier = FIRST, None, None, None
    recs, totals, counts = [], defaultdict(float), defaultdict(int)
    stuck_days = []

    def close_option(d, price, result, ts=None):
        nonlocal cash, opt
        n = opt["contracts"]
        cost = 0.0
        if price is not None:
            cost = n * (price * 100 + FEE)
            cash -= cost
            totals["buybacks"] += n * price * 100
            totals["fees"] += n * FEE
        opt["rec"].update(result=result, close_day=d.isoformat(), close_time=ts.isoformat() if ts else None,
                          close_price=price, pnl=opt["premium_net"] - cost)
        counts[result] += 1
        opt = None

    for d in trading_days:
        if prev is not None:
            i = interest(cash, prev, d)
            cash += i
            totals["interest"] += i
        prev = d
        if d in divs.get(ticker, {}) and shares > EPS:
            cash += shares * divs[ticker][d]
            totals["dividends"] += shares * divs[ticker][d]
        if opt is not None:
            hit = find_buyback(opt["quotes"], opt["sale_day"], opt["sale_price"], d)
            if hit:
                close_option(d, hit[1], "closed_50", hit[0])
                next_sale = d if hit[0].time() < DECIDE else d + timedelta(days=1)
        if opt is None and d >= next_sale and d < LAST:
            spot = spot1545(d, ticker)
            if spot == "missing":
                frontier = (d.isoformat(), "spot1545 file missing")
                break
            if spot is not None:
                kind = "C" if shares > EPS else "P"
                chain = chain_file(ticker, d)
                if chain is None:
                    frontier = (d.isoformat(), "chain file missing")
                    break
                pick = pick_contract(d, kind, spot, chain, floor=basis if kind == "C" else None)
                if isinstance(pick, str):
                    counts["skip: " + pick] += 1
                    if pick.startswith("no call at/above"):
                        stuck_days.append(d)
                else:
                    exp, k = pick["expiration"], pick["strike"]
                    files = quote_files(ticker, d, exp, kind, k)
                    if not files:
                        others = sorted(p.name for p in (DATA / "quotes" / ticker).glob(f"{d.isoformat()}_*"))
                        frontier = (d.isoformat(), f"quote file missing for my pick {osi_compact(ticker, exp, kind, k)}",
                                    {"other_cached_files_that_day": others})
                        break
                    n = cash / (k * 100) if kind == "P" else shares / 100
                    last_day = life_end(exp, trading_days)
                    premium = n * pick["bid"] * 100
                    cash += premium - n * FEE
                    totals["premiums"] += premium
                    totals["fees"] += n * FEE
                    counts["fallback"] += pick["fallback"]
                    rec = {"ticker": ticker, "sale_day": d.isoformat(), "kind": kind, "expiration": exp.isoformat(),
                           "strike": k, "spot": spot, "delta": round(pick["delta"], 4), "sale_price": pick["bid"],
                           "contracts": n, "fallback": pick["fallback"], "floor": basis if kind == "C" else None,
                           "last_day": last_day.isoformat(), "cache_file": files[0].name}
                    recs.append(rec)
                    opt = {"kind": kind, "expiration": exp, "strike": k, "contracts": n, "sale_price": pick["bid"],
                           "sale_day": d, "last_day": last_day, "quotes": read_quotes(files[0]),
                           "premium_net": premium - n * FEE, "rec": rec}
                    hit = find_buyback(opt["quotes"], d, pick["bid"], d)
                    if hit:
                        close_option(d, hit[1], "closed_50", hit[0])
                        next_sale = d + timedelta(days=1)
        if opt is not None and d == opt["last_day"] and opt["expiration"] <= LAST:
            close = closes[ticker][d]
            k, n = opt["strike"], opt["contracts"]
            if opt["kind"] == "P" and close < k:
                cash -= n * 100 * k
                shares += n * 100
                basis = k
                totals["share_buys"] += n * 100 * k
                res = "assigned"
            elif opt["kind"] == "C" and close > k:
                cash += n * 100 * k
                totals["share_sales"] += n * 100 * k
                totals["called_away_shares_pnl"] += shares * (k - basis)
                shares, basis = 0.0, None
                res = "called_away"
            else:
                res = "expired_worthless"
            opt["rec"]["expiry_close"] = close
            close_option(d, None, res)
            next_sale = d + timedelta(days=1)
        opt_val = 0.0
        if opt is not None:
            m = last_mid(opt["quotes"], d)
            opt_val = opt["contracts"] * 100 * (m if m is not None else 0.0)
        value = cash + shares * closes[ticker][d] - opt_val
    if opt is not None and frontier is None:
        opt["rec"].update(result="open_at_end", close_price=last_mid(opt["quotes"], LAST),
                          pnl=opt["premium_net"] - opt["contracts"] * 100 * (last_mid(opt["quotes"], LAST) or 0.0))
    return {"contracts": recs, "totals": dict(totals), "counts": dict(counts), "cash": cash, "shares": shares,
            "basis": basis, "final_value": value, "frontier": frontier,
            "stuck_days_no_call_allowed": len(stuck_days),
            "stuck_weeks_no_call_allowed": len({d.isocalendar()[:2] for d in stuck_days})}


# ------------------------------------------------------------------ standalone single-contract recompute

def recheck_contract(ticker, sale_day, kind, contracts, floor, trading_days, closes):
    spot = spot1545(sale_day, ticker)
    chain = chain_file(ticker, sale_day)
    if spot in (None, "missing") or chain is None:
        return {"error": f"raw file missing: spot={spot!r}, chain={'ok' if chain else 'missing'}"}
    pick = pick_contract(sale_day, kind, spot, chain, floor=floor if kind == "C" else None)
    if isinstance(pick, str):
        return {"error": pick}
    exp, k, bid = pick["expiration"], pick["strike"], pick["bid"]
    files = quote_files(ticker, sale_day, exp, kind, k)
    if not files:
        return {"error": f"quote file missing for {osi_compact(ticker, exp, kind, k)}", "expiration": exp.isoformat(),
                "strike": k}
    quotes = read_quotes(files[0])
    last_day = life_end(exp, trading_days)
    premium_net = contracts * (bid * 100 - FEE)
    out = {"spot": spot, "expiration": exp.isoformat(), "strike": k, "delta": round(pick["delta"], 4),
           "fallback": pick["fallback"], "sale_price": bid, "contracts": contracts, "floor": floor,
           "last_day": last_day.isoformat(), "cache_file": files[0].name}
    for d in [x for x in trading_days if sale_day <= x <= last_day]:
        hit = find_buyback(quotes, sale_day, bid, d)
        if hit:
            return {**out, "result": "closed_50", "close_time": hit[0].isoformat(), "close_price": hit[1],
                    "pnl": premium_net - contracts * (hit[1] * 100 + FEE)}
    if exp > LAST:
        m = last_mid(quotes, LAST)
        return {**out, "result": "open_at_end", "close_price": m, "pnl": premium_net - contracts * 100 * m}
    close = closes[ticker][last_day]
    if kind == "P" and close < k:
        res, marked = "assigned", premium_net - contracts * 100 * (k - close)
    elif kind == "C" and close > k:
        res, marked = "called_away", premium_net - contracts * 100 * (close - k)
    else:
        res, marked = "expired_worthless", premium_net
    return {**out, "result": res, "expiry_close": close, "pnl": premium_net, "pnl_marked_to_close": marked}


# ------------------------------------------------------------------ holding comparison

def hold_benchmark(closes, trading_days, divs):
    out, total = {}, 0.0
    for t in TICKERS:
        spot = spot1545(FIRST, t)
        shares, cash, prev, div_total, int_total = ACCOUNT / spot, 0.0, FIRST, 0.0, 0.0
        for d in trading_days:
            if d == FIRST:
                continue
            i = interest(cash, prev, d)
            cash += i
            int_total += i
            prev = d
            if d in divs.get(t, {}):
                cash += shares * divs[t][d]
                div_total += shares * divs[t][d]
        value = shares * closes[t][LAST] + cash
        out[t] = {"buy_price": spot, "shares": shares, "close_last": closes[t][LAST], "dividends": div_total,
                  "interest": int_total, "final_value": value}
        total += value
    out["combined_final_value"] = total
    return out


# ------------------------------------------------------------------ reading the main run's JSON (field-name tolerant)

ALIASES = {
    "ticker": ("ticker", "symbol", "stock", "account", "sleeve"),
    "sale_day": ("sale_day", "entry_day", "sold_day", "sale_date", "open_day", "day", "date"),
    "expiration": ("expiration", "expiry", "exp"),
    "strike": ("strike",),
    "kind": ("kind", "type", "right", "option_type"),
    "sale_price": ("sale_price", "sale_bid", "bid", "sold_at", "entry_price"),
    "contracts": ("contracts", "qty", "quantity", "n_contracts"),
    "result": ("result", "outcome", "exit", "exit_reason", "how", "end"),
    "close_price": ("buyback_price", "close_price", "exit_price", "buyback_ask"),
    "close_time": ("buyback_time", "close_time", "exit_time", "buyback_minute"),
    "pnl": ("pnl", "option_pnl", "profit", "pl", "net_pnl"),
    "fallback": ("fallback",),
    "floor": ("floor", "basis", "cost_basis", "assignment_strike", "basis_floor"),
}


def field(d, name):
    for k in ALIASES[name]:
        if k in d and d[k] is not None:
            return d[k]
    return None


def walk(obj, path=()):
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + (str(i),))


def json_main_contracts(res):
    out, where = defaultdict(list), defaultdict(set)
    main_trades = ((res.get("versions") or {}).get("main") or {}).get("trades") if isinstance(res, dict) else None
    if isinstance(main_trades, list) and main_trades:
        # the run's layout: versions/main/trades only (recent_view_fresh_start is a separate fresh start, info only)
        for c in main_trades:
            if field(c, "ticker") in TICKERS:
                out[field(c, "ticker")].append(c)
                where[field(c, "ticker")].add("versions/main/trades")
        for t in out:
            out[t].sort(key=lambda c: str(field(c, "sale_day")))
        return out, {t: sorted(v) for t, v in where.items()}
    for path, obj in walk(res):
        if not (isinstance(obj, list) and obj and isinstance(obj[0], dict)):
            continue
        if field(obj[0], "strike") is None or field(obj[0], "expiration") is None:
            continue
        if any(any(v in p for v in INFO_VERSIONS + ("recent_view",)) for p in path):
            continue
        tick = next((p for p in path if p in TICKERS), None)
        for c in obj:
            t = field(c, "ticker") if field(c, "ticker") in TICKERS else tick
            if t:
                out[t].append(c)
                where[t].add("/".join(path))
    for t in out:
        out[t].sort(key=lambda c: str(field(c, "sale_day")))
    return out, {t: sorted(v) for t, v in where.items()}


def json_numbers(res, names):
    return {"/".join(p): o for p, o in walk(res)
            if isinstance(o, (int, float)) and not isinstance(o, bool) and p and p[-1] in names}


def norm_result(x):
    s = str(x or "").lower()
    if "assign" in s:
        return "assigned"
    if "call" in s and "away" in s or s == "called":
        return "called_away"
    if "worthless" in s or s == "expired":
        return "expired_worthless"
    if "50" in s or "take" in s or "buyback" in s or "bought" in s or "close" in s and "end" not in s:
        return "closed_50"
    if "open" in s or "end" in s or "mark" in s:
        return "open_at_end"
    return s


def near(a, b, tol):
    try:
        return a is not None and b is not None and abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def compare_contract(main, mine):
    """Field checks between a JSON contract and my record (replay or standalone)."""
    n = float(field(main, "contracts") or mine.get("contracts") or 0)
    checks = {
        "expiration": str(field(main, "expiration"))[:10] == mine["expiration"],
        "strike": near(field(main, "strike"), mine["strike"], 1e-6),
        "kind": str(field(main, "kind") or "")[:1].upper() == mine["kind"] if field(main, "kind") else None,
        "sale_price": near(field(main, "sale_price"), mine["sale_price"], PRICE_TOL)
        if field(main, "sale_price") is not None else None,
        "contracts": near(field(main, "contracts"), mine["contracts"], 1e-6 * max(1.0, mine["contracts"]))
        if field(main, "contracts") is not None and "contracts" in mine else None,
        "result": norm_result(field(main, "result")) == mine.get("result") if field(main, "result") else None,
    }
    if mine.get("result") == "closed_50" and field(main, "close_price") is not None:
        checks["buyback_price"] = near(field(main, "close_price"), mine["close_price"], PRICE_TOL)
    if field(main, "pnl") is not None and mine.get("pnl") is not None:
        tol = 0.05 * max(n, 1e-9) + 0.01
        alts = [mine["pnl"]] + ([mine["pnl_marked_to_close"]] if "pnl_marked_to_close" in mine else [])
        checks["pnl"] = any(near(field(main, "pnl"), a, tol) for a in alts)
    return {k: v for k, v in checks.items() if v is not None}


# ------------------------------------------------------------------ main

def main():
    closes = {t: daily(t) for t in TICKERS}
    days = [d for d in sorted(set.intersection(*(set(c) for c in closes.values()))) if FIRST <= d <= LAST]
    splits, divs = corporate_actions()
    mismatches = []
    if splits:
        mismatches.append(f"unexpected splits in corporate actions: {splits}")
    res = json.loads(RESULTS.read_text()) if RESULTS.exists() else None
    summary = {"results_json": str(RESULTS.relative_to(ROOT)) if res else "MISSING (main run not finished)"}

    # 1. full replay; before the JSON exists every replayed pick must already be a cached file (the run's own pick)
    replays, rep = {}, {}
    for t in TICKERS:
        r = simulate_account(t, closes, days, divs)
        replays[t] = r
        cached = sorted(p.name for p in (DATA / "quotes" / t).glob("*.csv.gz"))
        mine = {c["cache_file"] for c in r["contracts"]}
        frontier_day = r["frontier"][0] if r["frontier"] else "9999-12-31"
        # cached files sold before my frontier that my replay did not pick (info versions share this cache, so this
        # is a mismatch only when no information version could explain it: reported, judged with the JSON below)
        extra = [f for f in cached if f[:10] < frontier_day and f not in mine]
        pick_disagree = bool(r["frontier"] and len(r["frontier"]) > 2 and r["frontier"][2]["other_cached_files_that_day"])
        rep[t] = {"my_contracts": len(r["contracts"]), "frontier": r["frontier"],
                  "cached_quote_files": len(cached), "cached_before_frontier_not_in_my_replay": extra[:20],
                  "frontier_day_has_other_cached_pick": pick_disagree,
                  "counts": r["counts"], "stuck_weeks_no_call_allowed": r["stuck_weeks_no_call_allowed"],
                  "final_value": None if r["frontier"] else round(r["final_value"], 2),
                  "end_state": {"cash": round(r["cash"], 2), "shares": round(r["shares"], 4), "basis": r["basis"]},
                  "totals": {k: round(v, 2) for k, v in r["totals"].items()}}
        if pick_disagree:
            mismatches.append(f"replay {t}: my pick on {frontier_day} is not cached but another contract that day is")
        if res is None and extra:
            # no info versions should have run yet if main is still in progress; flag but keep going
            rep[t]["note"] = "cached files not in my replay exist (could be information versions, or a disagreement)"
    summary["replay"] = rep

    # 4a. full contract-by-contract comparison against the JSON
    jc, jwhere = json_main_contracts(res) if res else ({}, {})
    if res:
        summary["json_contract_lists"] = jwhere
        comp = {}
        for t in TICKERS:
            mine_list, main_list = replays[t]["contracts"], jc.get(t, [])
            bad = []
            for i in range(max(len(mine_list), len(main_list))):
                a = main_list[i] if i < len(main_list) else None
                b = mine_list[i] if i < len(mine_list) else None
                if a is None or b is None:
                    bad.append({"i": i, "main": a, "mine": b})
                    continue
                ch = {"sale_day": str(field(a, "sale_day"))[:10] == b["sale_day"], **compare_contract(a, b)}
                if not all(ch.values()):
                    bad.append({"i": i, "failed": [k for k, v in ch.items() if not v],
                                "main": {k: field(a, k) for k in ALIASES},
                                "mine": {k: b.get(k) for k in ("sale_day", "kind", "expiration", "strike", "sale_price",
                                                               "contracts", "result", "close_price", "pnl", "floor")}})
            size_only, substantive = [], []
            for x in bad:
                f = set(x.get("failed", ["missing"]))
                if f <= {"contracts", "pnl"} and x.get("mine") and x["mine"].get("contracts"):
                    rel = abs(float(x["main"]["contracts"]) / x["mine"]["contracts"] - 1)
                    pnl_ok = "pnl" not in f or near(float(x["main"]["pnl"]) * x["mine"]["contracts"]
                                                    / float(x["main"]["contracts"]), x["mine"]["pnl"], 0.05)
                    if rel < 0.01 and pnl_ok:
                        x["contracts_rel_diff"] = rel
                        size_only.append(x)
                        continue
                substantive.append(x)
            comp[t] = {"main_contracts": len(main_list), "my_contracts": len(mine_list),
                       "size_only_mismatches (contracts/P&L off by <1%, same pick and outcome)": len(size_only),
                       "max_contracts_rel_diff": max((x["contracts_rel_diff"] for x in size_only), default=0.0),
                       "substantive_mismatches": len(substantive), "first_substantive": substantive[:5]}
            if substantive or not main_list:
                mismatches.append(f"contract list {t}: {len(substantive)} substantive")
            if size_only:
                mismatches.append(f"contract sizes {t}: {len(size_only)} off by <1% (cash convention)")
        summary["contract_by_contract"] = comp

    # 2. 12 random main contracts, 6 per stock, recomputed standalone
    rng = random.Random(3232)
    sample = []
    for t in TICKERS:
        if jc.get(t):
            pool = [("json", c) for c in jc[t] if norm_result(field(c, "result")) != "open_at_end" or True]
        else:
            fd = replays[t]["frontier"][0] if replays[t]["frontier"] else "9999-12-31"
            pool = [("cache", c) for c in replays[t]["contracts"] if c["sale_day"] < fd and c.get("result")]
        floors, last_assigned = [], None
        seq = [c for _, c in pool]
        for c in seq:  # the call floor = the strike of the latest assigned put before it, from the same list
            src_kind = (str(field(c, "kind"))[:1].upper() if pool[0][0] == "json" else c["kind"])
            floors.append(last_assigned if src_kind == "C" else None)
            r = norm_result(field(c, "result")) if pool[0][0] == "json" else c.get("result")
            if src_kind == "P" and r == "assigned":
                last_assigned = float(field(c, "strike") if pool[0][0] == "json" else c["strike"])
        idx = sorted(rng.sample(range(len(pool)), min(6, len(pool))))
        for i in idx:
            src, c = pool[i]
            if src == "json":
                sale_day = date.fromisoformat(str(field(c, "sale_day"))[:10])
                kind, n = str(field(c, "kind"))[:1].upper(), float(field(c, "contracts"))
                main_vals = {k: field(c, k) for k in ALIASES}
            else:
                sale_day, kind, n = date.fromisoformat(c["sale_day"]), c["kind"], c["contracts"]
                sym = c["cache_file"].split("_")[1]
                main_vals = {"source": "the run's cached quote-file name", "expiration":
                             f"20{sym[-15:-13]}-{sym[-13:-11]}-{sym[-11:-9]}", "strike": int(sym[-8:]) / 1000,
                             "kind": sym[-9], "last_day": c["cache_file"].rsplit("_", 1)[1][:10]}
            mine = recheck_contract(t, sale_day, kind, n, floors[i], days, closes)
            if "error" in mine:
                checks = {"recomputed": False}
            elif src == "json":
                checks = compare_contract(c, {**mine, "kind": kind})
            else:
                checks = {"expiration": main_vals["expiration"] == mine["expiration"],
                          "strike": near(main_vals["strike"], mine["strike"], 1e-6),
                          "last_day": main_vals["last_day"] == mine["last_day"],
                          "replay_agrees_result": c.get("result") == mine["result"],
                          "replay_agrees_pnl": near(c.get("pnl"), mine["pnl"], 1e-6 + 1e-9 * abs(mine["pnl"]))}
            ok = all(checks.values())
            if not ok:
                mismatches.append(f"sample contract {t} {sale_day}")
            sample.append({"ticker": t, "sale_day": sale_day.isoformat(), "kind": kind, "source": src,
                           "floor_used": floors[i], "main": {k: v for k, v in main_vals.items() if v is not None},
                           "mine": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in mine.items()},
                           "checks": checks, "ok": ok})
    summary["sample_contracts"] = sample

    # 3. account final values and holding
    hold = hold_benchmark(closes, days, divs)
    summary["holding_mine"] = {t: {k: round(v, 4) for k, v in hold[t].items()} for t in TICKERS}
    summary["holding_mine"]["combined_final_value"] = round(hold["combined_final_value"], 2)
    if res:
        fv = json_numbers(res, ("final_value", "final_equity", "end_value", "value_end", "ending_value"))
        acc = {}
        for t in TICKERS:
            keys = [k for k in fv if t in k.split("/") and not any(v in k for v in INFO_VERSIONS)
                    and not any(x in k.lower() for x in ("hold", "bench", "buy_and"))]
            rv = replays[t]["final_value"] if not replays[t]["frontier"] else None
            acc[t] = {"json": {k: fv[k] for k in keys}, "replay": None if rv is None else round(rv, 2)}
            if rv is None or not keys or not any(near(fv[k], rv, 1.0) for k in keys):
                mismatches.append(f"account final value {t}")
        summary["account_final_values"] = acc
        hk = {k: v for k, v in fv.items() if any(x in k.lower() for x in ("hold", "bench", "buy_and"))}
        hold_check = {}
        for t in TICKERS:
            ks = [k for k in hk if t in k.split("/")]
            hold_check[t] = {"json": {k: hk[k] for k in ks}, "mine": round(hold[t]["final_value"], 2),
                             "ok": any(near(hk[k], hold[t]["final_value"], 1.0) for k in ks)}
            if not hold_check[t]["ok"]:
                mismatches.append(f"holding {t}")
        summary["holding_check"] = hold_check
    summary["mismatches"] = mismatches
    summary["verdict"] = ("ALL MATCH" if not mismatches else "MISMATCH") if res else (
        "PARTIAL (no results JSON yet): " + ("cache agrees so far" if not mismatches else "MISMATCH"))
    print(json.dumps(summary, indent=1, default=str))
    sys.exit(1 if mismatches or not res else 0)


if __name__ == "__main__":
    main()
