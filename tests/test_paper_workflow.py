from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from swingbot.config import load_config
from swingbot.paper_config import load_paper_config
from swingbot.paper_journal import JournalError, PaperJournal
from swingbot.paper_models import PaperOrder, PaperPosition
from swingbot.paper_policy import PaperPolicyError
from swingbot.paper_state import reduce_events
from swingbot.paper_workflow import (
    AUTOPILOT_AUTHORIZATION,
    PaperWorkflow,
    PaperWorkflowError,
)

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

    def _new_open_position_stack(self, name: str):
        journal = PaperJournal(Path(self.temporary.name) / f"{name}.sqlite")
        broker = FakeBroker()
        broker.permit_validator = journal.claim_permit
        workflow = PaperWorkflow(broker, journal, self.strategy, self.paper)
        workflow.bind_clean_account(now=NOW)
        broker.entry_status = "filled"
        entry = workflow.propose_entry("SPY")
        review = workflow.review(entry.proposal_id)
        entry_order = workflow.execute(
            entry.proposal_id,
            review["confirmation_code"],
            session_id=f"session-{name}-entry",
            environment=ENABLED,
        )
        market_value = entry.quantity * entry.ask
        cash = Decimal("500") - market_value
        broker.positions = [
            PaperPosition(
                "SPY", entry.quantity, "long", entry.ask, entry.ask, market_value
            )
        ]
        broker.account = replace(
            broker.account,
            cash=cash,
            non_marginable_buying_power=cash,
            buying_power=cash,
            long_market_value=market_value,
            equity=cash + market_value,
        )
        self.assertTrue(workflow.reconcile_now(now=NOW).ok)
        exit_proposal = workflow.propose_exit(
            "SPY", reason="manual_owner_exit"
        )
        exit_review = workflow.review(exit_proposal.proposal_id)
        return journal, broker, workflow, entry_order, exit_proposal, exit_review

    def test_entry_proposal_is_whole_share_gtc(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        self.assertFalse(proposal.fractional)
        self.assertEqual(proposal.quantity, proposal.quantity.to_integral_value())
        self.assertEqual(proposal.time_in_force, "gtc")
        second = self.workflow.propose_entry("SPY")
        self.assertNotEqual(proposal.proposal_id, second.proposal_id)
        self.assertNotEqual(proposal.client_order_id, second.client_order_id)

    def test_execution_revalidates_current_cash_only_buying_power(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        reduced_cash = replace(
            self.broker.account,
            cash=Decimal("1"),
            non_marginable_buying_power=Decimal("1"),
        )
        with self.assertRaisesRegex(PaperWorkflowError, "cash-only buying power"):
            self.workflow._revalidate_entry(
                proposal,
                reduced_cash,
                self.broker.clock,
                self.broker.quote,
                [],
                [],
            )

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

    def test_automated_execution_requires_policy_and_records_its_true_source(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        with self.assertRaisesRegex(PaperWorkflowError, "autopilot authorization"):
            self.workflow.execute_automated(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="paper-autopilot-test",
                authorization="WRONG",
                environment=ENABLED,
            )
        order = self.workflow.execute_automated(
            proposal.proposal_id,
            review["confirmation_code"],
            session_id="paper-autopilot-test",
            authorization=AUTOPILOT_AUTHORIZATION,
            environment=ENABLED,
        )
        self.assertEqual(order.order_class, "oto")
        event_types = self.journal.proposal_event_types(proposal.proposal_id)
        self.assertIn("automation_approved", event_types)
        self.assertNotIn("owner_approved", event_types)
        with self.assertRaises(Exception):
            self.workflow.execute(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="session-1",
                environment=ENABLED,
            )
        self.assertEqual(self.broker.submitted_entries, 1)

    def test_runtime_kill_switch_and_live_endpoint_environment_overrides_are_rejected(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        with self.assertRaisesRegex(PaperWorkflowError, "runtime kill switch"):
            self.workflow.execute(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="session-killed",
                environment={
                    "SWINGBOT_PAPER_EXECUTION": "I_UNDERSTAND_PAPER_ONLY",
                    "SWINGBOT_KILL_SWITCH": "1",
                },
            )
        for variable in ("APCA_API_BASE_URL", "ALPACA_API_BASE_URL"):
            with self.subTest(variable=variable):
                environment = {**ENABLED, variable: "https://api.alpaca.markets"}
                with self.assertRaisesRegex(PaperWorkflowError, "outside the paper endpoint"):
                    self.workflow.execute(
                        proposal.proposal_id,
                        review["confirmation_code"],
                        session_id="session-live-override",
                        environment=environment,
                    )
        self.assertEqual(self.broker.submitted_entries, 0)

    def test_rebinding_is_idempotent_but_identity_change_latches(self) -> None:
        first = self.journal.account_binding()
        self.assertEqual(self.workflow.bind_clean_account(now=NOW), first)
        self.broker.account = replace(
            self.broker.account, account_id="different-paper-account"
        )
        with self.assertRaisesRegex(PaperPolicyError, "different paper account"):
            self.workflow.bind_clean_account(now=NOW)
        self.assertTrue(self.journal.kill_switch_latched())

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

    def test_final_refresh_blocks_expiry_or_market_close_during_preflight(self) -> None:
        for scenario in ("expiry", "quote_stale", "market_close"):
            with self.subTest(scenario=scenario):
                journal = PaperJournal(
                    Path(self.temporary.name) / f"final-refresh-{scenario}.sqlite"
                )
                broker = FakeBroker()
                broker.permit_validator = journal.claim_permit
                workflow = PaperWorkflow(broker, journal, self.strategy, self.paper)
                workflow.bind_clean_account(now=NOW)
                proposal = workflow.propose_entry("SPY")
                review = workflow.review(proposal.proposal_id)
                if scenario == "expiry":
                    broker.clock = replace(
                        broker.clock, timestamp=NOW + timedelta(seconds=119)
                    )
                    broker.quote = replace(
                        broker.quote, timestamp=broker.clock.timestamp
                    )
                else:
                    broker.clock = replace(
                        broker.clock, next_close=NOW + timedelta(seconds=1)
                    )
                original_asset = broker.get_asset

                def delayed_asset(symbol):
                    delay = 31 if scenario == "quote_stale" else 2
                    broker.clock = replace(
                        broker.clock,
                        timestamp=broker.clock.timestamp + timedelta(seconds=delay),
                        is_open=scenario != "market_close",
                    )
                    return original_asset(symbol)

                broker.get_asset = delayed_asset
                with self.assertRaises(Exception):
                    workflow.execute(
                        proposal.proposal_id,
                        review["confirmation_code"],
                        session_id=f"session-{scenario}",
                        environment=ENABLED,
                    )
                self.assertEqual(broker.submitted_entries, 0)

    def test_fill_timestamp_is_bounded_by_post_acknowledgement_clock(self) -> None:
        self.broker.entry_status = "filled"
        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        original_submit = self.broker.submit_entry

        def submit_with_normal_broker_latency(*args, **kwargs):
            order = original_submit(*args, **kwargs)
            order = replace(order, filled_at=NOW + timedelta(seconds=1))
            self.broker.orders = [order]
            self.broker.clock = replace(
                self.broker.clock, timestamp=NOW + timedelta(seconds=2)
            )
            return order

        self.broker.submit_entry = submit_with_normal_broker_latency
        order = self.workflow.execute(
            proposal.proposal_id,
            review["confirmation_code"],
            session_id="session-valid-fill-latency",
            environment=ENABLED,
        )
        self.assertEqual(order.filled_at, NOW + timedelta(seconds=1))
        self.assertEqual(self.broker.submitted_entries, 1)
        self.assertFalse(self.journal.kill_switch_latched())

    def test_entry_and_stop_can_both_fill_before_acknowledgement(self) -> None:
        self.broker.entry_status = "filled"
        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        original_submit = self.broker.submit_entry

        def submit_round_trip(*args, **kwargs):
            order = original_submit(*args, **kwargs)
            stop = replace(
                order.legs[0],
                status="filled",
                filled_quantity=proposal.quantity,
                filled_average_price=proposal.stop_price,
                filled_at=NOW + timedelta(seconds=2),
            )
            order = replace(
                order,
                filled_at=NOW + timedelta(seconds=1),
                legs=(stop,),
            )
            self.broker.orders = [order]
            self.broker.clock = replace(
                self.broker.clock, timestamp=NOW + timedelta(seconds=3)
            )
            return order

        self.broker.submit_entry = submit_round_trip
        order = self.workflow.execute(
            proposal.proposal_id,
            review["confirmation_code"],
            session_id="session-round-trip-ack",
            environment=ENABLED,
        )
        self.assertEqual(order.legs[0].status, "filled")
        self.assertFalse(self.journal.kill_switch_latched())

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

    def test_exit_scan_reports_active_rule_and_deduplicates_same_observation(self) -> None:
        self.assertEqual(self.workflow.scan_exits(), [])
        self.broker.entry_status = "filled"
        entry = self.workflow.propose_entry("SPY")
        review = self.workflow.review(entry.proposal_id)
        self.workflow.execute(
            entry.proposal_id,
            review["confirmation_code"],
            session_id="session-entry",
            environment=ENABLED,
        )
        self._set_open_position(entry)
        self.assertTrue(self.workflow.reconcile_now(now=NOW).ok)

        first = self.workflow.scan_exits()
        self.assertEqual(
            first,
            [
                {
                    "symbol": "SPY",
                    "bar_date": (NOW.date() - timedelta(days=1)).isoformat(),
                    "exit_required": True,
                    "reason": "recovery_target",
                }
            ],
        )
        event_count = sum(
            event["event_type"].startswith("live_exit_")
            for event in self.journal.events()
        )
        self.assertEqual(self.workflow.scan_exits(), first)
        self.assertEqual(
            sum(
                event["event_type"].startswith("live_exit_")
                for event in self.journal.events()
            ),
            event_count,
        )

    def test_auto_exit_requires_current_deterministic_rule(self) -> None:
        with self.assertRaisesRegex(PaperWorkflowError, "no reconciled managed position"):
            self.workflow.propose_exit("SPY", reason="auto")

        self.broker.entry_status = "filled"
        entry = self.workflow.propose_entry("SPY")
        review = self.workflow.review(entry.proposal_id)
        self.workflow.execute(
            entry.proposal_id,
            review["confirmation_code"],
            session_id="session-entry",
            environment=ENABLED,
        )
        self._set_open_position(entry)
        self.assertTrue(self.workflow.reconcile_now(now=NOW).ok)
        exit_proposal = self.workflow.propose_exit("SPY", reason="auto")
        self.assertEqual(exit_proposal.exit_reason, "recovery_target")

        original_bars = self.broker.bars["SPY"]
        self.broker.bars["SPY"] = original_bars[:-1]
        with self.assertRaisesRegex(PaperWorkflowError, "latest completed trading-day bar"):
            self.workflow.propose_exit("SPY", reason="auto")
        self.broker.bars["SPY"] = original_bars
        with self.assertRaisesRegex(PaperWorkflowError, "unsupported exit reason"):
            self.workflow.propose_exit("SPY", reason="unsupported")

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
        self.assertFalse(
            self.journal.claim_permit(proposal, permit, "submit_order", NOW)
        )
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
        self.assertEqual(
            exit_review["protective_stop_order_id"], entry_order.legs[0].order_id
        )
        self.assertEqual(
            exit_review["protective_stop"], str(entry_order.legs[0].stop_price)
        )
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

    def test_terminal_entry_ack_and_submission_journal_failure_latch(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        review = self.workflow.review(proposal.proposal_id)
        self.broker.entry_status = "rejected"
        with self.assertRaisesRegex(PaperWorkflowError, "not working: rejected"):
            self.workflow.execute(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="session-rejected",
                environment=ENABLED,
            )
        self.assertEqual(self.broker.submitted_entries, 1)
        self.assertTrue(self.journal.kill_switch_latched())

        journal = PaperJournal(Path(self.temporary.name) / "journal-failure.sqlite")
        broker = FakeBroker()
        broker.permit_validator = journal.claim_permit
        workflow = PaperWorkflow(broker, journal, self.strategy, self.paper)
        workflow.bind_clean_account(now=NOW)
        second = workflow.propose_entry("SPY")
        second_review = workflow.review(second.proposal_id)
        original_append_state = journal._append_state

        def fail_order_submitted(event_type, payload, **kwargs):
            if event_type == "order_submitted":
                raise RuntimeError("simulated journal write failure")
            return original_append_state(event_type, payload, **kwargs)

        with patch.object(journal, "_append_state", side_effect=fail_order_submitted):
            with self.assertRaisesRegex(PaperWorkflowError, "could not be journaled"):
                workflow.execute(
                    second.proposal_id,
                    second_review["confirmation_code"],
                    session_id="session-journal-failure",
                    environment=ENABLED,
                )
        self.assertEqual(broker.submitted_entries, 1)
        self.assertTrue(journal.kill_switch_latched())

    def test_stop_cancel_unconfirmed_filled_or_unjournaled_blocks_exit(self) -> None:
        for scenario in ("unconfirmed", "filled", "partial_then_canceled", "unjournaled"):
            with self.subTest(scenario=scenario):
                (
                    journal,
                    broker,
                    workflow,
                    entry_order,
                    proposal,
                    review,
                ) = self._new_open_position_stack(f"cancel-{scenario}")
                original_cancel = broker.cancel_order
                if scenario == "unconfirmed":
                    broker.cancel_order = lambda *_args, **_kwargs: replace(
                        entry_order.legs[0], status="pending_cancel"
                    )
                    expected = "cancellation was not confirmed"
                    context = patch.object(
                        journal,
                        "record_protective_stop_cancellation_verified",
                        wraps=journal.record_protective_stop_cancellation_verified,
                    )
                elif scenario == "filled":
                    broker.cancel_order = lambda *_args, **_kwargs: replace(
                        entry_order.legs[0],
                        status="filled",
                        filled_quantity=entry_order.legs[0].quantity,
                        filled_average_price=entry_order.legs[0].stop_price,
                        filled_at=NOW,
                    )
                    expected = "protective stop filled"
                    context = patch.object(
                        journal,
                        "record_protective_stop_cancellation_verified",
                        wraps=journal.record_protective_stop_cancellation_verified,
                    )
                elif scenario == "partial_then_canceled":
                    broker.cancel_order = lambda *_args, **_kwargs: replace(
                        entry_order.legs[0],
                        status="canceled",
                        filled_quantity=entry_order.legs[0].quantity / 2,
                        filled_average_price=entry_order.legs[0].stop_price,
                        filled_at=NOW,
                    )
                    expected = "partially filled before cancellation"
                    context = patch.object(
                        journal,
                        "record_protective_stop_cancellation_verified",
                        wraps=journal.record_protective_stop_cancellation_verified,
                    )
                else:
                    broker.cancel_order = original_cancel
                    expected = "verification could not be journaled"
                    context = patch.object(
                        journal,
                        "record_protective_stop_cancellation_verified",
                        side_effect=RuntimeError("simulated verification write failure"),
                    )
                with context:
                    with self.assertRaisesRegex(PaperWorkflowError, expected):
                        workflow.execute(
                            proposal.proposal_id,
                            review["confirmation_code"],
                            session_id=f"session-{scenario}-exit",
                            environment=ENABLED,
                        )
                self.assertEqual(broker.submitted_exits, 0)
                self.assertTrue(journal.kill_switch_latched())

    def test_position_is_rechecked_after_protective_stop_cancellation(self) -> None:
        journal, broker, workflow, _entry_order, proposal, review = (
            self._new_open_position_stack("post-cancel-position-change")
        )
        original_cancel = broker.cancel_order

        def cancel_then_change_position(*args, **kwargs):
            stop = original_cancel(*args, **kwargs)
            broker.positions = [
                replace(broker.positions[0], quantity=proposal.quantity / 2)
            ]
            return stop

        broker.cancel_order = cancel_then_change_position
        with self.assertRaisesRegex(PaperWorkflowError, "state changed after stop cancellation"):
            workflow.execute(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="session-post-cancel-change",
                environment=ENABLED,
            )
        self.assertEqual(broker.submitted_exits, 0)
        self.assertTrue(journal.kill_switch_latched())

    def test_exit_is_rejected_too_close_to_market_close_before_stop_cancel(self) -> None:
        journal, broker, workflow, _entry_order, proposal, review = (
            self._new_open_position_stack("near-close")
        )
        broker.clock = replace(
            broker.clock, next_close=broker.clock.timestamp + timedelta(seconds=30)
        )
        with self.assertRaisesRegex(PaperWorkflowError, "too close"):
            workflow.execute(
                proposal.proposal_id,
                review["confirmation_code"],
                session_id="session-near-close",
                environment=ENABLED,
            )
        self.assertEqual(broker.canceled_order_ids, [])
        self.assertEqual(broker.submitted_exits, 0)

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

    def test_entry_ack_rejects_envelope_and_fill_inconsistencies(self) -> None:
        proposal = self.workflow.propose_entry("SPY")
        stop = PaperOrder(
            "stop-1",
            "",
            proposal.symbol,
            "sell",
            "stop",
            "gtc",
            "simple",
            "held",
            proposal.quantity,
            Decimal("0"),
            stop_price=proposal.stop_price,
        )
        base = PaperOrder(
            "entry-1",
            proposal.client_order_id,
            proposal.symbol,
            "buy",
            "market",
            "gtc",
            "oto",
            "new",
            proposal.quantity,
            Decimal("0"),
            legs=(stop,),
        )
        self.workflow._validate_entry_ack(proposal, base, NOW)
        invalid = (
            (replace(base, symbol="QQQ"), "differs from approved order"),
            (
                replace(base, filled_quantity=proposal.quantity),
                "unfilled broker entry reports inconsistent fill fields",
            ),
            (
                replace(
                    base,
                    status="filled",
                    filled_quantity=proposal.quantity,
                    filled_average_price=None,
                    filled_at=NOW,
                    legs=(replace(stop, status="new"),),
                ),
                "incomplete or inconsistent fill evidence",
            ),
            (
                replace(
                    base,
                    status="filled",
                    filled_quantity=proposal.quantity,
                    filled_average_price=proposal.ask,
                    filled_at=NOW,
                ),
                "protective stop is missing or mismatched",
            ),
        )
        for order, message in invalid:
            with self.subTest(message=message):
                with self.assertRaisesRegex(PaperWorkflowError, message):
                    self.workflow._validate_entry_ack(proposal, order, NOW)

    def test_exit_ack_rejects_envelope_partial_and_fill_inconsistencies(self) -> None:
        proposal = replace(
            sample_proposal(action="close_position"),
            proposal_id="prop-x-test",
            client_order_id="swing-x-test",
            strategy_config_sha256=self.paper["strategy_config_sha256"],
        )
        base = PaperOrder(
            "exit-1",
            proposal.client_order_id,
            proposal.symbol,
            "sell",
            "market",
            "day",
            "simple",
            "new",
            proposal.quantity,
            Decimal("0"),
        )
        self.workflow._validate_exit_ack(proposal, base, NOW)
        invalid = (
            (replace(base, side="buy"), "differs from approved order"),
            (
                replace(
                    base,
                    status="partially_filled",
                    filled_quantity=proposal.quantity / 2,
                    filled_average_price=proposal.bid,
                ),
                "partially filled",
            ),
            (
                replace(
                    base,
                    status="filled",
                    filled_quantity=proposal.quantity,
                    filled_average_price=None,
                    filled_at=NOW,
                ),
                "incomplete or inconsistent fill evidence",
            ),
            (
                replace(base, filled_at=NOW),
                "unfilled broker exit reports inconsistent fill fields",
            ),
        )
        for order, message in invalid:
            with self.subTest(message=message):
                with self.assertRaisesRegex(PaperWorkflowError, message):
                    self.workflow._validate_exit_ack(proposal, order, NOW)


if __name__ == "__main__":
    unittest.main()
