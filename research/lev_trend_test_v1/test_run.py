"""Offline tests for test #14."""
import unittest

from research.lev_trend_test_v1.run import SWITCH_COST, lev_return, run_strategy, signals


class LevTrendTest(unittest.TestCase):
    def test_cost_formula(self):
        # 2x on a +1% day with 0.01% cash: 2*1% - (0.01% + 0.5%/252) - 0.9%/252
        self.assertAlmostEqual(lev_return(0.01, 0.0001, 2), 0.02 - 0.0001 - 0.005 / 252 - 0.009 / 252)
        self.assertAlmostEqual(lev_return(0.01, 0.0001, 1), 0.01)

    def test_signal_needs_full_window_and_compares_to_mean(self):
        sig = signals([1, 2, 3, 4], n=3)
        self.assertEqual(sig[:2], [None, None])
        self.assertEqual(sig[2], 3 > 2)
        self.assertEqual(sig[3], True)

    def test_no_peeking_and_switch_cost(self):
        # signal turns "down" at t=2's close -> day 3 earns cash, not the market's -50%
        mkt = [0.0, 0.0, 0.0, -0.5, 0.0]
        rf = [0.0] * 5
        sig = [None, True, False, False, False]
        curve, switches, inv = run_strategy(mkt, rf, sig, 1, True, start=2)
        # day2 uses sig[1]=True (market 0%), day3 uses sig[2]=False (cash) with one switch cost
        self.assertAlmostEqual(curve[1], 1 - SWITCH_COST)
        self.assertEqual(switches, 1)
        curve_unf, _, _ = run_strategy(mkt, rf, sig, 1, False, start=2)
        self.assertAlmostEqual(curve_unf[1], 0.5)


if __name__ == "__main__":
    unittest.main()
