"""Offline tests for test #27."""
from datetime import date
import unittest

from research.mu_dip_calls_v1 import backtest as bt

D = date(2024, 3, 4)  # Monday


class Tests(unittest.TestCase):
    def test_pick_week_expiration_and_nearest_strike(self):
        chain = {(date(2024, 3, 8), 90.0): (1.0, 1.1),     # 4 days
                 (date(2024, 3, 11), 90.0): (1.5, 1.6),    # 7 days
                 (date(2024, 3, 11), 95.0): (0.5, 0.6),
                 (date(2024, 3, 15), 90.0): (2.0, 2.1)}    # 11 days
        self.assertEqual(bt.pick_contract(chain, D, 92.5), (date(2024, 3, 11), 95.0, 0.5, 0.6))  # tie -> higher strike
        self.assertEqual(bt.pick_contract(chain, D, 91.0)[1], 90.0)
        tie = {(date(2024, 3, 10), 90.0): (1, 1.1), (date(2024, 3, 12), 90.0): (1, 1.1)}  # 6 vs 8 days
        self.assertEqual(bt.pick_contract(tie, D, 90)[0], date(2024, 3, 12))

    def test_target_first_minute_else_intrinsic(self):
        q = [("t1", 1.5, 1.6), ("t2", 2.0, 2.1), ("t3", 3.0, 3.1)]
        self.assertEqual(bt.exit_scan(q, 1.0, 2.0, 80, 90), (2.0, "target", "t2"))
        self.assertEqual(bt.exit_scan(q[:1], 1.0, 2.0, 93.5, 90), (3.5, "expiration", None))
        self.assertEqual(bt.exit_scan(q, 1.0, None, 85, 90), (0.0, "expiration", None))

    def test_thousand_dollar_sizing(self):
        pnl, n = bt.trade_pnl(2.0, 4.0, "target")
        self.assertAlmostEqual(n, 1000 / 200.03)
        self.assertAlmostEqual(pnl, n * (400 - 0.03) - 1000)
        self.assertAlmostEqual(bt.trade_pnl(2.0, 0.0, "expiration")[0], -1000)

    def test_osi_round_trip(self):
        s = bt.osi(date(2020, 3, 13), 45)
        self.assertEqual(s, "MU    200313C00045000")
        self.assertEqual(bt.parse_osi(s), (date(2020, 3, 13), "C", 45.0))


if __name__ == "__main__":
    unittest.main()
