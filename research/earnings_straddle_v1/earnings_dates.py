"""Fetch earnings report dates and timing for test #7's fixed stock list (Alpha Vantage EARNINGS, owner's free key).

  PYTHONPATH=src:. .venv/bin/python -m research.earnings_straddle_v1.earnings_dates

Writes research/earnings_straddle_v1/events.json: {symbol: [[report_date, "pre"|"post"], ...]} for 2012-01-01..2026-09-30.
20 calls, paced 13 s apart (free key: 5 a minute, about 25 a day). Dates only; no prices.
"""
from __future__ import annotations

import json
from pathlib import Path
import time
import urllib.parse
from urllib.request import ProxyHandler, Request, build_opener

from research.lite_paper_bot_v1.news import URL, api_key

SYMBOLS = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "NFLX", "AMD", "INTC",
           "MU", "ORCL", "CRM", "ADBE", "AVGO", "QCOM", "CSCO", "JPM", "BAC", "XOM"]
FIRST, LAST = "2012-01-01", "2026-09-30"
OUT = Path(__file__).resolve().parent / "events.json"
TIMING = {"pre-market": "pre", "post-market": "post"}


def main():
    key, events, skipped = api_key(), {}, {}
    for i, symbol in enumerate(SYMBOLS):
        if i:
            time.sleep(13)
        query = urllib.parse.urlencode({"function": "EARNINGS", "symbol": symbol, "apikey": key})
        with build_opener(ProxyHandler({})).open(Request(f"{URL}?{query}", headers={"User-Agent": "research/1"}),
                                                 timeout=30) as reply:
            rows = json.loads(reply.read()).get("quarterlyEarnings")
        if not isinstance(rows, list):
            raise SystemExit(f"Alpha Vantage refused {symbol} (daily limit?); nothing written")
        inside = [r for r in rows if FIRST <= r.get("reportedDate", "") <= LAST]
        events[symbol] = sorted([r["reportedDate"], TIMING[r.get("reportTime")]]
                                for r in inside if r.get("reportTime") in TIMING)
        skipped[symbol] = len(inside) - len(events[symbol])
        print(symbol, len(events[symbol]), "events,", skipped[symbol], "skipped (timing unknown)")
    OUT.write_text(json.dumps(events, indent=1) + "\n")
    print("total", sum(map(len, events.values())), "events; skipped", sum(skipped.values()))


if __name__ == "__main__":
    main()
