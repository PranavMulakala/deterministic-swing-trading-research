import unittest
from decimal import Decimal
from types import SimpleNamespace

from research.lite_funded_comparison_v1.run import quantity, signal, simulate


def day(opening=100, first_low=98, close=98, later_close=None):
    rows = [SimpleNamespace(o=opening, h=max(opening, close), l=min(opening, close), c=close)
            for _ in range(78)]
    rows[0] = SimpleNamespace(o=opening, h=opening, l=first_low, c=close)
    if later_close is not None:
        for index in range(7, 78):
            rows[index] = SimpleNamespace(o=later_close, h=later_close, l=later_close,
                                          c=later_close)
    return rows


class ComparisonTests(unittest.TestCase):
    def test_signal_only_uses_completed_window(self):
        rows = day()
        self.assertEqual(signal("dip_10", rows), 2)
        rows[1] = SimpleNamespace(o=100, h=101, l=98, c=101)
        self.assertIsNone(signal("dip_10", rows))
        self.assertEqual(signal("dip_30", rows), 6)

    def test_quantity_never_exceeds_ticket(self):
        self.assertLessEqual(quantity(4000, 1000.01, 0.001) * Decimal("1000.01") * Decimal("1.001"), 1000)

    def test_no_loss_stop_and_deadline_is_next_session(self):
        days = {f"2026-01-{n:02}": day() for n in range(1, 8)}
        result = simulate(days, "dip_10", deadline=5)
        self.assertEqual(result["entries"], 2)
        self.assertEqual(result["closed_trades"], 1)
        self.assertEqual(result["trades"][0]["exit_date"], "2026-01-06")
        self.assertEqual(result["trades"][0]["exit_reason"], "deadline_next_session_open")

    def test_target_requires_completed_close_then_next_open(self):
        days = {"2026-01-01": day(later_close=105),
                "2026-01-02": day(opening=105, first_low=105, close=105)}
        result = simulate(days, "dip_10")
        self.assertEqual(result["closed_trades"], 1)
        self.assertEqual(result["trades"][0]["exit_date"], "2026-01-01")
        self.assertEqual(result["trades"][0]["exit_reason"], "target_close_then_next_open")

    def test_end_of_data_position_is_unresolved(self):
        result = simulate({"2026-01-01": day()}, "dip_10")
        self.assertEqual(result["closed_trades"], 0)
        self.assertEqual(result["unresolved_positions"], 1)


if __name__ == "__main__":
    unittest.main()
