import unittest
from datetime import datetime, timedelta, timezone

from research.alpaca_stock_paper_v1.alerts import Draft
from research.alpaca_stock_paper_v1.outbox import connect, enqueue, recover_ambiguous, send_one

NOW = datetime(2026, 9, 23, 14, 30, tzinfo=timezone.utc)


class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")
        self.draft = Draft("stable-key", "[PAPER STOCK] Review LITE", "Paper only", "urgent")

    def tearDown(self):
        self.db.close()

    def test_duplicate_draft_stays_single(self):
        enqueue(self.db,self.draft,NOW,NOW+timedelta(minutes=5))
        enqueue(self.db,self.draft,NOW,NOW+timedelta(minutes=5))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM stock_alert_outbox").fetchone()[0],1)

    def test_expired_price_alert_cannot_send(self):
        enqueue(self.db,self.draft,NOW,NOW+timedelta(minutes=5))
        invoked=[]
        self.assertFalse(send_one(self.db,self.draft.key,NOW+timedelta(minutes=6),
                                  lambda *args:invoked.append(args)))
        self.assertEqual(invoked,[])
        self.assertEqual(self.db.execute("SELECT state FROM stock_alert_outbox").fetchone()[0],"expired")

    def test_delivery_uses_stable_key_and_no_duplicate(self):
        enqueue(self.db,self.draft,NOW,NOW+timedelta(minutes=5))
        calls=[]
        def fake(subject,body,key):
            calls.append((subject,body,key))
            return "fake-provider-id"
        self.assertTrue(send_one(self.db,self.draft.key,NOW,fake))
        self.assertFalse(send_one(self.db,self.draft.key,NOW,fake))
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][2],"paper-stock-stable-key")
        self.assertEqual(self.db.execute("SELECT state FROM stock_alert_outbox").fetchone()[0],"accepted")

    def test_failure_retries_same_key_before_expiry(self):
        enqueue(self.db,self.draft,NOW,NOW+timedelta(minutes=5))
        keys=[]
        def failed(subject,body,key):
            keys.append(key)
            raise RuntimeError("mock_failure")
        self.assertFalse(send_one(self.db,self.draft.key,NOW,failed))
        self.assertTrue(send_one(self.db,self.draft.key,NOW+timedelta(seconds=1),
                                 lambda subject,body,key: keys.append(key) or "accepted"))
        self.assertEqual(keys,["paper-stock-stable-key"]*2)

    def test_recover_ambiguous_after_two_minutes(self):
        enqueue(self.db,self.draft,NOW,NOW+timedelta(minutes=5))
        with self.db:
            self.db.execute("UPDATE stock_alert_outbox SET state='sending',last_attempt_at=?",
                            (NOW.isoformat(),))
        self.assertEqual(recover_ambiguous(self.db,NOW+timedelta(minutes=1)),0)
        self.assertEqual(recover_ambiguous(self.db,NOW+timedelta(minutes=3)),1)


if __name__ == "__main__":
    unittest.main()
