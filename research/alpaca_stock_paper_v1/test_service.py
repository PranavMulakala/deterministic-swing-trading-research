from datetime import datetime, timezone
import unittest

from research.alpaca_stock_paper_v1.outbox import connect
from research.alpaca_stock_paper_v1.alerts import Draft
from research.alpaca_stock_paper_v1.outbox import enqueue
from datetime import timedelta
from research.alpaca_stock_paper_v1.read_only import PaperReader, URLS
from research.alpaca_stock_paper_v1.service import run_once

NOW = datetime(2026, 9, 23, 14, 30, tzinfo=timezone.utc)


class ServiceTests(unittest.TestCase):
    def test_empty_account_does_not_email(self):
        values = {
            URLS["account"]: {"id": "paper-1", "status": "ACTIVE", "cash": "7500"},
            URLS["positions"]: [], URLS["open_orders"]: [],
            URLS["clock"]: {"is_open": True, "timestamp": NOW.isoformat()},
        }
        reader = PaperReader(values.__getitem__, clock=lambda: NOW)
        db = connect(":memory:")
        seen = []
        result = run_once(reader, expected_account_id="paper-1", card=None, now=NOW,
                          outbox_db=db, delivery=lambda *parts: seen.append(parts))
        self.assertEqual((result.status, result.drafted, result.accepted_by_provider),
                         ("no_paper_position", 0, 0))
        self.assertEqual(seen, [])

    def test_broker_failure_enqueues_without_default_delivery(self):
        reader = PaperReader(lambda _: (_ for _ in ()).throw(RuntimeError("secret")),
                             clock=lambda: NOW)
        db = connect(":memory:")
        result = run_once(reader, expected_account_id="paper-1", card=None, now=NOW,
                          outbox_db=db)
        self.assertEqual((result.status, result.drafted, result.accepted_by_provider),
                         ("read_blocked", 1, 0))
        body, state = db.execute("SELECT body,state FROM stock_alert_outbox").fetchone()
        self.assertNotIn("secret", body)
        self.assertEqual(state, "pending")

    def test_explicit_fake_transport_accepts_once(self):
        reader = PaperReader(lambda _: (_ for _ in ()).throw(RuntimeError("read failed")),
                             clock=lambda: NOW)
        db = connect(":memory:")
        keys = []

        def fake_delivery(subject, body, key):
            keys.append(key)
            return "fake-receipt"

        first = run_once(reader, expected_account_id="paper-1", card=None, now=NOW,
                         outbox_db=db, delivery=fake_delivery)
        second = run_once(reader, expected_account_id="paper-1", card=None, now=NOW,
                          outbox_db=db, delivery=fake_delivery)
        self.assertEqual((first.accepted_by_provider, second.accepted_by_provider), (1, 0))
        self.assertEqual(len(keys), 1)

    def test_pending_message_dispatches_after_position_is_gone(self):
        values = {
            URLS["account"]: {"id": "paper-1", "status": "ACTIVE", "cash": "7500"},
            URLS["positions"]: [], URLS["open_orders"]: [],
            URLS["clock"]: {"is_open": True, "timestamp": NOW.isoformat()},
        }
        reader = PaperReader(values.__getitem__, clock=lambda: NOW)
        db = connect(":memory:")
        enqueue(db, Draft("old-key", "[PAPER STOCK] Earlier alert", "Review", "normal"),
                NOW - timedelta(minutes=5), NOW + timedelta(hours=1))
        sent = []
        result = run_once(reader, expected_account_id="paper-1", card=None, now=NOW,
                          outbox_db=db, delivery=lambda *args: sent.append(args) or "fake-id")
        self.assertEqual((result.drafted, result.accepted_by_provider), (0, 1))
        self.assertEqual(len(sent), 1)

    def test_delivery_failure_and_expiry_remain_visible(self):
        reader = PaperReader(lambda _: (_ for _ in ()).throw(RuntimeError("read failed")),
                             clock=lambda: NOW)
        db = connect(":memory:")

        def failed_mail(*_):
            raise TimeoutError("email provider unavailable")

        first = run_once(reader, expected_account_id="paper-1", card=None, now=NOW,
                         outbox_db=db, delivery=failed_mail)
        self.assertEqual((first.pending_delivery, first.expired_unsent), (1, 0))
        later = run_once(reader, expected_account_id="paper-1", card=None,
                         now=NOW + timedelta(minutes=31), outbox_db=db,
                         delivery=failed_mail)
        self.assertEqual((later.pending_delivery, later.expired_unsent), (0, 1))


if __name__ == "__main__":
    unittest.main()
