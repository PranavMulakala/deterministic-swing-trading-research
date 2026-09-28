from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from research.agentic_paper_runtime_v1.runtime import RuntimeBlocked, canonical, process_cycle, sha256_bytes
from research.agentic_portfolio_v1.evidence import EvidencePacket
from research.agentic_portfolio_v1.options import STRATEGY as OPTION_STRATEGY, VERSION as OPTION_VERSION
from research.agentic_portfolio_v1.stock import STRATEGY as STOCK_STRATEGY, VERSION as STOCK_VERSION


NOW = datetime(2026, 9, 15, 15, 0, tzinfo=timezone.utc)
STOCKS = ["AAOI", "CIEN", "COHR", "FN", "LITE"]
OPTIONS = ["QQQ", "SPY"]


def evidence(kind, strategy, version, symbol, now, data):
    return EvidencePacket.build(
        kind=kind, strategy=strategy, version=version, symbol=symbol,
        source="SYNTHETIC_CONTRACT_TEST_ONLY", feature_as_of=now,
        observed_at=now, retrieved_at=now, data=data,
    ).as_dict()


def stock_entry(symbol, now, *, pass_filter=False):
    return evidence("stock_entry", STOCK_STRATEGY, STOCK_VERSION, symbol, now, {
        "price": "100", "next_ask": "100", "entry_limit": "101",
        "dollar_volumes_20": ["60000000"] * 20, "atr14": "5",
        "session_return": "-0.03" if pass_filter else "0",
        "session_vwap": "99", "sma50": "90", "earnings_sessions_away": 5,
        "hard_adverse_news": False, "thesis_broken": False,
        "thesis": "contract-test thesis", "invalidation": "contract-test invalidation",
    })


def option_entry(symbol, now, *, pass_filter=False):
    return evidence("option_entry", OPTION_STRATEGY, OPTION_VERSION, symbol, now, {
        "underlying_price": "500", "bid": "0.40", "ask": "0.41",
        "open_interest": 500, "volume": 100, "expiration": "2026-10-01",
        "strike": "500", "right": "CALL", "trend_3bar_bps": "30" if pass_filter else "0",
    })


def cycle(now=NOW, *, cycle_id="cycle-1", stale=False):
    observed = now - timedelta(minutes=6) if stale else now
    coverage = {
        "stock_history_sessions": 50, "stock_symbols": STOCKS,
        "stock_observed_at": observed.isoformat(), "earnings_symbols": STOCKS,
        "earnings_calendar_through": "2026-10-30", "option_underlyings": OPTIONS,
        "option_observed_at": now.isoformat(), "complete_option_chain": True,
        "news_lookback_seconds": 86400, "context_complete": True,
        "receipt_hashes": {name: "a" * 64 for name in (
            "direct_news", "earnings_calendar", "macro_calendar", "market_context",
            "option_chain", "sector_news", "stock_history", "stock_quotes",
        )},
    }
    unsigned = {
        "schema_version": "1.0", "cycle_id": cycle_id, "decision_at": now.isoformat(),
        "completed_session_date": None, "coverage": coverage,
        "stock_entries": [stock_entry(symbol, now, pass_filter=symbol == "AAOI") for symbol in STOCKS],
        "stock_management": [],
        "option_entries": [option_entry(symbol, now, pass_filter=symbol == "SPY") for symbol in OPTIONS],
        "option_management": [],
    }
    return {**unsigned, "cycle_hash": sha256_bytes(canonical(unsigned).encode())}


def rehash(raw):
    unsigned = {key: value for key, value in raw.items() if key != "cycle_hash"}
    raw["cycle_hash"] = sha256_bytes(canonical(unsigned).encode())
    return raw


class RuntimeTests(unittest.TestCase):
    def test_complete_cycle_fills_two_separate_paper_accounts_and_replays(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle()
            result = process_cycle(raw, Path(tmp))
            self.assertEqual(result["status"], "PAPER_CYCLE_COMPLETE")
            self.assertFalse(result["orders_enabled"])
            self.assertEqual(result["stock_account"]["deployed_cents"], 199800)
            self.assertEqual(result["option_account"]["deployed_cents"], 4200)
            self.assertEqual(len([e for e in result["events"] if "fill" in e]), 2)
            replay = process_cycle(raw, Path(tmp))
            self.assertTrue(replay["replay"])
            self.assertEqual(replay["stock_account"], result["stock_account"])

    def test_fresh_management_closes_at_frozen_targets_without_reentry(self):
        with tempfile.TemporaryDirectory() as tmp:
            first_raw = cycle()
            first = process_cycle(first_raw, Path(tmp))
            contract = next(event["contract"] for event in first["events"] if event["arm"] == "options" and "contract" in event)
            point = NOW + timedelta(minutes=1)
            second = cycle(point, cycle_id="cycle-2")
            second["stock_management"] = [evidence(
                "stock_management", STOCK_STRATEGY, STOCK_VERSION, "AAOI", point,
                {"price": "112", "thesis_broken": False},
            )]
            second["option_management"] = [evidence(
                "option_management", OPTION_STRATEGY, OPTION_VERSION, "SPY", point,
                {"contract": contract, "premium": "0.70", "sessions_held": 0,
                 "entry_evidence_hash": first_raw["option_entries"][1]["evidence_hash"],
                 "opened_at": NOW.isoformat(), "position_quantity": "1"},
            )]
            rehash(second)
            result = process_cycle(second, Path(tmp))
            closes = [event for event in result["events"] if "close" in event]
            self.assertEqual(len(closes), 2)
            self.assertEqual(result["stock_account"]["deployed_cents"], 0)
            self.assertEqual(result["option_account"]["deployed_cents"], 0)
            self.assertFalse(any("fill" in event for event in result["events"]))

    def test_stale_coverage_blocks_before_ledgers_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeBlocked, "older than five minutes"):
                process_cycle(cycle(stale=True), Path(tmp))
            self.assertFalse((Path(tmp) / "accounts").exists())

    def test_missing_receipt_and_unknown_earnings_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle(); raw["coverage"]["receipt_hashes"].pop("earnings_calendar"); rehash(raw)
            with self.assertRaisesRegex(RuntimeBlocked, "source receipts"):
                process_cycle(raw, Path(tmp))
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle()
            raw["stock_entries"][0] = evidence(
                "stock_entry", STOCK_STRATEGY, STOCK_VERSION, "AAOI", NOW,
                {**raw["stock_entries"][0]["data"], "earnings_sessions_away": None},
            )
            rehash(raw)
            with self.assertRaisesRegex(RuntimeBlocked, "earnings distance"):
                process_cycle(raw, Path(tmp))

    def test_management_exactly_covers_open_positions(self):
        with tempfile.TemporaryDirectory() as tmp:
            process_cycle(cycle(), Path(tmp))
            raw = cycle(NOW + timedelta(minutes=1), cycle_id="cycle-2")
            with self.assertRaisesRegex(RuntimeBlocked, "exactly cover open stock"):
                process_cycle(raw, Path(tmp))

    def test_cycle_id_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = cycle(); process_cycle(raw, Path(tmp))
            changed = cycle(NOW + timedelta(seconds=1), cycle_id="cycle-1")
            with self.assertRaisesRegex(RuntimeBlocked, "different input"):
                process_cycle(changed, Path(tmp))


if __name__ == "__main__":
    unittest.main()
