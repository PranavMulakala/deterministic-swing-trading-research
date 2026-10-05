"""Offline tests for test #9 on hand-built 5-minute bars."""
import unittest

from research.crt_1h_test_v1.backtest import day_trades
from research.crt_1h_test_v1.verify import trades_for_day
from research.crt_sweep_test_v1.backtest import mirror


def hour(o, h, l, c):
    """12 five-minute bars whose combined candle is (o, h, l, c)."""
    bars = [(o, o, o, o)] * 12
    bars[3] = (o, h, o, o)
    bars[7] = (o, o, l, o)
    bars[11] = (o, o, o, c)
    return bars


def day_from(hours, rest):
    out, m = [], 570
    for o, h, l, c in [b for x in hours for b in hour(*x)] + rest:
        out.append({"m": m, "o": o, "h": max(o, h, c), "l": min(o, l, c), "c": c})
        m += 5
    last = out[-1]["c"]
    while m < 960:
        out.append({"m": m, "o": last, "h": last, "l": last, "c": last})
        m += 5
    return out


C1, C2 = (100, 102, 99, 100), (100, 100.5, 98.5, 100)   # C2 sweeps 99, closes inside, high 100.5


class OneHourCRT(unittest.TestCase):
    def test_long_hits_target_with_sweep_low_stop(self):
        day = day_from([C1, C2], [(100, 100.8, 100, 100.7), (100.7, 102.1, 100.6, 102)])
        t = day_trades(day)[0]
        self.assertEqual((t["entry"], t["stop"], t["target"], t["reason"]), (100.7, 98.5, 102, "target"))

    def test_close_outside_range_is_invalid(self):
        day = day_from([C1, (100, 100.5, 98.5, 98.8)], [(98.8, 101, 98.8, 100.9)])
        self.assertEqual(day_trades(day), [])

    def test_expires_after_60_minutes(self):
        day = day_from([C1, C2], [(100, 100.2, 99.9, 100)] * 12 + [(100, 101, 100, 100.9)])
        self.assertEqual(day_trades(day), [])

    def test_mirror_matches_explicit_short(self):
        flip = lambda x: (-x[0], -x[2], -x[1], -x[3])
        rest = [(100, 100.8, 100, 100.7), (100.7, 102.1, 100.6, 102)]
        day = day_from([flip(C1), flip(C2)], [flip(r) for r in rest])
        m, e = day_trades(mirror(day)), trades_for_day(day, "short")
        self.assertEqual(len(m), 1)
        self.assertEqual((e[0]["entry"], e[0]["stop"], e[0]["target"], e[0]["reason"]),
                         (-m[0]["entry"], -m[0]["stop"], -m[0]["target"], "target"))


if __name__ == "__main__":
    unittest.main()
