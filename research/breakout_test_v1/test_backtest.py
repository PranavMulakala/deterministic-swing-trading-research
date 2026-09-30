"""Offline tests for the breakout backtest on made-up prices."""
import unittest

from research.breakout_test_v1 import backtest as bt


def bars_from(closes, volume=2_000_000, spike_at=None, spike=4_000_000):
    days = [f"2020-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(len(closes))]
    return {"date": days, "open": list(closes), "high": [c * 1.005 for c in closes], "low": [c * 0.995 for c in closes],
            "close": list(closes), "volume": [spike if i == spike_at else volume for i in range(len(closes))]}


def flag(breakout=21.5):
    """A run from $12 to $20, a tight 10-day base near $20-21, then a breakout close."""
    closes = [12.0] * 25 + [12.0 + 8.0 * i / 30 for i in range(1, 31)] + [20.5, 20.3, 20.6, 20.4, 20.7, 20.5, 20.6, 20.4, 20.8, 20.6] + [breakout]
    return closes


class ScanTests(unittest.TestCase):
    def test_flag_breakout_on_volume_is_a_candidate(self):
        closes = flag()
        liquid, found = bt.scan(bars_from(closes, spike_at=len(closes) - 1))
        self.assertEqual([x["date"] for x in found], [bars_from(closes)["date"][-1]])
        self.assertIn(found[0]["date"], liquid)

    def test_no_candidate_without_volume_or_below_the_base(self):
        closes = flag()
        self.assertEqual(bt.scan(bars_from(closes))[1], [])                          # no volume spike
        low_close = flag(breakout=20.7)
        self.assertEqual(bt.scan(bars_from(low_close, spike_at=len(low_close) - 1))[1], [])  # not above the base high

    def test_illiquid_stock_is_skipped(self):
        closes = flag()
        self.assertEqual(bt.scan(bars_from(closes, volume=100_000, spike_at=len(closes) - 1, spike=400_000)), ({}, []))


class SimulateTests(unittest.TestCase):
    def setUp(self):
        self.days = ["d0", "d1", "d2", "d3", "d4", "d5", "d6"]
        self.stop = 95.0  # wide enough that the 1% risk rule, not the 25% cap, sets the size

    def run_case(self, lows, closes, sma10=None):
        series = {"X": {"at": {d: i for i, d in enumerate(self.days)}, "open": list(closes), "low": lows, "close": closes,
                        "sma10": sma10 or [0.0] * len(closes)}}
        candidates = {"d0": [{"symbol": "X", "date": "d0", "close": 100.0, "low": self.stop, "ret21": 0.5}]}
        return bt.simulate(self.days, {"d0": True}, {"d0": 0.1}, candidates, series)

    def test_stop_exit_loses_about_one_percent_of_the_account(self):
        trades, curve, _ = self.run_case([95.0, 94.0, 94, 94, 94, 94, 94], [100.0, 99.0, 99, 99, 99, 99, 99])
        self.assertEqual(trades[0]["exits"], ["stop"])
        self.assertAlmostEqual(curve[-1][1], bt.START_EQUITY - 1000, delta=150)

    def test_trims_on_days_three_and_five_then_ten_day_average_exit(self):
        closes = [100.0, 101, 102, 104, 105, 106, 103]
        sma10 = [0.0, 0, 0, 0, 0, 0, 104.0]
        trades, _, _ = self.run_case([95.0, 100, 101, 103, 104, 105, 102.5], closes, sma10)
        self.assertEqual(trades[0]["exits"], ["trim_day3", "trim_day5", "below_10sma"])
        self.assertGreater(trades[0]["pnl"], 0)



class CapTests(unittest.TestCase):
    def test_tight_stop_is_capped_at_a_quarter_of_the_account(self):
        days = ["d0", "d1"]
        series = {"X": {"at": {"d0": 0, "d1": 1}, "open": [100.0, 100.0], "low": [99.0, 99.5], "close": [100.0, 100.0], "sma10": [0.0, 0.0]}}
        _, _, still_open = bt.simulate(days, {"d0": True}, {"d0": 0.1}, {"d0": [{"symbol": "X", "date": "d0", "close": 100.0, "low": 99.0, "ret21": 0.5}]}, series)
        self.assertLessEqual(still_open["X"]["cost"], 0.25 * bt.START_EQUITY)

if __name__ == "__main__":
    unittest.main()
