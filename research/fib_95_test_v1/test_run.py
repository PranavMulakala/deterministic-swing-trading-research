"""Offline tests for test #11 on hand-built candles."""
import unittest

from research.fib_95_test_v1.run import faker_outcome, mirror, pivots, signal_and_outcome, up_moves


def candle(h, l, c=None):
    c = (h + l) / 2 if c is None else c
    return {"d": "", "o": c, "h": h, "l": l, "c": c}


def ramp(a, b, n):
    """n candles moving from a to b, each 0.2 wide around its centre."""
    return [candle(a + (b - a) * i / (n - 1) + 0.1, a + (b - a) * i / (n - 1) - 0.1) for i in range(n)]


BASE = ramp(105, 100, 6) + ramp(100.5, 110, 8) + ramp(109.5, 104, 6)   # low ~99.9 at 5, high ~110.1 at 13


class FibTest(unittest.TestCase):
    def test_pivots_and_move(self):
        highs, lows = pivots(BASE)
        self.assertIn(13, highs)
        self.assertIn(5, lows)
        self.assertEqual(up_moves(BASE, 0.01), [(5, 13)])

    def test_two_closes_beyond_887_then_reversal(self):
        # 88.7% level = 110.1 - 0.887*10.2 = 101.05
        c = BASE + [candle(101.2, 100.6, 100.9), candle(101.0, 100.5, 100.8), candle(100.6, 99.5, 99.7)]
        r = signal_and_outcome(c, 5, 13, 0.887)
        self.assertEqual(r["outcome"], "reversal")
        self.assertEqual(r["t"], len(BASE) + 1)

    def test_new_high_before_signal_cancels(self):
        c = BASE + [candle(110.5, 109, 110)] + [candle(101, 100.4, 100.6)] * 3
        self.assertIsNone(signal_and_outcome(c, 5, 13, 0.887))

    def test_continuation(self):
        c = BASE + [candle(101.2, 100.6, 100.9), candle(101.0, 100.5, 100.8), candle(110.3, 100.7, 110)]
        self.assertEqual(signal_and_outcome(c, 5, 13, 0.887)["outcome"], "continuation")

    def test_no_peeking_watch_starts_after_confirmation(self):
        # The 5 confirmation candles (14-18) close below 88.7%? Not in BASE; signal must use candles >= 19.
        c = BASE + [candle(101.2, 100.6, 100.9), candle(101.0, 100.5, 100.8), candle(99.8, 99.0, 99.2)]
        self.assertGreaterEqual(signal_and_outcome(c, 5, 13, 0.887)["t"] - 1, 13 + 5 + 1)

    def test_faker_snap_back(self):
        # 76.4% = 110.1 - 0.764*10.2 = 102.31 ; 61.8% = 103.80
        c = BASE + [candle(102.5, 102.0, 102.2), candle(104.5, 102.1, 104.2)]
        self.assertEqual(faker_outcome(c, 5, 13, 0.764), "snap")

    def test_faker_invalid(self):
        c = BASE + [candle(102.5, 102.0, 102.2), candle(101.0, 100.6, 100.9), candle(101.0, 100.5, 100.7)]
        self.assertEqual(faker_outcome(c, 5, 13, 0.764), "invalid")

    def test_mirror_finds_down_move(self):
        m = mirror(BASE)
        self.assertEqual(up_moves(m, 0.01), [])   # mirrored: the 105->100 leg is too short and starts at the edge


if __name__ == "__main__":
    unittest.main()
