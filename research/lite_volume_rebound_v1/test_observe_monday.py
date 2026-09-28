"""Deterministic Monday observer tests; fake client only."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.lite_volume_rebound_v1 import observe_monday as observer
from research.lite_volume_rebound_v1 import refresh


NOW = datetime(2026, 9, 28, 14, 0, 30, tzinfo=timezone.utc)


def morning(day, volume=100):
    bars = []
    for index, close in enumerate((98, 98, 98, 97, 97.5, 98)):
        minute = 30 + 5 * index
        opening = 100 if index == 0 else close
        bars.append({"t": f"{day}T09:{minute:02}:00-04:00",
                     "o": opening, "h": max(opening, close),
                     "l": min(opening, close, 98 if index == 0 else close),
                     "c": close, "v": volume, "vw": close})
    return bars


def history_fixture(folder):
    days = [(date(2026, 9, 25) - timedelta(days=19 - i)).isoformat() for i in range(20)]
    calendar = [{"date": day, "open": "09:30", "close": "16:00"} for day in days]
    payload = {"feed": "iex", "query": {"feed": "iex", "adjustment": "raw",
               "timeframe": "5Min", "start": refresh.START,
               "end": refresh.END_EXCLUSIVE}, "path": refresh.BAR_PATH,
               "complete": True, "rows": [bar for day in days for bar in morning(day)]}
    report = {"status": "COMPLETE_SIP_WITH_IEX_COVERAGE_REPORTED",
              "pinned_overlap": {"data_equivalent": True}}
    contents = {"calendar.json": calendar, "LITE_5Min_iex.json": payload, "report.json": report}
    files = []
    for name, value in contents.items():
        raw = json.dumps(value).encode()
        (folder / name).write_bytes(raw)
        files.append({"file": name, "sha256": hashlib.sha256(raw).hexdigest()})
    (folder / "manifest.json").write_text(json.dumps({"status": "GET_ONLY_MARKET_DATA",
        "start": refresh.START, "end_exclusive": refresh.END_EXCLUSIVE, "files": files}))
    return days


class FakeClient:
    def __init__(self, bars=None, *, clock=None, calendar=None):
        self.bars = bars if bars is not None else morning(observer.MONDAY, 200)
        self.clock = clock if clock is not None else {"timestamp": "2026-09-28T14:00:30Z", "is_open": True}
        self.calendar = calendar if calendar is not None else [{"date": observer.MONDAY,
                                                                "open": "09:30", "close": "16:00"}]
        self.calls = []

    def _request(self, method, path, *, data_api=False, query=None):
        self.calls.append((method, path, data_api, query))
        if method != "GET":
            raise AssertionError("Mutation attempted")
        if path == "/v2/calendar":
            return self.calendar
        if path == "/v2/clock":
            return self.clock
        if path == refresh.BAR_PATH and data_api and query == observer.QUERY:
            return {"symbol": "LITE", "bars": self.bars, "next_page_token": None}
        raise AssertionError("Unexpected endpoint or query")


class MondayObserverTests(unittest.TestCase):
    def test_signal_proposal_is_iex_only_and_get_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            days = history_fixture(path)
            client = FakeClient()
            result = observer.observe(client, path, now=lambda: NOW)
            self.assertEqual(result["status"], "SIGNAL_PROPOSAL")
            self.assertEqual(result["feed"], "iex")
            self.assertEqual(result["proposal"]["limit_price"], "98")
            self.assertEqual(result["proposal"]["prior_20_mean_volume"], "600")
            self.assertEqual(result["prior_20_dates"], days)
            self.assertEqual(result["orders_sent"], 0)
            self.assertFalse(result["proposal"]["order_submitted"])
            self.assertEqual([call[1] for call in client.calls], ["/v2/calendar", "/v2/clock", refresh.BAR_PATH])
            self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_before_ten_and_after_window_make_no_requests(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            history_fixture(path)
            for when in (datetime(2026, 9, 28, 13, 59, tzinfo=timezone.utc),
                         datetime(2026, 9, 28, 14, 5, tzinfo=timezone.utc)):
                client = FakeClient()
                result = observer.observe(client, path, now=lambda: when)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(client.calls, [])

    def test_incomplete_duplicate_stale_and_closed_all_block(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            history_fixture(path)
            cases = [FakeClient(bars=morning(observer.MONDAY, 200)[:-1]),
                     FakeClient(bars=morning(observer.MONDAY, 200) + morning(observer.MONDAY, 200)[-1:]),
                     FakeClient(clock={"timestamp": "2026-09-28T13:58:00Z", "is_open": True}),
                     FakeClient(clock={"timestamp": "2026-09-28T13:59:45Z", "is_open": True}),
                     FakeClient(calendar=[])]
            for client in cases:
                with self.subTest(client=client):
                    result = observer.observe(client, path, now=lambda: NOW)
                    self.assertEqual(result["status"], "BLOCKED")
                    self.assertEqual(result["orders_sent"], 0)
                    self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_malformed_decimal_blocks_current_and_saved_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            history_fixture(path)
            malformed = morning(observer.MONDAY, 200)
            malformed[0]["v"] = "bad"
            client = FakeClient(bars=malformed)
            self.assertEqual(observer.observe(client, path, now=lambda: NOW)["status"], "BLOCKED")
            saved = path / "LITE_5Min_iex.json"
            payload = json.loads(saved.read_text())
            payload["rows"][0]["v"] = "bad"
            saved.write_text(json.dumps(payload))
            manifest_path = path / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            for item in manifest["files"]:
                if item["file"] == saved.name:
                    item["sha256"] = hashlib.sha256(saved.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest))
            fresh = FakeClient()
            self.assertEqual(observer.observe(fresh, path, now=lambda: NOW)["reason"], "REFRESH_INVALID")
            self.assertEqual(fresh.calls, [])
            output = path / "blocked.json"
            with patch("sys.argv", ["observe_monday", "--refresh", str(path), "--output", str(output)]), \
                 patch.object(observer, "client_from_local_keys", side_effect=AssertionError("credentials loaded")):
                observer.main()
            self.assertEqual(json.loads(output.read_text())["reason"], "REFRESH_INVALID")

    def test_tampered_refresh_blocks_before_network(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            history_fixture(path)
            (path / "LITE_5Min_iex.json").write_text("{}")
            client = FakeClient()
            result = observer.observe(client, path, now=lambda: NOW)
            self.assertEqual(result["reason"], "REFRESH_INVALID")
            self.assertEqual(client.calls, [])

    def test_valid_bars_can_return_no_signal(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            history_fixture(path)
            client = FakeClient(bars=morning(observer.MONDAY, 100))
            result = observer.observe(client, path, now=lambda: NOW)
            self.assertEqual(result["status"], "NO_SIGNAL")
            self.assertIsNone(result["proposal"])

    def test_wrong_symbol_and_late_response_block(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            history_fixture(path)
            class WrongSymbol(FakeClient):
                def _request(self, method, path, *, data_api=False, query=None):
                    reply = super()._request(method, path, data_api=data_api, query=query)
                    return {**reply, "symbol": "SPY"} if path == refresh.BAR_PATH else reply
            self.assertEqual(observer.observe(WrongSymbol(), path, now=lambda: NOW)["status"], "BLOCKED")
            ticks = iter((NOW, NOW, datetime(2026, 9, 28, 14, 5, tzinfo=timezone.utc)))
            self.assertEqual(observer.observe(FakeClient(), path, now=lambda: next(ticks))["reason"],
                             "STALE_AFTER_BAR_REQUEST")


if __name__ == "__main__":
    unittest.main()
