"""Offline tests for test #15 on hand-built 30-minute bars."""
import unittest

from research.dip_many_test_v1.backtest import exit_price, per_stock_trades, signal


def b(m, o, h, l, c):
    return {"m": m, "o": o, "h": h, "l": l, "c": c}


class DipRuleTest(unittest.TestCase):
    def test_signal_needs_1pct_dip_and_close_below_open(self):
        self.assertIsNotNone(signal([b(570, 100, 100.2, 98.9, 99.5)]))
        self.assertIsNone(signal([b(570, 100, 100.2, 99.2, 99.5)]))   # dip only 0.8%
        self.assertIsNone(signal([b(570, 100, 100.2, 98.5, 100.1)]))  # back above the open by 10:00

    def test_same_day_exit_uses_only_bars_after_10(self):
        day = [b(570, 100, 102.5, 98.9, 99.5), b(600, 99.5, 101.6, 99.4, 101.0)]
        entry = 99.5 * 1.001
        self.assertAlmostEqual(exit_price(day, entry * 1.02, True), entry * 1.02)
        self.assertIsNone(exit_price(day[:1], entry * 1.02, True))   # the 9:30 bar's high doesn't count

    def test_gap_up_fills_at_open_and_stuck_to_end(self):
        self.assertEqual(exit_price([b(570, 105, 106, 104, 105)], 101.5, False), 105)
        days = {"2022-01-03": [b(570, 100, 100, 98, 99), b(600, 99, 99.5, 97, 97)],
                "2022-01-04": [b(570, 96, 97, 95, 96)]}
        tr = per_stock_trades(days)
        self.assertEqual(len(tr), 1)
        self.assertTrue(tr[0]["open"])
        self.assertEqual(tr[0]["exit"], 96)


if __name__ == "__main__":
    unittest.main()
