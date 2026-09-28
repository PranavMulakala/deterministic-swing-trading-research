"""Frozen scheduled-macro abstention calendar for the context arm only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .receipts import ReceiptError, aware_utc


@dataclass(frozen=True)
class MacroState:
    status: str
    reason: str
    event_id: str | None = None


def _load() -> dict[str, Any]:
    from .freeze import verify as verify_self
    errors = verify_self()
    if errors:
        raise ReceiptError("macro package freeze verification failed: " + "; ".join(errors))
    raw = json.loads(Path(__file__).with_name("macro_calendar.json").read_text(encoding="utf-8"))
    expected = {
        "schema_version", "calendar_id", "retrieved_on", "timezone", "coverage_start",
        "coverage_end_exclusive", "policy", "sources", "events", "warning",
    }
    if type(raw) is not dict or set(raw) != expected or raw["schema_version"] != "1.0":
        raise ReceiptError("invalid frozen macro calendar schema")
    if raw["timezone"] != "America/New_York" or type(raw["events"]) is not list:
        raise ReceiptError("invalid frozen macro calendar timezone or events")
    if type(raw["sources"]) is not list or len(raw["sources"]) != 3:
        raise ReceiptError("invalid frozen macro source list")
    return raw


def macro_state(cutoff: datetime) -> MacroState:
    """Return VETO in a frozen event window, CLEAR in coverage, UNKNOWN outside it."""
    raw = _load()
    utc = aware_utc(cutoff, "receipt_cutoff")
    et = utc.astimezone(ZoneInfo(raw["timezone"]))
    coverage_start = datetime.fromisoformat(raw["coverage_start"])
    coverage_end = datetime.fromisoformat(raw["coverage_end_exclusive"])
    if et < coverage_start or et >= coverage_end:
        return MacroState("UNKNOWN", "cutoff lies outside the frozen macro-calendar coverage")
    required = {"id", "label", "source_index", "start_inclusive", "end_exclusive"}
    for event in raw["events"]:
        if type(event) is not dict or set(event) != required:
            raise ReceiptError("invalid frozen macro event")
        if isinstance(event["source_index"], bool) or not isinstance(event["source_index"], int):
            raise ReceiptError("invalid macro source index")
        if not 0 <= event["source_index"] < len(raw["sources"]):
            raise ReceiptError("macro source index is out of bounds")
        start = datetime.fromisoformat(event["start_inclusive"])
        end = datetime.fromisoformat(event["end_exclusive"])
        if start.tzinfo is None or end.tzinfo is None or start >= end:
            raise ReceiptError("invalid macro event window")
        if start <= et < end:
            return MacroState("VETO", f"scheduled macro abstention window: {event['label']}", event["id"])
    return MacroState("CLEAR", "no frozen scheduled-macro window contains the cutoff")
