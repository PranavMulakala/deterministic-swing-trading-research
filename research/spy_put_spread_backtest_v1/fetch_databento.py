"""Download SPY option quotes from Databento for the bull put spread backtest. Uses the owner's free credit.

Owner approval (2026-09-28): "approve both" = 2013-04-01 through 2025-12-31, up to $64 of the $125 free
credit (expected about $6.50). For each trading day it pulls the whole SPY option chain's consolidated best
bid/ask (OPRA.PILLAR, schema cbbo-1m) in two 1-minute windows: 10:30 ET (decision time) and the session
close (16:00 ET, or 13:00 on half days). Rows are trimmed to expirations within 70 days and strikes within
70-115% of the at-the-money strike, then saved as one gzip CSV per day under outputs/spy_options_data/.

Hard limits: only this dataset/schema/symbol; the key is never printed; the run stops by itself once the
estimated billable volume reaches $20 (80 bytes per record at $2/GiB); finished days are skipped on rerun.

  PYTHONPATH=src:. .venv/bin/python -m research.spy_put_spread_backtest_v1.fetch_databento --days 2022-06-13,2024-08-05
  PYTHONPATH=src:. .venv/bin/python -m research.spy_put_spread_backtest_v1.fetch_databento --start 2013-04-01 --end 2025-12-31
"""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import io
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/spy_options_data"
KEY_FILE = ROOT / ".env.databento"
URL = "https://hist.databento.com/v0/timeseries.get_range"
RECORD_BYTES, DOLLARS_PER_GIB, BUDGET_DOLLARS = 80, 2.0, 20.0
MAX_DTE, STRIKE_LO, STRIKE_HI = 70, 0.70, 1.15


def api_key(path=KEY_FILE):
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise PermissionError("Owner-only .env.databento required")
    for line in path.read_text(encoding="utf-8").splitlines():
        name, _, value = line.strip().partition("=")
        if name.strip() == "DATABENTO_API_KEY" and value.strip():
            return value.strip().strip("\"'")
    raise ValueError("DATABENTO_API_KEY missing")


class Databento:
    """Only SPY option cbbo-1m windows from OPRA.PILLAR can be requested."""

    def __init__(self, key):
        self._key = key
        self._auth = "Basic " + base64.b64encode((key + ":").encode()).decode()

    def window(self, start, end):
        if not (timedelta(0) < end - start <= timedelta(minutes=2)):
            raise ValueError("Only short windows are allowed")
        body = urllib.parse.urlencode({
            "dataset": "OPRA.PILLAR", "symbols": "SPY.OPT", "stype_in": "parent", "schema": "cbbo-1m",
            "start": start.astimezone(timezone.utc).isoformat(), "end": end.astimezone(timezone.utc).isoformat(),
            "encoding": "csv", "compression": "none", "pretty_px": "true", "pretty_ts": "true",
            "map_symbols": "true"}).encode()
        for attempt in range(5):
            request = urllib.request.Request(URL, data=body, method="POST", headers={
                "Authorization": self._auth, "Content-Type": "application/x-www-form-urlencoded"})
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    return response.read().decode()
            except urllib.error.HTTPError as exc:
                detail = exc.read(600).decode(errors="replace").replace(self._key, "[key]")
                if exc.code in (429, 500, 502, 503, 504) and attempt < 4:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise RuntimeError(f"HTTP {exc.code}: {detail}") from None
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(3 * (attempt + 1))


def parse_osi(symbol):
    """'SPY   240805P00500000' -> (expiration, 'P'/'C', strike)."""
    s = symbol.replace(" ", "")
    if not s.startswith("SPY") or len(s) != 18:
        return None
    return date(2000 + int(s[3:5]), int(s[5:7]), int(s[7:9])), s[9], int(s[10:18]) / 1000


def trim(rows, day):
    """Keep expirations <= 70 days and strikes 70-115% of the at-the-money strike (put-call mids closest)."""
    parsed = []
    for row in rows:
        info = parse_osi(row.get("symbol", ""))
        try:
            bid, ask = float(row.get("bid_px_00") or 0), float(row.get("ask_px_00") or 0)
        except ValueError:
            continue
        if info and (info[0] - day).days <= MAX_DTE:
            parsed.append((info, bid, ask, row))
    near = min((p[0][0] for p in parsed), default=None)
    mids = {}
    for (exp, cp, strike), bid, ask, _ in parsed:
        if exp == near and bid > 0 and ask >= bid:
            mids.setdefault(strike, {})[cp] = (bid + ask) / 2
    pairs = [(abs(v["C"] - v["P"]), k) for k, v in mids.items() if "C" in v and "P" in v]
    atm = min(pairs)[1] if pairs else None
    kept = [p for p in parsed if atm is None or STRIKE_LO * atm <= p[0][2] <= STRIKE_HI * atm]
    return kept, atm


def trading_days(start, end):
    from research.lite_volume_rebound_v1.refresh import client_from_local_keys
    rows = client_from_local_keys()._request("GET", "/v2/calendar",
                                             query={"start": start.isoformat(), "end": end.isoformat()})
    return [(date.fromisoformat(r["date"]), r["close"]) for r in rows]


def fetch_day(client, day, close):
    out = OUT / str(day.year) / f"{day.isoformat()}.csv.gz"
    if out.exists():
        return None
    windows = {"t1030": datetime.combine(day, dtime(10, 30), NY),
               "close": datetime.combine(day, dtime.fromisoformat(close), NY)}
    lines, records, columns = [], 0, None
    for name, start in windows.items():
        text = client.window(start, start + timedelta(minutes=1))
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        columns = columns or reader.fieldnames
        records += len(rows)
        kept, atm = trim(rows, day)
        for (exp, cp, strike), bid, ask, row in kept:
            lines.append([name, exp.isoformat(), cp, f"{strike:g}", f"{bid:.2f}", f"{ask:.2f}",
                          row.get("bid_sz_00", ""), row.get("ask_sz_00", ""), row.get("ts_recv", "")])
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    with gzip.open(tmp, "wt", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["window", "expiration", "type", "strike", "bid", "ask", "bid_size", "ask_size", "ts_recv"])
        writer.writerows(lines)
    tmp.replace(out)
    return {"date": day.isoformat(), "records": records, "kept": len(lines), "columns": columns}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be 1-16")
    if args.days:
        wanted = {date.fromisoformat(d) for d in args.days.split(",")}
        span = trading_days(min(wanted), max(wanted))
        days = [(d, c) for d, c in span if d in wanted]
    else:
        days = trading_days(date.fromisoformat(args.start), date.fromisoformat(args.end))
    client = Databento(api_key())
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
        return fetch_day(client, *item)

    # Databento answers each 1-minute window in 15-60 s regardless of size, so days run in parallel.
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(work, todo):
            if result is None:
                continue
            with lock:
                spent["records"] += result["records"]
                with progress.open("a") as handle:
                    handle.write(json.dumps({k: v for k, v in result.items() if k != "columns"}) + "\n")
            print(json.dumps({**{k: v for k, v in result.items() if k != "columns"},
                              "estimated_dollars_so_far": round(dollars(), 3),
                              **({"columns": result["columns"]} if args.days else {})}), flush=True)
    if dollars() >= BUDGET_DOLLARS:
        print(json.dumps({"stopped": "budget guard", "estimated_dollars": round(dollars(), 2)}))


if __name__ == "__main__":
    main()
