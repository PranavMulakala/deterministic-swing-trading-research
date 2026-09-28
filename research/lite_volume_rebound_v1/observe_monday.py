"""One-shot, GET-only IEX LITE 10:00 signal observer; never submits orders."""
from __future__ import annotations

import argparse
from datetime import datetime, time, timezone
from decimal import Decimal, DecimalException
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from research.lite_execution_data.collect import save
from swingbot.alpaca_paper import AlpacaPaperError
from research.lite_reversal_v1.experiment import timestamp
from research.lite_volume_rebound_v1.refresh import (
    BAR_PATH, END_EXCLUSIVE, START, calendar_sessions, client_from_local_keys,
    validate_feed,
)
from research.lite_volume_rebound_v1.run import decision

MONDAY = "2026-09-28"
NY = ZoneInfo("America/New_York")
WINDOW_START = datetime(2026, 9, 28, 10, 0, tzinfo=NY)
WINDOW_END = datetime(2026, 9, 28, 10, 5, tzinfo=NY)
QUERY = {"feed": "iex", "adjustment": "raw", "timeframe": "5Min",
         "start": "2026-09-28T13:30:00Z", "end": "2026-09-28T13:59:59Z",
         "sort": "asc", "limit": 100}


def verified_history(folder):
    """Read only the saved refresh; verify every manifest hash before use."""
    manifest = json.loads((folder / "manifest.json").read_bytes())
    if manifest.get("status") != "GET_ONLY_MARKET_DATA" or manifest.get("start") != START or manifest.get("end_exclusive") != END_EXCLUSIVE:
        raise ValueError("Wrong refresh manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Missing refresh files")
    seen = set()
    for item in files:
        name = item.get("file")
        if not isinstance(name, str) or Path(name).name != name or name in seen:
            raise ValueError("Unsafe or duplicate refresh file")
        seen.add(name)
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != item.get("sha256"):
            raise ValueError("Refresh file hash mismatch")
    if not {"report.json", "calendar.json", "LITE_5Min_iex.json"}.issubset(seen):
        raise ValueError("Required refresh file absent")
    report = json.loads((folder / "report.json").read_bytes())
    if (report.get("status") != "COMPLETE_SIP_WITH_IEX_COVERAGE_REPORTED"
            or report.get("pinned_overlap", {}).get("data_equivalent") is not True):
        raise ValueError("Refresh validation did not pass")
    calendar = calendar_sessions(json.loads((folder / "calendar.json").read_bytes()))
    if max(calendar) != "2026-09-25":
        raise ValueError("Refresh calendar does not reach prior Friday")
    payload = json.loads((folder / "LITE_5Min_iex.json").read_bytes())
    if payload.get("feed") != "iex":
        raise ValueError("History must be IEX")
    _, morning, _ = validate_feed(payload, calendar)
    standard = [day for day, row in calendar.items()
                if row.get("open") == "09:30" and row.get("close") == "16:00"]
    previous_days = standard[-20:]
    if len(previous_days) != 20 or previous_days[-1] != "2026-09-25" or any(day not in morning for day in previous_days):
        raise ValueError("Missing one of the prior 20 IEX opening mornings")
    return [[SimpleNamespace(**row) for row in morning[day]] for day in previous_days], previous_days


def monday_bars(reply):
    if not isinstance(reply, dict) or reply.get("symbol") != "LITE" or not isinstance(reply.get("bars"), list):
        raise ValueError("Wrong Monday bar response")
    if reply.get("next_page_token"):
        raise ValueError("Monday bars were truncated")
    found = {}
    for row in reply["bars"]:
        dt = timestamp(row["t"])
        minute = dt.hour * 60 + dt.minute
        if dt.date().isoformat() != MONDAY or not 570 <= minute < 600 or minute % 5 or dt.second or dt.microsecond:
            raise ValueError("Out-of-window or incomplete Monday bar")
        if minute in found:
            raise ValueError("Duplicate Monday bar")
        values = [Decimal(str(row[key])) for key in ("o", "h", "l", "c", "v")]
        o, high, low, close, volume = values
        if not all(value.is_finite() and value > 0 for value in values) or not low <= min(o, close) <= max(o, close) <= high:
            raise ValueError("Malformed Monday OHLCV")
        found[minute] = row
    if set(found) != set(range(570, 600, 5)):
        raise ValueError("Missing completed Monday bar")
    return [SimpleNamespace(**found[minute]) for minute in range(570, 600, 5)]


def observe(client, history_dir, now=lambda: datetime.now(timezone.utc)):
    base = {"date": MONDAY, "symbol": "LITE", "feed": "iex", "orders_sent": 0,
            "mode": "GET_ONLY_SIGNAL_OBSERVER", "proposal": None}
    try:
        previous, previous_days = verified_history(history_dir)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, DecimalException):
        return {**base, "status": "BLOCKED", "reason": "REFRESH_INVALID"}
    before = now().astimezone(NY)
    if not WINDOW_START <= before < WINDOW_END:
        return {**base, "status": "BLOCKED", "reason": "OUTSIDE_1000_TO_1005_WINDOW"}
    try:
        calendar = client._request("GET", "/v2/calendar", query={"start": MONDAY, "end": MONDAY})
        if (not isinstance(calendar, list) or len(calendar) != 1 or calendar[0].get("date") != MONDAY
                or calendar[0].get("open") != "09:30" or calendar[0].get("close") != "16:00"):
            return {**base, "status": "BLOCKED", "reason": "MARKET_CALENDAR_CLOSED_OR_UNKNOWN"}
        clock = client._request("GET", "/v2/clock")
        clock_time = timestamp(clock["timestamp"])
        if (clock.get("is_open") is not True or not WINDOW_START <= clock_time < WINDOW_END
                or abs((clock_time - before).total_seconds()) > 60):
            return {**base, "status": "BLOCKED", "reason": "MARKET_CLOCK_CLOSED_OR_STALE"}
        request_started = now().astimezone(NY)
        if not WINDOW_START <= request_started < WINDOW_END:
            return {**base, "status": "BLOCKED", "reason": "OUTSIDE_1000_TO_1005_WINDOW"}
        reply = client._request("GET", BAR_PATH, data_api=True, query=QUERY)
        observed = now().astimezone(NY)
        if not WINDOW_START <= observed < WINDOW_END:
            return {**base, "status": "BLOCKED", "reason": "STALE_AFTER_BAR_REQUEST"}
        bars = monday_bars(reply)
        result = decision(bars, previous)
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            DecimalException, AlpacaPaperError):
        return {**base, "status": "BLOCKED", "reason": "MARKET_DATA_UNAVAILABLE_OR_INVALID"}
    common = {**base, "observed_at": observed.isoformat(), "prior_20_dates": previous_days,
              "completed_bar_times": [bar.t for bar in bars]}
    if result is None:
        return {**common, "status": "NO_SIGNAL", "reason": "RULE_NOT_MET"}
    return {**common, "status": "SIGNAL_PROPOSAL", "reason": "RULE_MET",
            "proposal": {"side": "buy", "shares_research": 5,
                         "limit_price": str(result["limit"]),
                         "opening_price_target_research": str(bars[0].o),
                         "eligible_bar": "10:00-10:05 America/New_York",
                         "morning_volume": str(result["morning_volume"]),
                         "prior_20_mean_volume": str(result["prior_20_mean_volume"]),
                         "cash_and_quote_not_verified": True,
                         "order_submitted": False}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    # History and clock preflight can block without loading credentials.
    try:
        verified_history(args.refresh)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, DecimalException):
        result = {"date": MONDAY, "symbol": "LITE", "feed": "iex", "orders_sent": 0,
                  "mode": "GET_ONLY_SIGNAL_OBSERVER", "proposal": None,
                  "status": "BLOCKED", "reason": "REFRESH_INVALID"}
    else:
        current = datetime.now(timezone.utc).astimezone(NY)
        if not WINDOW_START <= current < WINDOW_END:
            result = {"date": MONDAY, "symbol": "LITE", "feed": "iex", "orders_sent": 0,
                      "mode": "GET_ONLY_SIGNAL_OBSERVER", "proposal": None,
                      "status": "BLOCKED", "reason": "OUTSIDE_1000_TO_1005_WINDOW"}
        else:
            result = observe(client_from_local_keys(), args.refresh)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save(args.output, result)
    print(json.dumps({"status": result["status"], "reason": result["reason"],
                      "feed": result["feed"], "orders_sent": 0,
                      "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
