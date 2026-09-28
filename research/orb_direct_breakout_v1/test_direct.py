from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import unittest
from zoneinfo import ZoneInfo

from research.orb_direct_breakout_v1.engine import assert_only_pattern_changed, direct_pattern


ET = ZoneInfo("America/New_York")


def at(hm: str) -> datetime:
    return datetime.fromisoformat(f"2026-09-16T{hm}:00").replace(tzinfo=ET)


def spec() -> dict:
    return {
        "selection": {"range_end_exclusive": "09:35"},
        "pattern": {"last_confirmation_close": "11:00"},
    }


class DirectPatternTests(unittest.TestCase):
    def feature(self) -> dict:
        return {"day": "2026-09-16", "high": Decimal("100"), "low": Decimal("98")}

    def rows(self, breakout: str | None = "09:40") -> dict:
        rows = {}
        cursor = at("09:35")
        while cursor < at("11:00"):
            close = Decimal("100.01") if breakout and cursor.strftime("%H:%M") == breakout else Decimal("99.90")
            rows[cursor] = {"c": close}
            cursor += timedelta(minutes=5)
        return rows

    def test_first_breakout_close_is_signal_without_retest(self):
        out = direct_pattern(self.feature(), self.rows(), spec())
        self.assertEqual(out["status"], "signal")
        self.assertEqual(out["time"], at("09:45"))
        self.assertEqual(out["breakout_time"], at("09:45"))
        self.assertEqual(out["stop"], Decimal("98.99"))
        self.assertEqual(out["confirmation_close"], Decimal("100.01"))

    def test_exact_high_is_not_breakout(self):
        rows = self.rows(None)
        rows[at("09:35")]["c"] = Decimal("100")
        self.assertEqual(direct_pattern(self.feature(), rows, spec())["status"], "no_breakout")

    def test_missing_bar_is_unknown_not_no_breakout(self):
        rows = self.rows(None)
        del rows[at("10:00")]
        out = direct_pattern(self.feature(), rows, spec())
        self.assertEqual(out, {"status": "unknown_pattern_gap", "time": at("10:00")})

    def test_no_breakout_by_deadline(self):
        self.assertEqual(direct_pattern(self.feature(), self.rows(None), spec()), {"status": "no_breakout"})

    def test_feature_drift_detector_ignores_only_pattern(self):
        left = {"2026-09-16": {"LITE": {"status": "eligible", "rvol": Decimal("1"), "pattern": {"status": "retest_expired"}}}}
        right = {"2026-09-16": {"LITE": {"status": "eligible", "rvol": Decimal("1"), "pattern": {"status": "signal"}}}}
        assert_only_pattern_changed(left, right)
        right["2026-09-16"]["LITE"]["rvol"] = Decimal("2")
        with self.assertRaisesRegex(ValueError, "non-pattern feature drift"):
            assert_only_pattern_changed(left, right)


if __name__ == "__main__":
    unittest.main()

