"""Offline tests for the price-only position alert; fake market data and fake mail only."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from research.real_position_alert_v1 import monitor

ARMED = "2026-09-28T10:07:00-04:00"
NOW = datetime(2026, 9, 28, 14, 30, tzinfo=timezone.utc)


def config():
    return {"shares": "33.034698", "average_cost": "908.14", "levels": [
        {"id": "minus_500", "direction": "down", "price": "893.00", "label": "down $500", "armed_at": ARMED},
        {"id": "break_even", "direction": "up", "price": "908.14", "label": "back to break-even",
         "requires": "minus_500", "armed_at": ARMED},
        {"id": "plus_2pct", "direction": "up", "price": "926.30", "label": "up 2%", "armed_at": ARMED}]}


def bar(minute, low, high, close=None):
    return {"t": f"2026-09-28T14:{minute:02}:00Z", "o": close or low, "h": high, "l": low,
            "c": close or low, "v": 100}


class FakeClient:
    def __init__(self, bars, is_open=True):
        self.bars, self.is_open, self.calls = bars, is_open, []

    def _request(self, method, path, *, data_api=False, query=None):
        self.calls.append((method, path))
        assert method == "GET", "mutation attempted"
        if path == "/v2/clock":
            return {"is_open": self.is_open}
        if path.startswith("/v2/stocks/") and data_api:
            symbol = path.split("/")[3]
            bars = self.bars.get(symbol, []) if isinstance(self.bars, dict) else self.bars
            return {"symbol": symbol, "bars": bars, "next_page_token": None}
        raise AssertionError("unexpected endpoint")


class FakeOpener:
    def __init__(self, fail=False):
        self.requests, self.fail = [], fail

    def open(self, request, timeout):
        if self.fail:
            raise OSError("network down")
        self.requests.append(json.loads(request.data))
        opener = self

        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, limit):
                return json.dumps({"id": f"email-{len(opener.requests)}"}).encode()
        return Reply()


class AlertTests(unittest.TestCase):
    def test_closed_market_sends_nothing(self):
        client, mail = FakeClient([bar(10, 880, 890)], is_open=False), FakeOpener()
        state, sent = monitor.run(client, config(), {}, NOW, "re_test", mail)
        self.assertEqual(sent, [])
        self.assertEqual(client.calls, [("GET", "/v2/clock")])
        self.assertEqual(mail.requests, [])

    def test_bars_before_arming_are_ignored(self):
        early = {"t": "2026-09-28T13:45:00Z", "o": 880, "h": 950, "l": 880, "c": 900, "v": 1}
        state, sent = monitor.run(FakeClient([early, bar(10, 900, 905)]), config(), {}, NOW, "re_test", FakeOpener())
        self.assertEqual(sent, [])

    def test_level_fires_once_and_break_even_waits_for_the_drop(self):
        mail = FakeOpener()
        bars = [bar(10, 900, 909), bar(11, 892, 899)]
        state, sent = monitor.run(FakeClient(bars), config(), {}, NOW, "re_test", mail)
        # 909 before the drop must not count as "back to break-even".
        self.assertEqual(sent, ["minus_500"])
        self.assertIn("down $500", mail.requests[0]["subject"])
        self.assertEqual(mail.requests[0]["to"], [monitor.RECIPIENT])
        self.assertIn("No order was placed", mail.requests[0]["text"])
        state, sent = monitor.run(FakeClient(bars + [bar(12, 895, 910)]), config(), state, NOW, "re_test", mail)
        self.assertEqual(sent, ["break_even"])
        state, sent = monitor.run(FakeClient(bars + [bar(12, 895, 910), bar(13, 880, 890)]), config(), state,
                                  NOW, "re_test", mail)
        self.assertEqual(sent, [])
        self.assertEqual(len(mail.requests), 2)

    def test_failed_send_stays_pending(self):
        state, sent = monitor.run(FakeClient([bar(10, 892, 899)]), config(), {}, NOW, "re_test", FakeOpener(fail=True))
        self.assertEqual(sent, [])
        self.assertNotIn("minus_500", state["fired"])
        self.assertEqual(state["last_send_error"]["error"], "OSError")
        state, sent = monitor.run(FakeClient([bar(10, 892, 899)]), config(), state, NOW, "re_test", FakeOpener())
        self.assertEqual(sent, ["minus_500"])

    def test_second_symbol_uses_its_own_bars_and_position(self):
        cfg = config()
        cfg["positions"] = {"MU": {"shares": "50.96", "average_cost": "1079.08"}}
        cfg["levels"].append({"id": "mu_1000", "symbol": "MU", "direction": "down", "price": "1000.00",
                              "label": "down to $1,000", "armed_at": ARMED})
        mail = FakeOpener()
        bars = {"LITE": [bar(10, 900, 905)], "MU": [bar(10, 999, 1010, 1001)]}
        state, sent = monitor.run(FakeClient(bars), cfg, {}, NOW, "re_test", mail)
        self.assertEqual(sent, ["mu_1000"])
        self.assertTrue(mail.requests[0]["subject"].startswith("MU down to $1,000"))
        self.assertIn("50.96 shares (average $1,079.08)", mail.requests[0]["text"])
        self.assertEqual(state["checked_through_by_symbol"]["MU"], "2026-09-28T14:10:00Z")
        self.assertEqual(state["checked_through"], "2026-09-28T14:10:00Z")  # LITE, legacy key kept

    def test_bad_symbol_refused(self):
        with self.assertRaises(ValueError):
            monitor.bar_path("../v2/orders")

    def test_resend_key_requires_private_single_valid_key(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            path.write_text("OTHER=1\nTRADING_REPORT_RESEND_API_KEY=re_abc123\n")
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                monitor.resend_key(path)
            path.chmod(0o600)
            self.assertEqual(monitor.resend_key(path), "re_abc123")
            path.write_text("TRADING_REPORT_RESEND_API_KEY=re_a\nTRADING_REPORT_RESEND_API_KEY=re_b\n")
            with self.assertRaises(ValueError):
                monitor.resend_key(path)


if __name__ == "__main__":
    unittest.main()
