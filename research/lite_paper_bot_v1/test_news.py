"""Offline tests for the learning-only LITE news reading: no network, no real key."""
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from research.lite_paper_bot_v1 import bot, news

NY = news.NY


def article(stamp, lite=None, relevance="1.000000", title="Headline", source="Source"):
    rows = [{"ticker": "NVDA", "relevance_score": "0.9", "ticker_sentiment_score": "0.9"}]
    if lite is not None:
        rows.append({"ticker": "LITE", "relevance_score": relevance, "ticker_sentiment_score": lite})
    return {"time_published": stamp, "title": title, "source": source, "ticker_sentiment": rows}


# Trimmed from Alpha Vantage's real LITE feed for Thu Sep 24 16:00 to Mon Sep 28 14:00, 2026.
SEPT_28 = [article("20260928T102210", "0.465973", title="Citigroup raises Lumentum target to $1,400"),
           article("20260926T022318", "-0.186609", "0.973337", "President sells $928k in stock", "Investing.com"),
           article("20260926T022317", "-0.413261", title="Insider sells as stock trades far above GF Value"),
           article("20260926T012318", "0.143370", title="Insider sells 500 shares"),
           article("20260926T012317", "-0.240702", title="Two share sales followed a trading plan"),
           article("20260926T012208", "0.005333", title="Form 4 filing"),
           article("20260925T212208", "0.122501", title="Stock price page"),
           article("20260925T085228", "0.456576", title="LITE has run 450% in 12 months")]


class Reply:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return json.dumps(self.payload).encode()


class Opener:
    def __init__(self, payload):
        self.payload, self.urls = payload, []

    def open(self, request, timeout):
        self.urls.append(request.full_url)
        return Reply(self.payload)


class NewsTests(unittest.TestCase):
    def test_window_runs_from_the_previous_weekday_close_to_ten(self):
        self.assertEqual(news.window(datetime(2026, 9, 28, 10, 5, tzinfo=NY)),  # Monday: from Friday's close
                         (datetime(2026, 9, 25, 16, tzinfo=NY), datetime(2026, 9, 28, 10, tzinfo=NY)))
        self.assertEqual(news.window(datetime(2026, 9, 29, 9, 40, tzinfo=NY)),  # before 10:00: up to now
                         (datetime(2026, 9, 28, 16, tzinfo=NY), datetime(2026, 9, 29, 9, 40, tzinfo=NY)))

    def test_real_monday_feed_keeps_only_news_published_before_the_decision(self):
        start, end = news.window(datetime(2026, 9, 28, 10, 5, tzinfo=NY))
        result = news.score(SEPT_28, start, end)  # drops the 10:22 Citi note and Friday-morning story
        self.assertEqual((result["articles"], result["score"], result["label"]), (6, "-0.094", "Neutral"))
        self.assertEqual(result["top"][0], "Sat 02:23 -0.41 Source: Insider sells as stock trades far above GF Value")

    def test_score_is_relevance_weighted_and_ignores_other_tickers(self):
        start, end = news.window(datetime(2026, 9, 29, 10, 1, tzinfo=NY))
        feed = [article("20260929T062210", "0.40"), article("20260928T200000", "-0.20", "0.5"), article("20260929T070000")]
        self.assertEqual((news.score(feed, start, end)["score"], news.score(feed, start, end)["label"]),
                         ("0.200", "Somewhat-Bullish"))
        self.assertEqual(news.score([], start, end), {"articles": 0})

    def test_labels_follow_alpha_vantage_cutoffs(self):
        self.assertEqual([news.label(Decimal(x)) for x in ("-0.35", "-0.15", "0", "0.15", "0.35")],
                         ["Bearish", "Somewhat-Bearish", "Neutral", "Somewhat-Bullish", "Bullish"])

    def test_missing_key_refusals_and_loose_permissions_never_raise_or_reveal_the_key(self):
        now = datetime(2026, 9, 29, 10, 6, tzinfo=NY)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env.news"
            self.assertIn("not set up", news.reading(now, path)["error"])
            path.write_text("ALPHAVANTAGE_API_KEY=\n")
            path.chmod(0o600)
            self.assertIn("not set up", news.reading(now, path)["error"])
            path.write_text("ALPHAVANTAGE_API_KEY=secret123\n")
            opener = Opener({"Information": "Our standard API rate limit is 25 requests per day."})
            record = news.reading(now, path, opener)
            self.assertIn("refused", record["error"])
            self.assertNotIn("secret123", json.dumps(record))
            self.assertIn("time_from=20260928T1600&time_to=20260929T1000", opener.urls[0])
            ok = news.reading(now, path, Opener({"feed": [article("20260929T063000", "-0.5")]}))
            self.assertEqual((ok["articles"], ok["label"]), (1, "Bearish"))
            path.chmod(0o644)
            self.assertIn("PermissionError", news.reading(now, path)["error"])

    def test_email_shows_the_reading_without_changing_the_headline(self):
        record = {"type": news.EVENT, "window_et": "Mon 16:00 to Tue 10:00", "articles": 2, "score": "0.200",
                  "label": "Somewhat-Bullish", "top": ["Tue 06:22 +0.40 Source: Headline"]}
        headline, body = bot.summary([{"type": "NO_SIGNAL", "at": "x"}], "Holding: nothing (flat).", record)
        self.assertEqual(headline, "No Signal")
        self.assertIn("2 LITE articles; relevance-weighted sentiment 0.200 (Somewhat-Bullish).", body)
        self.assertIn("  - Tue 06:22 +0.40 Source: Headline", body)
        self.assertLess(body.index("Holding:"), body.index("News (learning only"))
        self.assertEqual(bot.summary([{"type": "SIGNAL"}], "Holding: nothing (flat).")[0], "Signal")


if __name__ == "__main__":
    unittest.main()
