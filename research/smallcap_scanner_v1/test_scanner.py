"""Offline tests for the paper small-cap scanner on made-up data."""
from datetime import datetime
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from research.smallcap_scanner_v1 import scanner as sc


class PillarTests(unittest.TestCase):
    def test_grades(self):
        _, grade = sc.pillars(7.6, 76.0, 14000.0, True, 2_870_000)
        self.assertEqual(grade, "A")
        checks, grade = sc.pillars(7.6, 76.0, 14000.0, False, 2_870_000)
        self.assertEqual((checks["news_24h"], grade), (False, "B"))
        _, grade = sc.pillars(25.0, 9.0, 3.0, True, 50_000_000)
        self.assertIsNone(grade)

    def test_missing_data_never_counts_as_a_pass(self):
        checks, grade = sc.pillars(7.6, 76.0, None, True, None)
        self.assertEqual((checks["rvol_5x"], checks["float_under_20m"], grade), (None, None, None))

    def test_edges(self):
        checks, _ = sc.pillars(2.0, 10.0, 5.0, True, 19_999_999)
        self.assertTrue(all(checks.values()))
        checks, _ = sc.pillars(20.01, 9.99, 4.99, True, 20_000_000)
        self.assertEqual([checks[k] for k in ("price_2_20", "up_10pct", "rvol_5x", "float_under_20m")], [False] * 4)

    def test_common_stock_filter_drops_warrants_and_funds(self):
        base = {"exchange": "NASDAQ", "tradable": True, "class": "us_equity"}
        self.assertTrue(sc.is_common_stock({**base, "symbol": "NXL", "name": "Nexalin Technology Inc. Common Stock"}))
        self.assertFalse(sc.is_common_stock({**base, "symbol": "GFAIW", "name": "Guardforce AI Co. Warrant"}))
        self.assertFalse(sc.is_common_stock({**base, "symbol": "ABC", "name": "Some Acquisition Corp"}))
        self.assertFalse(sc.is_common_stock({**base, "exchange": "OTC", "symbol": "XYZ", "name": "XYZ Inc"}))


class NewsTests(unittest.TestCase):
    def test_roundups_are_not_catalysts(self):
        self.assertTrue(sc.is_roundup({"headline": "12 Health Care Stocks Moving In Thursday's Intraday Session",
                                       "symbols": ["SDEV"]}))
        self.assertTrue(sc.is_roundup({"headline": "Nasdaq Gains 100 Points", "symbols": ["NXL"]}))
        self.assertTrue(sc.is_roundup({"headline": "Contract wins", "symbols": ["A", "B", "C", "D"]}))
        self.assertFalse(sc.is_roundup({"headline": "Nexalin Receives FDA Clearance", "symbols": ["NXL"]}))


class FakeData:
    def candidates(self):
        return {"AAA": {}, "BBB": {}, "CCC": {}, "DDDW": {}, "EEE": {}}

    def snapshots(self, symbols):
        snap = lambda p, prev, v, t="2026-10-01T12:29:00Z": {"latestTrade": {"p": p, "t": t},
                                                             "prevDailyBar": {"c": prev}, "dailyBar": {"v": v}}
        return {"AAA": snap(8.0, 5.0, 60_000), "BBB": snap(30.0, 20.0, 1), "CCC": snap(5.0, 4.9, 1),
                "DDDW": snap(3.0, 1.0, 1), "EEE": snap(6.0, 4.0, 60_000, "2026-09-30T19:59:00Z")}

    def asset(self, symbol):
        return {"exchange": "NASDAQ", "tradable": True, "class": "us_equity", "symbol": symbol,
                "name": "D Warrant" if symbol.endswith("W") else f"{symbol} Inc"}

    def avg_volume(self, symbols, today):
        return {"AAA": 10_000}

    def news(self, symbols, now):
        return {"AAA": "AAA wins contract"}


class ScanTests(unittest.TestCase):
    def test_end_to_end_with_fake_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(sc, "OUT", Path(tmp)), \
                 mock.patch.object(sc, "float_shares", return_value={"AAA": 3_000_000}):
                rec = sc.scan(FakeData(), datetime(2026, 10, 1, 8, 30, tzinfo=sc.NY))
            # BBB too pricey, CCC +2%, DDDW warrant, EEE last traded yesterday
            self.assertEqual([r["symbol"] for r in rec["results"]], ["AAA"])
            a = rec["results"][0]
            self.assertEqual((a["change_pct"], a["rvol"], a["grade"]), (60.0, 6.0, "A"))
            self.assertEqual(len((Path(tmp) / "scans.jsonl").read_text().splitlines()), 1)
            self.assertIn("AAA", sc.table(rec))
            with mock.patch.object(sc, "OUT", Path(tmp)):
                text = sc.summary_text("2026-10-01")
            self.assertIn("AAA", text)
            self.assertIn("first seen 08:30 ET at $8.00", text)
            self.assertIn("Closed above the first-seen price: 1 of 1", sc.review_text("2026-10-01", [
                {"grade": "A", "symbol": "AAA", "at": "2026-10-01T08:30:00-04:00", "price": 8.0,
                 "max_up_pct": 20.0, "max_down_pct": -5.0, "close_pct": 3.0}]))


class FloatBudgetTests(unittest.TestCase):
    def test_daily_cap_and_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "c.json"
            from datetime import date
            cache.write_text(json.dumps({"_calls": {date.today().isoformat(): 20},
                                         "OLD": {"float": 1_000_000, "on": date.today().isoformat()}}))
            with mock.patch.object(sc, "av_key", return_value="k"):
                out = sc.float_shares(["OLD", "NEW"], cache_path=cache, opener=object())
            self.assertEqual(out, {"OLD": 1_000_000, "NEW": None})  # cached hit; NEW refused at the daily cap


if __name__ == "__main__":
    unittest.main()
