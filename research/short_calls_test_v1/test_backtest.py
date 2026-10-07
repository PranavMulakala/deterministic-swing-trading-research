"""Offline tests for test #24 on a hand-built option chain."""
from datetime import date
import unittest

from research.short_calls_test_v1.backtest import FEE, START, Account, pick_call


def chain(day):
    q = {}
    for exp in (date(2024, 1, 5), date(2024, 1, 10), date(2024, 1, 12), date(2024, 1, 19)):
        for k in (98.0, 100.0, 101.0, 102.0):
            q[(exp, "C", k)] = (1.00, 1.10)
    return q


class PickTest(unittest.TestCase):
    def test_expiration_and_strike(self):
        day = date(2024, 1, 3)                                   # Wed: Jan 10 is 7 days out
        self.assertEqual(pick_call(chain(day), day, 100.4), (date(2024, 1, 10), 100.0, 1.00, 1.10))
        self.assertEqual(pick_call(chain(day), day, 100.4, otm=0.015)[1], 102.0)   # 101.9 -> nearest 102
        day = date(2024, 1, 4)                                   # 6 and 8 days tie -> the later (Jan 12)
        self.assertEqual(pick_call(chain(day), day, 100.0)[0], date(2024, 1, 12))
        self.assertIsNone(pick_call({}, day, 100.0))


class AccountTest(unittest.TestCase):
    def test_buy_at_ask_then_settle_at_intrinsic(self):
        a = Account()
        d0, d1 = date(2024, 1, 3), date(2024, 1, 10)
        a.step(d0, chain(d0), 100.4, 0.0)
        p = a.open[0]
        n = int(0.02 * START // (110 + FEE))                      # $2,000 / ($110 + $0.03) = 18
        self.assertEqual((p["n"], p["price"]), (n, 1.10))
        a.step(d1, {}, 103.0, 0.0)                               # expires $3 in the money
        t = a.trades[0]
        self.assertAlmostEqual(t["pnl"], n * 300 - n * (110 + FEE))
        self.assertAlmostEqual(a.cash, START + t["pnl"])

    def test_take_profit_sells_at_the_bid(self):
        a = Account(take_profit=1.0)
        d0, d1 = date(2024, 1, 3), date(2024, 1, 4)
        a.step(d0, chain(d0), 100.4, 0.0)
        q = chain(d1)
        q[(date(2024, 1, 10), "C", 100.0)] = (2.30, 2.40)         # bid >= 2 x 1.10
        a.step(d1, q, 102.5, 0.0)
        self.assertEqual(a.trades[0]["why"], "take_profit")
        self.assertEqual(a.trades[0]["exit_value"], 2.30)


if __name__ == "__main__":
    unittest.main()
