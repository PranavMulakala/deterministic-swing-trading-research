"""Data for pre-declared test #32, the weekly wheel on LITE and MU (plan: output/WHEEL_LITE_MU_TEST_PLAN_20261010.md).

Reuses test #29's data layer (research/wheel_test_v1/data.py, committed in ef5e22b, NOT modified): the same Alpaca,
Databento and T-bill code, pointed at a SEPARATE folder with its own budget:
- outputs/wheel_lite_mu_data/ (gitignored). Test #29 uses outputs/wheel_test_data/ concurrently; nothing is written
  there. The T-bill file tb3ms.csv is copied from it once (read-only) instead of re-downloading from FRED.
- Databento OPRA.PILLAR cbbo-1m, HARD STOP $12 for this whole test (main + all information versions, cumulative across
  runs): every request is priced with the free metadata.get_cost endpoint first, the running total lives in
  outputs/wheel_lite_mu_data/databento_spent.json, and a request that would pass $12 stops the run. The key is never
  printed.
- Earnings dates (information version skip_earnings): SEC EDGAR 8-K filings with Item 2.02, free, from the
  data.sec.gov submissions API (User-Agent "Pranav Mulakala pmulakala90@gmail.com", paced well under 10 requests/s).
  Only the extracted Item 2.02 rows are saved (outputs/wheel_lite_mu_data/edgar/<cik>.json).

"Earnings session" (precise definition): the filing's acceptance time in New York time T. If T is on a trading day
before 16:00 ET (pre-market or during the session), the earnings session is that day; otherwise (at or after 16:00, or
on a non-trading day) it is the next trading day. Filings before the test's first trading day are dropped. Every
Item 2.02 8-K counts (including the few that announce a deal or a CEO change with preliminary results); amendments
(8-K/A) do not.

Time base of EDGAR's acceptanceDateTime (calibrated, not assumed): the "...Z" stamps cached by test #16 on Oct 5, 2026
were true UTC (Apple's 16:30 ET releases at 20:30Z), but the same filings fetched on Oct 10, 2026 came back 4-5 hours
later (00:30Z the next day), i.e. New York wall-clock time re-labelled as UTC once more. So calibrate() reads Apple's
(CIK 320193) Item 2.02 filings, which are always at 16:30 ET, and picks the reading ("utc" or "shifted") that puts them
at 16:25-16:40 ET; the choice is saved in edgar/calibration.json and the results record whether the other reading would
have changed any LITE/MU earnings session.

  PYTHONPATH=src:. .venv/bin/python -m research.wheel_lite_mu_v1.data --earnings    # free: fetch + print EDGAR dates
  PYTHONPATH=src:. .venv/bin/python -m research.wheel_lite_mu_v1.data --estimate    # free Databento cost estimate
"""
from __future__ import annotations

import argparse
import bisect
import gzip
import json
import random
import shutil
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

from research.ep_test_v1.fetch_edgar import earnings_rows
from research.wheel_test_v1 import data as w29

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/wheel_lite_mu_data"
TB3MS_FROM = ROOT / "outputs/wheel_test_data/tb3ms.csv"    # read once, never written
TICKERS = ("LITE", "MU")
CIKS = {"LITE": 1633978, "MU": 723125}
APPLE_CIK = 320193            # calibration only: Apple files its Item 2.02 8-K at 16:30 ET
BUDGET = 12.0
USER_AGENT = "Pranav Mulakala pmulakala90@gmail.com"
SUBMISSIONS = "https://data.sec.gov/submissions/"
EDGAR_SINCE = "2019-10-01"
NY = w29.NY
SESSION_CLOSE = (16, 0)


# ---------------------------------------------------------------- EDGAR earnings dates

def _edgar_json(url, pause=0.3):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"})
    for attempt in range(6):
        try:
            with build_opener(ProxyHandler({})).open(req, timeout=60) as reply:
                body, enc = reply.read(), reply.headers.get("Content-Encoding", "")
            time.sleep(pause)
            return json.loads(gzip.decompress(body) if enc == "gzip" else body)
        except Exception:
            if attempt == 5:
                raise
            time.sleep(5 * (attempt + 1))


def fetch_earnings(ticker, data=DATA):
    """[[acceptanceDateTime, filingDate, items], ...] for the stock's 8-K Item 2.02 filings (cached)."""
    return fetch_item202(CIKS[ticker], data)


def fetch_item202(cik, data=DATA):
    path = data / "edgar" / f"{cik}.json"
    if path.exists():
        return json.loads(path.read_text())["rows"]
    sub = _edgar_json(f"{SUBMISSIONS}CIK{cik:010d}.json")
    recent = sub["filings"]["recent"]
    rows = earnings_rows(recent)          # research/ep_test_v1/fetch_edgar.py: form == "8-K" and "2.02" in items
    if not recent["filingDate"] or min(recent["filingDate"]) > EDGAR_SINCE:
        for f in sub["filings"].get("files", []):
            if f.get("filingTo", "9999") >= EDGAR_SINCE:
                rows += earnings_rows(_edgar_json(SUBMISSIONS + f["name"]))
    rows = sorted(r for r in rows if r[1] >= EDGAR_SINCE)
    w29._write_json(path, {"cik": cik, "name": sub.get("name"), "user_agent": USER_AGENT, "rows": rows,
                           "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return rows


def acceptance_ny(stamp, shifted=False):
    """EDGAR acceptanceDateTime -> New York datetime. shifted=False: the stamp is true UTC. shifted=True: the stamp is
    true UTC converted to New York wall-clock and labelled UTC again, so undo that once more."""
    t = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(NY)
    return t.replace(tzinfo=timezone.utc).astimezone(NY) if shifted else t


def calibrate(data=DATA, rows=None):
    """Pick the time base from Apple's Item 2.02 filings (16:30 ET). Cached in <data>/edgar/calibration.json."""
    path = data / "edgar" / "calibration.json"
    if rows is None and path.exists():
        return json.loads(path.read_text())
    apple = rows if rows is not None else fetch_item202(APPLE_CIK, data)
    hits = {}
    for name, shifted in (("utc", False), ("shifted", True)):
        times = [acceptance_ny(r[0], shifted) for r in apple]
        hits[name] = sum((16, 25) <= (t.hour, t.minute) <= (16, 40) for t in times)
    best = max(hits, key=hits.get)
    if not apple or hits[best] < 0.8 * len(apple) or min(hits.values()) > 0.2 * len(apple):
        raise RuntimeError(f"EDGAR time base unclear from Apple's filings: {hits} of {len(apple)}")
    out = {"reading": best, "shifted": best == "shifted", "apple_filings": len(apple),
           "apple_filings_at_1625_1640_et": hits}
    if rows is None:
        w29._write_json(path, out)
    return out


def earnings_session(stamp, trading_days, shifted=False):
    """The first trading session that can react to a filing accepted at `stamp` (see the module docstring), or None
    for a filing before the first trading day. trading_days: sorted list of dates. Past the end of the list, the next
    weekday is used."""
    t = acceptance_ny(stamp, shifted)
    d = t.date()
    if d < trading_days[0]:
        return None
    i = bisect.bisect_left(trading_days, d)
    on_trading_day = i < len(trading_days) and trading_days[i] == d
    if on_trading_day and (t.hour, t.minute) < SESSION_CLOSE:
        return d
    j = bisect.bisect_right(trading_days, d)
    if j < len(trading_days):
        return trading_days[j]
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def earnings_sessions(rows, trading_days, shifted=False):
    return sorted({s for r in rows if (s := earnings_session(r[0], trading_days, shifted)) is not None})


def changed_sessions(rows, trading_days, shifted):
    """Filings whose earnings session would differ under the other time-base reading (expected: none)."""
    return [r[0] for r in rows
            if earnings_session(r[0], trading_days, shifted) != earnings_session(r[0], trading_days, not shifted)]


# ---------------------------------------------------------------- provider (test #29's, separate folder + budget)

def ensure_tbill_file(data=DATA, source=TB3MS_FROM):
    """Copy test #29's FRED TB3MS file into this test's folder once, so no new download is needed."""
    dest = data / "tb3ms.csv"
    if not dest.exists():
        data.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    return dest


def make_provider(data=DATA, budget=BUDGET, db=None):
    ensure_tbill_file(data)
    return w29.Provider(tickers=TICKERS, data=data, db=db, budget=budget)


# ---------------------------------------------------------------- free dry-run cost estimate

def estimate(samples_per_ticker=20, seed=32):
    """Prices sample 15:45 chain minutes and 1-2 week contract windows across 2020-2026 with the free cost endpoint.
    Buys nothing (metadata.get_cost only; the spent file is not touched)."""
    db = w29.Databento(BUDGET, DATA)
    prov = make_provider(db=db)
    days = prov.trading_days(w29.FIRST, w29.LAST)
    rng = random.Random(seed)
    out = {"chain_minute": {}, "contract_window": {}, "sample_days": {}}
    for t in TICKERS:
        by_year = {}
        for d in days:
            by_year.setdefault(d.year, []).append(d)
        picks = sorted(d for y in sorted(by_year) for d in rng.sample(by_year[y], 3))[:samples_per_ticker]
        chain_costs, window_costs = [], []
        for d in picks:
            start = datetime.combine(d, w29.DECIDE, NY)
            chain_costs.append(db.cost(f"{t}.OPT", "parent", start, datetime.combine(d, w29.DECIDE_END, NY)))
            spot = prov.close(t, d)
            fri = d + timedelta(days=(4 - d.weekday()) % 7 + 7)
            step = 5 if spot > 200 else (2.5 if spot > 50 else 1)
            strike = round(0.95 * spot / step) * step
            last = max(x for x in days if x <= fri) if fri <= days[-1] else days[-1]
            try:
                for root, a, b in w29.quote_segments(t, d, last):
                    window_costs.append(db.cost(w29.osi(root, fri, "P", strike), "raw_symbol", a, b))
            except RuntimeError as e:
                window_costs.append(None)
                print(json.dumps({"window_cost_error": str(e)[:160], "ticker": t, "day": d.isoformat()}))
        out["sample_days"][t] = [d.isoformat() for d in picks]
        out["chain_minute"][t] = [round(c, 6) for c in chain_costs]
        out["contract_window"][t] = [None if c is None else round(c, 6) for c in window_costs]
    return out, len(days), db.spent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--estimate", action="store_true", help="free Databento cost estimate (no purchase)")
    ap.add_argument("--earnings", action="store_true", help="fetch (free) and print the EDGAR earnings sessions")
    args = ap.parse_args()
    if args.earnings:
        prov = make_provider()
        days = prov.trading_days(w29.FIRST, w29.LAST)
        cal = calibrate()
        print(json.dumps({"calibration": cal}))
        for t in TICKERS:
            rows = fetch_earnings(t)
            print(json.dumps({"ticker": t, "filings": len(rows),
                              "alternative_reading_changes": changed_sessions(rows, days, cal["shifted"]),
                              "sessions": [[r[0], acceptance_ny(r[0], cal["shifted"]).isoformat(timespec="minutes"),
                                            str(earnings_session(r[0], days, cal["shifted"])), r[2]] for r in rows]},
                             indent=1))
    if args.estimate:
        out, n_days, spent = estimate()
        print(json.dumps({"trading_days": n_days, "spent_so_far_in_this_tests_budget": spent, **out}, indent=1))


if __name__ == "__main__":
    main()
