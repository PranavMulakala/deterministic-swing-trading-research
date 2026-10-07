"""Offline tests for the dollars-first scorecard."""
import unittest

from research.scorecard_v1.scorecard import scorecard, spy_curve


class ScorecardTest(unittest.TestCase):
    def test_weeks_months_and_drop(self):
        # Mon-Fri week 1 (+1,500), week 2 (-700), week 3 (+200); one month
        curve = [("2026-01-05", 100_500), ("2026-01-09", 101_500), ("2026-01-12", 101_000), ("2026-01-16", 100_800),
                 ("2026-01-20", 101_000)]
        c = scorecard(curve, 100_000)
        self.assertEqual(c["profit"], 1_000)
        self.assertEqual(c["weeks"], 3)
        self.assertEqual(c["weeks_at_or_above_1000"], 1)
        self.assertEqual(c["worst_week"], -700)
        self.assertEqual(c["best_week"], 1_500)
        self.assertEqual(c["worst_drop_dollars"], -700)
        self.assertEqual(c["longest_losing_weeks_in_a_row"], 1)
        self.assertEqual(c["worst_month"], 1_000)

    def test_spy_line_uses_the_same_money_and_dates(self):
        spy = {"2026-01-05": 100.0, "2026-01-09": 110.0}
        curve = [("2026-01-05", 50_000), ("2026-01-09", 51_000)]
        self.assertEqual(spy_curve(curve, 50_000, spy), [("2026-01-05", 50_000.0), ("2026-01-09", 55_000.0)])


if __name__ == "__main__":
    unittest.main()
