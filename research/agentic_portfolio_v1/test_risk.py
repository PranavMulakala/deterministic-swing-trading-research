from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import tempfile
import unittest

from research.agentic_portfolio_v1.common import ValidationError
from research.agentic_portfolio_v1.risk import IdempotencyConflict, RiskLedger, RiskPolicy, RiskRejected


NOW = datetime(2026, 9, 14, 20, 0, tzinfo=timezone.utc)


class RiskLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = f"{self.tmp.name}/risk.sqlite"
        self.ledger = RiskLedger(self.path, "stock-1000", Decimal("1000"))

    def tearDown(self):
        self.tmp.cleanup()

    def reserve(self, key="k1", strategy="s1", symbol="LITE", amount="100", now=NOW, asset="EQUITY", loss="0"):
        return self.ledger.reserve(
            idempotency_key=key, strategy=strategy, symbol=symbol, asset_type=asset,
            notional=Decimal(amount), contractual_loss=Decimal(loss), now=now,
        )

    def test_equity_position_limit(self):
        with self.assertRaisesRegex(RiskRejected, "20%"):
            self.reserve(amount="200.01")

    def test_option_contractual_loss_limit(self):
        with self.assertRaisesRegex(RiskRejected, "5%"):
            self.reserve(asset="OPTION", symbol="SPY:C", amount="50.01", loss="50.01")

    def test_total_option_loss_is_aggregated_across_strategies(self):
        self.reserve(key="oa", strategy="oa", symbol="SPY:A", amount="30", loss="30", asset="OPTION")
        self.reserve(key="ob", strategy="ob", symbol="QQQ:B", amount="20", loss="20", asset="OPTION")
        with self.assertRaisesRegex(RiskRejected, "total option"):
            self.reserve(key="oc", strategy="oc", symbol="SPY:C", amount="0.01", loss="0.01", asset="OPTION")

    def test_equity_symbol_exposure_is_aggregated_across_strategies(self):
        self.reserve(key="sa", strategy="sa", symbol="LITE", amount="150")
        with self.assertRaisesRegex(RiskRejected, "symbol exposure"):
            self.reserve(key="sb", strategy="sb", symbol="LITE", amount="50.01")

    def test_aggregate_deployment_and_cash_reserve_across_strategies(self):
        self.reserve(key="a", strategy="a", amount="200")
        self.reserve(key="b", strategy="b", symbol="COHR", amount="200")
        self.reserve(key="c", strategy="c", symbol="CIEN", amount="100")
        with self.assertRaisesRegex(RiskRejected, "50%|cash reserve"):
            self.reserve(key="d", strategy="d", symbol="FN", amount="0.01")

    def test_same_strategy_only_one_new_intent_per_day(self):
        self.reserve()
        with self.assertRaisesRegex(RiskRejected, "already opened"):
            self.reserve(key="k2", symbol="COHR")

    def test_day_rollover_allows_new_intent(self):
        first = self.reserve()
        self.ledger.release(first["reservation_id"])
        second = self.reserve(key="k2", symbol="COHR", now=NOW + timedelta(days=1))
        self.assertEqual(second["status"], "OPEN")

    def test_idempotent_replay_and_conflict(self):
        first = self.reserve()
        replay = self.reserve(now=NOW + timedelta(seconds=1))
        self.assertEqual(first["reservation_id"], replay["reservation_id"])
        self.assertTrue(replay["replay"])
        with self.assertRaises(IdempotencyConflict):
            self.reserve(symbol="COHR")

    def test_simultaneous_same_key_is_atomic(self):
        other = RiskLedger(self.path, "stock-1000", Decimal("1000"))
        def make(ledger):
            return ledger.reserve(idempotency_key="race", strategy="race", symbol="LITE", asset_type="EQUITY",
                                  notional=Decimal("100"), contractual_loss=Decimal("0"), now=NOW)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(make, (self.ledger, other)))
        self.assertEqual(results[0]["reservation_id"], results[1]["reservation_id"])
        self.assertEqual(sum(int(result["replay"]) for result in results), 1)

    def test_partial_fills_update_weighted_basis_and_reconcile(self):
        reservation = self.reserve()["reservation_id"]
        first = self.ledger.record_fill(reservation_id=reservation, quantity=Decimal("0.5"),
                                        price=Decimal("100"), costs=Decimal("0"), filled_at=NOW,
                                        event_id="partial-1")
        self.assertEqual(first["status"], "PARTIAL")
        second = self.ledger.record_fill(reservation_id=reservation, quantity=Decimal("0.5"),
                                         price=Decimal("100"), costs=Decimal("0"), filled_at=NOW,
                                         event_id="partial-2")
        self.assertEqual(second["status"], "FILLED")
        position = self.ledger.get_position("s1", "LITE")
        self.assertEqual(position["quantity"], "1.0")
        self.assertEqual(position["basis_cents"], 10000)
        closed = self.ledger.close_position(strategy="s1", symbol="LITE", quantity=Decimal("0.4"),
                                            price=Decimal("110"), costs=Decimal("0"), closed_at=NOW, reason="TEST")
        self.assertEqual(closed["realized_pnl_cents"], 400)
        self.assertTrue(self.ledger.reconcile()["ok"])
        reopened = RiskLedger(self.path, "stock-1000", Decimal("1000"))
        self.assertTrue(reopened.reconcile()["ok"])

    def test_expire_and_release_reservations(self):
        first = self.reserve()["reservation_id"]
        release = self.ledger.release(first, event_id="release-first")
        self.assertTrue(self.ledger.release(first, event_id="release-first")["replay"])
        self.assertFalse(release["replay"])
        second = self.reserve(key="k2", strategy="s2", symbol="COHR", now=NOW)["reservation_id"]
        self.assertEqual(self.ledger.expire_reservations(NOW + timedelta(minutes=11)), 1)
        with self.assertRaises(RiskRejected):
            self.ledger.record_fill(reservation_id=second, quantity=Decimal("1"), price=Decimal("10"),
                                    costs=Decimal("0"), filled_at=NOW + timedelta(minutes=11))

    def test_reservation_transition_conflicts_and_tampering_reconcile(self):
        first = self.reserve(key="r1", strategy="r1", symbol="LITE")["reservation_id"]
        second = self.reserve(key="r2", strategy="r2", symbol="COHR")["reservation_id"]
        self.ledger.release(first, released_at=NOW, event_id="transition")
        with self.assertRaises(IdempotencyConflict):
            self.ledger.release(second, released_at=NOW, event_id="transition")
        with self.ledger._transaction() as conn:
            conn.execute("UPDATE reservations SET status='RELEASED',remaining_cents=0 WHERE reservation_id=?", (second,))
        self.assertFalse(self.ledger.reconcile()["ok"])

    def test_reservation_time_version_and_policy_are_hash_bound(self):
        reservation = self.reserve()["reservation_id"]
        with self.ledger._transaction() as conn:
            conn.execute(
                "UPDATE reservations SET expires_at=? WHERE account_id=? AND reservation_id=?",
                ((NOW + timedelta(days=7)).isoformat(), self.ledger.account_id, reservation),
            )
        self.assertFalse(self.ledger.reconcile()["ok"])
        with self.assertRaisesRegex(ValidationError, "policy"):
            RiskLedger(
                self.path, "stock-1000", Decimal("1000"),
                RiskPolicy(max_equity_position=Decimal("0.19")),
            )

    def _assert_receipt_corruption_blocks_replay(self, event_type):
        with tempfile.TemporaryDirectory() as tmp:
            path = f"{tmp}/replay.sqlite"
            ledger = RiskLedger(path, "replay-1000", Decimal("1000"))
            reservation = ledger.reserve(
                idempotency_key="entry", strategy="s", symbol="LITE", asset_type="EQUITY",
                notional=Decimal("100"), contractual_loss=Decimal("100"), now=NOW,
            )
            reservation_id = reservation["reservation_id"]
            replay = lambda reopened: reopened.reserve(
                idempotency_key="entry", strategy="s", symbol="LITE", asset_type="EQUITY",
                notional=Decimal("100"), contractual_loss=Decimal("100"), now=NOW,
            )
            table, where, params = "reservation_events", "event_type='CREATE'", ()
            if event_type in {"FILL", "CLOSE"}:
                ledger.record_fill(
                    reservation_id=reservation_id, quantity=Decimal("1"), price=Decimal("100"),
                    costs=Decimal("0"), filled_at=NOW, event_id="fill-replay",
                )
                table, where, params = "fill_events", "event_id=?", ("fill-replay",)
                replay = lambda reopened: reopened.record_fill(
                    reservation_id=reservation_id, quantity=Decimal("1"), price=Decimal("100"),
                    costs=Decimal("0"), filled_at=NOW, event_id="fill-replay",
                )
            if event_type == "CLOSE":
                ledger.close_position(
                    strategy="s", symbol="LITE", quantity=Decimal("1"), price=Decimal("101"),
                    costs=Decimal("0"), closed_at=NOW, reason="TEST", event_id="close-replay",
                )
                table, where, params = "close_events", "event_id=?", ("close-replay",)
                replay = lambda reopened: reopened.close_position(
                    strategy="s", symbol="LITE", quantity=Decimal("1"), price=Decimal("101"),
                    costs=Decimal("0"), closed_at=NOW, reason="TEST", event_id="close-replay",
                )
            elif event_type == "RELEASE":
                ledger.release(reservation_id, released_at=NOW, event_id="release-replay")
                table, where, params = "reservation_events", "event_id=?", ("release-replay",)
                replay = lambda reopened: reopened.release(
                    reservation_id, released_at=NOW, event_id="release-replay",
                )
            elif event_type == "EXPIRE":
                expiry = NOW + timedelta(minutes=11)
                ledger.expire_reservations(expiry)
                table, where, params = "reservation_events", "event_type='EXPIRE'", ()
                replay = lambda reopened: reopened.expire_reservations(expiry)
            with ledger._transaction() as conn:
                conn.execute(f"UPDATE {table} SET receipt_json='{{}}' WHERE {where}", params)
            reopened = RiskLedger(path, "replay-1000", Decimal("1000"))
            with self.assertRaisesRegex(RiskRejected, "integrity"):
                replay(reopened)
            self.assertTrue(reopened.reconcile()["integrity_latched"])

    def test_reservation_create_replay_reconciles_before_return(self):
        self._assert_receipt_corruption_blocks_replay("CREATE")

    def test_fill_replay_reconciles_before_return(self):
        self._assert_receipt_corruption_blocks_replay("FILL")

    def test_close_replay_reconciles_before_return(self):
        self._assert_receipt_corruption_blocks_replay("CLOSE")

    def test_release_replay_reconciles_before_return(self):
        self._assert_receipt_corruption_blocks_replay("RELEASE")

    def test_expiry_replay_reconciles_before_return(self):
        self._assert_receipt_corruption_blocks_replay("EXPIRE")

    def test_fill_and_close_cannot_precede_durable_state(self):
        rid = self.reserve()["reservation_id"]
        with self.assertRaisesRegex(RiskRejected, "backdated"):
            self.ledger.record_fill(reservation_id=rid, quantity=Decimal("1"), price=Decimal("100"),
                                    costs=Decimal("0"), filled_at=NOW - timedelta(seconds=1))
        self.ledger.record_fill(reservation_id=rid, quantity=Decimal("1"), price=Decimal("100"),
                                costs=Decimal("0"), filled_at=NOW)
        with self.assertRaisesRegex(RiskRejected, "backdated"):
            self.ledger.close_position(strategy="s1", symbol="LITE", quantity=Decimal("1"), price=Decimal("100"),
                                       costs=Decimal("0"), closed_at=NOW - timedelta(seconds=1), reason="BAD_TIME")

    def test_unknown_and_stale_marks_fail_closed(self):
        rid = self.reserve()["reservation_id"]
        self.ledger.record_fill(reservation_id=rid, quantity=Decimal("1"), price=Decimal("100"),
                                costs=Decimal("0"), filled_at=NOW)
        with self.assertRaisesRegex(RiskRejected, "missing mark"):
            self.ledger.reserve(idempotency_key="new", strategy="new", symbol="COHR", asset_type="EQUITY",
                                notional=Decimal("10"), contractual_loss=Decimal("0"), now=NOW)
        self.ledger.set_mark("LITE", Decimal("100"), NOW)
        with self.assertRaisesRegex(RiskRejected, "stale mark"):
            self.ledger.reserve(idempotency_key="new", strategy="new", symbol="COHR", asset_type="EQUITY",
                                notional=Decimal("10"), contractual_loss=Decimal("0"), now=NOW + timedelta(minutes=6))

    def test_fill_and_close_events_are_idempotent_and_conflicts_reject(self):
        rid = self.reserve()["reservation_id"]
        first = self.ledger.record_fill(
            reservation_id=rid, quantity=Decimal("0.5"), price=Decimal("100"), costs=Decimal("0"),
            filled_at=NOW, event_id="fill-one",
        )
        replay = self.ledger.record_fill(
            reservation_id=rid, quantity=Decimal("0.5"), price=Decimal("100"), costs=Decimal("0"),
            filled_at=NOW, event_id="fill-one",
        )
        self.assertFalse(first["replay"])
        self.assertTrue(replay["replay"])
        self.assertEqual(self.ledger.get_position("s1", "LITE")["basis_cents"], 5000)
        with self.assertRaises(IdempotencyConflict):
            self.ledger.record_fill(
                reservation_id=rid, quantity=Decimal("0.4"), price=Decimal("100"), costs=Decimal("0"),
                filled_at=NOW, event_id="fill-one",
            )
        closed = self.ledger.close_position(
            strategy="s1", symbol="LITE", quantity=Decimal("0.5"), price=Decimal("101"),
            costs=Decimal("0"), closed_at=NOW, reason="TEST", event_id="close-one",
        )
        replay_close = self.ledger.close_position(
            strategy="s1", symbol="LITE", quantity=Decimal("0.5"), price=Decimal("101"),
            costs=Decimal("0"), closed_at=NOW, reason="TEST", event_id="close-one",
        )
        self.assertFalse(closed["replay"])
        self.assertTrue(replay_close["replay"])
        with self.assertRaises(IdempotencyConflict):
            self.ledger.close_position(
                strategy="s1", symbol="LITE", quantity=Decimal("0.5"), price=Decimal("102"),
                costs=Decimal("0"), closed_at=NOW, reason="TEST", event_id="close-one",
            )

    def test_option_quantity_loss_and_zero_value_rules(self):
        with self.assertRaisesRegex(RiskRejected, "contractual loss"):
            self.reserve(asset="OPTION", symbol="SPY:C", amount="40", loss="0")
        rid = self.reserve(asset="OPTION", symbol="SPY:C", amount="40", loss="40")["reservation_id"]
        with self.assertRaisesRegex(RiskRejected, "one whole"):
            self.ledger.record_fill(reservation_id=rid, quantity=Decimal("0.5"), price=Decimal("0.40"),
                                    costs=Decimal("0"), filled_at=NOW, event_id="bad-half")
        self.assertIsNone(self.ledger.get_position("s1", "SPY:C"))
        self.ledger.record_fill(reservation_id=rid, quantity=Decimal("1"), price=Decimal("0.40"),
                                costs=Decimal("0"), filled_at=NOW, event_id="whole")
        self.ledger.set_mark("SPY:C", Decimal("0"), NOW, asset_type="OPTION")
        self.ledger.close_position(strategy="s1", symbol="SPY:C", quantity=Decimal("1"), price=Decimal("0"),
                                   costs=Decimal("0"), closed_at=NOW, reason="WORTHLESS", event_id="zero-close")
        self.assertEqual(self.ledger.snapshot(NOW)["cash_cents"], 96000)
        with self.assertRaises(ValidationError):
            self.ledger.set_mark("LITE", Decimal("0"), NOW, asset_type="EQUITY")

    def test_backdated_requests_cannot_reset_daily_loss(self):
        rid = self.reserve()["reservation_id"]
        self.ledger.record_fill(reservation_id=rid, quantity=Decimal("1"), price=Decimal("100"),
                                costs=Decimal("0"), filled_at=NOW, event_id="loss-fill")
        self.ledger.close_position(strategy="s1", symbol="LITE", quantity=Decimal("1"), price=Decimal("79"),
                                   costs=Decimal("0"), closed_at=NOW, reason="LOSS", event_id="loss-close")
        self.ledger.snapshot(NOW + timedelta(days=1))
        with self.assertRaisesRegex(RiskRejected, "backdated"):
            self.reserve(key="back", strategy="back", symbol="COHR", amount="10", now=NOW)

    def test_utc_midnight_and_same_day_clock_are_monotonic(self):
        late = datetime(2026, 9, 14, 23, 59, 59, tzinfo=timezone.utc)
        early_next = late + timedelta(seconds=2)
        self.ledger.snapshot(late)
        self.assertEqual(self.ledger.snapshot(early_next)["trading_date_basis"], "UTC")
        with self.assertRaisesRegex(RiskRejected, "backdated"):
            self.ledger.snapshot(late + timedelta(seconds=1))

    def test_reconciliation_latches_and_requires_explicit_clean_repair(self):
        rid = self.reserve()["reservation_id"]
        self.ledger.record_fill(reservation_id=rid, quantity=Decimal("1"), price=Decimal("100"),
                                costs=Decimal("0"), filled_at=NOW, event_id="basis-fill")
        self.ledger.set_mark("LITE", Decimal("100"), NOW)
        pending = self.reserve(key="pending", strategy="pending", symbol="COHR", amount="50")["reservation_id"]
        with self.ledger._transaction() as conn:
            conn.execute("UPDATE positions SET basis_cents=9999 WHERE account_id=?", (self.ledger.account_id,))
        self.assertFalse(self.ledger.reconcile()["ok"])
        reopened = RiskLedger(self.path, "stock-1000", Decimal("1000"))
        with self.assertRaisesRegex(RiskRejected, "integrity"):
            reopened.reserve(idempotency_key="blocked", strategy="blocked", symbol="COHR", asset_type="EQUITY",
                             notional=Decimal("10"), contractual_loss=Decimal("0"), now=NOW)
        with self.assertRaisesRegex(RiskRejected, "integrity"):
            reopened.close_position(strategy="s1", symbol="LITE", quantity=Decimal("1"), price=Decimal("100"),
                                    costs=Decimal("0"), closed_at=NOW, reason="BLOCKED", event_id="blocked-close")
        with self.assertRaisesRegex(RiskRejected, "integrity"):
            reopened.record_fill(reservation_id=pending, quantity=Decimal("1"), price=Decimal("50"),
                                 costs=Decimal("0"), filled_at=NOW, event_id="blocked-fill")
        with reopened._transaction() as conn:
            conn.execute("UPDATE positions SET basis_cents=10000 WHERE account_id=?", (reopened.account_id,))
        with self.assertRaisesRegex(RiskRejected, "acknowledgement"):
            reopened.clear_integrity_latch_after_repair(acknowledgement="yes", now=NOW)
        reopened.clear_integrity_latch_after_repair(
            acknowledgement="I_HAVE_REPAIRED_AND_RECONCILED_OFFLINE", now=NOW,
        )
        self.assertTrue(reopened.reconcile()["ok"])

    def test_admission_reconciles_and_persists_latch_without_prior_manual_check(self):
        with self.ledger._transaction() as conn:
            conn.execute("UPDATE accounts SET cash_cents=cash_cents+100 WHERE account_id=?", (self.ledger.account_id,))
        with self.assertRaisesRegex(RiskRejected, "integrity"):
            self.reserve()
        reopened = RiskLedger(self.path, "stock-1000", Decimal("1000"))
        self.assertTrue(reopened.reconcile()["integrity_latched"])
        with self.assertRaisesRegex(RiskRejected, "integrity"):
            reopened.snapshot(NOW)

    def test_close_economics_are_recomputed_in_chronological_replay(self):
        rid = self.reserve()["reservation_id"]
        self.ledger.record_fill(reservation_id=rid, quantity=Decimal("1"), price=Decimal("100"),
                                costs=Decimal("0"), filled_at=NOW, event_id="chron-fill")
        self.ledger.close_position(strategy="s1", symbol="LITE", quantity=Decimal("0.5"), price=Decimal("100"),
                                   costs=Decimal("0"), closed_at=NOW, reason="PARTIAL", event_id="chron-close")
        with self.ledger._transaction() as conn:
            conn.execute("UPDATE close_events SET basis_delta_cents=0,realized_pnl_cents=5000 WHERE event_id='chron-close'")
            conn.execute("UPDATE positions SET basis_cents=10000 WHERE account_id=?", (self.ledger.account_id,))
            conn.execute("UPDATE accounts SET realized_pnl_cents=5000 WHERE account_id=?", (self.ledger.account_id,))
        result = self.ledger.reconcile()
        self.assertFalse(result["ok"])
        self.assertTrue(any("chronological replay" in error for error in result["errors"]))

    def test_close_credits_round_down_subcents(self):
        rid = self.reserve(amount="10")["reservation_id"]
        self.ledger.record_fill(reservation_id=rid, quantity=Decimal("1"), price=Decimal("1"),
                                costs=Decimal("0"), filled_at=NOW, event_id="small-fill")
        closed = self.ledger.close_position(
            strategy="s1", symbol="LITE", quantity=Decimal("1"), price=Decimal("1.001"),
            costs=Decimal("0"), closed_at=NOW, reason="SUBCENT", event_id="small-close",
        )
        self.assertEqual(closed["net_proceeds_cents"], 100)

    def test_kill_switch_persists_across_reopen(self):
        self.ledger.set_kill_switch(True)
        reopened = RiskLedger(self.path, "stock-1000", Decimal("1000"))
        self.assertTrue(reopened.kill_switch_enabled())
        with self.assertRaisesRegex(RiskRejected, "kill switch"):
            reopened.reserve(idempotency_key="x", strategy="x", symbol="LITE", asset_type="EQUITY",
                             notional=Decimal("1"), contractual_loss=Decimal("0"), now=NOW)

    def test_daily_realized_loss_pause_and_rollover(self):
        rid = self.reserve(amount="100")["reservation_id"]
        self.ledger.record_fill(reservation_id=rid, quantity=Decimal("1"), price=Decimal("100"),
                                costs=Decimal("0"), filled_at=NOW)
        self.ledger.close_position(strategy="s1", symbol="LITE", quantity=Decimal("1"), price=Decimal("79"),
                                   costs=Decimal("0"), closed_at=NOW, reason="LOSS")
        with self.assertRaisesRegex(RiskRejected, "daily realized-loss"):
            self.reserve(key="later", strategy="later", symbol="COHR", amount="10")
        accepted = self.reserve(key="tomorrow", strategy="later", symbol="COHR", amount="10", now=NOW + timedelta(days=1))
        self.assertEqual(accepted["status"], "OPEN")

    def test_high_water_drawdown_pause(self):
        rid = self.reserve(amount="100")["reservation_id"]
        self.ledger.record_fill(reservation_id=rid, quantity=Decimal("1"), price=Decimal("100"),
                                costs=Decimal("0"), filled_at=NOW)
        self.ledger.set_mark("LITE", Decimal("50"), NOW)
        with self.assertRaisesRegex(RiskRejected, "drawdown"):
            self.reserve(key="later", strategy="later", symbol="COHR", amount="10")

    def test_two_virtual_accounts_are_isolated(self):
        options = RiskLedger(self.path, "options-1000", Decimal("1000"))
        self.reserve()
        self.assertEqual(options.snapshot(NOW)["pending_cents"], 0)
        self.assertEqual(options.snapshot(NOW)["cash_cents"], 100000)

    def test_position_strategy_version_is_durable_and_reconciled(self):
        reservation = self.ledger.reserve(
            idempotency_key="versioned-position", strategy="versioned", strategy_version="7.1.0",
            symbol="LITE", asset_type="EQUITY", notional=Decimal("100"),
            contractual_loss=Decimal("100"), now=NOW, quantity=Decimal("1"),
        )
        self.ledger.record_fill(
            reservation_id=reservation["reservation_id"], quantity=Decimal("1"),
            price=Decimal("100"), costs=Decimal("0"), filled_at=NOW,
            event_id="versioned-position-fill",
        )
        self.assertEqual(self.ledger.get_position("versioned", "LITE")["strategy_version"], "7.1.0")
        reopened = RiskLedger(self.path, "stock-1000", Decimal("1000"))
        self.assertTrue(reopened.reconcile()["ok"])
        with reopened._transaction() as conn:
            conn.execute(
                "UPDATE positions SET strategy_version='7.1.1' WHERE account_id=?",
                (reopened.account_id,),
            )
        result = reopened.reconcile()
        self.assertFalse(result["ok"])
        self.assertTrue(result["integrity_latched"])

    def test_malformed_values_rejected(self):
        with self.assertRaises(ValidationError):
            self.reserve(amount="NaN")
        with self.assertRaises(ValidationError):
            self.ledger.set_mark("lite", Decimal("1"), NOW)
        with self.assertRaises(ValidationError):
            RiskLedger(self.path, "stock-1000", Decimal("999"))
        with self.assertRaises(ValidationError):
            RiskPolicy(max_total_deployed=Decimal("NaN"))


if __name__ == "__main__":
    unittest.main()
