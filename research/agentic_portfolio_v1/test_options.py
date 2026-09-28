from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import tempfile
import unittest

from research.agentic_portfolio_v1.council import build_proposal, no_op_proposal, validate_council
from research.agentic_portfolio_v1.evidence import EvidencePacket
from research.agentic_portfolio_v1.options import STRATEGY, VERSION, OptionPlan, OptionShadowEngine
from research.agentic_portfolio_v1.risk import RiskLedger, RiskRejected


NOW = datetime(2026, 9, 14, 20, 0, tzinfo=timezone.utc)


def option_data(**updates):
    data = {
        "underlying_price": "500", "bid": "0.38", "ask": "0.40",
        "open_interest": 1000, "volume": 300, "expiration": "2026-10-01",
        "strike": "500", "right": "CALL", "trend_3bar_bps": "35",
    }
    data.update(updates)
    return data


def packet(data=None, *, observed_at=NOW - timedelta(seconds=10), retrieved_at=NOW - timedelta(seconds=2)):
    return EvidencePacket.build(
        kind="option_entry", strategy=STRATEGY, version=VERSION, symbol="SPY", source="SYNTHETIC_OPTION_TEST",
        feature_as_of=observed_at - timedelta(seconds=1), observed_at=observed_at, retrieved_at=retrieved_at,
        data=data or option_data(),
    )


def management_packet(plan, premium, sessions_held, decision_at, *, completed_session_dates=None):
    data = {"contract": plan.contract, "premium": str(premium), "sessions_held": sessions_held,
            "entry_evidence_hash": plan.evidence_hash, "opened_at": plan.opened_at.isoformat(),
            "position_quantity": "1"}
    if completed_session_dates is not None:
        data["completed_session_dates"] = completed_session_dates
    feature_as_of = max(plan.opened_at, decision_at - timedelta(seconds=3))
    observed_at = max(feature_as_of, decision_at - timedelta(seconds=2))
    retrieved_at = max(observed_at, decision_at - timedelta(seconds=1))
    return EvidencePacket.build(
        kind="option_management", strategy=STRATEGY, version=VERSION, symbol=plan.contract.split(":")[0],
        source="SYNTHETIC_OPTION_MANAGEMENT", feature_as_of=feature_as_of,
        observed_at=observed_at, retrieved_at=retrieved_at,
        data=data,
    )


class OptionEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = RiskLedger(f"{self.tmp.name}/options.sqlite", "options-1000", Decimal("1000"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_deterministic_baseline_creates_one_contract_intent(self):
        result = OptionShadowEngine(self.ledger).evaluate_entry(packet(), NOW, "opt-1")
        self.assertEqual(result.action, "PAPER_ENTRY_INTENT")
        self.assertEqual(result.details["contracts"], 1)
        self.assertEqual(result.details["contractual_loss"], "41.65")
        self.assertTrue(result.paper_only and result.no_order)

    def test_contract_indivisibility_rejects_premium_over_budget(self):
        result = OptionShadowEngine(self.ledger).evaluate_entry(packet(option_data(ask="0.60", bid="0.58")), NOW, "opt-1")
        self.assertEqual(result.action, "ABSTAIN")
        self.assertIn("5%", " ".join(result.reasons))
        self.assertIn("indivisible", result.details["budget_note"])

    def test_neutral_baseline_abstains(self):
        result = OptionShadowEngine(self.ledger).evaluate_entry(packet(option_data(trend_3bar_bps="0")), NOW, "opt-1")
        self.assertEqual(result.action, "ABSTAIN")

    def test_put_baseline(self):
        result = OptionShadowEngine(self.ledger).evaluate_entry(
            packet(option_data(right="PUT", trend_3bar_bps="-35")), NOW, "opt-1"
        )
        self.assertEqual(result.action, "PAPER_ENTRY_INTENT")

    def test_wrong_right_conflicts_with_signal(self):
        result = OptionShadowEngine(self.ledger).evaluate_entry(packet(option_data(right="PUT", trend_3bar_bps="35")), NOW, "opt-1")
        self.assertEqual(result.action, "ABSTAIN")

    def test_dte_strike_right_and_liquidity_filters(self):
        cases = {
            "dte_low": {"expiration": "2026-09-20"},
            "dte_high": {"expiration": "2026-11-01"},
            "strike": {"strike": "550"},
            "right": {"right": "SIDEWAYS"},
            "spread": {"bid": "0.20", "ask": "0.40"},
            "open_interest": {"open_interest": 499},
            "volume": {"volume": 99},
        }
        for index, (name, updates) in enumerate(cases.items()):
            with self.subTest(name=name):
                result = OptionShadowEngine(self.ledger).evaluate_entry(packet(option_data(**updates)), NOW, f"bad-{index}")
                self.assertEqual(result.action, "ABSTAIN")

    def test_stale_option_quote_abstains(self):
        stale = packet(observed_at=NOW - timedelta(seconds=31), retrieved_at=NOW - timedelta(seconds=2))
        self.assertEqual(OptionShadowEngine(self.ledger).evaluate_entry(stale, NOW, "stale").action, "ABSTAIN")

    def test_only_one_open_position(self):
        first = OptionShadowEngine(self.ledger).evaluate_entry(packet(), NOW, "first")
        self.ledger.record_fill(
            reservation_id=first.details["reservation"]["reservation_id"], quantity=Decimal("1"),
            price=Decimal(first.details["modeled_entry_premium"]), costs=Decimal("0.65"), filled_at=NOW,
        )
        later = NOW + timedelta(days=1)
        fresh = packet(observed_at=later - timedelta(seconds=10), retrieved_at=later - timedelta(seconds=2))
        second = OptionShadowEngine(self.ledger).evaluate_entry(fresh, later, "second")
        self.assertEqual(second.action, "ABSTAIN")
        self.assertIn("one-position", second.reasons[0])

    def test_second_pending_intent_is_rejected_but_same_key_replays(self):
        engine = OptionShadowEngine(self.ledger)
        first = engine.evaluate_entry(packet(), NOW, "first")
        replay = engine.evaluate_entry(packet(), NOW, "first")
        self.assertEqual(replay.action, "ABSTAIN")
        self.assertEqual(first.details["reservation"]["reservation_id"], replay.details["reservation"]["reservation_id"])
        other = engine.evaluate_entry(packet(), NOW, "other")
        self.assertEqual(other.action, "ABSTAIN")
        self.assertIn("one-position", other.reasons[0])

    def test_option_management_stop_target_and_time(self):
        engine = OptionShadowEngine(self.ledger)
        entry_packet = packet()
        entry = engine.evaluate_entry(entry_packet, NOW, "managed")
        contract = entry.symbol
        premium = Decimal(entry.details["modeled_entry_premium"])
        self.ledger.record_fill(reservation_id=entry.details["reservation"]["reservation_id"], quantity=Decimal("1"),
                                price=premium, costs=Decimal("0.65"), filled_at=NOW, event_id="managed-fill")
        plan = OptionPlan(contract, premium, NOW, NOW.date(), premium * Decimal("0.70"),
                          premium * Decimal("1.50"), entry_packet.evidence_hash)
        same_day = NOW
        day_two = NOW + timedelta(days=2)
        self.assertEqual(engine.evaluate_position(plan, management_packet(plan, plan.stop_premium, 0, same_day), same_day).action,
                         "PAPER_EXIT_INTENT")
        self.assertEqual(engine.evaluate_position(plan, management_packet(plan, plan.target_premium, 0, same_day), same_day).action,
                         "PAPER_EXIT_INTENT")
        self.assertEqual(engine.evaluate_position(plan, management_packet(plan, premium, 2, day_two), day_two).action,
                         "PAPER_EXIT_INTENT")
        self.assertEqual(engine.evaluate_position(plan, management_packet(plan, premium, 1, day_two), day_two).action,
                         "PAPER_EXIT_INTENT")
        day_one = NOW + timedelta(days=1)
        self.assertEqual(engine.evaluate_position(plan, management_packet(plan, premium, 1, day_one), day_one).action, "HOLD")
        bad = management_packet(plan, premium, 1, day_two)
        bad.data["contract"] = "QQQ:2099-01-01:PUT:1"
        self.assertEqual(engine.evaluate_position(plan, bad, day_two).action, "ABSTAIN")

    def test_forged_plan_and_reset_clock_cannot_bypass_management(self):
        engine = OptionShadowEngine(self.ledger)
        entry_packet = packet()
        entry = engine.evaluate_entry(entry_packet, NOW, "bound")
        self.ledger.record_fill(reservation_id=entry.details["reservation"]["reservation_id"], quantity=Decimal("1"),
                                price=Decimal("0.41"), costs=Decimal("0.65"), filled_at=NOW, event_id="bound-fill")
        plan = engine.plan_from_fill(entry.symbol)
        forged = OptionPlan(plan.contract, Decimal("999"), plan.opened_at, plan.entry_session,
                            Decimal("0"), Decimal("99999"), "f" * 64)
        self.assertEqual(engine.evaluate_position(forged, management_packet(forged, "0.10", 0, NOW), NOW).action,
                         "ABSTAIN")
        day_two = NOW + timedelta(days=2)
        reset = engine.evaluate_position(plan, management_packet(plan, plan.entry_premium, 0, day_two), day_two)
        self.assertEqual(reset.action, "PAPER_EXIT_INTENT")
        expired = NOW + timedelta(days=30)
        self.assertEqual(
            engine.evaluate_position(plan, management_packet(plan, plan.entry_premium, 0, expired), expired).action,
            "PAPER_EXIT_INTENT",
        )

    def test_management_calendar_must_match_durable_weekday_clock(self):
        engine = OptionShadowEngine(self.ledger)
        entry_packet = packet()
        entry = engine.evaluate_entry(entry_packet, NOW, "calendar-bound")
        self.ledger.record_fill(
            reservation_id=entry.details["reservation"]["reservation_id"], quantity=Decimal("1"),
            price=Decimal("0.41"), costs=Decimal("0.65"), filled_at=NOW,
            event_id="calendar-bound-fill",
        )
        plan = engine.plan_from_fill(entry.symbol)
        day_two = NOW + timedelta(days=2)
        forged = management_packet(plan, plan.entry_premium, 0, day_two, completed_session_dates=[])
        self.assertEqual(engine.evaluate_position(plan, forged, day_two).action, "ABSTAIN")
        verified = management_packet(
            plan, plan.entry_premium, 2, day_two,
            completed_session_dates=[
                (NOW + timedelta(days=1)).date().isoformat(),
                (NOW + timedelta(days=2)).date().isoformat(),
            ],
        )
        self.assertEqual(engine.evaluate_position(plan, verified, day_two).action, "PAPER_EXIT_INTENT")

    def test_malformed_option_fields_fail_closed(self):
        malformed = packet(option_data(right=[]))
        self.assertEqual(OptionShadowEngine(self.ledger).evaluate_entry(malformed, NOW, "malformed").action, "ABSTAIN")

    def test_closed_reservation_replay_never_creates_intent(self):
        engine = OptionShadowEngine(self.ledger)
        first = engine.evaluate_entry(packet(), NOW, "released")
        self.ledger.release(first.details["reservation"]["reservation_id"])
        replay = engine.evaluate_entry(packet(), NOW, "released")
        self.assertEqual(replay.action, "ABSTAIN")
        self.assertIn("replay/status", replay.reasons[0])

    def test_management_cannot_predate_fill_and_equal_boundary_is_allowed(self):
        engine = OptionShadowEngine(self.ledger)
        entry = engine.evaluate_entry(packet(), NOW, "causal")
        self.ledger.record_fill(
            reservation_id=entry.details["reservation"]["reservation_id"], quantity=Decimal("1"),
            price=Decimal("0.41"), costs=Decimal("0.65"), filled_at=NOW,
            event_id="causal-fill",
        )
        plan = engine.plan_from_fill(entry.symbol)
        before = NOW - timedelta(seconds=1)
        pre_open = EvidencePacket.build(
            kind="option_management", strategy=STRATEGY, version=VERSION, symbol="SPY",
            source="SYNTHETIC_OPTION_MANAGEMENT", feature_as_of=before,
            observed_at=before, retrieved_at=before,
            data={"contract": plan.contract, "premium": str(plan.entry_premium),
                  "sessions_held": 0, "entry_evidence_hash": plan.evidence_hash,
                  "opened_at": plan.opened_at.isoformat(), "position_quantity": "1"},
        )
        self.assertEqual(engine.evaluate_position(plan, pre_open, NOW).action, "ABSTAIN")
        self.assertEqual(
            engine.evaluate_position(plan, management_packet(plan, plan.entry_premium, 0, NOW), NOW).action,
            "HOLD",
        )

    def test_foreign_and_missing_origin_versions_fail_across_reopen_and_replay(self):
        contract = "SPY:2026-10-01:CALL:500"
        for origin_version in ("99.0.0", "UNVERSIONED"):
            with self.subTest(origin_version=origin_version), tempfile.TemporaryDirectory() as tmp:
                path = f"{tmp}/option-version.sqlite"
                ledger = RiskLedger(path, "option-version", Decimal("1000"))
                reservation = ledger.reserve(
                    idempotency_key="versioned", strategy=STRATEGY,
                    strategy_version=origin_version, symbol=contract, asset_type="OPTION",
                    notional=Decimal("41.65"), contractual_loss=Decimal("41.65"), now=NOW,
                    quantity=Decimal("1"), evidence_hash="a" * 64,
                )
                ledger.record_fill(
                    reservation_id=reservation["reservation_id"], quantity=Decimal("1"),
                    price=Decimal("0.41"), costs=Decimal("0.65"), filled_at=NOW,
                    event_id="version-fill",
                )
                reopened = RiskLedger(path, "option-version", Decimal("1000"))
                with self.assertRaisesRegex(RiskRejected, "strategy version"):
                    OptionShadowEngine(reopened).plan_from_fill(contract)

            with self.subTest(replay_version=origin_version), tempfile.TemporaryDirectory() as tmp:
                ledger = RiskLedger(f"{tmp}/option-replay.sqlite", "option-replay", Decimal("1000"))
                ledger.reserve(
                    idempotency_key="same-key", strategy=STRATEGY,
                    strategy_version=origin_version, symbol=contract, asset_type="OPTION",
                    notional=Decimal("41.65"), contractual_loss=Decimal("41.65"), now=NOW,
                    quantity=Decimal("1"), evidence_hash=packet().evidence_hash,
                )
                result = OptionShadowEngine(ledger).evaluate_entry(packet(), NOW, "same-key")
                self.assertEqual(result.action, "ABSTAIN")
                self.assertIn("different input", " ".join(result.reasons))


class CouncilTests(unittest.TestCase):
    def proposals(self, evidence, critic_action="AGREE", critic_strike="500"):
        analyst = build_proposal(
            role="analyst", producer="synthetic-analyst", action="CALL", symbol="SPY", right="CALL",
            expiration="2026-10-01", strike="500", evidence=evidence,
            grounded_fields=["trend_3bar_bps"], observed_at=NOW,
        )
        critic = build_proposal(
            role="critic", producer="synthetic-critic", action=critic_action, symbol="SPY", right="CALL",
            expiration="2026-10-01", strike=critic_strike, evidence=evidence,
            grounded_fields=["trend_3bar_bps"], observed_at=NOW,
        )
        return analyst, critic

    def test_agreement_passes_deterministic_validator(self):
        evidence = packet()
        analyst, critic = self.proposals(evidence)
        self.assertTrue(validate_council(analyst, critic, evidence, NOW).accepted)

    def test_disagreement_abstains(self):
        evidence = packet()
        analyst, critic = self.proposals(evidence, critic_action="DISAGREE")
        result = validate_council(analyst, critic, evidence, NOW)
        self.assertFalse(result.accepted)
        self.assertEqual(result.action, "ABSTAIN")

    def test_conflicting_instrument_abstains(self):
        evidence = packet()
        analyst, critic = self.proposals(evidence, critic_strike="501")
        self.assertFalse(validate_council(analyst, critic, evidence, NOW).accepted)

    def test_council_cannot_jointly_substitute_a_different_contract(self):
        evidence = packet()
        analyst = build_proposal(
            role="analyst", producer="a", action="CALL", symbol="SPY", right="CALL",
            expiration="2030-01-01", strike="9999", evidence=evidence,
            grounded_fields=["trend_3bar_bps"], observed_at=NOW,
        )
        critic = build_proposal(
            role="critic", producer="c", action="AGREE", symbol="SPY", right="CALL",
            expiration="2030-01-01", strike="9999", evidence=evidence,
            grounded_fields=["trend_3bar_bps"], observed_at=NOW,
        )
        self.assertFalse(validate_council(analyst, critic, evidence, NOW).accepted)

    def test_malformed_or_tampered_proposal_abstains(self):
        evidence = packet()
        analyst, critic = self.proposals(evidence)
        del analyst["grounded_fields"]
        self.assertFalse(validate_council(analyst, critic, evidence, NOW).accepted)
        analyst, critic = self.proposals(evidence)
        analyst["action"] = "PUT"
        self.assertFalse(validate_council(analyst, critic, evidence, NOW).accepted)

    def test_unavailable_grounding_abstains(self):
        evidence = packet()
        analyst, critic = self.proposals(evidence)
        analyst = build_proposal(
            role="analyst", producer="a", action="CALL", symbol="SPY", right="CALL",
            expiration="2026-10-01", strike="500", evidence=evidence,
            grounded_fields=["imaginary_field"], observed_at=NOW,
        )
        self.assertFalse(validate_council(analyst, critic, evidence, NOW).accepted)

    def test_noop_and_missing_agents_abstain(self):
        evidence = packet()
        noop = no_op_proposal(evidence, NOW)
        self.assertFalse(validate_council(noop, None, evidence, NOW).accepted)
        with tempfile.TemporaryDirectory() as tmp:
            result = OptionShadowEngine(
                RiskLedger(f"{tmp}/council.sqlite", "council-1000", Decimal("1000")), mode="council"
            ).evaluate_entry(evidence, NOW, "none", analyst=None, critic=None)
            self.assertEqual(result.action, "ABSTAIN")

    def test_council_mode_can_create_intent_only_after_validation(self):
        evidence = packet()
        analyst, critic = self.proposals(evidence)
        with tempfile.TemporaryDirectory() as tmp:
            engine = OptionShadowEngine(RiskLedger(f"{tmp}/c.sqlite", "council-1000", Decimal("1000")), mode="council")
            self.assertEqual(engine.evaluate_entry(evidence, NOW, "valid", analyst=analyst, critic=critic).action,
                             "PAPER_ENTRY_INTENT")

    def test_same_producer_cannot_fill_both_roles(self):
        evidence = packet()
        analyst, _ = self.proposals(evidence)
        critic = build_proposal(
            role="critic", producer="synthetic-analyst", action="AGREE", symbol="SPY", right="CALL",
            expiration="2026-10-01", strike="500", evidence=evidence,
            grounded_fields=["trend_3bar_bps"], observed_at=NOW,
        )
        self.assertFalse(validate_council(analyst, critic, evidence, NOW).accepted)


if __name__ == "__main__":
    unittest.main()
