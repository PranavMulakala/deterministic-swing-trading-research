"""Build free, hash-bound stock cycles from Alpaca Basic and Nasdaq calendar data.

This adapter performs market-data GETs only. It has no broker/account/order URL.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import statistics
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

from research.agentic_portfolio_paper_10000_v1.profile import SCHEDULED_SESSION_DATES
from research.agentic_portfolio_v1.evidence import EvidencePacket
from research.agentic_portfolio_v1.stock import STRATEGY, VERSION


ALPACA = "https://data.alpaca.markets"
NASDAQ = "https://api.nasdaq.com"
SYMBOLS = ("AAOI", "CIEN", "COHR", "FN", "LITE")
SOURCE_MODE = "ALPACA_BASIC_FREE_IEX_QUOTES_SIP_HISTORY_V2"
MAX_RESPONSE = 16 * 1024 * 1024
ADVERSE_PHRASES = (
    "bankruptcy", "files for bankruptcy", "fraud", "accounting investigation",
    "sec investigation", "ceo resign", "lowers guidance", "cuts guidance",
    "public offering", "dilution", "delisting", "cyberattack", "data breach",
)


class ProviderBlocked(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderBlocked("redirect forbidden")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest_pages(pages: list[bytes]) -> str:
    digest = hashlib.sha256()
    for page in pages:
        digest.update(len(page).to_bytes(8, "big"))
        digest.update(page)
    return digest.hexdigest()


def parse_time(value: str) -> datetime:
    point = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if point.tzinfo is None or point.utcoffset() is None:
        raise ProviderBlocked("provider timestamp is timezone-naive")
    return point.astimezone(timezone.utc)


def number(value, field: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise ProviderBlocked(f"{field} is not numeric")
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ProviderBlocked(f"{field} is not numeric") from exc
    if not result.is_finite() or (positive and result <= 0):
        raise ProviderBlocked(f"{field} is invalid")
    return result


def text_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")


class Client:
    def __init__(self, credentials: dict[str, str]):
        key = credentials.get("key")
        secret = credentials.get("secret")
        if not isinstance(key, str) or not key or not isinstance(secret, str) or not secret:
            raise ProviderBlocked("Alpaca credentials are missing")
        self.alpaca_headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def get(self, host: str, path: str, query: dict[str, str], *, alpaca: bool) -> tuple[dict, bytes]:
        if host not in {ALPACA, NASDAQ} or not path.startswith("/"):
            raise ProviderBlocked("provider host or path is outside the allowlist")
        headers = dict(self.alpaca_headers) if alpaca else {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 free-stock-paper-research/1.0",
            "Origin": "https://www.nasdaq.com",
            "Referer": "https://www.nasdaq.com/market-activity/earnings",
        }
        request = Request(host + path + "?" + urlencode(query), headers=headers, method="GET")
        with self.opener.open(request, timeout=30) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ProviderBlocked("provider response exceeds 16 MiB")
        try:
            value = json.loads(raw)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProviderBlocked("provider response is not JSON") from exc
        if type(value) is not dict:
            raise ProviderBlocked("provider response is not an object")
        return value, raw


def alpaca_pages(client: Client, path: str, query: dict[str, str], row_key: str) -> tuple[list, list[bytes]]:
    rows: list = []
    pages: list[bytes] = []
    token = None
    seen: set[str] = set()
    for _ in range(100):
        current = dict(query)
        if token is not None:
            current["page_token"] = token
        body, raw = client.get(ALPACA, path, current, alpaca=True)
        pages.append(raw)
        value = body.get(row_key)
        if value is None:
            value = []
        if type(value) not in {list, dict}:
            raise ProviderBlocked(f"invalid Alpaca {row_key} response")
        if isinstance(value, list):
            rows.extend(value)
        else:
            rows.append(value)
        token = body.get("next_page_token")
        if token is None:
            return rows, pages
        if not isinstance(token, str) or not token or token in seen:
            raise ProviderBlocked("invalid or repeated pagination token")
        seen.add(token)
    raise ProviderBlocked("provider pagination cap reached")


def history(client: Client, now: datetime) -> tuple[dict[str, list[dict]], list[bytes]]:
    start = (now - timedelta(days=130)).date().isoformat()
    query = {
        "symbols": ",".join(SYMBOLS), "timeframe": "1Day", "start": start,
        "end": (now - timedelta(minutes=16)).isoformat(), "feed": "sip",
        "adjustment": "raw", "sort": "asc", "limit": "10000",
    }
    body, raw = client.get(ALPACA, "/v2/stocks/bars", query, alpaca=True)
    bars = body.get("bars")
    if type(bars) is not dict or set(bars) - set(SYMBOLS):
        raise ProviderBlocked("daily history response is malformed")
    local_today = now.astimezone(ZoneInfo("America/New_York")).date()
    result: dict[str, list[dict]] = {}
    for symbol in SYMBOLS:
        values = bars.get(symbol)
        if not isinstance(values, list):
            raise ProviderBlocked(f"daily history missing for {symbol}")
        completed = [row for row in values if isinstance(row, dict) and parse_time(row["t"]).astimezone(ZoneInfo("America/New_York")).date() < local_today]
        if len(completed) < 51:
            raise ProviderBlocked(f"fewer than 51 completed daily bars for {symbol}")
        result[symbol] = completed[-70:]
    return result, [raw]


def snapshots(client: Client) -> tuple[dict[str, dict], list[bytes]]:
    body, raw = client.get(ALPACA, "/v2/stocks/snapshots", {"symbols": ",".join(SYMBOLS), "feed": "iex"}, alpaca=True)
    snapshots = body.get("snapshots", body)
    if type(snapshots) is not dict or any(symbol not in snapshots for symbol in SYMBOLS):
        raise ProviderBlocked("IEX snapshot coverage is incomplete")
    return snapshots, [raw]


def direct_news(client: Client, now: datetime) -> tuple[dict[str, bool], list[bytes]]:
    rows, pages = alpaca_pages(client, "/v1beta1/news", {
        "symbols": ",".join(SYMBOLS), "start": (now - timedelta(hours=24)).isoformat(),
        "end": now.isoformat(), "sort": "asc", "limit": "50", "include_content": "false",
    }, "news")
    flags = {symbol: False for symbol in SYMBOLS}
    for row in rows:
        if type(row) is not dict or not isinstance(row.get("headline"), str) or not isinstance(row.get("symbols"), list):
            raise ProviderBlocked("news response contains a malformed row")
        created = parse_time(row["created_at"])
        if created < now - timedelta(hours=24) or created > now:
            raise ProviderBlocked("news row lies outside the requested window")
        headline = row["headline"].lower()
        adverse = any(phrase in headline for phrase in ADVERSE_PHRASES)
        if adverse:
            for symbol in row["symbols"]:
                if symbol in flags:
                    flags[symbol] = True
    return flags, pages


def earnings(client: Client, now: datetime, cache_path: Path | None = None) -> tuple[dict[str, int], date, str]:
    local_date = now.astimezone(ZoneInfo("America/New_York")).date()
    through = local_date + timedelta(days=10)
    if cache_path is not None and cache_path.is_file() and not cache_path.is_symlink():
        try:
            if cache_path.stat().st_size > 1024 * 1024:
                raise ProviderBlocked("earnings cache is oversized")
            cached = json.loads(cache_path.read_text())
            fetched = parse_time(cached["fetched_at"])
            cached_distances = cached["distances"]
            cached_digest = cached["receipt_hash"]
            if (
                cached["schema_version"] == "1.0"
                and cached["local_date"] == local_date.isoformat()
                and date.fromisoformat(cached["through"]) >= through
                and now - fetched <= timedelta(hours=6)
                and type(cached_distances) is dict
                and sorted(cached_distances) == sorted(SYMBOLS)
                and all(type(value) is int and value >= 0 for value in cached_distances.values())
                and isinstance(cached_digest, str) and len(cached_digest) == 64
            ):
                return cached_distances, date.fromisoformat(cached["through"]), cached_digest
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass
    found: dict[str, date] = {}
    pages: list[bytes] = []
    cursor = local_date
    while cursor <= through:
        body, raw = client.get(NASDAQ, "/api/calendar/earnings", {"date": cursor.isoformat()}, alpaca=False)
        pages.append(raw)
        data = body.get("data")
        if data is None:
            rows = []
        elif type(data) is dict and (data.get("rows") is None or isinstance(data.get("rows"), list)):
            rows = data.get("rows") or []
        else:
            raise ProviderBlocked("Nasdaq earnings calendar response is malformed")
        for row in rows:
            if type(row) is not dict:
                raise ProviderBlocked("Nasdaq earnings calendar row is malformed")
            symbol = str(row.get("symbol", "")).lstrip("$").upper()
            if symbol in SYMBOLS and symbol not in found:
                found[symbol] = cursor
        cursor += timedelta(days=1)
    distances = {}
    schedule = [date.fromisoformat(value) for value in SCHEDULED_SESSION_DATES]
    for symbol in SYMBOLS:
        target = found.get(symbol)
        if target is None:
            distances[symbol] = 10
        else:
            distances[symbol] = sum(1 for session in schedule if local_date <= session <= target) - 1
            distances[symbol] = max(0, distances[symbol])
    receipt_hash = digest_pages(pages)
    if cache_path is not None:
        atomic_write(cache_path, {
            "schema_version": "1.0", "local_date": local_date.isoformat(),
            "through": through.isoformat(), "fetched_at": now.isoformat(),
            "distances": distances, "receipt_hash": receipt_hash,
        })
    return distances, through, receipt_hash


def atr14(rows: list[dict]) -> Decimal:
    selected = rows[-15:]
    ranges = []
    for previous, current in zip(selected, selected[1:]):
        high = number(current["h"], "daily high", positive=True)
        low = number(current["l"], "daily low", positive=True)
        close = number(previous["c"], "previous close", positive=True)
        ranges.append(max(high - low, abs(high - close), abs(low - close)))
    if len(ranges) != 14:
        raise ProviderBlocked("ATR14 history is incomplete")
    return sum(ranges) / Decimal(14)


def build_cycle(client: Client, now: datetime, *, earnings_cache: Path | None = None) -> dict:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ProviderBlocked("decision time must be timezone-aware")
    now = now.astimezone(timezone.utc)
    current, quote_pages = snapshots(client)
    for symbol in SYMBOLS:
        snapshot = current[symbol]
        quote = snapshot.get("latestQuote") if isinstance(snapshot, dict) else None
        if not isinstance(quote, dict):
            raise ProviderBlocked(f"IEX snapshot fields are incomplete for {symbol}")
        quote_at = parse_time(quote["t"])
        if now - quote_at < timedelta(0) or now - quote_at > timedelta(minutes=5):
            raise ProviderBlocked(f"IEX snapshot is stale for {symbol}")
        number(quote.get("bp"), "latest executable bid", positive=True)
        number(quote.get("ap"), "latest ask", positive=True)
    histories, history_pages = history(client, now)
    adverse, news_pages = direct_news(client, now)
    earnings_away, earnings_through, earnings_hash = earnings(client, now, cache_path=earnings_cache)
    entries = []
    management = []
    observed: list[datetime] = []
    for symbol in SYMBOLS:
        snapshot = current[symbol]
        if type(snapshot) is not dict:
            raise ProviderBlocked(f"snapshot is malformed for {symbol}")
        quote = snapshot.get("latestQuote")
        day = snapshot.get("dailyBar")
        if not all(isinstance(value, dict) for value in (quote, day)):
            raise ProviderBlocked(f"IEX snapshot fields are incomplete for {symbol}")
        quote_at = parse_time(quote["t"])
        feature_at = quote_at
        if now - feature_at < timedelta(0) or now - feature_at > timedelta(minutes=5):
            raise ProviderBlocked(f"IEX snapshot is stale for {symbol}")
        observed.append(feature_at)
        price = number(quote["bp"], "latest executable bid", positive=True)
        ask = number(quote["ap"], "latest ask", positive=True)
        rows = histories[symbol]
        prior = number(rows[-1]["c"], "prior close", positive=True)
        closes = [number(row["c"], "history close", positive=True) for row in rows[-50:]]
        volumes = [number(row["v"], "history volume") * number(row["c"], "history close", positive=True) for row in rows[-20:]]
        vwap = number(day.get("vw"), "IEX session VWAP", positive=True)
        data = {
            "price": text_decimal(price),
            "next_ask": text_decimal(ask),
            "entry_limit": text_decimal(price * Decimal("1.001")),
            "dollar_volumes_20": [text_decimal(value) for value in volumes],
            "atr14": text_decimal(atr14(rows)),
            "session_return": text_decimal(price / prior - Decimal(1)),
            "session_vwap": text_decimal(vwap),
            "sma50": text_decimal(sum(closes) / Decimal(50)),
            "earnings_sessions_away": earnings_away[symbol],
            "hard_adverse_news": adverse[symbol],
            "thesis_broken": adverse[symbol],
            "thesis": "frozen technical dip-and-reclaim candidate using free-data adapter",
            "invalidation": "hard-adverse direct news or the frozen management review conditions",
        }
        entry = EvidencePacket.build(
            kind="stock_entry", strategy=STRATEGY, version=VERSION, symbol=symbol,
            source="alpaca-basic-iex-quotes-plus-sip-history-v2", feature_as_of=feature_at,
            observed_at=feature_at, retrieved_at=now, data=data,
        )
        manage = EvidencePacket.build(
            kind="stock_management", strategy=STRATEGY, version=VERSION, symbol=symbol,
            source="alpaca-basic-iex-executable-bid-v2", feature_as_of=feature_at,
            observed_at=feature_at, retrieved_at=now,
            data={"price": text_decimal(price), "thesis_broken": adverse[symbol]},
        )
        entries.append(entry.as_dict())
        management.append(manage.as_dict())
    local = now.astimezone(ZoneInfo("America/New_York"))
    scheduled = local.date().isoformat() in SCHEDULED_SESSION_DATES
    completed = local.date().isoformat() if scheduled and (local.hour, local.minute) >= (16, 5) else None
    unsigned = {
        "schema_version": "1.0",
        "cycle_id": "free-stock-" + now.strftime("%Y%m%dT%H%M%S.%fZ"),
        "decision_at": now.isoformat(),
        "completed_session_date": completed,
        "coverage": {
            "source_mode": SOURCE_MODE,
            "stock_history_sessions": {symbol: len(histories[symbol]) for symbol in SYMBOLS},
            "stock_symbols": list(SYMBOLS),
            "stock_observed_at": min(observed).isoformat(),
            "earnings_calendar_through": earnings_through.isoformat(),
            "news_lookback_seconds": 86400,
            "context_complete": True,
            "receipt_hashes": {
                "stock_history": digest_pages(history_pages),
                "stock_quotes": digest_pages(quote_pages),
                "direct_news": digest_pages(news_pages),
                "earnings_calendar": earnings_hash,
            },
        },
        "stock_entries": entries,
        "stock_management": management,
    }
    return {**unsigned, "cycle_hash": hashlib.sha256(canonical(unsigned).encode()).hexdigest()}


def atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        raw = (canonical(value) + "\n").encode()
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", type=Path, default=Path("/etc/trading-collector/credentials.json"))
    parser.add_argument("--output", type=Path, default=Path("/var/lib/agentic-stock-free-input/latest.json"))
    parser.add_argument("--status", type=Path, default=Path("/var/lib/agentic-stock-free-input/status.json"))
    parser.add_argument("--earnings-cache", type=Path, default=Path("/var/lib/agentic-stock-free-input/earnings-cache.json"))
    args = parser.parse_args()
    try:
        credentials = json.loads(args.credentials.read_text())
        cycle = build_cycle(Client(credentials), datetime.now(timezone.utc), earnings_cache=args.earnings_cache)
        atomic_write(args.output, cycle)
        status = {
            "status": "PROVIDER_CYCLE_READY", "checked_at": cycle["decision_at"],
            "cycle_id": cycle["cycle_id"], "source_mode": SOURCE_MODE,
            "orders_enabled": False, "symbols": list(SYMBOLS),
        }
        code = 0
    except Exception as exc:
        status = {
            "status": "BLOCKED_DATA", "checked_at": datetime.now(timezone.utc).isoformat(),
            "reason": str(exc)[:300], "source_mode": SOURCE_MODE, "orders_enabled": False,
        }
        code = 2
    atomic_write(args.status, status)
    print(canonical(status))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
