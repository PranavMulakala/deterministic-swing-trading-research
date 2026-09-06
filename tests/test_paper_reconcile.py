from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swingbot.config import load_config
from swingbot.paper_config import load_paper_config
from swingbot.paper_journal import PaperJournal
from swingbot.paper_models import PaperOrder, PaperPosition
from swingbot.paper_reconcile import PaperReconciler

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
        self.journal.append(
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
            filled_average_price=Decimal("120.10"), legs=(stop,),
        )
        self.journal.append(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id, "broker_order_id": parent.order_id,
                "status": "filled",
                "planned_loss": str(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=NOW,
        )
        self.assertFalse(any(event["event_type"] == "entry_filled" for event in self.journal.events()))
        broker_position = PaperPosition(
            "SPY", proposal.quantity, "long", Decimal("120.10"), Decimal("120.10"), Decimal("60.05")
        )
        report = self.reconciler.reconcile(
            account=self.broker.account,
            positions=[broker_position],
            orders=[parent],
            now=NOW,
        )
        self.assertTrue(report.ok, report.issues)
        self.assertTrue(any(event["event_type"] == "entry_filled" for event in self.journal.events()))

    def test_partial_fill_and_missing_stop_both_fail_closed(self) -> None:
        proposal = sample_proposal()
        self.journal.record_proposal(proposal)
        partial = PaperOrder(
            "entry-partial", proposal.client_order_id, "SPY", "buy", "market", "gtc", "oto",
            "partially_filled", proposal.quantity, Decimal("0.5"),
            filled_average_price=Decimal("120"), legs=(),
        )
        self.journal.append(
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
            journal.append("account_bound", {"account_id": ACCOUNT_ID}, occurred_at=NOW)
            journal.append(
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
        self.journal.append(
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
            filled_average_price=Decimal("125"), legs=(stop,),
        )
        self.journal.append(
            "order_submitted",
            {
                "action": "entry_oto", "symbol": "SPY",
                "client_order_id": proposal.client_order_id,
                "broker_order_id": parent.order_id, "status": "filled",
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
        self.journal.append(
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


if __name__ == "__main__":
    unittest.main()
