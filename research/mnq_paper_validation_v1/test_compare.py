import json
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

from compare import compare, read_json, stamp
from fixture import bundles


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paper, self.sim = bundles(self.root)

    def result(self):
        return compare(self.paper, self.sim, paper_root=self.root, simulation_root=self.root)

    def assert_blocked(self, reason):
        report = self.result()
        self.assertTrue(any(reason in item for item in report["blockers"]), report)
        self.assertFalse(report["live_trial_authorized"])
        self.assertEqual(report["live_readiness"], "NOT_READY")

    def shifted(self, value, *, minutes=0, hours=0):
        if isinstance(value, dict):
            return {key: self.shifted(item, minutes=minutes, hours=hours) for key, item in value.items()}
        if isinstance(value, list):
            return [self.shifted(item, minutes=minutes, hours=hours) for item in value]
        if isinstance(value, str) and value.startswith("2026-09-09T"):
            return (datetime.fromisoformat(value.replace("Z", "+00:00")) + timedelta(minutes=minutes, hours=hours)).isoformat()
        return value

    def append_trade(self, suffix, minutes):
        signal = self.shifted(deepcopy(self.sim["signals"][0]), minutes=minutes)
        signal["signal_id"] += suffix
        self.sim["signals"].append(signal)
        decision = {key: signal[key] for key in ("signal_id", "at", "direction", "decision", "reason")}
        self.paper["decisions"].append(decision)
        for order in deepcopy(self.paper["orders"][:2]):
            order = self.shifted(order, minutes=minutes)
            order["order_id"] += suffix
            order["signal_id"] = signal["signal_id"]
            self.paper["orders"].append(order)
        for fill in deepcopy(self.paper["fills"][:2]):
            fill = self.shifted(fill, minutes=minutes)
            fill["fill_id"] += suffix
            fill["order_id"] += suffix
            self.paper["fills"].append(fill)

    def test_absent_records_are_not_ready(self):
        report = compare()
        self.assertEqual(report["comparison_status"], "EVIDENCE_BLOCKED")
        self.assertIn("MISSING_ACTUAL_BROKER_PAPER_RECORDS", report["blockers"])
        self.assertFalse(report["live_trial_authorized"])

    def test_clean_synthetic_match_is_still_only_a_fixture(self):
        report = self.result()
        self.assertEqual(report["comparison_status"], "SYNTHETIC_FIXTURE_ONLY")
        self.assertEqual(report["matches"][0]["paper_net_pnl_usd"], "6.00")
        self.assertEqual(report["differences"], [])
        self.assertEqual(len(report["blockers"]), 2)  # Both inputs explicitly synthetic.
        self.assertEqual(report["live_readiness"], "NOT_READY")

    def test_price_fees_and_latency_differences_are_measured(self):
        self.paper["fills"][0].update(price="22000.25", fee_usd="1.30", at="2026-09-09T13:45:01.120Z")
        self.paper["fills"][1]["price"] = "22003.50"
        match = self.result()["differences"][0]
        self.assertEqual(match["entry_adverse_difference_ticks"], "1")
        self.assertEqual(match["exit_adverse_difference_ticks"], "2")
        self.assertEqual(match["entry_time_difference_ms"], "100")
        self.assertEqual(match["net_pnl_difference_usd"], "-1.80")
        self.assertEqual(match["fee_difference_usd"], "0.30")

    def test_short_trade_difference_sign_and_accounting(self):
        self.paper["decisions"][0]["direction"] = self.sim["signals"][0]["direction"] = -1
        self.paper["orders"][0]["side"] = "SELL"
        self.paper["orders"][1]["side"] = "BUY"
        self.paper["fills"][0]["price"] = "21999.75"
        match = self.result()["matches"][0]
        self.assertEqual(match["entry_adverse_difference_ticks"], "1")
        self.assertEqual(match["paper_net_pnl_usd"], "-10.50")

    def test_duplicate_fill_is_rejected_not_silently_deduplicated(self):
        self.paper["fills"].append(dict(self.paper["fills"][0]))
        self.assert_blocked("duplicate_fill_id")

    def test_duplicate_order_is_rejected(self):
        self.paper["orders"].append(dict(self.paper["orders"][0]))
        self.assert_blocked("duplicate_order_id")

    def test_missing_fill_and_end_position_fail_closed(self):
        self.paper["fills"].pop()
        report = self.result()
        self.assertEqual(report["matches"], [])
        self.assert_blocked("FILL_LEDGER_MISMATCH")
        self.assert_blocked("UNRESOLVED_END_POSITION_FROM_FILLS")
        self.assert_blocked("POSITION_FILL_LEDGER_MISMATCH")

    def test_missing_fee_never_becomes_zero(self):
        self.paper["fills"][0]["fee_usd"] = None
        self.assert_blocked("MISSING_FILL_FEE")
        self.assertEqual(self.result()["matches"], [])
        self.assert_blocked("CASH_RECONCILIATION_NOT_ASSESSABLE")

    def test_cash_mismatch_is_not_a_performance_result(self):
        self.paper["cash_snapshots"][-1]["cash_usd"] = "5005.99"
        self.assert_blocked("CASH_LEDGER_MISMATCH")
        self.assertEqual(self.result()["cash_reconciliation"]["unexplained_cash_difference_usd"], "-0.01")

    def test_explicit_non_trade_cash_flows_reconcile_without_hiding_fees(self):
        self.paper["cash_flows"] = [
            {"flow_id": "fixture-deposit", "at": "2026-09-09T13:50:00Z", "currency": "USD", "kind": "DEPOSIT",
             "amount_usd": "100.00", "source_reference": "synthetic-source.txt"},
            {"flow_id": "fixture-platform-fee", "at": "2026-09-09T13:55:00Z", "currency": "USD", "kind": "NON_TRADE_ACCOUNT_FEE",
             "amount_usd": "-2.00", "source_reference": "synthetic-source.txt"},
        ]
        self.paper["cash_snapshots"][-1]["cash_usd"] = "5104.00"
        report = self.result()
        self.assertEqual(report["cash_reconciliation"]["unexplained_cash_difference_usd"], "0.00")
        self.assertEqual(len(report["blockers"]), 2)

    def test_missing_cash_or_unsettled_ledger_blocks(self):
        self.paper["cash_snapshots"] = []
        self.assert_blocked("MISSING_EXACT_START_END_CASH_SNAPSHOTS")
        self.paper["cash_ledger_complete"] = False
        self.assert_blocked("INCOMPLETE_OR_UNSETTLED_CASH_LEDGER")

    def test_fill_before_local_ack_receipt_is_not_invented_clock_failure(self):
        self.paper["orders"][0]["acknowledgement_received_at"] = "2026-09-09T13:45:01.200Z"
        report = self.result()
        self.assertEqual(len(report["blockers"]), 2)

    def test_broker_ack_event_must_follow_submission_and_precede_local_receipt(self):
        self.paper["orders"][0]["broker_acknowledged_at"] = "2026-09-09T13:30:00Z"
        self.assert_blocked("BROKER_ACKNOWLEDGEMENT_CLOCK_ORDER_INVALID")
        self.paper["orders"][0]["broker_acknowledged_at"] = "2026-09-09T13:45:02Z"
        self.assert_blocked("BROKER_ACKNOWLEDGEMENT_CLOCK_ORDER_INVALID")

    def test_exit_trigger_cannot_exist_before_corresponding_entry_fill(self):
        self.paper["orders"][1]["trigger_at"] = "2026-09-09T13:30:00Z"
        self.assert_blocked("EXIT_TRIGGER_NOT_AFTER_ENTRY_FILL")

    def test_provenance_is_typed_and_references_retained_hashed_source(self):
        for field in ("execution_model_source", "clock_alignment_source"):
            for value in (True, "does-not-exist.txt", ""):
                with self.subTest(field=field, value=value):
                    self.paper, self.sim = bundles(self.root)
                    self.paper[field] = value
                    expected = "EXECUTION_MODEL_PROVENANCE" if field == "execution_model_source" else "UNVERIFIED_CLOCK_ALIGNMENT"
                    self.assert_blocked(expected)

    def test_deposit_cannot_hide_behind_nonexistent_source(self):
        self.paper["cash_flows"] = [{"flow_id": "fixture-flow", "at": "2026-09-09T13:50:00Z", "currency": "USD",
                                     "kind": "DEPOSIT", "amount_usd": "100.00", "source_reference": "does-not-exist.txt"}]
        self.paper["cash_snapshots"][-1]["cash_usd"] = "5106.00"
        self.assert_blocked("CASH_FLOW_SOURCE_MISSING_OR_NOT_RETAINED")

    def test_new_york_late_signal_and_entry_are_rejected(self):
        self.paper = self.shifted(self.paper, hours=2)
        self.sim = self.shifted(self.sim, hours=2)
        self.assert_blocked("SIGNAL_OUTSIDE_FROZEN_ENTRY_WINDOW")
        self.assert_blocked("ENTRY_QUOTE_OUTSIDE_FROZEN_SESSION_WINDOW")

    def test_three_same_day_entries_violate_both_frozen_limits(self):
        self.append_trade("-second", 3)
        self.append_trade("-third", 6)
        self.paper["cash_snapshots"][-1]["cash_usd"] = "5018.00"
        self.assert_blocked("PAPER_DAILY_ENTRY_LIMIT_EXCEEDED")
        self.assert_blocked("SIMULATION_DAILY_ENTRY_LIMIT_EXCEEDED")

    def test_second_entry_after_realized_daily_loss_pause_is_rejected(self):
        self.append_trade("-second", 3)
        self.paper["fills"][1]["price"] = self.sim["signals"][0]["exit"]["price"] = "21986.00"
        self.paper["cash_snapshots"][-1]["cash_usd"] = "4976.00"
        self.assert_blocked("ENTRY_AFTER_OBSERVED_DAILY_LOSS_PAUSE")

    def test_account_realized_drawdown_pause_latches(self):
        self.append_trade("-second", 3)
        self.paper["fills"][1]["price"] = self.sim["signals"][0]["exit"]["price"] = "21874.00"
        self.paper["cash_snapshots"][-1]["cash_usd"] = "4752.00"
        self.assert_blocked("ENTRY_AFTER_OBSERVED_ACCOUNT_DRAWDOWN_PAUSE")

    def test_unverified_fee_is_explicit(self):
        self.paper["fills"][0]["fee_source"] = "ILLUSTRATIVE"
        self.assert_blocked("UNVERIFIED_FILL_FEE")

    def test_verified_fee_label_requires_retained_fee_source(self):
        self.paper["fills"][0]["fee_source"] = "VERIFIED_FEE_SCHEDULE"
        self.paper["fills"][0]["fee_source_reference"] = "missing-fee-schedule.pdf"
        self.assert_blocked("FILL_FEE_SOURCE_NOT_RETAINED")

    def test_partial_fill_and_oversize_order_cannot_pass(self):
        self.paper["orders"][0].update(quantity=2, status="PARTIALLY_FILLED")
        self.assert_blocked("UNRESOLVED_ORDER")
        self.assert_blocked("MAX_ONE_CONTRACT_VIOLATION")

    def test_duplicate_time_does_not_invent_execution_order(self):
        self.paper["fills"][1]["at"] = self.paper["fills"][0]["at"]
        self.assert_blocked("AMBIGUOUS_FILL_ORDER_AT_SHARED_TIMESTAMP")

    def test_wrong_side_exit_does_not_reconcile_to_flat(self):
        self.paper["orders"][1]["side"] = "BUY"
        self.assert_blocked("EXIT_DOES_NOT_CLOSE_EXISTING_POSITION")
        self.assert_blocked("EXCESS_POSITION_EXPOSURE")
        self.assert_blocked("UNRESOLVED_END_POSITION_FROM_FILLS")

    def test_fractional_contract_fill_is_invalid(self):
        self.paper["fills"][0]["quantity"] = 0.5
        self.assert_blocked("quantity_must_be_whole_contracts")

    def test_naive_timestamp_rejected_and_offsets_preserve_ns(self):
        self.assertEqual(stamp("2026-09-09T09:45:01.123456789-04:00"), stamp("2026-09-09T13:45:01.123456789Z"))
        self.assertEqual(stamp("2026-09-09T13:45:01.123456789Z") - stamp("2026-09-09T13:45:01.123456788Z"), 1)
        self.paper["fills"][0]["at"] = "2026-09-09T13:45:01"
        self.assert_blocked("timestamp_requires_RFC3339_offset")

    def test_equivalent_timezone_representation_matches(self):
        self.paper["fills"][0]["at"] = "2026-09-09T09:45:01.020-04:00"
        self.assertEqual(self.result()["differences"], [])

    def test_stale_quote_future_quote_and_stale_snapshot(self):
        self.paper["orders"][0]["reference_quote_at"] = "2026-09-09T13:44:58Z"
        self.assert_blocked("STALE_OR_FUTURE_REFERENCE_QUOTE")
        self.paper["orders"][0]["reference_quote_at"] = "2026-09-09T13:45:01.001Z"
        self.assert_blocked("STALE_OR_FUTURE_REFERENCE_QUOTE")
        self.paper["positions"][-1]["at"] = "2026-09-09T13:59:00Z"
        self.assert_blocked("MISSING_OR_STALE_END_POSITION_SNAPSHOT")

    def test_wrong_contract_unmatched_order_and_missing_signal_detection(self):
        self.paper["orders"][0]["symbol"] = "MNQZ6"
        self.assert_blocked("ORDER_CONTRACT_MISMATCH")
        self.paper["orders"][0]["signal_id"] = "unknown"
        self.assert_blocked("UNMATCHED_PAPER_ORDER")
        self.paper["decisions"] = []
        self.assert_blocked("SIGNAL_SET_MISMATCH")

    def test_order_for_skipped_signal_is_violation(self):
        self.sim["signals"][0].update(decision="SKIP", entry=None, exit=None, reason="RISK_BUDGET")
        self.assert_blocked("PAPER_ORDER_FOR_SKIPPED_SIGNAL")
        self.assert_blocked("SIGNAL_DECISION_MISMATCH")

    def test_native_bracket_semantics_block_comparison(self):
        self.paper["execution_model"]["target_order"] = "NATIVE_LIMIT"
        self.assert_blocked("EXECUTION_MODEL_OR_TRIGGER_MISMATCH")
        self.paper["orders"][1]["order_type"] = "LIMIT"
        self.assert_blocked("ORDER_EXECUTION_SEMANTICS_MISMATCH")
        self.paper["orders"][1]["trigger_basis"] = "LAST_TRADE"
        self.assert_blocked("EXIT_TRIGGER_BASIS_MISMATCH")

    def test_exit_delay_and_entry_deadline_are_checked(self):
        self.paper["orders"][1]["trigger_at"] = "2026-09-09T13:45:59.950Z"
        self.assert_blocked("EXIT_TRIGGER_DELAY_MISMATCH")
        self.paper["orders"][0]["reference_quote_at"] = "2026-09-09T13:45:00.999999999Z"
        self.assert_blocked("ENTRY_QUOTE_OUTSIDE_FROZEN_WINDOW")

    def test_source_tampering_and_incomplete_export_block(self):
        (self.root / "synthetic-source.txt").write_text("changed")
        self.assert_blocked("SOURCE_HASH_MISMATCH")
        self.paper["complete"] = False
        self.assert_blocked("INCOMPLETE_EXPORT")

    def test_unverified_clock_and_receipt_after_submission_block(self):
        self.paper["clock_alignment_verified"] = False
        self.assert_blocked("UNVERIFIED_CLOCK_ALIGNMENT")
        self.paper["orders"][0]["reference_quote_received_at"] = "2026-09-09T13:45:01.100Z"
        self.assert_blocked("QUOTE_RECEIPT_CLOCK_ORDER_INVALID")

    def test_source_traversal_and_absolute_paths_rejected(self):
        self.paper["source_files"][0]["path"] = "../outside"
        self.assert_blocked("source_paths_must_be_relative")
        self.paper["source_files"][0]["path"] = str(self.root / "synthetic-source.txt")
        self.assert_blocked("source_paths_must_be_relative")

    def test_nonfinite_offtick_and_negative_fees_rejected(self):
        for field, value, expected in (("price", "NaN", "invalid_nonnegative_decimal"),
                                       ("price", "22000.10", "off_tick_price"),
                                       ("fee_usd", "-1", "invalid_nonnegative_decimal")):
            with self.subTest(field=field, value=value):
                self.paper, self.sim = bundles(self.root)
                self.paper["fills"][0][field] = value
                self.assert_blocked(expected)

    def test_json_duplicate_keys_and_nonfinite_literals_rejected(self):
        path = self.root / "bad.json"
        for text in ('{"a":1,"a":2}', '{"a":NaN}'):
            path.write_text(text)
            with self.assertRaises(ValueError):
                read_json(path)

    def test_missing_field_and_malformed_bundles_fail_closed(self):
        self.paper.pop("positions")
        self.assert_blocked("INVALID_EVIDENCE")
        self.assertEqual(compare([], {})["live_readiness"], "NOT_READY")


if __name__ == "__main__":
    unittest.main()
