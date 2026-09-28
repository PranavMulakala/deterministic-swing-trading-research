"""Offline tests for the SPY bull put spread historical replay (synthetic chains only)."""
from datetime import date, timedelta
import math
import unittest

from research.spy_put_spread_backtest_v1 import backtest as bt

R = 0.02


MONDAY = date(2026, 10, 5)
EXPIRATIONS = (MONDAY + timedelta(days=30), MONDAY + timedelta(days=9))  # fixed contracts, as in real data


def chain(day, spot, iv=0.20, expirations=EXPIRATIONS, half_spread=0.02):
    """Synthetic two-sided quotes for puts and calls priced with Black-Scholes (calls via parity)."""
    quotes = {}
    for exp in expirations:
        dte = (exp - day).days
        t = (dte + 5.5 / 24) / 365
        for k in range(int(spot * 0.8), int(spot * 1.1) + 1):
            put, _ = bt.bs_put(spot, k, t, R, iv)
            call = put + spot * math.exp(-bt.Q * t) - k * math.exp(-R * t)
            for typ, price in (("P", put), ("C", call)):
                if price > half_spread + 0.01:
                    quotes[(exp, typ, float(k))] = (round(price - half_spread, 2), round(price + half_spread, 2))
    return quotes


def replay(days, scenario="mid", vol_filter=True):
    calendar = [days[0] + timedelta(days=i) for i in range(200) if (days[0] + timedelta(days=i)).weekday() < 5]
    return bt.Replay(days, calendar, {}, scenario, vol_filter)


class MathTests(unittest.TestCase):
    def test_black_scholes_put_matches_textbook(self):
        price, delta = bt.bs_put(100, 100, 1.0, 0.05, 0.2, q=0.0)
        self.assertAlmostEqual(price, 5.5735, places=3)
        self.assertAlmostEqual(delta, -0.3632, places=3)

    def test_implied_vol_round_trip(self):
        price, _ = bt.bs_put(765, 740, 30 / 365, 0.04, 0.17)
        self.assertAlmostEqual(bt.implied_vol(price, 765, 740, 30 / 365, 0.04), 0.17, places=4)

    def test_parity_recovers_spot(self):
        day = date(2026, 10, 5)
        self.assertAlmostEqual(bt.parity_spot(chain(day, 765.0), day, R, 5.5), 765.0, delta=0.3)


class ReplayTests(unittest.TestCase):
    def setup_history(self, rp, start_price=700.0, n=60, drift=0.001):
        # Gentle uptrend with small alternating moves: trend filter passes, realized vol about 8%.
        price = start_price
        for i in range(n):
            price *= 1 + drift + (0.005 if i % 2 else -0.005)
            rp.closes.append(price)
        return price

    def test_monday_entry_then_profit_take(self):
        monday = date(2026, 10, 5)
        rp = replay([monday, monday + timedelta(days=1)])
        last = self.setup_history(rp)
        rp.step(monday, chain(monday, last, iv=0.20), {}, last, None)
        self.assertIsNotNone(rp.position)
        p = rp.position
        self.assertEqual(p["long"], p["short"] - 5)
        self.assertLess(abs(abs(p["delta"]) - 0.20), 0.03)
        self.assertGreaterEqual(p["mid_credit"], bt.MIN_CREDIT)
        self.assertEqual(p["tp_limit"], bt.floor_cents(p["credit"] / 2))
        tuesday = monday + timedelta(days=1)
        rally = chain(tuesday, last * 1.04, iv=0.15)
        rp.step(tuesday, rally, rally, last * 1.04, last * 1.04)
        self.assertIsNone(rp.position)
        t = rp.trades[-1]
        self.assertEqual(t["reason"], "profit_take")
        self.assertAlmostEqual(t["pnl"], (t["credit"] - t["tp_limit"]) * 100 * t["qty"] - 0.12 * t["qty"], places=2)

    def test_breakeven_exit_uses_prior_close_and_blocks_same_day_entry(self):
        monday = date(2026, 10, 5)
        next_monday = monday + timedelta(days=7)
        rp = replay([monday, next_monday])
        last = self.setup_history(rp)
        rp.step(monday, chain(monday, last), {}, last, None)
        breakeven = rp.position["breakeven"]
        rp.closes.append(breakeven - 1)  # the prior session closed below break-even
        crash = chain(next_monday, breakeven - 1, iv=0.35)
        rp.step(next_monday, crash, {}, breakeven - 1, None)
        self.assertEqual(rp.trades[-1]["reason"], "breakeven")
        self.assertLess(rp.trades[-1]["pnl"], 0)
        self.assertIsNone(rp.position)
        self.assertEqual(rp.stats["no_same_day_reentry"], 1)

    def test_filters_block_entry_but_unfiltered_variant_enters(self):
        monday = date(2026, 10, 5)
        filtered, unfiltered = replay([monday]), replay([monday], vol_filter=False)
        for rp in (filtered, unfiltered):
            last = self.setup_history(rp)
            # History realized vol is about 7.9%, so the filter needs IV >= about 9.5%; 9% fails.
            rp.step(monday, chain(monday, last, iv=0.09), {}, last, None)
        self.assertIsNone(filtered.position)
        self.assertEqual((filtered.stats["vol_ok"], filtered.stats["skip_filters"]), (0, 1))
        self.assertEqual(unfiltered.stats["skip_filters"], 0)  # it may still skip for a small credit

    def test_natural_fills_are_worse_than_mid(self):
        monday = date(2026, 10, 5)
        results = {}
        for scenario in ("mid", "natural"):
            rp = replay([monday], scenario)
            last = self.setup_history(rp)
            rp.step(monday, chain(monday, last, half_spread=0.05), {}, last, None)
            results[scenario] = rp.position["credit"]
        self.assertLess(results["natural"], results["mid"])

    def test_non_monday_does_not_enter(self):
        tuesday = date(2026, 10, 6)
        rp = replay([tuesday])
        last = self.setup_history(rp)
        rp.step(tuesday, chain(tuesday, last), {}, last, None)
        self.assertIsNone(rp.position)
        self.assertEqual(rp.stats["mondays_evaluated"], 0)


if __name__ == "__main__":
    unittest.main()
