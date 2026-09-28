import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from research.alpaca_stock_paper_v1.fallback import Observation, ProfitFallback, check
from research.alpaca_stock_paper_v1.guard import PAPER_ENDPOINT

NOW = datetime(2026, 9, 23, 15, 0, tzinfo=timezone.utc)
D = Decimal


def fixture():
    auth = ProfitFallback("one-off-1", "paper-position-1", D("1"), D("840"),
                          NOW-timedelta(hours=2), NOW-timedelta(hours=1),
                          NOW+timedelta(hours=1), timedelta(minutes=15), True)
    obs = Observation(PAPER_ENDPOINT, "paper-position-1", D("1"), D("841"), NOW,
                      "iex", True, NOW-timedelta(minutes=20), NOW, True, False)
    return auth, obs


class FallbackTests(unittest.TestCase):
    def test_default_is_no_automatic_sale(self):
        _, obs = fixture()
        self.assertEqual(check(None,obs,NOW),(False,("no_explicit_fallback",)))

    def test_exact_opt_in_can_pass_pure_gate(self):
        auth, obs = fixture()
        self.assertEqual(check(auth,obs,NOW),(True,()))

    def test_reply_or_unverified_inbox_blocks(self):
        auth, obs = fixture()
        self.assertIn("owner_response_present_or_unknown",check(auth,replace(obs,owner_responded=True),NOW)[1])
        self.assertIn("response_status_unverified",check(auth,replace(obs,inbound_response_monitor_healthy=False),NOW)[1])

    def test_no_accepted_email_or_unconfirmed_instruction_blocks(self):
        auth, obs = fixture()
        self.assertIn("missing_or_naive_time",check(auth,replace(obs,email_accepted_at=None),NOW)[1])
        self.assertIn("not_confirmed",check(replace(auth,explicitly_confirmed=False),obs,NOW)[1])

    def test_expired_or_wrong_account_or_stale_quote_blocks(self):
        auth, obs = fixture()
        self.assertIn("invalid_or_expired_instruction",check(replace(auth,expires_at=NOW),obs,NOW)[1])
        self.assertIn("wrong_paper_position",check(auth,replace(obs,endpoint="https://api.alpaca.markets"),NOW)[1])
        self.assertIn("stale_or_wrong_feed",check(auth,replace(obs,quote_at=NOW-timedelta(seconds=3)),NOW)[1])


if __name__ == "__main__":
    unittest.main()
