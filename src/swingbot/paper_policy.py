from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_DOWN
from typing import Any

from .paper_config import QUOTE_FUTURE_TOLERANCE_SECONDS
from .paper_models import PaperAccount, PaperAsset, PaperClock, PaperOrder, PaperPosition, PaperQuote
from .paper_state import OperationalState
from .risk import RiskManager, RiskPolicy


class PaperPolicyError(RuntimeError):
    pass


def require_operable_account(account: PaperAccount, paper_config: dict[str, Any]) -> None:
    expected_currency = str(paper_config["account"]["currency"])
    if account.status != "ACTIVE":
        raise PaperPolicyError(f"paper account status is {account.status}, not ACTIVE")
    if account.currency != expected_currency:
        raise PaperPolicyError("paper account currency mismatch")
    if account.trading_blocked or account.account_blocked or account.trade_suspended_by_user:
        raise PaperPolicyError("paper account is blocked or trade-suspended")
    numeric = (
        account.equity,
        account.last_equity,
        account.cash,
        account.non_marginable_buying_power,
        account.buying_power,
        account.multiplier,
        account.long_market_value,
        account.short_market_value,
    )
    if not all(value.is_finite() for value in numeric):
        raise PaperPolicyError("paper account contains a non-finite numeric value")
    if account.short_market_value != 0:
        raise PaperPolicyError("cash/long-only policy rejects any short market value")
    if (
        account.equity <= 0
        or account.cash < 0
        or account.non_marginable_buying_power < 0
        or account.buying_power < 0
        or account.multiplier <= 0
        or account.long_market_value < 0
    ):
        raise PaperPolicyError("paper account equity/cash state is invalid")


def require_initial_account(
    account: PaperAccount,
    positions: list[PaperPosition],
    orders: list[PaperOrder],
    paper_config: dict[str, Any],
) -> None:
    require_operable_account(account, paper_config)
    target = Decimal(str(paper_config["account"]["initial_equity"]))
    tolerance = Decimal(str(paper_config["account"]["initial_equity_tolerance"]))
    if abs(account.equity - target) > tolerance:
        raise PaperPolicyError(
            f"paper account must be reset to ${target} before binding; equity is ${account.equity}"
        )
    if abs(account.cash - target) > tolerance:
        raise PaperPolicyError(
            f"paper account must have ${target} cash before binding; cash is ${account.cash}"
        )
    if positions or account.long_market_value != 0:
        raise PaperPolicyError("paper account must have no positions before binding")
    terminal = set(paper_config["monitoring"]["order_terminal_statuses"])
    working = [order for order in _flatten_orders(orders) if order.status not in terminal]
    if working:
        raise PaperPolicyError("paper account must have no working orders before binding")


def require_account_binding(account: PaperAccount, binding: dict[str, Any] | None) -> None:
    if not binding:
        raise PaperPolicyError("paper account has not been bound at a clean $500 baseline")
    if str(binding.get("account_id")) != account.account_id:
        raise PaperPolicyError("credentials point to a different paper account")


def require_asset(asset: PaperAsset, symbol: str, *, fractional: bool) -> None:
    if asset.symbol != symbol or asset.status != "active" or asset.asset_class != "us_equity":
        raise PaperPolicyError("asset identity/status/class is not eligible")
    if not asset.tradable:
        raise PaperPolicyError("asset is not tradable")
    if fractional and not asset.fractionable:
        raise PaperPolicyError("asset does not support fractional shares")


def require_market_open(clock: PaperClock) -> None:
    if not clock.is_open:
        raise PaperPolicyError("orders may be submitted only during the regular market session")


def require_quote(
    quote: PaperQuote,
    *,
    now: datetime,
    paper_config: dict[str, Any],
    prior_ask: Decimal | None = None,
    prior_bid: Decimal | None = None,
) -> None:
    if now.tzinfo is None or quote.timestamp.tzinfo is None:
        raise PaperPolicyError("quote and decision timestamps must be timezone-aware")
    age = (now - quote.timestamp).total_seconds()
    max_age = int(paper_config["execution"]["quote_max_age_seconds"])
    future_tolerance = int(
        paper_config["execution"]["quote_future_tolerance_seconds"]
    )
    if age < -future_tolerance or age > max_age:
        raise PaperPolicyError(f"quote is stale ({age:.3f}s old; maximum {max_age}s)")
    if (
        not quote.bid.is_finite()
        or not quote.ask.is_finite()
        or quote.bid <= 0
        or quote.ask <= 0
        or quote.ask < quote.bid
        or quote.mid <= 0
    ):
        raise PaperPolicyError("quote has invalid bid/ask values")
    spread_bps = (quote.ask - quote.bid) / quote.mid * Decimal("10000")
    if spread_bps > Decimal(str(paper_config["execution"]["max_quote_spread_bps"])):
        raise PaperPolicyError(f"quote spread is too wide ({spread_bps:.4f} bps)")
    if prior_ask is not None:
        if not prior_ask.is_finite() or prior_ask <= 0:
            raise PaperPolicyError("prior ask is invalid")
        drift_bps = abs(quote.ask - prior_ask) / prior_ask * Decimal("10000")
        if drift_bps > Decimal(str(paper_config["execution"]["max_requote_drift_bps"])):
            raise PaperPolicyError(
                f"ask moved {drift_bps:.4f} bps; create and approve a fresh proposal"
            )
    if prior_bid is not None:
        if not prior_bid.is_finite() or prior_bid <= 0:
            raise PaperPolicyError("prior bid is invalid")
        drift_bps = abs(quote.bid - prior_bid) / prior_bid * Decimal("10000")
        if drift_bps > Decimal(str(paper_config["execution"]["max_requote_drift_bps"])):
            raise PaperPolicyError(
                f"bid moved {drift_bps:.4f} bps; create and approve a fresh proposal"
            )


def price_floor(value: Decimal) -> Decimal:
    increment = Decimal("0.01") if value >= 1 else Decimal("0.0001")
    return value.quantize(increment, rounding=ROUND_DOWN)


def is_fractional(quantity: Decimal) -> bool:
    return quantity != quantity.to_integral_value()


def size_entry(
    *,
    account: PaperAccount,
    quote: PaperQuote,
    atr14: Decimal,
    strategy_config: dict[str, Any],
    paper_config: dict[str, Any],
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
    if not atr14.is_finite() or atr14 <= 0:
        raise PaperPolicyError("ATR must be a positive finite value")
    multiple = Decimal(str(strategy_config["strategy"]["stop_atr_multiple"]))
    stop = price_floor(quote.ask - atr14 * multiple)
    if stop <= 0 or stop >= quote.ask:
        raise PaperPolicyError("calculated protective stop is invalid")
    buffer = Decimal(str(paper_config["execution"]["market_fill_buffer_bps"])) / Decimal("10000")
    maximum_entry = quote.ask * (Decimal("1") + buffer)
    available_cash = min(account.cash, account.non_marginable_buying_power)
    risk_cfg = strategy_config["risk"]
    data_cfg = strategy_config["data"]
    account_cfg = strategy_config["account"]
    manager = RiskManager(
        RiskPolicy(
            max_planned_loss_pct=float(risk_cfg["max_planned_loss_pct"]),
            max_aggregate_open_risk_pct=float(risk_cfg["max_aggregate_open_risk_pct"]),
            daily_loss_halt_pct=float(risk_cfg["daily_loss_halt_pct"]),
            quote_max_age_seconds=int(data_cfg["quote_max_age_seconds"]),
            fractional_precision=int(account_cfg["fractional_precision"]),
            quote_future_tolerance_seconds=int(
                paper_config["execution"]["quote_future_tolerance_seconds"]
            ),
        )
    )
    qty, _, _ = manager.calculate_quantity(
        float(account.equity), float(available_cash), float(maximum_entry), float(stop)
    )
    quantity = Decimal(str(qty)).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
    # Alpaca documents fractional equity orders as DAY-only. A swing-trade
    # protective stop must remain active overnight, so the GTC OTO path is
    # deliberately whole-share only.
    quantity = quantity.to_integral_value(rounding=ROUND_DOWN)
    if quantity <= 0:
        raise PaperPolicyError(
            "risk/cash sizing produced zero whole shares; Alpaca fractional DAY orders cannot carry an overnight stop"
        )
    planned_loss = quantity * (maximum_entry - stop)
    risk_limit = account.equity * Decimal(str(risk_cfg["max_planned_loss_pct"]))
    estimated_cost = quantity * maximum_entry
    if planned_loss > risk_limit + Decimal("0.00000001"):
        raise PaperPolicyError("sizing exceeded the per-trade planned-loss limit")
    if estimated_cost > available_cash + Decimal("0.00000001"):
        raise PaperPolicyError("sizing exceeded cash-only buying power")
    return quantity, stop, maximum_entry, planned_loss, risk_limit


def authorize_entry_risk(
    *,
    client_order_id: str,
    symbol: str,
    account: PaperAccount,
    quote: PaperQuote,
    now: datetime,
    planned_loss: Decimal,
    day_start_equity: Decimal,
    state: OperationalState,
    strategy_config: dict[str, Any],
    kill_switch: bool,
) -> None:
    risk_cfg = strategy_config["risk"]
    manager = RiskManager(
        RiskPolicy(
            max_planned_loss_pct=float(risk_cfg["max_planned_loss_pct"]),
            max_aggregate_open_risk_pct=float(risk_cfg["max_aggregate_open_risk_pct"]),
            daily_loss_halt_pct=float(risk_cfg["daily_loss_halt_pct"]),
            quote_max_age_seconds=int(strategy_config["data"]["quote_max_age_seconds"]),
            fractional_precision=int(strategy_config["account"]["fractional_precision"]),
            quote_future_tolerance_seconds=QUOTE_FUTURE_TOLERANCE_SECONDS,
        )
    )
    if not day_start_equity.is_finite() or day_start_equity <= 0:
        raise PaperPolicyError("observed trading-day start equity is invalid")
    today = now.date()
    manager.start_day(today, float(day_start_equity))
    manager.state.open_risk_by_symbol = {
        key: float(value.planned_loss) for key, value in state.positions.items()
    }
    manager.state.open_risk_by_symbol.update(
        {key: float(value) for key, value in state.pending_entry_risk_by_symbol.items()}
    )
    manager.state.daily_realized_pnl = float(state.realized_pnl(today))
    manager.set_kill_switch(kill_switch)
    decision = manager.authorize_entry(
        order_id=client_order_id,
        symbol=symbol,
        equity=float(account.equity),
        planned_loss=float(planned_loss),
        quote_timestamp=quote.timestamp,
        decision_timestamp=now,
    )
    if not decision.accepted:
        raise PaperPolicyError(f"risk manager rejected entry: {decision.reason}")


def require_no_symbol_conflict(
    symbol: str,
    positions: list[PaperPosition],
    orders: list[PaperOrder],
    terminal_statuses: set[str],
) -> None:
    if any(position.symbol == symbol for position in positions):
        raise PaperPolicyError("position already exists for symbol")
    if any(
        order.symbol == symbol and order.status not in terminal_statuses
        for order in _flatten_orders(orders)
    ):
        raise PaperPolicyError("working order already exists for symbol")


def daily_loss_day(now: datetime) -> date:
    if now.tzinfo is None:
        raise PaperPolicyError("timestamp must be timezone-aware")
    return now.date()


def _flatten_orders(orders: list[PaperOrder]) -> list[PaperOrder]:
    flattened: list[PaperOrder] = []
    for order in orders:
        flattened.append(order)
        flattened.extend(_flatten_orders(list(order.legs)))
    return flattened
