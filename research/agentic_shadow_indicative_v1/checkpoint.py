"""Audit scheduled indicative runs without interpreting simulated returns."""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, time, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
from statistics import median
from urllib.parse import parse_qsl, urlsplit
from zoneinfo import ZoneInfo

from .engine import canonical, digest


ET = ZoneInfo("America/New_York")
MAX_ARCHIVE_COMPRESSED_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_REQUESTS = 40
MAX_RUN_LOG_BYTES = 16 * 1024 * 1024
ACTIVE_START = time(10, 0)
ACTIVE_END = time(15, 55)
ACTIVE_RECORD_END = time(16, 0)
MAX_SUCCESS_GAP_SECONDS = 180
FORBIDDEN_ARCHIVE_KEYS = {
    "apca-api-key-id", "apca-api-secret-key", "alpaca_paper_api_key",
    "alpaca_paper_api_secret", "authorization",
}


class CheckpointError(ValueError):
    pass


def utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise CheckpointError("timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CheckpointError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise CheckpointError("timestamp_naive")
    return parsed.astimezone(timezone.utc)


def _read_gzip_json(path: Path) -> tuple[dict, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ARCHIVE_COMPRESSED_BYTES:
        raise CheckpointError("archive_file_invalid")
    compressed = path.read_bytes()
    archive_sha = hashlib.sha256(compressed).hexdigest()
    try:
        with gzip.open(path, "rb") as stream:
            raw = stream.read(MAX_ARCHIVE_UNCOMPRESSED_BYTES + 1)
    except (OSError, EOFError) as exc:
        raise CheckpointError("archive_gzip_invalid") from exc
    if len(raw) > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
        raise CheckpointError("archive_uncompressed_too_large")
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CheckpointError("archive_json_invalid") from exc
    if not isinstance(value, dict):
        raise CheckpointError("archive_shape_invalid")
    return value, archive_sha


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in FORBIDDEN_ARCHIVE_KEYS or _contains_forbidden_key(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _response_base_and_token(url: str) -> tuple[tuple, str | None]:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "data.alpaca.markets", "paper-api.alpaca.markets"
    } or parsed.username or parsed.password or parsed.fragment:
        raise CheckpointError("response_url_invalid")
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    tokens = [value for key, value in pairs if key == "page_token"]
    if len(tokens) > 1:
        raise CheckpointError("response_page_token_invalid")
    base = (parsed.scheme, parsed.netloc, parsed.path,
            tuple(sorted((key, value) for key, value in pairs if key != "page_token")))
    return base, tokens[0] if tokens else None


def audit_archive(path: Path, expected_event_id: str, expected_sha: str) -> dict:
    archive, actual_sha = _read_gzip_json(path)
    if actual_sha != expected_sha:
        raise CheckpointError("archive_hash_mismatch")
    if (archive.get("event_id") != expected_event_id
            or archive.get("purpose") != "plumbing_only"
            or archive.get("credentials_included") is not False
            or _contains_forbidden_key(archive)):
        raise CheckpointError("archive_envelope_invalid")
    responses = archive.get("responses")
    packet_without_hash = archive.get("normalized_packet_without_archive_hash")
    if not isinstance(responses, list) or not isinstance(packet_without_hash, dict):
        raise CheckpointError("archive_shape_invalid")
    if not 0 < len(responses) <= MAX_REQUESTS:
        raise CheckpointError("archive_request_count_invalid")
    response_hashes: set[str] = set()
    parsed_responses = []
    for response in responses:
        if not isinstance(response, dict) or set(response) != {
            "url", "received_at", "sha256", "size_bytes", "raw_base64", "payload"
        }:
            raise CheckpointError("response_shape_invalid")
        try:
            raw = base64.b64decode(response["raw_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise CheckpointError("response_raw_invalid") from exc
        if (type(response["size_bytes"]) is not int or response["size_bytes"] != len(raw)
                or len(raw) > MAX_RESPONSE_BYTES
                or hashlib.sha256(raw).hexdigest() != response["sha256"]):
            raise CheckpointError("response_binding_invalid")
        try:
            decoded = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CheckpointError("response_raw_json_invalid") from exc
        if decoded != response["payload"]:
            raise CheckpointError("response_payload_mismatch")
        base, requested_token = _response_base_and_token(response["url"])
        parsed_responses.append((base, requested_token, response))
        utc(response["received_at"])
        response_hashes.add(response["sha256"])
    for index, (base, _, response) in enumerate(parsed_responses):
        payload = response["payload"]
        next_token = payload.get("next_page_token") if isinstance(payload, dict) else None
        if next_token not in (None, "") and not isinstance(next_token, str):
            raise CheckpointError("response_next_page_token_invalid")
        if next_token:
            if index + 1 >= len(parsed_responses):
                raise CheckpointError("pagination_incomplete")
            next_base, requested, _ = parsed_responses[index + 1]
            if next_base != base or requested != next_token:
                raise CheckpointError("pagination_incomplete")
    referenced: set[str] = set()
    def collect_hashes(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "provider_response_sha256" and isinstance(item, str):
                    referenced.add(item)
                elif key == "provider_response_sha256s" and isinstance(item, list):
                    referenced.update(part for part in item if isinstance(part, str))
                collect_hashes(item)
        elif isinstance(value, list):
            for item in value:
                collect_hashes(item)
    collect_hashes(packet_without_hash)
    if not referenced or not referenced.issubset(response_hashes):
        raise CheckpointError("packet_response_binding_invalid")
    if (packet_without_hash.get("event_id") != expected_event_id
            or packet_without_hash.get("kind") != "indicative"
            or packet_without_hash.get("purpose") != "plumbing_only"
            or packet_without_hash.get("orders_enabled") is not False
            or "provider_archive_sha256" in packet_without_hash):
        raise CheckpointError("normalized_packet_envelope_invalid")
    observed = utc(packet_without_hash.get("observed_at"))
    received = [utc(item[2]["received_at"]) for item in parsed_responses]
    if any(moment > observed for moment in received) or observed - min(received) > timedelta(seconds=60):
        raise CheckpointError("packet_collection_not_current")
    packet = deepcopy(packet_without_hash)
    packet["provider_archive_sha256"] = actual_sha
    return {
        "event_id": expected_event_id,
        "packet_sha256": digest(packet),
        "requests": len(responses),
        "response_bytes": sum(item[2]["size_bytes"] for item in parsed_responses),
        "contracts": len(packet_without_hash.get("chain", {}).get("contracts", [])),
        "observed_at": packet_without_hash["observed_at"],
    }


def read_run_log(path: Path, revision: str) -> list[dict]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_RUN_LOG_BYTES:
        raise CheckpointError("run_log_invalid")
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        if len(line.encode()) > 16 * 1024:
            raise CheckpointError("run_log_record_too_large")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CheckpointError("run_log_json_invalid") from exc
        if not isinstance(record, dict):
            raise CheckpointError("run_log_shape_invalid")
        if record.get("release_revision") == revision:
            result.append(record)
    return result


def read_ledger(path: Path) -> dict[str, dict]:
    if path.is_symlink() or not path.is_file():
        raise CheckpointError("ledger_invalid")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute("SELECT seq,event_id,body,prev,hash FROM events ORDER BY seq").fetchall()
    except sqlite3.Error as exc:
        raise CheckpointError("ledger_read_failed") from exc
    finally:
        connection.close()
    result = {}
    previous = "0" * 64
    for expected, (seq, event_id, body, parent, row_hash) in enumerate(rows, 1):
        if (seq != expected or parent != previous
                or digest([event_id, body, parent]) != row_hash or event_id in result):
            raise CheckpointError("ledger_integrity_failed")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise CheckpointError("ledger_body_invalid") from exc
        result[event_id] = parsed
        previous = row_hash
    return result


def evaluate(run_log: Path, archive_dir: Path, ledger_path: Path,
             revision: str, required_sessions: int = 5) -> dict:
    if len(revision) != 64 or any(c not in "0123456789abcdef" for c in revision):
        raise CheckpointError("revision_invalid")
    records = read_run_log(run_log, revision)
    ledger = read_ledger(ledger_path)
    issues = []
    archive_results = {}
    published = [record for record in records if record.get("status") == "PUBLISHED"]
    for record in published:
        try:
            event_id = record["event_id"]
            archive_name = Path(record["provider_archive"]).name
            if archive_name != event_id + ".json.gz":
                raise CheckpointError("archive_name_invalid")
            audited = audit_archive(archive_dir / archive_name, event_id,
                                    record["provider_archive_sha256"])
            if (audited["packet_sha256"] != record.get("packet_sha256")
                    or audited["requests"] != record.get("network_requests")
                    or audited["contracts"] != record.get("contracts")):
                raise CheckpointError("status_packet_hash_mismatch")
            body = ledger.get(event_id)
            if (not body or body.get("evidence_kind") != "indicative"
                    or body.get("packet_hash") != audited["packet_sha256"]
                    or body.get("packet", {}).get("full_packet_sha256") != audited["packet_sha256"]):
                raise CheckpointError("consumer_event_missing_or_unbound")
            archive_results[event_id] = audited
        except (KeyError, TypeError, CheckpointError) as exc:
            issues.append({"event_id": record.get("event_id"), "reason": str(exc)})

    sessions: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        try:
            checked = utc(record.get("checked_at"))
        except CheckpointError:
            issues.append({"event_id": record.get("event_id"), "reason": "run_timestamp_invalid"})
            continue
        local = checked.astimezone(ET)
        local_time = local.time().replace(tzinfo=None)
        if not record.get("forced") and local.weekday() < 5 and ACTIVE_START <= local_time <= ACTIVE_RECORD_END:
            sessions[local.date().isoformat()].append(record)

    session_results = []
    complete_sessions = 0
    latencies = []
    for day, day_records in sorted(sessions.items()):
        day_records.sort(key=lambda item: utc(item["checked_at"]))
        successes = [item for item in day_records if item.get("status") == "PUBLISHED"
                     and item.get("event_id") in archive_results]
        timestamps = [utc(item["checked_at"]) for item in successes]
        for item in day_records:
            try:
                latencies.append((utc(item["finished_at"]) - utc(item["checked_at"])).total_seconds())
            except (KeyError, CheckpointError):
                issues.append({"event_id": item.get("event_id"), "reason": "run_duration_invalid"})
        gap = max((right - left).total_seconds() for left, right in zip(timestamps, timestamps[1:])) if len(timestamps) > 1 else None
        first_local = timestamps[0].astimezone(ET).time().replace(tzinfo=None) if timestamps else None
        last_local = timestamps[-1].astimezone(ET).time().replace(tzinfo=None) if timestamps else None
        statuses = defaultdict(int)
        for item in day_records:
            statuses[str(item.get("status"))] += 1
        complete = bool(
            successes
            and first_local <= time(10, 5)
            and last_local >= ACTIVE_END
            and gap is not None and gap <= MAX_SUCCESS_GAP_SECONDS
            and len(successes) == len(day_records)
        )
        complete_sessions += int(complete)
        session_results.append({
            "date": day, "complete": complete, "scheduled_runs": len(day_records),
            "published_and_consumed": len(successes), "status_counts": dict(statuses),
            "max_success_gap_seconds": gap,
        })
    sorted_latencies = sorted(latencies)
    p95 = sorted_latencies[min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.95))] if sorted_latencies else None
    passed = complete_sessions >= required_sessions and not issues
    return {
        "experiment": "agentic-options-shadow-indicative-7500-v1",
        "purpose": "PLUMBING ONLY",
        "execution_validity": "NOT VALID FOR PROFIT, EXECUTION, OR AGENT-EFFICACY ANALYSIS",
        "revision": revision,
        "required_complete_sessions": required_sessions,
        "complete_sessions": complete_sessions,
        "checkpoint_passed": passed,
        "runs_for_revision": len(records),
        "published_archives_verified": len(archive_results),
        "consumer_events": len(ledger),
        "session_results": session_results,
        "run_latency_seconds": {
            "median": median(latencies) if latencies else None,
            "p95": p95,
            "max": max(latencies) if latencies else None,
        },
        "issues": issues,
        "interpretation": "Operational evidence only. Do not interpret P&L, fills, win rate, drawdown, or arm differences.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-log", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--required-sessions", type=int, default=5)
    args = parser.parse_args()
    if not 0 <= args.required_sessions <= 100:
        parser.error("--required-sessions must be between 0 and 100")
    try:
        report = evaluate(args.run_log, args.archive_dir, args.ledger,
                          args.revision, args.required_sessions)
    except (CheckpointError, OSError, sqlite3.Error) as exc:
        print(canonical({"checkpoint_passed": False, "error": str(exc),
                         "purpose": "PLUMBING ONLY"}))
        raise SystemExit(1)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["checkpoint_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
