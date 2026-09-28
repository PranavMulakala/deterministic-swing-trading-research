"""Offline accounting and fail-closed boundary regressions; no broker calls."""
import copy
from decimal import Decimal
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from trial_budget import assess, load_proposal


def snapshot(**updates):
    value = {
        "day_start_equity_usd": 5000,
        "marked_equity_usd": 5000,
        "high_water_equity_usd": 5000,
        "closed_trade_net_pnls_usd": [],
        "position_contracts": 0,
        "open_position_gross_pnl_usd": 0,
        "open_position_paid_entry_fees_usd": 0,
        "open_position_unpaid_exit_fee_reserve_usd": 0,
        "entry_attempts_today": 0,
        "completed_sessions": 0,
        "pending_entry_contracts": 0,
        "instrument_root": "MNQ",
        "data_fresh": True,
        "broker_position_known": True,
        "broker_connection_healthy": True,
        "equity_reconciled": True,
        "protective_exit_confirmed": None,
        "prior_pause_latched": False,
        "operator_available": True,
        "candidate_contracts": 1,
        "candidate_planned_loss_usd": 12.5,
        "candidate_costs_verified": True,
    }
    value.update(updates)
    return value


class TrialBudgetTest(unittest.TestCase):
    def test_good_snapshot_is_only_proposal_fit_and_has_no_side_effects(self):
        inputs = snapshot()
        original = copy.deepcopy(inputs)
        result = assess(inputs)
        self.assertEqual(inputs, original)
        self.assertTrue(result["entry_fits_proposed_limits"])
        self.assertEqual(result["proposal_status"], "NOT_APPROVED")
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["live_authorized"])
        self.assertFalse(result["state_persisted"])
        self.assertIn("broker_margin", result["not_assessed"])

    def test_equity_caps_scale_down_and_never_scale_up(self):
        result = assess(snapshot(day_start_equity_usd=4000, marked_equity_usd=4000,
                                 high_water_equity_usd=4000))
        self.assertEqual(Decimal(result["metrics_usd"]["trade_risk_cap"]), Decimal("10"))
        self.assertEqual(Decimal(result["metrics_usd"]["daily_loss_cap"]), Decimal("20"))
        self.assertIn("CANDIDATE_EXCEEDS_TRADE_RISK_CAP", result["entry_block_reasons"])
        result = assess(snapshot(day_start_equity_usd=6000, marked_equity_usd=6000,
                                 high_water_equity_usd=6000))
        self.assertEqual(Decimal(result["metrics_usd"]["trade_risk_cap"]), Decimal("12.5"))
        self.assertEqual(Decimal(result["metrics_usd"]["daily_loss_cap"]), Decimal("25"))

    def test_fractional_cent_budget_is_not_rounded_up(self):
        result = assess(snapshot(day_start_equity_usd=4999, marked_equity_usd=4999,
                                 high_water_equity_usd=4999))
        self.assertEqual(Decimal(result["metrics_usd"]["trade_risk_cap"]), Decimal("12.4975"))
        self.assertFalse(result["entry_fits_proposed_limits"])

    def test_candidate_exact_limit_and_next_decimal(self):
        self.assertTrue(assess(snapshot())["entry_fits_proposed_limits"])
        result = assess(snapshot(candidate_planned_loss_usd=Decimal("12.500000000000001")))
        self.assertIn("CANDIDATE_EXCEEDS_TRADE_RISK_CAP", result["entry_block_reasons"])

    def test_candidate_must_fit_remaining_daily_and_total_allowance(self):
        result = assess(snapshot(marked_equity_usd=4980, closed_trade_net_pnls_usd=[-20]))
        self.assertEqual(Decimal(result["metrics_usd"]["remaining_daily_allowance"]), Decimal("5"))
        self.assertIn("CANDIDATE_EXCEEDS_REMAINING_DAILY_ALLOWANCE", result["entry_block_reasons"])
        result = assess(snapshot(closed_trade_net_pnls_usd=[-40, 40]))
        self.assertEqual(Decimal(result["metrics_usd"]["remaining_total_allowance"]), Decimal("10"))
        self.assertIn("CANDIDATE_EXCEEDS_REMAINING_TOTAL_ALLOWANCE", result["entry_block_reasons"])
        self.assertTrue(assess(snapshot(closed_trade_net_pnls_usd=[-40, 40],
                                       candidate_planned_loss_usd=10))["entry_fits_proposed_limits"])

    def test_wins_never_restore_total_loss_allowance(self):
        result = assess(snapshot(closed_trade_net_pnls_usd=[-20, 100, -15],
                                 marked_equity_usd=5065, high_water_equity_usd=5065))
        metrics = result["metrics_usd"]
        self.assertEqual(Decimal(metrics["closed_nonreplenishing_losses"]), Decimal("35"))
        self.assertEqual(Decimal(metrics["remaining_total_allowance"]), Decimal("15"))
        self.assertEqual(Decimal(metrics["remaining_daily_allowance"]), Decimal("25"))

    def test_paid_entry_fee_is_not_subtracted_twice_from_daily_equity(self):
        result = assess(snapshot(marked_equity_usd=4989, position_contracts=1,
            open_position_gross_pnl_usd=-10, open_position_paid_entry_fees_usd=1,
            open_position_unpaid_exit_fee_reserve_usd=1, protective_exit_confirmed=True))
        metrics = result["metrics_usd"]
        self.assertEqual(Decimal(metrics["daily_loss_including_unpaid_exit_fee_reserve"]), Decimal("12"))
        self.assertEqual(Decimal(metrics["open_loss_including_entry_fees_and_exit_reserve"]), Decimal("12"))
        self.assertEqual(Decimal(metrics["remaining_total_allowance"]), Decimal("38"))

    def test_winning_open_position_does_not_offset_closed_losses(self):
        result = assess(snapshot(closed_trade_net_pnls_usd=[-40, 40],
            position_contracts=-1, open_position_gross_pnl_usd=20,
            open_position_paid_entry_fees_usd=1, open_position_unpaid_exit_fee_reserve_usd=1,
            marked_equity_usd=5019, high_water_equity_usd=5019, protective_exit_confirmed=True))
        self.assertEqual(Decimal(result["metrics_usd"]["total_nonreplenishing_allowance_used"]), Decimal("40"))

    def test_exit_fee_reserve_can_cross_daily_threshold(self):
        result = assess(snapshot(marked_equity_usd=4976, position_contracts=1,
            open_position_gross_pnl_usd=-23, open_position_paid_entry_fees_usd=1,
            open_position_unpaid_exit_fee_reserve_usd=1.5, protective_exit_confirmed=True))
        self.assertIn("DAILY_LOSS_LIMIT_REACHED_OR_EXCEEDED", result["pause_reasons"])
        self.assertEqual(Decimal(result["metrics_usd"]["daily_loss_including_unpaid_exit_fee_reserve"]), Decimal("25.5"))
        self.assertEqual(Decimal(result["metrics_usd"]["remaining_daily_allowance"]), Decimal("0"))

    def test_exact_and_overshot_loss_thresholds_pause(self):
        for loss in (25, 26, 60):
            with self.subTest(daily_loss=loss):
                result = assess(snapshot(marked_equity_usd=5000-loss,
                                         closed_trade_net_pnls_usd=[-loss]))
                self.assertIn("DAILY_LOSS_LIMIT_REACHED_OR_EXCEEDED", result["pause_reasons"])
        for loss in (50, 51):
            with self.subTest(total_loss=loss):
                result = assess(snapshot(closed_trade_net_pnls_usd=[-loss, 100],
                    marked_equity_usd=5100-loss, high_water_equity_usd=5100-loss))
                self.assertIn("TOTAL_NONREPLENISHING_LOSS_LIMIT_REACHED_OR_EXCEEDED", result["pause_reasons"])
                self.assertEqual(Decimal(result["metrics_usd"]["remaining_total_allowance"]), Decimal("0"))

    def test_completed_round_trip_and_session_boundaries_require_review(self):
        cases = (
            ({"closed_trade_net_pnls_usd": [0]*5}, "COMPLETED_ROUND_TRIP_REVIEW_BOUNDARY"),
            ({"completed_sessions": 5}, "COMPLETED_SESSION_REVIEW_BOUNDARY"),
        )
        for update, reason in cases:
            with self.subTest(reason=reason):
                self.assertIn(reason, assess(snapshot(**update))["pause_reasons"])
        self.assertTrue(assess(snapshot(completed_sessions=4, entry_attempts_today=1,
                                       closed_trade_net_pnls_usd=[0]*4))["entry_fits_proposed_limits"])

    def test_second_entry_blocks_more_entries_without_pausing_its_position(self):
        for position, pending in ((0, 0), (0, 1), (1, 0), (-1, 0)):
            with self.subTest(position=position, pending=pending):
                result = assess(snapshot(entry_attempts_today=2,
                    position_contracts=position, pending_entry_contracts=pending,
                    protective_exit_confirmed=True))
                self.assertFalse(result["entry_fits_proposed_limits"])
                self.assertIn("DAILY_ENTRY_ATTEMPT_LIMIT", result["entry_block_reasons"])
                self.assertFalse(result["pause_required_by_proposal"])
                self.assertEqual(result["pause_reasons"], [])

    def test_more_than_two_attempts_is_a_violation_pause(self):
        result = assess(snapshot(entry_attempts_today=3,
                                 position_contracts=1, protective_exit_confirmed=True))
        self.assertIn("DAILY_ENTRY_ATTEMPT_LIMIT", result["entry_block_reasons"])
        self.assertIn("DAILY_ENTRY_ATTEMPT_LIMIT_EXCEEDED", result["pause_reasons"])
        self.assertTrue(result["pause_required_by_proposal"])

    def test_health_flags_unknown_and_failed_block_and_pause(self):
        fields = ("data_fresh", "broker_position_known", "broker_connection_healthy",
                  "equity_reconciled", "operator_available")
        for field in fields:
            for value in (False, None):
                with self.subTest(field=field, value=value):
                    result = assess(snapshot(**{field: value}))
                    self.assertTrue(result["pause_required_by_proposal"])
                    self.assertFalse(result["entry_fits_proposed_limits"])
        for value in (False, None):
            result = assess(snapshot(position_contracts=1, protective_exit_confirmed=value))
            self.assertIn("PROTECTIVE_EXIT_UNCONFIRMED_OR_FAILED", result["pause_reasons"])
        result = assess(snapshot(prior_pause_latched=True))
        self.assertIn("PREVIOUS_PAUSE_REQUIRES_REVIEW", result["pause_reasons"])

    def test_exposure_and_instrument_restrictions(self):
        for position in (2, -2):
            result = assess(snapshot(position_contracts=position, protective_exit_confirmed=True))
            self.assertIn("EXCESS_OR_DUPLICATE_EXPOSURE", result["pause_reasons"])
        result = assess(snapshot(position_contracts=1, pending_entry_contracts=1,
                                 protective_exit_confirmed=True))
        self.assertIn("EXCESS_OR_DUPLICATE_EXPOSURE", result["pause_reasons"])
        self.assertFalse(assess(snapshot(pending_entry_contracts=1))["entry_fits_proposed_limits"])
        self.assertFalse(assess(snapshot(candidate_contracts=2))["entry_fits_proposed_limits"])
        self.assertFalse(assess(snapshot(candidate_contracts=0))["entry_fits_proposed_limits"])
        self.assertFalse(assess(snapshot(instrument_root="NQ"))["entry_fits_proposed_limits"])

    def test_unknown_nonpositive_equity_never_produces_a_passing_assessment(self):
        for field in ("day_start_equity_usd", "marked_equity_usd", "high_water_equity_usd"):
            for value in (None, 0, -5):
                with self.subTest(field=field, value=value):
                    result = assess(snapshot(**{field: value}))
                    self.assertFalse(result["entry_fits_proposed_limits"])
                    self.assertTrue(result["pause_required_by_proposal"])

    def test_frozen_high_water_drawdown_boundary(self):
        result = assess(snapshot(day_start_equity_usd=4750, marked_equity_usd=4750))
        self.assertIn("FROZEN_HIGH_WATER_DRAWDOWN_LIMIT", result["pause_reasons"])
        result = assess(snapshot(day_start_equity_usd=5000, marked_equity_usd=5001))
        self.assertIn("HIGH_WATER_BELOW_CURRENT_EQUITY", result["pause_reasons"])

    def test_high_water_must_include_day_start_even_after_a_loss(self):
        result = assess(snapshot(day_start_equity_usd=5000, marked_equity_usd=4990,
            high_water_equity_usd=4990, closed_trade_net_pnls_usd=[-10]))
        self.assertIn("HIGH_WATER_BELOW_DAY_START_EQUITY", result["pause_reasons"])
        self.assertTrue(result["pause_required_by_proposal"])
        self.assertFalse(result["entry_fits_proposed_limits"])

    def test_nonfinite_and_wrong_types_rejected(self):
        for field in ("day_start_equity_usd", "marked_equity_usd", "high_water_equity_usd",
                      "open_position_gross_pnl_usd", "open_position_paid_entry_fees_usd",
                      "open_position_unpaid_exit_fee_reserve_usd", "candidate_planned_loss_usd"):
            for value in (float("nan"), float("inf"), float("-inf"), True, "12.5"):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        assess(snapshot(**{field: value}))
        for value in (float("nan"), True, "0", None):
            with self.assertRaises(ValueError):
                assess(snapshot(closed_trade_net_pnls_usd=[value]))
        for update in ({"data_fresh": 1}, {"entry_attempts_today": True},
                       {"completed_sessions": -1}, {"position_contracts": 1.0},
                       {"candidate_contracts": -1}, {"prior_pause_latched": None},
                       {"closed_trade_net_pnls_usd": ()}):
            with self.assertRaises(ValueError):
                assess(snapshot(**update))

    def test_unknown_accounting_and_missing_costs_fail_closed(self):
        result = assess(snapshot(position_contracts=1, protective_exit_confirmed=True,
            open_position_unpaid_exit_fee_reserve_usd=None))
        self.assertIn("OPEN_POSITION_ACCOUNTING_UNKNOWN", result["pause_reasons"])
        self.assertIsNone(result["metrics_usd"]["remaining_total_allowance"])
        self.assertFalse(assess(snapshot(candidate_costs_verified=None))["entry_fits_proposed_limits"])
        self.assertFalse(assess(snapshot(candidate_planned_loss_usd=None))["entry_fits_proposed_limits"])
        with self.assertRaises(ValueError):
            assess(snapshot(open_position_paid_entry_fees_usd=1))
        with self.assertRaises(ValueError):
            assess(snapshot(open_position_unpaid_exit_fee_reserve_usd=-1))
        with self.assertRaises(ValueError):
            assess({"day_start_equity_usd": 5000})
        with self.assertRaises(ValueError):
            assess(snapshot(unrecognized_field=True))

    def test_policy_cannot_be_changed_into_live_permission_or_bool_count(self):
        proposal = json.loads(Path(__file__).with_name("trial_budget_proposal.json").read_text())
        for change in ({"orders_enabled": True}, {"status": "APPROVED"},
                       {"max_contracts": True}, {"trade_risk_cap_usd": 50}):
            with patch("trial_budget.PROPOSAL_PATH") as path:
                path.read_text.return_value = json.dumps({**proposal, **change})
                with self.assertRaises(ValueError):
                    load_proposal()


if __name__ == "__main__":
    unittest.main()
