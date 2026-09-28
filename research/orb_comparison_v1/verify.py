"""Offline snapshot integrity and coverage report; never evaluates profit."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
STOCKS = ("LITE", "COHR", "CIEN", "FN", "AAOI")
JOBS = tuple((s, m) for s in STOCKS for m in (1, 5)) + (("SPY", 5), ("QQQ", 5))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def calendar_sessions(rows):
    result = {}
    previous = ""
    for row in rows:
        day = row["date"]
        if day <= previous or datetime.strptime(day, "%Y-%m-%d").strftime("%Y-%m-%d") != day:
            raise ValueError("Duplicate, unordered or invalid calendar date")
        start = datetime.fromisoformat(f"{day}T{row['open']}").replace(tzinfo=NY)
        end = datetime.fromisoformat(f"{day}T{row['close']}").replace(tzinfo=NY)
        if start.strftime("%H:%M") != "09:30" or end <= start or (end-start).total_seconds() % 300:
            raise ValueError("Invalid regular session")
        result[day] = (start, end)
        previous = day
    if not result:
        raise ValueError("Empty calendar")
    return result


def parse_bars(payload, symbol, step, sessions):
    q = payload.get("query", {})
    expected = {"feed": "sip", "adjustment": "raw", "timeframe": f"{step}Min",
                "start": "2025-11-01T00:00:00Z", "end": "2026-09-05T00:00:00Z",
                "asof": "2026-09-04", "sort": "asc", "limit": 10000}
    if payload.get("complete") is not True or q != expected or payload.get("path") != f"/v2/stocks/{symbol}/bars":
        raise ValueError("Unmatched or incomplete bar provenance")
    if type(payload.get("pages")) is not int or payload["pages"] < 1:
        raise ValueError("Invalid page count")
    if not isinstance(payload.get("rows"), list) or not payload["rows"]:
        raise ValueError("Empty bars")
    start_bound = datetime.fromisoformat(q["start"].replace("Z", "+00:00"))
    end_bound = datetime.fromisoformat(q["end"].replace("Z", "+00:00"))
    grouped = {d: {} for d in sessions}
    prev = None
    extended = 0
    for row in payload["rows"]:
        timestamp = datetime.fromisoformat(row["t"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None or not start_bound <= timestamp <= end_bound:
            raise ValueError("Timestamp outside query or without timezone")
        if prev is not None and timestamp <= prev:
            raise ValueError("Duplicate or unordered bars")
        prev = timestamp
        timestamp = timestamp.astimezone(NY)
        if timestamp.second or timestamp.microsecond or timestamp.minute % step:
            raise ValueError("Misaligned bar")
        for field in ("o", "h", "l", "c", "v", "vw"):
            value = row.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError("Nonpositive or invalid bar value")
        if not row["l"] <= min(row["o"], row["c"]) <= max(row["o"], row["c"]) <= row["h"]:
            raise ValueError("Invalid OHLC geometry")
        day = timestamp.date().isoformat()
        if day in sessions and sessions[day][0] <= timestamp < sessions[day][1]:
            grouped[day][timestamp] = row
        else:
            extended += 1
    coverage = []
    for day, (start, end) in sessions.items():
        expected_times = [start + timedelta(minutes=m) for m in range(0, int((end-start).total_seconds()/60), step)]
        missing = [t.strftime("%H:%M") for t in expected_times if t not in grouped[day]]
        coverage.append({"day": day, "evaluation": day >= "2026-01-01", "expected": len(expected_times),
                         "present": len(grouped[day]), "missing": missing,
                         "opening_window_complete": all(start+timedelta(minutes=m) in grouped[day] for m in range(0, 5, step))})
    return grouped, {"symbol": symbol, "minutes": step, "rows": len(payload["rows"]),
                     "extended_or_outside_calendar_rows": extended, "sessions": coverage}


def reconciliation(ones, fives):
    checked = 0
    mismatches = []
    incomplete = 0
    for day in fives:
        for timestamp, five in fives[day].items():
            minute_rows = [ones[day].get(timestamp + timedelta(minutes=m)) for m in range(5)]
            if any(r is None for r in minute_rows):
                incomplete += 1
                continue
            aggregate = {"o": minute_rows[0]["o"], "c": minute_rows[-1]["c"],
                         "h": max(r["h"] for r in minute_rows), "l": min(r["l"] for r in minute_rows),
                         "v": sum(r["v"] for r in minute_rows)}
            fields = [key for key in aggregate if not math.isclose(aggregate[key], five[key], rel_tol=1e-10, abs_tol=1e-6)]
            checked += 1
            if fields:
                mismatches.append({"time": timestamp.isoformat(), "fields": fields})
    return {"complete_windows_checked": checked, "incomplete_one_minute_windows": incomplete,
            "mismatches": mismatches, "vwap_comparison": "not_tested"}


def verify(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    expected_files = {"calendar.json"} | {f"{s}_{m}Min.json" for s, m in JOBS}
    names = [f["file"] for f in manifest["files"]]
    if manifest.get("complete") is not True or manifest.get("errors") or set(names) != expected_files or len(names) != len(expected_files):
        raise ValueError("Incomplete manifest or unexpected file set")
    for entry in manifest["files"]:
        path = folder / entry["file"]
        if path.is_symlink() or sha(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            raise ValueError("Snapshot integrity failed")
    sessions = calendar_sessions(json.loads((folder / "calendar.json").read_text()))
    if min(sessions) != "2025-11-03" or max(sessions) != "2026-09-04":
        raise ValueError("Calendar bounds mismatch")
    all_bars, details, totals = {}, {}, []
    for symbol, step in JOBS:
        name = f"{symbol}_{step}Min"
        all_bars[name], details[name] = parse_bars(json.loads((folder / f"{name}.json").read_text()), symbol, step, sessions)
        rows = details[name]["sessions"]
        totals.append({"symbol": symbol, "minutes": step, "rows": details[name]["rows"],
                       "warmup_full": sum(not r["evaluation"] and not r["missing"] for r in rows),
                       "evaluation_full": sum(r["evaluation"] and not r["missing"] for r in rows),
                       "evaluation_opening_complete": sum(r["evaluation"] and r["opening_window_complete"] for r in rows),
                       "evaluation_missing_bars": sum(len(r["missing"]) for r in rows if r["evaluation"])})
    matched = [day for day in sessions if day >= "2026-01-01" and all(
        not next(r for r in details[f"{symbol}_5Min"]["sessions"] if r["day"] == day)["missing"] for symbol in STOCKS)]
    reconciled = {s: reconciliation(all_bars[f"{s}_1Min"], all_bars[f"{s}_5Min"]) for s in STOCKS}
    # This measures warmup availability, not price/risk eligibility or profit.
    days = list(sessions)
    warmup = {}
    for symbol in STOCKS:
        rows = {r["day"]: r for r in details[f"{symbol}_5Min"]["sessions"]}
        available = []
        for index, day in enumerate(days):
            if day < "2026-01-01":
                continue
            previous = days[max(0, index-20):index]
            if len(previous) == 20 and all(not rows[d]["missing"] for d in previous):
                available.append(day)
        warmup[symbol] = {"evaluation_sessions_with_full_prior_20": len(available),
                          "first_available": available[0] if available else None,
                          "unavailable_days": [d for d in days if d >= "2026-01-01" and d not in available]}
    return {"status": "integrity_verified_coverage_measured_not_execution_validated",
            "manifest_sha256": sha(folder / "manifest.json"), "verifier_sha256": sha(__file__),
            "calendar_sessions": len(sessions), "evaluation_sessions": sum(d >= "2026-01-01" for d in sessions),
            "warmup_sessions": sum(d < "2026-01-01" for d in sessions), "files": totals,
            "matched_full_5minute_evaluation_sessions": len(matched), "matched_days": matched,
            "prior_input_coverage": warmup, "reconciliation": reconciled, "coverage": details,
            "unresolved": ["corporate_action_history", "original_bar_receipt_and_revisions", "historical_quotes_and_halts", "news_event_text_and_receipt"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.folder)
    if args.output:
        with args.output.open("x") as handle:
            json.dump(result, handle, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("coverage", "matched_days", "reconciliation")}, indent=2))
    print(json.dumps({s: {"checked": r["complete_windows_checked"], "mismatches": len(r["mismatches"]),
                           "incomplete": r["incomplete_one_minute_windows"]} for s, r in result["reconciliation"].items()}, indent=2))


if __name__ == "__main__":
    main()
