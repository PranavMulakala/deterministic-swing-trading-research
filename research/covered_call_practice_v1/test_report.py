"""Offline tests for the covered-call practice report."""
from datetime import date
import unittest

from research.covered_call_practice_v1.report import summarize


class ReportTest(unittest.TestCase):
    def test_dollars_and_flags(self):
        positions = [{"symbol": "AMZN", "qty": "200", "avg_entry_price": "259.69", "current_price": "280"},
                     {"symbol": "AMZN261113C00275000", "qty": "-2", "avg_entry_price": "6.85", "current_price": "8.00"},
                     {"symbol": "HOOD", "qty": "400", "avg_entry_price": "109.38", "current_price": "90"},
                     {"symbol": "HOOD261113C00120000", "qty": "-4", "avg_entry_price": "4.75", "current_price": "0.50"}]
        amzn, hood = summarize(positions, date(2026, 11, 9))
        self.assertAlmostEqual(amzn["shares_pnl"], (280 - 259.69) * 200)
        self.assertAlmostEqual(amzn["call_pnl"], (6.85 - 8.00) * 200)
        self.assertAlmostEqual(amzn["if_called_away"], (275 - 259.69) * 200 + 6.85 * 200)
        self.assertAlmostEqual(amzn["break_even"], 259.69 - 6.85)
        self.assertTrue(any("above the $275 strike" in f for f in amzn["flags"]))
        self.assertEqual(len(hood["flags"]), 2)  # call nearly worthless + stock down 18%
        self.assertAlmostEqual(hood["total_pnl"], (90 - 109.38) * 400 + (4.75 - 0.50) * 400)


if __name__ == "__main__":
    unittest.main()
