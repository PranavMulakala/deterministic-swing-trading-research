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
from swingbot.paper_reconcile import PaperReconciler
from swingbot.paper_state import reduce_events

from paper_fixtures import FakeBroker, NOW, ACCOUNT_ID, sample_proposal


ROOT = Path(__file__).parents[1]


class PaperReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.journal = PaperJournal(Path(self.temporary.name) / "journal.sqlite")
        self.paper = load_paper_config(
            ROOT / "config/paper_v1.json", ROOT / "config/strategy_v1.json"
        )
        self.strategy = load_config(ROOT / "config/strategy_v1.json")
        self.journal._append_state(
            "account_bound",
            {"account_id": ACCOUNT_ID, "initial_equity": "500"},
            occurred_at=NOW,
        )
        self.reconciler = PaperReconciler(self.journal, self.paper, self.strategy)
        self.broker = FakeBroker()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_unknown_position_latches_durable_kill_switch(self) -> None:
        position = PaperPosition(
            "SPY", Decimal("1"), "long", Decimal("100"), Decimal("101"), Decimal("101")
        )
        report = self.reconciler.reconcile(
            account=self.broker.account,
            positions=[position],
            orders=[],
            now=NOW,
        )
        self.assertFalse(report.ok)
        self.assertIn("unknown_broker_position:SPY", report.issues)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_cash_ledger_and_accounting_identities_fail_closed(self) -> None:
        inconsistent = replace(
            self.broker.account,
            cash=Decimal("499"),
            non_marginable_buying_power=Decimal("499"),
            buying_power=Decimal("499"),
        )
        report = self.reconciler.reconcile(
            account=inconsistent, positions=[], orders=[], now=NOW
        )
        self.assertIn("account_equity_identity_mismatch", report.issues)
        self.assertIn("cash_ledger_mismatch", report.issues)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_market_driven_aggregate_risk_ratio_warns_without_deadlocking_exits(self) -> None:
        self.journal._append_state(
            "entry_filled",
            {
                "symbol": "SPY", "quantity": "1", "entry_price": "100",
                "entry_date": NOW.date().isoformat(), "planned_loss": "15",
                "stop_price": "90", "parent_order_id": "parent-risk",
                "stop_order_id": "stop-risk", "client_order_id": "client-risk",
            },
            occurred_at=NOW,
        )
        stop = PaperOrder(
            "stop-risk", "", "SPY", "sell", "stop", "gtc", "simple",
            "new", Decimal("1"), Decimal("0"), stop_price=Decimal("90"),
        )
        parent = PaperOrder(
            "parent-risk", "client-risk", "SPY", "buy", "market", "gtc",
            "oto", "filled", Decimal("1"), Decimal("1"),
            filled_average_price=Decimal("100"), legs=(stop,), filled_at=NOW,
        )
        position = PaperPosition(
            "SPY", Decimal("1"), "long", Decimal("100"), Decimal("99"),
            Decimal("99"),
        )
        account = replace(
            self.broker.account,
            cash=Decimal("400"), non_marginable_buying_power=Decimal("400"),
            buying_power=Decimal("400"), long_market_value=Decimal("99"),
            equity=Decimal("499"),
        )
        report = self.reconciler.reconcile(
            account=account, positions=[position], orders=[parent], now=NOW
        )
        self.assertTrue(report.ok, report.issues)
        self.assertEqual(
            report.warnings, ("aggregate_open_risk_breach_observed",)
        )
        self.assertFalse(self.journal.kill_switch_latched())

    def test_position_market_value_identities_fail_closed(self) -> None:
        position = PaperPosition(
            "SPY", Decimal("1"), "long", Decimal("100"), Decimal("101"), Decimal("100")
        )
        account = replace(
            self.broker.account,
            cash=Decimal("400"),
            non_marginable_buying_power=Decimal("400"),
            buying_power=Decimal("400"),
            long_market_value=Decimal("101"),
            equity=Decimal("501"),
        )
        report = self.reconciler.reconcile(
            account=account, positions=[position], orders=[], now=NOW
        )
        self.assertIn("broker_position_market_value_mismatch:SPY", report.issues)
        self.assertIn("account_position_market_value_mismatch", report.issues)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_duplicate_or_malformed_broker_positions_fail_closed(self) -> None:
        good = PaperPosition(
            "SPY", Decimal("1"), "long", Decimal("100"), Decimal("101"), Decimal("101")
        )
        malformed = replace(good, quantity=Decimal("-1"), market_value=Decimal("-101"))
        report = self.reconciler.reconcile(
            account=self.broker.account,
            positions=[good, malformed],
            orders=[],
            now=NOW,
        )
        self.assertIn("duplicate_broker_position:SPY", report.issues)
        self.assertIn("invalid_broker_position_values:SPY", report.issues)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_broker_fill_creates_local_position_only_during_reconciliation(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        stop = PaperOrder(
            "stop-1", "", "SPY", "sell", "stop", "gtc", "", "new",
            proposal.quantity, Decimal("0"), stop_price=proposal.stop_price,
        )
        parent = PaperOrder(
            "entry-1", proposal.client_order_id, "SPY", "buy", "market", "gtc", "oto",
            "filled", proposal.quantity, proposal.quantity,
            filled_average_price=Decimal("120.10"), legs=(stop,), filled_at=NOW,
        )
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id, "broker_order_id": parent.order_id,
                "status": "filled",
                "filled_quantity": str(parent.filled_quantity),
                "filled_average_price": str(parent.filled_average_price),
                "filled_at": parent.filled_at.isoformat(),
                "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        self.assertFalse(any(event["event_type"] == "entry_filled" for event in self.journal.events()))
        broker_position = PaperPosition(
            "SPY", proposal.quantity, "long", Decimal("120.10"), Decimal("120.10"), Decimal("120.10")
        )
        cash = Decimal("500") - proposal.quantity * Decimal("120.10")
        account = replace(
            self.broker.account,
            cash=cash,
            non_marginable_buying_power=cash,
            buying_power=cash,
            long_market_value=broker_position.market_value,
            equity=cash + broker_position.market_value,
        )
        report = self.reconciler.reconcile(
            account=account,
            positions=[broker_position],
            orders=[parent],
            now=NOW,
        )
        self.assertTrue(report.ok, report.issues)
        self.assertTrue(any(event["event_type"] == "entry_filled" for event in self.journal.events()))

    def test_filled_parent_with_still_held_child_is_not_treated_as_protected(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        held_stop = PaperOrder(
            "held-stop", "", "SPY", "sell", "stop", "gtc", "simple", "held",
            proposal.quantity, Decimal("0"), stop_price=proposal.stop_price,
        )
        parent = PaperOrder(
            "held-parent", proposal.client_order_id, "SPY", "buy", "market", "gtc", "oto",
            "filled", proposal.quantity, proposal.quantity,
            filled_average_price=Decimal("120.10"), legs=(held_stop,), filled_at=NOW,
        )
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": parent.order_id, "status": "filled",
                "filled_quantity": str(parent.filled_quantity),
                "filled_average_price": str(parent.filled_average_price),
                "filled_at": parent.filled_at.isoformat(),
                "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        position = PaperPosition(
            "SPY", proposal.quantity, "long", Decimal("120.10"),
            Decimal("120.10"), Decimal("120.10"),
        )
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[position], orders=[parent], now=NOW
        )
        self.assertIn("filled_entry_stop_not_active:SPY:held", report.issues)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_partial_fill_and_missing_stop_both_fail_closed(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        partial = PaperOrder(
            "entry-partial", proposal.client_order_id, "SPY", "buy", "market", "gtc", "oto",
            "partially_filled", proposal.quantity, Decimal("0.5"),
            filled_average_price=Decimal("120"), legs=(),
        )
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": partial.order_id,
                "status": partial.status,
                "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        broker_position = PaperPosition(
            "SPY", Decimal("0.5"), "long", Decimal("120"), Decimal("120"), Decimal("60")
        )
        partial_report = self.reconciler.reconcile(
            account=self.broker.account,
            positions=[broker_position],
            orders=[partial],
            now=NOW,
        )
        self.assertIn("partially_filled_entry_unprotected:SPY", partial_report.issues)

        with TemporaryDirectory() as second_directory:
            journal = PaperJournal(Path(second_directory) / "journal.sqlite")
            journal._append_state("account_bound", {"account_id": ACCOUNT_ID}, occurred_at=NOW)
            journal._append_state(
                "entry_filled",
                {
                    "symbol": "SPY", "quantity": "1", "entry_price": "120",
                    "entry_date": NOW.date().isoformat(), "planned_loss": "2",
                    "stop_price": "115", "parent_order_id": "parent",
                    "stop_order_id": "missing-stop", "client_order_id": "client",
                },
                occurred_at=NOW,
            )
            missing_report = PaperReconciler(journal, self.paper, self.strategy).reconcile(
                account=self.broker.account,
                positions=[replace(broker_position, quantity=Decimal("1"), market_value=Decimal("120"))],
                orders=[],
                now=NOW,
            )
            self.assertIn("missing_working_native_stop:SPY", missing_report.issues)

    def test_partial_fill_latches_even_before_position_endpoint_catches_up(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        partial = PaperOrder(
            "entry-partial", proposal.client_order_id, "SPY", "buy", "market", "gtc", "oto",
            "partially_filled", proposal.quantity, Decimal("0.5"),
            filled_average_price=Decimal("120"), legs=(),
        )
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": partial.order_id,
                "status": partial.status,
                "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[], orders=[partial], now=NOW
        )
        self.assertIn("partially_filled_entry_unprotected:SPY", report.issues)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_different_account_id_is_rejected_and_latched(self) -> None:
        report = self.reconciler.reconcile(
            account=replace(self.broker.account, account_id="another-paper-account"),
            positions=[],
            orders=[],
            now=NOW,
        )
        self.assertIn("account_binding_mismatch", report.issues)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_known_working_order_missing_from_broker_is_not_silently_ignored(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": "missing-parent", "status": "new",
                "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[], orders=[], now=NOW
        )
        self.assertIn(
            "known_working_order_missing_from_broker:missing-parent", report.issues
        )

    def test_restart_recovers_exact_claimed_submission_from_broker(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        review = self.journal.record_review(
            proposal, quote_timestamp=NOW, bid="119.9", ask="120.1", reviewed_at=NOW
        )
        permit = self.journal.approve_and_consume(
            proposal,
            self.journal.confirmation_code_for_review(proposal, review),
            review_event_id=review["event_id"],
            session_id="session",
            now=NOW,
        )
        self.journal._append_state(
            "order_submission_started",
            {
                "action": proposal.action,
                "symbol": proposal.symbol,
                "client_order_id": proposal.client_order_id,
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        self.assertTrue(self.journal.claim_permit(proposal, permit, "submit_order"))
        stop = PaperOrder(
            "restart-stop", "", "SPY", "sell", "stop", "gtc", "simple", "held",
            proposal.quantity, Decimal("0"), stop_price=proposal.stop_price,
        )
        parent = PaperOrder(
            "restart-parent", proposal.client_order_id, "SPY", "buy", "market", "gtc",
            "oto", "new", proposal.quantity, Decimal("0"), legs=(stop,),
        )
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[], orders=[parent], now=NOW
        )
        self.assertTrue(report.ok, report.issues)
        recovered = [
            event for event in self.journal.events()
            if event["event_type"] == "order_submitted"
        ]
        self.assertEqual(len(recovered), 1)
        self.assertTrue(recovered[0]["payload"]["recovered_after_restart"])

    def test_restart_with_claimed_submission_and_no_broker_order_latches(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        review = self.journal.record_review(
            proposal, quote_timestamp=NOW, bid="119.9", ask="120.1", reviewed_at=NOW
        )
        permit = self.journal.approve_and_consume(
            proposal,
            self.journal.confirmation_code_for_review(proposal, review),
            review_event_id=review["event_id"],
            session_id="session",
            now=NOW,
        )
        self.journal._append_state(
            "order_submission_started",
            {
                "action": proposal.action,
                "symbol": proposal.symbol,
                "client_order_id": proposal.client_order_id,
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        self.assertTrue(self.journal.claim_permit(proposal, permit, "submit_order"))
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[], orders=[], now=NOW
        )
        self.assertIn(
            f"claimed_submission_has_uncertain_broker_outcome:{proposal.client_order_id}",
            report.issues,
        )
        self.assertTrue(self.journal.kill_switch_latched())

    def test_actual_fill_risk_breach_is_measured_and_latched(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        stop = PaperOrder(
            "stop-risk", "", "SPY", "sell", "stop", "gtc", "", "new",
            proposal.quantity, Decimal("0"), stop_price=proposal.stop_price,
        )
        parent = PaperOrder(
            "entry-risk", proposal.client_order_id, "SPY", "buy", "market", "gtc", "oto",
            "filled", proposal.quantity, proposal.quantity,
            filled_average_price=Decimal("125"), legs=(stop,), filled_at=NOW,
        )
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": parent.order_id, "status": "filled",
                "filled_quantity": str(parent.filled_quantity),
                "filled_average_price": str(parent.filled_average_price),
                "filled_at": parent.filled_at.isoformat(),
                "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        position = PaperPosition(
            "SPY", proposal.quantity, "long", Decimal("125"), Decimal("125"), Decimal("125")
        )
        report = self.reconciler.reconcile(
            account=self.broker.account,
            positions=[position],
            orders=[parent],
            now=NOW,
        )
        self.assertIn("filled_entry_risk_limit_breach:SPY", report.issues)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_native_stop_must_be_nested_under_recorded_parent(self) -> None:
        self.journal._append_state(
            "entry_filled",
            {
                "symbol": "SPY", "quantity": "1", "entry_price": "120",
                "entry_date": NOW.date().isoformat(), "planned_loss": "2",
                "stop_price": "118", "parent_order_id": "expected-parent",
                "stop_order_id": "stop-1", "client_order_id": "client-1",
            },
            occurred_at=NOW,
        )
        stop = PaperOrder(
            "stop-1", "", "SPY", "sell", "stop", "gtc", "", "new",
            Decimal("1"), Decimal("0"), stop_price=Decimal("118"),
        )
        wrong_parent = PaperOrder(
            "wrong-parent", "", "SPY", "buy", "market", "gtc", "oto", "filled",
            Decimal("1"), Decimal("1"), filled_average_price=Decimal("120"),
            legs=(stop,),
        )
        position = PaperPosition(
            "SPY", Decimal("1"), "long", Decimal("120"), Decimal("120"), Decimal("120")
        )
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[position], orders=[wrong_parent], now=NOW
        )
        self.assertIn("native_stop_parent_mismatch:SPY", report.issues)

    def test_unknown_status_and_duplicate_client_id_latch(self) -> None:
        first = PaperOrder(
            "manual-1", "duplicate-client", "SPY", "buy", "market", "day", "simple",
            "mystery_status", Decimal("1"), Decimal("0"),
        )
        second = replace(first, order_id="manual-2", status="new")
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[], orders=[first, second], now=NOW
        )
        self.assertIn("unknown_order_status:manual-1:mystery_status", report.issues)
        self.assertIn("duplicate_broker_client_order_id:duplicate-client", report.issues)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_terminal_status_or_filled_quantity_cannot_regress(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": "regressed-parent", "status": "filled",
                "filled_quantity": "1", "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        stop = PaperOrder(
            "regressed-stop", "", "SPY", "sell", "stop", "gtc", "simple", "held",
            Decimal("1"), Decimal("0"), stop_price=proposal.stop_price,
        )
        regressed = PaperOrder(
            "regressed-parent", proposal.client_order_id, "SPY", "buy", "market", "gtc",
            "oto", "new", Decimal("1"), Decimal("0"), legs=(stop,),
        )
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[], orders=[regressed], now=NOW
        )
        self.assertIn(
            "terminal_order_state_changed:regressed-parent:filled:new", report.issues
        )
        self.assertIn("order_filled_quantity_invalid:regressed-parent", report.issues)

    def test_partial_fill_quantity_is_recorded_even_when_status_does_not_change(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        stop = PaperOrder(
            "partial-stop", "", "SPY", "sell", "stop", "gtc", "simple", "held",
            proposal.quantity, Decimal("0"), stop_price=proposal.stop_price,
        )
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": "partial-parent", "status": "partially_filled",
                "filled_quantity": "0.25", "filled_average_price": "120",
                "filled_at": None, "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        advanced = PaperOrder(
            "partial-parent", proposal.client_order_id, "SPY", "buy", "market", "gtc",
            "oto", "partially_filled", proposal.quantity, Decimal("0.5"),
            filled_average_price=Decimal("120.1"), legs=(stop,),
        )
        first = self.reconciler.reconcile(
            account=self.broker.account, positions=[], orders=[advanced], now=NOW
        )
        self.assertIn("partially_filled_entry_unprotected:SPY", first.issues)
        self.assertEqual(
            reduce_events(self.journal.events()).last_filled_quantity["partial-parent"],
            Decimal("0.5"),
        )
        regressed = replace(advanced, filled_quantity=Decimal("0.4"))
        second = self.reconciler.reconcile(
            account=self.broker.account, positions=[], orders=[regressed], now=NOW
        )
        self.assertIn("order_filled_quantity_invalid:partial-parent", second.issues)

    def test_known_order_envelope_mutation_is_rejected(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": "mutated-parent", "status": "new",
                "filled_quantity": "0", "filled_average_price": None,
                "filled_at": None, "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        stop = PaperOrder(
            "mutated-stop", "", "SPY", "sell", "stop", "gtc", "simple", "held",
            proposal.quantity, Decimal("0"), stop_price=proposal.stop_price,
        )
        mutated = PaperOrder(
            "mutated-parent", proposal.client_order_id, "SPY", "buy", "limit", "gtc",
            "oto", "new", proposal.quantity, Decimal("0"), legs=(stop,),
        )
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[], orders=[mutated], now=NOW
        )
        self.assertIn(f"observed_order_mismatch:{proposal.client_order_id}", report.issues)

    def test_filled_entry_cannot_import_a_recursively_nested_stop(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": "nested-parent", "status": "new",
                "filled_quantity": "0", "filled_average_price": None,
                "filled_at": None, "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        stop = PaperOrder(
            "nested-stop", "", "SPY", "sell", "stop", "gtc", "simple", "new",
            proposal.quantity, Decimal("0"), stop_price=proposal.stop_price,
        )
        container = PaperOrder(
            "nested-container", "", "SPY", "sell", "limit", "gtc", "simple", "new",
            proposal.quantity, Decimal("0"), legs=(stop,),
        )
        parent = PaperOrder(
            "nested-parent", proposal.client_order_id, "SPY", "buy", "market", "gtc",
            "oto", "filled", proposal.quantity, proposal.quantity,
            filled_average_price=Decimal("120.1"), filled_at=NOW, legs=(container,),
        )
        position = PaperPosition(
            "SPY", proposal.quantity, "long", Decimal("120.1"),
            Decimal("120.1"), Decimal("120.1"),
        )
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[position], orders=[parent], now=NOW
        )
        self.assertIn(f"observed_order_mismatch:{proposal.client_order_id}", report.issues)
        self.assertNotIn("SPY", reduce_events(self.journal.events()).positions)

    def test_working_stop_after_local_close_is_never_treated_as_harmless(self) -> None:
        self.journal._append_state(
            "entry_filled",
            {
                "symbol": "SPY", "quantity": "1", "entry_price": "120",
                "entry_date": NOW.date().isoformat(), "planned_loss": "2",
                "stop_price": "118", "parent_order_id": "parent-orphan",
                "stop_order_id": "stop-orphan", "client_order_id": "entry-orphan",
            },
            occurred_at=NOW,
        )
        self.journal._append_state(
            "position_closed",
            {
                "symbol": "SPY", "quantity": "1", "exit_price": "121",
                "closed_date": NOW.date().isoformat(), "realized_pnl": "1",
                "reason": "manual_owner_exit", "broker_order_id": "exit-orphan",
            },
            occurred_at=NOW,
        )
        stop = PaperOrder(
            "stop-orphan", "", "SPY", "sell", "stop", "gtc", "simple", "new",
            Decimal("1"), Decimal("0"), stop_price=Decimal("118"),
        )
        parent = PaperOrder(
            "parent-orphan", "entry-orphan", "SPY", "buy", "market", "gtc", "oto",
            "filled", Decimal("1"), Decimal("1"),
            filled_average_price=Decimal("120"), legs=(stop,), filled_at=NOW,
        )
        report = self.reconciler.reconcile(
            account=self.broker.account, positions=[], orders=[parent], now=NOW
        )
        self.assertIn("orphan_working_native_stop:stop-orphan", report.issues)
        self.assertTrue(self.journal.kill_switch_latched())

    def test_account_marks_are_appended_and_fill_dates_use_broker_time(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        stop = PaperOrder(
            "stop-time", "", "SPY", "sell", "stop", "gtc", "simple", "new",
            proposal.quantity, Decimal("0"), stop_price=proposal.stop_price,
        )
        parent = PaperOrder(
            "entry-time", proposal.client_order_id, "SPY", "buy", "market", "gtc", "oto",
            "filled", proposal.quantity, proposal.quantity,
            filled_average_price=Decimal("120.10"), legs=(stop,), filled_at=NOW,
        )
        self.journal._append_state(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": parent.order_id, "status": "filled",
                "filled_quantity": str(parent.filled_quantity),
                "filled_average_price": str(parent.filled_average_price),
                "filled_at": parent.filled_at.isoformat(),
                "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        position = PaperPosition(
            "SPY", proposal.quantity, "long", Decimal("120.10"),
            Decimal("121"), Decimal("121"),
        )
        entry_cash = Decimal("500") - parent.filled_quantity * Decimal("120.10")
        open_account = replace(
            self.broker.account,
            cash=entry_cash,
            non_marginable_buying_power=entry_cash,
            buying_power=entry_cash,
            long_market_value=position.market_value,
            equity=entry_cash + position.market_value,
        )
        delayed = NOW + timedelta(days=2)
        report = self.reconciler.reconcile(
            account=open_account, positions=[position], orders=[parent], now=delayed
        )
        self.assertTrue(report.ok, report.issues)
        state = reduce_events(self.journal.events())
        self.assertEqual(state.positions["SPY"].entry_date, NOW.date())
        snapshot = self.journal.latest_payload("account_snapshot_observed")
        self.assertEqual(snapshot["positions"][0]["current_price"], "121")
        self.assertEqual(snapshot["day_pnl"], "0.9")

        exit_proposal = replace(
            sample_proposal(action="close_position"),
            proposal_id="prop-exit-time",
            client_order_id="swing-exit-time",
        )
        self.journal.record_proposal(exit_proposal)
        exit_fill_time = NOW + timedelta(days=1)
        exit_order = PaperOrder(
            "exit-time", exit_proposal.client_order_id, "SPY", "sell", "market", "day",
            "simple", "filled", exit_proposal.quantity, exit_proposal.quantity,
            filled_average_price=Decimal("119"), filled_at=exit_fill_time,
        )
        self.journal._append_state(
            "order_submitted",
            {
                "action": "close_position", "symbol": "SPY",
                "client_order_id": exit_proposal.client_order_id,
                "broker_order_id": exit_order.order_id, "status": "filled",
                "filled_quantity": str(exit_order.filled_quantity),
                "filled_average_price": str(exit_order.filled_average_price),
                "filled_at": exit_order.filled_at.isoformat(),
                "planned_loss": "0",
            },
            proposal_id=exit_proposal.proposal_id,
            occurred_at=delayed,
        )
        canceled_parent = replace(
            parent, legs=(replace(stop, status="canceled"),)
        )
        closed = self.reconciler.reconcile(
            account=replace(
                self.broker.account,
                cash=entry_cash + exit_order.filled_quantity * Decimal("119"),
                non_marginable_buying_power=(
                    entry_cash + exit_order.filled_quantity * Decimal("119")
                ),
                buying_power=entry_cash + exit_order.filled_quantity * Decimal("119"),
                equity=entry_cash + exit_order.filled_quantity * Decimal("119"),
                long_market_value=Decimal("0"),
            ),
            positions=[],
            orders=[canceled_parent, exit_order],
            now=NOW + timedelta(days=3),
        )
        self.assertTrue(closed.ok, closed.issues)
        state = reduce_events(self.journal.events())
        self.assertNotIn("SPY", state.positions)
        self.assertIn(exit_fill_time.date(), state.realized_pnl_by_day)
        realized_once = state.realized_pnl_by_day[exit_fill_time.date()]
        close_events_once = len(
            [
                event for event in self.journal.events()
                if event["event_type"] == "position_closed"
            ]
        )
        repeated = self.reconciler.reconcile(
            account=replace(
                self.broker.account,
                cash=entry_cash + exit_order.filled_quantity * Decimal("119"),
                non_marginable_buying_power=(
                    entry_cash + exit_order.filled_quantity * Decimal("119")
                ),
                buying_power=entry_cash + exit_order.filled_quantity * Decimal("119"),
                equity=entry_cash + exit_order.filled_quantity * Decimal("119"),
                long_market_value=Decimal("0"),
            ),
            positions=[],
            orders=[canceled_parent, exit_order],
            now=NOW + timedelta(days=4),
        )
        self.assertTrue(repeated.ok, repeated.issues)
        repeated_state = reduce_events(self.journal.events())
        self.assertEqual(
            repeated_state.realized_pnl_by_day[exit_fill_time.date()], realized_once
        )
        self.assertEqual(
            len(
                [
                    event for event in self.journal.events()
                    if event["event_type"] == "position_closed"
                ]
            ),
            close_events_once,
        )


if __name__ == "__main__":
    unittest.main()
