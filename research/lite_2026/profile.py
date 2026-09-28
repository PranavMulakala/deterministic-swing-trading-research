"""Read-only exploratory snapshot; no strategy simulation or broker orders.

Run from the repo: PYTHONPATH=src .venv/bin/python research/lite_2026/profile.py
Use --refresh to download again. Cached snapshots contain public market data,
news metadata, and no account identifiers or credentials.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, time, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import mean, median
from zoneinfo import ZoneInfo

from swingbot.alpaca_paper import AlpacaPaperClient, AlpacaPaperError
from swingbot.paper_cli import _load_env

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / "snapshot.json"
NY = ZoneInfo("America/New_York")
SYMBOLS = ["LITE", "COHR", "CIEN", "AAOI", "FN", "SPY", "QQQ"]
END = "2026-09-06T00:00:00Z"


def pages(client, path, query, field):
    token = None
    seen = set()
    for _ in range(100):
        response = client._request("GET", path, data_api=True,
                                   query={**query, **({"page_token": token} if token else {})})
        yield response[field]
        token = response.get("next_page_token")
        if not token:
            return
        if token in seen:
            raise ValueError("Repeated pagination token")
        seen.add(token)
    raise ValueError("Pagination exceeded bounded request limit; snapshot incomplete")


def fetch_bars(client, symbols, timeframe, start):
    result = {symbol: [] for symbol in symbols}
    query = dict(symbols=",".join(symbols), timeframe=timeframe, start=start,
                 end=END, feed="iex", adjustment="all", sort="asc", limit=10000)
    for page in pages(client, "/v2/stocks/bars", query, "bars"):
        for symbol, rows in page.items():
            if symbol not in result:
                raise ValueError("Unexpected symbol")
            result[symbol].extend(rows)
    for rows in result.values():
        rows.sort(key=lambda r: r["t"])
        if len({row["t"] for row in rows}) != len(rows):
            raise ValueError("Duplicate bar timestamp")
        for row in rows:
            values = [float(row[key]) for key in ("o", "h", "l", "c")]
            if not all(math.isfinite(value) and value > 0 for value in values):
                raise ValueError("Nonfinite or nonpositive price")
            o, h, low, c = values
            if not low <= min(o, c) <= max(o, c) <= h:
                raise ValueError("Inconsistent OHLC")
    return result


def fetch():
    _load_env(ROOT / ".env")
    client = AlpacaPaperClient(os.environ.get("ALPACA_PAPER_API_KEY", ""),
                               os.environ.get("ALPACA_PAPER_API_SECRET", ""))
    daily = fetch_bars(client, SYMBOLS, "1Day", "2025-12-01T00:00:00Z")
    intraday = fetch_bars(client, ["LITE"], "5Min", "2026-01-01T00:00:00Z")
    calendar = client._request("GET", "/v2/calendar",
                               query={"start": "2026-01-01", "end": "2026-09-04"})
    articles = []
    news_status = "historical_endpoint_access_confirmed"
    try:
        for page in pages(client, "/v1beta1/news",
                          dict(symbols="LITE", start="2026-01-01T00:00:00Z", end=END,
                               sort="asc", limit=50, include_content="false"), "news"):
            for article in page:
                # Retain provenance and revision times; not the article text.
                articles.append({k: article.get(k) for k in
                                 ("id", "created_at", "updated_at", "source", "url", "symbols")})
    except AlpacaPaperError as exc:
        news_status = "unavailable_or_incomplete: " + str(exc)
    return dict(fetched_at=datetime.now(timezone.utc).isoformat(),
                start="2026-01-01", through="2026-09-04", feed="iex",
                adjustment="all", daily=daily, intraday=intraday,
                calendar=calendar, news_status=news_status, news=articles)


def percent(value):
    return round(value * 100, 3)


def describe_daily(rows):
    prior = [row for row in rows if row["t"][:10] < "2026-01-01"]
    year = [row for row in rows if "2026-01-01" <= row["t"][:10] <= "2026-09-04"]
    if not prior or not year:
        return {"error": "insufficient coverage"}
    return dict(sessions=len(year), last_date=year[-1]["t"][:10],
                adjusted_close_change_ytd_pct=percent(year[-1]["c"] / prior[-1]["c"] - 1),
                median_daily_bar_range_pct=percent(median((r["h"]-r["l"])/r["o"] for r in year)),
                range_note="IEX daily-bar range, not necessarily regular-hours-only")


def describe_lite(snapshot):
    grouped = defaultdict(dict)
    for row in snapshot["intraday"]["LITE"]:
        dt = datetime.fromisoformat(row["t"].replace("Z", "+00:00")).astimezone(NY)
        if time(9, 30) <= dt.time() < time(16):
            grouped[dt.date().isoformat()][dt.hour * 60 + dt.minute] = row
    excluded = Counter()
    observations = []
    for session in snapshot["calendar"]:
        if session["open"] != "09:30" or session["close"] != "16:00":
            excluded["shortened_or_nonstandard_session"] += 1
            continue
        bars = grouped.get(session["date"], {})
        if any(key not in bars for key in (570, 575, 580, 585, 590, 595, 600, 955)):
            excluded["missing_open_early_or_close_bar"] += 1
            continue
        if len(bars) < math.ceil(78 * 0.9):
            excluded["less_than_90_percent_bar_coverage"] += 1
            continue
        opening = bars[570]["o"]
        early_low = min(bars[key]["l"] for key in range(570, 600, 5))
        later_high = max(row["h"] for key, row in bars.items() if key >= 600)
        observations.append(dict(date=session["date"],
                                 early_drop_pct=100 * (early_low / opening - 1),
                                 recovered_open=later_high >= opening,
                                 ten_to_close_pct=percent(bars[955]["c"] / bars[600]["o"] - 1)))
    selected = [row for row in observations if row["early_drop_pct"] <= -1.0]
    def stats(rows):
        values = [r["ten_to_close_pct"] for r in rows]
        return dict(n=len(rows), recovered_open_pct=round(100*sum(r["recovered_open"] for r in rows)/len(rows), 2),
                    mean_ten_to_close_pct=round(mean(values), 3),
                    median_ten_to_close_pct=round(median(values), 3),
                    positive_ten_to_close_pct=round(100*sum(v>0 for v in values)/len(values), 2),
                    worst_ten_to_close_pct=min(values)) if rows else {"n": 0}
    return dict(calendar_sessions=len(snapshot["calendar"]), qualified_sessions=len(observations),
                excluded=dict(excluded), early_drop_at_least_one_pct=stats(selected),
                by_month={month: stats([r for r in selected if r["date"][:7] == month])
                          for month in sorted({r["date"][:7] for r in observations})},
                observations=observations)


def summarize(snapshot):
    unique = {str(article["id"]): article for article in snapshot["news"]}
    return dict(exploratory=True, feed=snapshot["feed"], through=snapshot["through"],
                snapshot_sha256=hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
                selected_cohort={s: describe_daily(rows) for s, rows in snapshot["daily"].items()},
                lite=describe_lite(snapshot),
                news=dict(status=snapshot["news_status"], unique_article_ids=len(unique),
                          updated_after_creation=sum(a["updated_at"] != a["created_at"] for a in unique.values()),
                          sources=sorted({a["source"] for a in unique.values() if a["source"]}),
                          note="Current historical versions; original article text and first delivery time not established."))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.refresh or not SNAPSHOT.exists():
        SNAPSHOT.write_text(json.dumps(fetch(), sort_keys=True, separators=(",", ":")) + "\n")
    result = summarize(json.loads(SNAPSHOT.read_text()))
    (HERE / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    result["lite"].pop("observations")
    print(json.dumps(result, indent=2))
