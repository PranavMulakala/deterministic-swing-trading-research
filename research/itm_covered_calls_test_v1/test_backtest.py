"""Offline tests for test #26 (in-the-money covered calls with roll-downs). Expected numbers are worked by hand."""
from datetime import date, timedelta
import unittest

from research.itm_covered_calls_test_v1 import backtest as bt

D0 = date(2020, 1, 2)
E40 = D0 + timedelta(days=40)          # 2020-02-11
D10 = D0 + timedelta(days=10)          # 2020-01-12
E2 = D10 + timedelta(days=40)          # 2020-02-21


def chain():
    """SPY 100 on D0. At 40 days: 90 (2.0%/yr), 92 (6.0%/yr), 95 (10.7%/yr), 98 (14.2%/yr), 100 (not below SPY)."""
    return {(E40, "C", 90.0): (10.2, 10.4), (E40, "C", 92.0): (8.6, 8.8), (E40, "C", 95.0): (6.1, 6.3),
            (E40, "C", 98.0): (3.5, 3.7), (E40, "C", 100.0): (2.0, 2.2),
            (D0 + timedelta(days=55), "C", 95.0): (7.0, 7.2), (D0 + timedelta(days=20), "C", 95.0): (5.5, 5.7)}


def roll_chain(old=(0.8, 1.0), new_bid=5.0):
    """Ten days later, SPY 94. The old 95 call, and at 40 days: 85 (2.2%/yr) and 90 (10.2%/yr at a 5.00 bid)."""
    return {(E40, "C", 95.0): old, (E2, "C", 85.0): (9.2, 9.4), (E2, "C", 90.0): (new_bid, new_bid + 0.2)}


class PickTests(unittest.TestCase):
    def test_lowest_strike_reaching_the_annualized_return(self):
        self.assertEqual(bt.pick_call(chain(), D0, 100.0), (E40, 95.0, 6.1, 6.3))
        self.assertEqual(bt.pick_call(chain(), D0, 100.0, ann=0.05)[1], 92.0)
        self.assertIsNone(bt.pick_call(chain(), D0, 100.0, ann=0.20))   # 98 gives 14.2%; 100 is not below SPY
        self.assertAlmostEqual(bt.annualized_if_called(100.0, 95.0, 6.1, 40), 1.1 / 93.9 * 365 / 40)

    def test_expiration_tie_goes_later(self):
        q = {(D0 + timedelta(days=35), "C", 95.0): (6.0, 6.2), (D0 + timedelta(days=45), "C", 95.0): (6.5, 6.7)}
        self.assertEqual(bt.pick_expiration(q, D0, "C", bt.CALL_DTE), D0 + timedelta(days=45))


class AccountTests(unittest.TestCase):
    def opened(self, **kw):
        a = bt.Account(**kw)
        a.step(D0, chain(), 100.0, 0.0)
        self.assertEqual((a.shares, a.open["n"], a.open["strike"]), (999, 9, 95.0))
        self.assertAlmostEqual(a.open["credit"], 9 * (610 - 0.03))
        return a

    def test_roll_down_for_a_net_credit(self):
        a = self.opened()
        a.step(D10, roll_chain(), 94.0, 0.0)
        t = a.trades[0]
        self.assertEqual((t["closed"], a.open["strike"], a.open["exp"]), ("rolled", 90.0, E2))
        self.assertAlmostEqual(t["close_cost"], 9 * (100 + 0.03))
        self.assertAlmostEqual(t["pnl"], 9 * (610 - 0.03) - 9 * (100 + 0.03))
        self.assertAlmostEqual(a.open["credit"], 9 * (500 - 0.03))

    def test_no_roll_without_credit_or_with_under_7_days_or_when_disabled(self):
        a = self.opened()
        a.step(D10, roll_chain(old=(5.0, 5.3), new_bid=5.0), 94.0, 0.0)        # new bid 5.00 is not above the old ask
        self.assertEqual((a.trades, a.open["strike"], a.stats["roll_skipped_no_credit_or_call"]), ([], 95.0, 1))
        a = self.opened()
        a.step(E40 - timedelta(days=6), roll_chain(), 94.0, 0.0)               # 6 days left: let it expire
        self.assertEqual((a.trades, a.open["strike"]), ([], 95.0))
        a = self.opened(roll=False)
        a.step(D10, roll_chain(), 94.0, 0.0)
        self.assertEqual((a.trades, a.open["strike"]), ([], 95.0))

    def test_early_exercise_before_ex_date_and_no_sale_that_day(self):
        a = self.opened()
        d1 = date(2020, 1, 3)
        a.step(d1, {(E40, "C", 95.0): (15.5, 15.9)}, 110.0, 0.0, pre_ex_dividend=1.5)   # time value 0.70 < 1.50
        t = a.trades[0]
        self.assertEqual((t["closed"], a.open, a.stats["no_sale_day_before_exdate"]), ("early_exercise", None, 1))
        self.assertAlmostEqual(t["close_cost"], 15 * 100 * 9)
        self.assertEqual((a.stats["shares_sold_to_cover"], a.shares), (73, 926))   # cash 5,579.74 < 13,500
        cash = a.cash
        a.step(date(2020, 1, 6), {}, 110.0, 0.0, dividend=1.5)
        self.assertAlmostEqual(a.cash, cash + 926 * 1.5)
        b = self.opened()
        b.step(d1, {(E40, "C", 95.0): (16.0, 16.4)}, 110.0, 0.0, pre_ex_dividend=1.5)   # time value 1.20 < 1.50
        self.assertEqual(b.trades[0]["closed"], "early_exercise")
        c = self.opened()
        c.step(d1, {(E40, "C", 95.0): (16.6, 17.0)}, 110.0, 0.0, pre_ex_dividend=1.5)   # time value 1.80: kept
        self.assertEqual((c.trades, c.open["strike"]), ([], 95.0))

    def test_expiration_settles_and_sells_shares_when_cash_short(self):
        a = self.opened()
        a.cash = 0.0
        a.step(E40, {}, 110.0, 0.0)
        owe = (110 - 95) * 100 * 9
        self.assertEqual((a.trades[0]["closed"], a.stats["shares_sold_to_cover"], a.shares), ("assigned_at_expiry", 123, 876))
        self.assertAlmostEqual(a.cash, 123 * 110 - owe)
        b = self.opened()
        b.step(E40, {}, 94.0, 0.0)
        self.assertEqual((b.trades[0]["closed"], b.trades[0]["close_cost"]), ("expired", 0.0))

    def test_collar_put_on_a_three_percent_drop(self):
        a = self.opened(collar=True)
        e50 = D10 + timedelta(days=50)
        puts = {(e50, "P", 96.0): (3.0, 3.2), (e50, "P", 97.0): (3.5, 3.7), (E40, "C", 95.0): (2.0, 2.2)}
        cash = a.cash
        a.step(D10, puts, 96.5, 0.0)                     # -3.5%: buy 9 puts at the 97 strike (tie goes higher)
        self.assertEqual((a.put["strike"], a.put["n"], a.put["exp"]), (97.0, 9, e50))
        self.assertAlmostEqual(a.cash, cash - 9 * (370 + 0.03))
        a.step(e50, {}, 90.0, 0.0)
        self.assertAlmostEqual(a.put_trades[0]["value_at_expiry"], 7 * 100 * 9)


if __name__ == "__main__":
    unittest.main()
