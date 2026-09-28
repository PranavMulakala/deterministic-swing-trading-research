"""Narrow Alpaca PAPER read client. GET only; no orders or credential loader."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import re
from urllib.parse import quote, unquote
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

PAPER = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"
URLS = {
    "account": PAPER + "/v2/account",
    "positions": PAPER + "/v2/positions",
    "open_orders": PAPER + "/v2/orders?status=open&limit=500",
    "clock": PAPER + "/v2/clock",
    "lite_quote": DATA + "/v2/stocks/LITE/quotes/latest?feed=iex",
    "lite_news": DATA + "/v1beta1/news?symbols=LITE&limit=50&sort=desc&include_content=false",
}


def news_page_url(token: str) -> str:
    if not isinstance(token, str) or not token or len(token) > 256 or any(ord(c) < 33 for c in token):
        raise ValueError("invalid_news_page_token")
    return URLS["lite_news"] + "&page_token=" + quote(token, safe="")


def calendar_url(start: date, end: date) -> str:
    if not isinstance(start, date) or isinstance(start, datetime) or not isinstance(end, date) or isinstance(end, datetime):
        raise ValueError("calendar_dates_required")
    if not start <= end <= start + timedelta(days=366):
        raise ValueError("calendar_range_invalid")
    return PAPER + f"/v2/calendar?start={start.isoformat()}&end={end.isoformat()}&date_type=TRADING"


def _approved_url(url: str) -> bool:
    if url in URLS.values():
        return True
    news_prefix = URLS["lite_news"] + "&page_token="
    if url.startswith(news_prefix):
        try:
            return url == news_page_url(unquote(url[len(news_prefix):]))
        except ValueError:
            return False
    match = re.fullmatch(
        re.escape(PAPER) + r"/v2/calendar\?start=(\d{4}-\d{2}-\d{2})&end=(\d{4}-\d{2}-\d{2})&date_type=TRADING",
        url)
    if not match:
        return False
    try:
        return url == calendar_url(date.fromisoformat(match[1]), date.fromisoformat(match[2]))
    except ValueError:
        return False


class ReadError(Exception):
    """Sanitized read failure; never includes URL, response, or credentials."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ReadError("redirect_blocked")


class HttpsGet:
    """Explicit paper credentials supplied by caller, never loaded from disk."""

    def __init__(self, *, key_id: str, secret_key: str):
        if not key_id or not secret_key or "\n" in key_id + secret_key or "\r" in key_id + secret_key:
            raise ValueError("invalid_credentials")
        self._headers = {"APCA-API-KEY-ID": key_id,
                         "APCA-API-SECRET-KEY": secret_key,
                         "User-Agent": "stock-paper-read-only/1.0"}
        self._opener = build_opener(ProxyHandler({}), _NoRedirect())

    def __call__(self, url: str):
        if not _approved_url(url):
            raise ReadError("unapproved_read_endpoint")
        request = Request(url, headers=self._headers, method="GET")
        try:
            with self._opener.open(request, timeout=10) as response:
                data = response.read(1_000_001)
            if len(data) > 1_000_000:
                raise ReadError("response_too_large")
            return json.loads(data)
        except ReadError:
            raise
        except Exception:
            raise ReadError("alpaca_read_failed") from None


def _time(value):
    if not isinstance(value, str):
        raise ReadError("invalid_time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ReadError("invalid_time") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReadError("invalid_time")
    return parsed.astimezone(timezone.utc)


def _positive(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ReadError("invalid_amount") from None
    if not number.is_finite() or number <= 0:
        raise ReadError("invalid_amount")
    return number


@dataclass(frozen=True)
class PaperPosition:
    asset_id: str
    symbol: str
    quantity: Decimal
    average_entry: Decimal
    side: str


@dataclass(frozen=True)
class PaperQuote:
    bid: Decimal
    ask: Decimal
    quoted_at: datetime
    feed: str = "iex"


@dataclass(frozen=True)
class NewsItem:
    article_id: str
    updated_at: datetime
    published_at: datetime
    headline: str
    source: str
    url: str


@dataclass(frozen=True)
class PaperSnapshot:
    account_id: str
    account_status: str
    cash: Decimal
    positions: tuple[PaperPosition, ...]
    open_order_ids: tuple[str, ...]
    market_open: bool
    clock_at: datetime
    quote: PaperQuote | None
    news: tuple[NewsItem, ...]
    observed_at: datetime
    news_problem: str | None = None
    quote_problem: str | None = None


class PaperReader:
    def __init__(self, fetch, *, clock=None):
        if not callable(fetch):
            raise ValueError("fetch_required")
        self._fetch = fetch
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _get(self, name):
        try:
            return self._fetch(URLS[name])
        except ReadError:
            raise
        except Exception:
            raise ReadError("alpaca_read_failed") from None

    def trading_calendar(self, start: date, end: date):
        """Read a bounded official trading calendar; caller must first lock account."""
        url = calendar_url(start, end)
        try:
            raw = self._fetch(url)
        except ReadError:
            raise
        except Exception:
            raise ReadError("alpaca_calendar_failed") from None
        if not isinstance(raw, list) or len(raw) > 367:
            raise ReadError("invalid_calendar")
        rows = []
        for item in raw:
            try:
                day = date.fromisoformat(item["date"])
                opening = item["open"]
                closing = item["close"]
            except (KeyError, TypeError, ValueError):
                raise ReadError("invalid_calendar") from None
            if (day < start or day > end or not isinstance(opening, str) or
                not isinstance(closing, str) or not re.fullmatch(r"\d{2}:\d{2}", closing) or
                not re.fullmatch(r"\d{2}:\d{2}", opening)):
                raise ReadError("invalid_calendar")
            rows.append((day, opening, closing))
        if len({row[0] for row in rows}) != len(rows):
            raise ReadError("duplicate_calendar_date")
        return tuple(sorted(rows))

    def snapshot(self, *, expected_account_id: str, observed_at: datetime | None = None,
                 include_news: bool = False, news_since: datetime | None = None) -> PaperSnapshot:
        if not expected_account_id:
            raise ValueError("account_lock_required")
        account = self._get("account")
        if not isinstance(account, dict) or account.get("id") != expected_account_id:
            raise ReadError("paper_account_mismatch")
        if account.get("status") != "ACTIVE":
            raise ReadError("paper_account_not_active")
        raw_positions = self._get("positions")
        raw_orders = self._get("open_orders")
        raw_clock = self._get("clock")
        if not isinstance(raw_positions, list) or not isinstance(raw_orders, list) or not isinstance(raw_clock, dict):
            raise ReadError("invalid_broker_snapshot")
        if len(raw_orders) >= 500:
            raise ReadError("open_orders_truncated")
        try:
            positions = tuple(PaperPosition(str(p["asset_id"]), p["symbol"],
                                            _positive(p["qty"]), _positive(p["avg_entry_price"]),
                                            p["side"]) for p in raw_positions)
            orders = tuple(str(o["id"]) for o in raw_orders)
            is_open = raw_clock["is_open"]
            clock_at = _time(raw_clock["timestamp"])
            cash = Decimal(str(account["cash"]))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            raise ReadError("invalid_broker_snapshot") from None
        if type(is_open) is not bool or not cash.is_finite() or cash < 0:
            raise ReadError("invalid_broker_snapshot")
        quote = None
        quote_problem = None
        if any(p.symbol == "LITE" for p in positions):
            try:
                raw = self._get("lite_quote")
                try:
                    q = raw["quote"]
                    quote = PaperQuote(_positive(q["bp"]), _positive(q["ap"]), _time(q["t"]))
                except (KeyError, TypeError):
                    raise ReadError("invalid_quote") from None
                if quote.bid > quote.ask:
                    raise ReadError("crossed_quote")
            except ReadError as exc:
                quote_problem = str(exc)
                quote = None
        news = ()
        news_problem = None
        if include_news and any(p.symbol == "LITE" for p in positions):
            try:
                if not isinstance(news_since, datetime) or news_since.tzinfo is None or news_since.utcoffset() is None:
                    raise ReadError("news_cutoff_missing")
                parsed = []
                url = URLS["lite_news"]
                seen_tokens = set()
                previous_updated = None
                for _ in range(10):
                    try:
                        raw = self._fetch(url)
                    except ReadError:
                        raise
                    except Exception:
                        raise ReadError("alpaca_news_failed") from None
                    if not isinstance(raw, dict) or not isinstance(raw.get("news"), list) or len(raw["news"]) > 50:
                        raise ReadError("invalid_news_response")
                    page = []
                    for item in raw["news"]:
                        try:
                            published = _time(item["created_at"])
                            updated = _time(item["updated_at"])
                            if previous_updated is not None and updated > previous_updated:
                                raise ReadError("news_out_of_order")
                            previous_updated = updated
                            if "LITE" in item["symbols"] and updated >= news_since:
                                page.append(NewsItem(str(item["id"]), updated, published,
                                                     str(item["headline"]), str(item["source"]), str(item["url"])))
                        except (KeyError, TypeError):
                            raise ReadError("invalid_news_response") from None
                    parsed.extend(page)
                    token = raw.get("next_page_token")
                    if not token or (previous_updated is not None and previous_updated < news_since):
                        break
                    if not isinstance(token, str):
                        raise ReadError("invalid_news_page_token")
                    if token in seen_tokens:
                        raise ReadError("news_page_cycle")
                    seen_tokens.add(token)
                    try:
                        url = news_page_url(token)
                    except ValueError:
                        raise ReadError("invalid_news_page_token") from None
                else:
                    raise ReadError("news_page_limit")
                news = tuple(parsed)
            except ReadError as exc:
                news_problem = str(exc)
        observed_at = observed_at if observed_at is not None else self._clock()
        if not isinstance(observed_at, datetime) or observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("aware_time_required")
        if abs((observed_at.astimezone(timezone.utc) - clock_at).total_seconds()) > 60:
            raise ReadError("stale_market_clock")
        if any(item.updated_at > observed_at or item.published_at > observed_at for item in news):
            news = ()
            news_problem = "future_news_timestamp"
        return PaperSnapshot(expected_account_id, account["status"], cash, positions,
                             orders, is_open, clock_at, quote, news,
                             observed_at.astimezone(timezone.utc), news_problem, quote_problem)
