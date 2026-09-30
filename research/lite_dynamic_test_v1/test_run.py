"""Offline tests for the LITE dynamic-rule replay on made-up five-minute bars (plan check 2)."""
from decimal import Decimal as D
import unittest

from research.lite_dynamic_test_v1 import run


def bar(clock, o, h, l, c):
    return (clock, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


def flat_day(price, clocks=("09:30", "09:35", "09:40", "09:45", "09:50", "09:55", "10:00", "10:05", "10:10")):
    return [bar(c, price, price, price, price) for c in clocks]


class TurnTriggerTests(unittest.TestCase):
    def test_fires_on_first_bar_closing_above_prior_high_after_a_one_percent_dip(self):
        bars = [bar("09:30", 100, 100, 99.5, 99.6), bar("09:35", 99.6, 99.7, 98.8, 98.9),   # dip reaches -1.2%
                bar("09:40", 98.9, 99.0, 98.7, 98.8), bar("09:45", 98.8, 99.4, 98.8, 99.3),  # closes above 99.0
                bar("09:50", 99.3, 99.5, 99.2, 99.4)]
        index, dip = run.turn_trigger(bars)
        self.assertEqual(index, 3)
        self.assertEqual(dip, D("-1.3"))

    def test_no_trigger_when_the_turn_bar_closes_above_the_open(self):
        bars = [bar("09:30", 100, 100, 99.5, 99.6), bar("09:35", 99.6, 99.7, 98.8, 98.9),
                bar("09:40", 98.9, 100.5, 98.9, 100.2)]
        self.assertIsNone(run.turn_trigger(bars))

    def test_no_trigger_without_a_one_percent_dip_or_after_1025(self):
        shallow = [bar("09:30", 100, 100, 99.5, 99.6), bar("09:35", 99.6, 99.7, 99.2, 99.3),
                   bar("09:40", 99.3, 99.9, 99.3, 99.8)]
        self.assertIsNone(run.turn_trigger(shallow))
        late = [bar("09:30", 100, 100, 98.5, 98.6), bar("10:30", 98.6, 99.5, 98.6, 99.4)]
        self.assertIsNone(run.turn_trigger(late))


class ExitTests(unittest.TestCase):
    def held(self):
        return {"fill": D("100"), "target": D("102"), "low": D("100"), "armed": False, "peak": None, "shares": 600}

    def test_target_exit_sells_at_target_and_at_the_open_on_a_gap(self):
        self.assertEqual(run.check_exit(self.held(), bar("11:00", 101, 102.5, 100.5, 102.2), "target", D(0)), D("102"))
        self.assertEqual(run.check_exit(self.held(), bar("09:30", 104, 105, 103, 104), "target", D(0)), D("104"))
        self.assertIsNone(run.check_exit(self.held(), bar("11:00", 101, 101.9, 100.5, 101), "target", D(0)))

    def test_trailing_exit_arms_at_target_then_sells_one_percent_below_the_high(self):
        h = self.held()
        self.assertIsNone(run.check_exit(h, bar("11:00", 101, 103, 100.9, 102.8), "trail", D(0)))  # arms; peak 103
        self.assertTrue(h["armed"])
        self.assertIsNone(run.check_exit(h, bar("11:05", 102.8, 105, 102.5, 104.8), "trail", D(0)))  # 102.5 > 101.97
        self.assertEqual(h["peak"], D("105"))
        price = run.check_exit(h, bar("11:10", 104.8, 104.9, 103.5, 103.6), "trail", D(0))  # level 103.95
        self.assertEqual(price, D("103.85"))  # 103.95 x 0.999, to the cent

    def test_trailing_exit_gap_down_sells_at_the_open(self):
        h = {**self.held(), "armed": True, "peak": D("105")}
        self.assertEqual(run.check_exit(h, bar("09:30", 101, 101.5, 100, 100.5), "trail", D(0)), D("100.90"))

    def test_unarmed_trailing_position_never_sells_below_target(self):
        h = self.held()
        self.assertIsNone(run.check_exit(h, bar("11:00", 99, 99.5, 90, 91), "trail", D(0)))
        self.assertEqual(h["low"], D("90"))


class SizingTests(unittest.TestCase):
    def test_tiers(self):
        for dip, dollars in (("-1.00", 40000), ("-1.99", 40000), ("-2.00", 60000), ("-2.99", 60000), ("-3.00", 80000),
                             ("-7.5", 80000)):
            self.assertEqual(run.ticket_for(D(dip), "tiered"), D(dollars))
        self.assertEqual(run.ticket_for(D("-7.5"), "flat"), D(60000))


class EngineTests(unittest.TestCase):
    def test_baseline_buys_at_1000_and_sells_the_next_day_at_target(self):
        signal = {"signal": True, "dip_pct": "-2.50", "close_0955": "98"}
        day1 = flat_day(98)
        day2 = flat_day(98)[:7] + [bar("10:05", 98, 101, 98, 100.5), bar("10:10", 100.5, 100.6, 100, 100)]
        result = run.simulate({"d1": signal}, {"d1": day1, "d2": day2}, ["d1", "d2"], "0_baseline")
        trade = result["trades"][0]
        self.assertEqual(trade["fill"], D("98.10"))              # 98 x 1.001
        self.assertEqual(trade["shares"], 611)                   # floor(60000 / 98.10)
        self.assertEqual(trade["target"], D("100.07"))           # 98.10 x 1.02, rounded up
        self.assertEqual((trade["exit_day"], trade["exit_time"], trade["exit"]), ("d2", "10:05", D("100.07")))
        tiered = run.simulate({"d1": signal}, {"d1": day1, "d2": day2}, ["d1", "d2"], "3_bigger_dip_bigger_buy")
        self.assertEqual(tiered["trades"][0]["shares"], 611)     # a 2.5% dip is the $60,000 tier
        self.assertEqual(result["dollar_days"], D("98.10") * 611)  # held at one close only


if __name__ == "__main__":
    unittest.main()
