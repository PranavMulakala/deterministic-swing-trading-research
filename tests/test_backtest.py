from datetime import date, timedelta
import unittest
from unittest.mock import patch

from swingbot.backtest import BacktestEngine
from swingbot.models import Bar, Signal
from swingbot.strategy import StrategyEvaluation


def _config() -> dict:
    return {
        "strategy_id": "test",
        "account": {"initial_equity": 500.0, "fractional_precision": 6},
        "data": {"quote_max_age_seconds": 30},
        "risk": {
            "max_planned_loss_pct": 0.005,
            "max_aggregate_open_risk_pct": 0.03,
            "daily_loss_halt_pct": 0.02,
        },
        "strategy": {
            "trend_sma_days": 3,
            "recovery_sma_days": 2,
            "rsi_period": 1,
            "rsi_entry_below": 10,
            "stop_atr_days": 2,
            "stop_atr_multiple": 2,
            "time_stop_trading_days": 20,
        },
        "costs": {"half_spread_bps": 1, "slippage_bps": 2, "fee_bps_per_side": 0.1},
    }


class BacktestTests(unittest.TestCase):
    def test_close_signal_enters_and_exits_on_later_bars(self) -> None:
        start = date(2026, 1, 5)
        closes = [50, 100, 90, 95, 96]
        opens = [50, 100, 90, 92, 96]
        bars = [
            Bar("SPY", start + timedelta(days=i), opens[i], max(opens[i], close) + 1,
                min(opens[i], close) - 1, close, 1_000_000)
            for i, close in enumerate(closes)
        ]
        result = BacktestEngine(
            _config(), {"SPY": bars}, split="test", start_date=bars[0].date,
            end_date=bars[-1].date, run_id="deterministic-test",
        ).run()
        self.assertEqual(len(result.trades), 1)
        trade = result.trades[0]
        self.assertEqual(trade.signal_date, bars[2].date)
        self.assertEqual(trade.entry_date, bars[3].date)
        self.assertEqual(trade.exit_signal_date, bars[3].date)
        self.assertEqual(trade.exit_date, bars[4].date)
        self.assertLessEqual(trade.planned_risk_pct, 0.5 + 1e-8)
        self.assertEqual(trade.exit_reason, "recovery_target")

    def test_same_inputs_produce_identical_events(self) -> None:
        start = date(2026, 1, 5)
        bars = [Bar("SPY", start + timedelta(days=i), 100, 101, 99, 100, 1_000_000) for i in range(6)]
        args = dict(config=_config(), bars_by_symbol={"SPY": bars}, split="test",
                    start_date=bars[0].date, end_date=bars[-1].date, run_id="same")
        self.assertEqual(BacktestEngine(**args).run().events, BacktestEngine(**args).run().events)

    def test_multiple_open_losses_can_halt_later_entries_that_day(self) -> None:
        start = date(2026, 1, 5)
        days = [start + timedelta(days=i) for i in range(3)]
        exiting_symbols = {"AAA", "AAB", "AAC", "AAD", "AAE"}
        bars = {
            symbol: [
                Bar(symbol, days[0], 100, 101, 99, 100, 1_000_000),
                Bar(symbol, days[1], 100, 101, 99, 100, 1_000_000),
                Bar(symbol, days[2], 90.1, 91, 89, 90, 1_000_000),
            ]
            for symbol in exiting_symbols
        }
        bars["ZZZ"] = [Bar("ZZZ", day, 100, 101, 99, 100, 1_000_000) for day in days]
        config = _config()
        config["strategy"]["recovery_sma_days"] = 1

        def signals(*, symbol: str, day: date, **_: object) -> StrategyEvaluation:
            if symbol in exiting_symbols and day == days[0]:
                return StrategyEvaluation(
                    Signal(symbol, day, 5, 100, 100, 90, 0, "test", "test"), None
                )
            if (symbol, day) == ("ZZZ", days[1]):
                return StrategyEvaluation(
                    Signal(symbol, day, 5, 100, 100, 90, 0, "test", "test"), None
                )
            return StrategyEvaluation(None, "test_no_signal")

        with patch("swingbot.backtest.evaluate_entry", side_effect=signals):
            result = BacktestEngine(
                config, bars, split="test", start_date=days[0], end_date=days[-1],
                run_id="daily-halt-path",
            ).run()
        halt_events = [
            event for event in result.events
            if event["event_type"] == "order_rejected"
            and event.get("reason") == "daily_loss_halt"
        ]
        self.assertEqual(len(halt_events), 1)
        self.assertEqual(halt_events[0]["symbol"], "ZZZ")


if __name__ == "__main__":
    unittest.main()
