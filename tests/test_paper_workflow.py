from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swingbot.config import load_config
from swingbot.paper_config import load_paper_config
from swingbot.paper_journal import PaperJournal
from swingbot.paper_models import PaperOrder, PaperPosition
from swingbot.paper_state import reduce_events
from swingbot.paper_workflow import PaperWorkflow, PaperWorkflowError

from paper_fixtures import FakeBroker, NOW, ACCOUNT_ID, sample_proposal


ROOT = Path(__file__).parents[1]
ENABLED = {
    "SWINGBOT_PAPER_EXECUTION": "I_UNDERSTAND_PAPER_ONLY",
    "SWINGBOT_KILL_SWITCH": "0",
}


class PaperWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.journal = PaperJournal(Path(self.temporary.name) / "journal.sqlite")
        self.broker = FakeBroker()
        self.strategy = load_config(ROOT / "config/strategy_v1.json")
        self.paper = load_paper_config(
            ROOT / "config/paper_v1.json", ROOT / "config/strategy_v1.json"
        )
        self.workflow = PaperWorkflow(self.broker, self.journal, self.strategy, self.paper)
        self.workflow.bind_clean_account(now=NOW)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_entry_proposal_is_whole_share_gtc(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        self.assertFalse(proposal.fractional)
        self.assertEqual(proposal.quantity, proposal.quantity.to_integral_value())
        self.assertEqual(proposal.time_in_force, "gtc")
        second = self.workflow.propose_entry("SPY")
        self.assertNotEqual(proposal.proposal_id, second.proposal_id)
        self.assertNotEqual(proposal.client_order_id, second.client_order_id)

    def test_submission_needs_runtime_switch_exact_code_and_is_one_use(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        self.assertEqual(review["ticker"], "SPY")
        self.assertEqual(review["protective_stop"], str(proposal.stop_price))
        self.assertTrue(review["one_order_only"])
        with self.assertRaisesRegex(PaperWorkflowError, "enable phrase"):
            self.workflow.execute(
                proposal.proposal_id, proposal.confirmation_code,
                session_id="session-1", environment={},
            )
        with self.assertRaises(Exception):
            self.workflow.execute(
                proposal.proposal_id, "WRONG",
                session_id="session-1", environment=ENABLED,
            )
        order = self.workflow.execute(
            proposal.proposal_id,
            proposal.confirmation_code,
            session_id="session-1",
            environment=ENABLED,
        )
        self.assertEqual(order.order_class, "oto")
        self.assertEqual(len(order.legs), 1)
        self.assertEqual(self.broker.submitted_entries, 1)
        with self.assertRaises(Exception):
            self.workflow.execute(
                proposal.proposal_id,
                proposal.confirmation_code,
                session_id="session-1",
                environment=ENABLED,
            )
        self.assertEqual(self.broker.submitted_entries, 1)

    def test_expired_or_changed_quote_cannot_submit(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        self.workflow.review(proposal.proposal_id)
        self.broker.quote = replace(self.broker.quote, ask=Decimal("121"))
        with self.assertRaises(Exception):
            self.workflow.execute(
                proposal.proposal_id,
                proposal.confirmation_code,
                session_id="session-1",
                environment=ENABLED,
            )
        self.assertEqual(self.broker.submitted_entries, 0)

    def test_missing_latest_trading_day_bar_rejects_proposal(self) -> None:
        self.broker.bars["SPY"] = self.broker.bars["SPY"][:-1]
        with self.assertRaisesRegex(PaperWorkflowError, "latest completed bar"):
            self.workflow.propose_entry("SPY")

    def test_status_scan_and_owner_clear_are_point_in_time_and_fail_closed(self) -> None:
        status = self.workflow.status()
        self.assertTrue(status["paper_only"])
        self.assertTrue(status["reconciliation"]["ok"])
        self.assertIn("point-in-time", status["monitoring_honesty"])
        decisions = self.workflow.scan_entries()
        self.assertEqual(len(decisions), len(self.strategy["universe"]))
        self.journal.append(
            "kill_switch_latched", {"reason": "test"}, occurred_at=NOW
        )
        with self.assertRaises(PaperWorkflowError):
            self.workflow.clear_kill_switch("WRONG")
        self.workflow.clear_kill_switch("CLEAR-PAPER-KILL-SWITCH")
        self.assertFalse(self.journal.kill_switch_latched())

    def test_position_remains_local_until_broker_confirms_exit_fill(self) -> None:
        self.broker.entry_status = "filled"
        entry = self.workflow.propose_entry("SPY")
        self.workflow.review(entry.proposal_id)
        entry_order = self.workflow.execute(
            entry.proposal_id, entry.confirmation_code,
            session_id="session-entry", environment=ENABLED,
        )
        self.broker.positions = [
            PaperPosition(
                "SPY", entry.quantity, "long", entry.ask, entry.ask,
                entry.quantity * entry.ask,
            )
        ]
        report = self.workflow.reconcile_now(now=NOW)
        self.assertTrue(report.ok, report.issues)
        self.assertIn("SPY", reduce_events(self.journal.events()).positions)

        exit_proposal = self.workflow.propose_exit("SPY", reason="manual_owner_exit")
        self.workflow.review(exit_proposal.proposal_id)
        exit_order = self.workflow.execute(
            exit_proposal.proposal_id,
            exit_proposal.confirmation_code,
            session_id="session-exit",
            environment=ENABLED,
        )
        self.assertIn("SPY", reduce_events(self.journal.events()).positions)
        self.assertEqual(self.broker.canceled_order_ids, [entry_order.legs[0].order_id])

        filled_exit = replace(
            exit_order,
            status="filled",
            filled_quantity=exit_proposal.quantity,
            filled_average_price=exit_proposal.bid,
        )
        self.broker.orders = [
            filled_exit if order.order_id == exit_order.order_id else order
            for order in self.broker.orders
        ]
        self.broker.positions = []
        final = self.workflow.reconcile_now(now=NOW)
        self.assertTrue(final.ok, final.issues)
        self.assertNotIn("SPY", reduce_events(self.journal.events()).positions)

    def test_uncertain_submission_latches_and_never_retries(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        self.workflow.review(proposal.proposal_id)
        self.broker.fail_submit = True
        with self.assertRaisesRegex(PaperWorkflowError, "outcome is uncertain"):
            self.workflow.execute(
                proposal.proposal_id,
                proposal.confirmation_code,
                session_id="session-1",
                environment=ENABLED,
            )
        self.assertTrue(self.journal.kill_switch_latched())
        self.assertEqual(self.broker.submitted_entries, 1)

    def test_uncertain_stop_cancellation_latches_and_blocks_exit_submission(self) -> None:
        self.broker.entry_status = "filled"
        entry = self.workflow.propose_entry("SPY")
        self.workflow.review(entry.proposal_id)
        entry_order = self.workflow.execute(
            entry.proposal_id, entry.confirmation_code,
            session_id="session-entry", environment=ENABLED,
        )
        self.broker.positions = [
            PaperPosition(
                "SPY", entry.quantity, "long", entry.ask, entry.ask,
                entry.quantity * entry.ask,
            )
        ]
        report = self.workflow.reconcile_now(now=NOW)
        self.assertTrue(report.ok, report.issues)
        self.assertTrue(entry_order.legs)

        exit_proposal = self.workflow.propose_exit("SPY", reason="manual_owner_exit")
        self.workflow.review(exit_proposal.proposal_id)
        self.broker.fail_cancel = True
        with self.assertRaisesRegex(PaperWorkflowError, "cancellation outcome is uncertain"):
            self.workflow.execute(
                exit_proposal.proposal_id,
                exit_proposal.confirmation_code,
                session_id="session-exit",
                environment=ENABLED,
            )
        self.assertTrue(self.journal.kill_switch_latched())
        self.assertEqual(self.broker.submitted_exits, 0)


if __name__ == "__main__":
    unittest.main()
