from dataclasses import replace
from datetime import timedelta
import multiprocessing
import os
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swingbot.paper_journal import JournalError, PaperJournal

from paper_fixtures import NOW, sample_proposal


def _hold_journal_lock(path: str, acquired, release) -> None:
    journal = PaperJournal(path)
    with journal.mutation_lock():
        acquired.set()
        release.wait(5)


class PaperJournalTests(unittest.TestCase):
    def test_hash_chain_detects_tampering(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "journal.sqlite"
            journal = PaperJournal(path)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(path.parent).st_mode & 0o777, 0o700)
            with journal.mutation_lock():
                lock_path = path.with_suffix(path.suffix + ".lock")
                self.assertEqual(os.stat(lock_path).st_mode & 0o777, 0o600)
            journal.append("one", {"value": 1}, occurred_at=NOW)
            journal.append("two", {"value": 2}, occurred_at=NOW + timedelta(seconds=1))
            journal.verify_integrity()
            with sqlite3.connect(path) as connection:
                connection.execute("UPDATE events SET payload_json = '{\"value\":9}' WHERE seq = 1")
            with self.assertRaises(JournalError):
                journal.verify_integrity()

    def test_mutation_lock_serializes_distinct_processes(self) -> None:
        with TemporaryDirectory() as directory:
            path = str(Path(directory) / "journal.sqlite")
            PaperJournal(path)
            context = multiprocessing.get_context("spawn")
            first_acquired = context.Event()
            first_release = context.Event()
            second_acquired = context.Event()
            second_release = context.Event()
            first = context.Process(
                target=_hold_journal_lock,
                args=(path, first_acquired, first_release),
            )
            second = context.Process(
                target=_hold_journal_lock,
                args=(path, second_acquired, second_release),
            )
            try:
                first.start()
                self.assertTrue(
                    first_acquired.wait(3), "first process never acquired lock"
                )
                second.start()
                self.assertFalse(
                    second_acquired.wait(0.25),
                    "second process entered the mutation section concurrently",
                )
                first_release.set()
                self.assertTrue(
                    second_acquired.wait(3), "second process never acquired lock"
                )
            finally:
                first_release.set()
                second_release.set()
                if first.pid is not None:
                    first.join(3)
                if second.pid is not None:
                    second.join(3)
            self.assertEqual(first.exitcode, 0)
            self.assertEqual(second.exitcode, 0)

    def test_journal_and_lock_paths_reject_symbolic_links(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.sqlite"
            PaperJournal(target)
            linked_journal = root / "linked.sqlite"
            linked_journal.symlink_to(target)
            with self.assertRaisesRegex(JournalError, "symbolic link"):
                PaperJournal(linked_journal)

            journal = PaperJournal(root / "journal.sqlite")
            lock_path = journal.path.with_suffix(journal.path.suffix + ".lock")
            lock_target = root / "lock-target"
            lock_target.write_text("unchanged", encoding="utf-8")
            lock_path.symlink_to(lock_target)
            with self.assertRaisesRegex(JournalError, "symbolic link"):
                with journal.mutation_lock():
                    self.fail("symlinked lock was acquired")
            self.assertEqual(lock_target.read_text(encoding="utf-8"), "unchanged")

    def test_journal_rejects_symlinked_ancestor_without_chmodding_target(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "actual"
            target.mkdir(mode=0o755)
            os.chmod(target, 0o755)
            alias = root / "alias"
            alias.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(JournalError, "traverse a symbolic link"):
                PaperJournal(alias / "journal.sqlite")
            self.assertEqual(os.stat(target).st_mode & 0o777, 0o755)

    def test_first_observed_equity_is_scoped_to_day_and_current_run(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            journal._append_state(
                "account_bound", {"account_id": "paper"}, occurred_at=NOW
            )
            journal._append_state(
                "account_snapshot_observed", {"equity": "500"}, occurred_at=NOW
            )
            journal._append_state(
                "account_snapshot_observed", {"equity": "490"},
                occurred_at=NOW + timedelta(minutes=1),
            )
            self.assertEqual(journal.first_observed_equity_for_day(NOW), 500)
            self.assertIsNone(
                journal.first_observed_equity_for_day(NOW + timedelta(days=1))
            )
            journal._append_state(
                "paper_run_rebaselined", {"account_id": "paper"},
                occurred_at=NOW + timedelta(minutes=2),
            )
            self.assertIsNone(journal.first_observed_equity_for_day(NOW))

    def test_exact_approval_is_one_use(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            proposal = sample_proposal()
            journal.record_proposal(proposal)
            review = journal.record_review(
                proposal,
                quote_timestamp=NOW,
                bid="119.9",
                ask="120.1",
                reviewed_at=NOW,
            )
            code = journal.confirmation_code_for_review(proposal, review)
            with self.assertRaises(JournalError):
                journal.approve_and_consume(
                    proposal, "WRONG", review_event_id=review["event_id"],
                    session_id="session", now=NOW
                )
            with self.assertRaises(JournalError):
                journal.approve_and_consume(
                    proposal, code,
                    review_event_id=review["event_id"], session_id="", now=NOW
                )
            with self.assertRaises(JournalError):
                journal.approve_and_consume(
                    proposal, code,
                    review_event_id=review["event_id"],
                    session_id="session", now=proposal.created_at - timedelta(seconds=1),
                )
            permit = journal.approve_and_consume(
                proposal, code,
                review_event_id=review["event_id"], session_id="session", now=NOW
            )
            self.assertTrue(
                journal.claim_permit(proposal, permit, "submit_order", NOW)
            )
            self.assertFalse(
                journal.claim_permit(proposal, permit, "submit_order", NOW)
            )
            with self.assertRaises(JournalError):
                journal.approve_and_consume(
                    proposal, code,
                    review_event_id=review["event_id"], session_id="session", now=NOW
                )

    def test_permit_claim_rejects_the_exact_mutation_deadline(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            proposal = sample_proposal()
            journal.record_proposal(proposal)
            review = journal.record_review(
                proposal,
                quote_timestamp=NOW,
                bid="119.9",
                ask="120.1",
                reviewed_at=NOW,
            )
            deadline = NOW + timedelta(seconds=1)
            permit = journal.approve_and_consume(
                proposal,
                journal.confirmation_code_for_review(proposal, review),
                review_event_id=review["event_id"],
                session_id="deadline-session",
                now=NOW,
                mutation_deadline=deadline,
            )
            self.assertFalse(
                journal.claim_permit(proposal, permit, "submit_order", deadline)
            )
            self.assertNotIn(
                "broker_mutation_claimed",
                journal.proposal_event_types(proposal.proposal_id),
            )

    def test_approval_without_recorded_full_review_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            proposal = sample_proposal()
            journal.record_proposal(proposal)
            with self.assertRaisesRegex(JournalError, "full-order review"):
                journal.approve_and_consume(
                    proposal, "CONFIRM-NOT-A-RECORDED-REVIEW",
                    review_event_id="missing-review",
                    session_id="session", now=NOW,
                )

    def test_approval_is_bound_to_stored_proposal_and_exact_latest_review(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            proposal = sample_proposal()
            journal.record_proposal(proposal)
            review = journal.record_review(
                proposal, quote_timestamp=NOW, bid="119.9", ask="120.1", reviewed_at=NOW
            )
            changed = replace(proposal, quantity=proposal.quantity + 1)
            code = journal.confirmation_code_for_review(proposal, review)
            with self.assertRaisesRegex(JournalError, "stored exact proposal"):
                journal.approve_and_consume(
                    changed,
                    code,
                    review_event_id=review["event_id"],
                    session_id="session",
                    now=NOW,
                )

            newer_review = journal.record_review(
                proposal,
                quote_timestamp=NOW,
                bid="119.9",
                ask="120.1",
                reviewed_at=NOW,
            )
            self.assertNotEqual(
                code, journal.confirmation_code_for_review(proposal, newer_review)
            )
            with self.assertRaisesRegex(JournalError, "newer or different"):
                journal.approve_and_consume(
                    proposal,
                    code,
                    review_event_id=review["event_id"],
                    session_id="session",
                    now=NOW,
                )

    def test_generic_events_cannot_forge_a_mutation_permit(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            proposal = sample_proposal()
            journal.record_proposal(proposal)
            with self.assertRaisesRegex(JournalError, "validated journal operation"):
                journal.append(
                    "owner_approved",
                    {
                        "content_hash": proposal.content_hash,
                        "review_event_id": "fake-review",
                        "session_id": "session",
                    },
                    proposal_id=proposal.proposal_id,
                    occurred_at=NOW,
                )
            for state_event in (
                "account_bound",
                "entry_filled",
                "kill_switch_cleared",
                "order_submitted",
                "paper_run_rebaselined",
                "position_closed",
            ):
                with self.subTest(state_event=state_event), self.assertRaisesRegex(
                    JournalError, "validated journal operation"
                ):
                    journal.append(state_event, {}, occurred_at=NOW)

            review = journal.record_review(
                proposal, quote_timestamp=NOW, bid="119.9", ask="120.1", reviewed_at=NOW
            )
            journal.approve_and_consume(
                proposal,
                journal.confirmation_code_for_review(proposal, review),
                review_event_id=review["event_id"],
                session_id="session",
                now=NOW,
            )
            with sqlite3.connect(journal.path) as connection:
                connection.execute(
                    "UPDATE approval_permits SET session_id = 'tampered'"
                )
            with self.assertRaisesRegex(JournalError, "permit content"):
                journal.verify_integrity()

    def test_exit_permit_requires_cancel_claim_and_verified_cancel_before_submit(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            proposal = sample_proposal(action="close_position")
            journal.record_proposal(proposal)
            review = journal.record_review(
                proposal, quote_timestamp=NOW, bid="119.9", ask="120.1", reviewed_at=NOW
            )
            permit = journal.approve_and_consume(
                proposal,
                journal.confirmation_code_for_review(proposal, review),
                review_event_id=review["event_id"],
                session_id="session",
                now=NOW,
            )
            self.assertFalse(
                journal.claim_permit(proposal, permit, "submit_order", NOW)
            )
            self.assertTrue(
                journal.claim_permit(
                    proposal, permit, "cancel_protective_stop", NOW
                )
            )
            self.assertFalse(
                journal.claim_permit(proposal, permit, "submit_order", NOW)
            )
            with self.assertRaisesRegex(JournalError, "not bound"):
                journal.record_protective_stop_cancellation_verified(
                    proposal, permit, stop_order_id="different-stop", verified_at=NOW
                )
            journal.record_protective_stop_cancellation_verified(
                proposal, permit, stop_order_id="stop-1", verified_at=NOW
            )
            self.assertTrue(
                journal.claim_permit(proposal, permit, "submit_order", NOW)
            )


if __name__ == "__main__":
    unittest.main()
