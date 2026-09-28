"""Learning-only LITE news reading for the paper bot's daily email. It never changes a decision.

Source: Alpha Vantage NEWS_SENTIMENT, with the owner's key in the owner-only .env.news
(ALPHAVANTAGE_API_KEY). Its timestamps are New York time: bank prime-rate cuts that followed the
Fed's 14:00 ET decision on 2025-09-17 are stamped 15:09 and 15:20. The window runs from the previous
weekday's 16:00 close to 10:00 ET, so only news published before the bot's decision counts.
"""
from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import urllib.parse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[2]
KEY_FILE = ROOT / ".env.news"
KEY_NAME = "ALPHAVANTAGE_API_KEY"
URL = "https://www.alphavantage.co/query"
EVENT = "NEWS_LEARNING_ONLY"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("redirect_refused")


def api_key(path=KEY_FILE):
    """The owner's key, or None when .env.news is missing or has no value."""
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise PermissionError("Owner-only .env.news required (chmod 600 .env.news)")
    for line in path.read_text(encoding="utf-8").splitlines():
        name, _, value = line.strip().partition("=")
        if name.strip() == KEY_NAME:
            return value.strip().strip("\"'") or None
    return None


def window(now):
    """From the previous weekday's 16:00 close to 10:00 today (or now, if earlier), New York time."""
    local = now.astimezone(NY)
    previous = local.date() - timedelta(days=1)
    while previous.weekday() >= 5:
        previous -= timedelta(days=1)
    return datetime.combine(previous, dtime(16, 0), NY), min(local, datetime.combine(local.date(), dtime(10, 0), NY))


def fetch(key, start, end, opener=None):
    query = urllib.parse.urlencode({"function": "NEWS_SENTIMENT", "tickers": "LITE", "sort": "LATEST", "limit": 200,
                                    "time_from": f"{start:%Y%m%dT%H%M}", "time_to": f"{end:%Y%m%dT%H%M}", "apikey": key})
    opener = opener or build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(Request(f"{URL}?{query}", headers={"User-Agent": "lite-paper-bot/1"}), timeout=20) as reply:
        data = json.loads(reply.read(5_000_000))
    if not isinstance(data, dict) or not isinstance(data.get("feed"), list):
        raise RuntimeError("Alpha Vantage refused the request (daily limit reached or key not accepted)")
    return data["feed"]


def label(score):
    """Alpha Vantage's own cut-offs."""
    if score <= Decimal("-0.35"):
        return "Bearish"
    if score <= Decimal("-0.15"):
        return "Somewhat-Bearish"
    if score < Decimal("0.15"):
        return "Neutral"
    return "Somewhat-Bullish" if score < Decimal("0.35") else "Bullish"


def score(feed, start, end):
    """Relevance-weighted LITE sentiment of the articles published inside the window."""
    rows = []
    for article in feed:
        try:
            published = datetime.strptime(article["time_published"], "%Y%m%dT%H%M%S").replace(tzinfo=NY)
            lite = next(row for row in article.get("ticker_sentiment") or [] if row.get("ticker") == "LITE")
            relevance, value = Decimal(lite["relevance_score"]), Decimal(lite["ticker_sentiment_score"])
        except (KeyError, TypeError, ValueError, StopIteration, ArithmeticError):
            continue
        if start <= published <= end and relevance > 0:
            rows.append((published, relevance, value, article))
    if not rows:
        return {"articles": 0}
    average = sum(r * v for _, r, v, _ in rows) / sum(r for _, r, _, _ in rows)
    top = sorted(rows, key=lambda row: (-row[1], -row[0].timestamp()))[:5]
    return {"articles": len(rows), "score": str(average.quantize(Decimal("0.001"))), "label": label(average),
            "top": [f"{when:%a %H:%M} {value:+.2f} {article.get('source', '?')}: {str(article.get('title', ''))[:120]}"
                    for when, _, value, article in top]}


def reading(now, key_file=KEY_FILE, opener=None):
    """The learning-only record for this run. It never raises and never reveals the key."""
    start, end = window(now)
    record = {"type": EVENT, "window_et": f"{start:%a %H:%M} to {end:%a %H:%M}"}
    key = None
    try:
        key = api_key(key_file)
        if key is None:
            return {**record, "error": f"not set up: add {KEY_NAME} to .env.news"}
        return {**record, **score(fetch(key, start, end, opener), start, end)}
    except Exception as exc:
        detail = f"{type(exc).__name__}: {str(exc)[:160]}"
        return {**record, "error": detail.replace(key, "[key]") if key else detail}


def lines(record):
    head = f"News (learning only; it never changes a trade), {record['window_et']} ET:"
    if "error" in record:
        return [head, f"  unavailable: {record['error']}"]
    if not record.get("articles"):
        return [head, "  no LITE articles in this window."]
    return [head, f"  {record['articles']} LITE articles; relevance-weighted sentiment {record['score']} ({record['label']}).",
            *(f"  - {line}" for line in record["top"])]
