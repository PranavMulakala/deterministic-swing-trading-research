"""Independent verifier for pre-declared test #29, the Reddit wheel on AVGO/CRM/AMZN/META/CBOE
(plan: output/WHEEL_TEST_PLAN_20261010.md). Written without reading backtest.py / test_backtest.py.

1. 12 random main-version contracts (random.Random(2929), spread across the sleeves): recomputed from the raw cached
   files (15:45 chain snapshot, 15:45 stock price, the contract's minute quotes, daily closes): expiration and strike
   pick, sale price, 75% buyback minute and price, otherwise the expiration outcome, and the contract's P&L.
2. Each main sleeve: the trade list (premiums - buybacks - fees, share buys/sells at strike, dividends, interest)
   replayed day by day must add up to the reported final value within $1.
3. "Holding the same five stocks" rebuilt from Alpaca daily data in the cache.

Only cached files are read; nothing is fetched or bought. Exits non-zero on any mismatch.

  PYTHONPATH=src:. .venv/bin/python -m research.wheel_test_v1.verify
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime, time as dtime, timezone
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
DATA = ROOT / "outputs/wheel_test_data"
RESULTS = ROOT / "output/wheel-test-results.json"
TICKERS = ("AVGO", "CRM", "AMZN", "META", "CBOE")
FIRST, LAST = date(2020, 1, 2), date(2026, 10, 9)
SLEEVE = 40_000.0
FEE = 0.03
TARGET, BAND = 0.35, (0.25, 0.45)
PRICE_TOL = 0.005


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
    out = []
    with gzip.open(p, "rt") as f:
        for r in csv.DictReader(f):
            out.append((date.fromisoformat(r["expiration"]), r["type"], float(r["strike"]), float(r["bid"]),
                        float(r["ask"])))
    return out


def osi_compact(ticker, exp, kind, strike):
    return f"{ticker}{exp:%y%m%d}{kind}{round(strike * 1000):08d}"


def quote_file(ticker, sale_day, exp, kind, strike):
    hits = sorted((DATA / "quotes" / ticker).glob(f"{sale_day.isoformat()}_{osi_compact(ticker, exp, kind, strike)}_*.csv.gz"))
    return hits


def read_quotes(path):
    rows = []
    with gzip.open(path, "rt") as f:
        for r in csv.DictReader(f):
            if not r["ts"]:
                continue
            ts = datetime.strptime(r["ts"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(NY)
            rows.append((ts, float(r["bid"]), float(r["ask"])))
    rows.sort(key=lambda x: x[0])
    return rows


def corporate_actions():
    ca = json.loads((DATA / "corporate_actions.json").read_text())
    splits, divs = defaultdict(dict), defaultdict(lambda: defaultdict(float))
    for s in ca["forward_splits"]:
        splits[s["symbol"]][date.fromisoformat(s["ex_date"])] = s["new_rate"] / s["old_rate"]
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


# ------------------------------------------------------------------ independent rules

def pick_contract(ticker, day, kind, spot, chain):
    """Expiration + strike from the 15:45 chain. Returns dict or a reason string."""
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
    best = None
    for e, k, strike, bid, ask in chain:
        if e != exp or k != kind or bid <= 0:
            continue
        if (kind == "P" and not strike < spot) or (kind == "C" and not strike > spot):
            continue
        mid = (bid + ask) / 2
        if kind == "P":
            iv = implied_vol(mid, spot, strike, t, r, q=0.0)
            if iv is None:
                continue
            delta = bs_put(spot, strike, t, r, iv, q=0.0)[1]
        else:
            iv = call_iv(mid, spot, strike, t, r, q=0.0)
            if iv is None:
                continue
            delta = bs_call(spot, strike, t, r, iv, q=0.0)[1]
        a = abs(delta)
        if not BAND[0] <= a <= BAND[1]:
            continue
        key = (abs(a - TARGET), -abs(strike - spot))
        if best is None or key < best[0]:
            best = (key, {"expiration": exp, "strike": strike, "bid": bid, "ask": ask, "delta": delta, "iv": iv,
                          "fallback": fallback})
    return best[1] if best else "no strike in band"


def last_day_for(ticker, sale_day, exp, trading_days, splits):
    """Expiration (last trading day <= exp), the trading day before a split ex-date, or the test's end."""
    candidates = [max(d for d in trading_days if d <= exp) if exp <= LAST else LAST]
    for ex in splits.get(ticker, {}):
        if sale_day < ex <= exp:
            candidates.append(max(d for d in trading_days if d < ex))
    return min(candidates)


def outcome(ticker, sale_day, kind, exp, strike, sale_bid, quotes, last_day, closes, split_cut, contracts):
    """First 75% buyback minute, else expiration / split / end valuation. Dollar P&L of the option leg."""
    trigger = 0.25 * sale_bid
    sale_min = datetime.combine(sale_day, dtime(15, 45), NY)
    for ts, bid, ask in quotes:
        if ts <= sale_min or ts.date() > last_day or ts.time() > dtime(15, 59):
            continue
        if ask > 0 and ask <= trigger + 1e-9:
            pnl = contracts * ((sale_bid * 100 - FEE) - (ask * 100 + FEE))
            return {"result": "closed_75", "close_time": ts.isoformat(), "close_price": ask, "pnl": pnl}
    premium = contracts * (sale_bid * 100 - FEE)
    if last_day < exp or (exp > LAST):
        # split-eve buyback or still open at the end: the last mid of last_day
        day_q = [(ts, b, a) for ts, b, a in quotes if ts.date() == last_day and ts.time() <= dtime(15, 59)]
        if not day_q:
            day_q = [(ts, b, a) for ts, b, a in quotes if ts.date() <= last_day]
        ts, b, a = day_q[-1]
        mid = (b + a) / 2
        kind_res = "split_close" if split_cut else "open_at_end"
        pnl = premium - contracts * mid * 100 - (contracts * FEE if split_cut else 0.0)
        return {"result": kind_res, "close_time": ts.isoformat(), "close_price": mid, "pnl": pnl,
                "pnl_alt_no_fee": premium - contracts * mid * 100}
    close = closes[last_day]
    if kind == "P" and close < strike:
        return {"result": "assigned", "expiry_close": close, "pnl": premium,
                "pnl_marked_to_close": premium - contracts * 100 * (strike - close)}
    if kind == "C" and close > strike:
        return {"result": "called_away", "expiry_close": close, "pnl": premium,
                "pnl_marked_to_close": premium - contracts * 100 * (close - strike)}
    return {"result": "expired_worthless", "expiry_close": close, "pnl": premium}


# ------------------------------------------------------------------ holding the five stocks

def interest(cash, prev, day):
    return cash * rate_on(day) * (day - prev).days / 365


def hold_benchmark(closes, trading_days, splits, divs):
    out = {}
    total = 0.0
    for t in TICKERS:
        spot = spot1545(FIRST, t)
        shares, cash, prev = SLEEVE / spot, 0.0, FIRST
        div_total = int_total = 0.0
        for d in trading_days:
            if d == FIRST:
                continue
            i = interest(cash, prev, d)
            cash += i
            int_total += i
            prev = d
            if d in splits.get(t, {}):
                shares *= splits[t][d]
            if d in divs.get(t, {}):
                cash += shares * divs[t][d]
                div_total += shares * divs[t][d]
        value = shares * closes[t][LAST] + cash
        out[t] = {"buy_price": spot, "shares_end": shares, "dividends": div_total, "interest": int_total,
                  "final_value": value}
        total += value
    out["total_final_value"] = total
    return out


# ------------------------------------------------------------------ independent full sleeve replay (own rules)

def day_quotes(quotes, day):
    return [(ts, b, a) for ts, b, a in quotes if ts.date() == day and ts.time() <= dtime(15, 59)]


def last_mid(quotes, day):
    q = [(ts, b, a) for ts, b, a in quotes if ts.date() <= day and ts.time() <= dtime(15, 59)]
    if not q:
        return None
    return (q[-1][1] + q[-1][2]) / 2


def simulate_sleeve(ticker, closes, trading_days, splits, divs):
    """Runs one sleeve with this file's own reading of the plan, from the cache only. Stops at the first contract
    whose files are not cached yet (the frontier). Returns the contract list, totals and the final state."""
    cash, shares, opt = SLEEVE, 0.0, None
    next_sale = FIRST  # selling allowed on trading days >= this date
    prev, value, frontier = None, None, None
    recs, totals = [], defaultdict(float)

    def close_option(d, price, result, ts=None, buy=True):
        nonlocal cash, opt
        n = opt["contracts"]
        cost = n * (price * 100 + FEE) if buy else 0.0
        if buy:
            cash -= cost
            totals["buybacks"] += n * price * 100
            totals["fees"] += n * FEE
        opt["rec"].update(result=result, close_day=d.isoformat(), close_time=ts.isoformat() if ts else None,
                          close_price=price if buy else None, pnl=opt["premium_net"] - cost)
        opt = None

    def check_buyback(d):
        trig = 0.25 * opt["sale_price"]
        sale_min = datetime.combine(opt["sale_day"], dtime(15, 45), NY)
        for ts, b, a in day_quotes(opt["quotes"], d):
            if ts > sale_min and a > 0 and a <= trig + 1e-9:
                close_option(d, a, "closed_75", ts)
                return ts
        return None

    for d in trading_days:
        if prev is not None:
            i = interest(cash, prev, d)
            cash += i
            totals["interest"] += i
        prev = d
        if d in splits.get(ticker, {}):
            shares *= splits[ticker][d]
        if d in divs.get(ticker, {}) and shares:
            cash += shares * divs[ticker][d]
            totals["dividends"] += shares * divs[ticker][d]
        if opt is not None:
            ts = check_buyback(d)
            if ts is not None:
                next_sale = d if ts.time() < dtime(15, 45) else date.fromordinal(d.toordinal() + 1)
        # 15:45 decision
        if opt is None and d >= next_sale and d < LAST:
            spot = spot1545(d, ticker)
            if spot == "missing":
                frontier = (d.isoformat(), "spot1545 file missing")
                break
            if spot is not None:
                kind = "C" if shares > 1e-9 else "P"
                chain = chain_file(ticker, d)
                if chain is None:
                    frontier = (d.isoformat(), "chain file missing")
                    break
                pick = pick_contract(ticker, d, kind, spot, chain)
                if isinstance(pick, dict):
                    exp, k = pick["expiration"], pick["strike"]
                    files = quote_file(ticker, d, exp, kind, k)
                    if not files:
                        frontier = (d.isoformat(), f"quote file missing for my pick {osi_compact(ticker, exp, kind, k)}")
                        break
                    n = cash / (k * 100) if kind == "P" else shares / 100
                    last_day = last_day_for(ticker, d, exp, trading_days, splits)
                    premium = n * pick["bid"] * 100
                    cash += premium - n * FEE
                    totals["premiums"] += premium
                    totals["fees"] += n * FEE
                    rec = {"ticker": ticker, "sale_day": d.isoformat(), "kind": kind, "expiration": exp.isoformat(),
                           "strike": k, "spot": spot, "delta": round(pick["delta"], 4), "sale_price": pick["bid"],
                           "contracts": n, "fallback": pick["fallback"], "last_day": last_day.isoformat(),
                           "cache_file": files[0].name}
                    recs.append(rec)
                    opt = {"kind": kind, "expiration": exp, "strike": k, "contracts": n, "sale_price": pick["bid"],
                           "sale_day": d, "last_day": last_day, "quotes": read_quotes(files[0]),
                           "premium_net": premium - n * FEE, "rec": rec}
                    if check_buyback(d) is not None:
                        next_sale = date.fromordinal(d.toordinal() + 1)
        # end of the option's life (after the 15:45 decision; judged at the close)
        if opt is not None and d == opt["last_day"] and d < LAST or (opt is not None and d == LAST
                                                                     and opt["expiration"] == LAST):
            if d < opt["expiration"]:  # trading day before a split ex-date
                close_option(d, last_mid(opt["quotes"], d), "split_close")
            else:
                close = closes[ticker][d]
                k, n = opt["strike"], opt["contracts"]
                if opt["kind"] == "P" and close < k:
                    cash -= n * 100 * k
                    shares += n * 100
                    res = "assigned"
                elif opt["kind"] == "C" and close > k:
                    cash += n * 100 * k
                    shares -= n * 100
                    res = "called_away"
                else:
                    res = "expired_worthless"
                opt["rec"]["expiry_close"] = close
                close_option(d, 0.0, res, buy=False)
            next_sale = date.fromordinal(d.toordinal() + 1)
        opt_val = 0.0
        if opt is not None:
            m = last_mid(opt["quotes"], d)
            opt_val = opt["contracts"] * 100 * (m if m is not None else 0.0)
        value = cash + shares * closes[ticker][d] - opt_val
    return {"contracts": recs, "totals": dict(totals), "cash": cash, "shares": shares, "final_value": value,
            "frontier": frontier,
            "open_option": None if opt is None else {k: str(v) for k, v in opt.items() if k not in ("quotes", "rec")}}


def cached_main_contracts(ticker):
    out = []
    for p in sorted((DATA / "quotes" / ticker).glob("*.csv.gz")):
        sale, sym, last = p.name[:-7].split("_")
        out.append((sale, sym, last))
    return out


# ------------------------------------------------------------------ reading the main run's JSON (field-name tolerant)

ALIASES = {
    "ticker": ("ticker", "symbol", "stock", "sleeve"),
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
    """{ticker: [contract dicts]} from the main version: lists of dicts with a strike and an expiration, on a path
    that mentions 'main' (or no version at all), never an information version."""
    info = ("delta_25", "delta_45", "hold_to_expiry", "basis_floor", "whole_contracts")
    out = defaultdict(list)
    for path, obj in walk(res):
        if not (isinstance(obj, list) and obj and isinstance(obj[0], dict)):
            continue
        if field(obj[0], "strike") is None or field(obj[0], "expiration") is None:
            continue
        if any(x in path for x in info):
            continue
        tick = next((p for p in path if p in TICKERS), None)
        for c in obj:
            t = field(c, "ticker") if field(c, "ticker") in TICKERS else tick
            if t:
                out[t].append(c)
    return out


def json_final_values(res):
    """{(path...): value} of every key that looks like a final value, for the report to match by ticker."""
    out = {}
    for path, obj in walk(res):
        if isinstance(obj, (int, float)) and path and path[-1] in ("final_value", "final_equity", "end_value"):
            out["/".join(path)] = obj
    return out


# ------------------------------------------------------------------ main

def near(a, b, tol):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def recheck_contract(ticker, sale_day, kind, contracts, trading_days, closes, splits):
    """Standalone recomputation of one contract from the raw files (does not use the sleeve replay)."""
    spot = spot1545(sale_day, ticker)
    chain = chain_file(ticker, sale_day)
    if spot in (None, "missing") or chain is None:
        return {"error": f"raw file missing: spot={spot!r}, chain={'ok' if chain else 'missing'}"}
    pick = pick_contract(ticker, sale_day, kind, spot, chain)
    if not isinstance(pick, dict):
        return {"error": pick}
    exp, k = pick["expiration"], pick["strike"]
    files = quote_file(ticker, sale_day, exp, kind, k)
    if not files:
        return {"error": f"quote file missing for {osi_compact(ticker, exp, kind, k)}", "expiration": exp.isoformat(),
                "strike": k}
    last_day = last_day_for(ticker, sale_day, exp, trading_days, splits)
    split_cut = last_day < exp and last_day < LAST
    o = outcome(ticker, sale_day, kind, exp, k, pick["bid"], read_quotes(files[0]), last_day, closes[ticker],
                split_cut, contracts)
    return {"spot": spot, "expiration": exp.isoformat(), "strike": k, "delta": round(pick["delta"], 4),
            "fallback": pick["fallback"], "sale_price": pick["bid"], "contracts": contracts,
            "last_day": last_day.isoformat(), "cache_file": files[0].name, **o}


def main():
    closes = {t: daily(t) for t in TICKERS}
    days = [d for d in sorted(set.intersection(*(set(c) for c in closes.values()))) if FIRST <= d <= LAST]
    splits, divs = corporate_actions()
    res = json.loads(RESULTS.read_text()) if RESULTS.exists() else None
    mismatches = []
    summary = {"results_json": str(RESULTS.relative_to(ROOT)) if res else "MISSING (main run not finished)"}

    # A. full independent replay of each sleeve vs the main run's cached contract choices
    replays, replay_check = {}, {}
    for t in TICKERS:
        r = simulate_sleeve(t, closes, days, splits, divs)
        replays[t] = r
        mine = {c["cache_file"] for c in r["contracts"]}
        frontier = r["frontier"][0] if r["frontier"] else "9999-12-31"
        cached = [f"{a}_{b}_{c}.csv.gz" for a, b, c in cached_main_contracts(t)]
        missing_from_mine = [f for f in cached if f[:10] < frontier and f not in mine]
        lastday_bad = [c["cache_file"] for c in r["contracts"] if c["cache_file"].rsplit("_", 1)[1][:10] != c["last_day"]]
        replay_check[t] = {"my_contracts": len(r["contracts"]), "cached_files_before_frontier":
                           sum(f[:10] < frontier for f in cached), "frontier": r["frontier"],
                           "cached_not_in_my_replay": missing_from_mine[:10], "last_day_mismatch": lastday_bad[:10],
                           "replay_final_value": None if r["frontier"] else round(r["final_value"], 2),
                           "replay_totals": {k: round(v, 2) for k, v in r["totals"].items()}}
        if missing_from_mine or lastday_bad:
            mismatches.append(f"replay vs cache {t}")
    summary["replay_vs_cached_main_contracts"] = replay_check

    # B. 12 random contracts recomputed standalone from the raw files
    rng = random.Random(2929)
    jc = json_main_contracts(res) if res else {}
    pools = {}
    for t in TICKERS:
        if jc.get(t):
            pools[t] = [("json", c) for c in jc[t]]
        else:  # no JSON yet: the main run's own choices, read from its cached quote-file names
            frontier = replays[t]["frontier"][0] if replays[t]["frontier"] else "9999-12-31"
            pools[t] = [("cache", c) for c in replays[t]["contracts"] if c["sale_day"] < frontier and c.get("result")]
    picks, order = [], list(TICKERS)
    for i in range(12):
        t = order[i % 5]
        pool = [x for x in pools[t] if x not in [p[1] for p in picks]]
        if pool:
            picks.append((t, rng.choice(pool)))
    sample = []
    for t, (src, c) in picks:
        if src == "json":
            sale_day = date.fromisoformat(str(field(c, "sale_day"))[:10])
            kind = str(field(c, "kind"))[0].upper()
            n = float(field(c, "contracts"))
            main_vals = {k: field(c, k) for k in ALIASES}
        else:
            sale_day, kind, n = date.fromisoformat(c["sale_day"]), c["kind"], c["contracts"]
            sym = c["cache_file"].split("_")[1]
            main_vals = {"expiration": f"20{sym[-15:-13]}-{sym[-13:-11]}-{sym[-11:-9]}", "strike": int(sym[-8:]) / 1000,
                         "kind": sym[-9], "last_day": c["cache_file"].rsplit("_", 1)[1][:10]}
        mine = recheck_contract(t, sale_day, kind, n, days, closes, splits)
        checks = {}
        if "error" not in mine:
            checks["expiration"] = str(main_vals.get("expiration"))[:10] == mine["expiration"]
            checks["strike"] = near(main_vals.get("strike"), mine["strike"], 1e-9)
            if src == "json":
                if main_vals.get("sale_price") is not None:
                    checks["sale_price"] = near(main_vals["sale_price"], mine["sale_price"], PRICE_TOL)
                if main_vals.get("result") is not None:
                    checks["result_text"] = f"main={main_vals['result']} mine={mine['result']}"
                if main_vals.get("close_price") is not None and mine["result"] == "closed_75":
                    checks["buyback_price"] = near(main_vals["close_price"], mine["close_price"], PRICE_TOL)
                if main_vals.get("pnl") is not None:
                    checks["pnl"] = near(main_vals["pnl"], mine["pnl"], 0.05 * max(n, 1e-9) + 1e-9)
            else:
                checks["last_day"] = main_vals["last_day"] == mine["last_day"]
                rp = next(x for x in replays[t]["contracts"] if x["sale_day"] == c["sale_day"])
                checks["replay_agrees_result"] = rp.get("result") == mine["result"]
                checks["replay_agrees_pnl"] = near(rp.get("pnl"), mine["pnl"], 0.05 * max(n, 1e-9))
        bad = "error" in mine or any(v is False for v in checks.values())
        if bad:
            mismatches.append(f"contract {t} {sale_day}")
        sample.append({"ticker": t, "sale_day": sale_day.isoformat(), "kind": kind, "source": src,
                       "main": {k: v for k, v in main_vals.items() if v is not None}, "mine":
                       {k: (round(v, 4) if isinstance(v, float) else v) for k, v in mine.items()},
                       "checks": checks, "ok": not bad})
    summary["sample_contracts"] = sample

    # C. sleeve final values
    if res:
        fv = json_final_values(res)
        summary["json_final_value_keys"] = fv
        sleeve = {}
        for t in TICKERS:
            keys = [k for k in fv if t in k.split("/") and not any(x in k for x in (
                "delta_25", "delta_45", "hold_to_expiry", "basis_floor", "whole_contracts", "hold", "bench"))]
            rv = replays[t]["final_value"] if not replays[t]["frontier"] else None
            sleeve[t] = {"json_keys": keys, "json_values": [fv[k] for k in keys], "replay": rv}
            if rv is None or not keys or not any(near(fv[k], rv, 1.0) for k in keys):
                mismatches.append(f"sleeve final {t}")
        summary["sleeve_final_values"] = sleeve
    else:
        summary["sleeve_final_values"] = "not checked: results JSON missing (replay stops at the cache frontier)"

    # D. holding the same five stocks
    hold = hold_benchmark(closes, days, splits, divs)
    summary["hold_five_stocks_mine"] = {k: (round(v["final_value"], 2) if isinstance(v, dict) else round(v, 2))
                                        for k, v in hold.items()}
    if res:
        hk = {k: v for k, v in json_final_values(res).items() if "hold" in k or "bench" in k}
        summary["hold_json_keys"] = hk
        if not any(near(v, hold["total_final_value"], 1.0) for v in hk.values()):
            mismatches.append("hold benchmark total")
    summary["mismatches"] = mismatches
    summary["verdict"] = "ALL MATCH" if not mismatches else "MISMATCH"
    print(json.dumps(summary, indent=1, default=str))
    sys.exit(1 if mismatches or not res else 0)


if __name__ == "__main__":
    main()
