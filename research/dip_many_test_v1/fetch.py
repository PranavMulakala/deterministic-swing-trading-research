"""Download Alpaca SIP 30-minute bars (regular session kept) for test #15's universes, Jan 3, 2022 - Sep 30, 2026.

  PYTHONPATH=src:. .venv/bin/python -m research.dip_many_test_v1.fetch

Read-only data keys (LITE paper account); places no orders. Cached per symbol in outputs/dip_many_data/ (gitignored),
fetched slowly with retries because the bar API rate-limits bursts.
"""
from __future__ import annotations

from datetime import datetime
import gzip
import json
from pathlib import Path
import time
from zoneinfo import ZoneInfo

import urllib.parse

from research.lite_dip_history_v1.run import DATA, fetch
from research.lite_paper_bot_v1.bot import credentials

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "outputs/dip_many_data"
HERE = Path(__file__).resolve().parent
NY = ZoneInfo("America/New_York")
START, END = "2022-01-03T00:00:00Z", "2026-10-01T00:00:00Z"


def paged_bars(symbol, key, secret, pause=0.32):
    """All 30-minute bars, retrying a failed page (not the whole symbol) with backoff; paced under ~190 requests/min."""
    query = {"timeframe": "30Min", "feed": "sip", "adjustment": "all", "sort": "asc", "limit": 10000,
             "start": START, "end": END}
    rows, token = [], None
    while True:
        if token:
            query["page_token"] = token
        for attempt in range(8):
            try:
                page = fetch(f"{DATA}/v2/stocks/{symbol}/bars?{urllib.parse.urlencode(query)}", key, secret)
                break
            except Exception:
                time.sleep(3 * (attempt + 1))
        else:
            raise RuntimeError(f"page failed 8 times for {symbol}")
        rows += page.get("bars") or []
        token = page.get("next_page_token")
        time.sleep(pause)
        if not token:
            return rows


def path_for(symbol):
    return CACHE / f"{symbol}_30min.json.gz"


def regular(rows):
    out = []
    for r in rows:
        t = datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(NY)
        m = t.hour * 60 + t.minute
        if 570 <= m < 960:
            out.append([t.date().isoformat(), m, r["o"], r["h"], r["l"], r["c"]])
    return out


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    u = json.loads((HERE / "universe.json").read_text())
    symbols = sorted({r["symbol"] for r in u["main"]} | set(u["hindsight"]) | {"SPY"})
    key, secret = credentials()
    done, failed = 0, []
    for s in symbols:
        if path_for(s).exists():
            done += 1
            continue
        for attempt in range(5):
            try:
                rows = regular(paged_bars(s, key, secret))
                with gzip.open(path_for(s), "wt") as f:
                    json.dump(rows, f)
                done += 1
                break
            except Exception as e:
                err = f"{type(e).__name__}: {str(e)[:80]}"
                time.sleep(10 * (attempt + 1))
        else:
            failed.append([s, err])
        if done % 10 == 0:
            print(json.dumps({"done": done, "of": len(symbols)}), flush=True)
    print(json.dumps({"done": done, "of": len(symbols), "failed": failed}))


if __name__ == "__main__":
    main()
