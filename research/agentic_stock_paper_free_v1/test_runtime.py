from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from research.agentic_portfolio_v1.evidence import EvidencePacket
from research.agentic_portfolio_v1.stock import STRATEGY, VERSION
from research.agentic_stock_paper_free_v1.runtime import RuntimeBlocked, canonical, process_cycle, sha256_bytes


NOW = datetime(2026, 9, 16, 17, 0, tzinfo=timezone.utc)
STOCKS = ["AAOI", "CIEN", "COHR", "FN", "LITE"]


def evidence(kind, symbol, now, data):
    return EvidencePacket.build(
        kind=kind, strategy=STRATEGY, version=VERSION, symbol=symbol,
        source="SYNTHETIC_FREE_STOCK_CONTRACT_TEST_ONLY", feature_as_of=now,
        observed_at=now, retrieved_at=now, data=data,
    ).as_dict()


def entry(symbol, now, *, passes=False, earnings=5):
    return evidence("stock_entry", symbol, now, {
        "price": "100", "next_ask": "100", "entry_limit": "101",
        "dollar_volumes_20": ["60000000"] * 20, "atr14": "5",
        "session_return": "-0.03" if passes else "0", "session_vwap": "99",
        "sma50": "90", "earnings_sessions_away": earnings,
        "hard_adverse_news": False, "thesis_broken": False,
        "thesis": "contract-test thesis", "invalidation": "contract-test invalidation",
    })


def management(symbol, now, price="100"):
    return evidence("stock_management", symbol, now, {"price": price, "thesis_broken": False})


def cycle(now=NOW, *, cycle_id="cycle-1", stale=False):
    observed = now - timedelta(minutes=6) if stale else now
    unsigned = {
        "schema_version": "1.0", "cycle_id": cycle_id, "decision_at": now.isoformat(),
        "completed_session_date": None,
        "coverage": {
            "source_mode": "ALPACA_BASIC_FREE_IEX_LIVE_SIP_HISTORY_V1",
            "stock_history_sessions": {symbol: 60 for symbol in STOCKS},
            "stock_symbols": STOCKS, "stock_observed_at": observed.isoformat(),
            "earnings_calendar_through": "2026-09-30", "news_lookback_seconds": 86400,
            "context_complete": True,
            "receipt_hashes": {name: "a" * 64 for name in (
                "direct_news", "earnings_calendar", "stock_history", "stock_quotes",
            )},
        },
        "stock_entries": [entry(symbol, now, passes=symbol == "AAOI") for symbol in STOCKS],
        "stock_management": [management(symbol, now) for symbol in STOCKS],
    }
    return {**unsigned, "cycle_hash": sha256_bytes(canonical(unsigned).encode())}


def rehash(raw):
    unsigned = {key: value for key, value in raw.items() if key != "cycle_hash"}
    raw["cycle_hash"] = sha256_bytes(canonical(unsigned).encode())
    return raw


class FreeStockRuntimeTests(unittest.TestCase):
    def test_cycle_fills_only_stock_and_replays(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle()
            result = process_cycle(raw, Path(tmp))
            self.assertEqual(result["status"], "PAPER_STOCK_CYCLE_COMPLETE")
            self.assertFalse(result["orders_enabled"])
            self.assertNotIn("option_account", result)
            self.assertEqual(result["stock_account"]["deployed_cents"], 199800)
            self.assertEqual(len([event for event in result["events"] if "fill" in event]), 1)
            replay = process_cycle(raw, Path(tmp))
            self.assertTrue(replay["replay"])
            self.assertEqual(replay["stock_account"], result["stock_account"])

    def test_fresh_management_closes_target_without_same_cycle_reentry(self):
        with tempfile.TemporaryDirectory() as tmp:
            process_cycle(cycle(), Path(tmp))
            point = NOW + timedelta(minutes=1)
            raw = cycle(point, cycle_id="cycle-2")
            raw["stock_management"] = [management(symbol, point, "112" if symbol == "AAOI" else "100") for symbol in STOCKS]
            rehash(raw)
            result = process_cycle(raw, Path(tmp))
            self.assertEqual(len([event for event in result["events"] if "close" in event]), 1)
            self.assertFalse(any("fill" in event for event in result["events"]))
            self.assertEqual(result["stock_account"]["deployed_cents"], 0)

    def test_stale_coverage_blocks_before_state_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeBlocked, "older than five minutes"):
                process_cycle(cycle(stale=True), Path(tmp))
            self.assertFalse((Path(tmp) / "stock.sqlite").exists())

    def test_missing_receipt_and_unknown_earnings_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle()
            raw["coverage"]["receipt_hashes"].pop("earnings_calendar")
            rehash(raw)
            with self.assertRaisesRegex(RuntimeBlocked, "source receipts"):
                process_cycle(raw, Path(tmp))
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle()
            raw["stock_entries"][0] = entry("AAOI", NOW, passes=True, earnings=None)
            rehash(raw)
            with self.assertRaisesRegex(RuntimeBlocked, "earnings distance"):
                process_cycle(raw, Path(tmp))

    def test_history_and_earnings_horizon_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle()
            raw["coverage"]["stock_history_sessions"]["LITE"] = 49
            rehash(raw)
            with self.assertRaisesRegex(RuntimeBlocked, "fewer than 50"):
                process_cycle(raw, Path(tmp))
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle()
            raw["coverage"]["earnings_calendar_through"] = "2026-09-20"
            rehash(raw)
            with self.assertRaisesRegex(RuntimeBlocked, "earnings calendar"):
                process_cycle(raw, Path(tmp))

    def test_wrong_source_mode_and_incomplete_symbol_coverage_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle()
            raw["coverage"]["source_mode"] = "UNLABELED"
            rehash(raw)
            with self.assertRaisesRegex(RuntimeBlocked, "source mode"):
                process_cycle(raw, Path(tmp))
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle()
            raw["stock_entries"].pop()
            rehash(raw)
            with self.assertRaisesRegex(RuntimeBlocked, "one fresh stock-entry"):
                process_cycle(raw, Path(tmp))

    def test_cycle_id_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            process_cycle(cycle(), Path(tmp))
            changed = cycle(NOW + timedelta(seconds=1), cycle_id="cycle-1")
            with self.assertRaisesRegex(RuntimeBlocked, "different input"):
                process_cycle(changed, Path(tmp))


if __name__ == "__main__":
    unittest.main()
