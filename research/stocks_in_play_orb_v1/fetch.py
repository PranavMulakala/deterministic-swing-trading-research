"""Test #21 data: Alpaca SIP bars for the "Stocks in Play" opening-range breakout
(plan: output/STOCKS_IN_PLAY_ORB_TEST_PLAN_20261005.md). Read-only data keys (LITE paper account); places no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.stocks_in_play_orb_v1.fetch [--pilot]

0. SPY daily bars (dividend-adjusted) for the benchmark and the trading calendar.
1. Daily bars, raw and split-adjusted, Nov 16, 2015 - Oct 2, 2026, for the 5,259 stocks on disk (the folder also
   holds two bitcoin price files, saved there on Sep 30; they aren't stocks and are skipped).
2. The 9:30-9:35 bar (raw) each day for every stock passing the daily filters that day or within its next 14 trading
   days (relative volume needs 14 days of history). The price filter here uses the daily open > $4.50; the exact $5
   rule is applied later to the 9:30 bar's own open.
3. Full regular-session 5-minute bars (raw) for each day's 25 highest relative volumes under the exact rules
   (the test trades the top 20; 5 spare).

Stored under outputs/orb_play_data/ (gitignored). Resumable: finished files are skipped, a day file missing any stock
it now needs is topped up, and a stage that ends with failures stops the run so a rerun can finish it first. Paced
under Alpaca's free-plan limit (200 requests/minute) on 3 threads; failed pages are retried with backoff.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
import json
import threading
import time
from urllib.error import HTTPError, URLError
import urllib.parse
from zoneinfo import ZoneInfo

from research.breakout_test_v1.backtest import DATA as STOCK_DIR
from research.lite_dip_history_v1.run import DATA, fetch
from research.lite_paper_bot_v1.bot import credentials
from research.stocks_in_play_orb_v1.data import base_dir, calendar, load, metric_table, need_by_day, save, selections

NY, UTC = ZoneInfo("America/New_York"), ZoneInfo("UTC")
FIRST, LAST, TEST_START = "2015-11-16", "2026-10-02", "2016-01-04"
SLACK_PRICE, CHUNK, SPARE, BATCH = 4.50, 400, 25, 50
PILOT = ["NVDA", "AAPL", "LITE", "TSLA", "AMC", "GME"]
NOT_STOCKS = {"SPY", "BTCUSD", "BTCUSD_BITSTAMP"}                 # SPY is fetched separately as the benchmark


class Client:
    def __init__(self, per_minute=170):
        self.key, self.secret = credentials()
        self.gap, self.next, self.lock, self.requests = 60.0 / per_minute, 0.0, threading.Lock(), 0

    def get(self, url):
        for attempt in range(10):
            with self.lock:
                t = max(time.monotonic(), self.next)
                self.next = t + self.gap
                self.requests += 1
            time.sleep(max(0.0, t - time.monotonic()))
            try:
                return fetch(url, self.key, self.secret)
            except HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504):
                    raise
            except (URLError, OSError):
                pass
            time.sleep(min(60, 2 ** attempt))
        raise RuntimeError(f"failed 10 times: {url[:150]}")

    def bars(self, symbols, timeframe, start, end, adjustment):
        q = {"symbols": ",".join(symbols), "timeframe": timeframe, "feed": "sip", "adjustment": adjustment,
             "sort": "asc", "limit": 10000, "start": start, "end": end}
        out, token = {}, None
        while True:
            if token:
                q["page_token"] = token
            page = self.get(f"{DATA}/v2/stocks/bars?{urllib.parse.urlencode(q)}")
            for s, rows in (page.get("bars") or {}).items():
                out.setdefault(s, []).extend(rows)
            token = page.get("next_page_token")
            if not token:
                return out


def utc(day, minute):
    d = date.fromisoformat(day)
    return datetime(d.year, d.month, d.day, minute // 60, minute % 60, tzinfo=NY).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def minute_et(t):
    x = datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(NY)
    return x.hour * 60 + x.minute


def ohlcv(r):
    return [r["o"], r["h"], r["l"], r["c"], r["v"]]


def pool(client, work, items, label):
    done, failed, start = 0, [], time.monotonic()
    with ThreadPoolExecutor(3) as ex:
        futures = {ex.submit(work, item): item for item in items}
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as e:                                    # keep going; a rerun retries what failed
                failed.append([str(futures[fut])[:40], f"{type(e).__name__}: {str(e)[:100]}"])
            done += 1
            if done % 50 == 0 or done == len(items):
                print(json.dumps({"stage": label, "done": done, "of": len(items), "failed": len(failed),
                                  "requests": client.requests, "minutes": round((time.monotonic() - start) / 60, 1)}),
                      flush=True)
    if failed:
        print(json.dumps({"stage": label, "failed": failed[:20]}), flush=True)
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--first-day", default=TEST_START)
    ap.add_argument("--last-day", default=LAST)
    args = ap.parse_args()
    base, client = base_dir(args.pilot), Client()
    symbols = PILOT if args.pilot else sorted(p.name[:-7] for p in STOCK_DIR.glob("*.csv.gz") if p.name[:-7] not in NOT_STOCKS)
    spy_path = base / "SPY_all.json.gz"
    if not spy_path.exists():
        rows = client.bars(["SPY"], "1Day", f"{FIRST}T00:00:00Z", f"{LAST}T23:59:00Z", "all")["SPY"]
        save(spy_path, {"date": [r["t"][:10] for r in rows], "bars": [ohlcv(r) for r in rows]})
    cal = calendar(base)

    def daily(batch):
        got = {a: client.bars(batch, "1Day", f"{FIRST}T00:00:00Z", f"{LAST}T23:59:00Z", a) for a in ("raw", "split")}
        for s in batch:
            raw = {r["t"][:10]: ohlcv(r) for r in got["raw"].get(s, [])}
            spl = {r["t"][:10]: ohlcv(r) for r in got["split"].get(s, [])}
            days = sorted(set(raw) & set(spl))
            save(base / "daily" / f"{s}.json.gz", {"date": days, "raw": [raw[d] for d in days],
                                                    "split": [spl[d] for d in days]})

    todo = [s for s in symbols if not (base / "daily" / f"{s}.json.gz").exists()]
    if pool(client, daily, [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)], "1 daily"):
        raise SystemExit("stage 1 incomplete: rerun to retry")
    table = metric_table(base, symbols, cal)
    need = need_by_day(table, cal, args.first_day, SLACK_PRICE)
    span = [g for g, d in enumerate(cal) if d <= args.last_day and need[g]]
    print(json.dumps({"stage": "2 plan", "days": len(span), "symbol_days": sum(len(need[g]) for g in span),
                      "requests_about": sum(-(-len(need[g]) // CHUNK) for g in span)}), flush=True)

    def have(path, key):
        return set(load(path)[key]) if path.exists() else set()

    def opening(g):
        day = cal[g]
        path = base / "open5" / f"{day}.json.gz"
        old = load(path) if path.exists() else {"requested": [], "bars": {}}
        syms, found = sorted(need[g] - set(old["requested"])), dict(old["bars"])
        for i in range(0, len(syms), CHUNK):
            for s, rows in client.bars(syms[i:i + CHUNK], "5Min", utc(day, 570), utc(day, 574), "raw").items():
                for r in rows:
                    if minute_et(r["t"]) == 570:
                        found[s] = ohlcv(r)
        save(path, {"requested": sorted(set(old["requested"]) | need[g]), "bars": found})

    todo = [g for g in span if need[g] - have(base / "open5" / f"{cal[g]}.json.gz", "requested")]
    failed = pool(client, opening, todo, "2 open5")
    if failed:
        raise SystemExit("stage 2 incomplete: rerun to retry")
    picks = selections(base, table, cal, SPARE, args.first_day)

    def full_day(day):
        path = base / "day5" / f"{day}.json.gz"
        old = load(path) if path.exists() else {"symbols": [], "bars": {}}
        syms, out = [p[0] for p in picks[day] if p[0] not in old["symbols"]], dict(old["bars"])
        for s, rows in client.bars(syms, "5Min", utc(day, 570), utc(day, 955), "raw").items():
            out[s] = [[minute_et(r["t"])] + ohlcv(r) for r in rows if 570 <= minute_et(r["t"]) < 960]
        save(path, {"symbols": sorted(set(old["symbols"]) | set(syms)), "bars": out})

    days = [d for d in picks if d <= args.last_day and picks[d]
            and {p[0] for p in picks[d]} - have(base / "day5" / f"{d}.json.gz", "symbols")]
    failed = pool(client, full_day, days, "3 day5")
    print(json.dumps({"finished": not failed, "requests": client.requests}), flush=True)


if __name__ == "__main__":
    main()
