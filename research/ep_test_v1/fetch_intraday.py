"""Download Alpaca SIP 5-minute bars (adjustment=all, matching the daily data) for test #16's candidate days.

  PYTHONPATH=src:. .venv/bin/python -m research.ep_test_v1.fetch_intraday

One multi-symbol request per date (all of that day's candidates), retried per page, paced under the rate limit.
Read-only data keys (LITE paper account); places no orders. Regular session only, stored per date as
outputs/ep_data/intraday/<date>.json.gz = {symbol: [[minute_of_day_ET, open, high, low, close, volume], ...]}.
Resumable: dates already saved are skipped.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import gzip
import json
import time
import urllib.parse
from zoneinfo import ZoneInfo

from research.ep_test_v1.candidates import OUT_DIR
from research.lite_dip_history_v1.run import DATA, fetch
from research.lite_paper_bot_v1.bot import credentials

NY = ZoneInfo("America/New_York")
INTRADAY = OUT_DIR / "intraday"


def path_for(day):
    return INTRADAY / f"{day}.json.gz"


def regular(rows):
    out = []
    for r in rows:
        t = datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(NY)
        m = t.hour * 60 + t.minute
        if 570 <= m < 960:
            out.append([m, r["o"], r["h"], r["l"], r["c"], r["v"]])
    return out


def day_bars(day, symbols, key, secret, pause=0.35):
    nxt = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    query = {"symbols": ",".join(symbols), "timeframe": "5Min", "feed": "sip", "adjustment": "all", "sort": "asc",
             "limit": 10000, "start": f"{day}T00:00:00Z", "end": f"{nxt}T00:00:00Z"}
    found, token = {s: [] for s in symbols}, None
    while True:
        if token:
            query["page_token"] = token
        for attempt in range(8):
            try:
                page = fetch(f"{DATA}/v2/stocks/bars?{urllib.parse.urlencode(query)}", key, secret)
                break
            except Exception:
                time.sleep(3 * (attempt + 1))
        else:
            raise RuntimeError(f"page failed 8 times for {day}")
        for sym, rows in (page.get("bars") or {}).items():
            found.setdefault(sym, []).extend(rows)
        token = page.get("next_page_token")
        time.sleep(pause)
        if not token:
            return {s: regular(rows) for s, rows in found.items()}


def main():
    INTRADAY.mkdir(parents=True, exist_ok=True)
    by_date = json.loads((OUT_DIR / "candidates.json").read_text())["by_date"]
    key, secret = credentials()
    done, failed = 0, []
    for day, symbols in by_date.items():
        if path_for(day).exists():
            done += 1
            continue
        try:
            bars = day_bars(day, symbols, key, secret)
            with gzip.open(path_for(day), "wt") as f:
                json.dump(bars, f)
            done += 1
        except Exception as e:
            failed.append([day, f"{type(e).__name__}: {str(e)[:80]}"])
        if done % 100 == 0:
            print(json.dumps({"dates_done": done, "of": len(by_date)}), flush=True)
    print(json.dumps({"dates_done": done, "of": len(by_date), "failed": failed}), flush=True)


if __name__ == "__main__":
    main()
