"""Offline tests for the dip-sized shadow ledger on made-up bot events."""
import unittest

from research.lite_sized_shadow_v1.shadow import ledger

EVENTS = [
    {"type": "NO_SIGNAL", "at": "2026-10-01T14:00:30+00:00", "dip_pct": "-0.40"},
    {"type": "SIGNAL", "at": "2026-10-02T14:00:30+00:00", "dip_pct": "-3.31"},
    {"type": "BUY_SUBMITTED", "at": "2026-10-02T14:00:31+00:00"},
    {"type": "FILLED_AND_TARGET_PLACED", "at": "2026-10-02T14:00:36+00:00", "avg_fill": "960.00", "qty": "66",
     "target": "979.20"},
    {"type": "SIGNAL", "at": "2026-10-05T14:00:30+00:00", "dip_pct": "-1.20"},
    {"type": "SIGNAL_SKIPPED_HOLDING", "at": "2026-10-05T14:00:30+00:00"},
    {"type": "SOLD_AT_TARGET", "at": "2026-10-06T14:00:31+00:00", "exit_price": "979.20",
     "exit_at": "2026-10-05T15:12:00Z"},
    {"type": "SIGNAL", "at": "2026-10-07T14:00:30+00:00", "dip_pct": "-1.50"},
    {"type": "FILLED_AND_TARGET_PLACED", "at": "2026-10-07T14:00:36+00:00", "avg_fill": "1000.00", "qty": "66",
     "target": "1020.00"},
]


class LedgerTests(unittest.TestCase):
    def test_resizes_each_real_trade_by_its_dip(self):
        out = ledger(EVENTS, mark="990")
        first, second = out["trades"]
        self.assertEqual((first["shadow_ticket"], first["shadow_shares"]), (80000, 83))   # 3.31% dip
        self.assertEqual(first["bot_pnl"], "1267.20")                                     # 66 x 19.20
        self.assertEqual(first["shadow_pnl"], "1593.60")                                  # 83 x 19.20
        self.assertEqual(first["exit_at"], "2026-10-05")
        # the skipped Oct 5 signal must not leak its dip into the Oct 7 trade
        self.assertEqual((second["dip_pct"], second["shadow_ticket"], second["shadow_shares"]), ("-1.50", 40000, 40))
        self.assertEqual((second["bot_open_pnl"], second["shadow_open_pnl"]), ("-660.00", "-400.00"))
        self.assertEqual((out["sales"], out["bot_realized"], out["shadow_realized"]), (1, "1267.20", "1593.60"))

    def test_open_position_without_a_mark_has_no_open_pnl(self):
        out = ledger(EVENTS)
        self.assertNotIn("bot_open_pnl", out["trades"][1])
        self.assertEqual(out["bot_open"], "0")


if __name__ == "__main__":
    unittest.main()
