from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import unittest

from swingbot.config import load_config
from swingbot.paper_signals import latest_entry_decision

from paper_fixtures import NOW, qualifying_bars


ROOT = Path(__file__).parents[1]


class PaperSignalTests(unittest.TestCase):
    def test_current_session_bar_is_never_used(self) -> None:
        config = load_config(ROOT / "config/strategy_v1.json")
        bars = qualifying_bars()
        prior = latest_entry_decision(
            bars,
            session_date=NOW.date(),
            strategy_config=config,
        )
        today = replace(
            bars[-1],
            date=NOW.date(),
            close=1.0,
            high=200.0,
            low=1.0,
        )
        with_incomplete = latest_entry_decision(
            bars + [today],
            session_date=NOW.date(),
            strategy_config=config,
        )
        self.assertEqual(prior, with_incomplete)
        self.assertLess(with_incomplete.bar_date, NOW.date())

    def test_nonfinite_completed_bar_cannot_create_a_signal(self) -> None:
        config = load_config(ROOT / "config/strategy_v1.json")
        bars = qualifying_bars()
        bars[-1] = replace(bars[-1], close=float("nan"))
        decision = latest_entry_decision(
            bars, session_date=NOW.date(), strategy_config=config
        )
        self.assertIsNone(decision.signal)
        self.assertEqual(decision.rejection_reason, "invalid_market_data")


if __name__ == "__main__":
    unittest.main()
