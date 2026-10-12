"""Offline tests for the EdwardAlerts follower scorer (fake bars, no network)."""
from datetime import datetime, timezone
import unittest

from research.edward_alerts_v1.score import occ, score_alert, summarize

A = {"id": "T", "ts": "2026-10-09T14:36:36Z", "underlying": "PLTR", "strike": 207.5, "cp": "C", "expiry": "2026-10-16",
     "price": 2.71, "updates": [{"ts": "2026-10-09T15:00:10Z", "price": 4.0, "note": "UP"}]}


def bar(t, h, l, c):
    return {"t": t, "o": c, "h": h, "l": l, "c": c, "v": 1}


BARS = [bar("2026-10-09T14:36:00Z", 2.74, 2.71, 2.74), bar("2026-10-09T14:37:00Z", 2.80, 2.70, 2.75),
        bar("2026-10-09T15:01:00Z", 4.30, 3.90, 4.00), bar("2026-10-09T19:59:00Z", 3.00, 2.90, 3.00)]
NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


class ScoreTests(unittest.TestCase):
    def test_occ_symbol(self):
        self.assertEqual(occ(A), "PLTR261016C00207500")

    def test_entry_is_high_of_minute_after_alert_and_update_exit_is_low(self):
        r = score_alert(A, now=NOW, bars=BARS)
        self.assertEqual(r["entry"], 2.80)
        self.assertAlmostEqual(r["pnl"]["last_update"], 1000 * (3.90 / 2.80 - 1), places=1)
        self.assertAlmostEqual(r["pnl"]["hold"], 1000 * (3.00 / 2.80 - 1), places=1)
        self.assertAlmostEqual(r["pnl"]["tp50"], 500.0, places=1)       # 4.30 >= 2.80 * 1.5
        self.assertAlmostEqual(r["pnl"]["tp100"], r["pnl"]["hold"], places=6)  # never doubled

    def test_new_rules_his_rule_and_stops(self):
        r = score_alert(A, now=NOW, bars=BARS, stake=300)
        self.assertAlmostEqual(r["pnl"]["first_update"], 300 * (3.90 / 2.80 - 1), places=1)
        self.assertAlmostEqual(r["pnl"]["his_rule"], 300 * ((0.75 * 3.90 + 0.25 * 3.00) / 2.80 - 1), places=1)
        self.assertAlmostEqual(r["pnl"]["tp20_sl30"], 60.0, places=1)   # 4.30 high >= 2.80 * 1.2 before any -30%
        down = [BARS[0], BARS[1], bar("2026-10-09T15:01:00Z", 2.85, 1.90, 2.00), bar("2026-10-09T15:02:00Z", 4.0, 3.9, 4.0)]
        r2 = score_alert(A, now=NOW, bars=down, stake=300)
        self.assertAlmostEqual(r2["pnl"]["tp30_sl30"], -90.0, places=1)  # stop hit before the later spike

    def test_expired_uses_intrinsic_value_and_no_update_means_held(self):
        a = dict(A, updates=[], expiry="2026-10-09")
        r = score_alert(a, now=NOW, bars=BARS, expiry_close=206.0)
        self.assertEqual(r["status"], "expired")
        self.assertEqual(r["pnl"]["hold"], -1000.0)
        self.assertEqual(r["pnl"]["last_update"], -1000.0)
        self.assertEqual(summarize([r])["never_updated"], 1)


if __name__ == "__main__":
    unittest.main()
