"""Offline tests for the 50-day SMA backtest on made-up prices (plan check 1). A 3-day SMA keeps the hand math short."""
import unittest

from research.sma50_test_v1 import backtest as bt


def bars(opens, closes):
    return {"date": [f"2020-01-{i + 1:02d}" for i in range(len(closes))], "open": opens, "close": closes}


# 3-day SMA: day2 10.00 (tie), day3 10.67, day4 11.67, day5 11.33, day6 10.00, day7 9.33
HAND = bars([10, 10, 10, 11, 12.5, 10, 8.5, 10.5], [10, 10, 10, 12, 13, 9, 8, 11])


class RuleTests(unittest.TestCase):
    def test_hand_worked_example(self):
        # tie on day 2 -> nothing; close above on day 3 -> buy day 4 open 12.5;
        # close below on day 5 -> sell day 6 open 8.5; close above on day 7 is the last day, so no fill
        self.assertEqual(bt.signals(HAND["close"], 3), [0, 0, 0, 1, 1, -1, -1, 1])
        trades, curve = bt.simulate(HAND, length=3)
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual((t["entry_date"], t["entry_price"], t["exit_date"], t["exit_price"]),
                         ("2020-01-05", 12.5, "2020-01-07", 8.5))
        expected = 100_000 * 8.5 * 0.999 / (12.5 * 1.001)
        self.assertAlmostEqual(t["pnl"], expected - 100_000, places=6)
        self.assertAlmostEqual(curve[-1][1], expected, places=6)
        self.assertEqual([h for *_, h in curve], [False, True, True, False, False])
        self.assertAlmostEqual(curve[1][1], 100_000 / (12.5 * 1.001) * 13, places=6)  # marked at the close

    def test_never_above_means_no_trades(self):
        closes = [20 - 0.5 * i for i in range(30)]
        trades, curve = bt.simulate(bars(closes, closes), length=3)
        self.assertEqual(trades, [])
        self.assertEqual(curve[-1][1], 100_000)

    def test_always_above_matches_buy_and_hold(self):
        closes = [10 + i for i in range(30)]
        opens = [c - 0.5 for c in closes]
        b = bars(opens, closes)
        trades, curve = bt.simulate(b, length=3)
        self.assertEqual(len(trades), 1)
        self.assertTrue(trades[0]["open_at_end"])
        self.assertAlmostEqual(curve[-1][1], bt.buy_hold(b, first=3)[-1][1], places=6)

    def test_close_equal_to_sma_keeps_the_position(self):
        closes = [10, 10, 10, 13, 11.5, 12.5, 12]  # days 4 and 6 close exactly on the SMA (11.5 and 12) -> no change
        trades, curve = bt.simulate(bars(closes, closes), length=3)
        self.assertEqual(bt.signals(closes, 3), [0, 0, 0, 1, 0, 1, 0])
        self.assertTrue(all(h for *_, h in curve[1:]))

    def test_two_calculations_agree(self):
        for b in (HAND, bars([10 + (i % 7) for i in range(60)], [10 + ((i * 3) % 11) for i in range(60)])):
            _, curve = bt.simulate(b, length=3)
            self.assertAlmostEqual(curve[-1][1], bt.replay(b, length=3), places=6)


if __name__ == "__main__":
    unittest.main()
