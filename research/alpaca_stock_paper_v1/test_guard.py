import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from research.alpaca_stock_paper_v1.guard import (
    Account, Intent, Policy, Quote, PAPER_ENDPOINT, preflight,
)

NY = ZoneInfo("America/New_York")
NOW = datetime(2026, 9, 23, 10, 30, tzinfo=NY)
D = Decimal


def fixture():
    account = Account(PAPER_ENDPOINT, NOW, D("7500"), D("30000"), 0, 0, True)
    quote = Quote(NOW, D("809"), D("810"), "iex")
    intent = Intent("proposal-v1", "LITE", NOW, D("1"), D("811"))
    policy = Policy(frozenset({"proposal-v1"}), D("4000"))
    return account, quote, intent, policy


class GuardTests(unittest.TestCase):
    def test_no_approved_version_fails_closed(self):
        a, q, i, p = fixture()
        self.assertIn("strategy_not_approved", preflight(a, q, i, Policy(), NOW)[1])

    def test_valid_paper_intent_has_stable_id(self):
        args = fixture()
        first = preflight(*args, NOW)
        self.assertTrue(first[0])
        self.assertEqual(first, preflight(*args, NOW))
        self.assertIn("duplicate_decision", preflight(*args, NOW, frozenset({first[2]}))[1])

    def test_broker_buying_power_cannot_override_cash_cap(self):
        a, q, i, p = fixture()
        i = replace(i, quantity=D("2"))
        self.assertIn("position_cap", preflight(a, q, i, p, NOW)[1])
        self.assertIn("experimental_cash", preflight(a, q, i, replace(p, experimental_cash_available=D("500")), NOW)[1])

    def test_wrong_endpoint_and_stale_quote_block(self):
        a, q, i, p = fixture()
        reasons = preflight(replace(a, endpoint="https://api.alpaca.markets"),
                            replace(q, observed_at=NOW-timedelta(seconds=3)), i, p, NOW)[1]
        self.assertIn("wrong_endpoint", reasons)
        self.assertIn("stale_quote", reasons)

    def test_existing_exposure_and_crossed_quote_block(self):
        a, q, i, p = fixture()
        reasons = preflight(replace(a, open_orders=1), replace(q, bid=D("812")), i, p, NOW)[1]
        self.assertIn("existing_exposure", reasons)
        self.assertIn("invalid_quote", reasons)

    def test_closed_market_blocks_even_on_weekday(self):
        a, q, i, p = fixture()
        self.assertIn("market_not_open", preflight(replace(a, market_open=False), q, i, p, NOW)[1])


if __name__ == "__main__":
    unittest.main()
