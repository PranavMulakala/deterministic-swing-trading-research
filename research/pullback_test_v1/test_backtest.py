"""Offline tests for the pullback backtest on made-up prices."""
import unittest
from unittest import mock

from research.pullback_test_v1 import backtest as bt


def trend_then_pullback(turn_early=False):
    """220 days rising 0.5 a day, a 4-day pullback, then a close above the prior day's high on day 224."""
    closes = [100 + 0.5 * i for i in range(220)] + [205, 202, 199, 197, 201]
    if turn_early:
        closes[222] = 204  # closes above day 221's high, so day 224 is no longer the first turn
    days = [f"day{i:03d}" for i in range(len(closes))]
    return {"date": days, "open": list(closes), "high": [c + 1 for c in closes], "low": [c - 1 for c in closes],
            "close": closes, "volume": [1_000_000] * len(closes)}


class ScanTests(unittest.TestCase):
    def test_first_turn_after_pullback_is_a_signal_with_video_levels(self):
        bars = trend_then_pullback()
        found = bt.scan(bars, bars)
        self.assertEqual([x["date"] for x in found], ["day224"])
        x = found[0]
        self.assertEqual(x["peak_date"], "day219")
        self.assertAlmostEqual(x["entry"], 202 * 1.001)
        self.assertAlmostEqual(x["stop"], 196 * 0.999)
        self.assertAlmostEqual(x["target"], 209.5 * 0.999)

    def test_not_the_first_turn_is_skipped(self):
        bars = trend_then_pullback(turn_early=True)
        self.assertEqual(bt.scan(bars, bars), [])

    def test_short_side_is_the_mirror_image(self):
        up = trend_then_pullback()
        real = {"date": up["date"], "open": [400 - x for x in up["open"]], "high": [400 - x for x in up["low"]],
                "low": [400 - x for x in up["high"]], "close": [400 - x for x in up["close"]], "volume": up["volume"]}
        found = bt.scan(bt.mirror(real), real)
        self.assertEqual([x["date"] for x in found], ["day224"])
        self.assertAlmostEqual(-found[0]["entry"], 198 * 0.999)   # sell stop just under the real low
        self.assertAlmostEqual(-found[0]["stop"], 204 * 1.001)    # stop just over the rally's highest high

    def test_illiquid_or_cheap_stock_is_skipped(self):
        bars = trend_then_pullback()
        thin = {**bars, "volume": [50_000] * len(bars["close"])}
        self.assertEqual(bt.scan(thin, thin), [])


class SimulateTests(unittest.TestCase):
    days = ["d0", "d1", "d2", "d3", "d4"]

    def run_case(self, rows, signals=None, side="long"):
        series = {"X": {"at": {d: i for i, d in enumerate(self.days)}, "open": [r[0] for r in rows],
                        "high": [r[1] for r in rows], "low": [r[2] for r in rows], "close": [r[3] for r in rows]}}
        signals = signals or {"d0": [{"symbol": "X", "peak_date": "d0", "entry": 100.0, "stop": 95.0, "target": 110.0,
                                      "dollar_volume": 1e8}]}
        return bt.simulate(self.days, signals, series, side)

    def test_fill_at_entry_then_target(self):
        trades, curve, _ = self.run_case([(99, 99, 99, 99), (99, 101, 98, 100), (104, 111, 103, 109), (1, 1, 1, 1), (1, 1, 1, 1)])
        t = trades[0]
        self.assertEqual((t["reason"], t["shares"], t["entry_date"], t["exit_date"]), ("target", 200, "d1", "d2"))
        self.assertAlmostEqual(t["pnl"], 200 * (110 * 0.999 - 100 * 1.001))
        self.assertAlmostEqual(curve[-1][1], bt.START_EQUITY + t["pnl"])

    def test_gap_above_entry_fills_at_the_open(self):
        trades, _, _ = self.run_case([(99, 99, 99, 99), (102, 103, 101, 102), (104, 111, 103, 109), (1, 1, 1, 1), (1, 1, 1, 1)])
        self.assertAlmostEqual(trades[0]["entry"], 102 * 1.001, places=3)

    def test_stop_and_target_same_day_counts_as_stop(self):
        trades, _, _ = self.run_case([(99, 99, 99, 99), (99, 101, 98, 100), (100, 111, 94, 100), (1, 1, 1, 1), (1, 1, 1, 1)])
        self.assertEqual(trades[0]["reason"], "stop")
        self.assertAlmostEqual(trades[0]["r_multiple"], -1.0, delta=0.05)

    def test_gap_below_stop_exits_at_the_open(self):
        trades, _, _ = self.run_case([(99, 99, 99, 99), (99, 101, 98, 100), (90, 91, 89, 90), (1, 1, 1, 1), (1, 1, 1, 1)])
        self.assertEqual((trades[0]["reason"], trades[0]["exit"]), ("stop_gap", round(90 * 0.999, 4)))

    def test_untouched_order_is_cancelled(self):
        trades, _, still_open = self.run_case([(99, 99, 99, 99), (99, 99.5, 98, 99), (99, 120, 98, 99), (99, 99, 99, 99), (99, 99, 99, 99)])
        self.assertEqual((trades, still_open), ([], {}))

    def test_time_exit(self):
        with mock.patch.object(bt, "MAX_HOLD", 2):
            trades, _, _ = self.run_case([(99, 99, 99, 99), (99, 101, 98, 100), (101, 102, 99, 101), (101, 103, 100, 102), (1, 1, 1, 1)])
        self.assertEqual((trades[0]["reason"], trades[0]["exit_date"]), ("time", "d3"))

    def test_new_trade_needs_a_new_peak_after_the_exit(self):
        rows = [(99, 99, 99, 99), (99, 101, 98, 100), (104, 111, 103, 109), (99, 99, 99, 99), (99, 101, 98, 100)]
        old = {"symbol": "X", "peak_date": "d0", "entry": 100.0, "stop": 95.0, "target": 110.0, "dollar_volume": 1e8}
        trades, _, _ = self.run_case(rows, {"d0": [old], "d3": [old]})
        self.assertEqual(len(trades), 1)
        trades, _, _ = self.run_case(rows, {"d0": [old], "d3": [{**old, "peak_date": "d3"}]})
        self.assertEqual(len(trades), 1)  # fills on d4 and is still open at the end
        _, _, still_open = self.run_case(rows, {"d0": [old], "d3": [{**old, "peak_date": "d3"}]})
        self.assertIn("X", still_open)

    def test_short_trade_profits_when_the_real_price_falls(self):
        # Real prices fall from 100 to 90; mirrored prices are their negatives.
        real = [(101, 101, 101, 101), (101, 102, 99.5, 100), (95, 96, 89, 90), (90, 90, 90, 90), (90, 90, 90, 90)]
        rows = [(-o, -lo, -hi, -c) for o, hi, lo, c in real]
        signal = {"symbol": "X", "peak_date": "d0", "entry": -100.0, "stop": -105.0, "target": -90.0, "dollar_volume": 1e8}
        trades, _, _ = self.run_case(rows, {"d0": [signal]}, side="short")
        t = trades[0]
        self.assertEqual((t["reason"], t["entry"] > 0, t["exit"] > 0), ("target", True, True))
        self.assertGreater(t["pnl"], 0)
        self.assertAlmostEqual(t["pnl"], t["shares"] * (100 * 0.999 - 90 * 1.001))

    def test_position_capped_at_a_quarter_of_the_account(self):
        tight = {"symbol": "X", "peak_date": "d0", "entry": 100.0, "stop": 99.9, "target": 110.0, "dollar_volume": 1e8}
        _, _, still_open = self.run_case([(99, 99, 99, 99), (99, 101, 99.95, 100), (100, 101, 99.95, 100), (100, 101, 99.95, 100),
                                          (100, 101, 99.95, 100)], {"d0": [tight]})
        self.assertLessEqual(still_open["X"]["shares"] * 100, 0.25 * bt.START_EQUITY)


if __name__ == "__main__":
    unittest.main()
