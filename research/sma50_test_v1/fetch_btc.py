"""Download BTC/USD daily bars from Alpaca's free crypto data for the Bitcoin code check (owner approved 2026-09-30).

  PYTHONPATH=src:. .venv/bin/python -m research.sma50_test_v1.fetch_btc

Saves outputs/breakout_data/BTCUSD.csv.gz (gitignored) in the same format as the stock files. Read-only.
"""
from __future__ import annotations

import gzip
import json

from research.breakout_test_v1.fetch import OUT, client


def main():
    get, rows, token = client(), [], None
    while True:
        query = {"symbols": "BTC/USD", "timeframe": "1Day", "start": "2015-01-01T00:00:00Z",
                 "end": "2026-09-29T00:00:00Z", "limit": 10000}
        if token:
            query["page_token"] = token
        page = get("https://data.alpaca.markets", "/v1beta3/crypto/us/bars", query)
        rows += page["bars"].get("BTC/USD", [])
        token = page.get("next_page_token")
        if not token:
            break
    lines = ["date,open,high,low,close,volume"] + [f"{b['t'][:10]},{b['o']},{b['h']},{b['l']},{b['c']},{b['v']}" for b in rows]
    (OUT / "BTCUSD.csv.gz").write_bytes(gzip.compress(("\n".join(lines) + "\n").encode()))
    print(json.dumps({"bars": len(rows), "first": rows[0]["t"] if rows else None, "last": rows[-1]["t"] if rows else None}))


if __name__ == "__main__":
    main()
