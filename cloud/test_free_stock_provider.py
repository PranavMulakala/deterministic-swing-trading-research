from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from cloud.free_stock_provider import ALPACA, NASDAQ, ProviderBlocked, SYMBOLS, build_cycle, canonical
from research.agentic_stock_paper_free_v2.runtime import process_cycle


NOW = datetime(2026, 9, 16, 17, 0, tzinfo=timezone.utc)


class FakeClient:
    def __init__(self, *, stale=False, malformed_calendar=False, weekend_none=False):
        self.stale = stale
        self.malformed_calendar = malformed_calendar
        self.weekend_none = weekend_none

    @staticmethod
    def raw(value):
        return canonical(value).encode()

    def get(self, host, path, query, *, alpaca):
        if host == ALPACA and path == "/v2/stocks/bars":
            bars = {}
            cursor = datetime(2026, 6, 1, 20, 0, tzinfo=timezone.utc)
            for symbol_index, symbol in enumerate(SYMBOLS):
                rows = []
                point = cursor
                while len(rows) < 70:
                    if point.weekday() < 5:
                        close = 80 + symbol_index + len(rows) / 10
                        rows.append({
                            "t": point.isoformat(), "o": close - 1, "h": close + 2,
                            "l": close - 2, "c": close, "v": 1_000_000, "vw": close,
                        })
                    point += timedelta(days=1)
                bars[symbol] = rows
            value = {"bars": bars, "next_page_token": None}
            return value, self.raw(value)
        if host == ALPACA and path == "/v2/stocks/snapshots":
            at = NOW - timedelta(minutes=6 if self.stale else 1)
            value = {"snapshots": {
                symbol: {
                    "latestTrade": {"p": 100, "t": at.isoformat()},
                    "latestQuote": {"bp": 99.95, "ap": 100.05, "t": at.isoformat()},
                    "dailyBar": {"vw": 99.5},
                }
                for symbol in SYMBOLS
            }}
            return value, self.raw(value)
        if host == ALPACA and path == "/v1beta1/news":
            value = {"news": [], "next_page_token": None}
            return value, self.raw(value)
        if host == NASDAQ and path == "/api/calendar/earnings":
            if self.malformed_calendar:
                value = {"data": []}
            elif self.weekend_none and query["date"] in {"2026-09-19", "2026-09-20"}:
                value = {"data": {"rows": None}}
            else:
                value = {"data": {"rows": []}}
            return value, self.raw(value)
        raise AssertionError((host, path, query, alpaca))


class FreeStockProviderTests(unittest.TestCase):
    def test_fixture_cycle_passes_runtime_and_contains_no_options(self):
        raw = build_cycle(FakeClient(), NOW)
        self.assertEqual(raw["coverage"]["stock_symbols"], list(SYMBOLS))
        self.assertEqual(len(raw["stock_entries"]), 5)
        self.assertNotIn("option_entries", raw)
        with tempfile.TemporaryDirectory() as tmp:
            result = process_cycle(raw, Path(tmp))
        self.assertEqual(result["status"], "PAPER_STOCK_CYCLE_COMPLETE")
        self.assertFalse(result["orders_enabled"])

    def test_stale_iex_quote_fails_closed(self):
        with self.assertRaisesRegex(ProviderBlocked, "stale"):
            build_cycle(FakeClient(stale=True), NOW)

    def test_empty_weekend_calendar_rows_are_valid(self):
        raw = build_cycle(FakeClient(weekend_none=True), NOW)
        self.assertEqual(len(raw["stock_entries"]), 5)

    def test_malformed_earnings_calendar_fails_closed(self):
        with self.assertRaisesRegex(ProviderBlocked, "earnings calendar"):
            build_cycle(FakeClient(malformed_calendar=True), NOW)


if __name__ == "__main__":
    unittest.main()
