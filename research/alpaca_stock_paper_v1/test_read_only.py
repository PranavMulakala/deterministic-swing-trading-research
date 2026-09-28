from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import unittest

from research.alpaca_stock_paper_v1.read_only import HttpsGet, PaperReader, ReadError, URLS, calendar_url, news_page_url
from research.alpaca_stock_paper_v1.monitor import PositionCard, evaluate
from research.alpaca_stock_paper_v1.pipeline import collect

NOW = datetime(2026, 9, 23, 14, 30, tzinfo=timezone.utc)


def fixture(*, positions=None, orders=None, quote=None, news=None):
    values = {
        URLS["account"]: {"id": "paper-account-1", "status": "ACTIVE", "cash": "7500"},
        URLS["positions"]: [] if positions is None else positions,
        URLS["open_orders"]: [] if orders is None else orders,
        URLS["clock"]: {"is_open": True, "timestamp": NOW.isoformat()},
        URLS["lite_quote"]: {"quote": {"bp": "815", "ap": "815.20", "t": NOW.isoformat()}} if quote is None else quote,
        URLS["lite_news"]: {"news": [] if news is None else news},
    }
    seen = []

    def fetch(url):
        seen.append(url)
        return values[url]

    return PaperReader(fetch), values, seen


POSITION = {"asset_id": "asset-lite", "symbol": "LITE", "qty": "1",
            "avg_entry_price": "800", "side": "long"}


class ReadOnlyTests(unittest.TestCase):
    def test_empty_paper_snapshot_uses_no_data_endpoint(self):
        reader, _, seen = fixture()
        snapshot = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW, include_news=True)
        self.assertEqual(evaluate(snapshot, None, now=NOW).status, "no_paper_position")
        self.assertEqual(seen, [URLS[x] for x in ("account", "positions", "open_orders", "clock")])

    def test_wrong_account_blocks_before_further_reads(self):
        reader, _, seen = fixture(positions=[POSITION])
        with self.assertRaisesRegex(ReadError, "paper_account_mismatch"):
            reader.snapshot(expected_account_id="other", observed_at=NOW)
        self.assertEqual(seen, [URLS["account"]])

    def test_unapproved_endpoint_has_no_network(self):
        client = HttpsGet(key_id="test", secret_key="test")
        with self.assertRaisesRegex(ReadError, "unapproved_read_endpoint"):
            client("https://api.alpaca.markets/v2/account")
        with self.assertRaisesRegex(ReadError, "unapproved_read_endpoint"):
            client("https://paper-api.alpaca.markets/v2/calendar?start=2026-09-01&end=2026-09-30&date_type=TRADING&evil=1")
        self.assertIn("start=2026-09-01", calendar_url(date(2026, 9, 1), date(2026, 9, 30)))

    def test_http_transport_uses_get_and_sanitizes_failure(self):
        client = HttpsGet(key_id="fake-key", secret_key="fake-secret")
        seen = []

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self, _):
                return b'{"id":"paper-account-1"}'

        class Opener:
            def open(self, request, timeout):
                seen.append((request.get_method(), request.full_url, timeout))
                return Response()

        client._opener = Opener()
        self.assertEqual(client(URLS["account"])["id"], "paper-account-1")
        self.assertEqual(seen, [("GET", URLS["account"], 10)])

        class Broken:
            def open(self, *_args, **_kwargs):
                raise RuntimeError("fake-secret must not leak")

        client._opener = Broken()
        with self.assertRaises(ReadError) as caught:
            client(URLS["account"])
        self.assertEqual(str(caught.exception), "alpaca_read_failed")

    def test_target_is_draft_only_for_approved_matching_card(self):
        reader, _, seen = fixture(positions=[POSITION])
        snapshot = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW)
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("1"),
                            Decimal("810"), 1, False, True)
        result = evaluate(snapshot, card, now=NOW)
        self.assertEqual(result.status, "ready_for_email_drafts")
        self.assertTrue(any("target observed" in d.subject.lower() for d in result.drafts))
        self.assertTrue(any("Paper position ID: reopen-1" in d.body for d in result.drafts))
        self.assertIn(URLS["lite_quote"], seen)
        self.assertNotIn(URLS["lite_news"], seen)

    def test_unapproved_card_and_open_order_block_price_alert(self):
        reader, _, _ = fixture(positions=[POSITION], orders=[{"id": "pending-1"}])
        snap = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW)
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("1"),
                            Decimal("810"), 1, False, True)
        result = evaluate(snap, card, now=NOW)
        self.assertEqual(result.status, "open_orders_present")
        self.assertFalse(any("target observed" in d.subject.lower() for d in result.drafts))
        no_order_reader, _, _ = fixture(positions=[POSITION])
        snap = no_order_reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW)
        result = evaluate(snap, PositionCard("paper-account-1", "asset-lite", "reopen-1",
                                             Decimal("1"), Decimal("810"), 1, False), now=NOW)
        self.assertEqual(result.status, "position_mismatch")

    def test_quantity_mismatch_blocks_price_alert(self):
        reader, _, _ = fixture(positions=[POSITION])
        snap = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW)
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("2"),
                            Decimal("810"), 1, False, True)
        self.assertEqual(evaluate(snap, card, now=NOW).status, "position_mismatch")

    def test_news_requires_explicit_cutoff_and_is_unclassified(self):
        item = {"id": 123, "symbols": ["LITE"], "created_at": "2026-09-23T14:29:00Z",
                "updated_at": "2026-09-23T14:29:01Z", "headline": "Company update",
                "source": "wire", "url": "https://example.com/story"}
        reader, _, _ = fixture(positions=[POSITION], news=[item])
        cutoff = datetime(2026, 9, 23, 14, tzinfo=timezone.utc)
        snap = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW,
                               include_news=True, news_since=cutoff)
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("1"),
                            Decimal("900"), 1, False, True)
        self.assertFalse(any("news" in d.subject.lower() for d in evaluate(snap, card, now=NOW).drafts))
        result = evaluate(snap, card, now=NOW, news_since=datetime(2026, 9, 23, 14, 0, tzinfo=timezone.utc))
        self.assertTrue(any("unclassified" in d.subject.lower() for d in result.drafts))

    def test_bad_quote_and_pagination_fail_closed(self):
        reader, _, _ = fixture(positions=[POSITION], quote={"quote": {"bp": 820, "ap": 810, "t": NOW.isoformat()}})
        bad_quote = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW)
        self.assertEqual(bad_quote.quote_problem, "crossed_quote")
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("1"),
                            Decimal("810"), 1, False, True)
        warning = evaluate(bad_quote, card, now=NOW)
        self.assertTrue(any("unavailable" in d.subject.lower() for d in warning.drafts))
        self.assertFalse(any("target observed" in d.subject.lower() for d in warning.drafts))
        reader, values, _ = fixture(positions=[POSITION])
        values[URLS["lite_news"]] = {"news": [], "next_page_token": "more"}
        snap = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW,
                               include_news=True, news_since=datetime(2026, 9, 23, 14, tzinfo=timezone.utc))
        self.assertEqual(snap.news_problem, "alpaca_news_failed")
        result = evaluate(snap, card, now=NOW)
        self.assertTrue(any("news could not be verified" in d.body.lower() for d in result.drafts))
        self.assertTrue(any("target observed" in d.subject.lower() for d in result.drafts))

    def test_news_still_drafts_when_quote_endpoint_fails(self):
        article = {"id": 123, "symbols": ["LITE"], "created_at": "2026-09-23T14:29:00Z",
                   "updated_at": "2026-09-23T14:29:01Z", "headline": "Company update",
                   "source": "wire", "url": "https://example.com/story"}
        reader, values, _ = fixture(positions=[POSITION], news=[article])
        del values[URLS["lite_quote"]]
        snap = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW,
                               include_news=True, news_since=datetime(2026, 9, 23, 14, tzinfo=timezone.utc))
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("1"),
                            Decimal("900"), 1, False, True)
        result = evaluate(snap, card, now=NOW,
                          news_since=datetime(2026, 9, 23, 14, tzinfo=timezone.utc))
        self.assertTrue(any("unclassified" in d.subject.lower() for d in result.drafts))
        self.assertTrue(any("unavailable" in d.subject.lower() for d in result.drafts))

    def test_decision_time_follows_read_completion_for_news_and_quote(self):
        completed_at = NOW + timedelta(seconds=2)
        article_at = NOW + timedelta(seconds=1)
        article = {"id": 124, "symbols": ["LITE"], "created_at": article_at.isoformat(),
                   "updated_at": article_at.isoformat(), "headline": "New update",
                   "source": "wire", "url": "https://example.com/new"}
        reader, values, _ = fixture(positions=[POSITION], news=[article])
        values[URLS["lite_quote"]] = {"quote": {"bp": "815", "ap": "815.20",
                                                  "t": article_at.isoformat()}}
        reader = PaperReader(values.__getitem__, clock=lambda: completed_at)
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("1"),
                            Decimal("810"), 0, False, True)
        result = collect(reader, expected_account_id="paper-account-1", card=card,
                         now=NOW, news_since=NOW)
        self.assertEqual(result.status, "ready_for_email_drafts")
        self.assertTrue(any("target observed" in d.subject.lower() for d in result.drafts))
        self.assertTrue(any("unclassified" in d.subject.lower() for d in result.drafts))

    def test_paginated_news_reaches_cutoff_and_does_not_drop_recent_item(self):
        recent = {"id": 123, "symbols": ["LITE"], "created_at": "2026-09-23T14:29:00Z",
                  "updated_at": "2026-09-23T14:29:01Z", "headline": "Recent update",
                  "source": "wire", "url": "https://example.com/recent"}
        old = {"id": 122, "symbols": ["LITE"], "created_at": "2026-09-23T13:00:00Z",
               "updated_at": "2026-09-23T13:00:01Z", "headline": "Earlier update",
               "source": "wire", "url": "https://example.com/old"}
        reader, values, seen = fixture(positions=[POSITION])
        values[URLS["lite_news"]] = {"news": [recent], "next_page_token": "page+2"}
        values[news_page_url("page+2")] = {"news": [old], "next_page_token": "older"}
        cutoff = datetime(2026, 9, 23, 14, tzinfo=timezone.utc)
        snap = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW,
                               include_news=True, news_since=cutoff)
        self.assertIsNone(snap.news_problem)
        self.assertEqual([item.article_id for item in snap.news], ["123"])
        self.assertIn(news_page_url("page+2"), seen)

    def test_future_news_timestamp_creates_warning_instead_of_silent_drop(self):
        future = NOW + timedelta(seconds=10)
        article = {"id": 125, "symbols": ["LITE"], "created_at": future.isoformat(),
                   "updated_at": future.isoformat(), "headline": "Future dated update",
                   "source": "wire", "url": "https://example.com/future"}
        reader, _, _ = fixture(positions=[POSITION], news=[article])
        snap = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW,
                               include_news=True, news_since=NOW)
        self.assertEqual(snap.news_problem, "future_news_timestamp")
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("1"),
                            Decimal("900"), 0, False, True)
        result = evaluate(snap, card, now=NOW, news_since=NOW)
        self.assertTrue(any("news could not be verified" in d.body.lower() for d in result.drafts))
        self.assertFalse(any("Future dated update" in d.body for d in result.drafts))

    def test_stale_quote_creates_warning_not_target(self):
        old = datetime(2026, 9, 23, 14, 29, tzinfo=timezone.utc)
        reader, _, _ = fixture(positions=[POSITION], quote={"quote": {"bp": 820, "ap": 821, "t": old.isoformat()}})
        snap = reader.snapshot(expected_account_id="paper-account-1", observed_at=NOW)
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("1"),
                            Decimal("810"), 1, False, True)
        result = evaluate(snap, card, now=NOW)
        self.assertTrue(any("unavailable" in d.subject.lower() for d in result.drafts))
        self.assertFalse(any("target observed" in d.subject.lower() for d in result.drafts))

    def test_read_failure_becomes_operational_draft_without_raw_error(self):
        def bad_fetch(_):
            raise RuntimeError("SECRET_KEY_should_not_appear")
        reader = PaperReader(bad_fetch)
        result = collect(reader, expected_account_id="paper-account-1", card=None, now=NOW)
        self.assertEqual(result.status, "read_blocked")
        self.assertNotIn("SECRET_KEY", result.drafts[0].body)

    def test_five_completed_sessions_create_holding_review_from_calendar(self):
        after_close = datetime(2026, 9, 23, 21, tzinfo=timezone.utc)
        opened_at = datetime(2026, 9, 17, 14, tzinfo=timezone.utc)
        reader, values, _ = fixture(positions=[POSITION])
        values[URLS["clock"]] = {"is_open": False, "timestamp": after_close.isoformat()}
        values[URLS["lite_news"]] = {"news": []}
        values[calendar_url(date(2026, 9, 17), date(2026, 9, 23))] = [
            {"date": f"2026-09-{day:02d}", "open": "09:30", "close": "16:00"}
            for day in (17, 18, 21, 22, 23)]
        reader = PaperReader(values.__getitem__, clock=lambda: after_close)
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("1"),
                            Decimal("900"), 0, False, True, opened_at, (5, 10), 5)
        result = collect(reader, expected_account_id="paper-account-1", card=card,
                         now=after_close, news_since=opened_at)
        self.assertEqual(result.status, "ready_for_email_drafts")
        self.assertTrue(any("Holding review due" in d.subject for d in result.drafts))

    def test_missing_calendar_warns_without_fake_review(self):
        after_close = datetime(2026, 9, 23, 21, tzinfo=timezone.utc)
        opened_at = datetime(2026, 9, 17, 14, tzinfo=timezone.utc)
        reader, values, _ = fixture(positions=[POSITION])
        values[URLS["clock"]] = {"is_open": False, "timestamp": after_close.isoformat()}
        values[URLS["lite_news"]] = {"news": []}
        reader = PaperReader(values.__getitem__, clock=lambda: after_close)
        card = PositionCard("paper-account-1", "asset-lite", "reopen-1", Decimal("1"),
                            Decimal("900"), 0, False, True, opened_at, (5, 10), 5)
        result = collect(reader, expected_account_id="paper-account-1", card=card,
                         now=after_close, news_since=opened_at)
        self.assertTrue(any("calendar could not be verified" in d.body for d in result.drafts))
        self.assertFalse(any("Holding review due" in d.subject for d in result.drafts))


if __name__ == "__main__":
    unittest.main()
