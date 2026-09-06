from __future__ import annotations

import fcntl
import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from .paper_journal import PaperJournal
from .paper_models import parse_timestamp
from .paper_workflow import AUTOPILOT_AUTHORIZATION, PaperWorkflow
from .safe_paths import private_parent


class PaperAutopilotError(RuntimeError):
    pass


_RUNTIME_EXECUTION_ENV = {
    "SWINGBOT_PAPER_EXECUTION": "I_UNDERSTAND_PAPER_ONLY",
    "SWINGBOT_KILL_SWITCH": "0",
}


@contextmanager
def _single_process(root: Path) -> Iterator[None]:
    path = root / "outputs/paper/autopilot-process.lock"
    with private_parent(path, label="paper autopilot lock") as directory:
        descriptor = directory.open_file(path.name, os.O_CREAT | os.O_RDWR)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise PaperAutopilotError("another paper autopilot process is already running") from None
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


def run_cycle(
    workflow: PaperWorkflow,
    journal: PaperJournal,
    *,
    authorization: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Reconcile once and process each frozen-strategy action at most once per session."""
    if authorization != AUTOPILOT_AUTHORIZATION:
        raise PaperAutopilotError("exact unattended paper authorization is required")
    status = workflow.status()
    now = parse_timestamp(str(status["broker_timestamp"]))
    result: dict[str, Any] = {
        "paper_only": True,
        "broker_timestamp": now.isoformat(),
        "market_open": bool(status["market_open"]),
        "next_open": status["next_open"],
        "next_close": status["next_close"],
        "kill_switch_latched": bool(status["kill_switch_latched"]),
        "reconciliation_ok": bool(status["reconciliation"]["ok"]),
        "session_processed": False,
        "submitted": [],
        "deferred": [],
        "failures": [],
    }
    if (
        not result["market_open"]
        or result["kill_switch_latched"]
        or not result["reconciliation_ok"]
    ):
        return result

    run_number = int(status["paper_run_number"])
    session_date = now.date().isoformat()
    events = journal.events()
    completed = any(
        event["event_type"] == "paper_autopilot_session_completed"
        and event["payload"].get("paper_run_number") == run_number
        and event["payload"].get("session_date") == session_date
        for event in events
    )
    if completed:
        result["session_processed"] = True
        return result

    claimed = {
        (
            str(event["payload"].get("action")),
            str(event["payload"].get("symbol")),
        )
        for event in events
        if event["event_type"] == "paper_autopilot_action_claimed"
        and event["payload"].get("paper_run_number") == run_number
        and event["payload"].get("session_date") == session_date
    }
    active_session_id = session_id or f"paper-autopilot-{session_date}-{uuid.uuid4().hex}"

    exit_decisions = workflow.scan_exits()
    exit_actions = [
        ("close_position", str(item["symbol"]))
        for item in exit_decisions
        if item.get("exit_required") is True
    ]
    if exit_actions:
        action_plan = exit_actions[:1]
        result["deferred"] = [
            {"action": action, "symbol": symbol, "reason": "one_exit_at_a_time"}
            for action, symbol in exit_actions[1:]
        ]
        result["deferred"].append(
            {
                "action": "entry_scan",
                "symbol": "*",
                "reason": "entries_deferred_until_exit_reconciles",
            }
        )
    else:
        entry_decisions = workflow.scan_entries()
        action_plan = [
            ("entry_oto", str(item["symbol"]))
            for item in entry_decisions
            if item.get("qualified") is True
        ]

    for action, symbol in action_plan:
        if (action, symbol) in claimed:
            continue
        journal.append(
            "paper_autopilot_action_claimed",
            {
                "paper_run_number": run_number,
                "session_date": session_date,
                "action": action,
                "symbol": symbol,
                "retry_after_failure": False,
            },
            occurred_at=now,
        )
        claimed.add((action, symbol))
        try:
            if action == "close_position":
                proposal = workflow.propose_exit(symbol, reason="auto")
            else:
                proposal = workflow.propose_entry(symbol)
            review = workflow.review(proposal.proposal_id)
            order = workflow.execute_automated(
                proposal.proposal_id,
                str(review["confirmation_code"]),
                session_id=active_session_id,
                authorization=authorization,
                environment=_RUNTIME_EXECUTION_ENV,
            )
            submitted = {
                "action": action,
                "symbol": symbol,
                "client_order_id": order.client_order_id,
                "status": order.status,
            }
            journal.append(
                "paper_autopilot_order_submitted",
                submitted,
                proposal_id=proposal.proposal_id,
                occurred_at=now,
            )
            result["submitted"].append(submitted)
        except Exception as exc:
            failure = {
                "action": action,
                "symbol": symbol,
                "error_type": type(exc).__name__,
                "reason": str(exc),
                "automatic_retry": False,
            }
            journal.append(
                "paper_autopilot_action_failed",
                failure,
                occurred_at=now,
            )
            result["failures"].append(failure)
            break

    journal.append(
        "paper_autopilot_session_completed",
        {
            "paper_run_number": run_number,
            "session_date": session_date,
            "submitted_count": len(result["submitted"]),
            "deferred_count": len(result["deferred"]),
            "failure_count": len(result["failures"]),
        },
        occurred_at=now,
    )
    result["session_processed"] = True
    return result


def run_autopilot(
    workflow: PaperWorkflow,
    journal: PaperJournal,
    root: Path,
    *,
    authorization: str,
    iterations: int = 0,
    interval: int = 15,
    closed_interval: int = 60,
    sleep: Callable[[float], None] = time.sleep,
    emit: Callable[[str], None] = print,
) -> None:
    """Run until the first observed open session closes, or for a test iteration limit."""
    if authorization != AUTOPILOT_AUTHORIZATION:
        raise PaperAutopilotError("exact unattended paper authorization is required")
    if iterations < 0 or interval <= 0 or closed_interval <= 0:
        raise PaperAutopilotError("autopilot intervals and iterations are invalid")
    with _single_process(root):
        journal.append(
            "paper_autopilot_started",
            {
                "paper_only": True,
                "automatic_entries": True,
                "automatic_rule_exits": True,
                "fixed_strategy_only": True,
                "one_attempt_per_symbol_per_session": True,
            },
            occurred_at=datetime.now(timezone.utc),
        )
        count = 0
        observed_open_session = False
        while iterations == 0 or count < iterations:
            result = run_cycle(
                workflow,
                journal,
                authorization=authorization,
            )
            emit(json.dumps(result, sort_keys=True))
            count += 1
            if result["kill_switch_latched"] or not result["reconciliation_ok"]:
                break
            if result["market_open"]:
                observed_open_session = True
            elif observed_open_session:
                break
            elif iterations == 0:
                broker_time = parse_timestamp(str(result["broker_timestamp"]))
                next_open = parse_timestamp(str(result["next_open"]))
                if next_open.date() != broker_time.date():
                    break
            if iterations != 0 and count >= iterations:
                break
            sleep(interval if result["market_open"] else closed_interval)
