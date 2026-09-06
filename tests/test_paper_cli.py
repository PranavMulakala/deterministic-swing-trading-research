import argparse
import os
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, call, patch

from swingbot.paper_cli import (
    _load_env,
    _monitor,
    _print,
    _print_status,
    _safe_exit_checks,
    add_paper_parser,
    run_paper,
)


class PaperCliTests(unittest.TestCase):
    def tearDown(self) -> None:
        for key in ("ALPACA_PAPER_API_KEY", "ALPACA_PAPER_API_SECRET"):
            os.environ.pop(key, None)

    def test_env_requires_private_permissions_and_known_keys(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("ALPACA_PAPER_API_KEY=paper-only\n", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                _load_env(path)
            path.chmod(0o600)
            _load_env(path)
            self.assertEqual(os.environ["ALPACA_PAPER_API_KEY"], "paper-only")
            path.write_text("UNEXPECTED_KEY=value\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                _load_env(path)
            path.write_text("SWINGBOT_KILL_SWITCH=0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected .env key"):
                _load_env(path)

    def test_env_values_are_not_shell_evaluated(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("ALPACA_PAPER_API_SECRET=$(not-a-command)\n", encoding="utf-8")
            path.chmod(0o600)
            _load_env(path)
            self.assertEqual(os.environ["ALPACA_PAPER_API_SECRET"], "$(not-a-command)")

    def test_env_rejects_symlink_malformed_line_and_preserves_process_override(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_text("ALPACA_PAPER_API_KEY=from-file\n", encoding="utf-8")
            target.chmod(0o600)
            link = root / ".env"
            link.symlink_to(target)
            with self.assertRaisesRegex(PermissionError, "symbolic link"):
                _load_env(link)

            link.unlink()
            link.write_text("not-an-assignment\n", encoding="utf-8")
            link.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "invalid .env line 1"):
                _load_env(link)

            os.environ["ALPACA_PAPER_API_KEY"] = "process-value"
            link.write_text("ALPACA_PAPER_API_KEY=file-value\n", encoding="utf-8")
            _load_env(link)
            self.assertEqual(os.environ["ALPACA_PAPER_API_KEY"], "process-value")

    def test_missing_or_comment_only_env_is_a_noop(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            _load_env(path)
            path.write_text("\n# paper credentials stay local\n", encoding="utf-8")
            path.chmod(0o600)
            _load_env(path)
        self.assertNotIn("ALPACA_PAPER_API_KEY", os.environ)
        self.assertNotIn("ALPACA_PAPER_API_SECRET", os.environ)

    def test_reset_run_command_requires_explicit_confirmation_argument(self) -> None:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        add_paper_parser(subparsers)
        args = parser.parse_args(
            [
                "paper", "reset-run", "--confirmation",
                "REBASELINE-PAPER-RUN-AT-CLEAN-500",
            ]
        )
        self.assertEqual(args.paper_command, "reset-run")
        self.assertEqual(
            args.confirmation, "REBASELINE-PAPER-RUN-AT-CLEAN-500"
        )

    def test_parser_routes_every_paper_command_and_required_fields(self) -> None:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        add_paper_parser(subparsers)
        cases = (
            (["paper", "bind"], "bind"),
            (["paper", "status"], "status"),
            (["paper", "scan"], "scan"),
            (["paper", "propose-entry", "SPY"], "propose-entry"),
            (
                ["paper", "propose-exit", "SPY", "--reason", "time_stop"],
                "propose-exit",
            ),
            (["paper", "review", "proposal-1"], "review"),
            (
                [
                    "paper",
                    "execute",
                    "proposal-1",
                    "--confirmation-code",
                    "CONFIRM-123",
                    "--session-id",
                    "session-1",
                ],
                "execute",
            ),
            (
                ["paper", "clear-kill", "--confirmation", "CLEAR-PAPER-KILL-SWITCH"],
                "clear-kill",
            ),
            (
                [
                    "paper",
                    "reset-run",
                    "--confirmation",
                    "REBASELINE-PAPER-RUN-AT-CLEAN-500",
                ],
                "reset-run",
            ),
            (
                ["paper", "monitor", "--iterations", "2", "--interval", "3"],
                "monitor",
            ),
        )
        for argv, expected in cases:
            with self.subTest(argv=argv):
                args = parser.parse_args(argv)
                self.assertEqual(args.command, "paper")
                self.assertEqual(args.paper_command, expected)

    def test_run_paper_routes_every_command_without_broker_io(self) -> None:
        workflow = MagicMock()
        journal = MagicMock()
        broker = object()
        proposal = SimpleNamespace(proposal_id="proposal-1")
        order = SimpleNamespace(
            order_id="broker-1", client_order_id="client-1", status="new"
        )
        workflow.bind_clean_account.return_value = {"bound": True}
        workflow.scan_entries.return_value = [{"symbol": "SPY"}]
        workflow.scan_exits.return_value = []
        workflow.propose_entry.return_value = proposal
        workflow.propose_exit.return_value = proposal
        workflow.review.return_value = {"proposal_id": "proposal-1"}
        workflow.execute.return_value = order
        workflow.rebaseline_clean_account.return_value = {"run_number": 2}
        journal.kill_switch_latched.return_value = False
        paper_config = {
            "broker": {
                "trading_base_url": "https://paper-api.alpaca.markets",
                "data_base_url": "https://data.alpaca.markets",
                "request_timeout_seconds": 20,
            },
            "execution": {
                "cancel_verification_attempts": 5,
                "cancel_verification_interval_seconds": 0.25,
            },
            "monitoring": {"poll_seconds": 15},
        }
        print_status = MagicMock()
        monitor = MagicMock()
        with TemporaryDirectory() as directory, patch.multiple(
            "swingbot.paper_cli",
            _load_env=MagicMock(),
            load_config=MagicMock(return_value={"strategy": True}),
            load_paper_config=MagicMock(return_value=paper_config),
            PaperJournal=MagicMock(return_value=journal),
            AlpacaPaperClient=MagicMock(return_value=broker),
            PaperWorkflow=MagicMock(return_value=workflow),
            _print=MagicMock(),
            _print_status=print_status,
            _monitor=monitor,
        ):
            root = Path(directory)
            resolved_root = root.resolve()
            cases = (
                ("bind", {}, call.bind_clean_account()),
                ("status", {}, None),
                ("scan", {}, call.scan_entries()),
                ("propose-entry", {"symbol": "SPY"}, call.propose_entry("SPY")),
                (
                    "propose-exit",
                    {"symbol": "SPY", "reason": "time_stop"},
                    call.propose_exit("SPY", reason="time_stop"),
                ),
                ("review", {"proposal_id": "proposal-1"}, call.review("proposal-1")),
                (
                    "execute",
                    {
                        "proposal_id": "proposal-1",
                        "confirmation_code": "CONFIRM-123",
                        "session_id": "session-1",
                    },
                    call.execute(
                        "proposal-1", "CONFIRM-123", session_id="session-1"
                    ),
                ),
                (
                    "clear-kill",
                    {"confirmation": "CLEAR-PAPER-KILL-SWITCH"},
                    call.clear_kill_switch("CLEAR-PAPER-KILL-SWITCH"),
                ),
                (
                    "reset-run",
                    {"confirmation": "REBASELINE-PAPER-RUN-AT-CLEAN-500"},
                    call.rebaseline_clean_account(
                        "REBASELINE-PAPER-RUN-AT-CLEAN-500"
                    ),
                ),
                ("monitor", {"iterations": 2, "interval": None}, None),
            )
            for command, extra, expected_call in cases:
                with self.subTest(command=command):
                    workflow.reset_mock()
                    args = argparse.Namespace(
                        root=root, paper_command=command, **extra
                    )
                    run_paper(args)
                    if expected_call is not None:
                        self.assertIn(expected_call, workflow.method_calls)
                    if command == "status":
                        print_status.assert_called_with(workflow, resolved_root)
                    if command == "monitor":
                        monitor.assert_called_with(
                            workflow, journal, resolved_root, 2, 15
                        )

    def test_explicit_zero_monitor_interval_is_rejected(self) -> None:
        paper_config = {
            "broker": {
                "trading_base_url": "https://paper-api.alpaca.markets",
                "data_base_url": "https://data.alpaca.markets",
                "request_timeout_seconds": 20,
            },
            "execution": {
                "cancel_verification_attempts": 5,
                "cancel_verification_interval_seconds": 0.25,
            },
            "monitoring": {"poll_seconds": 15},
        }
        with TemporaryDirectory() as directory, patch.multiple(
            "swingbot.paper_cli",
            _load_env=MagicMock(),
            load_config=MagicMock(return_value={}),
            load_paper_config=MagicMock(return_value=paper_config),
            PaperJournal=MagicMock(return_value=MagicMock()),
            AlpacaPaperClient=MagicMock(return_value=MagicMock()),
            PaperWorkflow=MagicMock(return_value=MagicMock()),
        ):
            args = argparse.Namespace(
                root=Path(directory),
                paper_command="monitor",
                iterations=1,
                interval=0,
            )
            with self.assertRaisesRegex(ValueError, "interval positive"):
                run_paper(args)

    def test_monitor_deduplicates_output_and_safe_exit_check_fails_closed(self) -> None:
        workflow = MagicMock()
        workflow.status.return_value = {"paper_only": True}
        workflow.scan_exits.return_value = []
        journal = MagicMock()
        journal.events.return_value = []
        with TemporaryDirectory() as directory, patch(
            "swingbot.paper_cli.write_paper_dashboard"
        ) as write_dashboard, patch("builtins.print") as print_mock, patch(
            "swingbot.paper_cli.time.sleep"
        ) as sleep_mock:
            _monitor(
                workflow,
                journal,
                Path(directory),
                iterations=2,
                interval=1,
            )
        self.assertEqual(workflow.status.call_count, 2)
        self.assertEqual(workflow.scan_exits.call_count, 2)
        self.assertEqual(write_dashboard.call_count, 2)
        print_mock.assert_called_once()
        sleep_mock.assert_called_once_with(1)

        workflow.scan_exits.side_effect = RuntimeError("exit scan failed")
        self.assertEqual(
            _safe_exit_checks(workflow),
            [{"exit_check_error": "exit scan failed", "orders_remain_blocked": True}],
        )

    def test_status_writes_dashboard_and_prints_exact_payload(self) -> None:
        workflow = MagicMock()
        workflow.status.return_value = {"paper_only": True}
        workflow.scan_exits.return_value = [{"symbol": "SPY"}]
        workflow.journal.events.return_value = [{"event_type": "account_snapshot"}]
        with TemporaryDirectory() as directory, patch(
            "swingbot.paper_cli.write_paper_dashboard"
        ) as write_dashboard, patch("swingbot.paper_cli._print") as print_payload:
            root = Path(directory)
            _print_status(workflow, root)
            expected = {
                "paper_only": True,
                "exit_checks": [{"symbol": "SPY"}],
                "dashboard": str(root / "outputs/paper/status.html"),
            }
            write_dashboard.assert_called_once_with(
                expected,
                [{"event_type": "account_snapshot"}],
                root / "outputs/paper/status.html",
            )
            print_payload.assert_called_once_with(expected)

        with patch("builtins.print") as print_mock:
            _print({"b": 2, "a": 1})
        print_mock.assert_called_once_with('{\n  "a": 1,\n  "b": 2\n}')


if __name__ == "__main__":
    unittest.main()
