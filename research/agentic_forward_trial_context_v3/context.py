"""Deterministic context gate. Context can veto, block, or preserve; never originate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .macro import macro_state
from .receipts import ArchiveReceipt, ReceiptError, aware_utc, decimal_string, plain_object


MARKET_SYMBOLS = frozenset({"SPY", "QQQ", "XLK", "IWM", "DIA"})
REQUIRED_NEWS_STREAMS = frozenset({"direct_news", "sector_news"})
_ADVERSE_PHRASES = (
    "bankruptcy", "fraud", "accounting investigation", "guidance cut", "cuts guidance",
    "share offering", "stock offering", "dilution", "default", "delisting", "restatement",
    "data breach", "ceo resigns", "ceo resigned", "credit downgrade",
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MAPPING_SOURCE_HASH = "14936e9065cdba1e6c9370b1cc17f2fb848ccf247fc04f2b7381e8005d3c6728"
_MAX_RAW_ARCHIVE_BYTES = 16 * 1024 * 1024
_UTF8_HASH_CHUNK_CHARS = 64 * 1024


@dataclass(frozen=True)
class ContextResult:
    action: str
    reasons: tuple[str, ...]
    market_receipt_hash: str | None = None
    news_receipt_hash: str | None = None
    macro_event_id: str | None = None


def _context_policy() -> dict[str, Decimal | int]:
    from .freeze import verify as verify_self
    errors = verify_self()
    if errors:
        raise ReceiptError("context package freeze verification failed: " + "; ".join(errors))
    raw = json.loads(Path(__file__).with_name("config.json").read_text(encoding="utf-8"))
    policy = plain_object(raw.get("context_gate"), "context_gate")
    expected = {
        "broad_adverse_bps", "tech_adverse_bps", "tech_support_floor_bps",
        "minimum_supportive_symbols",
    }
    if set(policy) != expected:
        raise ReceiptError("context threshold policy is incomplete")
    minimum = policy["minimum_supportive_symbols"]
    if type(minimum) is not int or not 1 <= minimum <= 5:
        raise ReceiptError("minimum_supportive_symbols is invalid")
    return {
        "broad_adverse_bps": decimal_string(policy["broad_adverse_bps"], "broad_adverse_bps"),
        "tech_adverse_bps": decimal_string(policy["tech_adverse_bps"], "tech_adverse_bps"),
        "tech_support_floor_bps": decimal_string(policy["tech_support_floor_bps"], "tech_support_floor_bps"),
        "minimum_supportive_symbols": minimum,
    }


def _sector_mapping() -> dict[str, frozenset[str]]:
    raw = json.loads(Path(__file__).with_name("sector_mapping.json").read_text(encoding="utf-8"))
    expected = {
        "schema_version", "mapping_id", "source_reference", "source_reference_sha256",
        "mapped_symbols", "applies_to", "limitations",
    }
    if type(raw) is not dict or set(raw) != expected or raw["schema_version"] != "1.0":
        raise ReceiptError("sector mapping schema is invalid")
    if raw["source_reference_sha256"] != _MAPPING_SOURCE_HASH:
        raise ReceiptError("sector mapping source binding is invalid")
    mapped = raw["mapped_symbols"]
    applies = plain_object(raw["applies_to"], "sector_mapping.applies_to")
    if type(mapped) is not list or mapped != sorted(set(mapped)):
        raise ReceiptError("mapped sector symbols must be sorted and unique")
    result: dict[str, frozenset[str]] = {}
    for target, symbols in applies.items():
        if type(symbols) is not list or symbols != sorted(set(symbols)) or set(symbols) - set(mapped):
            raise ReceiptError("target sector mapping is invalid")
        result[target] = frozenset(symbols)
    if set(result) != {"AAOI", "CIEN", "COHR", "FN", "LITE", "QQQ", "SPY"}:
        raise ReceiptError("sector mapping target coverage is incomplete")
    return result


def _canonical_item_time(value: Any, field: str) -> datetime:
    parsed = aware_utc(value, field)
    if value != parsed.isoformat():
        raise ReceiptError(f"{field} must use canonical UTC ISO-8601 form")
    return parsed


def _bounded_utf8_sha256(value: Any, remaining_bytes: int) -> tuple[int, str]:
    """Count and hash UTF-8 incrementally, failing before the aggregate bound is crossed."""
    if type(value) is not str:
        raise ReceiptError("raw provider page must contain UTF-8 text")
    digest = hashlib.sha256()
    total = 0
    try:
        for offset in range(0, len(value), _UTF8_HASH_CHUNK_CHARS):
            encoded = value[offset:offset + _UTF8_HASH_CHUNK_CHARS].encode("utf-8", "strict")
            total += len(encoded)
            if total > remaining_bytes:
                raise ReceiptError("embedded raw provider pages exceed the 16 MiB UTF-8 bound")
            digest.update(encoded)
    except UnicodeEncodeError as exc:
        raise ReceiptError("raw provider page is not valid UTF-8 text") from exc
    return total, digest.hexdigest()


def validate_market(receipt: ArchiveReceipt, cutoff: datetime) -> dict[str, dict[str, Decimal]]:
    if not isinstance(receipt, ArchiveReceipt) or receipt.kind != "MARKET_CONTEXT":
        raise ReceiptError("market context receipt is missing or has the wrong kind")
    receipt.validate_at(cutoff, max_age=timedelta(minutes=5))
    if set(receipt.payload) != {"bars"}:
        raise ReceiptError("market context payload fields do not match the frozen schema")
    bars = plain_object(receipt.payload["bars"], "market.bars")
    if set(bars) != MARKET_SYMBOLS:
        raise ReceiptError("market context must contain exactly SPY/QQQ/XLK/IWM/DIA")
    validated: dict[str, dict[str, Decimal]] = {}
    latest: datetime | None = None
    for symbol, raw in bars.items():
        bar = plain_object(raw, f"market.bars.{symbol}")
        if set(bar) != {"last", "session_vwap", "return_bps", "as_of"}:
            raise ReceiptError(f"market bar fields are invalid for {symbol}")
        as_of = _canonical_item_time(bar["as_of"], f"market.bars.{symbol}.as_of")
        if as_of > receipt.observed_at or receipt.observed_at - as_of > timedelta(minutes=5):
            raise ReceiptError(f"market bar is future-dated or stale within receipt for {symbol}")
        latest = as_of if latest is None or as_of > latest else latest
        validated[symbol] = {
            "last": decimal_string(bar["last"], f"{symbol}.last", positive=True),
            "session_vwap": decimal_string(bar["session_vwap"], f"{symbol}.session_vwap", positive=True),
            "return_bps": decimal_string(bar["return_bps"], f"{symbol}.return_bps"),
        }
    if latest != receipt.observed_at:
        raise ReceiptError("market receipt observed_at must equal the latest component timestamp")
    return validated


def validate_news(
    receipt: ArchiveReceipt, target_symbol: str, cutoff: datetime,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(receipt, ArchiveReceipt) or receipt.kind != "NEWS_ARCHIVE":
        raise ReceiptError("news archive receipt is missing or has the wrong kind")
    receipt.validate_at(cutoff)
    expected = {
        "target_symbol", "coverage_start", "coverage_end", "streams", "complete", "items", "raw_pages",
    }
    if set(receipt.payload) != expected:
        raise ReceiptError("news archive fields do not match the frozen schema")
    payload = receipt.payload
    if payload["target_symbol"] != target_symbol:
        raise ReceiptError("news archive target does not match the candidate")
    if type(payload["complete"]) is not bool or payload["complete"] is not True:
        raise ReceiptError("news archive coverage is unknown or incomplete")
    streams = payload["streams"]
    if type(streams) is not list or len(streams) != len(set(streams)) or set(streams) != REQUIRED_NEWS_STREAMS:
        raise ReceiptError("both direct_news and sector_news archive streams are required")
    point = aware_utc(cutoff, "receipt_cutoff")
    start = _canonical_item_time(payload["coverage_start"], "news.coverage_start")
    end = _canonical_item_time(payload["coverage_end"], "news.coverage_end")
    if end - start != timedelta(hours=24) or end < point - timedelta(minutes=5) or end > point:
        raise ReceiptError("news archive does not prove the required 24-hour point-in-time coverage")
    if receipt.observed_at != end:
        raise ReceiptError("news receipt observed_at must equal coverage_end")
    pages = payload["raw_pages"]
    if type(pages) is not list or not pages or len(pages) > 4096:
        raise ReceiptError("news context requires embedded raw provider pages")
    sector_symbols = _sector_mapping().get(target_symbol)
    if sector_symbols is None:
        raise ReceiptError("no frozen sector mapping exists for target")
    derived_items: list[dict[str, Any]] = []
    page_streams: set[str] = set()
    page_fields = {
        "stream", "window_start", "window_end", "page_index", "received_at",
        "raw_payload_hash", "raw_payload_utf8",
    }
    windows: dict[tuple[str, datetime, int], tuple[datetime, datetime, dict[str, Any]]] = {}
    raw_archive_bytes = 0
    for index, raw_page in enumerate(pages):
        page = plain_object(raw_page, f"news.raw_pages[{index}]")
        if set(page) != page_fields or page["stream"] not in REQUIRED_NEWS_STREAMS:
            raise ReceiptError("raw news page fields or stream are invalid")
        page_streams.add(page["stream"])
        raw_text = page["raw_payload_utf8"]
        raw_hash = page["raw_payload_hash"]
        if type(raw_hash) is not str or not _HEX64.fullmatch(raw_hash):
            raise ReceiptError("raw provider page must contain UTF-8 text and SHA-256")
        page_bytes, computed_hash = _bounded_utf8_sha256(
            raw_text, _MAX_RAW_ARCHIVE_BYTES - raw_archive_bytes,
        )
        raw_archive_bytes += page_bytes
        if computed_hash != raw_hash:
            raise ReceiptError("raw provider page hash mismatch")
        window_start = _canonical_item_time(page["window_start"], "news.raw_page.window_start")
        window_end = _canonical_item_time(page["window_end"], "news.raw_page.window_end")
        page_index = page["page_index"]
        if (window_start < start or window_end > end or window_end - window_start != timedelta(minutes=5)
                or int(window_start.timestamp()) % 300 != 0
                or type(page_index) is not int or page_index < 0):
            raise ReceiptError("raw provider page window or index is invalid")
        received = _canonical_item_time(page["received_at"], "news.raw_page.received_at")
        # Coverage describes market/publication time. Provider receipt is a separate
        # availability timestamp and may honestly trail the final window boundary.
        if (received < window_end or received > receipt.retrieved_at
                or received > receipt.archived_at or received > point):
            raise ReceiptError("raw provider page receipt is not point-in-time available")
        try:
            body = plain_object(json.loads(raw_text), "raw provider page")
        except (json.JSONDecodeError, ReceiptError) as exc:
            raise ReceiptError("raw provider page is not valid JSON") from exc
        rows = body.get("news")
        if type(rows) is not list or len(rows) > 2000 or any(type(row) is not dict for row in rows):
            raise ReceiptError("raw provider page lacks a news array")
        token = body.get("next_page_token")
        if token is not None and (not isinstance(token, str) or not token):
            raise ReceiptError("raw provider pagination token is invalid")
        window_key = (page["stream"], window_start, page_index)
        if window_key in windows:
            raise ReceiptError("duplicate or conflicting raw provider page identity")
        windows[window_key] = (window_end, received, body)
        row_fields = {"id", "symbols", "headline", "source", "created_at"}
        for raw_row_index, row in enumerate(rows):
            if set(row) != row_fields:
                raise ReceiptError("raw provider news row fields do not match the frozen schema")
            article_id = row["id"]
            if not isinstance(article_id, str) or not article_id:
                raise ReceiptError("raw provider article ID must be a non-empty string")
            symbols = row["symbols"]
            if type(symbols) is not list or not symbols or len(symbols) != len(set(symbols)):
                raise ReceiptError("raw provider symbols must be a non-empty unique array")
            if any(not isinstance(s, str) or not s.isascii() or s != s.upper() or not s.isalnum()
                   for s in symbols):
                raise ReceiptError("raw provider symbols must be uppercase ASCII tickers")
            for field in ("headline", "source"):
                if (not isinstance(row[field], str) or not row[field].strip()
                        or len(row[field]) > 1000):
                    raise ReceiptError(f"raw provider {field} must be bounded and non-empty")
            published = _canonical_item_time(row["created_at"], "news.raw_row.created_at")
            if published < start or published > end or published > received:
                raise ReceiptError("raw provider news row lies outside market coverage or availability")
            eligible = (
                target_symbol in symbols if page["stream"] == "direct_news"
                else bool(sector_symbols.intersection(symbols))
            )
            if not eligible:
                continue
            derived_items.append({
                "article_id": article_id,
                "stream": page["stream"],
                "symbols": list(symbols),
                "headline": row["headline"],
                "source": row["source"],
                "published_at": published.isoformat(),
                "first_received_at": received.isoformat(),
                "raw_payload_hash": raw_hash,
                "raw_page_window_start": window_start.isoformat(),
                "raw_page_index": page_index,
                "raw_row_index": raw_row_index,
                "raw_archive": True,
            })
    if page_streams != REQUIRED_NEWS_STREAMS:
        raise ReceiptError("embedded provider pages must cover both frozen streams")
    for stream in sorted(REQUIRED_NEWS_STREAMS):
        cursor = start
        while cursor < end:
            indices = sorted(index for s, opened, index in windows if s == stream and opened == cursor)
            if not indices or indices != list(range(indices[-1] + 1)):
                raise ReceiptError("raw archive has a missing window or pagination gap")
            for page_index in indices:
                window_end, _, body = windows[(stream, cursor, page_index)]
                if window_end != cursor + timedelta(minutes=5):
                    raise ReceiptError("raw archive window boundaries conflict")
                token = body.get("next_page_token")
                if page_index < indices[-1] and token is None:
                    raise ReceiptError("raw archive pagination is truncated")
                if page_index == indices[-1] and token is not None:
                    raise ReceiptError("raw archive final page is missing")
            cursor += timedelta(minutes=5)
    items = payload["items"]
    if type(items) is not list or len(items) > 2000 or len(derived_items) > 2000:
        raise ReceiptError("news items must be an array")
    item_fields = {
        "article_id", "stream", "symbols", "headline", "source", "published_at",
        "first_received_at", "raw_payload_hash", "raw_page_window_start",
        "raw_page_index", "raw_row_index", "raw_archive",
    }
    for index, raw in enumerate(items):
        item = plain_object(raw, f"news.items[{index}]")
        if set(item) != item_fields:
            raise ReceiptError("news item fields do not match the frozen schema")
        for field in (
            "article_id", "stream", "headline", "source", "published_at",
            "first_received_at", "raw_payload_hash", "raw_page_window_start",
        ):
            if type(item[field]) is not str:
                raise ReceiptError(f"news item {field} must be a JSON string")
        if type(item["symbols"]) is not list or any(type(symbol) is not str for symbol in item["symbols"]):
            raise ReceiptError("news item symbols must be an array of JSON strings")
        for field in ("raw_page_index", "raw_row_index"):
            if type(item[field]) is not int or item[field] < 0:
                raise ReceiptError(f"news item {field} must be a nonnegative JSON integer")
        if type(item["raw_archive"]) is not bool or item["raw_archive"] is not True:
            raise ReceiptError("news item raw_archive must be literal JSON true")
    order_key = lambda item: (
        item["published_at"], item["stream"], item["article_id"],
        item["raw_page_window_start"], item["raw_page_index"], item["raw_row_index"],
    )
    derived_items.sort(key=order_key)
    if items != derived_items:
        raise ReceiptError(
            "normalized news items must be the exact deterministic projection of every eligible raw row"
        )
    return tuple(derived_items)


def _market_state(
    bars: dict[str, dict[str, Decimal]], policy: dict[str, Decimal | int],
) -> str:
    returns = {symbol: row["return_bps"] for symbol, row in bars.items()}
    tech_adverse = policy["tech_adverse_bps"]
    broad_adverse = policy["broad_adverse_bps"]
    support_floor = policy["tech_support_floor_bps"]
    minimum = policy["minimum_supportive_symbols"]
    assert isinstance(tech_adverse, Decimal) and isinstance(broad_adverse, Decimal)
    assert isinstance(support_floor, Decimal) and isinstance(minimum, int)
    if returns["QQQ"] <= tech_adverse or returns["XLK"] <= tech_adverse:
        return "VETO"
    if sum(value <= broad_adverse for value in returns.values()) >= 3:
        return "VETO"
    if (sum(value >= 0 for value in returns.values()) >= minimum
            and returns["QQQ"] > support_floor and returns["XLK"] > support_floor):
        return "CLEAR"
    return "UNKNOWN"


def _has_adverse_news(items: tuple[dict[str, Any], ...], target: str) -> bool:
    relevant_sector_symbols = _sector_mapping().get(target)
    if relevant_sector_symbols is None:
        raise ReceiptError("no frozen sector mapping exists for target")
    for item in items:
        if item["stream"] == "sector_news" and not relevant_sector_symbols.intersection(item["symbols"]):
            continue
        # Headline text is inert data. It is normalized only for fixed phrase matching.
        normalized = " ".join(item["headline"].casefold().split())
        if any(phrase in normalized for phrase in _ADVERSE_PHRASES):
            return True
    return False


def evaluate_context(
    *, baseline_action: str, target_symbol: str, cutoff: datetime,
    market_receipt: ArchiveReceipt | None, news_receipt: ArchiveReceipt | None,
) -> ContextResult:
    """Apply context only after a baseline candidate exists; never promote an abstention."""
    if baseline_action != "PAPER_ENTRY_INTENT":
        return ContextResult("ABSTAIN", ("context cannot originate a trade",))
    macro = macro_state(cutoff)
    if macro.status == "UNKNOWN":
        return ContextResult("BLOCKED_DATA", (macro.reason,))
    if macro.status == "VETO":
        return ContextResult("ABSTAIN", (macro.reason,), macro_event_id=macro.event_id)
    errors: list[str] = []
    bars: dict[str, dict[str, Decimal]] | None = None
    items: tuple[dict[str, Any], ...] | None = None
    try:
        bars = validate_market(market_receipt, cutoff)  # type: ignore[arg-type]
    except (ReceiptError, TypeError, ValueError, KeyError) as exc:
        errors.append(f"market context unknown: {exc}")
    try:
        items = validate_news(news_receipt, target_symbol, cutoff)  # type: ignore[arg-type]
    except (ReceiptError, TypeError, ValueError, KeyError) as exc:
        errors.append(f"news context unknown: {exc}")
    if errors:
        return ContextResult(
            "BLOCKED_DATA", tuple(errors),
            getattr(market_receipt, "receipt_hash", None), getattr(news_receipt, "receipt_hash", None),
        )
    assert bars is not None and items is not None
    market = _market_state(bars, _context_policy())
    if market == "UNKNOWN":
        return ContextResult(
            "BLOCKED_DATA", ("market regime is mixed or ambiguous",),
            market_receipt.receipt_hash, news_receipt.receipt_hash,
        )
    if market == "VETO":
        return ContextResult(
            "ABSTAIN", ("frozen market-regime veto fired",),
            market_receipt.receipt_hash, news_receipt.receipt_hash,
        )
    if _has_adverse_news(items, target_symbol):
        return ContextResult(
            "ABSTAIN", ("frozen hard-adverse headline veto fired",),
            market_receipt.receipt_hash, news_receipt.receipt_hash,
        )
    return ContextResult(
        "ALLOW_EXISTING_CANDIDATE",
        ("existing price candidate survived frozen context vetoes",),
        market_receipt.receipt_hash, news_receipt.receipt_hash,
    )
