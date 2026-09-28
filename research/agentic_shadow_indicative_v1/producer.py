"""Read-only Alpaca producer for the plumbing-only indicative experiment.

The module has no broker-order methods or URLs. It publishes one current packet
atomically and retains credential-free, compressed provider responses separately.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import uuid
from zoneinfo import ZoneInfo

from swingbot.safe_paths import private_parent, require_no_symlink_components

from .engine import canonical, digest


DATA_HOST = "data.alpaca.markets"
PAPER_HOST = "paper-api.alpaca.markets"
ALLOWED_HOSTS = {DATA_HOST, PAPER_HOST}
SYMBOLS = ("SPY", "QQQ")
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_PAGES = 20
MAX_REQUESTS = 40
MAX_RUN_LOG_BYTES = 16 * 1024 * 1024
ET = ZoneInfo("America/New_York")
KEY_NAMES = ("ALPACA_PAPER_API_KEY", "ALPACA_PAPER_API_SECRET")
RFC3339 = re.compile(
    r"^(?P<whole>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<fraction>\d{1,9}))?(?P<offset>Z|[+-]\d{2}:\d{2})$"
)


class ProducerError(RuntimeError):
    pass


class ExpectedBlock(ProducerError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ProducerError("redirect_refused")


def utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ProducerError("invalid_provider_timestamp")
    matched = RFC3339.fullmatch(value)
    if not matched:
        raise ProducerError("invalid_provider_timestamp")
    fraction = matched.group("fraction")
    normalized = matched.group("whole")
    if fraction:
        # Alpaca emits RFC3339 nanoseconds; datetime stores microseconds. Floor
        # only the sub-microsecond remainder (<1 us) for freshness arithmetic.
        normalized += "." + fraction[:6]
    normalized += "+00:00" if matched.group("offset") == "Z" else matched.group("offset")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ProducerError("invalid_provider_timestamp") from exc
    if parsed.tzinfo is None:
        raise ProducerError("naive_provider_timestamp")
    return parsed.astimezone(timezone.utc)


def iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ProducerError("naive_internal_timestamp")
    return value.astimezone(timezone.utc).isoformat()


def integer_money(value: object, scale: int) -> int:
    try:
        result = (Decimal(str(value)) * scale).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ProducerError("invalid_provider_price") from exc
    if not result.is_finite() or result < 0:
        raise ProducerError("invalid_provider_price")
    return int(result)


def sourced(raw: dict, *, source: str, feed: str, published_at: datetime,
            received_at: datetime) -> dict:
    result = deepcopy(raw)
    result["provenance"] = {
        "source": source,
        "feed": feed,
        "published_at": iso(published_at),
        "received_at": iso(received_at),
        "raw": deepcopy(raw),
        "sha256": digest(raw),
    }
    return result


def response_hashes(records: list[dict]) -> list[str]:
    return [record["sha256"] for record in records]


class AlpacaReadOnlyClient:
    def __init__(self, key: str, secret: str, *, opener=None, timeout: int = 10):
        if not key or not secret:
            raise ProducerError("credentials_missing")
        self._headers = {
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        }
        self._opener = opener or build_opener(ProxyHandler({}), NoRedirect())
        self._timeout = timeout
        self.records: list[dict] = []

    def get(self, base: str, params: dict[str, object]) -> dict:
        if len(self.records) >= MAX_REQUESTS:
            raise ProducerError("provider_request_limit")
        parsed = urlparse(base)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ProducerError("endpoint_not_allowlisted")
        query = urlencode({key: value for key, value in params.items() if value is not None})
        url = base + ("?" + query if query else "")
        request = Request(url, headers=self._headers, method="GET")
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                status = getattr(response, "status", 200)
        except HTTPError as exc:
            raise ProducerError(f"provider_http_{exc.code}") from None
        except (URLError, OSError, ValueError) as exc:
            raise ProducerError("provider_transport_failure") from exc
        if not 200 <= status < 300:
            raise ProducerError("provider_non_success")
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ProducerError("provider_response_too_large")
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProducerError("provider_json_invalid") from exc
        received = datetime.now(timezone.utc)
        record = {
            "url": url,
            "received_at": iso(received),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "raw_base64": base64.b64encode(raw).decode("ascii"),
            "payload": payload,
        }
        self.records.append(record)
        return record

    def pages(self, base: str, params: dict[str, object]) -> list[dict]:
        pages: list[dict] = []
        token = None
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            request_params = dict(params)
            if token:
                request_params["page_token"] = token
            record = self.get(base, request_params)
            if not isinstance(record["payload"], (dict, list)):
                raise ProducerError("provider_shape_invalid")
            pages.append(record)
            token = record["payload"].get("next_page_token") if isinstance(record["payload"], dict) else None
            if not token:
                return pages
            if not isinstance(token, str) or token in seen:
                raise ProducerError("provider_pagination_invalid")
            seen.add(token)
        raise ProducerError("provider_page_limit")


def _calendar_timestamp(day: str, value: object) -> datetime:
    if not isinstance(value, str):
        raise ProducerError("calendar_shape_invalid")
    if "T" in value:
        return utc(value)
    try:
        local = datetime.combine(date.fromisoformat(day), time.fromisoformat(value), ET)
    except ValueError as exc:
        raise ProducerError("calendar_shape_invalid") from exc
    return local.astimezone(timezone.utc)


def _merge_list_pages(pages: list[dict], key: str) -> list[tuple[dict, dict]]:
    result: list[tuple[dict, dict]] = []
    for page in pages:
        payload = page["payload"]
        items = payload.get(key) if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise ProducerError("provider_shape_invalid")
        for item in items:
            if not isinstance(item, dict):
                raise ProducerError("provider_shape_invalid")
            result.append((item, page))
    return result


def _merge_dict_pages(pages: list[dict], key: str) -> dict[str, tuple[dict, dict]]:
    result: dict[str, tuple[dict, dict]] = {}
    for page in pages:
        payload = page["payload"]
        items = payload.get(key) if isinstance(payload, dict) else None
        if not isinstance(items, dict):
            raise ProducerError("provider_shape_invalid")
        for symbol, item in items.items():
            if not isinstance(symbol, str) or not isinstance(item, dict) or symbol in result:
                raise ProducerError("provider_duplicate_or_invalid_item")
            result[symbol] = (item, page)
    return result


def _flatten_actions(value: object) -> list[dict]:
    if isinstance(value, list):
        result: list[dict] = []
        for item in value:
            result.extend(_flatten_actions(item))
        return result
    if isinstance(value, dict):
        if any(key in value for key in ("id", "symbol", "corporate_action_id")):
            return [value]
        result = []
        for item in value.values():
            result.extend(_flatten_actions(item))
        return result
    return []


def _previous_symbol(path: Path) -> str | None:
    try:
        safe = require_no_symlink_components(path, label="indicative output")
        if not safe.exists() or safe.stat().st_size > 10 * 1024 * 1024:
            return None
        payload = json.loads(safe.read_text(encoding="utf-8"))
        symbol = payload[0]["symbol"] if isinstance(payload, list) and len(payload) == 1 else None
        return symbol if symbol in SYMBOLS else None
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def choose_symbol(path: Path) -> str:
    return "QQQ" if _previous_symbol(path) == "SPY" else "SPY"


def in_collection_window(now: datetime) -> bool:
    local = now.astimezone(ET)
    # Three completed five-minute bars exist by this warmup boundary. Stop at
    # the regular close so a post-close stale quote cannot be published.
    return local.weekday() < 5 and time(9, 50) <= local.time().replace(tzinfo=None) <= time(16, 0)


def _atomic_bytes(path: Path, contents: bytes, *, mode: int = 0o640) -> None:
    path = require_no_symlink_components(path, label="indicative publication")
    with private_parent(path, label="indicative publication") as directory:
        # safe_paths defaults parents to private 0700. This producer publishes
        # credential-free market packets to one dedicated reader group, so the
        # directory must be traversable by that group before the atomic rename.
        os.fchmod(directory.descriptor, 0o750)
        temporary = f".{path.name}.{uuid.uuid4().hex}.tmp"
        descriptor = None
        try:
            descriptor = directory.open_file(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            os.fchmod(descriptor, mode)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = None
                stream.write(contents)
                stream.flush()
                os.fsync(stream.fileno())
            directory.check_leaf(path.name)
            os.replace(temporary, path.name, src_dir_fd=directory.descriptor,
                       dst_dir_fd=directory.descriptor)
            os.fsync(directory.descriptor)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=directory.descriptor)
            except FileNotFoundError:
                pass


def publish_json(path: Path, value: object) -> None:
    _atomic_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def append_jsonl(path: Path, value: object) -> None:
    """Append one small credential-free status record to the operational log."""
    path = require_no_symlink_components(path, label="indicative run log")
    encoded = (canonical(value) + "\n").encode()
    if len(encoded) > 16 * 1024:
        raise ProducerError("run_log_record_too_large")
    with private_parent(path, label="indicative run log") as directory:
        os.fchmod(directory.descriptor, 0o750)
        descriptor = directory.open_file(
            path.name, os.O_WRONLY | os.O_CREAT | os.O_APPEND
        )
        try:
            metadata = os.fstat(descriptor)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                    or metadata.st_size + len(encoded) > MAX_RUN_LOG_BYTES):
                raise ProducerError("run_log_invalid_or_full")
            os.fchmod(descriptor, 0o640)
            written = os.write(descriptor, encoded)
            if written != len(encoded):
                raise ProducerError("run_log_short_write")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def release_revision() -> str:
    value = os.environ.get("SHADOW_RELEASE_REVISION", "development")
    if value != "development" and (len(value) != 64 or any(c not in "0123456789abcdef" for c in value)):
        raise ProducerError("release_revision_invalid")
    return value


def record_status(status_path: Path, run_log: Path, value: dict) -> dict:
    completed = datetime.now(timezone.utc)
    result = {**value, "finished_at": iso(completed)}
    append_jsonl(run_log, result)
    publish_json(status_path, result)
    return result


def credentials(path: Path | None = None) -> tuple[str, str]:
    environment = tuple(os.environ.get(name, "") for name in KEY_NAMES)
    if all(environment):
        return environment  # Values are never logged or persisted by this module.
    if any(environment):
        raise ProducerError("partial_credentials")
    if path is None:
        directory = os.environ.get("CREDENTIALS_DIRECTORY")
        path = Path(directory) / "alpaca.env" if directory else None
    if path is None:
        raise ProducerError("credentials_missing")
    path = require_no_symlink_components(path, label="indicative credentials")
    metadata = path.stat()
    mode = stat.S_IMODE(metadata.st_mode)
    credential_directory = os.environ.get("CREDENTIALS_DIRECTORY")
    systemd_credential = bool(
        credential_directory
        and path.parent == Path(credential_directory)
        and mode == 0o440
        and metadata.st_uid == 0
        and metadata.st_gid == 0
    )
    private_file = mode == 0o600 and metadata.st_uid in (0, os.geteuid())
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
            or not (private_file or systemd_credential) or metadata.st_size > 4096):
        raise ProducerError("credentials_file_insecure")
    parsed: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ProducerError("credentials_file_invalid")
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in KEY_NAMES or key in parsed or not value:
            raise ProducerError("credentials_file_invalid")
        parsed[key] = value
    if set(parsed) != set(KEY_NAMES):
        raise ProducerError("credentials_file_invalid")
    return parsed[KEY_NAMES[0]], parsed[KEY_NAMES[1]]


def build_packet(client: AlpacaReadOnlyClient, symbol: str, *, now: datetime | None = None) -> dict:
    if symbol not in SYMBOLS:
        raise ProducerError("symbol_not_allowlisted")
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    today = started.astimezone(ET).date()
    expiry_start = today + timedelta(days=7)
    expiry_end = today + timedelta(days=14)
    calendar_pages = client.pages(
        f"https://{PAPER_HOST}/v2/calendar",
        {"start": today.isoformat(), "end": expiry_end.isoformat()},
    )
    if len(calendar_pages) != 1 or not isinstance(calendar_pages[0]["payload"], list):
        raise ProducerError("calendar_shape_invalid")
    calendar_record = calendar_pages[0]
    calendars: dict[str, tuple[datetime, datetime]] = {}
    for item in calendar_record["payload"]:
        if not isinstance(item, dict) or not isinstance(item.get("date"), str):
            raise ProducerError("calendar_shape_invalid")
        calendars[item["date"]] = (
            _calendar_timestamp(item["date"], item.get("open")),
            _calendar_timestamp(item["date"], item.get("close")),
        )
    if today.isoformat() not in calendars:
        raise ExpectedBlock("calendar_closed")
    today_open, today_close = calendars[today.isoformat()]

    market: dict[str, dict] = {}
    contract_rows: dict[str, tuple[dict, dict]] = {}
    snapshot_rows: dict[str, tuple[dict, dict]] = {}
    contract_pages_all: list[dict] = []
    chain_pages_all: list[dict] = []
    for item_symbol in SYMBOLS:
        completed: list[tuple[dict, dict, datetime]] = []
        if item_symbol == symbol:
            bars_pages = client.pages(
                f"https://{DATA_HOST}/v2/stocks/{item_symbol}/bars",
                {"timeframe": "5Min", "start": iso(today_open - timedelta(minutes=5)),
                 "end": iso(started), "feed": "iex", "adjustment": "raw",
                 "sort": "desc", "limit": 1000},
            )
            bars_with_pages = []
            for bars_page in bars_pages:
                bars_payload = bars_page["payload"]
                bars_values = bars_payload.get("bars") if isinstance(bars_payload, dict) else None
                if not isinstance(bars_values, list):
                    raise ProducerError("provider_shape_invalid")
                bars_with_pages.extend((bar, bars_page) for bar in bars_values if isinstance(bar, dict))
            for bar, page in bars_with_pages:
                begin = utc(bar.get("t"))
                end = begin + timedelta(minutes=5)
                if end <= started:
                    completed.append((bar, page, end))
            completed.sort(key=lambda row: row[2])
            if len(completed) < 3:
                raise ExpectedBlock(f"insufficient_completed_bars_{item_symbol}")
            completed = completed[-3:]
            if any(completed[index + 1][2] - completed[index][2] != timedelta(minutes=5)
                   for index in range(2)):
                raise ExpectedBlock(f"nonconsecutive_bars_{item_symbol}")
        trade_record = client.get(
            f"https://{DATA_HOST}/v2/stocks/{item_symbol}/trades/latest", {"feed": "iex"}
        )
        trade = trade_record["payload"].get("trade") if isinstance(trade_record["payload"], dict) else None
        if not isinstance(trade, dict):
            raise ProducerError("latest_trade_shape_invalid")
        price = Decimal(str(trade.get("p")))
        if not price.is_finite() or price <= 0:
            raise ProducerError("latest_trade_shape_invalid")
        low, high = price * Decimal("0.99"), price * Decimal("1.01")
        common = {
            "expiration_date_gte": expiry_start.isoformat(),
            "expiration_date_lte": expiry_end.isoformat(),
            "strike_price_gte": format(low, "f"),
            "strike_price_lte": format(high, "f"),
        }
        contract_pages = client.pages(
            f"https://{PAPER_HOST}/v2/options/contracts",
            {**common, "underlying_symbols": item_symbol, "status": "active",
             "show_deliverables": "true", "limit": 10000},
        )
        chain_pages = client.pages(
            f"https://{DATA_HOST}/v1beta1/options/snapshots/{item_symbol}",
            {**common, "feed": "indicative", "limit": 1000},
        )
        for contract, page in _merge_list_pages(contract_pages, "option_contracts"):
            contract_symbol = contract.get("symbol")
            if not isinstance(contract_symbol, str) or contract_symbol in contract_rows:
                raise ProducerError("contract_identity_invalid")
            contract_rows[contract_symbol] = (contract, page)
        for contract_symbol, pair in _merge_dict_pages(chain_pages, "snapshots").items():
            if contract_symbol in snapshot_rows:
                raise ProducerError("snapshot_identity_invalid")
            snapshot_rows[contract_symbol] = pair
        contract_pages_all.extend(contract_pages)
        chain_pages_all.extend(chain_pages)
        market[item_symbol] = {
            "bars": completed,
            "trade": trade,
            "trade_record": trade_record,
        }

    news_start = started - timedelta(hours=1)
    news_pages = client.pages(
        f"https://{DATA_HOST}/v1beta1/news",
        {"symbols": symbol, "start": iso(news_start), "end": iso(started),
         "sort": "asc", "limit": 50, "include_content": "false"},
    )
    action_pages = client.pages(
        f"https://{DATA_HOST}/v1/corporate-actions",
        {"symbols": symbol, "start": today.isoformat(), "end": expiry_end.isoformat(),
         "region": "us", "data_quality": "all", "sort": "asc", "limit": 1000},
    )
    # Explicit time is a deterministic fixture/replay seam. Live callers omit
    # it so the observation is stamped only after every provider response lands.
    observed = started if now is not None else datetime.now(timezone.utc)
    calendar_hash = calendar_record["sha256"]
    calendar = sourced({
        "date": today.isoformat(), "open": iso(today_open), "close": iso(today_close),
        "provider_response_sha256": calendar_hash,
    }, source=f"https://{PAPER_HOST}/v2/calendar", feed="alpaca-calendar",
       published_at=utc(calendar_record["received_at"]),
       received_at=utc(calendar_record["received_at"]))

    selected_market = market[symbol]
    trade = selected_market["trade"]
    trade_received = utc(selected_market["trade_record"]["received_at"])
    underlying = sourced({
        "symbol": symbol, "market_at": iso(utc(trade.get("t"))),
        "price_mills": integer_money(trade.get("p"), 1000),
        "provider_response_sha256": selected_market["trade_record"]["sha256"],
        "provider_conditions": trade.get("c", []),
    }, source=f"https://{DATA_HOST}/v2/stocks/{symbol}/trades/latest",
       feed="alpaca-iex", published_at=utc(trade.get("t")), received_at=trade_received)

    bars = []
    for bar, page, end in selected_market["bars"]:
        received = utc(page["received_at"])
        bars.append(sourced({
            "symbol": symbol, "end": iso(end),
            "close_mills": integer_money(bar.get("c"), 1000),
            "provider_response_sha256": page["sha256"],
            "provider_bar_start": bar.get("t"),
        }, source=f"https://{DATA_HOST}/v2/stocks/{symbol}/bars",
           feed="alpaca-iex", published_at=received, received_at=received))

    chain_contracts = []
    for contract_symbol in sorted(set(contract_rows) & set(snapshot_rows)):
        contract, contract_page = contract_rows[contract_symbol]
        snapshot, snapshot_page = snapshot_rows[contract_symbol]
        quote = snapshot.get("latestQuote")
        if not isinstance(quote, dict):
            continue
        expiry = contract.get("expiration_date")
        if not isinstance(expiry, str) or expiry not in calendars:
            continue
        _, expiry_close = calendars[expiry]
        try:
            multiplier = int(contract.get("multiplier") or contract.get("size"))
            strike_mills = integer_money(contract.get("strike_price"), 1000)
            open_interest = int(contract.get("open_interest") or 0)
            volume = int((snapshot.get("dailyBar") or {}).get("v") or 0)
            quote_at = utc(quote.get("t"))
            right = {"call": "C", "put": "P"}[str(contract.get("type")).lower()]
        except (ValueError, TypeError, KeyError, ProducerError):
            continue
        standard = (contract.get("root_symbol") == contract.get("underlying_symbol")
                    and multiplier == 100 and not contract.get("deliverables"))
        contract_received = utc(contract_page["received_at"])
        normalized_contract = sourced({
            "symbol": contract_symbol,
            "underlying": contract.get("underlying_symbol"),
            "right": right,
            "strike_mills": strike_mills,
            "expiry": expiry,
            "expiry_at": iso(expiry_close),
            "multiplier": multiplier,
            "adjusted": not standard,
            "currency": "USD",
            "style": str(contract.get("style", "")).lower(),
            "open_interest": open_interest,
            "open_interest_as_of": contract.get("open_interest_date"),
            "provider_contract_id": contract.get("id"),
            "provider_response_sha256": contract_page["sha256"],
            "normalization_basis": "expiry cutoff uses Alpaca market-calendar close; USD and standard status are declared transforms for plumbing only",
        }, source=f"https://{PAPER_HOST}/v2/options/contracts",
           feed="alpaca-indicative", published_at=contract_received,
           received_at=contract_received)
        quote_received = utc(snapshot_page["received_at"])
        normalized_quote = sourced({
            "symbol": contract_symbol,
            "market_at": iso(quote_at),
            "bid_cents": integer_money(quote.get("bp"), 100),
            "ask_cents": integer_money(quote.get("ap"), 100),
            "bid_size": int(quote.get("bs") or 0),
            "ask_size": int(quote.get("as") or 0),
            "volume": volume,
            "condition": "regular",
            "provider_conditions": quote.get("c", []),
            "provider_response_sha256": snapshot_page["sha256"],
        }, source=f"https://{DATA_HOST}/v1beta1/options/snapshots/{contract.get('underlying_symbol')}",
           feed="alpaca-indicative", published_at=quote_at, received_at=quote_received)
        chain_contracts.append({"contract": normalized_contract, "quote": normalized_quote})
    if not chain_contracts:
        raise ExpectedBlock("no_joined_option_contracts")
    chain_received = max(utc(record["received_at"]) for record in chain_pages_all)
    chain = sourced({
        "symbol": symbol, "covered_symbols": list(SYMBOLS), "complete": True,
        "contracts": chain_contracts,
        "provider_response_sha256s": response_hashes(chain_pages_all + contract_pages_all),
    }, source=f"https://{DATA_HOST}/v1beta1/options/snapshots/{symbol}",
       feed="alpaca-indicative", published_at=chain_received, received_at=chain_received)

    action_hashes = response_hashes(action_pages)
    actions = []
    for page in action_pages:
        payload = page["payload"]
        if not isinstance(payload, dict) or "corporate_actions" not in payload:
            raise ProducerError("corporate_action_shape_invalid")
        actions.extend(_flatten_actions(payload["corporate_actions"]))
    action_received = max(utc(record["received_at"]) for record in action_pages)
    events = sourced({
        "symbol": symbol,
        "earnings": "not_applicable_etf",
        "corporate_actions": "clear" if not actions else "scheduled",
        "coverage_end": iso(today_close),
        "actions": actions,
        "provider_warning": "Alpaca documents that corporate actions may be delayed; this remains a plumbing-only coverage limitation",
        "provider_response_sha256s": action_hashes,
    }, source=f"https://{DATA_HOST}/v1/corporate-actions",
       feed="alpaca-corporate-actions", published_at=action_received,
       received_at=action_received)

    news_items = []
    for item, page in _merge_list_pages(news_pages, "news"):
        published = utc(item.get("updated_at") or item.get("created_at"))
        received = utc(page["received_at"])
        news_items.append(sourced({
            "id": item.get("id"), "headline": item.get("headline"),
            "url": item.get("url"), "symbols": item.get("symbols", []),
            "provider_response_sha256": page["sha256"],
        }, source=f"https://{DATA_HOST}/v1beta1/news", feed="alpaca-news",
           published_at=published, received_at=received))
    news_received = max(utc(record["received_at"]) for record in news_pages)
    news = sourced({
        "symbol": symbol, "complete": True, "items": news_items,
        "coverage_start": iso(news_start), "coverage_end": iso(started),
        "provider_response_sha256s": response_hashes(news_pages),
    }, source=f"https://{DATA_HOST}/v1beta1/news", feed="alpaca-news",
       published_at=news_received, received_at=news_received)

    event_id = f"alpaca-indicative-{symbol}-{observed.strftime('%Y%m%dT%H%M%S%fZ')}"
    return {
        "event_id": event_id,
        "kind": "indicative",
        "purpose": "plumbing_only",
        "orders_enabled": False,
        "observed_at": iso(observed),
        "symbol": symbol,
        "calendar": calendar,
        "events": events,
        "news": news,
        "underlying": underlying,
        "bars": bars,
        "chain": chain,
    }


def build_with_fallback(client: AlpacaReadOnlyClient, preferred: str, *,
                        now: datetime | None = None) -> dict:
    if preferred not in SYMBOLS:
        raise ProducerError("symbol_not_allowlisted")
    attempts = (preferred,) + tuple(symbol for symbol in SYMBOLS if symbol != preferred)
    blocked = []
    for symbol in attempts:
        try:
            packet = build_packet(client, symbol, now=now)
            packet["producer_symbol_attempts"] = blocked + [{"symbol": symbol, "status": "selected"}]
            return packet
        except ExpectedBlock as exc:
            blocked.append({"symbol": symbol, "status": "blocked", "reason": str(exc)})
    raise ExpectedBlock("all_symbols_blocked:" + ",".join(item["reason"] for item in blocked))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--run-log", type=Path, required=True)
    parser.add_argument("--credentials", type=Path)
    parser.add_argument("--symbol", choices=("auto",) + SYMBOLS, default="auto")
    parser.add_argument("--force", action="store_true", help="collect outside the normal window for an operator smoke test")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    base_status = {
        "checked_at": iso(now), "purpose": "plumbing_only", "orders": False,
        "subscriptions_changed": False, "real_money": False,
        "release_revision": release_revision(),
        "forced": args.force,
    }
    if not args.force and not in_collection_window(now):
        status = record_status(
            args.status, args.run_log,
            {**base_status, "status": "IDLE_OUTSIDE_COLLECTION_WINDOW", "network_requests": 0},
        )
        print(canonical(status))
        return
    client = None
    try:
        key, secret = credentials(args.credentials)
        client = AlpacaReadOnlyClient(key, secret)
        symbol = choose_symbol(args.output) if args.symbol == "auto" else args.symbol
        packet = (build_with_fallback(client, symbol) if args.symbol == "auto"
                  else build_packet(client, symbol))
        symbol = packet["symbol"]
        archive_payload = {
            "event_id": packet["event_id"], "created_at": iso(datetime.now(timezone.utc)),
            "purpose": "plumbing_only", "credentials_included": False,
            "normalized_packet_without_archive_hash": packet,
            "responses": client.records,
        }
        archive_bytes = gzip.compress((json.dumps(archive_payload, sort_keys=True) + "\n").encode(), mtime=0)
        archive_sha = hashlib.sha256(archive_bytes).hexdigest()
        packet["provider_archive_sha256"] = archive_sha
        archive_path = args.archive_dir / (packet["event_id"] + ".json.gz")
        _atomic_bytes(archive_path, archive_bytes)
        publish_json(args.output, [packet])
        status = {**base_status, "status": "PUBLISHED", "event_id": packet["event_id"],
                  "symbol": symbol, "network_requests": len(client.records),
                  "provider_archive": str(archive_path), "provider_archive_sha256": archive_sha,
                  "packet_sha256": digest(packet), "contracts": len(packet["chain"]["contracts"]),
                  "symbol_attempts": packet.get("producer_symbol_attempts", [])}
        status = record_status(args.status, args.run_log, status)
        print(canonical(status))
    except ExpectedBlock as exc:
        status = {**base_status, "status": "BLOCKED", "reason": str(exc),
                  "network_requests": len(client.records) if client else 0}
        status = record_status(args.status, args.run_log, status)
        print(canonical(status))
    except (ProducerError, OSError, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, ProducerError) else type(exc).__name__
        status = {**base_status, "status": "ERROR", "reason": reason,
                  "network_requests": len(client.records) if client else 0}
        status = record_status(args.status, args.run_log, status)
        print(canonical(status))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
