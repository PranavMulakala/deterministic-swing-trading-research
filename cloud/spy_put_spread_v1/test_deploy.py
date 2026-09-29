"""Offline tests for the options bot deploy guards: no network, no keys."""
from datetime import datetime
import unittest

from cloud.spy_put_spread_v1 import deploy

NY = deploy.NY


class DeployGuardTests(unittest.TestCase):
    def test_refuses_around_the_weekday_run_and_on_monday_mornings(self):
        self.assertIsNotNone(deploy.refuse_now(datetime(2026, 9, 29, 10, 30, tzinfo=NY)))   # Tuesday 10:30
        self.assertIsNotNone(deploy.refuse_now(datetime(2026, 10, 5, 11, 0, tzinfo=NY)))    # Monday 11:00
        self.assertIsNone(deploy.refuse_now(datetime(2026, 9, 29, 11, 5, tzinfo=NY)))      # Tuesday 11:05
        self.assertIsNone(deploy.refuse_now(datetime(2026, 10, 5, 13, 0, tzinfo=NY)))      # Monday afternoon

    def test_test_run_is_clean_only_without_trades_or_failures(self):
        self.assertEqual(deploy.clean('{"headline": "No Events", "events": []}'), (True, "No Events"))
        self.assertTrue(deploy.clean('{"headline": "Market Closed", "events": ["MARKET_CLOSED"]}')[0])
        self.assertFalse(deploy.clean('{"headline": "Error", "events": ["ERROR"]}')[0])
        self.assertFalse(deploy.clean('{"headline": "Spread Opened", "events": ["OPEN_SUBMITTED", "SPREAD_OPENED"]}')[0])
        self.assertFalse(deploy.clean("not json")[0])


if __name__ == "__main__":
    unittest.main()
