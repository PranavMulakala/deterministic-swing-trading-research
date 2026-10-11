"""Independent verifier for pre-declared test #33, the $50k weekly wheel on the ten stocks screened as of Dec 31, 2025
(plan: output/WHEEL_YTD_SCREEN_TEST_PLAN_20261011.md, including "Correction before any result"; inherited rules: test
#32's plan and test #29's conventions). Adapted from test #32's independent verifier (research/wheel_lite_mu_v1/
verify.py, which matched that run to the cent), WITHOUT reading research/wheel_ytd_v1/backtest.py or
research/wheel_lite_mu_v1/backtest.py. research/wheel_ytd_v1/data.py was read for cache formats only.

Judgment calls (test #32 verifier's, plus #33's settings):
- Ten separate $50,000 accounts, Jan 2 - Oct 9, 2026. Trading days = the 15:45 snapshot files (194).
- 15:45 decision on any trading day with no open option and a 15:45 SIP price (no price -> no sale; PRAX on Jan 2);
  no new sale on an account's last day (Oct 9; RNA: Feb 25).
- Expiration / strike / delta / size / sale price / 50% buyback (through 16:00) / expiry on the official close /
  dividends / interest exactly as test #32's verifier. Interest uses the previous trading day's month rate by default
  (test #32's engine convention, found and confirmed there); --rate-day switches to the day's own month.
- Skip earnings: the normal pick is made; if its life (sale day through expiration, calendar dates inclusive) contains
  an earnings session, nothing is sold that day. Earnings sessions are taken from the results JSON
  (earnings_sessions), NOT re-derived (checked separately).
- CVNA 5-for-1 split, ex May 8, 2026 (test #29 convention): an option still open on the ex-date (expiration on/after
  it) is bought back at its last mid on the trading day before (plus the $0.03 fee; not exercised by the main run),
  shares x5, the call floor (assignment strike) /5; the account sells again on the ex-date under the normal rules.
  No sale on the split eve (the trading day before the ex-date): the engine's convention (test #29 engine, Sleeve.run
  `d not in self.split_eve`), adopted after the first run, which sold on CVNA's eve (May 7) and stopped there because
  the run had no chain cached that day (any >= 4-day contract sold then would be closed at mid the same day).
- RNA (Avidity): wheels through Feb 25 (an option still open is settled at its last mid that day, no fee); Feb 26 is
  valued at the Feb 25 close; on Feb 27 shares convert to $72 + 0.1 x the Atrium close (daily_RNA on Feb 27); cash
  earns T-bills to the end. Holding RNA gets the same treatment.
- Holding: $50,000 at the Jan 2 15:45 price (PRAX: the cached spot1545_fallback price, the run's documented
  fallback), dividends to cash earning T-bills, split x5, valued at the Oct 9 close.

Checks: (1) full main-version replay per account vs versions/main/trades field by field; (2) 12 random main contracts
(random.Random(3333), pooled across the ten accounts) recomputed standalone; (3) each account's final value within $1
of versions/main/per_account/<T>/ending_value; (4) holding per stock within $1 of holding/per_account/<T>/ending_value.
Only cached files are read; nothing is fetched or bought. Prints a JSON summary; exits non-zero on any mismatch.

  PYTHONPATH=src:. .venv/bin/python -m research.wheel_ytd_v1.verify [--rate-day]
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
DATA = ROOT / "outputs/wheel_ytd_data"
RESULTS = ROOT / "output/wheel-ytd-test-results.json"
TICKERS = ("PRAX", "LITE", "RKLB", "RIVN", "HL", "RNA", "AG", "COHR", "STX", "CVNA")
FIRST, LAST = date(2026, 1, 2), date(2026, 10, 9)
ACCOUNT = 50_000.0
FEE = 0.03
TARGET, BAND = 0.30, (0.25, 0.35)
TAKE = 0.50
DECIDE = dtime(15, 45)
LAST_MINUTE = dtime(16, 0)
RATE_FROM_PREV = "--rate-day" not in sys.argv
PRICE_TOL = 0.005
EPS = 1e-9
SEED, N_SAMPLE = 3333, 12
# RNA = Avidity Biosciences (plan correction): last option session, conversion day, terms
DELIST = {"RNA": {"last_session": date(2026, 2, 25), "effective": date(2026, 2, 27), "cash": 72.0, "spin": 0.1}}


# ------------------------------------------------------------------ raw files (own readers)

def trading_days():
    return sorted(d for d in (date.fromisoformat(p.name[:10]) for p in (DATA / "spot1545").glob("*.json"))
                  if FIRST <= d <= LAST)


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
    """{date: [(NY datetime, bid, ask)]} sorted by time, minutes through 16:00."""
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
    splits = defaultdict(dict)
    for s in ca["forward_splits"]:
        d = date.fromisoformat(s["ex_date"])
        if s["symbol"] in TICKERS and FIRST <= d <= LAST:
            splits[s["symbol"]][d] = float(s["new_rate"]) / float(s["old_rate"])
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


def account_last(ticker):
    return DELIST[ticker]["last_session"] if ticker in DELIST else LAST


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


def earnings_in_life(sessions, sale_day, exp):
    return [s for s in sessions if sale_day <= s <= exp]


def find_buyback(quotes, sale_day, sale_bid, day):
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


def split_close_day(exp, sale_day, ticker, splits, days):
    """The trading day before a split ex-date that falls inside the option's life (sale < ex <= expiration)."""
    for ex in sorted(splits.get(ticker, {})):
        if sale_day < ex <= exp:
            return max(d for d in days if d < ex), ex
    return None, None


def life_end(ticker, exp, days):
    """Last trading day of the option's life: expiration (or the trading day before), capped at the account's end."""
    end = account_last(ticker)
    return end if exp > end else max(d for d in days if d <= exp)


# ------------------------------------------------------------------ full account replay

def simulate_account(ticker, closes, days, divs, splits, sessions):
    cash, shares, basis, opt = ACCOUNT, 0.0, None, None
    next_sale, prev, value, frontier = FIRST, None, None, None
    acct_last = account_last(ticker)
    dl = DELIST.get(ticker)
    recs, totals, counts = [], defaultdict(float), defaultdict(int)
    stuck_days, last_close = [], None
    split_eves = {max(x for x in days if x < ex) for ex in splits.get(ticker, {})}

    def close_option(d, price, result, ts=None, fee=True):
        nonlocal cash, opt
        n = opt["contracts"]
        cost = 0.0
        if price is not None:
            cost = n * (price * 100 + (FEE if fee else 0.0))
            cash -= cost
            totals["buybacks_incl_fees"] += cost
        opt["rec"].update(result=result, close_day=d.isoformat(), close_time=ts.isoformat() if ts else None,
                          close_price=price, pnl=opt["premium_net"] - cost)
        counts[result] += 1
        opt = None

    for d in days:
        if prev is not None:
            i = interest(cash, prev, d)
            cash += i
            totals["interest"] += i
        prev = d
        if d in divs.get(ticker, {}) and shares > EPS and d <= acct_last:
            cash += shares * divs[ticker][d]
            totals["dividends"] += shares * divs[ticker][d]
        if d in splits.get(ticker, {}):
            ratio = splits[ticker][d]
            shares *= ratio
            basis = basis / ratio if basis is not None else None
            counts["split_applied"] += 1
        if dl and d > acct_last:
            if d == dl["effective"] and shares > EPS:
                cash += shares * (dl["cash"] + dl["spin"] * closes[ticker][d])
                totals["conversion_value"] += shares * (dl["cash"] + dl["spin"] * closes[ticker][d])
                shares, basis = 0.0, None
            value = cash + shares * (last_close if d < dl["effective"] else 0.0)
            continue
        if opt is not None:
            hit = find_buyback(opt["quotes"], opt["sale_day"], opt["sale_price"], d)
            if hit:
                close_option(d, hit[1], "closed_50", hit[0])
                next_sale = d if hit[0].time() < DECIDE else d + timedelta(days=1)
        if opt is None and d >= next_sale and d < acct_last and d in split_eves:
            counts["skip: split eve (no sale)"] += 1
        elif opt is None and d >= next_sale and d < acct_last:
            spot = spot1545(d, ticker)
            if spot == "missing":
                frontier = (d.isoformat(), "spot1545 file missing")
                break
            if spot is None:
                counts["skip: no 15:45 price"] += 1
            else:
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
                elif earnings_in_life(sessions, d, pick["expiration"]):
                    counts["skip: contract life includes earnings"] += 1
                else:
                    exp, k = pick["expiration"], pick["strike"]
                    files = quote_files(ticker, d, exp, kind, k)
                    if not files:
                        others = sorted(p.name for p in (DATA / "quotes" / ticker).glob(f"{d.isoformat()}_*"))
                        frontier = (d.isoformat(), f"quote file missing for my pick {osi_compact(ticker, exp, kind, k)}",
                                    {"other_cached_files_that_day": others})
                        break
                    n = cash / (k * 100) if kind == "P" else shares / 100
                    last_day = life_end(ticker, exp, days)
                    sc_day, sc_ex = split_close_day(exp, d, ticker, splits, days)
                    premium = n * pick["bid"] * 100
                    cash += premium - n * FEE
                    totals["premiums"] += premium
                    totals["sale_fees"] += n * FEE
                    counts["fallback"] += pick["fallback"]
                    counts["opened"] += 1
                    rec = {"ticker": ticker, "sale_day": d.isoformat(), "kind": kind, "expiration": exp.isoformat(),
                           "strike": k, "spot": spot, "delta": round(pick["delta"], 4), "sale_price": pick["bid"],
                           "contracts": n, "fallback": pick["fallback"], "floor": basis if kind == "C" else None,
                           "last_day": last_day.isoformat(), "cache_file": files[0].name}
                    recs.append(rec)
                    opt = {"kind": kind, "expiration": exp, "strike": k, "contracts": n, "sale_price": pick["bid"],
                           "sale_day": d, "last_day": last_day, "quotes": read_quotes(files[0]),
                           "premium_net": premium - n * FEE, "rec": rec, "split_close_day": sc_day}
                    hit = find_buyback(opt["quotes"], d, pick["bid"], d)
                    if hit:
                        close_option(d, hit[1], "closed_50", hit[0])
                        next_sale = d + timedelta(days=1)
        if opt is not None and opt["split_close_day"] == d:
            close_option(d, last_mid(opt["quotes"], d), "closed_before_split_at_mid")
            next_sale = d + timedelta(days=1)
        if opt is not None and d == opt["last_day"] and opt["expiration"] <= acct_last:
            close = closes[ticker][d]
            k, n = opt["strike"], opt["contracts"]
            if opt["kind"] == "P" and close < k:
                cash -= n * 100 * k
                shares += n * 100
                basis = k
                res = "assigned"
            elif opt["kind"] == "C" and close > k:
                cash += n * 100 * k
                totals["called_away_shares_pnl"] += shares * (k - basis)
                shares, basis = 0.0, None
                res = "called_away"
            else:
                res = "expired_worthless"
            opt["rec"]["expiry_close"] = close
            close_option(d, None, res)
            next_sale = d + timedelta(days=1)
        if opt is not None and dl and d == acct_last:
            # RNA: an option still open on the last option session is settled at its last mid (no fee)
            close_option(d, last_mid(opt["quotes"], d) or 0.0, "settled_at_last_mid_delisting", fee=False)
        opt_val = 0.0
        if opt is not None:
            m = last_mid(opt["quotes"], d)
            opt_val = opt["contracts"] * 100 * (m if m is not None else 0.0)
        last_close = closes[ticker][d]
        value = cash + shares * last_close - opt_val
    if opt is not None and frontier is None:
        m = last_mid(opt["quotes"], LAST)
        opt["rec"].update(result="open_at_end", close_price=m,
                          pnl=opt["premium_net"] - opt["contracts"] * 100 * (m or 0.0))
        counts["open_at_end"] += 1
    return {"contracts": recs, "totals": dict(totals), "counts": dict(counts), "cash": cash, "shares": shares,
            "basis": basis, "final_value": value, "frontier": frontier,
            "stuck_days_no_call_allowed": len(stuck_days),
            "stuck_weeks_no_call_allowed": len({d.isocalendar()[:2] for d in stuck_days})}


# ------------------------------------------------------------------ standalone single-contract recompute

def recheck_contract(ticker, sale_day, kind, contracts, floor, days, closes, splits, sessions):
    spot = spot1545(sale_day, ticker)
    chain = chain_file(ticker, sale_day)
    if spot in (None, "missing") or chain is None:
        return {"error": f"raw file missing: spot={spot!r}, chain={'ok' if chain else 'missing'}"}
    pick = pick_contract(sale_day, kind, spot, chain, floor=floor if kind == "C" else None)
    if isinstance(pick, str):
        return {"error": pick}
    exp, k, bid = pick["expiration"], pick["strike"], pick["bid"]
    blocked = earnings_in_life(sessions, sale_day, exp)
    files = quote_files(ticker, sale_day, exp, kind, k)
    if not files:
        return {"error": f"quote file missing for {osi_compact(ticker, exp, kind, k)}", "expiration": exp.isoformat(),
                "strike": k}
    quotes = read_quotes(files[0])
    last_day = life_end(ticker, exp, days)
    sc_day, _ = split_close_day(exp, sale_day, ticker, splits, days)
    premium_net = contracts * (bid * 100 - FEE)
    out = {"spot": spot, "expiration": exp.isoformat(), "strike": k, "delta": round(pick["delta"], 4),
           "fallback": pick["fallback"], "sale_price": bid, "contracts": contracts, "floor": floor,
           "earnings_in_life": [s.isoformat() for s in blocked], "last_day": last_day.isoformat(),
           "cache_file": files[0].name}
    end = sc_day if sc_day else last_day
    for d in [x for x in days if sale_day <= x <= end]:
        hit = find_buyback(quotes, sale_day, bid, d)
        if hit:
            return {**out, "result": "closed_50", "close_time": hit[0].isoformat(), "close_price": hit[1],
                    "pnl": premium_net - contracts * (hit[1] * 100 + FEE)}
    if sc_day:
        m = last_mid(quotes, sc_day)
        return {**out, "result": "closed_before_split_at_mid", "close_price": m,
                "pnl": premium_net - contracts * (m * 100 + FEE)}
    if exp > account_last(ticker):
        m = last_mid(quotes, last_day)
        res = "open_at_end" if ticker not in DELIST else "settled_at_last_mid_delisting"
        return {**out, "result": res, "close_price": m, "pnl": premium_net - contracts * 100 * m}
    close = closes[ticker][last_day]
    if kind == "P" and close < k:
        res, marked = "assigned", premium_net - contracts * 100 * (k - close)
    elif kind == "C" and close > k:
        res, marked = "called_away", premium_net - contracts * 100 * (close - k)
    else:
        res, marked = "expired_worthless", premium_net
    return {**out, "result": res, "expiry_close": close, "pnl": premium_net, "pnl_marked_to_close": marked}


# ------------------------------------------------------------------ holding comparison

def hold_benchmark(closes, days, divs, splits):
    out = {}
    for t in TICKERS:
        spot, src = spot1545(FIRST, t), "spot1545"
        if spot in (None, "missing"):
            fb = DATA / "spot1545_fallback" / f"{FIRST.isoformat()}_{t}.json"
            spot, src = json.loads(fb.read_text())["price"], "spot1545_fallback"
        shares, cash, prev, div_total, int_total = ACCOUNT / spot, 0.0, FIRST, 0.0, 0.0
        dl = DELIST.get(t)
        conv = None
        for d in days:
            if d == FIRST:
                continue
            i = interest(cash, prev, d)
            cash += i
            int_total += i
            prev = d
            if d in divs.get(t, {}) and (not dl or d <= dl["last_session"]):
                cash += shares * divs[t][d]
                div_total += shares * divs[t][d]
            if d in splits.get(t, {}):
                shares *= splits[t][d]
            if dl and d == dl["effective"]:
                conv = {"shares": shares, "value_per_share": dl["cash"] + dl["spin"] * closes[t][d],
                        "spin_close": closes[t][d]}
                cash += shares * conv["value_per_share"]
                shares = 0.0
        value = shares * closes[t][LAST] + cash
        out[t] = {"buy_price": spot, "buy_price_source": src, "shares_end": shares, "dividends": div_total,
                  "interest": int_total, "conversion": conv, "final_value": value}
    return out


# ------------------------------------------------------------------ comparison helpers

ALIASES = {
    "ticker": ("ticker",),
    "sale_day": ("sale_day",),
    "expiration": ("expiration",),
    "strike": ("strike",),
    "kind": ("kind",),
    "sale_price": ("sale_bid", "sale_price"),
    "contracts": ("contracts",),
    "result": ("how", "result"),
    "close_price": ("close_price",),
    "close_time": ("close_minute",),
    "pnl": ("option_pnl", "pnl"),
    "fallback": ("fallback_expiration",),
}


def field(d, name):
    for k in ALIASES[name]:
        if k in d and d[k] is not None:
            return d[k]
    return None


def norm_result(x):
    s = str(x or "").lower()
    if "split" in s:
        return "closed_before_split_at_mid"
    if "delist" in s or ("settle" in s and "mid" in s):
        return "settled_at_last_mid_delisting"
    if "assign" in s:
        return "assigned"
    if "call" in s and "away" in s:
        return "called_away"
    if "worthless" in s:
        return "expired_worthless"
    if "open" in s and "end" in s:
        return "open_at_end"
    if "50" in s or "early" in s:
        return "closed_50"
    return s


def near(a, b, tol):
    try:
        return a is not None and b is not None and abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def compare_contract(main, mine):
    n = float(field(main, "contracts") or mine.get("contracts") or 0)
    checks = {
        "kind": str(field(main, "kind"))[:1].upper() == mine["kind"],
        "expiration": str(field(main, "expiration"))[:10] == mine["expiration"],
        "strike": near(field(main, "strike"), mine["strike"], 1e-6),
        "sale_price": near(field(main, "sale_price"), mine["sale_price"], PRICE_TOL),
        "contracts": near(field(main, "contracts"), mine["contracts"], 1e-6 * max(1.0, mine["contracts"])),
        "result": norm_result(field(main, "result")) == mine.get("result"),
    }
    if mine.get("result") in ("closed_50", "closed_before_split_at_mid", "open_at_end",
                              "settled_at_last_mid_delisting"):
        checks["buyback_price"] = near(field(main, "close_price"), mine.get("close_price"), PRICE_TOL)
    if mine.get("result") == "closed_50" and field(main, "close_time") and mine.get("close_time"):
        checks["buyback_minute"] = (datetime.fromisoformat(str(field(main, "close_time")))
                                    == datetime.fromisoformat(mine["close_time"]))
    if field(main, "fallback") is not None and "fallback" in mine:
        checks["fallback"] = bool(field(main, "fallback")) == bool(mine["fallback"])
    tol = 0.005 * max(n, 1.0) + 0.01
    alts = [mine.get("pnl")] + ([mine["pnl_marked_to_close"]] if "pnl_marked_to_close" in mine else [])
    checks["pnl"] = any(near(field(main, "pnl"), a, tol) for a in alts if a is not None)
    return checks


# ------------------------------------------------------------------ main

def main():
    days = trading_days()
    closes = {t: daily(t) for t in TICKERS}
    splits, divs = corporate_actions()
    res = json.loads(RESULTS.read_text()) if RESULTS.exists() else None
    mismatches = []
    if res is None:
        print(json.dumps({"error": f"{RESULTS} missing"}))
        sys.exit(2)
    sessions = {t: [date.fromisoformat(s) for s in res["earnings_sessions"].get(t, [])] for t in TICKERS}
    missing_closes = {t: [d.isoformat() for d in days if d not in closes[t] and d <= account_last(t)] for t in TICKERS}
    missing_closes = {t: v for t, v in missing_closes.items() if v}
    summary = {"results_json": str(RESULTS.relative_to(ROOT)), "trading_days": len(days),
               "json_trading_days": res.get("trading_days"),
               "interest_convention": "previous trading day's month" if RATE_FROM_PREV else "day's own month",
               "splits_used": {t: {d.isoformat(): r for d, r in v.items()} for t, v in splits.items()},
               "earnings_sessions_used_from_json": {t: [s.isoformat() for s in v] for t, v in sessions.items()},
               "missing_daily_closes": missing_closes}
    if len(days) != res.get("trading_days"):
        mismatches.append(f"trading day count {len(days)} vs JSON {res.get('trading_days')}")
    if {t: list(v) for t, v in splits.items()} != {"CVNA": [date(2026, 5, 8)]}:
        mismatches.append(f"unexpected split set: {dict(splits)}")

    main_v = res["versions"]["main"]
    jc = defaultdict(list)
    for c in main_v["trades"]:
        jc[c["ticker"]].append(c)
    for t in jc:
        jc[t].sort(key=lambda c: c["sale_day"])

    # 1. full replay + contract-by-contract comparison
    replays, rep, comp = {}, {}, {}
    for t in TICKERS:
        r = simulate_account(t, closes, days, divs, splits, sessions[t])
        replays[t] = r
        rep[t] = {"my_contracts": len(r["contracts"]), "frontier": r["frontier"], "counts": r["counts"],
                  "stuck_weeks_no_call_allowed": r["stuck_weeks_no_call_allowed"],
                  "final_value": None if r["frontier"] else round(r["final_value"], 2),
                  "end_state": {"cash": round(r["cash"], 2), "shares": round(r["shares"], 4), "basis": r["basis"]},
                  "totals": {k: round(v, 2) for k, v in r["totals"].items()}}
        if r["frontier"]:
            mismatches.append(f"replay {t} stopped: {r['frontier'][:2]}")
        mine_list, main_list = r["contracts"], jc.get(t, [])
        bad = []
        for i in range(max(len(mine_list), len(main_list))):
            a = main_list[i] if i < len(main_list) else None
            b = mine_list[i] if i < len(mine_list) else None
            if a is None or b is None:
                bad.append({"i": i, "failed": ["missing"], "main": a and {k: field(a, k) for k in ALIASES},
                            "mine": b and {k: b.get(k) for k in ("sale_day", "kind", "expiration", "strike")}})
                continue
            ch = {"sale_day": a["sale_day"] == b["sale_day"], **compare_contract(a, b)}
            if not all(ch.values()):
                bad.append({"i": i, "failed": [k for k, v in ch.items() if not v],
                            "main": {k: field(a, k) for k in ALIASES},
                            "mine": {k: b.get(k) for k in ("sale_day", "kind", "expiration", "strike", "sale_price",
                                                           "contracts", "result", "close_time", "close_price", "pnl",
                                                           "floor")}})
        pa = main_v["per_account"][t]
        counts_cmp = {"contracts_opened": (pa.get("contracts_opened"), len(mine_list)),
                      "times_assigned": (pa.get("times_assigned"), r["counts"].get("assigned", 0)),
                      "times_called_away": (pa.get("times_called_away"), r["counts"].get("called_away", 0)),
                      "weeks_stuck_no_call_allowed": (
                          pa.get("stuck_holding_shares_no_call_allowed", {}).get("weeks_stuck_no_call_allowed"),
                          r["stuck_weeks_no_call_allowed"])}
        comp[t] = {"main_contracts": len(main_list), "my_contracts": len(mine_list), "mismatched_contracts": len(bad),
                   "first_mismatches": bad[:5],
                   "counts_json_vs_mine": {k: list(v) for k, v in counts_cmp.items()},
                   "counts_agree": all(a == b for a, b in counts_cmp.values())}
        if bad:
            mismatches.append(f"contract list {t}: {len(bad)} mismatched")
        if not comp[t]["counts_agree"]:
            mismatches.append(f"per-account counts {t}")
    summary["replay"] = rep
    summary["contract_by_contract"] = comp

    # 2. 12 random main contracts (pooled, account order then sale day), recomputed standalone
    pool, floors = [], []
    for t in TICKERS:
        last_assigned = None   # (strike, day)
        for c in jc.get(t, []):
            sd = date.fromisoformat(c["sale_day"])
            fl = None
            if c["kind"] == "C" and last_assigned:
                fl = last_assigned[0]
                for ex, ratio in splits.get(t, {}).items():
                    if last_assigned[1] < ex <= sd:
                        fl /= ratio
            pool.append(c)
            floors.append(fl)
            if c["kind"] == "P" and norm_result(c["how"]) == "assigned":
                last_assigned = (float(c["strike"]), date.fromisoformat(c["end_day"]))
    rng = random.Random(SEED)
    idx = sorted(rng.sample(range(len(pool)), min(N_SAMPLE, len(pool))))
    sample = []
    for i in idx:
        c, t = pool[i], pool[i]["ticker"]
        sale_day = date.fromisoformat(c["sale_day"])
        mine = recheck_contract(t, sale_day, c["kind"], float(c["contracts"]), floors[i], days, closes, splits,
                                sessions[t])
        if "error" in mine:
            checks = {"recomputed": False}
        else:
            checks = compare_contract(c, {**mine, "kind": c["kind"]})
            checks["no_earnings_in_life"] = not mine["earnings_in_life"]
        ok = all(checks.values())
        if not ok:
            mismatches.append(f"sample contract {t} {sale_day}")
        sample.append({"ticker": t, "sale_day": sale_day.isoformat(), "kind": c["kind"], "floor_used": floors[i],
                       "main": {k: field(c, k) for k in ALIASES if field(c, k) is not None},
                       "mine": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in mine.items()},
                       "checks": checks, "ok": ok})
    summary["sample_contracts"] = sample

    # 3. account final values
    acc = {}
    for t in TICKERS:
        j = main_v["per_account"][t]["ending_value"]
        rv = None if replays[t]["frontier"] else replays[t]["final_value"]
        acc[t] = {"json": j, "replay": None if rv is None else round(rv, 2),
                  "diff": None if rv is None else round(rv - j, 2), "ok": near(j, rv, 1.0)}
        if not acc[t]["ok"]:
            mismatches.append(f"account final value {t}")
    summary["account_final_values"] = acc

    # 4. holding per stock
    hold = hold_benchmark(closes, days, divs, splits)
    hc = {}
    for t in TICKERS:
        j = res["holding"]["per_account"][t]["ending_value"]
        hc[t] = {"json": j, "mine": round(hold[t]["final_value"], 2), "diff": round(hold[t]["final_value"] - j, 2),
                 "buy_price": hold[t]["buy_price"], "buy_price_source": hold[t]["buy_price_source"],
                 "ok": near(j, hold[t]["final_value"], 1.0)}
        if hold[t]["conversion"]:
            hc[t]["conversion"] = {k: round(v, 4) for k, v in hold[t]["conversion"].items()}
        if not hc[t]["ok"]:
            mismatches.append(f"holding {t}")
    summary["holding_check"] = hc

    summary["mismatches"] = mismatches
    summary["verdict"] = "ALL MATCH" if not mismatches else "MISMATCH"
    print(json.dumps(summary, indent=1, default=str))
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
