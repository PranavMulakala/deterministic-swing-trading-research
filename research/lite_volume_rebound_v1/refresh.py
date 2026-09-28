"""Bounded GET-only LITE SIP/IEX refresh and causal feed comparison.

Run only when authorized to make market-data GET requests:
PYTHONPATH=src .venv/bin/python -m research.lite_volume_rebound_v1.refresh --output NEW_DIR
No order, account, position, or trading endpoint is called.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from research.lite_execution_data.collect import ReadOnlyClient, save
from research.lite_funded_comparison_v1.run import D, ROOT
from research.lite_reversal_v1.experiment import timestamp
from research.lite_volume_rebound_v1.run import decision

START = "2026-01-01T00:00:00Z"
END_EXCLUSIVE = "2026-09-26T00:00:00Z"
CALENDAR_END = "2026-09-25"
BAR_PATH = "/v2/stocks/LITE/bars"
PAGE_LIMIT = 10000
MAX_PAGES = 20
ENV_KEYS = ("ALPACA_PAPER_API_KEY", "ALPACA_PAPER_API_SECRET")
PINNED = ROOT / "research/lite_execution_data/runs/sip-bars-01/LITE_5Min.json"
PINNED_MANIFEST = PINNED.with_name("manifest.json")
OVERLAP_DAY = "2026-09-04"


def credentials(env=None, path=None):
    """Load only the two paper keys; do not export or log unrelated .env values."""
    env = os.environ if env is None else env
    values = {key: env.get(key, "") for key in ENV_KEYS}
    if all(values.values()):
        return values[ENV_KEYS[0]], values[ENV_KEYS[1]]
    path = ROOT / ".env" if path is None else Path(path)
    if path.is_symlink():
        raise PermissionError("Credential file may not be a symbolic link")
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise PermissionError("Owner-only local paper credential file required")
    found = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in ENV_KEYS:
                continue
            if key in found:
                raise ValueError(f"Duplicate paper credential key at line {line_number}")
            found.add(key)
            if not values[key]:
                values[key] = value.strip()
    if not all(values.values()):
        raise ValueError("Both paper market-data credentials are required")
    return values[ENV_KEYS[0]], values[ENV_KEYS[1]]


def client_from_local_keys():
    key, secret = credentials()
    return ReadOnlyClient(key, secret, timeout=20)


def fetch_pages(client, feed, output):
    if feed not in ("sip", "iex"):
        raise ValueError("Unsupported feed")
    query = {"feed": feed, "adjustment": "raw", "timeframe": "5Min",
             "start": START, "end": END_EXCLUSIVE, "sort": "asc", "limit": PAGE_LIMIT}
    rows, files, seen = [], [], set()
    token = None
    for page_number in range(1, MAX_PAGES + 1):
        request_query = {**query, **({"page_token": token} if token else {})}
        reply = client._request("GET", BAR_PATH, data_api=True, query=request_query)
        if not isinstance(reply, dict) or reply.get("symbol") != "LITE" or not isinstance(reply.get("bars"), list):
            raise ValueError("Unexpected bar response shape or symbol")
        files.append(save(output / f"LITE_5Min_{feed}_page_{page_number:02}.json", reply))
        chunk = reply["bars"]
        rows.extend(chunk)
        token = reply.get("next_page_token")
        if not token:
            return {"feed": feed, "query": query, "path": BAR_PATH, "rows": rows,
                    "pages": page_number, "complete": True}, files
        if not isinstance(token, str) or token in seen or not chunk:
            raise ValueError("Stalled bar pagination")
        seen.add(token)
    raise ValueError("Bar page budget exhausted; partial raw pages retained")


def calendar_sessions(raw):
    if not isinstance(raw, list):
        raise ValueError("Unexpected calendar response")
    result = {}
    for row in raw:
        day = row.get("date")
        if not isinstance(day, str) or not "2026-01-01" <= day <= CALENDAR_END or day in result:
            raise ValueError("Unexpected calendar date")
        result[day] = row
    if not result:
        raise ValueError("Empty calendar")
    return dict(sorted(result.items()))


def validate_feed(payload, calendar):
    """Retain sparse IEX sessions; reject malformed bars and report coverage."""
    if payload.get("complete") is not True or payload.get("path") != BAR_PATH:
        raise ValueError("Incomplete or wrong bar payload")
    query = payload["query"]
    if any(query.get(key) != value for key, value in
           (("feed", payload["feed"]), ("adjustment", "raw"), ("timeframe", "5Min"),
            ("start", START), ("end", END_EXCLUSIVE))):
        raise ValueError("Wrong feed or bounds")
    groups = defaultdict(dict)
    previous = None
    for row in payload["rows"]:
        dt = timestamp(row["t"])
        if previous is not None and dt <= previous:
            raise ValueError("Duplicate or out-of-order bar")
        previous = dt
        if not datetime.fromisoformat(START.replace("Z", "+00:00")) <= dt.astimezone(timezone.utc) < datetime.fromisoformat(END_EXCLUSIVE.replace("Z", "+00:00")):
            raise ValueError("Bar outside request bounds")
        minute = dt.hour * 60 + dt.minute
        if not 570 <= minute < 960:
            continue
        day = dt.date().isoformat()
        if day not in calendar or dt.second or dt.microsecond or minute % 5:
            raise ValueError("Unexpected regular-session bar")
        values = [D(row[key]) for key in ("o", "h", "l", "c", "v")]
        o, h, low, close, volume = values
        if not all(v.is_finite() and v > 0 for v in values) or not low <= min(o, close) <= max(o, close) <= h:
            raise ValueError("Invalid OHLCV")
        if minute in groups[day]:
            raise ValueError("Duplicate regular-session bar")
        groups[day][minute] = row
    expected = set(range(570, 960, 5))
    standard = [day for day, row in calendar.items() if row.get("open") == "09:30" and row.get("close") == "16:00"]
    missing = {day: sorted(expected - set(groups[day])) for day in standard if set(groups[day]) != expected}
    morning = {day: [groups[day][minute] for minute in range(570, 600, 5)]
               for day in standard if set(range(570, 600, 5)).issubset(groups[day])}
    return groups, morning, {"standard_sessions": len(standard),
                             "complete_sessions": len(standard) - len(missing),
                             "missing_regular_bars_by_session": missing,
                             "complete_first_30m_sessions": len(morning),
                             "regular_bar_count": sum(len(group) for group in groups.values())}


def signal_comparison(calendar, sip_morning, iex_morning):
    standard = [day for day, row in calendar.items() if row.get("open") == "09:30" and row.get("close") == "16:00"]
    signals = {}
    for feed, morning in (("sip", sip_morning), ("iex", iex_morning)):
        hits = []
        reasons = Counter()
        for index, day in enumerate(standard):
            prior_days = standard[max(0, index - 20):index]
            if len(prior_days) != 20:
                reasons["warmup"] += 1
            elif day not in morning or any(prior not in morning for prior in prior_days):
                reasons["missing_current_or_prior_morning"] += 1
            else:
                # decision reads only first six bars and the preceding 20 mornings.
                current = [SimpleNamespace(**row) for row in morning[day]]
                previous = [[SimpleNamespace(**row) for row in morning[prior]] for prior in prior_days]
                found = decision(current, previous)
                if found:
                    hits.append({"date": day, "limit": str(found["limit"]),
                                 "morning_volume": str(found["morning_volume"]),
                                 "prior_20_mean_volume": str(found["prior_20_mean_volume"])})
        signals[feed] = {"count": len(hits), "dates": [row["date"] for row in hits],
                         "details": hits, "not_evaluable": dict(reasons)}
    sip_dates, iex_dates = set(signals["sip"]["dates"]), set(signals["iex"]["dates"])
    signals["alignment"] = {"both": sorted(sip_dates & iex_dates),
                            "sip_only": sorted(sip_dates - iex_dates),
                            "iex_only": sorted(iex_dates - sip_dates)}
    return signals


def pinned_overlap(fresh, pinned_path=PINNED, manifest_path=PINNED_MANIFEST):
    """Compare the shared raw regular-session day after verifying the old pin."""
    manifest = json.loads(manifest_path.read_bytes())
    expected = next((item["sha256"] for item in manifest["files"]
                     if item["file"] == pinned_path.name), None)
    raw = pinned_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if not expected or digest != expected:
        raise ValueError("Pinned SIP source hash mismatch")
    pinned = json.loads(raw)
    if pinned.get("path") != BAR_PATH or pinned.get("query", {}).get("feed") != "sip" or pinned.get("complete") is not True:
        raise ValueError("Wrong pinned SIP source")
    def overlap_rows(payload):
        return {row["t"]: row for row in payload["rows"]
                if timestamp(row["t"]).date().isoformat() == OVERLAP_DAY
                and 570 <= timestamp(row["t"]).hour * 60 + timestamp(row["t"]).minute < 960}
    old, new = overlap_rows(pinned), overlap_rows(fresh)
    differing = sorted(key for key in old.keys() | new.keys() if old.get(key) != new.get(key))
    return {"day": OVERLAP_DAY, "pinned_sha256": digest,
            "pinned_regular_bars": len(old), "fresh_regular_bars": len(new),
            "data_equivalent": len(old) == 78 and not differing,
            "differing_timestamps": differing}


def execute(client, output, *, pinned_path=PINNED, manifest_path=PINNED_MANIFEST):
    if output.exists():
        raise FileExistsError("Output already exists")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"status": "GET_ONLY_MARKET_DATA", "requested_at": datetime.now(timezone.utc).isoformat(),
                "start": START, "end_exclusive": END_EXCLUSIVE,
                "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "files": []}
    raw_calendar = client._request("GET", "/v2/calendar", query={"start": "2026-01-01", "end": CALENDAR_END})
    manifest["files"].append(save(output / "calendar.json", raw_calendar))
    calendar = calendar_sessions(raw_calendar)
    feeds, coverage, mornings = {}, {}, {}
    for feed in ("sip", "iex"):
        payload, pages = fetch_pages(client, feed, output)
        manifest["files"].extend(pages)
        manifest["files"].append(save(output / f"LITE_5Min_{feed}.json", payload))
        _, mornings[feed], coverage[feed] = validate_feed(payload, calendar)
        feeds[feed] = payload
    signals = signal_comparison(calendar, mornings["sip"], mornings["iex"])
    overlap = pinned_overlap(feeds["sip"], pinned_path, manifest_path)
    sip_complete = not coverage["sip"]["missing_regular_bars_by_session"]
    status = ("COMPLETE_SIP_WITH_IEX_COVERAGE_REPORTED" if sip_complete and overlap["data_equivalent"]
              else "INCOMPLETE_SIP_REVIEW_REQUIRED" if not sip_complete
              else "PINNED_OVERLAP_DRIFT_REVIEW_REQUIRED")
    report = {"status": status, "start": START, "end_exclusive": END_EXCLUSIVE,
              "feeds": {feed: {"pages": feeds[feed]["pages"], "raw_rows": len(feeds[feed]["rows"]),
                               **coverage[feed]} for feed in ("sip", "iex")},
              "signals": signals, "pinned_overlap": overlap,
              "limits": "Historical SIP/IEX bars are not executable quotes or proof of order fills; this is not an untouched holdout."}
    manifest["files"].append(save(output / "report.json", report))
    save(output / "manifest.json", manifest)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    report = execute(client_from_local_keys(), args.output)
    print(json.dumps({"status": report["status"],
                      "sip_complete_sessions": report["feeds"]["sip"]["complete_sessions"],
                      "iex_complete_sessions": report["feeds"]["iex"]["complete_sessions"],
                      "sip_signals": report["signals"]["sip"]["count"],
                      "iex_signals": report["signals"]["iex"]["count"],
                      "pinned_overlap_equivalent": report["pinned_overlap"]["data_equivalent"]}, indent=2))
    if report["status"] != "COMPLETE_SIP_WITH_IEX_COVERAGE_REPORTED":
        raise SystemExit("Refresh failed validation; inspect report in the new output directory")


if __name__ == "__main__":
    main()
