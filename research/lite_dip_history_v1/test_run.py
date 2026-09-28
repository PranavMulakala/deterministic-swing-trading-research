import unittest
from decimal import Decimal

from research.lite_dip_history_v1.run import replay, weekly


def bars(*prices):
    """Five-minute (time, open, high, low, close) bars from 09:30, one per (open, high, low, close)."""
    return [(f"{(570 + 5 * i) // 60:02d}:{(570 + 5 * i) % 60:02d}", *map(Decimal, map(str, p)))
            for i, p in enumerate(prices)]


FLAT = [(99, 99, 99, 99)] * 6
SIGNAL = {"signal": True, "close_0955": "99"}


class ReplayTests(unittest.TestCase):
    def test_buys_at_ten_with_buffer_and_sells_at_two_percent_same_day(self):
        day = bars(*FLAT, (99, 99.5, 98.8, 99.2), (99.2, 99.4, 99, 99.3), (99.3, 101.5, 99.3, 101.2))
        result = replay({"d1": SIGNAL}, {"d1": day}, ["d1"])
        trade = result["trades"][0]
        self.assertEqual((trade["fill"], trade["shares"], trade["target"]), (Decimal("99.10"), 605, Decimal("101.09")))
        self.assertEqual((trade["exit_time"], trade["exit"], trade["pnl"]), ("10:10", Decimal("101.09"), Decimal("1203.95")))
        self.assertEqual(result["daily"][-1]["equity"], Decimal("1203.95"))

    def test_gap_above_target_sells_at_open_and_frees_that_mornings_signal(self):
        day1 = bars(*FLAT, (99, 99.5, 98, 99), (99, 100, 97, 98))
        day2 = bars((103, 103, 99, 99), *FLAT[1:], (99, 99, 99, 99))
        result = replay({"d1": SIGNAL, "d2": SIGNAL}, {"d1": day1, "d2": day2}, ["d1", "d2"])
        self.assertEqual(result["trades"][0]["exit"], Decimal("103"))
        self.assertEqual(result["trades"][0]["low"], Decimal("97"))
        self.assertEqual(result["counts"]["buys"], 2)
        self.assertEqual(result["open"]["entry_day"], "d2")

    def test_signal_while_holding_is_skipped_and_paper_loss_is_marked(self):
        day = bars(*FLAT, (99, 99, 90, 90))
        result = replay({"d1": SIGNAL, "d2": SIGNAL}, {"d1": day, "d2": day}, ["d1", "d2"])
        self.assertEqual((result["counts"]["buys"], result["counts"]["skipped_holding"]), (1, 1))
        self.assertEqual(result["daily"][-1]["equity"], (Decimal("90") - Decimal("99.10")) * 605)

    def test_no_buy_when_price_is_far_from_the_0955_close_or_bars_are_missing(self):
        day = bars(*FLAT, (102, 102, 102, 102))
        result = replay({"d1": SIGNAL}, {"d1": day, "d2": day}, ["d1", "d2"])
        self.assertEqual(result["counts"], {"signals": 1, "no_price": 1, "no_data": 1})
        self.assertIsNone(result["open"])

    def test_weekly_splits_realized_and_marked_by_calendar_week(self):
        daily = [{"day": "2026-09-25", "realized": Decimal(0), "equity": Decimal(-500), "holding": True},
                 {"day": "2026-09-28", "realized": Decimal(1200), "equity": Decimal(1200), "holding": False},
                 {"day": "2026-09-29", "realized": Decimal(1200), "equity": Decimal(900), "holding": True}]
        self.assertEqual([(w["realized"], w["marked"]) for w in weekly(daily)],
                         [(Decimal(0), Decimal(-500)), (Decimal(1200), Decimal(1400))])


if __name__ == "__main__":
    unittest.main()
