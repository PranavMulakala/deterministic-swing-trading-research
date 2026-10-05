"""Offline tests for the daily market brief on made-up prices."""
from datetime import date
import unittest

from research.market_brief_v1.brief import market_flags, position_lines, trend_lines, trend_signal, upcoming

MU = {"symbol": "MU", "shares": 10, "cost": 100.0, "target_pct": 25, "limit_pct": -20}


def price(close, day=0.0, five=0.0, high=0.0):
    return {"day": "2026-10-02", "close": close, "day_pct": day, "five_day_pct": five, "from_high_pct": high}


def levels(flags):
    return [level for level, _ in flags]


class BriefTest(unittest.TestCase):
    def test_quiet_position_has_no_flags(self):
        lines, flags = position_lines([MU], {"MU": price(101)})
        assert flags == [] and "+10" in lines[0]

    def test_target_and_limit_are_red(self):
        assert "RED" in levels(position_lines([MU], {"MU": price(126)})[1])
        assert "RED" in levels(position_lines([MU], {"MU": price(79)})[1])

    def test_minus_ten_and_near_limit_are_yellow(self):
        flags = position_lines([MU], {"MU": price(82)})[1]
        assert levels(flags) == ["YELLOW", "YELLOW"]  # -10% zone, and within 3% of the $80 limit

    def test_market_flags_use_preset_lines(self):
        prices = {"SNDK": price(1, day=-6), "WDC": price(1, day=-6), "STX": price(1, day=-4),
                  "SMH": price(1, day=-3.1), "SPY": price(1, day=-1.9)}
        texts = [text for _, text in market_flags(prices)]
        assert any("peers" in t for t in texts) and any("SMH" in t for t in texts)
        assert not any("SPY" in t for t in texts)

    def test_upcoming_heads_up_only_within_three_days(self):
        events = [{"date": "2026-10-05", "what": "a", "why": "", "status": "confirmed"},
                  {"date": "2026-10-15", "what": "b", "why": "", "status": "estimated"},
                  {"date": "2026-11-30", "what": "c", "why": "", "status": "estimated"}]
        rows, flags = upcoming(events, date(2026, 10, 2))
        assert [e["what"] for e in rows] == ["a", "b"] and len(flags) == 1

    def test_trend_signal_up_and_flip(self):
        rows = [{"c": 100.0}] * 200 + [{"c": 99.0}, {"c": 102.0}]   # yesterday below, today above the average
        t = trend_signal(rows)
        assert t["up"] and t["flipped"] and t["gap_pct"] > 0
        lines, flags = trend_lines({"SPY": t})
        assert "UP" in lines[0] and flags and flags[0][0] == "HEADS-UP"

    def test_trend_signal_needs_history(self):
        assert trend_signal([{"c": 1.0}] * 150) is None


if __name__ == "__main__":
    unittest.main()
