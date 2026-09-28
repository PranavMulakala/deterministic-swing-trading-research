"""Read-only evidence that the delayed collector is ready for another session."""
from datetime import datetime, timezone
import sqlite3
from pathlib import Path
import shutil
import math


def assess(archive_folder, policy, asof):
    folder = Path(archive_folder)
    required = tuple(policy["readiness"]["required_streams"])
    result = {
        "checked_at": datetime.fromtimestamp(asof, timezone.utc).isoformat(),
        "orders_enabled": False,
        "required_streams": len(required),
        "status": "BLOCKED",
        "reasons": [],
    }
    if not required or len(required) != len(set(required)):
        result["reasons"].append("empty_or_duplicate_required_stream")
        return result
    try:
        db = sqlite3.connect((folder / "archive.sqlite").resolve().as_uri() + "?mode=ro", uri=True)
        try:
            db.execute('BEGIN')
            checkpoints = dict(db.execute("SELECT stream,end FROM checkpoints"))
            health = {s: (checked,error) for s, checked, error in db.execute("SELECT stream,checked_at,error FROM health")}
        finally:
            db.close()
    except (OSError, sqlite3.Error):
        result["reasons"].append("archive_unreadable")
        return result
    missing = sorted(set(required) - set(checkpoints))
    missing_health = sorted(set(required) - set(health))
    errors = sorted(s for s in required if s in health and health[s][1])
    if missing:
        result["reasons"].append("missing_checkpoints:" + ",".join(missing))
    if missing_health:
        result["reasons"].append("missing_health:" + ",".join(missing_health))
    if errors:
        result["reasons"].append("collector_errors:" + ",".join(errors))
    invalid_checkpoint = False
    for stream in required:
        if stream in checkpoints:
            cp=checkpoints[stream]
            if type(cp) is not int or cp % 300 or cp > asof:
                invalid_checkpoint = True
                result['reasons'].append('invalid_checkpoint:'+stream)
        if stream in health:
            try:
                checked=datetime.fromisoformat(health[stream][0].replace('Z','+00:00'))
                age=asof-checked.timestamp()
                if checked.tzinfo is None or not math.isfinite(age) or not 0<=age<=600:
                    raise ValueError('stale')
            except (TypeError,ValueError,AttributeError,OverflowError):
                result['reasons'].append('stale_or_invalid_health:'+stream)
    if not missing and not invalid_checkpoint:
        lag = max(0, int(asof - min(checkpoints[s] for s in required)))
        result["maximum_checkpoint_lag_seconds"] = lag
        if lag > policy["readiness"]["max_checkpoint_lag_seconds"]:
            result["reasons"].append("collector_checkpoint_stale")
    try:
        free = shutil.disk_usage(folder).free
    except OSError:
        result['reasons'].append('disk_unreadable')
        return result
    result["free_bytes"] = free
    if free < policy["readiness"]["minimum_free_bytes"]:
        result["reasons"].append("disk_reserve_breached")
    if not result["reasons"]:
        result["status"] = "READY_FOR_DELAYED_RESEARCH_SESSION"
    return result
