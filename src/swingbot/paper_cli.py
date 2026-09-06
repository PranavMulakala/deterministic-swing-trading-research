from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from .alpaca_paper import AlpacaPaperClient
from .config import load_config
from .paper_config import load_paper_config
from .paper_dashboard import write_paper_dashboard
from .paper_journal import PaperJournal
from .paper_workflow import PaperWorkflow
from .paper_autopilot import run_autopilot


ALLOWED_ENV_KEYS = {
    "ALPACA_PAPER_API_KEY",
    "ALPACA_PAPER_API_SECRET",
}


def add_paper_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    paper = subparsers.add_parser("paper", help="Alpaca paper-only operations")
    paper.add_argument("--root", type=Path, default=Path.cwd())
    commands = paper.add_subparsers(dest="paper_command", required=True)
    commands.add_parser("bind", help="bind an empty paper account at exactly $500")
    commands.add_parser("status", help="reconcile and print current paper state")
    commands.add_parser("scan", help="record current deterministic entry/exit decisions")
    entry = commands.add_parser("propose-entry", help="create an expiring exact entry proposal")
    entry.add_argument("symbol")
    exit_parser = commands.add_parser("propose-exit", help="create an expiring exact exit proposal")
    exit_parser.add_argument("symbol")
    exit_parser.add_argument(
        "--reason",
        choices=("auto", "recovery_target", "time_stop", "manual_owner_exit"),
        default="auto",
    )
    review = commands.add_parser("review", help="print the full order and one-use confirmation code")
    review.add_argument("proposal_id")
    execute = commands.add_parser("execute", help="submit exactly one approved paper order")
    execute.add_argument("proposal_id")
    execute.add_argument("--confirmation-code", required=True)
    execute.add_argument("--session-id", required=True)
    clear = commands.add_parser("clear-kill", help="clear only after a clean reconciliation")
    clear.add_argument("--confirmation", required=True)
    reset = commands.add_parser(
        "reset-run", help="start a new run after a clean manual broker recovery"
    )
    reset.add_argument("--confirmation", required=True)
    monitor = commands.add_parser("monitor", help="poll/reconcile while this process stays running")
    monitor.add_argument("--iterations", type=int, default=0, help="0 means run until interrupted")
    monitor.add_argument("--interval", type=int, default=None)
    autopilot = commands.add_parser(
        "autopilot",
        help="paper-only unattended scan, review, and execution of the frozen strategy",
    )
    autopilot.add_argument("--authorization", required=True)
    autopilot.add_argument(
        "--iterations", type=int, default=0,
        help="0 waits for the next open session and exits after that session closes",
    )
    autopilot.add_argument("--interval", type=int, default=None)
    autopilot.add_argument("--closed-interval", type=int, default=60)


def run_paper(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    _load_env(root / ".env")
    strategy_path = root / "config/strategy_v1.json"
    paper_path = root / "config/paper_v1.json"
    strategy = load_config(strategy_path)
    paper = load_paper_config(paper_path, strategy_path)
    broker_cfg = paper["broker"]
    journal = PaperJournal(root / "outputs/paper/paper_journal.sqlite")
    broker = AlpacaPaperClient(
        os.environ.get("ALPACA_PAPER_API_KEY", ""),
        os.environ.get("ALPACA_PAPER_API_SECRET", ""),
        trading_base_url=broker_cfg["trading_base_url"],
        data_base_url=broker_cfg["data_base_url"],
        timeout=int(broker_cfg["request_timeout_seconds"]),
        permit_validator=journal.claim_permit,
        cancel_verification_attempts=int(
            paper["execution"]["cancel_verification_attempts"]
        ),
        cancel_verification_interval_seconds=float(
            paper["execution"]["cancel_verification_interval_seconds"]
        ),
    )
    workflow = PaperWorkflow(broker, journal, strategy, paper)

    command = args.paper_command
    if command == "bind":
        _print(workflow.bind_clean_account())
    elif command == "status":
        _print_status(workflow, root)
    elif command == "scan":
        _print({"entries": workflow.scan_entries(), "exits": workflow.scan_exits()})
    elif command == "propose-entry":
        proposal = workflow.propose_entry(args.symbol)
        _print(workflow.review(proposal.proposal_id))
    elif command == "propose-exit":
        proposal = workflow.propose_exit(args.symbol, reason=args.reason)
        _print(workflow.review(proposal.proposal_id))
    elif command == "review":
        _print(workflow.review(args.proposal_id))
    elif command == "execute":
        order = workflow.execute(
            args.proposal_id,
            args.confirmation_code,
            session_id=args.session_id,
        )
        _print(
            {
                "paper_only": True,
                "broker_order_id": order.order_id,
                "client_order_id": order.client_order_id,
                "status": order.status,
                "next_required_action": "run paper status until reconciled; the process does not monitor after exit",
            }
        )
    elif command == "clear-kill":
        workflow.clear_kill_switch(args.confirmation)
        _print({"kill_switch_latched": journal.kill_switch_latched()})
    elif command == "reset-run":
        _print(workflow.rebaseline_clean_account(args.confirmation))
    elif command == "monitor":
        _monitor(
            workflow,
            journal,
            root,
            args.iterations,
            args.interval
            if args.interval is not None
            else int(paper["monitoring"]["poll_seconds"]),
        )
    elif command == "autopilot":
        run_autopilot(
            workflow,
            journal,
            root,
            authorization=args.authorization,
            iterations=args.iterations,
            interval=args.interval
            if args.interval is not None
            else int(paper["monitoring"]["poll_seconds"]),
            closed_interval=args.closed_interval,
        )


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink():
        raise PermissionError(".env may not be a symbolic link")
    if path.stat().st_mode & 0o077:
        raise PermissionError(".env must be readable and writable only by its owner; run chmod 600 .env")
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"invalid .env line {line_number}")
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_ENV_KEYS:
            raise ValueError(f"unexpected .env key at line {line_number}: {key}")
        if key not in os.environ:
            os.environ[key] = value.strip()


def _print_status(workflow: PaperWorkflow, root: Path) -> None:
    status = workflow.status()
    status["exit_checks"] = _safe_exit_checks(workflow)
    dashboard = root / "outputs/paper/status.html"
    write_paper_dashboard(status, workflow.journal.events(), dashboard)
    status["dashboard"] = str(dashboard)
    _print(status)


def _monitor(
    workflow: PaperWorkflow,
    journal: PaperJournal,
    root: Path,
    iterations: int,
    interval: int,
) -> None:
    if iterations < 0 or interval <= 0:
        raise ValueError("monitor iterations must be nonnegative and interval positive")
    count = 0
    previous = ""
    while iterations == 0 or count < iterations:
        status = workflow.status()
        status["exit_checks"] = _safe_exit_checks(workflow)
        dashboard = root / "outputs/paper/status.html"
        write_paper_dashboard(status, journal.events(), dashboard)
        status["dashboard"] = str(dashboard)
        encoded = json.dumps(status, indent=2, sort_keys=True)
        if encoded != previous:
            print(encoded)
            previous = encoded
        count += 1
        if iterations == 0 or count < iterations:
            time.sleep(interval)


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _safe_exit_checks(workflow: PaperWorkflow) -> list[dict[str, object]]:
    try:
        return workflow.scan_exits()
    except Exception as exc:
        return [{"exit_check_error": str(exc), "orders_remain_blocked": True}]
