"""Offline tests for test #23 (RFK) on hand-built daily bars."""
import unittest

from research.rfk_test_v1.backtest import (fakeout, liquidity, path, signals, simulate, swing_lows)


def series():
    """85 quiet days around $50 (range low $48 touched twice as swing lows), then a fakeout and a killshot."""
    bars = []
    for k in range(80):
        lo = 48.0 if k in (64, 72) else 49.0
        bars.append([50.0, 51.0, lo, 50.0, 2e6])
    bars.append([49.5, 49.6, 47.0, 47.2, 3e6])     # 80: red, undercuts 48, closes in the bottom 25%
    bars.append([48.0, 50.0, 47.9, 49.8, 3e6])     # 81: closes above 49.6 -> buy 49.8, stop 47.0, target 52.6
    bars.append([50.0, 51.0, 49.5, 50.5, 2e6])     # 82
    bars.append([50.5, 52.8, 50.2, 52.0, 2e6])     # 83: target hit
    bars.append([52.0, 52.5, 51.0, 52.0, 2e6])     # 84
    return bars


class RuleTest(unittest.TestCase):
    def test_range_fakeout_killshot(self):
        bars = series()
        self.assertEqual([j for j in swing_lows(bars, 60, 80) if bars[j][2] <= 48 * 1.02], [64, 72])
        self.assertTrue(fakeout(bars, 80))
        self.assertFalse(fakeout(bars, 79))                       # a green, quiet day
        self.assertTrue(fakeout(bars, 80, close_below=True))        # also closed below the range low
        dates = [f"D{k:03d}" for k in range(len(bars))]
        b = {"date": dates, "raw": bars, "split": bars}
        got = signals("AAA", b)
        self.assertEqual(len(got), 1)
        s = got[0]
        self.assertEqual((s["fakeout"], s["date"], s["entry"], s["stop"]), ("D080", "D081", 49.8, 47.0))
        self.assertAlmostEqual(s["target"], 52.6)
        self.assertEqual((s["exit_date"], round(s["exit"], 6), s["reason"]), ("D083", 52.6, "target"))
        self.assertAlmostEqual(s["r"], 1.0)

    def test_no_signal_without_two_clear_lows_or_with_a_wide_range(self):
        bars = series()
        bars[72][2] = 49.0                                         # only one swing low left at the range low
        self.assertFalse(fakeout(bars, 80))
        bars = series()
        bars[70][1] = 70.0                                         # range height above 25%
        self.assertFalse(fakeout(bars, 80))

    def test_exits(self):
        bars = [[10, 10, 10, 10, 1]] * 3 + [[9, 9.5, 8.5, 9, 1]]  # gap below the stop at the open
        self.assertEqual(path(bars, 2, 10.0, 9.5, 10.5), (3, 9, "stop_gap"))
        bars = [[10, 10, 10, 10, 1]] * 3 + [[10, 10.6, 9.4, 10, 1]]  # both touched the same day: stop
        self.assertEqual(path(bars, 2, 10.0, 9.5, 10.5), (3, 9.5, "stop"))
        bars = [[10, 10, 10, 10, 1]] * 30
        self.assertEqual(path(bars, 2, 10.0, 9.5, 10.5), (22, 10, "time"))

    def test_liquidity_needs_price_and_dollar_volume(self):
        raw = [[1, 1, 1, 20.0, 3e6]] * 70
        self.assertIsNone(liquidity(raw)[60])
        self.assertAlmostEqual(liquidity(raw)[61], 60e6)
        raw = [[1, 1, 1, 9.0, 1e8]] * 70
        self.assertIsNone(liquidity(raw)[65])

    def test_sizing_and_cash(self):
        sig = {"symbol": "AAA", "date": "2020-01-02", "entry": 100.0, "stop": 95.0, "target": 105.0,
               "exit_date": "2020-01-03", "exit": 105.0, "reason": "target", "dvol": 1e8, "r_after_costs": 0.9}
        closes = {"AAA": {"2020-01-02": 100.0, "2020-01-03": 105.0}}
        trades, curve, _ = simulate([sig], closes, ["2020-01-02", "2020-01-03"], "2020-01-02", "2020-01-03")
        self.assertEqual(trades[0]["shares"], 99)                  # 10% cap: $10,000 / $100.10
        self.assertAlmostEqual(trades[0]["pnl"], 99 * (105 * 0.999 - 100 * 1.001))
        self.assertAlmostEqual(curve[-1][1], 100_000 + trades[0]["pnl"])


if __name__ == "__main__":
    unittest.main()
