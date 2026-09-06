"""Counterexamples from the 35b570c audit and follow-up review; all brokers are offline."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import io
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from swingbot.alpaca_paper import AlpacaPaperClient, AlpacaPaperError, _GuardedHTTPSConnection
from swingbot.config import load_config
from swingbot.paper_config import load_paper_config
from swingbot.paper_dashboard import write_paper_dashboard
from swingbot.paper_journal import JournalError, PaperJournal
from swingbot.paper_models import PaperPosition
from swingbot.paper_state import reduce_events
from swingbot.paper_workflow import PaperWorkflow

from paper_fixtures import FakeBroker, NOW, sample_permit, sample_proposal


ROOT = Path(__file__).parents[1]
ENABLED = {"SWINGBOT_PAPER_EXECUTION": "I_UNDERSTAND_PAPER_ONLY", "SWINGBOT_KILL_SWITCH": "0"}


def _append_worker(path, start, worker):
    journal = PaperJournal(path)
    if not start.wait(5):
        raise RuntimeError("writer start timed out")
    for index in range(8):
        journal.append("test_writer", {"worker": worker, "index": index}, occurred_at=NOW)


class DeadlineRegressionTests(unittest.TestCase):
    def test_json_serialization_cannot_outlive_permit(self):
        proposal = sample_proposal()
        permit = sample_permit(proposal)
        current = [NOW]
        calls, claims = [], []
        client = AlpacaPaperClient(
            "synthetic-key", "synthetic-secret", transport=lambda *args: calls.append(args),
            permit_validator=lambda *args: claims.append(args) or True,
            utc_now=lambda: current[0],
        )
        original = json.dumps

        def slow_json(value, *args, **kwargs):
            if isinstance(value, dict) and "stop_loss" in value:
                current[0] = permit.mutation_deadline
            return original(value, *args, **kwargs)

        with patch("swingbot.alpaca_paper.json.dumps", side_effect=slow_json):
            with self.assertRaises(AlpacaPaperError):
                client.submit_entry(proposal, permit)
        self.assertEqual(calls, [])
        self.assertEqual(claims, [])

    def test_real_urllib_handler_guards_after_tls_and_between_header_and_body(self):
        proposal = sample_proposal()
        permit = sample_permit(proposal)
        for delay in ("connect", "headers", "none"):
            with self.subTest(delay=delay):
                elapsed, writes, claims = [0.0], [], []
                response = json.dumps({
                    "id": "order", "client_order_id": proposal.client_order_id, "symbol": "SPY",
                    "side": "buy", "type": "market", "time_in_force": "gtc", "order_class": "oto",
                    "status": "new", "qty": "1", "filled_qty": "0", "legs": [],
                }).encode()

                class Socket:
                    def sendall(self, data):
                        writes.append(data)
                        if delay == "headers":
                            elapsed[0] = 120

                    def makefile(self, *_args, **_kwargs):
                        return io.BytesIO(
                            b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(response)).encode()
                            + b"\r\nConnection: close\r\n\r\n" + response
                        )

                    def close(self):
                        pass

                def connect(connection):
                    connection.sock = Socket()
                    if delay == "connect":
                        elapsed[0] = 120

                client = AlpacaPaperClient(
                    "synthetic-key", "synthetic-secret",
                    permit_validator=lambda *args: claims.append(args) or True,
                    utc_now=lambda: NOW, monotonic=lambda: elapsed[0],
                )
                client._clock_anchor = (NOW, 0)
                with patch.object(_GuardedHTTPSConnection, "connect", connect):
                    if delay == "none":
                        self.assertEqual(client.submit_entry(proposal, permit).order_id, "order")
                    else:
                        with self.assertRaisesRegex(AlpacaPaperError, "expired before transport"):
                            client.submit_entry(proposal, permit)
                self.assertEqual(len(claims), 1)
                self.assertEqual(len(writes), {"connect": 0, "headers": 1, "none": 2}[delay])

    def test_local_and_broker_clock_regressions_cannot_extend_deadline(self):
        elapsed, broker_time = [0.0], [NOW]
        client = AlpacaPaperClient(
            "synthetic-key", "synthetic-secret", utc_now=lambda: NOW - timedelta(days=1),
            monotonic=lambda: elapsed[0],
            transport=lambda *_: {
                "timestamp": broker_time[0].isoformat(), "is_open": True,
                "next_open": (NOW + timedelta(days=1)).isoformat(),
                "next_close": (NOW + timedelta(hours=6)).isoformat(),
            },
        )
        client.get_clock()
        elapsed[0] = 118
        broker_time[0] -= timedelta(seconds=30)
        client.get_clock()
        with self.assertRaisesRegex(AlpacaPaperError, "expired before transport"):
            client._require_transport_window(sample_permit(sample_proposal()))


class WorkflowRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.strategy = load_config(ROOT / "config/strategy_v1.json")
        self.paper = load_paper_config(ROOT / "config/paper_v1.json", ROOT / "config/strategy_v1.json")

    def prepared(self, name):
        journal = PaperJournal(Path(self.temporary.name) / (name + ".sqlite"))
        broker = FakeBroker()
        broker.permit_validator = journal.claim_permit
        workflow = PaperWorkflow(broker, journal, self.strategy, self.paper)
        workflow.bind_clean_account(now=NOW)
        proposal = workflow.propose_entry("SPY")
        review = workflow.review(proposal.proposal_id)
        return journal, broker, workflow, proposal, review

    def execute(self, workflow, proposal, review):
        return workflow.execute(proposal.proposal_id, review["confirmation_code"], session_id="test", environment=ENABLED)

    def test_working_child_fill_evidence_is_rejected_and_latched(self):
        variants = [
            {"filled_quantity": Decimal("0.5"), "filled_average_price": Decimal("110"), "filled_at": NOW},
            {"filled_at": NOW + timedelta(days=1)}, {"filled_average_price": Decimal("110")},
            {"filled_quantity": Decimal("NaN")}, {"order_id": ""},
        ]
        for status in ("new", "held"):
            for index, fields in enumerate(variants):
                with self.subTest(status=status, fields=fields):
                    journal, broker, workflow, proposal, review = self.prepared(f"{status}-{index}")
                    original = broker.get_order

                    def invalid(order_id):
                        parent = original(order_id)
                        return replace(parent, legs=(replace(parent.legs[0], status=status, **fields),))

                    broker.get_order = invalid
                    with self.assertRaises(Exception):
                        self.execute(workflow, proposal, review)
                    self.assertTrue(journal.kill_switch_latched())
                    self.assertFalse(reduce_events(journal.events()).positions)

    def test_reconciliation_rejects_later_working_child_partial_fill_evidence(self):
        journal, broker, workflow, proposal, review = self.prepared(
            "later-child-partial-fill"
        )
        parent = self.execute(workflow, proposal, review)
        child = replace(
            parent.legs[0],
            status="new",
            filled_quantity=Decimal("0.5"),
            filled_average_price=proposal.ask,
            filled_at=NOW,
        )
        broker.orders = [
            replace(
                parent,
                status="filled",
                filled_quantity=proposal.quantity,
                filled_average_price=proposal.ask,
                filled_at=NOW,
                legs=(child,),
            )
        ]
        market_value = proposal.quantity * proposal.ask
        broker.positions = [
            PaperPosition(
                "SPY",
                proposal.quantity,
                "long",
                proposal.ask,
                proposal.ask,
                market_value,
            )
        ]
        remaining_cash = Decimal("500") - market_value
        broker.account = replace(
            broker.account,
            cash=remaining_cash,
            non_marginable_buying_power=remaining_cash,
            buying_power=remaining_cash,
            long_market_value=market_value,
        )

        result = workflow.reconcile_now()

        self.assertFalse(result.ok)
        self.assertIn(
            "invalid_order_fill_state:stop-1:inconsistent_partial_fill_evidence",
            result.issues,
        )
        self.assertTrue(journal.kill_switch_latched())


    def test_malformed_wire_read_latches_and_blocks_next_clean_execution(self):
        for field, value in (("filled_at", "bad-date"), ("qty", "bad-number"), ("symbol", None)):
            with self.subTest(field=field):
                journal, broker, workflow, proposal, review = self.prepared(field)
                payload = {
                    "id": "manual", "client_order_id": "manual", "symbol": "SPY", "side": "buy",
                    "type": "market", "time_in_force": "day", "order_class": "", "status": "new",
                    "qty": "1", "filled_qty": "0", "filled_at": None,
                }
                if value is None:
                    del payload[field]
                else:
                    payload[field] = value
                parser = AlpacaPaperClient("synthetic-key", "synthetic-secret", transport=lambda *_: [payload])
                original = broker.list_orders
                broker.list_orders = parser.list_orders
                with self.assertRaises(Exception):
                    workflow.status()
                self.assertTrue(journal.kill_switch_latched())
                broker.list_orders = original
                with self.assertRaises(Exception):
                    self.execute(workflow, proposal, review)
                self.assertEqual(broker.submitted_entries, 0)

    def test_working_parent_and_exit_cannot_report_an_average_fill_price(self):
        _journal, broker, workflow, proposal, _review = self.prepared("working-average")
        # Build legitimate fake acknowledgements without granting real authority.
        broker.permit_validator = None
        parent = broker.submit_entry(proposal, sample_permit(proposal))
        with self.assertRaisesRegex(Exception, "inconsistent fill fields"):
            workflow._validate_entry_ack(proposal, replace(parent, filled_average_price=proposal.ask), NOW)
        exit_proposal = sample_proposal(action="close_position")
        order = broker.close_position(exit_proposal, sample_permit(exit_proposal))
        with self.assertRaisesRegex(Exception, "inconsistent fill fields"):
            workflow._validate_exit_ack(exit_proposal, replace(order, filled_average_price=exit_proposal.bid), NOW)

    def test_ordinary_exit_cannot_predate_the_recorded_entry(self):
        journal, broker, workflow, proposal, review = self.prepared("backdated-exit")
        broker.entry_status = "filled"
        self.execute(workflow, proposal, review)
        value = proposal.quantity * proposal.ask
        broker.positions = [PaperPosition("SPY", proposal.quantity, "long", proposal.ask, proposal.ask, value)]
        broker.account = replace(broker.account, cash=Decimal(500)-value, non_marginable_buying_power=Decimal(500)-value,
                                 buying_power=Decimal(500)-value, long_market_value=value)
        self.assertTrue(workflow.reconcile_now().ok)
        exit_proposal = workflow.propose_exit("SPY", reason="manual_owner_exit")
        exit_review = workflow.review(exit_proposal.proposal_id)
        order = self.execute(workflow, exit_proposal, exit_review)
        filled = replace(order, status="filled", filled_quantity=proposal.quantity,
                         filled_average_price=proposal.ask, filled_at=NOW - timedelta(seconds=1))
        broker.orders = [broker.orders[0], filled]
        broker.positions = []
        broker.account = replace(broker.account, cash=Decimal(500), non_marginable_buying_power=Decimal(500),
                                 buying_power=Decimal(500), long_market_value=Decimal(0))
        result = workflow.reconcile_now()
        self.assertFalse(result.ok)
        self.assertIn("filled_exit_precedes_entry:SPY", result.issues)
        self.assertTrue(journal.kill_switch_latched())
        self.assertFalse(any(e["event_type"] == "position_closed" for e in journal.events()))

    def test_roundtrip_during_snapshot_uses_clock_after_orders(self):
        for method in ("status", "scan_entries", "reconcile_now", "clear_kill_switch"):
            with self.subTest(method=method):
                journal, broker, workflow, proposal, review = self.prepared(method)
                parent = self.execute(workflow, proposal, review)
                broker.clock = replace(broker.clock, timestamp=NOW + timedelta(seconds=3))

                def during_poll(**_kwargs):
                    child = replace(parent.legs[0], status="filled", filled_quantity=proposal.quantity,
                                    filled_average_price=proposal.ask, filled_at=NOW + timedelta(seconds=4.5))
                    broker.orders = [replace(parent, status="filled", filled_quantity=proposal.quantity,
                                             filled_average_price=proposal.ask, filled_at=NOW + timedelta(seconds=4),
                                             legs=(child,))]
                    broker.clock = replace(broker.clock, timestamp=NOW + timedelta(seconds=5))
                    return broker.orders

                broker.list_orders = during_poll
                if method == "clear_kill_switch":
                    journal._append_state("kill_switch_latched", {"reason": "test owner clear"}, occurred_at=NOW)
                    workflow.clear_kill_switch("CLEAR-PAPER-KILL-SWITCH")
                else:
                    getattr(workflow, method)()
                for _ in range(3):
                    self.assertTrue(workflow.reconcile_now().ok)
                self.assertFalse(journal.kill_switch_latched())
                state = reduce_events(journal.events())
                self.assertFalse(state.positions)
                self.assertEqual(state.realized_pnl(NOW.date()), 0)
                events = [e for e in journal.events() if e["event_type"] in {"entry_filled", "position_closed"}]
                self.assertEqual([e["event_type"] for e in events], ["entry_filled", "position_closed"])
                self.assertLess(events[0]["occurred_at"], events[1]["occurred_at"])

    def test_stop_cannot_predate_entry_already_imported_on_previous_poll(self):
        journal, broker, workflow, proposal, review = self.prepared("backdated-stop")
        parent = self.execute(workflow, proposal, review)
        parent = replace(parent, status="filled", filled_quantity=proposal.quantity,
                         filled_average_price=proposal.ask, filled_at=NOW + timedelta(seconds=4),
                         legs=(replace(parent.legs[0], status="new"),))
        value = proposal.quantity * proposal.ask
        broker.positions = [PaperPosition("SPY", proposal.quantity, "long", proposal.ask, proposal.ask, value)]
        broker.account = replace(broker.account, cash=Decimal(500)-value, non_marginable_buying_power=Decimal(500)-value,
                                 buying_power=Decimal(500)-value, long_market_value=value)
        broker.orders = [parent]
        broker.clock = replace(broker.clock, timestamp=NOW + timedelta(seconds=5))
        self.assertTrue(workflow.reconcile_now().ok)
        child = replace(parent.legs[0], status="filled", filled_quantity=proposal.quantity,
                        filled_average_price=proposal.ask, filled_at=NOW + timedelta(seconds=3))
        broker.orders = [replace(parent, legs=(child,))]
        broker.positions = []
        broker.account = replace(broker.account, cash=Decimal(500), non_marginable_buying_power=Decimal(500),
                                 buying_power=Decimal(500), long_market_value=Decimal(0))
        for _ in range(3):
            result = workflow.reconcile_now()
            self.assertFalse(result.ok)
            self.assertIn("filled_exit_precedes_entry:SPY", result.issues)
        self.assertTrue(journal.kill_switch_latched())
        self.assertFalse(any(e["event_type"] == "position_closed" for e in journal.events()))


class StorageRegressionTests(unittest.TestCase):
    def test_permit_cannot_expire_while_waiting_for_journal_checks(self):
        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            proposal = sample_proposal()
            journal.record_proposal(proposal)
            review = journal.record_review(proposal, quote_timestamp=NOW, bid="119.9", ask="120.1", reviewed_at=NOW)
            permit = journal.approve_and_consume(
                proposal, journal.confirmation_code_for_review(proposal, review),
                review_event_id=review["event_id"], session_id="test", now=NOW,
            )
            elapsed = [0]
            original = journal.verify_integrity

            def delayed():
                original()
                elapsed[0] = 120

            with patch.object(journal, "verify_integrity", side_effect=delayed), patch(
                "swingbot.paper_journal.time.monotonic", side_effect=lambda: elapsed[0]
            ):
                self.assertFalse(journal.claim_permit(proposal, permit, "submit_order", NOW))
            self.assertFalse(any(e["event_type"] == "broker_mutation_claimed" for e in journal.events()))

    def test_failure_after_atomic_publication_recovers_committed_event_once(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "journal.sqlite"
            journal = PaperJournal(path)
            journal.append("before", {}, occurred_at=NOW)
            original = os.replace

            def published_then_failed(*args, **kwargs):
                original(*args, **kwargs)
                raise OSError("injected failure after atomic rename")

            with patch("os.replace", side_effect=published_then_failed), self.assertRaises(OSError):
                journal.append("after", {}, occurred_at=NOW)
            for _ in range(3):
                reopened = PaperJournal(path)
                reopened.verify_integrity()
                self.assertEqual([e["event_type"] for e in reopened.events()], ["before", "after"])

    def test_ancestor_swap_before_sensitive_chmod_cannot_redirect_files(self):
        for operation in ("journal", "lock", "dashboard"):
            with self.subTest(operation=operation), TemporaryDirectory() as directory:
                root = Path(directory)
                parent, saved, target = root / "parent", root / "saved", root / "target"
                parent.mkdir()
                target.mkdir(mode=0o755)
                target_mode = target.stat().st_mode
                journal = PaperJournal(parent / "journal.sqlite") if operation == "lock" else None
                inode = parent.stat().st_ino
                original, swapped = os.fchmod, []

                def racing_chmod(descriptor, mode):
                    if os.fstat(descriptor).st_ino == inode and not swapped:
                        swapped.append(True)
                        parent.rename(saved)
                        parent.symlink_to(target, target_is_directory=True)
                    return original(descriptor, mode)

                with patch("os.fchmod", side_effect=racing_chmod):
                    if operation == "journal":
                        PaperJournal(parent / "journal.sqlite")
                    elif operation == "lock":
                        with journal.mutation_lock():
                            pass
                    else:
                        write_paper_dashboard({}, [], parent / "dashboard.html")
                self.assertTrue(swapped)
                self.assertEqual(list(target.iterdir()), [])
                self.assertEqual(target.stat().st_mode, target_mode)
                self.assertTrue(list(saved.iterdir()))

    def test_leaf_swap_between_check_and_open_cannot_read_or_chmod_target(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path, target = root / "journal.sqlite", root / "target"
            PaperJournal(path)
            target.write_bytes(b"unchanged")
            target.chmod(0o644)
            original, swapped = os.open, []

            def racing_open(name, flags, *args, **kwargs):
                if name == path.name and "dir_fd" in kwargs and not swapped:
                    swapped.append(True)
                    path.unlink()
                    path.symlink_to(target)
                return original(name, flags, *args, **kwargs)

            with patch("os.open", side_effect=racing_open), self.assertRaises(JournalError):
                PaperJournal(path)
            self.assertTrue(swapped)
            self.assertEqual(target.read_bytes(), b"unchanged")
            self.assertEqual(target.stat().st_mode & 0o777, 0o644)

    def test_failed_atomic_publication_preserves_previous_valid_journal(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "journal.sqlite"
            journal = PaperJournal(path)
            journal.append("before", {}, occurred_at=NOW)
            before = path.read_bytes()
            with patch("os.replace", side_effect=OSError("injected disk failure")):
                with self.assertRaises(OSError):
                    journal.append("after", {}, occurred_at=NOW)
            self.assertEqual(path.read_bytes(), before)
            reopened = PaperJournal(path)
            reopened.verify_integrity()
            self.assertEqual([e["event_type"] for e in reopened.events()], ["before"])
            self.assertFalse(list(path.parent.glob(".*.tmp")))

    def test_legacy_wal_requires_checkpoint_and_preserves_hash_chain(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "journal.sqlite"
            journal = PaperJournal(path)
            journal.append("before", {}, occurred_at=NOW)
            events = journal.events()
            connection = sqlite3.connect(path)
            try:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA wal_autocheckpoint=0")
                connection.execute("CREATE TABLE legacy_extra (id INTEGER)")
                connection.commit()
                wal = Path(str(path) + "-wal")
                before = (path.read_bytes(), wal.read_bytes())
                with self.assertRaisesRegex(JournalError, "owner-controlled checkpoint"):
                    PaperJournal(path)
                self.assertEqual((path.read_bytes(), wal.read_bytes()), before)
                connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            finally:
                connection.close()
            self.assertEqual(path.read_bytes()[18:20], b"\x02\x02")
            reopened = PaperJournal(path)
            self.assertEqual(reopened.events(), events)
            reopened.append("after", {}, occurred_at=NOW)
            reopened.verify_integrity()
            self.assertEqual(path.read_bytes()[18:20], b"\x01\x01")

    def test_competing_processes_do_not_lose_committed_events(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "journal.sqlite"
            PaperJournal(path)
            context = multiprocessing.get_context("spawn")
            start = context.Event()
            workers = [context.Process(target=_append_worker, args=(str(path), start, number)) for number in range(3)]
            try:
                for worker in workers:
                    worker.start()
                start.set()
                for worker in workers:
                    worker.join(8)
                    self.assertEqual(worker.exitcode, 0)
            finally:
                for worker in workers:
                    if worker.is_alive():
                        worker.terminate()
                    worker.join()
            journal = PaperJournal(path)
            journal.verify_integrity()
            events = journal.events()
            self.assertEqual(len(events), 24)
            self.assertEqual(len({(e["payload"]["worker"], e["payload"]["index"]) for e in events}), 24)

    def test_mutation_lock_preserves_the_protected_operation_error(self):
        from swingbot.safe_paths import UnsafePathError

        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            for original in (OSError("broker read failed"), UnsafePathError("dashboard path rejected")):
                with self.assertRaises(OSError) as caught:
                    with journal.mutation_lock():
                        raise original
                self.assertIs(caught.exception, original)
            # The descriptor and lock must still be released after the failure.
            with journal.mutation_lock():
                pass


if __name__ == "__main__":
    unittest.main()
