"""Offline checks of definitions used in the exploratory price report."""
import unittest

from research.lite_2026.profile import describe_daily, describe_lite


def session_rows():
    # January uses EST: 09:30 local is 14:30 UTC.
    rows = []
    for minute in range(14 * 60 + 30, 21 * 60, 5):
        rows.append(dict(t=f"2026-01-05T{minute // 60:02}:{minute % 60:02}:00Z",
                         o=100, h=100.5, l=99.5, c=100))
    return rows


def snapshot(rows, close="16:00"):
    return dict(intraday={"LITE": rows},
                calendar=[dict(date="2026-01-05", open="09:30", close=close)])


class ProfileTests(unittest.TestCase):
    def test_afternoon_low_does_not_become_opening_dip(self):
        rows = session_rows()
        rows[30]["l"] = 90
        result = describe_lite(snapshot(rows))
        self.assertEqual(result["qualified_sessions"], 1)
        self.assertEqual(result["early_drop_at_least_one_pct"]["n"], 0)

    def test_recovery_is_not_a_winning_close(self):
        rows = session_rows()
        rows[2]["l"] = 98
        rows[6].update(o=99, l=98, c=99)
        rows[-1].update(o=97, l=97, h=98, c=98)
        result = describe_lite(snapshot(rows))["early_drop_at_least_one_pct"]
        self.assertEqual(result["n"], 1)
        self.assertEqual(result["recovered_open_pct"], 100)
        self.assertEqual(result["positive_ten_to_close_pct"], 0)
        self.assertAlmostEqual(result["mean_ten_to_close_pct"], -1.010, places=3)

    def test_missing_open_and_short_session_are_explicit(self):
        result = describe_lite(snapshot(session_rows()[1:]))
        self.assertEqual(result["qualified_sessions"], 0)
        self.assertEqual(result["excluded"]["missing_open_early_or_close_bar"], 1)
        result = describe_lite(snapshot(session_rows(), close="13:00"))
        self.assertEqual(result["excluded"]["shortened_or_nonstandard_session"], 1)

    def test_ytd_uses_previous_year_close(self):
        rows = [dict(t="2025-12-31T05:00:00Z", c=50),
                dict(t="2026-01-02T05:00:00Z", o=60, h=80, l=50, c=75)]
        result = describe_daily(rows)
        self.assertEqual(result["adjusted_close_change_ytd_pct"], 50)
        self.assertEqual(result["median_daily_bar_range_pct"], 50)


if __name__ == "__main__":
    unittest.main()
