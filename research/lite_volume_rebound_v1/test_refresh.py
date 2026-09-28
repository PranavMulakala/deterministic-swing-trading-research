"""Local fake-client tests; no credentials or HTTP requests."""
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.lite_volume_rebound_v1 import refresh


def rows(day):
    result = []
    offset = "-04:00" if day[5:7] in ("04", "05", "06", "07", "08", "09") else "-05:00"
    for index in range(78):
        hour, minute = divmod(570 + 5 * index, 60)
        result.append({"t": f"{day}T{hour:02}:{minute:02}:00{offset}",
                       "o": 98, "h": 99, "l": 97, "c": 98, "v": 100, "vw": 98})
    result[0].update(o=100, h=100, l=98, c=98)
    result[3].update(o=97, h=97, l=97, c=97)
    result[4].update(o=97.5, h=97.5, l=97.5, c=97.5)
    return result


class FakeClient:
    def __init__(self, calendar, feeds):
        self.calendar, self.feeds, self.calls = calendar, feeds, []

    def _request(self, method, path, *, data_api=False, query=None):
        self.calls.append((method, path, data_api, dict(query or {})))
        if (method, path, data_api) == ("GET", "/v2/calendar", False):
            return self.calendar
        if (method, path, data_api) != ("GET", refresh.BAR_PATH, True):
            raise AssertionError("Request outside GET-only market-data scope")
        return self.feeds[query["feed"]]


class RefreshTests(unittest.TestCase):
    def test_credentials_read_only_selected_keys_without_exporting_others(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            path.write_text("UNRELATED=do-not-load\nALPACA_PAPER_API_KEY=fake-key\n"
                            "ALPACA_PAPER_API_SECRET=fake-secret\n")
            path.chmod(0o600)
            env = {}
            self.assertEqual(refresh.credentials(env, path), ("fake-key", "fake-secret"))
            self.assertEqual(env, {})
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                refresh.credentials({}, path)

    def test_bounded_pages_preserve_payload_and_reject_stall(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            class Paged:
                def _request(self, method, path, *, data_api, query):
                    calls.append((method, path, data_api, query))
                    return {"symbol": "LITE", "bars": [{"t": str(len(calls))}],
                            "next_page_token": "next" if len(calls) == 1 else None}
            payload, files = refresh.fetch_pages(Paged(), "sip", Path(folder))
            self.assertEqual((payload["pages"], len(files)), (2, 2))
            self.assertTrue(payload["complete"])
            self.assertEqual(calls[1][3]["page_token"], "next")
            self.assertTrue(all(call[:3] == ("GET", refresh.BAR_PATH, True) for call in calls))
            self.assertEqual(calls[0][3]["end"], "2026-09-26T00:00:00Z")
            self.assertEqual(files[0]["sha256"], hashlib.sha256((Path(folder) / files[0]["file"]).read_bytes()).hexdigest())
            with self.assertRaises(ValueError):
                refresh.fetch_pages(Paged(), "other", Path(folder))

    def test_report_retains_sparse_iex_and_manifest_hashes(self):
        days = ["2026-01-02", "2026-01-05", "2026-09-04"]
        calendar = [{"date": day, "open": "09:30", "close": "16:00"} for day in days]
        sip = rows(days[0]) + rows(days[1]) + rows(days[2])
        iex = rows(days[0]) + rows(days[1])[:-1] + rows(days[2])
        feeds = {feed: {"symbol": "LITE", "bars": bars, "next_page_token": None}
                 for feed, bars in (("sip", sip), ("iex", iex))}
        fake = FakeClient(calendar, feeds)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "new"
            pinned = Path(folder) / "LITE_5Min.json"
            pinned.write_text(json.dumps({"path": refresh.BAR_PATH, "query": {"feed": "sip"},
                                          "complete": True, "rows": rows(days[2])}))
            pinned_manifest = Path(folder) / "pinned-manifest.json"
            pinned_manifest.write_text(json.dumps({"files": [{"file": pinned.name,
                "sha256": hashlib.sha256(pinned.read_bytes()).hexdigest()}]}))
            report = refresh.execute(fake, output, pinned_path=pinned, manifest_path=pinned_manifest)
            self.assertEqual(report["status"], "COMPLETE_SIP_WITH_IEX_COVERAGE_REPORTED")
            self.assertEqual(report["feeds"]["sip"]["complete_sessions"], 3)
            self.assertEqual(report["feeds"]["iex"]["complete_sessions"], 2)
            self.assertEqual(report["feeds"]["iex"]["missing_regular_bars_by_session"][days[1]], [955])
            self.assertTrue(report["pinned_overlap"]["data_equivalent"])
            manifest = json.loads((output / "manifest.json").read_text())
            for entry in manifest["files"]:
                self.assertEqual(entry["sha256"], hashlib.sha256((output / entry["file"]).read_bytes()).hexdigest())
            self.assertTrue(all(call[0] == "GET" for call in fake.calls))
            previous_calls = len(fake.calls)
            with self.assertRaises(FileExistsError):
                refresh.execute(fake, output, pinned_path=pinned, manifest_path=pinned_manifest)
            self.assertEqual(len(fake.calls), previous_calls)
            changed = {"rows": [dict(row) for row in rows(days[2])]}
            changed["rows"][0]["v"] += 1
            self.assertFalse(refresh.pinned_overlap(changed, pinned, pinned_manifest)["data_equivalent"])

    def test_causal_volume_baseline_and_missing_iex_morning(self):
        days = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(22)]
        calendar = {day: {"date": day, "open": "09:30", "close": "16:00"} for day in days}
        sip = {day: rows(day)[:6] for day in days}
        for day in days[20:]:
            for bar in sip[day]:
                bar["v"] = 200
        iex = {day: [dict(bar) for bar in bars] for day, bars in sip.items()}
        iex.pop(days[0])
        signals = refresh.signal_comparison(calendar, sip, iex)
        self.assertEqual(signals["sip"]["dates"], days[20:])
        self.assertEqual(signals["iex"]["dates"], [days[21]])
        self.assertEqual(signals["alignment"]["sip_only"], [days[20]])
        # Future volume cannot revise an earlier 10:00 signal.
        for bar in sip[days[21]]:
            bar["v"] = 10**8
        self.assertEqual(refresh.signal_comparison(calendar, sip, iex)["sip"]["details"][0]["date"], days[20])


if __name__ == "__main__":
    unittest.main()
