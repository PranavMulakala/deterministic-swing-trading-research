"""Download BTC/USD daily bars from Bitstamp's free public API, the feed the video's TradingView chart used.

  PYTHONPATH=src:. .venv/bin/python -m research.sma50_test_v1.fetch_bitstamp

Alpaca's crypto history only starts in 2021, so this is the only way to replay the video's May 2015 window.
Saves outputs/breakout_data/BTCUSD_BITSTAMP.csv.gz (gitignored). Read-only, no key.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
import time
import urllib.parse
from urllib.request import ProxyHandler, Request, build_opener

from research.breakout_test_v1.fetch import OUT

URL = "https://www.bitstamp.net/api/v2/ohlc/btcusd/"


def main():
    opener, bars = build_opener(ProxyHandler({})), {}
    start = int(datetime(2014, 1, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(2026, 9, 29, tzinfo=timezone.utc).timestamp())
    while start < end:
        query = urllib.parse.urlencode({"step": 86400, "limit": 1000, "start": start})
        with opener.open(Request(f"{URL}?{query}", headers={"User-Agent": "research"}), timeout=60) as response:
            ohlc = json.load(response)["data"]["ohlc"]
        if not ohlc:
            break
        for b in ohlc:
            bars[int(b["timestamp"])] = b
        start = max(bars) + 86400
        time.sleep(1)
    rows = [bars[t] for t in sorted(bars) if t < end]
    day = lambda t: datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%d")
    lines = ["date,open,high,low,close,volume"] + [
        f"{day(b['timestamp'])},{b['open']},{b['high']},{b['low']},{b['close']},{b['volume']}" for b in rows]
    (OUT / "BTCUSD_BITSTAMP.csv.gz").write_bytes(gzip.compress(("\n".join(lines) + "\n").encode()))
    print(json.dumps({"bars": len(rows), "first": day(rows[0]["timestamp"]), "last": day(rows[-1]["timestamp"])}))


if __name__ == "__main__":
    main()
