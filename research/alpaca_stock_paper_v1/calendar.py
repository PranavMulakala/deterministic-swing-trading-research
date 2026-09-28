"""Derive holding-review count from an official paper trading calendar."""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def completed_sessions(opened_at: datetime, as_of: datetime, calendar_rows) -> int:
    """Count sessions whose close occurred after entry and by the observation."""
    if any(not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None
           for t in (opened_at, as_of)) or opened_at > as_of:
        raise ValueError("invalid_holding_times")
    count = 0
    seen = set()
    for day, opening, closing in calendar_rows:
        if day in seen:
            raise ValueError("duplicate_session")
        seen.add(day)
        try:
            open_at = datetime.combine(day, time.fromisoformat(opening), NY)
            close_at = datetime.combine(day, time.fromisoformat(closing), NY)
        except (TypeError, ValueError):
            raise ValueError("invalid_session_time") from None
        if open_at >= close_at:
            raise ValueError("invalid_session_order")
        if opened_at < close_at <= as_of:
            count += 1
    return count
