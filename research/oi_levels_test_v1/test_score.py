"""Offline tests for test #12 scoring on hand-built 5-minute bars."""
import unittest

from research.oi_levels_test_v1.score import score


def bar(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


def call(kind, lo, hi, target=None, symbol="NVDA"):
    return {"type": kind, "level_low": lo, "level_high": hi, "target": target, "symbol": symbol}


class ScoreTest(unittest.TestCase):
    def test_long_if_above_success(self):
        bars = [bar(99, 100, 98.5, 99.5), bar(99.5, 100.6, 99.4, 100.4), bar(100.4, 102.1, 100.3, 102)]
        r = score(call("LONG_IF_ABOVE", 100, 100, 102), bars)
        self.assertEqual(r["status"], "success")
        self.assertAlmostEqual(r["pct"], (102 / 100.4 - 1) * 100)

    def test_long_if_above_failure_on_close_back_below(self):
        bars = [bar(99, 100.6, 98.5, 100.4), bar(100.4, 100.5, 99.0, 99.2)]
        self.assertEqual(score(call("LONG_IF_ABOVE", 100, 100, 102), bars)["status"], "failure")

    def test_same_bar_counts_as_failure(self):
        bars = [bar(99, 100.6, 98.5, 100.4), bar(100.4, 102.5, 99.0, 99.5)]
        self.assertEqual(score(call("LONG_IF_ABOVE", 100, 100, 102), bars)["status"], "failure")

    def test_default_target_and_expiry(self):
        bars = [bar(100, 100.6, 99.9, 100.5), bar(100.5, 100.9, 100.2, 100.7)]
        r = score(call("LONG_IF_ABOVE", 100, 100), bars)        # stock: target = entry * 1.01 = 101.505
        self.assertEqual(r["status"], "expired")
        r = score(call("LONG_IF_ABOVE", 100, 100, symbol="QQQ"), bars)  # index: 0.5% -> 101.0025, not reached
        self.assertEqual(r["status"], "expired")

    def test_support_bounce_entry_and_success(self):
        bars = [bar(105, 105.5, 104, 104.5), bar(104.5, 104.6, 102.9, 103.4), bar(103.4, 106.2, 103.2, 106)]
        r = score(call("SUPPORT_BOUNCE", 102, 103, 106), bars)
        self.assertEqual(r["status"], "success")
        self.assertAlmostEqual(r["pct"], (106 / 103 - 1) * 100)

    def test_support_bounce_gap_below_fills_at_open_and_fails_on_close(self):
        bars = [bar(101.5, 102.0, 101.0, 101.2)]
        r = score(call("SUPPORT_BOUNCE", 102, 103, 106), bars)
        self.assertEqual(r["status"], "failure")
        self.assertAlmostEqual(r["pct"], (101.2 / 101.5 - 1) * 100)

    def test_short_if_below_and_shift(self):
        bars = [bar(101, 101.2, 99.5, 99.8), bar(99.8, 99.9, 97.9, 98.0)]
        self.assertEqual(score(call("SHORT_IF_BELOW", 100, 100, 98), bars)["status"], "success")
        # +1.5% shift: level 101.5, target 99.47; entry 99.8 (first close below 101.5) -> still a valid trade
        self.assertEqual(score(call("SHORT_IF_BELOW", 100, 100, 98), bars, shift=0.015)["status"], "success")
        # a target the trigger close has already passed is excluded
        self.assertEqual(score(call("SHORT_IF_BELOW", 100, 100, 99.9), bars)["status"], "target_already_reached")

    def test_not_triggered(self):
        bars = [bar(99, 99.5, 98.5, 99.2)]
        self.assertEqual(score(call("LONG_IF_ABOVE", 100, 100, 102), bars)["status"], "not_triggered")


if __name__ == "__main__":
    unittest.main()
