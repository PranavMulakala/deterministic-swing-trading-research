"""Offline tests for the after-the-fact feed check; fake client only."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.lite_feed_check_20260928 import compare
from research.lite_volume_rebound_v1 import refresh

LATE = datetime(2026, 9, 28, 14, 25, tzinfo=timezone.utc)


def bars(day, volume, closes=(98, 98, 98, 97, 97.5, 98), extra=True):
    rows = []
    for index, close in enumerate(closes):
        opening = 100 if index == 0 else close
        rows.append({"t": f"{day}T09:{30 + 5 * index:02}:00-04:00", "o": opening,
                     "h": max(opening, close), "l": min(opening, close, 98 if index == 0 else close),
                     "c": close, "v": volume})
    if extra:
        rows.append({"t": f"{day}T10:00:00-04:00", "o": 98.1, "h": 98.5, "l": 97.9, "c": 98.2, "v": volume})
    return rows


def refresh_fixture(folder):
    days = [(date(2026, 9, 25) - timedelta(days=19 - i)).isoformat() for i in range(20)]
    contents = {"calendar.json": [{"date": d, "open": "09:30", "close": "16:00"} for d in days],
                "report.json": {"status": "COMPLETE_SIP_WITH_IEX_COVERAGE_REPORTED"}}
    for feed in ("iex", "sip"):
        contents[f"LITE_5Min_{feed}.json"] = {
            "feed": feed, "path": refresh.BAR_PATH, "complete": True,
            "query": {"feed": feed, "adjustment": "raw", "timeframe": "5Min",
                      "start": refresh.START, "end": refresh.END_EXCLUSIVE},
            "rows": [row for d in days for row in bars(d, 100 if feed == "iex" else 1000, extra=False)]}
    files = []
    for name, value in contents.items():
        raw = json.dumps(value).encode()
        (folder / name).write_bytes(raw)
        files.append({"file": name, "sha256": hashlib.sha256(raw).hexdigest()})
    (folder / "manifest.json").write_text(json.dumps({"files": files}))


class Fake:
    def __init__(self, iex_volume=200, sip_volume=1200):
        self.volumes = {"iex": iex_volume, "sip": sip_volume}
        self.calls = []

    def _request(self, method, path, *, data_api=False, query=None):
        self.calls.append((method, path, query.get("feed")))
        if method != "GET" or not data_api:
            raise AssertionError("Only market-data GETs are allowed")
        if path == refresh.BAR_PATH:
            return {"symbol": "LITE", "bars": bars("2026-09-28", self.volumes[query["feed"]]), "next_page_token": None}
        if path == compare.QUOTE_PATH:
            return {"symbol": "LITE", "quotes": [{"t": "2026-09-28T14:00:01Z", "ap": 98.05},
                                                 {"t": "2026-09-28T14:00:02Z", "ap": 97.99}], "next_page_token": None}
        raise AssertionError("Unexpected endpoint")


def observation(folder, status, limit=None):
    path = folder / "obs.json"
    path.write_text(json.dumps({"date": "2026-09-28", "orders_sent": 0, "status": status,
                                "proposal": None if limit is None else {"limit_price": limit}}))
    return path


class FeedCheckTests(unittest.TestCase):
    def test_refuses_before_1020_without_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            refresh_fixture(folder)
            client = Fake()
            with self.assertRaises(ValueError):
                compare.execute(client, observation(folder, "NO_SIGNAL"), folder, folder / "out",
                                now=lambda: datetime(2026, 9, 28, 14, 19, tzinfo=timezone.utc))
            self.assertEqual(client.calls, [])
            self.assertFalse((folder / "out").exists())

    def test_disagreement_is_reported_per_condition(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            refresh_fixture(folder)
            # IEX volume 2x its baseline qualifies; SIP 1.2x its baseline does not.
            report = compare.execute(Fake(iex_volume=200, sip_volume=1200), observation(folder, "NO_SIGNAL"),
                                     folder, folder / "out", now=lambda: LATE)
            self.assertTrue(report["feeds"]["iex"]["volume_1_5x_met"])
            self.assertFalse(report["feeds"]["sip"]["volume_1_5x_met"])
            self.assertEqual(report["feeds"]["iex"]["decision_limit"], "98")
            self.assertIsNone(report["feeds"]["sip"]["decision_limit"])
            self.assertFalse(report["feeds_agree_on_signal"])
            self.assertIsNone(report["quotes"])
            self.assertEqual(report["orders_sent"], 0)

    def test_quotes_only_after_signal_and_all_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            refresh_fixture(folder)
            client = Fake()
            report = compare.execute(client, observation(folder, "SIGNAL_PROPOSAL", "98"), folder,
                                     folder / "out", now=lambda: LATE)
            self.assertEqual(report["quotes"]["lowest_sip_ask"], "97.99")
            self.assertEqual(report["quotes"]["first_ask_at_or_below_limit"], "2026-09-28T14:00:02Z")
            self.assertTrue(report["feeds"]["iex"]["entry_bar_vs_observer_limit"]["low_at_or_below_limit"])
            self.assertTrue(all(call[0] == "GET" for call in client.calls))
            self.assertIn(compare.QUOTE_PATH, [call[1] for call in client.calls])

    def test_tampered_refresh_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            refresh_fixture(folder)
            (folder / "LITE_5Min_sip.json").write_text("{}")
            client = Fake()
            with self.assertRaises(ValueError):
                compare.execute(client, observation(folder, "NO_SIGNAL"), folder, folder / "out", now=lambda: LATE)
            self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
