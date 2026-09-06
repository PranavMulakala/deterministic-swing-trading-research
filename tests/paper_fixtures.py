from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable

from swingbot.models import Bar
from swingbot.paper_models import (
    ApprovalPermit,
    OrderProposal,
    PaperAccount,
    PaperAsset,
    PaperClock,
    PaperOrder,
    PaperPosition,
    PaperQuote,
)


NOW = datetime(2026, 1, 5, 15, 0, tzinfo=timezone.utc)
ACCOUNT_ID = "paper-account-00001234"


def paper_account(*, equity: str = "500", cash: str = "500") -> PaperAccount:
    return PaperAccount(
        account_id=ACCOUNT_ID,
        account_number="PA001234",
        status="ACTIVE",
        currency="USD",
        equity=Decimal(equity),
        last_equity=Decimal("500"),
        cash=Decimal(cash),
        non_marginable_buying_power=Decimal(cash),
        buying_power=Decimal(cash),
        multiplier=Decimal("2"),
        long_market_value=Decimal("0"),
        short_market_value=Decimal("0"),
        trading_blocked=False,
        account_blocked=False,
        trade_suspended_by_user=False,
    )


def paper_clock(*, is_open: bool = True) -> PaperClock:
    return PaperClock(
        timestamp=NOW,
        is_open=is_open,
        next_open=NOW + timedelta(days=1),
        next_close=NOW + timedelta(hours=6),
    )


def qualifying_bars(symbol: str = "SPY", count: int = 220) -> list[Bar]:
    first = NOW.date() - timedelta(days=count)
    closes = [100.0 + index * 0.05 for index in range(count - 2)] + [110.75, 110.50]
    return [
        Bar(
            symbol=symbol,
            date=first + timedelta(days=index),
            open=close + 0.1,
            high=close + 0.10,
            low=close - 0.10,
            close=close,
            volume=1_000_000.0,
        )
        for index, close in enumerate(closes)
    ]


def sample_proposal(*, fractional: bool = False, action: str = "entry_oto") -> OrderProposal:
    quantity = Decimal("0.5") if fractional else Decimal("1")
    entry = action == "entry_oto"
    return OrderProposal(
        proposal_id="prop-1",
        client_order_id="swing-test-1",
        action=action,
        account_id=ACCOUNT_ID,
        symbol="SPY",
        side="buy" if entry else "sell",
        quantity=quantity,
        order_type="market",
        time_in_force="gtc" if entry else "day",
        order_class="oto" if entry else "simple",
        extended_hours=False,
        created_at=NOW,
        expires_at=NOW + timedelta(seconds=120),
        quote_timestamp=NOW,
        bid=Decimal("119.90"),
        ask=Decimal("120.10"),
        maximum_entry_reference=Decimal("120.40025") if entry else None,
        stop_price=Decimal("118") if entry else None,
        estimated_cost=quantity * Decimal("120.40025"),
        planned_loss=quantity * Decimal("2.40025") if entry else Decimal("0"),
        risk_limit=Decimal("2.5") if entry else Decimal("0"),
        signal_date=NOW.date() - timedelta(days=1) if entry else None,
        thesis="test thesis",
        invalidation="test invalidation",
        strategy_config_sha256="digest",
        fractional=fractional,
        exit_reason=None if entry else "manual_owner_exit",
    )


def sample_permit(proposal: OrderProposal) -> ApprovalPermit:
    return ApprovalPermit(
        proposal_id=proposal.proposal_id,
        content_hash=proposal.content_hash,
        approval_event_id="approval-event",
        review_event_id="review-event",
        session_id="test-session",
    )


class FakeBroker:
    def __init__(self) -> None:
        self.account = paper_account()
        self.clock = paper_clock()
        self.asset = PaperAsset("SPY", "active", "us_equity", "ARCA", True, True)
        self.quote = PaperQuote("SPY", Decimal("110.49"), Decimal("110.51"), NOW)
        self.positions: list[PaperPosition] = []
        self.orders: list[PaperOrder] = []
        self.bars = {"SPY": qualifying_bars("SPY")}
        self.submitted_entries = 0
        self.submitted_exits = 0
        self.canceled_order_ids: list[str] = []
        self.entry_status = "new"
        self.entry_stop_type = "stop"
        self.entry_stop_status: str | None = None
        self.exit_status = "new"
        self.fail_submit = False
        self.fail_cancel = False
        self.fail_cancel_verification = False
        self.permit_validator: Callable[[OrderProposal, ApprovalPermit, str], bool] | None = None

    def get_account(self) -> PaperAccount:
        return self.account

    def get_clock(self) -> PaperClock:
        return self.clock

    def trading_days(self, *, start: date, end: date) -> list[date]:
        latest = self.clock.timestamp.date() - timedelta(days=1)
        return [latest] if start <= latest <= end else []

    def get_asset(self, symbol: str) -> PaperAsset:
        return replace(self.asset, symbol=symbol)

    def latest_quote(self, symbol: str, *, feed: str) -> PaperQuote:
        assert feed in {"iex", "sip"}
        return replace(self.quote, symbol=symbol)

    def list_positions(self) -> list[PaperPosition]:
        return list(self.positions)

    def list_orders(self, *, status: str = "all") -> list[PaperOrder]:
        del status
        return list(self.orders)

    def get_order(self, order_id: str) -> PaperOrder:
        for order in self.orders:
            found = _find_order(order, order_id)
            if found:
                return found if found.order_id == order.order_id else found
        raise RuntimeError("order not found")

    def get_order_by_client_id(self, client_order_id: str) -> PaperOrder:
        for order in self.orders:
            if order.client_order_id == client_order_id:
                return order
        raise RuntimeError("order not found")

    def submit_entry(self, proposal: OrderProposal, permit: ApprovalPermit) -> PaperOrder:
        assert permit.proposal_id == proposal.proposal_id
        if self.permit_validator is not None:
            assert self.permit_validator(proposal, permit, "submit_order")
        self.submitted_entries += 1
        if self.fail_submit:
            raise RuntimeError("simulated connection loss")
        partially_filled = self.entry_status == "partially_filled"
        filled_quantity = (
            proposal.quantity
            if self.entry_status == "filled"
            else proposal.quantity / 2
            if partially_filled
            else Decimal("0")
        )
        stop = PaperOrder(
            order_id=f"stop-{self.submitted_entries}",
            client_order_id="",
            symbol=proposal.symbol,
            side="sell",
            order_type=self.entry_stop_type,
            time_in_force="gtc",
            order_class="simple",
            status=self.entry_stop_status
            or ("held" if self.entry_status != "filled" else "new"),
            quantity=proposal.quantity,
            filled_quantity=Decimal("0"),
            stop_price=proposal.stop_price,
        )
        order = PaperOrder(
            order_id=f"entry-{self.submitted_entries}",
            client_order_id=proposal.client_order_id,
            symbol=proposal.symbol,
            side="buy",
            order_type="market",
            time_in_force="gtc",
            order_class="oto",
            status=self.entry_status,
            quantity=proposal.quantity,
            filled_quantity=filled_quantity,
            filled_average_price=proposal.ask if filled_quantity > 0 else None,
            legs=(stop,),
            filled_at=NOW if self.entry_status == "filled" else None,
        )
        self.orders.append(order)
        return order

    def close_position(self, proposal: OrderProposal, permit: ApprovalPermit) -> PaperOrder:
        assert permit.proposal_id == proposal.proposal_id
        if self.permit_validator is not None:
            assert self.permit_validator(proposal, permit, "submit_order")
        self.submitted_exits += 1
        if self.fail_submit:
            raise RuntimeError("simulated connection loss")
        order = PaperOrder(
            order_id=f"exit-{self.submitted_exits}",
            client_order_id=proposal.client_order_id,
            symbol=proposal.symbol,
            side="sell",
            order_type="market",
            time_in_force="day",
            order_class="simple",
            status=self.exit_status,
            quantity=proposal.quantity,
            filled_quantity=proposal.quantity if self.exit_status == "filled" else Decimal("0"),
            filled_average_price=proposal.bid if self.exit_status == "filled" else None,
            filled_at=NOW if self.exit_status == "filled" else None,
        )
        self.orders.append(order)
        return order

    def cancel_order(
        self, order_id: str, expected_stop_price: Decimal,
        proposal: OrderProposal, permit: ApprovalPermit,
    ) -> PaperOrder:
        assert proposal.proposal_id == permit.proposal_id
        assert expected_stop_price > 0
        if self.permit_validator is not None:
            assert self.permit_validator(proposal, permit, "cancel_protective_stop")
        if self.fail_cancel:
            raise RuntimeError("simulated cancellation uncertainty")
        self.canceled_order_ids.append(order_id)
        self.orders = [_replace_order_status(order, order_id, "canceled") for order in self.orders]
        if self.fail_cancel_verification:
            raise RuntimeError("simulated cancellation verification loss")
        return self.get_order(order_id)

    def historical_daily_bars(
        self, symbols: list[str], *, start: date, end: date, feed: str, adjustment: str
    ) -> dict[str, list[Bar]]:
        assert feed in {"iex", "sip"}
        assert adjustment == "all"
        return {
            symbol: [bar for bar in self.bars.get(symbol, qualifying_bars(symbol)) if start <= bar.date <= end]
            for symbol in symbols
        }


def _find_order(order: PaperOrder, order_id: str) -> PaperOrder | None:
    if order.order_id == order_id:
        return order
    for leg in order.legs:
        found = _find_order(leg, order_id)
        if found:
            return found
    return None


def _replace_order_status(order: PaperOrder, order_id: str, status: str) -> PaperOrder:
    legs = tuple(_replace_order_status(leg, order_id, status) for leg in order.legs)
    return replace(order, status=status if order.order_id == order_id else order.status, legs=legs)
