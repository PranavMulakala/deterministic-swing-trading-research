"""Offline tests for test #16 (episodic pivot) on hand-built bars."""
import unittest

from research.ep_test_v1.backtest import (acceptance_times, earnings_ok, entry_signal, lifecycle, portfolio,
                                         prior_stats, size)

COST = 0.001


def daily(closes, opens=None, lows=None, highs=None):
    n = len(closes)
    return {"date": [f"2026-03-{d:02d}" for d in range(1, n + 1)], "open": opens or list(closes),
            "high": highs or [c + 1 for c in closes], "low": lows or [c - 1 for c in closes], "close": list(closes),
            "volume": [1000.0] * n}


# Entry day: 9:30 bar sets the day's low (101), the 10:00 bar keeps the opening-range high at 110.5,
# the 10:30 bar breaks above it.
BARS = [[570, 110, 110.5, 101, 105, 600], [600, 105, 109, 104, 108, 100], [630, 108, 111.5, 107, 111, 100],
        [700, 111, 112, 110, 111.5, 100]]
FILL = 110.5 * (1 + COST)


class SignalTest(unittest.TestCase):
    def test_prior_stats(self):
        b = {"date": [str(d) for d in range(22)], "close": [10.0] * 22, "high": [11.0] * 22, "low": [9.0] * 22,
             "volume": [1000.0] * 22}
        adv, adv_usd, adr = prior_stats(b, 21)
        self.assertEqual((adv, adv_usd), (1000.0, 10000.0))
        self.assertAlmostEqual(adr, 0.2)

    def test_earnings_window(self):
        def ok(stamp, prev, day):
            return earnings_ok(acceptance_times([[stamp]]), prev, day)
        self.assertTrue(ok("2026-01-29T21:05:00.000Z", "2026-01-29", "2026-01-30"))    # 4:05 PM ET (EST)
        self.assertFalse(ok("2026-01-29T20:59:00.000Z", "2026-01-29", "2026-01-30"))   # 3:59 PM ET: before the close
        self.assertTrue(ok("2026-01-30T15:29:00.000Z", "2026-01-29", "2026-01-30"))    # 10:29 AM ET
        self.assertFalse(ok("2026-01-30T15:30:00.000Z", "2026-01-29", "2026-01-30"))   # 10:30 AM ET: too late
        self.assertTrue(ok("2026-01-31T15:00:00.000Z", "2026-01-30", "2026-02-02"))    # Saturday, Monday gap
        self.assertTrue(ok("2026-07-30T20:30:28.000Z", "2026-07-30", "2026-07-31"))    # 4:30 PM ET (EDT)

    def test_volume_and_breakout(self):
        self.assertEqual(entry_signal(BARS, 601, 0.10)[1], "low_volume")              # 9:30-10:00 volume 600 < 601
        flat = [x[:] for x in BARS]
        flat[2][2] = flat[3][2] = 110.4                                                # never trades above 110.5
        self.assertEqual(entry_signal(flat, 500, 0.10)[1], "no_breakout")
        sig, why = entry_signal(BARS, 500, 0.10)
        self.assertEqual(why, "ok")
        self.assertEqual(sig["minute"], 630)
        self.assertAlmostEqual(sig["fill"], FILL)
        self.assertEqual(sig["stop"], 101)
        self.assertFalse(sig["ambiguous"])

    def test_fill_at_bar_open_when_it_opens_above_the_range(self):
        bars = [x[:] for x in BARS]
        bars[2][1], bars[2][2] = 112, 113
        self.assertAlmostEqual(entry_signal(bars, 500, 0.10)[0]["fill"], 112 * (1 + COST))

    def test_skip_when_stop_wider_than_average_range(self):
        self.assertEqual(entry_signal(BARS, 500, 0.08)[1], "stop_wider_than_adr")    # (110.61-101)/110.61 = 8.7%

    def test_same_bar_ambiguity(self):
        bars = [x[:] for x in BARS]
        bars[2][3] = 100                                                               # entry bar also trades below 101
        sig = entry_signal(bars, 500, 0.10)[0]
        self.assertTrue(sig["ambiguous"])
        b = daily([100.0] * 12 + [111.0, 115.0])
        self.assertEqual(lifecycle(b, 12, bars, sig), [(b["date"][12], 101 * (1 - COST), 1.0, "stop_entry_bar")])
        flip = entry_signal(bars, 500, 0.10, flip=True)[0]
        self.assertEqual(flip["stop"], 100)                                            # low first, then the breakout
        self.assertEqual(lifecycle(b, 12, bars, flip, flip=True)[-1][3], "open_end")


class LifecycleTest(unittest.TestCase):
    def setUp(self):
        self.sig = entry_signal(BARS, 500, 0.10)[0]

    def test_stopped_later_on_entry_day(self):
        bars = BARS + [[705, 111, 111, 100.5, 101, 100]]
        b = daily([100.0] * 12 + [101.0])
        self.assertEqual(lifecycle(b, 12, bars, self.sig), [(b["date"][12], 101 * (1 - COST), 1.0, "stop_entry_day")])

    def test_gap_below_stop_fills_at_open(self):
        b = daily([100.0] * 12 + [111.0, 99.0], opens=[100.0] * 12 + [110.0, 100.0])
        self.assertEqual(lifecycle(b, 12, BARS, self.sig), [(b["date"][13], 100 * (1 - COST), 1.0, "stop_open")])

    def test_half_on_day_3_then_break_even_stop(self):
        closes = [100.0] * 12 + [111.0, 116.0, 118.0, 120.0, 112.0]
        opens = [100.0] * 12 + [110.0, 112.0, 116.0, 118.0, 110.0]
        lows = [99.0] * 12 + [101.5, 114.0, 116.0, 118.0, 109.0]
        b = daily(closes, opens=opens, lows=lows)
        parts = lifecycle(b, 12, BARS, self.sig)
        self.assertEqual(parts, [(b["date"][15], 120 * (1 - COST), 0.5, "half_day3"),
                                 (b["date"][16], 110 * (1 - COST), 0.5, "stop_open")])   # opened below break-even

    def test_trail_below_10_day_average(self):
        closes = [100.0] * 12 + [111.0, 112.0, 102.0]
        opens = [100.0] * 12 + [110.0, 111.0, 108.0]
        lows = [99.0] * 12 + [101.5, 108.0, 101.5]
        b = daily(closes, opens=opens, lows=lows)
        self.assertEqual(lifecycle(b, 12, BARS, self.sig), [(b["date"][14], 102 * (1 - COST), 1.0, "trail")])

    def test_open_at_end_of_data(self):
        b = daily([100.0] * 12 + [111.0, 115.0], lows=[99.0] * 12 + [101.5, 113.0])
        self.assertEqual(lifecycle(b, 12, BARS, self.sig), [(b["date"][13], 115.0, 1.0, "open_end")])


class SizeTest(unittest.TestCase):
    def test_one_percent_risk_with_caps(self):
        self.assertAlmostEqual(size(100_000, 100_000, 100, 95), 20_000)    # $1,000 risk / $5 = 200 shares
        self.assertAlmostEqual(size(100_000, 100_000, 100, 99), 25_000)    # 25% cap
        self.assertAlmostEqual(size(100_000, 10_000, 100, 95), 10_000)     # cash cap
        self.assertEqual(size(100_000, 500, 100, 95), 0.0)                 # under $1,000: skip


class PortfolioTest(unittest.TestCase):
    def test_cash_from_later_sales_cannot_fund_same_day_buys(self):
        def ev(sym, day, parts):
            return {"symbol": sym, "day": day, "minute": 630, "gap": 0.2, "fill": 100.0, "stop": 99.0,
                    "ambiguous": False, "adv_usd": 1e8, "prior63": 0.1, "parts": parts}
        events = [ev("A", "d1", [("d1", 99 * (1 - COST), 1.0, "stop_entry_day")])]          # stopped out after 10:30
        events += [ev(s, "d1", [("d2", 110.0, 1.0, "trail")]) for s in "BCD"]
        events += [ev("E", "d1", [("d2", 110.0, 1.0, "trail")]),                               # no cash left at 10:30
                   ev("B", "d2", [("d2", 110.0, 1.0, "trail")])]                               # B still held on d2
        data = {s: {"date": ["d1", "d2"], "close": [100.0, 110.0], "_idx": {"d1": 0, "d2": 1}} for s in "ABCDE"}
        trades, curve, skipped = portfolio(events, data, ["d1", "d2"])
        self.assertEqual(dict(skipped), {"no_cash": 1, "already_held": 1})                     # 4 x 25% cap = all cash
        self.assertEqual(len(trades), 4)
        a = next(t for t in trades if t["symbol"] == "A")
        self.assertAlmostEqual(a["pnl"], 250 * 99 * (1 - COST) - 25_000, places=4)
        self.assertAlmostEqual(curve[-1][1], 250 * 99 * (1 - COST) + 3 * 250 * 110.0, places=4)


if __name__ == "__main__":
    unittest.main()
