"""Offline tests for test #19 (buy after a big one-day drop) on hand-built daily prices."""
from datetime import date, timedelta
import unittest

from research.big_drop_rebound_v1.backtest import COST, events, outcome, portfolio, prepare, signal


def weekdays(n, start="2020-01-02"):
    out, d = [], date.fromisoformat(start)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def stock(closes, highs=None, opens=None, lows=None, dollar=1e9):
    n = len(closes)
    days = weekdays(n)
    return prepare({"date": days, "open": opens or list(closes), "high": highs or list(closes),
                    "low": lows or list(closes), "close": list(closes), "volume": [dollar / c for c in closes]})


UP = [50.0 + 0.25 * k for k in range(210)]          # a steady uptrend: the last close is far above the 200-day average


class SignalTest(unittest.TestCase):
    def test_needs_a_10pct_drop_uptrend_and_liquidity(self):
        b = stock(UP + [UP[-1] * 0.89])
        self.assertAlmostEqual(signal(b, 210), -0.11)
        self.assertIsNone(signal(stock(UP + [UP[-1] * 0.91]), 210))                 # only -9%
        self.assertIsNone(signal(stock(UP + [UP[-1] * 0.89], dollar=1e8), 210))     # $100M a day: too small
        down = [150.0 - 0.25 * k for k in range(210)]
        self.assertIsNone(signal(stock(down + [down[-1] * 0.89]), 210))             # in a downtrend
        self.assertIsNotNone(signal(stock(down + [down[-1] * 0.89]), 210, uptrend=False))


class OutcomeTest(unittest.TestCase):
    def test_plus_20_fill_and_gap(self):
        closes = UP + [90.0, 95.0, 100.0, 104.0]
        highs = UP + [90.0, 96.0, 110.0, 104.0]                                      # day 212 trades above 90*1.001*1.2
        out = outcome(stock(closes, highs=highs), 210)
        fill = 90.0 * (1 + COST)
        self.assertEqual((out["reason"], out["exit_day"]), ("target", weekdays(213)[212]))
        self.assertAlmostEqual(out["exit"], fill * 1.2 * (1 - COST))
        opens = UP + [90.0, 95.0, 112.0, 104.0]                                      # gaps above the target
        out = outcome(stock(closes, highs=highs, opens=opens), 210)
        self.assertEqual(out["reason"], "target_gap")
        self.assertAlmostEqual(out["exit"], 112.0 * (1 - COST))

    def test_time_exit_on_day_10_and_worst_dip(self):
        closes = UP + [90.0] + [92.0] * 10
        lows = UP + [90.0] + [80.0] + [91.0] * 9                                     # dips 11% the next day
        out = outcome(stock(closes, lows=lows), 210)
        self.assertEqual((out["reason"], out["exit_day"]), ("time", weekdays(221)[220]))
        self.assertLess(out["worst_dip_pct"], -10)


class PortfolioTest(unittest.TestCase):
    def test_biggest_drop_first_slots_and_one_per_stock(self):
        names = [f"S{k}" for k in range(12)]
        stocks = {}
        for k, s in enumerate(names):
            drop = 0.80 - 0.005 * k                                                  # S0 -20%, S11 -25.5%: S11 biggest
            stocks[s] = stock(UP + [UP[-1] * drop] + [UP[-1] * drop] * 10)
        cal = weekdays(221)
        evts = events(stocks, (cal[210], cal[220]))
        trades, curve, skipped = portfolio(evts, stocks, cal, (cal[210], cal[220]))
        taken = sorted(t["symbol"] for t in trades)
        self.assertEqual(len(trades), 10)                                            # 10 slots
        self.assertNotIn("S0", taken)                                                # the two smallest drops were left out
        self.assertNotIn("S1", taken)
        self.assertEqual(skipped["no_slot_or_cash"], 2)


    def test_ranks_by_the_exact_drop_not_a_rounded_one(self):
        cal = weekdays(221)
        a = stock(UP + [UP[-1] * 0.879994] + [UP[-1] * 0.88] * 10)      # -12.0006%
        b = stock(UP + [UP[-1] * 0.880004] + [UP[-1] * 0.88] * 10)      # -11.9996%: same when rounded to 0.01%
        stocks = {"AAA": b, "ZZZ": a}                                    # alphabetical order would pick AAA first
        evts = events(stocks, (cal[210], cal[220]))
        import research.big_drop_rebound_v1.backtest as bt
        old = bt.MAX_POS
        bt.MAX_POS = 1
        try:
            trades, _, _ = portfolio(evts, stocks, cal, (cal[210], cal[220]))
        finally:
            bt.MAX_POS = old
        self.assertEqual([t["symbol"] for t in trades], ["ZZZ"])         # the bigger exact drop wins the only slot


if __name__ == "__main__":
    unittest.main()
