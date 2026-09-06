from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from swingbot.paper_autopilot import PaperAutopilotError, run_autopilot, run_cycle
from swingbot.paper_workflow import AUTOPILOT_AUTHORIZATION


def _status(*, market_open: bool = True) -> dict:
    return {
        "paper_only": True,
        "paper_run_number": 1,
        "broker_timestamp": "2026-09-08T09:35:00-04:00",
        "market_open": market_open,
        "next_open": "2026-09-09T09:30:00-04:00",
        "next_close": "2026-09-08T16:00:00-04:00",
        "kill_switch_latched": False,
        "reconciliation": {"ok": True},
    }


class PaperAutopilotTests(unittest.TestCase):
    def test_wrong_authorization_fails_before_broker_reads(self) -> None:
        workflow = MagicMock()
        with self.assertRaisesRegex(PaperAutopilotError, "exact unattended"):
            run_cycle(workflow, MagicMock(), authorization="WRONG")
        workflow.assert_not_called()

    def test_closed_market_only_reconciles(self) -> None:
        workflow = MagicMock()
        workflow.status.return_value = _status(market_open=False)
        result = run_cycle(
            workflow,
            MagicMock(),
            authorization=AUTOPILOT_AUTHORIZATION,
        )
        self.assertFalse(result["market_open"])
        workflow.scan_entries.assert_not_called()
        workflow.scan_exits.assert_not_called()
        workflow.execute_automated.assert_not_called()

    def test_open_cycle_prioritizes_one_exit_and_defers_entry_scan(self) -> None:
        workflow = MagicMock()
        workflow.status.return_value = _status()
        workflow.scan_exits.return_value = [
            {"symbol": "XLF", "exit_required": True, "reason": "time_stop"}
        ]
        workflow.propose_exit.return_value = SimpleNamespace(proposal_id="exit-1")
        workflow.review.return_value = {"confirmation_code": "CONFIRM-EXIT"}
        workflow.execute_automated.return_value = SimpleNamespace(
            client_order_id="close-xlf", status="new"
        )
        journal = MagicMock()
        journal.events.return_value = []

        result = run_cycle(
            workflow,
            journal,
            authorization=AUTOPILOT_AUTHORIZATION,
            session_id="paper-autopilot-test",
        )

        self.assertTrue(result["session_processed"])
        self.assertEqual([item["symbol"] for item in result["submitted"]], ["XLF"])
        workflow.propose_exit.assert_called_once_with("XLF", reason="auto")
        workflow.scan_entries.assert_not_called()
        workflow.propose_entry.assert_not_called()
        self.assertEqual(result["deferred"][0]["reason"], "entries_deferred_until_exit_reconciles")
        for call in workflow.execute_automated.call_args_list:
            self.assertEqual(call.kwargs["authorization"], AUTOPILOT_AUTHORIZATION)
            self.assertEqual(call.kwargs["session_id"], "paper-autopilot-test")

    def test_entry_only_cycle_processes_each_qualified_symbol(self) -> None:
        workflow = MagicMock()
        workflow.status.return_value = _status()
        workflow.scan_exits.return_value = []
        workflow.scan_entries.return_value = [
            {"symbol": "SPY", "qualified": True},
            {"symbol": "QQQ", "qualified": True},
            {"symbol": "DIA", "qualified": False},
        ]
        workflow.propose_entry.side_effect = [
            SimpleNamespace(proposal_id="entry-1"),
            SimpleNamespace(proposal_id="entry-2"),
        ]
        workflow.review.side_effect = [
            {"confirmation_code": "CONFIRM-1"},
            {"confirmation_code": "CONFIRM-2"},
        ]
        workflow.execute_automated.side_effect = [
            SimpleNamespace(client_order_id="buy-spy", status="new"),
            SimpleNamespace(client_order_id="buy-qqq", status="new"),
        ]
        journal = MagicMock()
        journal.events.return_value = []
        result = run_cycle(
            workflow,
            journal,
            authorization=AUTOPILOT_AUTHORIZATION,
            session_id="paper-autopilot-test",
        )
        self.assertEqual([item["symbol"] for item in result["submitted"]], ["SPY", "QQQ"])
        self.assertEqual(workflow.execute_automated.call_count, 2)

    def test_completed_session_is_not_scanned_or_retried(self) -> None:
        workflow = MagicMock()
        workflow.status.return_value = _status()
        journal = MagicMock()
        journal.events.return_value = [
            {
                "event_type": "paper_autopilot_session_completed",
                "payload": {"paper_run_number": 1, "session_date": "2026-09-08"},
            }
        ]
        result = run_cycle(
            workflow,
            journal,
            authorization=AUTOPILOT_AUTHORIZATION,
        )
        self.assertTrue(result["session_processed"])
        workflow.scan_entries.assert_not_called()
        workflow.scan_exits.assert_not_called()

    def test_scheduled_run_exits_when_next_open_is_another_day(self) -> None:
        workflow = MagicMock()
        workflow.status.return_value = _status(market_open=False)
        journal = MagicMock()
        sleeper = MagicMock()
        with TemporaryDirectory() as directory:
            run_autopilot(
                workflow,
                journal,
                Path(directory),
                authorization=AUTOPILOT_AUTHORIZATION,
                iterations=0,
                sleep=sleeper,
                emit=MagicMock(),
            )
        workflow.status.assert_called_once()
        sleeper.assert_not_called()

    def test_runner_exits_immediately_on_kill_switch(self) -> None:
        workflow = MagicMock()
        status = _status()
        status["kill_switch_latched"] = True
        workflow.status.return_value = status
        journal = MagicMock()
        sleeper = MagicMock()
        with TemporaryDirectory() as directory:
            run_autopilot(
                workflow,
                journal,
                Path(directory),
                authorization=AUTOPILOT_AUTHORIZATION,
                iterations=0,
                sleep=sleeper,
                emit=MagicMock(),
            )
        workflow.status.assert_called_once()
        sleeper.assert_not_called()


if __name__ == "__main__":
    unittest.main()
