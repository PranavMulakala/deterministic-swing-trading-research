"""Offline tests for the daily chatter email (no network)."""
from datetime import date, datetime, timezone
import unittest

from research.chatter_v1 import report

WSB_SEARCH = """<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Daily Discussion Thread for October 7, 2026</title><link href="https://www.reddit.com/r/wallstreetbets/comments/b/x/"/></entry>
<entry><title>Daily Discussion Thread for October 8, 2026</title><link href="https://www.reddit.com/r/wallstreetbets/comments/a/x/"/></entry>
</feed>"""
WSB_THREAD = """<feed xmlns="http://www.w3.org/2005/Atom">
<entry><author><name>/u/mod</name></author><content type="html">the post</content></entry>
<entry><author><name>/u/one</name></author><content type="html">&lt;p&gt;Easiest dip buy ever, loaded LITE&lt;/p&gt;</content></entry>
<entry><author><name>/u/two</name></author><content type="html">&lt;p&gt;SPY red tomorrow&lt;/p&gt;</content></entry>
</feed>"""


def page(ids_times):
    return {"messages": [{"id": i, "created_at": t, "body": f"post {i} bought the dip &amp; more",
                          "user": {"username": f"u{i % 2}", "followers": 10}, "likes": {"total": i},
                          "entities": {"sentiment": {"basic": "Bullish"} if i % 2 else None}} for i, t in ids_times]}


class ChatterTest(unittest.TestCase):
    def test_window_start_skips_weekend(self):
        monday = datetime(2026, 10, 12, 20, 15, tzinfo=timezone.utc)
        self.assertEqual(report.window_start(monday).isoformat(), "2026-10-09T16:00:00-04:00")
        thursday = datetime(2026, 10, 8, 20, 15, tzinfo=timezone.utc)
        self.assertEqual(report.window_start(thursday).isoformat(), "2026-10-07T16:00:00-04:00")

    def test_classify(self):
        c = report.classify(["Loaded more LITE, gift", "sold everything", "big red day tomorrow",
                             "bounce tomorrow 🚀", "nothing here"])
        self.assertEqual((c["buying"], c["selling"], c["ahead"], c["ahead_up"], c["ahead_down"]), (1, 1, 2, 1, 1))

    def test_stocktwits_stops_at_window_and_paginates(self):
        pages = [page([(5, "2026-10-08T19:00:00Z"), (4, "2026-10-08T15:00:00Z")]),
                 page([(3, "2026-10-07T21:00:00Z"), (2, "2026-10-07T19:00:00Z")])]
        calls = []
        def get(url):
            calls.append(url)
            return pages[len(calls) - 1]
        report.time.sleep = lambda s: None
        posts = report.stocktwits("LITE", datetime(2026, 10, 7, 20, 0, tzinfo=timezone.utc), get)
        self.assertEqual([p["text"][:6] for p in posts], ["post 5", "post 4", "post 3"])
        self.assertIn("max=3", calls[1])
        self.assertEqual(len(calls), 2)
        row = report.summarize("LITE", posts)
        self.assertEqual((row["posts"], row["users"], row["bullish"], row["buying"]), (3, 2, 2, 3))
        self.assertEqual([t["user"] for t in row["top"]], ["u1", "u0"])  # one post per person, most-liked first

    def test_wsb_thread_and_comments(self):
        link = report.wsb_thread(date(2026, 10, 8), text=lambda url: WSB_SEARCH)
        self.assertEqual(link, "https://www.reddit.com/r/wallstreetbets/comments/a/x/")
        comments = report.wsb_comments(link, text=lambda url: WSB_THREAD)
        self.assertEqual([c["user"] for c in comments], ["one", "two"])
        self.assertTrue(report.WSB_WORDS.search(comments[0]["text"]))
        self.assertFalse(report.WSB_WORDS.search(comments[1]["text"]))

    def test_price_target_mentions(self):
        hits = ["Stifel raised the firm's price target on Lumentum to $1,232",
                "analysts upgraded Micron Technology Inc MU -4.87%  90 to a Buy rating"]
        misses = ["PT $1500 by friday", "the next theme will upgrade the network at rack scale"]
        self.assertTrue(all(report.TARGET.search(t) for t in hits))
        self.assertFalse(any(report.TARGET.search(t) for t in misses))
        long = "x" * 300 + " price target raised to $1,232"
        self.assertTrue(report.snippet(long, report.TARGET.search(long)).startswith("…"))

    def test_render_mentions_unavailable_reddit(self):
        row = report.summarize("LITE", [])
        body = report.render(date(2026, 10, 8), [row], {"error": "HTTPError"}, {}, {})
        self.assertIn("Not available today", body)
        self.assertIn("(no posts)", body)


if __name__ == "__main__":
    unittest.main()
