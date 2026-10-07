"""Offline tests for the company research numbers helper."""
import unittest

from research.company_research_v1.numbers import growth, price_check, quarters


def fact(start, end, val, form="10-Q", filed="2026-01-01"):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed}


class NumbersTest(unittest.TestCase):
    def test_quarters_derives_q4_and_keeps_latest_filing(self):
        facts = [fact("2024-08-30", "2024-11-28", 10), fact("2024-08-30", "2024-11-28", 11, filed="2026-02-01"),
                 fact("2024-11-29", "2025-02-27", 20), fact("2024-08-30", "2025-02-27", 31),  # 6-month YTD: skipped
                 fact("2025-02-28", "2025-05-29", 30), fact("2024-08-30", "2025-08-28", 100, form="10-K")]
        self.assertEqual(quarters(facts), {"2024-11-28": 11, "2025-02-27": 20, "2025-05-29": 30, "2025-08-28": 39})

    def test_growth_matches_a_53_week_year(self):
        rows = growth({"2025-05-29": 50, "2025-08-28": 100, "2026-05-28": 75, "2026-09-03": 300})
        self.assertEqual([r[2] for r in rows], [None, None, 0.5, 2.0])

    def test_price_check_worst_drop_uses_closes(self):
        series = [("2025-12-31", 100.0), ("2026-01-02", 120.0), ("2026-02-02", 60.0), ("2026-03-02", 90.0)]
        out = price_check(series)
        self.assertEqual((out["this_year_pct"], out["worst_drop_pct"]), (-10.0, -50.0))
        self.assertEqual(out["worst_drop"], ("2026-01-02", 120.0, "2026-02-02", 60.0))
        self.assertEqual((out["one_year_high"], out["below_high_pct"]), (("2026-01-02", 120.0), -25.0))


if __name__ == "__main__":
    unittest.main()
