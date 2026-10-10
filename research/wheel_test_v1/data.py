"""Data for pre-declared test #29, the Reddit wheel on AVGO, CRM, AMZN, META, CBOE (plan: output/WHEEL_TEST_PLAN_20261010.md).

Owner approvals (chat, Oct 10, 2026): Databento spend with a HARD STOP of $40 in total for this test (main version and
the five information versions together), and a one-time download of FRED series TB3MS (3-month T-bill, monthly) to
extend the T-bill rates through Sep 2026. Nothing else is bought or downloaded beyond Alpaca market data.

Everything is fetched on demand by the backtest and cached under outputs/wheel_test_data/, so nothing is bought twice:
- Alpaca SIP raw daily bars (one file per stock), the 15:45 ET 1-minute bar on decision days (one small file per
  day, all five stocks in one request), splits and cash dividends from Alpaca corporate actions.
- Databento OPRA.PILLAR cbbo-1m:
  * the whole chain of one stock for the minute 15:45-15:46 ET on a day the sleeve sells, trimmed before saving to
    puts and calls expiring in 0-45 days with strikes within +-30% of the 15:45 stock price;
  * one contract's minutes from 15:46 ET on its sale day to 16:00 ET on its last day (expiration, the trading day
    before a split, or the test's end).
  Before EVERY Databento request the free metadata.get_cost endpoint prices it; the running total is kept in
  outputs/wheel_test_data/databento_spent.json (cumulative across runs) and a request that would take it past $40 is
  refused (the run stops). The key is never printed.
- FRED TB3MS saved once as outputs/wheel_test_data/tb3ms.csv (the shared CSV in research/spy_put_spread_backtest_v1
  is not touched).

  PYTHONPATH=src:. .venv/bin/python -m research.wheel_test_v1.data --estimate   # free cost estimate, no purchase
"""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict
import csv
from datetime import date, datetime, time as dtime, timedelta, timezone
import gzip
import http.client
import io
import json
import os
from pathlib import Path
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/wheel_test_data"
SHARED_RATES = ROOT / "research/spy_put_spread_backtest_v1/tbill_3m_monthly.csv"
TICKERS = ("AVGO", "CRM", "AMZN", "META", "CBOE")
FIRST, LAST = date(2020, 1, 2), date(2026, 10, 9)
BUDGET = 40.0
DB = "https://hist.databento.com/v0/"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TB3MS"
FB_LAST = date(2022, 6, 8)  # META's options traded under the FB root through this day, META from Jun 9, 2022
MAX_DTE, STRIKE_LO, STRIKE_HI = 45, 0.70, 1.30
DECIDE, DECIDE_END = dtime(15, 45), dtime(15, 46)
WINDOW_START, WINDOW_END = dtime(15, 46), dtime(16, 0)


class BudgetExceeded(SystemExit):
    pass


def option_root(ticker, day):
    return "FB" if ticker == "META" and day <= FB_LAST else ticker


def osi(root, expiration, kind, strike):
    """('AMZN', 2024-08-16, 'P', 160) -> 'AMZN  240816P00160000' (root padded to 6, as OPRA/Databento print it)."""
    return f"{root:<6}{expiration:%y%m%d}{kind}{round(strike * 1000):08d}"


def parse_osi(symbol):
    """'AMZN  240816P00160000' -> ('AMZN', date(2024, 8, 16), 'P', 160.0), else None."""
    s = (symbol or "").rstrip()
    if len(s) < 16:
        return None
    root, tail = s[:-15].strip(), s[-15:]
    try:
        exp = date(2000 + int(tail[0:2]), int(tail[2:4]), int(tail[4:6]))
        kind, strike = tail[6], int(tail[7:15]) / 1000
    except ValueError:
        return None
    return (root, exp, kind, strike) if kind in "CP" and root else None


def _num(x):
    try:
        return float(x) if x not in (None, "") else 0.0
    except ValueError:
        return 0.0


def _atomic_write(path, write):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    write(tmp)
    tmp.replace(path)  # a stopped run never leaves a half-written file behind


def _write_gz_csv(path, header, rows):
    def write(tmp):
        with gzip.open(tmp, "wt", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
    _atomic_write(path, write)


def _write_json(path, obj):
    _atomic_write(path, lambda tmp: tmp.write_text(json.dumps(obj, indent=1) + "\n"))


# ---------------------------------------------------------------- Databento (cost-guarded)

class Databento:
    """OPRA.PILLAR cbbo-1m only. Every request is priced first with the free metadata.get_cost endpoint; the spent
    total persists in <data>/databento_spent.json and nothing is requested that would take it past the budget."""

    def __init__(self, budget=BUDGET, data=DATA, workers=8):
        from research.spy_put_spread_backtest_v1.fetch_databento import api_key
        self._key = api_key()
        self._auth = "Basic " + base64.b64encode((self._key + ":").encode()).decode()
        self.budget, self.data = budget, data
        self.lock, self.slots = threading.Lock(), threading.Semaphore(workers)
        self.spent_path, self.ledger_path = data / "databento_spent.json", data / "databento_ledger.csv"
        self.spent = json.loads(self.spent_path.read_text())["spent_dollars"] if self.spent_path.exists() else 0.0
        self.spent_this_run = 0.0

    def _post(self, path, params):
        body = urllib.parse.urlencode(params).encode()
        for attempt in range(20):
            req = urllib.request.Request(DB + path, data=body, method="POST",
                                         headers={"Authorization": self._auth,
                                                  "Content-Type": "application/x-www-form-urlencoded"})
            try:
                with self.slots, urllib.request.urlopen(req, timeout=300) as r:
                    return r.read().decode()
            except urllib.error.HTTPError as e:
                detail = e.read(400).decode(errors="replace").replace(self._key, "[key]")
                if e.code in (429, 500, 502, 503, 504) and attempt < 19:
                    time.sleep(min(60, 5 * (attempt + 1)))
                    continue
                raise RuntimeError(f"Databento HTTP {e.code}: {detail}") from None
            except (OSError, http.client.HTTPException):
                if attempt == 19:
                    raise
                time.sleep(min(60, 5 * (attempt + 1)))

    @staticmethod
    def params(symbols, stype, start, end):
        return {"dataset": "OPRA.PILLAR", "symbols": symbols, "stype_in": stype, "schema": "cbbo-1m",
                "start": start.astimezone(timezone.utc).isoformat(), "end": end.astimezone(timezone.utc).isoformat()}

    def cost(self, symbols, stype, start, end):
        """Free: the dollar price of a request, without buying it."""
        return float(self._post("metadata.get_cost", self.params(symbols, stype, start, end)))

    def get(self, symbols, stype, start, end, label=""):
        p = self.params(symbols, stype, start, end)
        cost = float(self._post("metadata.get_cost", p))
        with self.lock:
            if self.spent + cost > self.budget + 1e-12:
                raise BudgetExceeded(f"Databento budget guard: ${self.spent:.4f} spent so far, the next request "
                                     f"(${cost:.4f}, {label}) would pass the ${self.budget:.2f} hard stop. Stopped.")
            self.spent += cost  # reserved before the download so parallel workers cannot overshoot
            self.spent_this_run += cost
            _write_json(self.spent_path, {"spent_dollars": round(self.spent, 6), "budget_dollars": self.budget,
                                          "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            new = not self.ledger_path.exists()
            with self.ledger_path.open("a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["utc", "label", "symbols", "stype", "start", "end", "cost", "spent_after"])
                w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), label, symbols, stype,
                            p["start"], p["end"], f"{cost:.6f}", f"{self.spent:.6f}"])
        text = self._post("timeseries.get_range", {**p, "encoding": "csv", "compression": "none", "pretty_px": "true",
                                                   "pretty_ts": "true", "map_symbols": "true"})
        return list(csv.DictReader(io.StringIO(text)))


# ---------------------------------------------------------------- Alpaca + FRED

_alpaca_pace = threading.Lock()


def alpaca(path):
    """Alpaca market data GET, paced to about 3 requests a second across threads, with retries."""
    from research.forward_watch_v1.watch import get
    from research.lite_dip_history_v1.run import DATA as ALPACA
    for attempt in range(10):
        with _alpaca_pace:
            time.sleep(0.35)
        try:
            return get(ALPACA + path)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 9:
                raise
            time.sleep(10 * (attempt + 1))
        except (urllib.error.URLError, OSError):
            if attempt == 9:
                raise
            time.sleep(5 * (attempt + 1))


def _utc(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_daily(ticker, data=DATA):
    path = data / f"daily_{ticker}.json"
    if path.exists():
        return json.loads(path.read_text())
    rows, token = [], None
    while True:
        q = {"timeframe": "1Day", "feed": "sip", "adjustment": "raw", "start": "2019-12-01T00:00:00Z",
             "end": f"{LAST + timedelta(days=1)}T00:00:00Z", "limit": 10000}
        if token:
            q["page_token"] = token
        page = alpaca(f"/v2/stocks/{ticker}/bars?{urllib.parse.urlencode(q)}")
        rows += page.get("bars") or []
        token = page.get("next_page_token")
        if not token:
            break
    out = {r["t"][:10]: r["c"] for r in rows}
    _write_json(path, out)
    return out


def fetch_spots(day, tickers=TICKERS, data=DATA):
    """{ticker: open of the 15:45 ET SIP 1-minute bar} (None if no bar, e.g. on 13:00 half days)."""
    path = data / "spot1545" / f"{day.isoformat()}.json"
    if path.exists():
        return json.loads(path.read_text())
    start = datetime.combine(day, DECIDE, NY)
    q = {"symbols": ",".join(tickers), "timeframe": "1Min", "feed": "sip", "adjustment": "raw", "limit": 100,
         "start": _utc(start), "end": _utc(start + timedelta(seconds=59))}
    bars = alpaca(f"/v2/stocks/bars?{urllib.parse.urlencode(q)}").get("bars") or {}
    want = _utc(start)
    out = {t: next((b["o"] for b in bars.get(t) or [] if b["t"] == want), None) for t in tickers}
    _write_json(path, out)
    return out


def fetch_corporate_actions(tickers=TICKERS, data=DATA):
    path = data / "corporate_actions.json"
    if path.exists():
        return json.loads(path.read_text())
    out, token = {"forward_splits": [], "cash_dividends": []}, None
    while True:
        q = {"symbols": ",".join(tickers), "types": "forward_split,cash_dividend", "start": "2019-12-01",
             "end": (LAST + timedelta(days=1)).isoformat(), "limit": 1000}
        if token:
            q["page_token"] = token
        page = alpaca(f"/v1/corporate-actions?{urllib.parse.urlencode(q)}")
        for k in out:
            out[k] += (page.get("corporate_actions") or {}).get(k) or []
        token = page.get("next_page_token")
        if not token:
            break
    _write_json(path, out)
    return out


def fetch_tb3ms(data=DATA):
    """One-time FRED TB3MS download (owner-approved), saved as <data>/tb3ms.csv."""
    path = data / "tb3ms.csv"
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(FRED_URL, headers={"User-Agent": "research"}),
                                    timeout=60) as r:
            text = r.read().decode()
        if "TB3MS" not in text.splitlines()[0]:
            raise RuntimeError("Unexpected FRED response")
        _atomic_write(path, lambda tmp: tmp.write_text(text))
    return path


def load_rates(data=DATA, shared=SHARED_RATES):
    """{'YYYY-MM': annual rate (decimal)}: the shared CSV through Dec 2025, FRED TB3MS for later months."""
    with shared.open() as f:
        rates = {r["month"]: float(r["rate_pct"]) / 100 for r in csv.DictReader(f)}
    last_shared = max(rates)
    path = data / "tb3ms.csv"
    if path.exists():
        with path.open() as f:
            rows = list(csv.reader(f))
        for row in rows[1:]:
            if len(row) >= 2 and row[1] not in ("", "."):
                month = row[0][:7]
                if month > last_shared:
                    rates[month] = float(row[1]) / 100
    return rates


# ---------------------------------------------------------------- provider used by the backtest

class Provider:
    """Answers the backtest's questions from the cache, fetching (and caching) anything missing."""

    def __init__(self, tickers=TICKERS, data=DATA, db=None, budget=BUDGET):
        self.tickers, self.data = tickers, data
        self._db, self._budget = db, budget
        self._meta = threading.Lock()
        self._locks = defaultdict(threading.Lock)
        self.closes = {t: {date.fromisoformat(d): c for d, c in fetch_daily(t, data).items()} for t in tickers}
        ca = fetch_corporate_actions(tickers, data)
        self._splits = defaultdict(dict)
        for s in ca["forward_splits"]:
            self._splits[s["symbol"]][date.fromisoformat(s["ex_date"])] = s["new_rate"] / s["old_rate"]
        self._divs = defaultdict(dict)
        for d in ca["cash_dividends"]:
            day = date.fromisoformat(d["ex_date"])
            self._divs[d["symbol"]][day] = self._divs[d["symbol"]].get(day, 0.0) + float(d["rate"])
        fetch_tb3ms(data)
        self._rates = load_rates(data)
        self.chain_fetches = self.quote_fetches = 0

    @property
    def db(self):
        with self._meta:
            if self._db is None:
                self._db = Databento(self._budget, self.data)
            return self._db

    def _lock(self, key):
        with self._meta:
            return self._locks[key]

    def trading_days(self, first=FIRST, last=LAST):
        days = sorted(set.intersection(*(set(c) for c in self.closes.values())))
        return [d for d in days if first <= d <= last]

    def close(self, ticker, day):
        return self.closes[ticker][day]

    def spot(self, ticker, day):
        with self._lock(("spot", day)):
            return fetch_spots(day, self.tickers, self.data).get(ticker)

    def splits(self, ticker):
        return dict(self._splits.get(ticker, {}))

    def dividends(self, ticker):
        return dict(self._divs.get(ticker, {}))

    def rate(self, day):
        key = day.strftime("%Y-%m")
        if key in self._rates:
            return self._rates[key]
        earlier = [m for m in self._rates if m <= key]
        return self._rates[max(earlier)] if earlier else 0.0

    def chain(self, ticker, day, spot):
        """{(expiration, 'P'/'C', strike): (bid, ask)} for 15:45-15:46 ET, 0-45 days, strikes within +-30%."""
        path = self.data / "chain" / ticker / f"{day.isoformat()}.csv.gz"
        with self._lock(("chain", ticker, day)):
            if not path.exists():
                root = option_root(ticker, day)
                start = datetime.combine(day, DECIDE, NY)
                rows = self.db.get(f"{root}.OPT", "parent", start, datetime.combine(day, DECIDE_END, NY),
                                   label=f"chain {ticker} {day}")
                best = {}
                for r in rows:
                    info = parse_osi(r.get("symbol", ""))
                    if not info or info[0] != root:  # also drops adjusted (non-standard) roots
                        continue
                    _, exp, kind, strike = info
                    if not 0 <= (exp - day).days <= MAX_DTE or not STRIKE_LO * spot <= strike <= STRIKE_HI * spot:
                        continue
                    key = (exp, kind, strike)
                    ts = r.get("ts_recv", "")
                    if key not in best or ts >= best[key][2]:
                        best[key] = (_num(r.get("bid_px_00")), _num(r.get("ask_px_00")), ts)
                _write_gz_csv(path, ["expiration", "type", "strike", "bid", "ask", "ts_recv"],
                              [[e.isoformat(), k, f"{s:g}", f"{b:.2f}", f"{a:.2f}", ts]
                               for (e, k, s), (b, a, ts) in sorted(best.items())])
                self.chain_fetches += 1
        return load_chain(path)

    def quotes(self, ticker, kind, expiration, strike, sale_day, last_day):
        """[(New York datetime of the minute, bid, ask)] from 15:46 on sale_day through 16:00 on last_day."""
        name = f"{sale_day.isoformat()}_{osi(ticker, expiration, kind, strike).replace(' ', '')}_{last_day.isoformat()}"
        path = self.data / "quotes" / ticker / f"{name}.csv.gz"
        with self._lock(("quotes", path.name)):
            if not path.exists():
                rows = []
                for root, a, b in quote_segments(ticker, sale_day, last_day):
                    sym = osi(root, expiration, kind, strike)
                    for r in self.db.get(sym, "raw_symbol", a, b, label=f"contract {sym.replace(' ', '')} {sale_day}"):
                        rows.append([r.get("ts_recv", ""), f"{_num(r.get('bid_px_00')):.2f}",
                                     f"{_num(r.get('ask_px_00')):.2f}"])
                rows.sort()
                _write_gz_csv(path, ["ts", "bid", "ask"], rows)
                self.quote_fetches += 1
        return load_quotes(path)


def quote_segments(ticker, sale_day, last_day):
    """[(option root, start, end)]: META contracts that straddle the FB -> META rename come in two pieces."""
    start, end = datetime.combine(sale_day, WINDOW_START, NY), datetime.combine(last_day, WINDOW_END, NY)
    if ticker == "META" and sale_day <= FB_LAST < last_day:
        cut = datetime.combine(FB_LAST, WINDOW_END, NY)
        return [("FB", start, cut), ("META", datetime.combine(FB_LAST + timedelta(days=1), dtime(9, 30), NY), end)]
    return [(option_root(ticker, sale_day), start, end)]


def load_chain(path):
    chain = {}
    with gzip.open(path, "rt") as f:
        for r in csv.DictReader(f):
            chain[(date.fromisoformat(r["expiration"]), r["type"], float(r["strike"]))] = (float(r["bid"]), float(r["ask"]))
    return chain


def parse_ts(ts):
    """'2020-01-03T20:46:00.000000000Z' -> New York datetime (to the second)."""
    return datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(NY)


def load_quotes(path):
    with gzip.open(path, "rt") as f:
        return [(parse_ts(r["ts"]), float(r["bid"]), float(r["ask"])) for r in csv.DictReader(f) if r["ts"]]


# ---------------------------------------------------------------- free dry-run cost estimate

def estimate(samples_per_ticker=14, seed=29):
    """Prices sample chain-minutes and ~1-2 week contract windows with the free cost endpoint. Buys nothing."""
    db = Databento()
    prov = Provider(db=db)
    days = prov.trading_days()
    rng = random.Random(seed)
    out = {"chain_minute": {}, "contract_window": {}}
    for t in TICKERS:
        picks = sorted(rng.sample(days, samples_per_ticker))
        chain_costs, window_costs = [], []
        for d in picks:
            root = option_root(t, d)
            start = datetime.combine(d, DECIDE, NY)
            chain_costs.append(db.cost(f"{root}.OPT", "parent", start, datetime.combine(d, DECIDE_END, NY)))
            # a plausible weekly contract: the Friday 5-11 days out, strike near 95% of the close, price the window
            spot = prov.close(t, d)
            fri = d + timedelta(days=(4 - d.weekday()) % 7 + 7)
            step = 5 if spot > 200 else (2.5 if spot > 50 else 1)
            strike = round(0.95 * spot / step) * step
            last = max(x for x in days if x <= fri) if fri <= days[-1] else days[-1]
            try:
                for root2, a, b in quote_segments(t, d, last):
                    window_costs.append(db.cost(osi(root2, fri, "P", strike), "raw_symbol", a, b))
            except RuntimeError as e:
                window_costs.append(None)
                print(json.dumps({"window_cost_error": str(e)[:160], "ticker": t, "day": d.isoformat()}))
        out["chain_minute"][t] = [round(c, 5) for c in chain_costs]
        out["contract_window"][t] = [None if c is None else round(c, 6) for c in window_costs]
    return out, len(days)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--estimate", action="store_true", help="free cost estimate only (no purchase)")
    args = ap.parse_args()
    if args.estimate:
        out, n_days = estimate()
        print(json.dumps({"trading_days": n_days, **out}, indent=1))


if __name__ == "__main__":
    main()
