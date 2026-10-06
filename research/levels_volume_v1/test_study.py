"""Offline tests for test #22 on hand-built bars."""
import math
import unittest

from research.levels_volume_v1.study import (BUCKETS, boot, daily_events, holm, hourly_levels, level_row, prior_series,
                                             resistance, spike_effect, spike_row, stall_effect, support, sweep_effect,
                                             sweep_row)


class EventTest(unittest.TestCase):
    def test_levels_and_placebos(self):
        self.assertEqual(resistance(99, 101, 99.5, 100), [1, 1, 1, 99.5 / 100 - 1])     # reached, closed back below
        self.assertEqual(resistance(99, 99.9, 99.5, 100), [1, 0, 0, 0.0])                # never reached
        self.assertEqual(resistance(101, 102, 101, 100), [0, 0, 0, 0.0])                 # opened above: not a test
        self.assertEqual(support(101, 99, 100.5, 100)[:3], [1, 1, 1])                    # dipped through, held
        row = level_row("resistance", 98.8, 100.7, 100.2, 100.0)
        self.assertEqual(len(row), 20)
        self.assertEqual(row[0:3], [1, 1, 0])       # real 100: reached, closed above
        self.assertEqual(row[4:7], [1, 1, 0])       # placebo 99: reached, closed above
        self.assertEqual(row[8:11], [1, 1, 0])      # placebo 99.5
        self.assertEqual(row[12:15], [1, 1, 1])     # placebo 100.5: reached, closed below
        self.assertEqual(row[16:19], [1, 0, 0])     # placebo 101: not reached
        self.assertEqual(level_row("resistance", 99, 101, 100, None), [0, 0, 0, 0.0] * 5)

    def test_sweeps(self):
        row = sweep_row(low=97.5, high=101, c=99.5, level=98.0, after=0.01, side="low")
        # real 98: under it and closed above; placebos 96.04 and 97.02 never traded under; 98.98 yes; 99.96 closed below
        self.assertEqual(row, [1, 0.01, 0, 0.0, 0, 0.0, 1, 0.01, 0, 0.0])
        self.assertEqual(sweep_row(97.5, 101, 99.5, 98.0, None, "low"), [0, 0.0] * 5)
        self.assertEqual(sweep_row(97.5, 101, 99.5, 100.0, -0.02, "high")[0:2], [1, -0.02])

    def test_spike_buckets(self):
        self.assertEqual(spike_row(0.05, 300, 100, 0.02)[0:4], [1, 0.02, 0, 0.0])      # 3x volume, +5%
        self.assertEqual(spike_row(0.07, 120, 100, -0.01)[4:8], [0, 0.0, 1, -0.01])    # calm, +7%
        self.assertEqual(spike_row(0.12, 170, 100, 0.03), [0, 0.0, 0, 0.0] * 3)        # 1.7x: neither
        self.assertEqual(spike_row(0.03, 300, 100, 0.02), [0, 0.0, 0, 0.0] * 3)        # too small a move
        self.assertEqual(spike_row(-0.11, 300, 100, 0.05, up=False)[8:12], [1, 0.05, 0, 0.0])
        self.assertEqual(len(BUCKETS), 3)


class EffectTest(unittest.TestCase):
    def test_effects(self):
        s = [10, 5, 4, 0.0, 10, 5, 2, 0.0, 10, 5, 2, 0.0, 10, 5, 2, 0.0, 10, 5, 2, 0.0]
        self.assertAlmostEqual(stall_effect(s), 0.8 - 0.4)
        self.assertIsNone(stall_effect([0] * 20))
        self.assertAlmostEqual(sweep_effect([2, 0.02, 1, 0.0, 1, 0.0, 1, 0.0, 1, 0.0]), 0.01)
        # bucket 1: spikes +2% avg vs calm 0%; bucket 2: spikes 0% vs calm +1% (weights 3 and 1)
        s5 = [3, 0.06, 2, 0.0, 1, 0.0, 4, 0.04, 0, 0.0, 0, 0.0]
        self.assertAlmostEqual(spike_effect(s5), (3 * 0.02 + 1 * (0.0 - 0.01)) / 4)

    def test_bootstrap_and_holm(self):
        agg = {f"2024-01-{d:02d}": [2, 0.02 + d * 1e-4, 1, 0.0, 1, 0.0, 1, 0.0, 1, 0.0] for d in range(1, 29)}
        a = boot(agg, sorted(agg), sweep_effect, n=200, seed=1)
        b = boot(agg, sorted(agg), sweep_effect, n=200, seed=1)
        self.assertEqual(a, b)
        self.assertGreater(a["effect"], 0)
        self.assertLess(a["p"], 0.01)
        self.assertEqual(holm([0.01, 0.04, None, 0.03]), [0.03, 0.06, None, 0.06])


class DailyTest(unittest.TestCase):
    def test_prior_series_and_events(self):
        n = 200
        dates = [f"D{k:03d}" for k in range(n)]
        closes = [50 * (1.002 ** k) for k in range(n)]
        raw = [[c, c * 1.01, c * 0.99, c, 2e6] for c in closes]       # $100M a day
        raw[-2] = [closes[-3] * 1.01, closes[-3] * 1.07, closes[-3] * 1.0, closes[-3] * 1.06, 9e6]   # +6%, 4.5x volume
        split = [list(r) for r in raw]
        prior = prior_series(raw, split)
        self.assertIsNone(prior[127])
        liquid, ret = prior[150]
        self.assertTrue(liquid)
        self.assertAlmostEqual(ret, closes[149] / closes[149 - 126] - 1)
        spy = {d: 100.0 for d in dates}
        agg, per = {"liquid": {}, "momentum": {}}, {}
        daily_events({"date": dates, "raw": raw, "split": split}, {d: -1.0 for d in dates}, spy, agg, per)
        h5 = agg["momentum"]["h5_1d"][dates[-2]]
        self.assertEqual(h5[4], 1)                                       # one spike in the 6-10% bucket
        self.assertAlmostEqual(h5[5], raw[-1][3] / raw[-2][3] - 1)       # next day vs a flat SPY
        self.assertEqual(per["liquid"], per["momentum"])
        self.assertTrue(math.isfinite(sum(agg["liquid"]["h1"][dates[150]])))


class IntradayTest(unittest.TestCase):
    def test_hourly_levels(self):
        bars = [[570, 10, 10.5, 9.9, 10.2, 0], [630, 10.2, 11.0, 10.1, 10.9, 0], [690, 10.9, 10.95, 10.6, 10.7, 0],
                [810, 10.7, 10.8, 10.4, 10.5, 0], [870, 10.5, 10.6, 10.3, 10.4, 0]]
        one, four = hourly_levels(bars, 10.55)
        self.assertEqual(one, 10.6)        # hourly highs 10.5, 11.0 (the day's high, excluded), 10.95, 10.8, 10.6
        self.assertEqual(four, 10.8)       # 4-hour highs 11.0 and 10.8: the lower one, above the open
        self.assertEqual(hourly_levels(bars, 10.96), (None, None))


if __name__ == "__main__":
    unittest.main()
