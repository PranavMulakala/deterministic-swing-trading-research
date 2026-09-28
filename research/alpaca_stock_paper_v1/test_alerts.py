import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from research.alpaca_stock_paper_v1.alerts import News, Position, drafts

NOW = datetime(2026, 9, 23, 14, 30, tzinfo=timezone.utc)
D = Decimal


def position():
    return Position("paper-position-1", "LITE", D("800"), D("1"), D("840"), 20)


class AlertTests(unittest.TestCase):
    def test_target_alert_is_not_an_order(self):
        first = drafts(position(), now=NOW, bid=D("841"), quote_at=NOW, quote_feed="iex")
        self.assertEqual(len(first), 1)
        self.assertIn("No order was placed", first[0].body)
        self.assertEqual(drafts(position(), now=NOW, bid=D("841"), quote_at=NOW,
                                quote_feed="iex", known_keys=frozenset({first[0].key})), ())

    def test_drawdown_is_review_only(self):
        alerts = drafts(position(), now=NOW, bid=D("715"), quote_at=NOW,
                        quote_feed="iex", drawdown_levels=(5, 10, 20))
        self.assertEqual(len(alerts), 2)
        self.assertTrue(all("no stop order" in item.body.lower() for item in alerts))

    def test_stale_quote_blocks_price_claims(self):
        alerts = drafts(position(), now=NOW, bid=D("900"), quote_at=NOW-timedelta(seconds=6),
                        quote_feed="iex", drawdown_levels=(5,))
        self.assertEqual(len(alerts), 1)
        self.assertIn("unavailable", alerts[0].subject.lower())

    def test_review_reminder_has_no_time_exit(self):
        alerts = drafts(position(), now=NOW, review_every_sessions=5, review_due=True)
        self.assertEqual(len(alerts), 1)
        self.assertIn("no automatic time exit", alerts[0].body.lower())

    def test_news_uses_receipt_and_remains_unclassified(self):
        article = News("123", "v1", "  LITE  earnings\n update  ", "Provider",
                       NOW-timedelta(minutes=2), NOW-timedelta(minutes=1), "https://example.com/story")
        alerts = drafts(position(), now=NOW, news=(article,))
        self.assertEqual(len(alerts), 1)
        self.assertIn("sentiment unclassified", alerts[0].subject.lower())
        self.assertIn("Received:", alerts[0].body)
        unsafe = News("124", "v1", "Story", "Provider", NOW-timedelta(minutes=2),
                      NOW-timedelta(minutes=1), "https://example.com/\nInjected")
        self.assertIn("No verified HTTPS link", drafts(position(), now=NOW, news=(unsafe,))[0].body)
        with self.assertRaises(ValueError):
            drafts(position(), now=NOW, news=(News("123", "v1", "x", "Provider", NOW, NOW+timedelta(seconds=1), "https://example.com"),))


if __name__ == "__main__":
    unittest.main()
