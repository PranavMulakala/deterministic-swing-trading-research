"""Download LITE call quotes from Databento for the pre-declared calls-on-dips test. Uses the owner's free credit.

Plan: output/LITE_CALLS_TEST_PLAN_20260929.md (committed before any download). For each trading day it pulls
LITE's option chain best bid/ask (OPRA.PILLAR, schema cbbo-1m) in two 1-minute windows: 10:05 ET (entry)
and 15:59 ET (12:59 on half days; the daily exit check). Rows are trimmed to calls expiring within 60 days
and strikes within 80-120% of LITE's price, and saved as one gzip CSV per day under outputs/lite_options_data/.

Hard limits: only this dataset, schema and symbol; the key is never printed; the run stops by itself once
the estimated billable volume reaches $10; finished days are skipped on rerun. --estimate asks Databento's
free cost endpoint for sample days and downloads nothing.

  PYTHONPATH=src:. .venv/bin/python -m research.lite_calls_test_v1.fetch_databento --estimate
  PYTHONPATH=src:. .venv/bin/python -m research.lite_calls_test_v1.fetch_databento --start 2022-01-03 --end 2026-09-28
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date, datetime, time as dtime, timedelta, timezone
import gzip
import io
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from research.spy_put_spread_backtest_v1.fetch_databento import NY, URL, Databento, api_key, trading_days

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/lite_options_data"
COST_URL = "https://hist.databento.com/v0/metadata.get_cost"
RECORD_BYTES, DOLLARS_PER_GIB, BUDGET_DOLLARS = 80, 2.0, 10.0
MAX_DTE, STRIKE_LO, STRIKE_HI = 60, 0.80, 1.20


class LiteDatabento(Databento):
    """Only LITE option cbbo-1m windows from OPRA.PILLAR, plus the free cost endpoint."""

    def _params(self, start, end):
        if not (timedelta(0) < end - start <= timedelta(minutes=2)):
            raise ValueError("Only short windows are allowed")
        return {"dataset": "OPRA.PILLAR", "symbols": "LITE.OPT", "stype_in": "parent", "schema": "cbbo-1m",
                "start": start.astimezone(timezone.utc).isoformat(), "end": end.astimezone(timezone.utc).isoformat()}

    def window(self, start, end):
        body = urllib.parse.urlencode({**self._params(start, end), "encoding": "csv", "compression": "none",
                                       "pretty_px": "true", "pretty_ts": "true", "map_symbols": "true"}).encode()
        attempts = 30  # Patient retries, as in the SPY fetcher, so a short Wi-Fi drop does not end the run.
        for attempt in range(attempts):
            request = urllib.request.Request(URL, data=body, method="POST", headers={
                "Authorization": self._auth, "Content-Type": "application/x-www-form-urlencoded"})
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    return response.read().decode()
            except urllib.error.HTTPError as exc:
                detail = exc.read(600).decode(errors="replace").replace(self._key, "[key]")
                if exc.code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                    time.sleep(min(60, 5 * (attempt + 1)))
                    continue
                raise RuntimeError(f"HTTP {exc.code}: {detail}") from None
            except OSError:
                if attempt == attempts - 1:
                    raise
                time.sleep(min(60, 5 * (attempt + 1)))

    def cost(self, start, end):
        body = urllib.parse.urlencode(self._params(start, end)).encode()
        request = urllib.request.Request(COST_URL, data=body, method="POST", headers={
            "Authorization": self._auth, "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=180) as response:
            return float(response.read().decode())


def parse_osi(symbol):
    """'LITE  261030C00975000' -> (expiration, 'C'/'P', strike)."""
    s = symbol.replace(" ", "")
    if not s.startswith("LITE") or len(s) != 19:
        return None
    return date(2000 + int(s[4:6]), int(s[6:8]), int(s[8:10])), s[10], int(s[11:19]) / 1000


def trim(rows, day, spot):
    kept = []
    for row in rows:
        info = parse_osi(row.get("symbol", ""))
        if not info or info[1] != "C" or not 0 < (info[0] - day).days <= MAX_DTE:
            continue
        if spot and not STRIKE_LO * spot <= info[2] <= STRIKE_HI * spot:
            continue
        try:
            bid, ask = float(row.get("bid_px_00") or 0), float(row.get("ask_px_00") or 0)
        except ValueError:
            continue
        kept.append((info, bid, ask, row))
    return kept


def spot_prices(start, end):
    """LITE's SIP 5-minute bar opens at 10:05 and closes at the last bar, from the history replay's cache."""
    from research.lite_dip_history_v1 import run
    from research.lite_paper_bot_v1.bot import credentials
    key, secret = credentials()
    closes = {r["date"]: r["close"] for r in run.cached(f"calendar_{run.FIRST}_{run.LAST}.json.gz", None) if r["open"] == "09:30"}
    sip = run.regular(run.history("sip", key, secret), closes)
    return {day: (next((o for c, o, *_ in bars if c == "10:05"), None), bars[-1][4] if bars else None)
            for day, bars in sip.items() if start.isoformat() <= day <= end.isoformat()}


def fetch_day(client, day, close, spot):
    out = OUT / str(day.year) / f"{day.isoformat()}.csv.gz"
    if out.exists():
        return None
    end_of_day = (datetime.combine(day, dtime.fromisoformat(close), NY) - timedelta(minutes=1)).time()
    windows = {"t1005": dtime(10, 5), "close": end_of_day}
    lines, records = [], 0
    for name, clock in windows.items():
        start = datetime.combine(day, clock, NY)
        rows = list(csv.DictReader(io.StringIO(client.window(start, start + timedelta(minutes=1)))))
        records += len(rows)
        for (exp, cp, strike), bid, ask, row in trim(rows, day, spot):
            lines.append([name, exp.isoformat(), cp, f"{strike:g}", f"{bid:.2f}", f"{ask:.2f}",
                          row.get("bid_sz_00", ""), row.get("ask_sz_00", ""), row.get("ts_recv", "")])
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    with gzip.open(tmp, "wt", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["window", "expiration", "type", "strike", "bid", "ask", "bid_size", "ask_size", "ts_recv"])
        writer.writerows(lines)
    tmp.replace(out)
    return {"date": day.isoformat(), "records": records, "kept": len(lines)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--start", default="2022-01-03")
    parser.add_argument("--end", default="2026-09-28")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be 1-16")
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    days = trading_days(start, end)
    client = LiteDatabento(api_key())
    if args.estimate:
        sample = days[:: max(1, len(days) // 12)]
        costs = []
        for day, close in sample:
            for clock in (dtime(10, 5), (datetime.combine(day, dtime.fromisoformat(close)) - timedelta(minutes=1)).time()):
                begin = datetime.combine(day, clock, NY)
                costs.append(client.cost(begin, begin + timedelta(minutes=1)))
        per_day = sum(costs) / len(sample)
        print(json.dumps({"trading_days": len(days), "sampled_days": len(sample),
                          "average_cost_per_day_usd": round(per_day, 5),
                          "estimated_total_usd": round(per_day * len(days), 2)}))
        return
    spots = spot_prices(start, end)
    progress = OUT / "progress.jsonl"
    OUT.mkdir(parents=True, exist_ok=True)
    spent = {"records": sum(json.loads(l)["records"] for l in progress.read_text().splitlines()) if progress.exists() else 0}
    todo = [(d, c) for d, c in days if not (OUT / str(d.year) / f"{d.isoformat()}.csv.gz").exists()]
    lock = threading.Lock()
    dollars = lambda: spent["records"] * RECORD_BYTES / 2**30 * DOLLARS_PER_GIB

    def work(item):
        with lock:
            if dollars() >= BUDGET_DOLLARS:
                return None
        day, close = item
        return fetch_day(client, day, close, (spots.get(day.isoformat()) or (None, None))[0])

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(work, todo):
            if result is None:
                continue
            with lock:
                spent["records"] += result["records"]
                with progress.open("a") as handle:
                    handle.write(json.dumps(result) + "\n")
            print(json.dumps({**result, "estimated_dollars_so_far": round(dollars(), 3)}), flush=True)
    if dollars() >= BUDGET_DOLLARS:
        print(json.dumps({"stopped": "budget guard", "estimated_dollars": round(dollars(), 2)}))


if __name__ == "__main__":
    main()
