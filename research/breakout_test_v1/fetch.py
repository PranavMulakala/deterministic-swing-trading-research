"""Download daily bars for the pre-declared breakout test (output/BREAKOUT_TEST_PLAN_20260929.md). Read-only.

Universe: active, tradable US common stocks on NYSE, Nasdaq and NYSE American from Alpaca's asset list, minus
names that look like funds, trusts, SPACs, warrants, units or rights; plus SPY for the market filter.
Bars: Alpaca SIP daily, adjusted for splits and dividends, 2016-01-01 to 2026-09-28, 100 symbols per request.
Saves one gzip CSV per symbol under outputs/breakout_data/ (gitignored); finished symbols are skipped on rerun.

  PYTHONPATH=src:. .venv/bin/python -m research.breakout_test_v1.fetch
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
from urllib.request import ProxyHandler, Request, build_opener

from research.lite_paper_bot_v1.bot import credentials

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/breakout_data"
START, END = "2016-01-01", "2026-09-28T21:00:00Z"
EXCHANGES = {"NYSE", "NASDAQ", "AMEX"}
NOT_STOCKS = re.compile(r"\b(ETFS?|ETNS?|FUNDS?|TRUST|WARRANTS?|UNITS?|RIGHTS?|ACQUISITION|SPAC|ISHARES|"
                        r"PROSHARES|DIREXION|INDEX|NOTES?|DEPOSITARY SHARES? REPRESENTING|PREFERRED)\b", re.I)


def client():
    key, secret = credentials()
    opener = build_opener(ProxyHandler({}))

    def get(base, path, query):
        request = Request(base + path + "?" + urllib.parse.urlencode(query),
                          headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
        for attempt in range(8):
            try:
                with opener.open(request, timeout=120) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 500, 502, 503, 504) and attempt < 7:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise RuntimeError(f"HTTP {exc.code} on {path}") from None
            except OSError:
                if attempt == 7:
                    raise
                time.sleep(5 * (attempt + 1))
    return get


def universe(get):
    assets = get("https://paper-api.alpaca.markets", "/v2/assets", {"status": "active", "asset_class": "us_equity"})
    symbols = sorted(a["symbol"] for a in assets
                     if a["exchange"] in EXCHANGES and a["tradable"] and re.fullmatch(r"[A-Z]{1,5}", a["symbol"])
                     and not NOT_STOCKS.search(a.get("name") or ""))
    return sorted(set(symbols) | {"SPY"})


def fetch_batch(get, symbols):
    todo = [s for s in symbols if not (OUT / f"{s}.csv.gz").exists()]
    if not todo:
        return 0
    rows, token = {s: [] for s in todo}, None
    while True:
        query = {"symbols": ",".join(todo), "timeframe": "1Day", "feed": "sip", "adjustment": "all",
                 "start": START, "end": END, "limit": 10000}
        if token:
            query["page_token"] = token
        reply = get("https://data.alpaca.markets", "/v2/stocks/bars", query)
        for symbol, bars in (reply.get("bars") or {}).items():
            rows[symbol].extend(bars)
        token = reply.get("next_page_token")
        if not token:
            break
    for symbol, bars in rows.items():
        text = "date,open,high,low,close,volume\n" + "".join(
            f"{b['t'][:10]},{b['o']},{b['h']},{b['l']},{b['c']},{b['v']}\n" for b in bars)
        tmp = OUT / f"{symbol}.tmp"
        tmp.write_bytes(gzip.compress(text.encode()))
        tmp.replace(OUT / f"{symbol}.csv.gz")
    return len(rows)


def main():
    get = client()
    OUT.mkdir(parents=True, exist_ok=True)
    symbols = universe(get)
    (OUT / "universe.json").write_text(json.dumps(symbols))
    batches = [symbols[i:i + 100] for i in range(0, len(symbols), 100)]
    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for count in pool.map(lambda batch: fetch_batch(get, batch), batches):
            done += count
            print(json.dumps({"symbols_saved": done, "universe": len(symbols)}), flush=True)


if __name__ == "__main__":
    main()
