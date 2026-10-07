"""Offline tests for test #25 (covered calls)."""
from datetime import date
import unittest

from research.covered_calls_test_v1 import backtest as bt

D0 = date(2020, 1, 2)
EXP = date(2020, 1, 31)


def chain(bid=1.0, ask=1.2):
    return {(EXP, "C", 100.0): (5.0, 5.2), (EXP, "C", 102.0): (bid, ask), (EXP, "C", 103.0): (0.6, 0.8),
            (date(2020, 2, 21), "C", 102.0): (2.0, 2.2), (date(2020, 1, 10), "C", 102.0): (0.3, 0.4)}


class CoveredCallTests(unittest.TestCase):
    def test_pick_30_day_first_strike_two_percent_up(self):
        self.assertEqual(bt.pick_call(chain(), D0, 100.0), (EXP, 102.0, 1.0, 1.2))
        self.assertEqual(bt.pick_call(chain(), D0, 100.0, atm=True)[1], 100.0)
        self.assertEqual(bt.pick_call(chain(), D0, 100.0, otm=0.01, dte=bt.WEEKLY)[0], date(2020, 1, 10))

    def test_expires_worthless_below_strike_and_dividend_credit(self):
        a = bt.Account()
        a.step(D0, chain(), 100.0, 0.0)
        self.assertEqual((a.shares, a.open["n"]), (999, 9))
        cash = a.cash
        a.step(date(2020, 1, 3), chain(), 100.0, 0.0, dividend=0.5)
        self.assertAlmostEqual(a.cash, cash + 999 * 0.5)
        a.step(EXP, {}, 101.0, 0.0)
        self.assertEqual(a.trades[0]["paid_at_expiry"], 0.0)
        self.assertAlmostEqual(a.trades[0]["pnl"], 9 * (100 - 0.03))

    def test_settles_above_strike_and_sells_shares_when_cash_short(self):
        a = bt.Account()
        a.step(D0, chain(), 100.0, 0.0)
        a.cash = 0.0
        a.step(EXP, {}, 110.0, 0.0)
        owe = (110 - 102) * 100 * 9
        self.assertAlmostEqual(a.trades[0]["paid_at_expiry"], owe)
        self.assertEqual(a.stats["shares_sold_to_cover"], 66)  # ceil(7,200 / 110)
        self.assertAlmostEqual(a.cash, 66 * 110 - owe)


if __name__ == "__main__":
    unittest.main()
