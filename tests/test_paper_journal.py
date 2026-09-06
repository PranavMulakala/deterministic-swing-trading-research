from datetime import timedelta
import os
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swingbot.paper_journal import JournalError, PaperJournal
from swingbot.paper_models import OrderProposal

from paper_fixtures import NOW, sample_proposal


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

    def test_exact_approval_is_one_use(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            proposal = sample_proposal()
            journal.record_proposal(proposal)
            journal.record_review(
                proposal,
                quote_timestamp=NOW,
                bid="119.9",
                ask="120.1",
                reviewed_at=NOW,
            )
            with self.assertRaises(JournalError):
                journal.approve_and_consume(
                    proposal, "WRONG", session_id="session", now=NOW
                )
            with self.assertRaises(JournalError):
                journal.approve_and_consume(
                    proposal, proposal.confirmation_code, session_id="", now=NOW
                )
            with self.assertRaises(JournalError):
                journal.approve_and_consume(
                    proposal, proposal.confirmation_code,
                    session_id="session", now=proposal.created_at - timedelta(seconds=1),
                )
            permit = journal.approve_and_consume(
                proposal, proposal.confirmation_code, session_id="session", now=NOW
            )
            self.assertTrue(journal.claim_permit(proposal, permit, "submit_order"))
            self.assertFalse(journal.claim_permit(proposal, permit, "submit_order"))
            with self.assertRaises(JournalError):
                journal.approve_and_consume(
                    proposal, proposal.confirmation_code, session_id="session", now=NOW
                )

    def test_approval_without_recorded_full_review_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaperJournal(Path(directory) / "journal.sqlite")
            proposal = sample_proposal()
            journal.record_proposal(proposal)
            with self.assertRaisesRegex(JournalError, "full-order review"):
                journal.approve_and_consume(
                    proposal, proposal.confirmation_code,
                    session_id="session", now=NOW,
                )


if __name__ == "__main__":
    unittest.main()
