"""Offline tests for the forward watch."""
import unittest

from research.forward_watch_v1.watch import evaluate, render, stock_result


SPY = [("2026-10-05", 100, 101, 99, 100), ("2026-10-06", 100, 102, 99, 101), ("2026-10-07", 101, 103, 100, 102)]


class WatchTest(unittest.TestCase):
    def test_stop_target_and_gaps(self):
        idea = {"added": "2026-10-05", "stop": 95.0, "target": 110.0}
        bars = [("2026-10-05", 100, 100, 100, 100), ("2026-10-06", 112, 113, 111, 112)]
        self.assertEqual(stock_result(bars, idea, 100.0), (1.12, "target hit (gap) 2026-10-06 at 112.00"))
        bars = [("2026-10-05", 100, 100, 100, 100), ("2026-10-06", 100, 111, 94, 100)]
        self.assertEqual(stock_result(bars, idea, 100.0)[1], "stopped 2026-10-06 at 95.00")     # both in a day: stop
        bars = [("2026-10-05", 100, 100, 100, 100), ("2026-10-06", 100, 104, 98, 103)]
        self.assertEqual(stock_result(bars, idea, 100.0), (1.03, "open"))

    def test_basket_option_and_spy_twin(self):
        ideas = [{"name": "b", "source": "s", "added": "2026-10-05", "entry_at": "close", "kind": "basket", "symbols": ["A", "B"]},
                 {"name": "o", "source": "s", "added": "2026-10-06", "kind": "option", "symbol": "OPT", "underlying": "SPY",
                  "strike": 101.5, "expires": "2026-10-07", "entry": 2.0}]
        bars = {"A": [("2026-10-05", 10, 10, 10, 10), ("2026-10-07", 11, 11, 11, 11)],
                "B": [("2026-10-05", 20, 20, 20, 20), ("2026-10-07", 19, 19, 19, 19)], "SPY": SPY}
        rows, totals = evaluate(ideas, bars, SPY, {"OPT": [("2026-10-06", 2.5)]}, "2026-10-07")
        self.assertAlmostEqual(rows[0]["profit"], 10_000 * ((1.1 + 0.95) / 2 - 1))
        self.assertAlmostEqual(rows[0]["spy_profit"], 10_000 * (102 / 100 - 1))
        self.assertAlmostEqual(rows[1]["profit"], 10_000 * (0.5 / 2.0 - 1))             # expired: 102 - 101.5 = 0.50
        self.assertEqual((totals["ideas"], totals["in_profit"]), (2, 1))
        body = render(rows, totals, "2026-10-07")                                       # owner: no SPY lines in the email
        self.assertNotIn("vs SPY", body)
        self.assertNotIn("in SPY", body)
        self.assertNotIn("Beating SPY", body)
        self.assertIn("Making money: 1 of 2.", body)


if __name__ == "__main__":
    unittest.main()
