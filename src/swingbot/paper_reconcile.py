from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from .paper_journal import PaperJournal
from .paper_models import OrderProposal, PaperAccount, PaperOrder, PaperPosition, decimal_string
from .paper_state import ManagedPosition, reduce_events


@dataclass(frozen=True)
class ReconciliationReport:
    ok: bool
    issues: tuple[str, ...]
    broker_position_count: int
    managed_position_count: int
    working_order_count: int


def flatten_orders(orders: list[PaperOrder]) -> list[PaperOrder]:
    flattened: list[PaperOrder] = []
    for order in orders:
        flattened.append(order)
        flattened.extend(flatten_orders(list(order.legs)))
    return flattened


def parent_contains_leg(orders: list[PaperOrder], parent_id: str, leg_id: str) -> bool:
    parent = next((order for order in orders if order.order_id == parent_id), None)
    if parent is None:
        return False
    return any(leg.order_id == leg_id for leg in flatten_orders(list(parent.legs)))


class PaperReconciler:
    def __init__(
        self,
        journal: PaperJournal,
        paper_config: dict[str, Any],
        strategy_config: dict[str, Any],
    ):
        self.journal = journal
        self.paper_config = paper_config
        self.strategy_config = strategy_config

    def reconcile(
        self,
        *,
        account: PaperAccount,
        positions: list[PaperPosition],
        orders: list[PaperOrder],
        now: datetime,
    ) -> ReconciliationReport:
        self.journal.verify_integrity()
        issues: list[str] = self._observe_known_orders(orders, now)
        state = reduce_events(self.journal.events())
        terminal = set(self.paper_config["monitoring"]["order_terminal_statuses"])
        working = [order for order in flatten_orders(orders) if order.status not in terminal]

        binding = self.journal.account_binding()
        if not binding or binding.get("account_id") != account.account_id:
            issues.append("account_binding_mismatch")
        if account.status != "ACTIVE" or account.currency != self.paper_config["account"]["currency"]:
            issues.append("account_status_or_currency_invalid")
        if account.trading_blocked or account.account_blocked or account.trade_suspended_by_user:
            issues.append("account_trading_blocked")
        if account.equity <= 0 or account.cash < 0:
            issues.append("account_equity_or_cash_invalid")
        if account.short_market_value != 0 or any(position.side != "long" for position in positions):
            issues.append("short_position_detected")

        known_ids = set(state.known_broker_order_ids)
        known_parent_ids = {item.broker_order_id for item in state.submitted_by_client_id.values()}
        broker_order_ids = {order.order_id for order in flatten_orders(orders)}
        for submitted in state.submitted_by_client_id.values():
            status = state.last_order_status.get(submitted.broker_order_id, "")
            if status not in terminal and submitted.broker_order_id not in broker_order_ids:
                issues.append(f"known_working_order_missing_from_broker:{submitted.broker_order_id}")
        for order in orders:
            if order.order_id in known_parent_ids:
                known_ids.update(leg.order_id for leg in flatten_orders(list(order.legs)))
        for order in working:
            if order.order_id not in known_ids:
                issues.append(f"unknown_working_order:{order.order_id}")

        broker_by_symbol = {position.symbol: position for position in positions}
        for symbol, broker_position in broker_by_symbol.items():
            managed = state.positions.get(symbol)
            if managed is None:
                if not self._known_partial_fill(symbol, orders, state):
                    issues.append(f"unknown_broker_position:{symbol}")
                else:
                    issues.append(f"partially_filled_entry_unprotected:{symbol}")
                continue
            if abs(broker_position.quantity - managed.quantity) > Decimal("0.000001"):
                issues.append(f"position_quantity_mismatch:{symbol}")

        for symbol, managed in state.positions.items():
            if symbol not in broker_by_symbol:
                issues.append(f"locally_open_but_broker_flat:{symbol}")
                continue
            stop = next((order for order in working if order.order_id == managed.stop_order_id), None)
            if stop is None:
                issues.append(f"missing_working_native_stop:{symbol}")
            elif stop.side != "sell" or stop.order_type not in {"stop", "stop_limit"}:
                issues.append(f"invalid_native_stop:{symbol}")
            elif stop.stop_price != managed.stop_price:
                issues.append(f"native_stop_price_mismatch:{symbol}")
            elif stop.quantity != managed.quantity:
                issues.append(f"native_stop_quantity_mismatch:{symbol}")
            elif stop.time_in_force != "gtc":
                issues.append(f"native_stop_not_gtc:{symbol}")
            elif not parent_contains_leg(
                orders, managed.parent_order_id, managed.stop_order_id
            ):
                issues.append(f"native_stop_parent_mismatch:{symbol}")

        aggregate_risk = sum(
            (position.planned_loss for position in state.positions.values()), Decimal("0")
        ) + sum(state.pending_entry_risk_by_symbol.values(), Decimal("0"))
        aggregate_limit = account.equity * Decimal(
            str(self.strategy_config["risk"]["max_aggregate_open_risk_pct"])
        )
        if aggregate_risk > aggregate_limit + Decimal("0.00000001"):
            issues.append("aggregate_open_risk_breach_observed")

        unique_issues = tuple(dict.fromkeys(issues))
        if unique_issues and not self.journal.kill_switch_latched():
            self.journal.append(
                "kill_switch_latched",
                {"reason": "reconciliation_mismatch", "issues": list(unique_issues)},
                occurred_at=now,
            )
        return ReconciliationReport(
            ok=not unique_issues,
            issues=unique_issues,
            broker_position_count=len(positions),
            managed_position_count=len(state.positions),
            working_order_count=len(working),
        )

    def _observe_known_orders(self, orders: list[PaperOrder], now: datetime) -> list[str]:
        issues: list[str] = []
        state = reduce_events(self.journal.events())
        by_client = {order.client_order_id: order for order in orders if order.client_order_id}
        for client_id, submitted in state.submitted_by_client_id.items():
            order = by_client.get(client_id)
            if order is None:
                continue
            prior = state.last_order_status.get(order.order_id)
            if prior != order.status:
                self.journal.append(
                    "order_status_observed",
                    {
                        "broker_order_id": order.order_id,
                        "client_order_id": client_id,
                        "status": order.status,
                        "filled_quantity": decimal_string(order.filled_quantity),
                        "filled_average_price": decimal_string(order.filled_average_price)
                        if order.filled_average_price is not None else None,
                        "leg_order_ids": [leg.order_id for leg in flatten_orders(list(order.legs))],
                    },
                    proposal_id=submitted.proposal_id,
                    occurred_at=now,
                )
            proposal = self.journal.get_proposal(submitted.proposal_id)
            if submitted.action == "entry_oto":
                issues.extend(self._sync_entry(proposal, order, now))
            elif submitted.action == "close_position":
                issues.extend(self._sync_close(proposal, order, now))
        return issues

    def _sync_entry(
        self, proposal: OrderProposal, order: PaperOrder, now: datetime
    ) -> list[str]:
        issues: list[str] = []
        state = reduce_events(self.journal.events())
        if proposal.symbol not in state.positions and order.status == "filled":
            if order.filled_average_price is None:
                return [f"filled_entry_missing_average_price:{proposal.symbol}"]
            stops = [
                leg for leg in flatten_orders(list(order.legs))
                if leg.side == "sell" and leg.order_type in {"stop", "stop_limit"}
            ]
            if len(stops) != 1:
                return [f"filled_entry_without_single_native_stop:{proposal.symbol}"]
            stop = stops[0]
            if order.filled_quantity != proposal.quantity:
                return [f"filled_entry_quantity_mismatch:{proposal.symbol}"]
            actual_planned_loss = order.filled_quantity * (
                order.filled_average_price - (proposal.stop_price or Decimal("0"))
            )
            if actual_planned_loss <= 0:
                issues.append(f"filled_entry_invalid_actual_risk:{proposal.symbol}")
            if actual_planned_loss > proposal.risk_limit + Decimal("0.00000001"):
                issues.append(f"filled_entry_risk_limit_breach:{proposal.symbol}")
                self.journal.append(
                    "risk_limit_breach_observed",
                    {
                        "symbol": proposal.symbol,
                        "actual_planned_loss": decimal_string(actual_planned_loss),
                        "approved_risk_limit": decimal_string(proposal.risk_limit),
                    },
                    proposal_id=proposal.proposal_id,
                    occurred_at=now,
                )
            self.journal.append(
                "entry_filled",
                {
                    "symbol": proposal.symbol,
                    "quantity": decimal_string(order.filled_quantity),
                    "entry_price": decimal_string(order.filled_average_price),
                    "entry_date": now.date().isoformat(),
                    "planned_loss": decimal_string(actual_planned_loss),
                    "proposal_planned_loss": decimal_string(proposal.planned_loss),
                    "stop_price": decimal_string(proposal.stop_price or Decimal("0")),
                    "parent_order_id": order.order_id,
                    "stop_order_id": stop.order_id,
                    "client_order_id": proposal.client_order_id,
                },
                proposal_id=proposal.proposal_id,
                occurred_at=now,
            )
            state = reduce_events(self.journal.events())
        managed = state.positions.get(proposal.symbol)
        if managed is None:
            return issues
        stop_order = next(
            (
                leg for leg in flatten_orders(list(order.legs))
                if leg.order_id == managed.stop_order_id
            ),
            None,
        )
        if stop_order and stop_order.status == "filled":
            issues.extend(
                self._record_close(
                    managed, stop_order, "protective_stop", now, proposal.proposal_id
                )
            )
        return issues

    def _sync_close(
        self, proposal: OrderProposal, order: PaperOrder, now: datetime
    ) -> list[str]:
        state = reduce_events(self.journal.events())
        managed = state.positions.get(proposal.symbol)
        if managed and order.status == "filled":
            return self._record_close(
                managed,
                order,
                proposal.exit_reason or "approved_exit",
                now,
                proposal.proposal_id,
            )
        return []

    def _record_close(
        self,
        managed: ManagedPosition,
        order: PaperOrder,
        reason: str,
        now: datetime,
        proposal_id: str,
    ) -> list[str]:
        if order.filled_average_price is None:
            return [f"filled_exit_missing_average_price:{managed.symbol}"]
        if order.filled_quantity != managed.quantity:
            return [f"filled_exit_quantity_mismatch:{managed.symbol}"]
        pnl = (order.filled_average_price - managed.entry_price) * order.filled_quantity
        self.journal.append(
            "position_closed",
            {
                "symbol": managed.symbol,
                "quantity": decimal_string(order.filled_quantity),
                "exit_price": decimal_string(order.filled_average_price),
                "closed_date": now.date().isoformat(),
                "realized_pnl": decimal_string(pnl),
                "reason": reason,
                "broker_order_id": order.order_id,
            },
            proposal_id=proposal_id,
            occurred_at=now,
        )
        return []

    @staticmethod
    def _known_partial_fill(
        symbol: str, orders: list[PaperOrder], state: Any
    ) -> bool:
        known_clients = set(state.submitted_by_client_id)
        return any(
            order.symbol == symbol
            and order.client_order_id in known_clients
            and order.status == "partially_filled"
            and order.filled_quantity > 0
            for order in orders
        )
