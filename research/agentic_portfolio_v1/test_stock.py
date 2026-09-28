from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from research.agentic_portfolio_v1.common import ValidationError
from research.agentic_portfolio_v1.config import load_config
from research.agentic_portfolio_v1.evidence import EvidencePacket
from research.agentic_portfolio_v1.risk import RiskLedger, RiskRejected
from research.agentic_portfolio_v1.stock import (
    STRATEGY, VERSION, CostModel, StockPlan, StockSwingEngine,
    entry_cost, net_return_at, target_for_net_return,
)


NOW = datetime(2026, 9, 14, 20, 0, tzinfo=timezone.utc)


def stock_data(**updates):
    data = {
        "price": "100", "next_ask": "100.05", "entry_limit": "100.10",
        "dollar_volumes_20": ["60000000"] * 20, "atr14": "5",
        "session_return": "-0.04", "session_vwap": "99", "sma50": "95",
        "earnings_sessions_away": 8, "hard_adverse_news": False, "thesis_broken": False,
        "thesis": "reversal with trend intact", "invalidation": "explicit thesis break",
    }
    data.update(updates)
    return data


def packet(data=None, *, kind="stock_entry", observed_at=NOW - timedelta(seconds=30),
           retrieved_at=NOW - timedelta(seconds=10), feature_as_of=NOW - timedelta(minutes=1)):
    return EvidencePacket.build(
        kind=kind, strategy=STRATEGY, version=VERSION, symbol="LITE", source="SYNTHETIC_TEST",
        feature_as_of=feature_as_of, observed_at=observed_at, retrieved_at=retrieved_at,
        data=data or stock_data(),
    )


class EvidenceTests(unittest.TestCase):
    def test_hash_tamper_is_rejected(self):
        raw = packet().as_dict()
        raw["data"]["price"] = "101"
        with self.assertRaisesRegex(ValidationError, "hash mismatch"):
            EvidencePacket.from_dict(raw)

    def test_mutation_after_construction_is_detected(self):
        built = packet()
        built.data["price"] = "101"
        with self.assertRaisesRegex(ValidationError, "hash mismatch"):
            built.validate_at(NOW, timedelta(minutes=5))

    def test_future_feature_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, "future-data leakage"):
            EvidencePacket.build(
                kind="stock_entry", strategy=STRATEGY, version=VERSION, symbol="LITE", source="TEST",
                feature_as_of=NOW, observed_at=NOW - timedelta(seconds=1), retrieved_at=NOW,
                data=stock_data(),
            )

    def test_retrieval_after_decision_is_rejected(self):
        p = packet(retrieved_at=NOW + timedelta(seconds=1))
        with self.assertRaisesRegex(ValidationError, "retrieved after decision"):
            p.validate_at(NOW, timedelta(minutes=5))

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, "timezone-aware"):
            EvidencePacket.build(
                kind="stock_entry", strategy=STRATEGY, version=VERSION, symbol="LITE", source="TEST",
                feature_as_of=datetime(2026, 1, 1), observed_at=NOW, retrieved_at=NOW, data=stock_data(),
            )


class StockMathTests(unittest.TestCase):
    def test_target_rounding_guarantees_ten_percent_net(self):
        costs = CostModel(entry_bps=Decimal("10"), exit_bps=Decimal("10"),
                          entry_fixed=Decimal("0.17"), exit_fixed=Decimal("0.23"))
        qty, fill = Decimal("1.234567"), Decimal("100.03")
        debit = qty * fill + entry_cost(qty, fill, costs)
        target = target_for_net_return(quantity=qty, actual_entry_debit=debit, costs=costs)
        self.assertGreaterEqual(net_return_at(target, qty, debit, costs), Decimal("0.10"))
        self.assertLess(net_return_at(target - Decimal("0.01"), qty, debit, costs), Decimal("0.10"))

    def test_nonfinite_math_is_rejected(self):
        with self.assertRaises(ValidationError):
            target_for_net_return(quantity=Decimal("NaN"), actual_entry_debit=Decimal("100"), costs=CostModel())


class StockEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = RiskLedger(f"{self.tmp.name}/stock.sqlite", "stock-1000", Decimal("1000"))
        self.engine = StockSwingEngine(self.ledger)

    def tearDown(self):
        self.tmp.cleanup()

    def test_qualifying_signal_creates_fractional_paper_intent(self):
        result = self.engine.evaluate_entry(packet(), NOW, "stock-1")
        self.assertEqual(result.action, "PAPER_ENTRY_INTENT")
        self.assertLessEqual(Decimal(result.details["modeled_entry_debit"]), Decimal("200"))
        self.assertNotEqual(Decimal(result.details["quantity"]), Decimal(int(Decimal(result.details["quantity"]))))
        self.assertTrue(result.paper_only and result.no_order)

    def test_no_averaging_down_when_position_exists(self):
        result = self.engine.evaluate_entry(packet(), NOW, "stock-1")
        reservation = result.details["reservation"]["reservation_id"]
        quantity = Decimal(result.details["quantity"])
        price = Decimal(result.details["modeled_entry_price"])
        self.ledger.record_fill(
            reservation_id=reservation, quantity=quantity, price=price,
            costs=entry_cost(quantity, price, self.engine.costs), filled_at=NOW,
        )
        later = NOW + timedelta(days=1)
        fresh = packet(observed_at=later - timedelta(seconds=30), retrieved_at=later - timedelta(seconds=10),
                       feature_as_of=later - timedelta(minutes=1))
        second = self.engine.evaluate_entry(fresh, later, "stock-2")
        self.assertEqual(second.action, "ABSTAIN")
        self.assertIn("averaging down", " ".join(second.reasons))

    def test_partial_fills_recalculate_target_from_durable_actual_basis(self):
        result = self.engine.evaluate_entry(packet(), NOW, "stock-1")
        reservation = result.details["reservation"]["reservation_id"]
        total_qty = Decimal(result.details["quantity"])
        half = (total_qty / 2).quantize(Decimal("0.000001"))
        self.ledger.record_fill(reservation_id=reservation, quantity=half, price=Decimal("99"),
                                costs=Decimal("0.10"), filled_at=NOW)
        plan = self.engine.plan_from_fills(
            symbol="LITE", opened_at=NOW, thesis="t", invalidation="i", evidence_hash=packet().evidence_hash
        )
        self.assertEqual(plan.actual_entry_debit, Decimal(self.ledger.get_position(STRATEGY, "LITE")["basis_cents"]) / 100)
        self.assertGreaterEqual(net_return_at(plan.target_price, plan.quantity, plan.actual_entry_debit, self.engine.costs),
                                Decimal("0.10"))

    def test_target_survives_ledger_floor_to_cent_exit_credit(self):
        reservation = self.ledger.reserve(
            idempotency_key="tiny", strategy=STRATEGY, symbol="LITE", asset_type="EQUITY",
            notional=Decimal("1.01"), contractual_loss=Decimal("1.01"), now=NOW,
            strategy_version=VERSION, evidence_hash="a" * 64,
        )["reservation_id"]
        self.ledger.record_fill(reservation_id=reservation, quantity=Decimal("0.001"), price=Decimal("1010"),
                                costs=Decimal("0"), filled_at=NOW, event_id="tiny-fill")
        plan = self.engine.plan_from_fills(
            symbol="LITE", opened_at=NOW, thesis="t", invalidation="i", evidence_hash="a" * 64,
        )
        fee = plan.quantity * plan.target_price * Decimal("0.001")
        closed = self.ledger.close_position(
            strategy=STRATEGY, symbol="LITE", quantity=plan.quantity, price=plan.target_price,
            costs=fee, closed_at=NOW, reason="NET10", event_id="tiny-close",
        )
        actual_credit = Decimal(closed["net_proceeds_cents"]) / 100
        self.assertGreaterEqual(actual_credit, plan.actual_entry_debit * Decimal("1.10"))

    def test_all_frozen_entry_filters_fail_closed(self):
        cases = {
            "price": {"price": "9", "next_ask": "9", "entry_limit": "9.1"},
            "liquidity": {"dollar_volumes_20": ["1"] * 20},
            "atr_low": {"atr14": "2"},
            "atr_high": {"atr14": "11"},
            "return": {"session_return": "-0.01"},
            "vwap": {"session_vwap": "101"},
            "sma": {"sma50": "101"},
            "earnings": {"earnings_sessions_away": 3},
            "news": {"hard_adverse_news": True},
            "thesis": {"thesis_broken": True},
            "limit": {"next_ask": "101", "entry_limit": "100"},
        }
        for index, (name, updates) in enumerate(cases.items()):
            with self.subTest(name=name):
                result = self.engine.evaluate_entry(packet(stock_data(**updates)), NOW, f"bad-{index}")
                self.assertEqual(result.action, "ABSTAIN")

    def test_stale_evidence_abstains(self):
        stale = packet(observed_at=NOW - timedelta(minutes=6), retrieved_at=NOW - timedelta(minutes=5),
                       feature_as_of=NOW - timedelta(minutes=7))
        self.assertEqual(self.engine.evaluate_entry(stale, NOW, "stale").action, "ABSTAIN")

    def _plan(self):
        if not self.ledger.has_position(STRATEGY, "LITE"):
            entry_packet = packet()
            intent = self.engine.evaluate_entry(entry_packet, NOW, "management-entry")
            quantity = Decimal(intent.details["quantity"])
            price = Decimal(intent.details["modeled_entry_price"])
            self.ledger.record_fill(
                reservation_id=intent.details["reservation"]["reservation_id"], quantity=quantity,
                price=price, costs=entry_cost(quantity, price, self.engine.costs), filled_at=NOW,
                event_id="management-fill",
            )
        return self.engine.plan_from_fills(
            symbol="LITE", opened_at=NOW, thesis="thesis", invalidation="broken",
            evidence_hash=packet().evidence_hash,
        )

    def _management(self, price="95", thesis=False, *, decision_at=NOW):
        feature_as_of = max(NOW, decision_at - timedelta(seconds=3))
        observed_at = max(feature_as_of, decision_at - timedelta(seconds=2))
        retrieved_at = max(observed_at, decision_at - timedelta(seconds=1))
        return EvidencePacket.build(
            kind="stock_management", strategy=STRATEGY, version=VERSION, symbol="LITE",
            source="SYNTHETIC_TEST", feature_as_of=feature_as_of,
            observed_at=observed_at, retrieved_at=retrieved_at,
            data={"price": price, "thesis_broken": thesis},
        )

    @staticmethod
    def _after_weekdays(count):
        cursor = NOW
        found = 0
        while found < count:
            cursor += timedelta(days=1)
            if cursor.weekday() < 5:
                found += 1
        return cursor

    def test_ten_percent_decline_requires_review_not_exit(self):
        result = self.engine.evaluate_position(self._plan(), self._management("90"), sessions_held=5, decision_at=NOW)
        self.assertEqual(result.action, "REVIEW_REQUIRED")
        self.assertIn("not an automatic stop", " ".join(result.reasons))

    def test_twenty_one_session_review_is_not_exit(self):
        decision = self._after_weekdays(21)
        result = self.engine.evaluate_position(
            self._plan(), self._management(decision_at=decision), sessions_held=0, decision_at=decision,
        )
        self.assertEqual(result.action, "REVIEW_REQUIRED")

    def test_missing_review_and_absolute_hold_exit(self):
        decision_42 = self._after_weekdays(42)
        plan = self._plan()
        self.assertEqual(self.engine.evaluate_position(
            plan, self._management(decision_at=decision_42), sessions_held=0, decision_at=decision_42,
        ).action, "PAPER_EXIT_INTENT")
        reviewed = self._after_weekdays(21)
        self.assertEqual(self.engine.evaluate_position(
            plan, self._management(decision_at=decision_42), sessions_held=0,
            decision_at=decision_42, reunderwritten_at=reviewed,
        ).action, "HOLD")
        decision_126 = self._after_weekdays(126)
        self.assertEqual(self.engine.evaluate_position(
            plan, self._management(decision_at=decision_126), sessions_held=0,
            decision_at=decision_126, reunderwritten_at=reviewed,
        ).action, "PAPER_EXIT_INTENT")

    def test_thesis_break_and_target_exit(self):
        self.assertEqual(self.engine.evaluate_position(self._plan(), self._management(thesis=True), sessions_held=1,
                                                       decision_at=NOW).action, "PAPER_EXIT_INTENT")
        self.assertEqual(self.engine.evaluate_position(self._plan(), self._management("111"), sessions_held=1,
                                                       decision_at=NOW).action, "PAPER_EXIT_INTENT")

    def test_wrong_management_version_and_future_review_abstain(self):
        plan = self._plan()
        wrong = EvidencePacket.build(
            kind="stock_management", strategy=STRATEGY, version="wrong", symbol="LITE", source="TEST",
            feature_as_of=NOW - timedelta(seconds=2), observed_at=NOW - timedelta(seconds=1), retrieved_at=NOW,
            data={"price": "95", "thesis_broken": False},
        )
        self.assertEqual(self.engine.evaluate_position(plan, wrong, sessions_held=42, decision_at=NOW).action,
                         "ABSTAIN")
        self.assertEqual(self.engine.evaluate_position(plan, self._management(), sessions_held=42,
                                                       decision_at=NOW, reunderwritten_at=NOW + timedelta(days=1)).action,
                         "ABSTAIN")

    def test_forged_plan_and_caller_session_reset_are_rejected_or_ignored(self):
        actual = self._plan()
        forged = StockPlan(
            actual.symbol, actual.quantity, Decimal("999"), Decimal("999"), Decimal("9999"),
            actual.opened_at, actual.thesis, actual.invalidation, "f" * 64,
        )
        self.assertEqual(
            self.engine.evaluate_position(forged, self._management(), sessions_held=0, decision_at=NOW).action,
            "ABSTAIN",
        )
        far = self._after_weekdays(126)
        result = self.engine.evaluate_position(
            actual, self._management(decision_at=far), sessions_held=0, decision_at=far,
            reunderwritten_at=self._after_weekdays(21),
        )
        self.assertEqual(result.action, "PAPER_EXIT_INTENT")
        self.assertEqual(result.details["sessions_held"], 126)

    def test_management_cannot_predate_fill_and_equal_boundary_is_allowed(self):
        plan = self._plan()
        before = NOW - timedelta(seconds=1)
        pre_open = EvidencePacket.build(
            kind="stock_management", strategy=STRATEGY, version=VERSION, symbol="LITE",
            source="SYNTHETIC_TEST", feature_as_of=before, observed_at=before,
            retrieved_at=before, data={"price": "95", "thesis_broken": False},
        )
        self.assertEqual(
            self.engine.evaluate_position(plan, pre_open, sessions_held=0, decision_at=NOW).action,
            "ABSTAIN",
        )
        self.assertEqual(
            self.engine.evaluate_position(
                plan, self._management(decision_at=NOW), sessions_held=0, decision_at=NOW,
            ).action,
            "HOLD",
        )

    def test_management_must_follow_latest_partial_fill(self):
        reservation = self.ledger.reserve(
            idempotency_key="partial-causal", strategy=STRATEGY, strategy_version=VERSION,
            symbol="LITE", asset_type="EQUITY", notional=Decimal("200"),
            contractual_loss=Decimal("200"), now=NOW, quantity=Decimal("2"),
            evidence_hash="a" * 64,
        )
        self.ledger.record_fill(
            reservation_id=reservation["reservation_id"], quantity=Decimal("1"),
            price=Decimal("50"), costs=Decimal("0"), filled_at=NOW, event_id="partial-first",
        )
        latest = NOW + timedelta(minutes=1)
        self.ledger.record_fill(
            reservation_id=reservation["reservation_id"], quantity=Decimal("1"),
            price=Decimal("50"), costs=Decimal("0"), filled_at=latest, event_id="partial-second",
        )
        plan = self.engine.plan_from_fills(
            symbol="LITE", opened_at=NOW, thesis="t", invalidation="i", evidence_hash="a" * 64,
        )
        stale_for_position = NOW + timedelta(seconds=30)
        before_latest_fill = EvidencePacket.build(
            kind="stock_management", strategy=STRATEGY, version=VERSION, symbol="LITE",
            source="SYNTHETIC_TEST", feature_as_of=stale_for_position,
            observed_at=stale_for_position, retrieved_at=stale_for_position,
            data={"price": "50", "thesis_broken": False},
        )
        self.assertEqual(
            self.engine.evaluate_position(
                plan, before_latest_fill, sessions_held=0, decision_at=latest,
            ).action,
            "ABSTAIN",
        )
        at_latest_fill = EvidencePacket.build(
            kind="stock_management", strategy=STRATEGY, version=VERSION, symbol="LITE",
            source="SYNTHETIC_TEST", feature_as_of=latest, observed_at=latest,
            retrieved_at=latest, data={"price": "50", "thesis_broken": False},
        )
        self.assertEqual(
            self.engine.evaluate_position(plan, at_latest_fill, sessions_held=0, decision_at=latest).action,
            "HOLD",
        )

    def test_foreign_and_missing_origin_versions_fail_across_reopen_and_replay(self):
        for origin_version in ("99.0.0", "UNVERSIONED"):
            with self.subTest(origin_version=origin_version), tempfile.TemporaryDirectory() as tmp:
                path = f"{tmp}/stock-version.sqlite"
                ledger = RiskLedger(path, "stock-version", Decimal("1000"))
                reservation = ledger.reserve(
                    idempotency_key="versioned", strategy=STRATEGY,
                    strategy_version=origin_version, symbol="LITE", asset_type="EQUITY",
                    notional=Decimal("100"), contractual_loss=Decimal("100"), now=NOW,
                    quantity=Decimal("1"), evidence_hash="a" * 64,
                )
                ledger.record_fill(
                    reservation_id=reservation["reservation_id"], quantity=Decimal("1"),
                    price=Decimal("100"), costs=Decimal("0"), filled_at=NOW,
                    event_id="version-fill",
                )
                reopened = RiskLedger(path, "stock-version", Decimal("1000"))
                with self.assertRaisesRegex(RiskRejected, "strategy/version"):
                    StockSwingEngine(reopened).plan_from_fills(
                        symbol="LITE", opened_at=NOW, thesis="t", invalidation="i",
                        evidence_hash="a" * 64,
                    )

            with self.subTest(replay_version=origin_version), tempfile.TemporaryDirectory() as tmp:
                ledger = RiskLedger(f"{tmp}/stock-replay.sqlite", "stock-replay", Decimal("1000"))
                ledger.reserve(
                    idempotency_key="same-key", strategy=STRATEGY,
                    strategy_version=origin_version, symbol="LITE", asset_type="EQUITY",
                    notional=Decimal("100"), contractual_loss=Decimal("100"), now=NOW,
                    quantity=Decimal("1"), evidence_hash=packet().evidence_hash,
                )
                result = StockSwingEngine(ledger).evaluate_entry(packet(), NOW, "same-key")
                self.assertEqual(result.action, "ABSTAIN")
                self.assertIn("different input", " ".join(result.reasons))


class ConfigTests(unittest.TestCase):
    def test_orders_enabled_is_false(self):
        self.assertIs(load_config()["orders_enabled"], False)

    def test_config_cannot_enable_orders(self):
        config = load_config()
        config["orders_enabled"] = True
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.json"
            target.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "immutable false"):
                load_config(target)


if __name__ == "__main__":
    unittest.main()
