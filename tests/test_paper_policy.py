from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import unittest

from swingbot.config import load_config
from swingbot.paper_config import load_paper_config
from swingbot.paper_models import PaperOrder, PaperPosition, PaperQuote
from swingbot.paper_policy import (
    PaperPolicyError,
    authorize_entry_risk,
    require_initial_account,
    require_quote,
    size_entry,
)
from swingbot.paper_state import OperationalState

from paper_fixtures import FakeBroker, NOW, paper_account


ROOT = Path(__file__).parents[1]


class PaperPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.strategy = load_config(ROOT / "config/strategy_v1.json")
        cls.paper = load_paper_config(
            ROOT / "config/paper_v1.json", ROOT / "config/strategy_v1.json"
        )

    def test_binding_rejects_default_100k_account_and_nonempty_account(self) -> None:
        with self.assertRaises(PaperPolicyError):
            require_initial_account(paper_account(equity="100000", cash="100000"), [], [], self.paper)
        with self.assertRaisesRegex(PaperPolicyError, "must have.*cash"):
            require_initial_account(
                paper_account(equity="500", cash="499"), [], [], self.paper
            )
        position = PaperPosition("SPY", Decimal("1"), "long", Decimal("100"), Decimal("100"), Decimal("100"))
        with self.assertRaises(PaperPolicyError):
            require_initial_account(paper_account(), [position], [], self.paper)
        broker_value_only = paper_account()
        broker_value_only = broker_value_only.__class__(
            **{**broker_value_only.__dict__, "long_market_value": Decimal("100")}
        )
        with self.assertRaises(PaperPolicyError):
            require_initial_account(broker_value_only, [], [], self.paper)
        nested_stop = PaperOrder(
            "stop", "", "SPY", "sell", "stop", "gtc", "simple", "new",
            Decimal("1"), Decimal("0"), stop_price=Decimal("90"),
        )
        terminal_parent = PaperOrder(
            "parent", "client", "SPY", "buy", "market", "gtc", "oto", "filled",
            Decimal("1"), Decimal("1"), filled_average_price=Decimal("100"),
            legs=(nested_stop,), filled_at=NOW,
        )
        with self.assertRaisesRegex(PaperPolicyError, "working orders"):
            require_initial_account(paper_account(), [], [terminal_parent], self.paper)

    def test_quote_staleness_future_spread_and_requote_drift_fail_closed(self) -> None:
        good = PaperQuote("SPY", Decimal("99.95"), Decimal("100.05"), NOW)
        require_quote(good, now=NOW, paper_config=self.paper)
        require_quote(
            PaperQuote(
                "SPY", Decimal("99.95"), Decimal("100.05"),
                NOW + timedelta(seconds=1),
            ),
            now=NOW,
            paper_config=self.paper,
        )
        cases = [
            (PaperQuote("SPY", Decimal("99.95"), Decimal("100.05"), NOW - timedelta(seconds=31)), None),
            (PaperQuote("SPY", Decimal("99.95"), Decimal("100.05"), NOW + timedelta(seconds=3)), None),
            (PaperQuote("SPY", Decimal("90"), Decimal("110"), NOW), None),
            (good, Decimal("99")),
        ]
        for quote, prior in cases:
            with self.subTest(quote=quote, prior=prior), self.assertRaises(PaperPolicyError):
                require_quote(quote, now=NOW, paper_config=self.paper, prior_ask=prior)
        with self.assertRaisesRegex(PaperPolicyError, "bid moved"):
            require_quote(
                good,
                now=NOW,
                paper_config=self.paper,
                prior_bid=Decimal("101"),
            )

    def test_sizing_is_cash_and_half_percent_risk_capped(self) -> None:
        broker = FakeBroker()
        quantity, stop, maximum, planned_loss, risk_limit = size_entry(
            account=broker.account,
            quote=broker.quote,
            atr14=Decimal("0.10"),
            strategy_config=self.strategy,
            paper_config=self.paper,
        )
        self.assertGreater(quantity, 0)
        self.assertLessEqual(planned_loss, Decimal("2.5"))
        self.assertEqual(risk_limit, Decimal("2.5"))
        self.assertLessEqual(quantity * maximum, Decimal("500"))
        self.assertEqual(stop.as_tuple().exponent, -2)

    def test_pending_orders_reserve_aggregate_risk_and_daily_loss_halts(self) -> None:
        broker = FakeBroker()
        state = OperationalState(
            pending_entry_risk_by_symbol={f"S{i}": Decimal("2.5") for i in range(6)}
        )
        with self.assertRaisesRegex(PaperPolicyError, "aggregate_open_risk_limit"):
            authorize_entry_risk(
                client_order_id="next", symbol="SPY", account=broker.account,
                quote=broker.quote, now=NOW, planned_loss=Decimal("0.01"),
                day_start_equity=Decimal("500"),
                state=state, strategy_config=self.strategy, kill_switch=False,
            )
        halted = OperationalState(realized_pnl_by_day={NOW.date(): Decimal("-10")})
        with self.assertRaisesRegex(PaperPolicyError, "daily_loss_halt"):
            authorize_entry_risk(
                client_order_id="halted", symbol="SPY", account=broker.account,
                quote=broker.quote, now=NOW, planned_loss=Decimal("1"),
                day_start_equity=Decimal("500"),
                state=halted, strategy_config=self.strategy, kill_switch=False,
            )

        authorize_entry_risk(
            client_order_id="future-within-tolerance", symbol="SPY",
            account=broker.account,
            quote=PaperQuote(
                "SPY", broker.quote.bid, broker.quote.ask,
                NOW + timedelta(seconds=1),
            ),
            now=NOW, planned_loss=Decimal("1"),
            day_start_equity=Decimal("500"), state=OperationalState(),
            strategy_config=self.strategy, kill_switch=False,
        )

        # Alpaca last_equity is the previous close, not the durable daily halt
        # base. The explicitly observed start value controls the 2% threshold.
        misleading = broker.account.__class__(
            **{**broker.account.__dict__, "last_equity": Decimal("100000")}
        )
        with self.assertRaisesRegex(PaperPolicyError, "daily_loss_halt"):
            authorize_entry_risk(
                client_order_id="halted-observed-base", symbol="SPY",
                account=misleading, quote=broker.quote, now=NOW,
                planned_loss=Decimal("1"), day_start_equity=Decimal("500"),
                state=halted, strategy_config=self.strategy, kill_switch=False,
            )


if __name__ == "__main__":
    unittest.main()
