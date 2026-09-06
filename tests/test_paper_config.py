import copy
import hashlib
from pathlib import Path
import unittest

from swingbot.config import load_config
from swingbot.paper_config import (
    FROZEN_STRATEGY_CONFIG_SHA256,
    FROZEN_STRATEGY_VALUE_SHA256,
    PaperConfigError,
    _validate,
    load_paper_config,
)
from swingbot.paper_models import canonical_json


ROOT = Path(__file__).parents[1]


class PaperConfigTests(unittest.TestCase):
    def test_committed_config_is_bound_to_frozen_strategy(self) -> None:
        config = load_paper_config(
            ROOT / "config/paper_v1.json", ROOT / "config/strategy_v1.json"
        )
        self.assertTrue(config["broker"]["paper_only"])
        self.assertEqual(config["broker"]["trading_base_url"], "https://paper-api.alpaca.markets")
        self.assertEqual(config["strategy_config_sha256"], FROZEN_STRATEGY_CONFIG_SHA256)
        strategy = load_config(ROOT / "config/strategy_v1.json")
        self.assertEqual(
            hashlib.sha256(canonical_json(strategy).encode("utf-8")).hexdigest(),
            FROZEN_STRATEGY_VALUE_SHA256,
        )

    def test_live_endpoint_and_weakened_defaults_are_rejected(self) -> None:
        config = load_paper_config(
            ROOT / "config/paper_v1.json", ROOT / "config/strategy_v1.json"
        )
        digest = config["strategy_config_sha256"]
        for path, value in (
            (("broker", "trading_base_url"), "https://api.alpaca.markets"),
            (("broker", "market_data_feed"), "sip"),
            (("broker", "request_timeout_seconds"), 600),
            (("broker", "paper_only"), False),
            (("account", "initial_equity_tolerance"), 100000),
            (("execution", "default_kill_switch"), False),
            (("execution", "approval_ttl_seconds"), 86400),
            (("execution", "quote_max_age_seconds"), 86400),
            (("execution", "quote_future_tolerance_seconds"), 86400),
            (("execution", "max_requote_drift_bps"), 10000),
            (("execution", "max_quote_spread_bps"), 10000),
            (("execution", "market_fill_buffer_bps"), 10000),
            (("execution", "cancel_verification_attempts"), 1),
            (("execution", "cancel_verification_interval_seconds"), 60),
            (("execution", "exit_cancel_cutoff_seconds_before_close"), 0),
            (("execution", "fractional_swing_orders"), "allowed"),
            (("monitoring", "order_terminal_statuses"), ["canceled"]),
            (("monitoring", "poll_seconds"), 3600),
        ):
            changed = copy.deepcopy(config)
            changed[path[0]][path[1]] = value
            with self.subTest(path=path), self.assertRaises(PaperConfigError):
                _validate(changed, digest)
        with self.assertRaises(PaperConfigError):
            _validate(config, "wrong-strategy-digest")


if __name__ == "__main__":
    unittest.main()
