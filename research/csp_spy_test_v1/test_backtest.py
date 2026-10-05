"""Offline tests for test #10 on a hand-built option chain."""
import unittest
from datetime import date

from research.csp_spy_test_v1.backtest import Account, contracts_for, pick_put, settlement_loss
from research.spy_put_spread_backtest_v1.backtest import bs_put


def chain(day, expiration, spot, r=0.02, iv=0.18):
    t = ((expiration - day).days + 5.5 / 24) / 365
    q = {}
    for k in range(int(spot * 0.85), int(spot * 1.05)):
        price = bs_put(spot, k, t, r, iv)[0]
        if price >= 0.05:
            q[(expiration, "P", float(k))] = (round(price - 0.02, 2), round(price + 0.02, 2))
    q[(date(2020, 1, 10), "P", 400.0)] = (1.0, 1.1)   # too short-dated: must be ignored
    return q


class CSPTest(unittest.TestCase):
    def test_picks_30_day_expiration_and_30_delta_put_below_spot(self):
        day, exp = date(2020, 1, 2), date(2020, 2, 3)
        e, strike, bid, ask, delta = pick_put(chain(day, exp, 400), day, 400, 0.02, 0.30)
        self.assertEqual(e, exp)
        self.assertLess(strike, 400)
        self.assertAlmostEqual(abs(delta), 0.30, delta=0.03)

    def test_contracts_are_fully_cash_secured(self):
        self.assertEqual(contracts_for(100_000, 380), 2)     # 2 x 38,000 = 76,000 <= 100,000
        self.assertEqual(contracts_for(75_000, 380), 1)

    def test_settlement(self):
        self.assertEqual(settlement_loss(380, 390, 2), 0.0)
        self.assertAlmostEqual(settlement_loss(380, 370.5, 2), 1900.0)

    def test_account_keeps_premium_when_expiring_worthless_and_earns_interest(self):
        day, exp = date(2020, 1, 2), date(2020, 2, 3)
        a = Account(0.30, "bid", True)
        q = chain(day, exp, 400)
        a.step(day, q, q, 400, 400, 0.0)
        p = a.pos
        self.assertIsNotNone(p)
        cash_after_sale = a.cash
        self.assertAlmostEqual(cash_after_sale, 100_000 + p["premium"] - p["fees"])
        a.step(exp, {}, {}, None, 450, 0.0365)              # 32 days at 3.65% on the cash, then expires worthless
        self.assertAlmostEqual(a.cash, cash_after_sale * (1 + 0.0365 * 32 / 365))
        self.assertTrue(a.trades[0]["expired_worthless"])
        self.assertTrue(a.need_entry)

    def test_assignment_loss_is_paid(self):
        day, exp = date(2020, 1, 2), date(2020, 2, 3)
        a = Account(0.30, "bid", True)
        q = chain(day, exp, 400)
        a.step(day, q, q, 400, 400, 0.0)
        p = dict(a.pos)
        a.step(exp, {}, {}, None, p["strike"] - 10, 0.0)
        self.assertAlmostEqual(a.trades[0]["loss"], 10 * 100 * p["contracts"])
        self.assertAlmostEqual(a.trades[0]["pnl"], round(p["premium"] - p["fees"] - 1000 * p["contracts"], 2))


if __name__ == "__main__":
    unittest.main()
