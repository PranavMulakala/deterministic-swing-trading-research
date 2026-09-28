"""Operational revision 3 around the unchanged frozen stock strategy/runtime.

Freshness is checked against wall time before any ledger access. Closed-session
coverage is derived independently of after-hours quotes. Coverage reports do not
alter historical cycles, trades, or original session counters.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

from research.agentic_portfolio_paper_10000_v1.profile import SCHEDULED_SESSION_DATES
from research.agentic_stock_paper_free_v2.runtime import (
    RuntimeBlocked, aware, atomic_write, blocked_status, load_config, process_cycle,
    validate_cycle,
)

NY = ZoneInfo("America/New_York")
QUALITY_POLICY = {"version": "session-coverage-v1", "minimum_cycles": 60,
                  "maximum_gap_seconds": 900, "edge_tolerance_seconds": 900}


def session_bounds(day):
    if day not in SCHEDULED_SESSION_DATES:
        raise RuntimeBlocked("date outside frozen session calendar")
    return (datetime.fromisoformat(day + "T09:30:00").replace(tzinfo=NY),
            datetime.fromisoformat(day + "T16:00:00").replace(tzinfo=NY))


def market_open(now):
    local = now.astimezone(NY)
    day = local.date().isoformat()
    if day not in SCHEDULED_SESSION_DATES:
        return False
    start, end = session_bounds(day)
    return start <= local < end


def assess_day(day, points):
    start, end = session_bounds(day)
    points = sorted(set(p for p in points if start <= p < end))
    gaps = [(b-a).total_seconds() for a,b in zip(points, points[1:])]
    first_gap = (points[0]-start).total_seconds() if points else 23400
    last_gap = (end-points[-1]).total_seconds() if points else 23400
    reasons = []
    if len(points) < QUALITY_POLICY["minimum_cycles"]:
        reasons.append("fewer_than_60_valid_cycles")
    if first_gap > 900: reasons.append("opening_coverage_missing")
    if last_gap > 900: reasons.append("closing_coverage_missing")
    if max(gaps, default=23400) > 900: reasons.append("intraday_gap_over_15_minutes")
    return {"date": day, "valid_cycles": len(points),
            "first_cycle": points[0].isoformat() if points else None,
            "last_cycle": points[-1].isoformat() if points else None,
            "maximum_gap_seconds": max([first_gap,last_gap]+gaps),
            "status": "QUALIFIED" if not reasons else "INCOMPLETE_COVERAGE",
            "reasons": reasons}


def session_report(state, now):
    path = state / "runtime.sqlite"
    if not path.exists():
        return {"policy": QUALITY_POLICY, "completed_sessions": 0,
                "qualified_sessions": 0, "days": [], "pending_cycles": 0}
    if path.is_symlink(): raise RuntimeBlocked("journal may not be a symlink")
    by_day = {}
    with sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True) as db:
        pending = db.execute("SELECT count(*) FROM cycles WHERE status='PENDING'").fetchone()[0]
        for created, encoded in db.execute("SELECT created_at,output_json FROM cycles WHERE status='COMPLETE' ORDER BY created_at"):
            output = json.loads(encoded)
            point = aware(created, "created_at")
            if output.get("decision_at") != created or output.get("status") != "PAPER_STOCK_CYCLE_COMPLETE":
                raise RuntimeBlocked("stored cycle identity mismatch")
            day = point.astimezone(NY).date().isoformat()
            if day in SCHEDULED_SESSION_DATES and market_open(point):
                by_day.setdefault(day, []).append(point)
    days = []
    if by_day:
        for day in SCHEDULED_SESSION_DATES:
            if day < min(by_day): continue
            _, end = session_bounds(day)
            if now < end + timedelta(minutes=5): continue
            days.append(assess_day(day, by_day.get(day, [])))
    return {"policy": QUALITY_POLICY, "completed_sessions": len(days),
            "qualified_sessions": sum(d["status"] == "QUALIFIED" for d in days),
            "pending_cycles": pending, "days": days,
            "note": "Coverage audit only; historical session counters and trades are unchanged."}


def run_once(input_path, provider_status, state, now=None):
    now = aware(now or datetime.now(timezone.utc), "wall time")
    load_config()
    coverage = session_report(state, now)
    try:
        if coverage["pending_cycles"]:
            raise RuntimeBlocked("pending cycle requires inspection")
        if not market_open(now):
            result = {**blocked_status("outside regular session; no new decisions", checked_at=now),
                      "status": "MARKET_CLOSED"}
        else:
            if input_path.is_symlink() or provider_status.is_symlink():
                raise RuntimeBlocked("provider files may not be symlinks")
            if input_path.stat().st_size > 32*1024*1024 or provider_status.stat().st_size > 65536:
                raise RuntimeBlocked("provider file exceeds size limit")
            status = json.loads(provider_status.read_text())
            if status.get("status") != "PROVIDER_CYCLE_READY":
                raise RuntimeBlocked("provider blocked: " + str(status.get("reason", "unknown")))
            raw = json.loads(input_path.read_text())
            cycle, decision, entries, management = validate_cycle(raw)
            if status.get("cycle_id") != cycle["cycle_id"]:
                raise RuntimeBlocked("provider status and cycle disagree")
            if not market_open(decision) or decision.astimezone(NY).date() != now.astimezone(NY).date():
                raise RuntimeBlocked("cycle belongs to a different/closed session")
            for field, point in (("decision", decision), ("provider", aware(status.get("checked_at"), "provider")),
                                 ("coverage", aware(cycle["coverage"]["stock_observed_at"], "coverage"))):
                if not 0 <= (now-point).total_seconds() <= 300:
                    raise RuntimeBlocked(field+" stale or future relative to wall clock")
            for packet in entries + management:
                packet.validate_at(now, timedelta(minutes=5))
            if cycle["completed_session_date"] is not None:
                raise RuntimeBlocked("intraday cycle cannot declare a completed session")
            result = process_cycle(raw, state)
            result["checked_at"] = now.isoformat()
            if result.get("replay"):
                result["status"] = "NO_NEW_CYCLE"
            review = result["review"]
            review["legacy_completed_sessions"] = review["completed_sessions"]
            review["completed_sessions"] = coverage["qualified_sessions"]
            review["eligible_for_review_not_proof"] = (
                coverage["qualified_sessions"] >= review["minimum_completed_sessions"]
                and review["closed_trades"] >= review["minimum_closed_trades"])
    except (RuntimeBlocked, OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        result = blocked_status(str(exc), checked_at=now)
    result["session_coverage"] = coverage
    result["operations_version"] = "free-stock-operations-v3"
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("/var/lib/agentic-stock-free-input/latest.json"))
    p.add_argument("--provider-status", type=Path, default=Path("/var/lib/agentic-stock-free-input/status.json"))
    p.add_argument("--state", type=Path, default=Path("/var/lib/agentic-stock-free-runtime"))
    args = p.parse_args()
    args.state.mkdir(parents=True, exist_ok=True)
    with (args.state / "supervisor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            result = run_once(args.input, args.provider_status, args.state)
        except (RuntimeBlocked, OSError, ValueError, TypeError, sqlite3.Error) as exc:
            result = blocked_status(str(exc))
        atomic_write(args.state / "status.json", result)
        if "session_coverage" in result:
            atomic_write(args.state / "session-coverage.json", result["session_coverage"])
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__": main()
