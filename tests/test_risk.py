from datetime import date, datetime, timedelta, timezone
import unittest

from swingbot.risk import RiskManager, RiskPolicy


class RiskManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = RiskManager(RiskPolicy(0.005, 0.03, 0.02, 30, 6))
        self.manager.start_day(date(2026, 1, 2), 500.0)
        self.now = datetime(2026, 1, 2, 16, tzinfo=timezone.utc)

    def test_quantity_caps_planned_loss_at_half_percent(self) -> None:
        quantity, loss, limit = self.manager.calculate_quantity(500.0, 500.0, 100.0, 95.0)
        self.assertEqual(quantity, 0.5)
        self.assertAlmostEqual(loss, 2.5)
        self.assertAlmostEqual(limit, 2.5)

    def test_stale_quote_is_rejected(self) -> None:
        decision = self.manager.authorize_entry(
            order_id="one", symbol="SPY", equity=500.0, planned_loss=2.0,
            quote_timestamp=self.now - timedelta(seconds=31), decision_timestamp=self.now,
        )
        self.assertEqual(decision.reason, "stale_quote")

    def test_naive_timestamp_is_rejected_without_exception(self) -> None:
        decision = self.manager.authorize_entry(
            order_id="one", symbol="SPY", equity=500.0, planned_loss=2.0,
            quote_timestamp=datetime(2026, 1, 2, 16), decision_timestamp=self.now,
        )
        self.assertEqual(decision.reason, "timestamp_must_be_timezone_aware")

    def test_kill_switch_duplicate_and_daily_halt(self) -> None:
        self.manager.set_kill_switch(True)
        kwargs = dict(order_id="one", symbol="SPY", equity=500.0, planned_loss=2.0,
                      quote_timestamp=self.now, decision_timestamp=self.now)
        self.assertEqual(self.manager.authorize_entry(**kwargs).reason, "global_kill_switch_active")
        self.manager.set_kill_switch(False)
        self.assertTrue(self.manager.authorize_entry(**kwargs).accepted)
        self.assertEqual(self.manager.authorize_entry(**kwargs).reason, "duplicate_order_id")
        self.manager.close_position("SPY", -10.0)
        kwargs.update(order_id="two", symbol="QQQ")
        self.assertEqual(self.manager.authorize_entry(**kwargs).reason, "daily_loss_halt")

    def test_aggregate_limit(self) -> None:
        for i in range(6):
            decision = self.manager.authorize_entry(
                order_id=str(i), symbol=f"S{i}", equity=500.0, planned_loss=2.5,
                quote_timestamp=self.now, decision_timestamp=self.now,
            )
            self.assertTrue(decision.accepted)
        rejected = self.manager.authorize_entry(
            order_id="six", symbol="S6", equity=500.0, planned_loss=0.01,
            quote_timestamp=self.now, decision_timestamp=self.now,
        )
        self.assertEqual(rejected.reason, "aggregate_open_risk_limit")


if __name__ == "__main__":
    unittest.main()
