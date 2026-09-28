import unittest
from types import SimpleNamespace

from research.lite_profit_only_v1.run import simulate


def day(opening=100, close=98, later_high=98, entry_bar_high=None):
    bars = [SimpleNamespace(o=close, h=close, l=close, c=close) for _ in range(78)]
    bars[0] = SimpleNamespace(o=opening, h=opening, l=min(98, close), c=close)
    for index in range(1, 6):
        bars[index] = SimpleNamespace(o=close, h=close, l=close, c=close)
    bars[6] = SimpleNamespace(o=close, h=opening + 2 if entry_bar_high is None else entry_bar_high,
                              l=close - 2, c=close)
    bars[7] = SimpleNamespace(o=close, h=later_high, l=close, c=close)
    return bars


class ProfitOnlyTests(unittest.TestCase):
    def test_entry_bar_target_cross_does_not_fill(self):
        result = simulate({"2026-01-02": day()}, "dip_30")
        self.assertEqual(result["entries"], 1)
        self.assertEqual(result["closed_trades"], 0)
        self.assertEqual(result["unresolved_positions"], 1)

    def test_later_strict_cross_fills_at_target(self):
        result = simulate({"2026-01-02": day(later_high=101)}, "dip_30")
        self.assertEqual(result["closed_trades"], 1)
        self.assertEqual(result["trades"][0]["exit_bar_index"], 7)
        self.assertEqual(result["trades"][0]["target_price"], "100")

    def test_no_deadline_and_unresolved_loss_is_marked(self):
        days = {f"2026-01-{number:02}": day(close=97-number,
                 entry_bar_high=95 if number == 2 else 97-number,
                 later_high=97-number)
                for number in range(2, 12)}
        result = simulate(days, "dip_30")
        self.assertEqual(result["entries"], 1)
        self.assertEqual(result["closed_trades"], 0)
        self.assertEqual(result["unresolved_positions"], 1)
        self.assertLess(float(result["net_marked_pnl"]), 0)
        self.assertEqual(result["skipped_occupied"], 9)


if __name__ == "__main__":
    unittest.main()
