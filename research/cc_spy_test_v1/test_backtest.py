"""Offline tests for test #13 on a hand-built call chain."""
import unittest
from datetime import date

from research.cc_spy_test_v1.backtest import Account, bs_call, lots_for, pick_call, zero_windows


def chain(day, expiration, spot, r=0.02, iv=0.16):
    t = ((expiration - day).days + 5.5 / 24) / 365
    q = {}
    for k in range(int(spot * 0.95), int(spot * 1.15)):
        price = bs_call(spot, k, t, r, iv)[0]
        if price >= 0.05:
            q[(expiration, "C", float(k))] = (round(price - 0.02, 2), round(price + 0.02, 2))
    return q


class CoveredCallTest(unittest.TestCase):
    def test_picks_30_delta_call_above_spot(self):
        day, exp = date(2020, 1, 2), date(2020, 2, 3)
        e, strike, bid, ask, delta = pick_call(chain(day, exp, 400), day, 400, 0.02, 0.30)
        self.assertEqual(e, exp)
        self.assertGreater(strike, 400)
        self.assertAlmostEqual(delta, 0.30, delta=0.03)

    def test_lot_sizing(self):
        self.assertEqual(lots_for(100_000, 400), 2)       # 2 x 40,004 fits, 3 doesn't
        self.assertEqual(lots_for(39_000, 400), 0)

    def test_buy_sell_expire_worthless_and_dividend(self):
        day, exp = date(2020, 1, 2), date(2020, 2, 3)
        a = Account(0.30, "bid", True)
        q = chain(day, exp, 400)
        a.step(day, q, q, 400, 400, 0.0, 0.0)
        self.assertEqual(a.shares, 200)
        self.assertIsNotNone(a.call)
        cash = a.cash
        a.step(date(2020, 1, 17), {}, {}, None, 401, 0.0, 1.5)  # ex-dividend $1.50/share
        self.assertAlmostEqual(a.cash, cash + 300)
        a.step(exp, {}, {}, None, 405, 0.0, 0.0)                # below a ~412 strike -> expires worthless
        self.assertFalse(a.trades[0]["called_away"])
        self.assertEqual(a.shares, 200)

    def test_called_away_then_bought_back(self):
        day, exp = date(2020, 1, 2), date(2020, 2, 3)
        a = Account(0.30, "bid", True)
        q = chain(day, exp, 400)
        a.step(day, q, q, 400, 400, 0.0, 0.0)
        k = a.call["strike"]
        a.step(exp, {}, {}, None, k + 10, 0.0, 0.0)
        self.assertTrue(a.trades[0]["called_away"])
        self.assertEqual(a.shares, 0)
        self.assertAlmostEqual(a.trades[0]["upside_given_up"], 10 * 100 * 2)
        nxt = date(2020, 2, 4)
        q2 = chain(nxt, date(2020, 3, 6), k + 10)
        a.step(nxt, q2, q2, k + 10, k + 10, 0.0, 0.0)
        self.assertGreater(a.shares, 0)
        self.assertIsNotNone(a.call)

    def test_zero_windows(self):
        curve = [("2020-01-01", 100.0), ("2020-01-02", 110.0), ("2020-01-03", 99.0), ("2020-01-04", 108.9)]
        out = zero_windows(curve, [("2020-01-03", "2020-01-03")])
        self.assertAlmostEqual(out[-1][1], 100 * 1.1 * 1.0 * 1.1)


if __name__ == "__main__":
    unittest.main()
