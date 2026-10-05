"""Offline tests for test #8 on hand-built 5-minute bars (no data download needed)."""
import unittest

from research.crt_sweep_test_v1.backtest import day_trades, mirror
from research.crt_sweep_test_v1.verify import trades_for_day


def bar(m, o, h, l, c):
    return {"m": m, "o": o, "h": h, "l": l, "c": c}


def day_from(c1, c2, rest, start=570):
    """c1, c2: lists of three (o,h,l,c) 5-minute bars; rest: later bars. Flat filler to 15:55."""
    bars, m = [], start
    for o, h, l, c in c1 + c2 + rest:
        bars.append(bar(m, o, h, l, c))
        m += 5
    last = bars[-1]["c"]
    while m < 960:
        bars.append(bar(m, last, last, last, last))
        m += 5
    return bars


C1 = [(100, 101, 99.5, 100.5), (100.5, 101, 100, 100.2), (100.2, 100.8, 99.6, 100)]   # C1 high 101, low 99.5
C2_SWEEP_LOW = [(100, 100.2, 99.2, 99.6), (99.6, 99.9, 99.3, 99.8), (99.8, 100.1, 99.7, 100)]  # low 99.2, close 100, high 100.2


class SweepTest(unittest.TestCase):
    def test_valid_long_hits_target(self):
        day = day_from(C1, C2_SWEEP_LOW, [(100, 100.4, 100, 100.3), (100.3, 101.2, 100.2, 101)])
        trades = day_trades(day)
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual((t["entry"], t["stop"], t["target"], t["reason"]), (100.3, 100, 101, "target"))

    def test_body_closing_outside_is_invalid(self):
        c2 = C2_SWEEP_LOW[:2] + [(99.8, 99.9, 99.2, 99.3)]  # closes below C1's low
        day = day_from(C1, c2, [(99.3, 100.5, 99.3, 100.4)])
        self.assertEqual(day_trades(day), [])

    def test_two_sided_sweep_is_skipped(self):
        c2 = C2_SWEEP_LOW[:2] + [(99.8, 101.3, 99.7, 100)]  # also breaks C1's high
        day = day_from(C1, c2, [(100, 101.5, 100, 101.4)])
        self.assertEqual(day_trades(day), [])

    def test_setup_expires_after_30_minutes(self):
        flat = [(100, 100.1, 99.9, 100)] * 6
        day = day_from(C1, C2_SWEEP_LOW, flat + [(100, 100.5, 100, 100.4)])
        self.assertEqual(day_trades(day), [])

    def test_same_bar_counts_as_stop_by_default(self):
        day = day_from(C1, C2_SWEEP_LOW, [(100, 100.4, 100.1, 100.3), (100.3, 101.2, 100.0, 100.5)])
        self.assertEqual(day_trades(day)[0]["reason"], "stop_same_bar")
        self.assertEqual(day_trades(day, same_bar="target")[0]["reason"], "target_same_bar")

    def test_exit_at_close_when_nothing_hits(self):
        day = day_from(C1, C2_SWEEP_LOW, [(100, 100.4, 100.1, 100.3)])
        t = day_trades(day)[0]
        self.assertEqual((t["reason"], t["exit_m"]), ("close", 955))

    def test_short_mirror_and_independent_code_agree(self):
        flip = lambda bars: [(-o, -l, -h, -c) for o, h, l, c in bars]
        rest = [(100, 100.4, 100, 100.3), (100.3, 101.2, 100.2, 101)]
        day = day_from(flip(C1), flip(C2_SWEEP_LOW), flip(rest))
        mirrored = day_trades(mirror(day))
        explicit = trades_for_day(day, "short")
        self.assertEqual(len(mirrored), 1)
        self.assertEqual(len(explicit), 1)
        self.assertEqual((explicit[0]["entry"], explicit[0]["stop"], explicit[0]["target"], explicit[0]["reason"]),
                         (-mirrored[0]["entry"], -mirrored[0]["stop"], -mirrored[0]["target"], "target"))
        long_day = day_from(C1, C2_SWEEP_LOW, rest)
        self.assertEqual(trades_for_day(long_day, "long")[0]["reason"], day_trades(long_day)[0]["reason"])


if __name__ == "__main__":
    unittest.main()
