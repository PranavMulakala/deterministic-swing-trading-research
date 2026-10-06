"""Test #17 benchmarks: Alpaca SIP daily bars (adjustment=all, dividends included) for SMH, SPY and QQQ, 2016 to the
last stock date on disk (Sep 28, 2026). Read-only; cached in outputs/momentum_lite_like_data/ (gitignored).

  PYTHONPATH=src:. .venv/bin/python -m research.momentum_lite_like_v1.fetch_etfs
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "outputs/momentum_lite_like_data"
ETFS, END = ["SMH", "SPY", "QQQ"], "2026-09-28"


def path_for(symbol):
    return CACHE / f"{symbol}_daily.json.gz"


def main():
    from research.lite_dip_history_v1.run import DATA, fetch
    from research.lite_paper_bot_v1.bot import credentials
    key, secret = credentials()
    CACHE.mkdir(parents=True, exist_ok=True)
    for s in ETFS:
        q = {"timeframe": "1Day", "feed": "sip", "adjustment": "all", "sort": "asc", "limit": 10000,
             "start": "2016-01-01T00:00:00Z", "end": f"{END}T23:59:00Z"}
        rows, token = [], None
        while True:
            if token:
                q["page_token"] = token
            page = fetch(f"{DATA}/v2/stocks/{s}/bars?{urllib.parse.urlencode(q)}", key, secret)
            rows += page.get("bars") or []
            token = page.get("next_page_token")
            if not token:
                break
        out = {"date": [r["t"][:10] for r in rows], "open": [r["o"] for r in rows], "high": [r["h"] for r in rows],
               "low": [r["l"] for r in rows], "close": [r["c"] for r in rows], "volume": [r["v"] for r in rows]}
        with gzip.open(path_for(s), "wt") as f:
            json.dump(out, f)
        print(s, len(rows), out["date"][0], out["date"][-1])


if __name__ == "__main__":
    main()
