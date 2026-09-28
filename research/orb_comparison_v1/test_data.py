"""Offline tests: synthetic credentials, synthetic bars, no broker calls."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest

from . import collect as c
from . import verify as v


def fixture(step=5, day="2026-01-02", close="16:00"):
    sessions = v.calendar_sessions([{"date": day, "open": "09:30", "close": close}])
    start, end = sessions[day]
    rows = [{"t": (start+timedelta(minutes=m)).isoformat(), "o": 100, "h": 102,
             "l": 99, "c": 101, "v": 100*step, "vw": 100.5}
            for m in range(0, int((end-start).total_seconds()/60), step)]
    return {"complete": True, "pages": 1, "query": c.bar_query(step),
            "path": "/v2/stocks/LITE/bars", "rows": rows}, sessions


class AcquisitionTests(unittest.TestCase):
    def test_only_scoped_get_requests_reach_transport(self):
        calls = []
        client = c.HistoricalClient("synthetic", "synthetic", transport=lambda *a: calls.append(a))
        for method, path, data in [("POST", "/v2/orders", False), ("GET", "/v2/account", False),
                                  ("GET", "/v2/positions", False), ("GET", "/v2/stocks/AAPL/bars", True),
                                  ("GET", "/v2/stocks/LITE/quotes", True), ("GET", "/v2/calendar", True),
                                  ("GET", "/v2/stocks/LITE/bars", False)]:
            with self.subTest(path=path, method=method), self.assertRaises(ValueError):
                client._request(method, path, data_api=data)
        with self.assertRaises(ValueError):
            client._request("GET", "/v2/calendar", body={})
        self.assertEqual(calls, [])
        client._request("GET", "/v2/calendar")
        client._request("GET", "/v2/stocks/COHR/bars", data_api=True)
        self.assertEqual([a[0] for a in calls], ["GET", "GET"])
        self.assertTrue(calls[0][1].startswith("https://paper-api.alpaca.markets/v2/calendar"))
        self.assertTrue(calls[1][1].startswith("https://data.alpaca.markets/v2/stocks/COHR/bars"))

    def test_pagination_exhausts_short_pages(self):
        calls = []
        class Fake:
            def _request(self, *args, **kwargs):
                calls.append(kwargs["query"])
                return {"symbol": "LITE", "bars": [{"t": len(calls)}], "next_page_token": "next" if len(calls) == 1 else None}
        result = c.paged(Fake(), "LITE", 1, pause=lambda _: None)
        self.assertTrue(result["complete"])
        self.assertEqual(result["pages"], 2)
        self.assertEqual(calls[1]["page_token"], "next")
        self.assertEqual(result["query"], c.bar_query(1))

    def test_bad_pagination_is_never_complete(self):
        for response in ({"symbol": "WRONG", "bars": []}, {"symbol": "LITE", "bars": None},
                         {"symbol": "LITE", "bars": [{}], "next_page_token": "same"},
                         {"symbol": "LITE", "bars": [], "next_page_token": "more"},
                         {"symbol": "LITE", "bars": [{}], "next_page_token": 1}):
            class Fake:
                def _request(self, *a, **kw): return response
            with self.subTest(response=response), self.assertRaises(ValueError):
                c.paged(Fake(), "LITE", 1, pause=lambda _: None)

    def test_page_cap_and_scope(self):
        class Fake:
            def _request(self, *a, **kw): return {"symbol": "LITE", "bars": [{}], "next_page_token": "more"}
        with self.assertRaisesRegex(ValueError, "limit"):
            c.paged(Fake(), "LITE", 1, max_pages=1, pause=lambda _: None)
        for symbol, step in (("AAPL", 1), ("LITE", 15), ("SPY", 1)):
            with self.assertRaises(ValueError): c.paged(Fake(), symbol, step)

    def test_files_are_exclusive_and_hashed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"x.json"
            entry = c.save(path, {"value": 1})
            self.assertEqual(v.sha(path), entry["sha256"])
            with self.assertRaises(FileExistsError): c.save(path, {})


class CoverageTests(unittest.TestCase):
    def test_frozen_specification_and_implementation_hashes(self):
        root = Path(__file__).resolve().parent
        frozen = json.loads((root/"FREEZE.json").read_text())
        for name, expected in frozen["files"].items():
            with self.subTest(file=name):
                self.assertEqual(v.sha(root/name), expected)
        spec = json.loads((root/"spec.json").read_text())
        self.assertEqual(spec["symbols"], list(v.STOCKS))
        self.assertEqual(spec["portfolio"]["initial_cash"], 5000)
        self.assertEqual(spec["selection"]["rvol_min"], 2)

    def test_regular_session_and_opening_coverage(self):
        data, sessions = fixture()
        bars, report = v.parse_bars(data, "LITE", 5, sessions)
        self.assertEqual(len(bars["2026-01-02"]), 78)
        self.assertEqual(report["sessions"][0]["missing"], [])
        self.assertTrue(report["sessions"][0]["opening_window_complete"])

    def test_early_close_and_dst(self):
        for day, close, count, offset in (("2025-11-28", "13:00", 42, -5), ("2026-07-01", "16:00", 78, -4)):
            data, sessions = fixture(day=day, close=close)
            bars, report = v.parse_bars(data, "LITE", 5, sessions)
            self.assertEqual(report["sessions"][0]["expected"], count)
            self.assertEqual(next(iter(bars[day])).utcoffset().total_seconds()/3600, offset)

    def test_missing_not_filled_and_not_opening_lookahead(self):
        data, sessions = fixture()
        data["rows"].pop()
        bars, report = v.parse_bars(data, "LITE", 5, sessions)
        self.assertEqual(report["sessions"][0]["missing"], ["15:55"])
        self.assertTrue(report["sessions"][0]["opening_window_complete"])
        self.assertEqual(len(bars["2026-01-02"]), 77)

    def test_wrong_provenance_fails(self):
        data, sessions = fixture()
        for field, value in (("complete", False), ("path", "/v2/stocks/FN/bars"), ("pages", 0)):
            modified = deepcopy(data)
            modified[field] = value
            with self.assertRaises(ValueError): v.parse_bars(modified, "LITE", 5, sessions)
        for field, value in (("feed", "iex"), ("adjustment", "all"), ("asof", "2026-09-07")):
            modified = deepcopy(data)
            modified["query"][field] = value
            with self.assertRaises(ValueError): v.parse_bars(modified, "LITE", 5, sessions)

    def test_duplicate_misaligned_out_of_window_and_invalid_values(self):
        data, sessions = fixture()
        bad = deepcopy(data)
        bad["rows"].append(bad["rows"][-1])
        with self.assertRaises(ValueError): v.parse_bars(bad, "LITE", 5, sessions)
        for field, value in (("t", "2026-01-02T09:31:00-05:00"), ("t", "2024-01-02T09:30:00-05:00"),
                             ("t", "2026-01-02T09:30:00"), ("h", 50), ("v", 0), ("c", float("nan")), ("o", True)):
            bad = deepcopy(data)
            bad["rows"][0][field] = value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                v.parse_bars(bad, "LITE", 5, sessions)

    def test_extended_hours_excluded_not_used_as_regular(self):
        data, sessions = fixture()
        extra = {**data["rows"][0], "t": "2026-01-02T08:00:00-05:00"}
        data["rows"].insert(0, extra)
        _, report = v.parse_bars(data, "LITE", 5, sessions)
        self.assertEqual(report["extended_or_outside_calendar_rows"], 1)
        self.assertEqual(report["sessions"][0]["present"], 78)

    def test_aggregation_agreement_disagreement_and_missing_minutes(self):
        one, sessions = fixture(1)
        five, _ = fixture(5)
        ones, _ = v.parse_bars(one, "LITE", 1, sessions)
        fives, _ = v.parse_bars(five, "LITE", 5, sessions)
        result = v.reconciliation(ones, fives)
        self.assertEqual(result["complete_windows_checked"], 78)
        self.assertEqual(result["mismatches"], [])
        first = next(iter(fives["2026-01-02"]))
        fives["2026-01-02"][first]["v"] += 1
        self.assertEqual(v.reconciliation(ones, fives)["mismatches"][0]["fields"], ["v"])
        del ones["2026-01-02"][first]
        self.assertEqual(v.reconciliation(ones, fives)["incomplete_one_minute_windows"], 1)

    def test_manifest_rejects_truncation_duplicates_and_bad_hash(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            names = ["calendar.json"]+[f"{s}_{m}Min.json" for s,m in v.JOBS]
            files = [c.save(folder/name, []) for name in names]
            base = {"complete": True, "errors": [], "files": files}
            for update in ({"complete": False}, {"files": files[:-1]}, {"files": files+[files[0]]},
                           {"files": [{**files[0], "sha256": "bad"}]+files[1:]}):
                (folder/"manifest.json").write_text(json.dumps({**base, **update}))
                with self.assertRaises(ValueError): v.verify(folder)

    def test_calendar_rejects_duplicates_and_empty(self):
        row = {"date": "2026-01-02", "open": "09:30", "close": "16:00"}
        for rows in ([], [row, row], [{**row, "close": "09:00"}]):
            with self.assertRaises(ValueError): v.calendar_sessions(rows)


if __name__ == "__main__":
    unittest.main()
