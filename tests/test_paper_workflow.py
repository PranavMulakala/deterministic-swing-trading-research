from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swingbot.config import load_config
from swingbot.paper_config import load_paper_config
from swingbot.paper_journal import JournalError, PaperJournal
from swingbot.paper_models import PaperOrder, PaperPosition
from swingbot.paper_policy import PaperPolicyError
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
        self.broker.permit_validator = self.journal.claim_permit
        self.strategy = load_config(ROOT / "config/strategy_v1.json")
        self.paper = load_paper_config(
            ROOT / "config/paper_v1.json", ROOT / "config/strategy_v1.json"
        )
        self.workflow = PaperWorkflow(self.broker, self.journal, self.strategy, self.paper)
        self.workflow.bind_clean_account(now=NOW)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _set_open_position(self, entry) -> None:
        market_value = entry.quantity * entry.ask
        cash = Decimal("500") - market_value
        self.broker.positions = [
            PaperPosition(
                "SPY", entry.quantity, "long", entry.ask, entry.ask, market_value
            )
        ]
        self.broker.account = replace(
            self.broker.account,
            cash=cash,
            non_marginable_buying_power=cash,
            buying_power=cash,
            long_market_value=market_value,
            equity=cash + market_value,
        )

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
                proposal.proposal_id, review["confirmation_code"],
                session_id="session-1", environment={},
            )
        with self.assertRaises(Exception):
            self.workflow.execute(
                proposal.proposal_id, "WRONG",
                session_id="session-1", environment=ENABLED,
            )
        order = self.workflow.execute(
            proposal.proposal_id,
            review["confirmation_code"],
            session_id="session-1",
            environment=ENABLED,
        )
        self.assertEqual(order.order_class, "oto")
        self.assertEqual(len(order.legs), 1)
        self.assertEqual(self.broker.submitted_entries, 1)
        with self.assertRaises(Exception):
            self.workflow.execute(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="session-1",
                environment=ENABLED,
            )
        self.assertEqual(self.broker.submitted_entries, 1)

    def test_expired_or_changed_quote_cannot_submit(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        self.broker.quote = replace(self.broker.quote, ask=Decimal("121"))
        with self.assertRaises(Exception):
            self.workflow.execute(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="session-1",
                environment=ENABLED,
            )
        self.assertEqual(self.broker.submitted_entries, 0)

    def test_confirmation_code_is_bound_to_the_exact_latest_review(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        first = self.workflow.review(proposal.proposal_id)
        self.broker.quote = replace(self.broker.quote, ask=Decimal("110.515"))
        second = self.workflow.review(proposal.proposal_id)
        self.assertNotEqual(first["confirmation_code"], second["confirmation_code"])
        with self.assertRaisesRegex(Exception, "exact latest full-order review"):
            self.workflow.execute(
                proposal.proposal_id,
                first["confirmation_code"],
                session_id="session-old-review",
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
        self.journal._append_state(
            "kill_switch_latched", {"reason": "test"}, occurred_at=NOW
        )
        with self.assertRaises(PaperWorkflowError):
            self.workflow.clear_kill_switch("WRONG")
        self.workflow.clear_kill_switch("CLEAR-PAPER-KILL-SWITCH")
        self.assertFalse(self.journal.kill_switch_latched())

    def test_failed_public_operation_is_recorded_with_reason(self) -> None:
        self.broker.clock = replace(self.broker.clock, is_open=False)
        with self.assertRaisesRegex(PaperPolicyError, "regular market session"):
            self.workflow.propose_entry("SPY")
        failure = self.journal.latest_payload("paper_operation_failed")
        self.assertEqual(failure["operation"], "propose_entry")
        self.assertEqual(failure["error_type"], "PaperPolicyError")
        self.assertIn("regular market session", failure["reason"])

    def test_clean_rebaseline_ends_old_run_and_invalidates_old_approval(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        permit = self.journal.approve_and_consume(
            proposal,
            review["confirmation_code"],
            review_event_id=review["review_event_id"],
            session_id="old-run-session",
            now=NOW,
        )
        self.journal._append_state(
            "entry_filled",
            {
                "symbol": proposal.symbol,
                "quantity": str(proposal.quantity),
                "entry_price": str(proposal.ask),
                "entry_date": NOW.date().isoformat(),
                "planned_loss": str(proposal.planned_loss),
                "stop_price": str(proposal.stop_price),
                "parent_order_id": "old-parent",
                "stop_order_id": "old-stop",
                "client_order_id": proposal.client_order_id,
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        self.journal._append_state(
            "kill_switch_latched", {"reason": "manual_recovery_required"},
            occurred_at=NOW,
        )

        baseline = self.workflow.rebaseline_clean_account(
            "REBASELINE-PAPER-RUN-AT-CLEAN-500", now=NOW
        )
        self.assertEqual(baseline["run_number"], 2)
        self.assertTrue(baseline["prior_run_terminated"])
        self.assertFalse(self.journal.kill_switch_latched())
        self.assertFalse(reduce_events(self.journal.events()).positions)
        self.assertFalse(self.journal.claim_permit(proposal, permit, "submit_order"))
        with self.assertRaisesRegex(JournalError, "prior paper run"):
            self.workflow.review(proposal.proposal_id)
        report = self.workflow.reconcile_now(now=NOW)
        self.assertTrue(report.ok, report.issues)
        status = self.workflow.status()
        self.assertEqual(status["paper_run_number"], 2)
        self.assertTrue(status["paper_gate_restarted"])
        self.assertIsNotNone(self.workflow.propose_entry("SPY"))

    def test_rebaseline_requires_latch_confirmation_same_clean_account(self) -> None:
        confirmation = "REBASELINE-PAPER-RUN-AT-CLEAN-500"
        with self.assertRaisesRegex(PaperWorkflowError, "latched kill switch"):
            self.workflow.rebaseline_clean_account(confirmation, now=NOW)
        self.journal._append_state(
            "kill_switch_latched", {"reason": "test"}, occurred_at=NOW
        )
        with self.assertRaisesRegex(PaperWorkflowError, "confirmation is incorrect"):
            self.workflow.rebaseline_clean_account("WRONG", now=NOW)

        original_account = self.broker.account
        self.broker.account = replace(
            original_account, account_id="different-paper-account"
        )
        with self.assertRaisesRegex(PaperPolicyError, "different paper account"):
            self.workflow.rebaseline_clean_account(confirmation, now=NOW)

        self.broker.account = replace(
            original_account,
            equity=Decimal("499"),
            cash=Decimal("499"),
            non_marginable_buying_power=Decimal("499"),
            buying_power=Decimal("499"),
        )
        with self.assertRaisesRegex(PaperPolicyError, "reset to.*500"):
            self.workflow.rebaseline_clean_account(confirmation, now=NOW)

        self.broker.account = original_account
        self.broker.positions = [
            PaperPosition(
                "SPY", Decimal("1"), "long", Decimal("100"), Decimal("100"),
                Decimal("100"),
            )
        ]
        with self.assertRaisesRegex(PaperPolicyError, "no positions"):
            self.workflow.rebaseline_clean_account(confirmation, now=NOW)

        self.broker.positions = []
        self.broker.orders = [
            PaperOrder(
                "working", "manual", "SPY", "buy", "limit", "day", "simple",
                "new", Decimal("1"), Decimal("0"),
            )
        ]
        with self.assertRaisesRegex(PaperPolicyError, "no working orders"):
            self.workflow.rebaseline_clean_account(confirmation, now=NOW)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_status_latches_account_binding_mismatch_before_any_new_order(self) -> None:
        self.broker.account = replace(
            self.broker.account, account_id="different-paper-account"
        )
        status = self.workflow.status()
        self.assertFalse(status["reconciliation"]["ok"])
        self.assertIn("account_binding_mismatch", status["reconciliation"]["issues"])
        self.assertTrue(self.journal.kill_switch_latched())

    def test_runtime_config_mutation_and_wrong_proposal_digest_fail_closed(self) -> None:
        changed_strategy = copy.deepcopy(self.strategy)
        changed_strategy["strategy"]["rsi_entry_below"] = 99
        with self.assertRaisesRegex(PaperWorkflowError, "does not match frozen v1"):
            PaperWorkflow(self.broker, self.journal, changed_strategy, self.paper)

        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        self.workflow.paper_config["execution"]["approval_ttl_seconds"] = 999
        with self.assertRaisesRegex(PaperWorkflowError, "runtime configuration changed"):
            self.workflow.execute(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="session-1",
                environment=ENABLED,
            )
        self.assertEqual(self.broker.submitted_entries, 0)

        second_journal = PaperJournal(Path(self.temporary.name) / "second.sqlite")
        second_broker = FakeBroker()
        second_broker.permit_validator = second_journal.claim_permit
        second = PaperWorkflow(second_broker, second_journal, self.strategy, self.paper)
        second.bind_clean_account(now=NOW)
        wrong = replace(sample_proposal(), strategy_config_sha256="wrong-digest")
        second_journal.record_proposal(wrong)
        with self.assertRaisesRegex(PaperWorkflowError, "different frozen strategy"):
            second.review(wrong.proposal_id)

    def test_internally_inconsistent_stored_proposal_cannot_be_reviewed(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        malformed = replace(
            proposal,
            proposal_id="prop-e-malformed",
            client_order_id="swing-e-malformed",
            planned_loss=Decimal("0"),
        )
        self.journal.record_proposal(malformed)
        with self.assertRaisesRegex(PaperWorkflowError, "internally inconsistent"):
            self.workflow.review(malformed.proposal_id)

    def test_position_remains_local_until_broker_confirms_exit_fill(self) -> None:
        self.broker.entry_status = "filled"
        entry = self.workflow.propose_entry("SPY")
        entry_review = self.workflow.review(entry.proposal_id)
        entry_order = self.workflow.execute(
            entry.proposal_id, entry_review["confirmation_code"],
            session_id="session-entry", environment=ENABLED,
        )
        self._set_open_position(entry)
        report = self.workflow.reconcile_now(now=NOW)
        self.assertTrue(report.ok, report.issues)
        self.assertIn("SPY", reduce_events(self.journal.events()).positions)

        exit_proposal = self.workflow.propose_exit("SPY", reason="manual_owner_exit")
        exit_review = self.workflow.review(exit_proposal.proposal_id)
        exit_order = self.workflow.execute(
            exit_proposal.proposal_id,
            exit_review["confirmation_code"],
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
            filled_at=NOW,
        )
        self.broker.orders = [
            filled_exit if order.order_id == exit_order.order_id else order
            for order in self.broker.orders
        ]
        self.broker.positions = []
        exit_cash = self.broker.account.cash + exit_proposal.quantity * exit_proposal.bid
        self.broker.account = replace(
            self.broker.account,
            cash=exit_cash,
            non_marginable_buying_power=exit_cash,
            buying_power=exit_cash,
            long_market_value=Decimal("0"),
            equity=exit_cash,
        )
        final = self.workflow.reconcile_now(now=NOW)
        self.assertTrue(final.ok, final.issues)
        self.assertNotIn("SPY", reduce_events(self.journal.events()).positions)

    def test_uncertain_submission_latches_and_never_retries(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        self.broker.fail_submit = True
        with self.assertRaisesRegex(PaperWorkflowError, "outcome is uncertain"):
            self.workflow.execute(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="session-1",
                environment=ENABLED,
            )
        self.assertTrue(self.journal.kill_switch_latched())
        self.assertEqual(self.broker.submitted_entries, 1)

    def test_uncertain_stop_cancellation_latches_and_blocks_exit_submission(self) -> None:
        self.broker.entry_status = "filled"
        entry = self.workflow.propose_entry("SPY")
        entry_review = self.workflow.review(entry.proposal_id)
        entry_order = self.workflow.execute(
            entry.proposal_id, entry_review["confirmation_code"],
            session_id="session-entry", environment=ENABLED,
        )
        self._set_open_position(entry)
        report = self.workflow.reconcile_now(now=NOW)
        self.assertTrue(report.ok, report.issues)
        self.assertTrue(entry_order.legs)

        exit_proposal = self.workflow.propose_exit("SPY", reason="manual_owner_exit")
        exit_review = self.workflow.review(exit_proposal.proposal_id)
        self.broker.fail_cancel = True
        with self.assertRaisesRegex(PaperWorkflowError, "cancellation outcome is uncertain"):
            self.workflow.execute(
                exit_proposal.proposal_id,
                exit_review["confirmation_code"],
                session_id="session-exit",
                environment=ENABLED,
            )
        self.assertTrue(self.journal.kill_switch_latched())
        self.assertEqual(self.broker.submitted_exits, 0)

    def test_lost_cancel_verification_latches_and_blocks_exit_submission(self) -> None:
        self.broker.entry_status = "filled"
        entry = self.workflow.propose_entry("SPY")
        entry_review = self.workflow.review(entry.proposal_id)
        self.workflow.execute(
            entry.proposal_id, entry_review["confirmation_code"],
            session_id="session-entry", environment=ENABLED,
        )
        self._set_open_position(entry)
        self.assertTrue(self.workflow.reconcile_now(now=NOW).ok)
        exit_proposal = self.workflow.propose_exit("SPY", reason="manual_owner_exit")
        exit_review = self.workflow.review(exit_proposal.proposal_id)
        self.broker.fail_cancel_verification = True
        with self.assertRaisesRegex(PaperWorkflowError, "cancellation outcome is uncertain"):
            self.workflow.execute(
                exit_proposal.proposal_id,
                exit_review["confirmation_code"],
                session_id="session-exit",
                environment=ENABLED,
            )
        self.assertTrue(self.journal.kill_switch_latched())
        self.assertEqual(self.broker.submitted_exits, 0)

    def test_partial_entry_or_stop_limit_ack_latches_immediately(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        self.broker.entry_status = "partially_filled"
        with self.assertRaisesRegex(PaperWorkflowError, "partially filled"):
            self.workflow.execute(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="session-partial",
                environment=ENABLED,
            )
        self.assertTrue(self.journal.kill_switch_latched())

        second_journal = PaperJournal(Path(self.temporary.name) / "third.sqlite")
        second_broker = FakeBroker()
        second_broker.permit_validator = second_journal.claim_permit
        second = PaperWorkflow(second_broker, second_journal, self.strategy, self.paper)
        second.bind_clean_account(now=NOW)
        second_proposal = second.propose_entry("SPY")
        second_review = second.review(second_proposal.proposal_id)
        second_broker.entry_stop_type = "stop_limit"
        with self.assertRaisesRegex(PaperWorkflowError, "protective stop"):
            second.execute(
                second_proposal.proposal_id,
                second_review["confirmation_code"],
                session_id="session-stop-limit",
                environment=ENABLED,
            )
        self.assertTrue(second_journal.kill_switch_latched())


if __name__ == "__main__":
    unittest.main()
