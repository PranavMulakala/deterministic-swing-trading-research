"""Download monthly adjusted price history from Alpha Vantage into data/raw/<TICKER>.json.

The key is read from the owner-only .env.news (ALPHAVANTAGE_API_KEY) or the environment and is never
printed or written anywhere. Cached files are reused, so re-running only fetches what is missing.
Usage: python fetch.py VFIAX VTSNX ...
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "raw"
KEY_FILE = HERE.parents[1] / ".env.news"
URL = "https://www.alphavantage.co/query"


def api_key():
    if os.environ.get("ALPHAVANTAGE_API_KEY"):
        return os.environ["ALPHAVANTAGE_API_KEY"]
    for line in KEY_FILE.read_text().splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "ALPHAVANTAGE_API_KEY":
            return value.strip().strip('"')
    sys.exit("ALPHAVANTAGE_API_KEY not found")


def fetch(ticker, key):
    if ticker == "CPI":  # US CPI-U, monthly, for converting nominal returns to real (today's dollars)
        query = urllib.parse.urlencode({"function": "CPI", "interval": "monthly", "apikey": key})
    else:
        query = urllib.parse.urlencode({"function": "TIME_SERIES_MONTHLY_ADJUSTED", "symbol": ticker, "apikey": key})
    with urllib.request.urlopen(f"{URL}?{query}", timeout=30) as reply:
        return json.load(reply)


def main(tickers):
    RAW.mkdir(parents=True, exist_ok=True)
    key = api_key()
    for i, ticker in enumerate(tickers):
        path = RAW / f"{ticker}.json"
        if path.exists():
            print(f"{ticker}: cached")
            continue
        data = fetch(ticker, key)
        series = data.get("Monthly Adjusted Time Series") or {row["date"]: row for row in data.get("data", [])}
        if not series:
            # Error/limit messages from Alpha Vantage do not contain the key; show only the message keys.
            msg = {k: v for k, v in data.items() if k in ("Note", "Information", "Error Message")}
            print(f"{ticker}: no data -> {msg}")
            if "Note" in msg or "Information" in msg:
                break
            continue
        path.write_text(json.dumps(data))
        months = sorted(series)
        print(f"{ticker}: {len(months)} months {months[0]} .. {months[-1]}")
        if i < len(tickers) - 1:
            time.sleep(1.5)


if __name__ == "__main__":
    main(sys.argv[1:])
