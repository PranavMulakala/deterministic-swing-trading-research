"""Offline tests for test #18 (the fence bar) on hand-built 5-minute bars."""
import unittest

from research.fence_bar_test_v1.backtest import day_trade, simulate


def bar(m, o, h, l, c):
    return {"m": m, "o": o, "h": h, "l": l, "c": c}


RISING = [90.0 + 0.1 * k for k in range(25)]          # earlier closes: the 20-bar average is rising
FALLING = [110.0 - 0.1 * k for k in range(25)]
FENCE = bar(570, 100, 101, 99, 100.5)                 # high 101, low 99, midpoint 100


class FenceBarTest(unittest.TestCase):
    def test_valid_long_hits_2r_target(self):
        day = [FENCE, bar(575, 100.5, 101.6, 100.4, 101.5),       # breakout: closes above 101
               bar(580, 101.4, 101.6, 100.9, 101.3),              # retest: opens above, dips to 100.9, closes above
               bar(585, 101.3, 104.0, 101.2, 103.8)]              # reaches the target 101.3 + 2 x 1.3 = 103.9
        t = day_trade(day, RISING)
        self.assertEqual((t["entry_m"], t["entry"], t["stop"]), (580, 101.3, 100.0))
        self.assertAlmostEqual(t["target"], 103.9)
        self.assertEqual((t["reason"], t["exit"]), ("target", t["target"]))

    def test_breakout_bar_is_not_itself_a_retest(self):
        day = [FENCE, bar(575, 100.5, 101.6, 100.4, 101.5), bar(580, 101.5, 102.0, 101.4, 101.9)]
        self.assertIsNone(day_trade(day, RISING))                 # no bar came back to the fence

    def test_close_back_inside_cancels(self):
        day = [FENCE, bar(575, 100.5, 101.6, 100.4, 101.5),       # breakout
               bar(580, 101.5, 101.6, 100.5, 100.8),              # closes back inside: disarmed
               bar(585, 101.2, 101.4, 100.9, 101.3)]              # looks like a retest, but no new breakout
        self.assertIsNone(day_trade(day, RISING))

    def test_retest_after_1055_is_skipped(self):
        day = [FENCE, bar(650, 100.5, 101.6, 100.4, 101.5), bar(660, 101.4, 101.6, 100.9, 101.3)]
        self.assertIsNone(day_trade(day, RISING))
        self.assertIsNotNone(day_trade(day, RISING, last_entry=895))

    def test_falling_anchor_line_skips(self):
        day = [FENCE, bar(575, 100.5, 101.6, 100.4, 101.5), bar(580, 101.4, 101.6, 100.9, 101.3)]
        self.assertIsNone(day_trade(day, FALLING))
        self.assertIsNotNone(day_trade(day, FALLING, use_filter=False))

    def test_same_bar_touch_assumes_stop(self):
        day = [FENCE, bar(575, 100.5, 101.6, 100.4, 101.5), bar(580, 101.4, 101.6, 100.9, 101.3),
               bar(585, 101.3, 104.0, 99.9, 101.0)]               # touches both 100.0 and 103.9
        self.assertEqual(day_trade(day, RISING)["reason"], "stop_same_bar")
        self.assertEqual(day_trade(day, RISING, same_bar="target")["reason"], "target_same_bar")

    def test_exit_at_close_when_nothing_hits(self):
        day = [FENCE, bar(575, 100.5, 101.6, 100.4, 101.5), bar(580, 101.4, 101.6, 100.9, 101.3),
               bar(955, 101.3, 101.8, 100.6, 101.7)]
        t = day_trade(day, RISING)
        self.assertEqual((t["reason"], t["exit"]), ("close", 101.7))

    def test_short_side_is_the_mirror(self):
        hist = [{"m": 955, "o": 110 - 0.1 * k, "h": 110 - 0.1 * k, "l": 110 - 0.1 * k, "c": 110 - 0.1 * k} for k in range(25)]
        day = [FENCE, bar(575, 99.5, 99.6, 98.4, 98.5),          # breakdown: closes below 99
               bar(580, 98.6, 99.1, 98.4, 98.7),                  # retest from below: opens below, back to 99.1, closes below
               bar(585, 98.7, 98.8, 96.0, 96.2)]                  # target 98.7 - 2 x 1.3 = 96.1
        days = {"2020-01-02": hist, "2020-01-03": day}
        trades, _ = simulate(days, "short", ("2020-01-03", "2020-01-03"), slip=0.0)
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual((t["side"], t["entry"], t["stop"], t["reason"]), ("short", 98.7, 100.0, "target"))
        self.assertAlmostEqual(t["target"], 96.1)
        self.assertGreater(t["pnl"], 0)


if __name__ == "__main__":
    unittest.main()
