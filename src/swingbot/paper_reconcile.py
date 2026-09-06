from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from .paper_journal import PaperJournal
from .paper_models import OrderProposal, PaperAccount, PaperOrder, PaperPosition, decimal_string, parse_timestamp
from .paper_state import ManagedPosition, reduce_events


NON_PROTECTIVE_STOP_STATUSES = {
    "calculated",
    "held",
    "partially_filled",
    "pending_cancel",
    "pending_replace",
    "suspended",
}


@dataclass(frozen=True)
class ReconciliationReport:
    ok: bool
    issues: tuple[str, ...]
    warnings: tuple[str, ...]
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
    return any(leg.order_id == leg_id for leg in parent.legs)


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
        flattened = flatten_orders(orders)
        terminal = set(self.paper_config["monitoring"]["order_terminal_statuses"])
        working_statuses = set(self.paper_config["monitoring"]["order_working_statuses"])
        known_statuses = terminal | working_statuses
        issues: list[str] = []
        warnings: list[str] = []
        for order in flattened:
            if order.status not in known_statuses:
                issues.append(f"unknown_order_status:{order.order_id}:{order.status}")
            fill_issue = self._order_fill_state_issue(order, now)
            if fill_issue:
                issues.append(f"invalid_order_fill_state:{order.order_id}:{fill_issue}")
        client_ids = [order.client_order_id for order in orders if order.client_order_id]
        for client_id in sorted(set(client_ids)):
            if client_ids.count(client_id) > 1:
                issues.append(f"duplicate_broker_client_order_id:{client_id}")
        issues.extend(
            self._recover_started_submissions(
                orders,
                now,
                known_statuses=known_statuses,
                working_statuses=working_statuses,
                terminal_statuses=terminal,
            )
        )
        issues.extend(
            self._observe_known_orders(orders, now, known_statuses=known_statuses)
        )
        self._record_account_snapshot(account, positions, now)
        state = reduce_events(self.journal.events())
        working = [order for order in flattened if order.status in working_statuses]

        binding = self.journal.account_binding()
        if not binding or binding.get("account_id") != account.account_id:
            issues.append("account_binding_mismatch")
        if account.status != "ACTIVE" or account.currency != self.paper_config["account"]["currency"]:
            issues.append("account_status_or_currency_invalid")
        if account.trading_blocked or account.account_blocked or account.trade_suspended_by_user:
            issues.append("account_trading_blocked")
        account_values = (
            account.equity,
            account.last_equity,
            account.cash,
            account.non_marginable_buying_power,
            account.buying_power,
            account.multiplier,
            account.long_market_value,
            account.short_market_value,
        )
        if (
            not all(value.is_finite() for value in account_values)
            or account.equity <= 0
            or account.cash < 0
            or account.non_marginable_buying_power < 0
            or account.buying_power < 0
            or account.multiplier <= 0
            or account.long_market_value < 0
        ):
            issues.append("account_equity_or_cash_invalid")
        if account.short_market_value != 0 or any(position.side != "long" for position in positions):
            issues.append("short_position_detected")
        accounting_tolerance = Decimal(
            str(self.paper_config["account"]["initial_equity_tolerance"])
        )
        if all(value.is_finite() for value in account_values) and abs(
            account.equity
            - (account.cash + account.long_market_value + account.short_market_value)
        ) > accounting_tolerance:
            issues.append("account_equity_identity_mismatch")
        position_symbols = [position.symbol for position in positions]
        for symbol in sorted(set(position_symbols)):
            if position_symbols.count(symbol) > 1:
                issues.append(f"duplicate_broker_position:{symbol}")
        invalid_position_symbols: set[str] = set()
        for position in positions:
            if (
                not all(
                    value.is_finite()
                    for value in (
                        position.quantity,
                        position.average_entry_price,
                        position.current_price,
                        position.market_value,
                    )
                )
                or position.quantity <= 0
                or position.average_entry_price <= 0
                or position.current_price <= 0
                or position.market_value < 0
            ):
                issues.append(f"invalid_broker_position_values:{position.symbol}")
                invalid_position_symbols.add(position.symbol)
            elif abs(
                position.market_value - position.quantity * position.current_price
            ) > accounting_tolerance:
                issues.append(f"broker_position_market_value_mismatch:{position.symbol}")

        valid_market_value = sum(
            (
                position.market_value
                for position in positions
                if position.symbol not in invalid_position_symbols
            ),
            Decimal("0"),
        )
        if (
            account.long_market_value.is_finite()
            and abs(account.long_market_value - valid_market_value) > accounting_tolerance
        ):
            issues.append("account_position_market_value_mismatch")

        known_ids = set(state.known_broker_order_ids)
        known_parent_ids = {item.broker_order_id for item in state.submitted_by_client_id.values()}
        broker_order_ids = {order.order_id for order in flattened}
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

        managed_stop_ids = {
            managed.stop_order_id for managed in state.positions.values()
        }
        pending_stop_ids = {
            leg.order_id
            for parent in orders
            for leg in flatten_orders(list(parent.legs))
            if parent.client_order_id in state.submitted_by_client_id
            and state.submitted_by_client_id[parent.client_order_id].action == "entry_oto"
            and parent.status in working_statuses
        }
        for order in working:
            if (
                order.side == "sell"
                and order.order_type == "stop"
                and order.order_id not in managed_stop_ids
                and order.order_id not in pending_stop_ids
            ):
                issues.append(f"orphan_working_native_stop:{order.order_id}")

        for parent in orders:
            submitted = state.submitted_by_client_id.get(parent.client_order_id)
            if (
                submitted is None
                or submitted.action != "entry_oto"
                or parent.status not in working_statuses
                or submitted.symbol in state.positions
            ):
                continue
            proposal = self.journal.get_proposal(submitted.proposal_id)
            if (
                parent.symbol != proposal.symbol
                or parent.side != "buy"
                or parent.order_type != "market"
                or parent.time_in_force != "gtc"
                or parent.order_class != "oto"
                or parent.quantity != proposal.quantity
                or parent.extended_hours
            ):
                issues.append(f"pending_entry_order_mismatch:{submitted.symbol}")
                continue
            if len(parent.legs) != 1:
                issues.append(f"pending_entry_native_stop_invalid:{submitted.symbol}")
                continue
            stop = parent.legs[0]
            if (
                stop.symbol != submitted.symbol
                or stop.side != "sell"
                or stop.order_type != "stop"
                or stop.time_in_force != "gtc"
                or stop.status not in working_statuses
                or stop.status in NON_PROTECTIVE_STOP_STATUSES - {"held"}
                or stop.quantity != parent.quantity
                or stop.stop_price != proposal.stop_price
                or stop.extended_hours
                or stop.legs
            ):
                issues.append(f"pending_entry_native_stop_invalid:{submitted.symbol}")

        broker_by_symbol = {position.symbol: position for position in positions}
        for symbol, broker_position in broker_by_symbol.items():
            if symbol in invalid_position_symbols:
                continue
            managed = state.positions.get(symbol)
            if managed is None:
                if not self._known_partial_fill(symbol, orders, state):
                    issues.append(f"unknown_broker_position:{symbol}")
                else:
                    issues.append(f"partially_filled_entry_unprotected:{symbol}")
                continue
            if abs(broker_position.quantity - managed.quantity) > Decimal("0.000001"):
                issues.append(f"position_quantity_mismatch:{symbol}")
            if (
                abs(broker_position.average_entry_price - managed.entry_price)
                > accounting_tolerance
            ):
                issues.append(f"position_cost_basis_mismatch:{symbol}")

        for symbol, managed in state.positions.items():
            if symbol not in broker_by_symbol:
                issues.append(f"locally_open_but_broker_flat:{symbol}")
                continue
            stop = next((order for order in working if order.order_id == managed.stop_order_id), None)
            if stop is None:
                issues.append(f"missing_working_native_stop:{symbol}")
            elif (
                stop.symbol != symbol
                or stop.side != "sell"
                or stop.order_type != "stop"
                or stop.extended_hours
                or bool(stop.legs)
            ):
                issues.append(f"invalid_native_stop:{symbol}")
            elif stop.stop_price != managed.stop_price:
                issues.append(f"native_stop_price_mismatch:{symbol}")
            elif stop.quantity != managed.quantity:
                issues.append(f"native_stop_quantity_mismatch:{symbol}")
            elif stop.time_in_force != "gtc":
                issues.append(f"native_stop_not_gtc:{symbol}")
            elif stop.status in NON_PROTECTIVE_STOP_STATUSES:
                issues.append(f"native_stop_not_active:{symbol}:{stop.status}")
            elif not parent_contains_leg(
                orders, managed.parent_order_id, managed.stop_order_id
            ):
                issues.append(f"native_stop_parent_mismatch:{symbol}")

        if account.equity.is_finite() and account.equity > 0:
            aggregate_risk = sum(
                (position.planned_loss for position in state.positions.values()), Decimal("0")
            ) + sum(state.pending_entry_risk_by_symbol.values(), Decimal("0"))
            aggregate_limit = account.equity * Decimal(
                str(self.strategy_config["risk"]["max_aggregate_open_risk_pct"])
            )
            if aggregate_risk > aggregate_limit + Decimal("0.00000001"):
                # Market-driven equity changes can move the ratio above 3%
                # without changing any authorized dollar risk. This blocks
                # subsequent entries in authorize_entry_risk, but is not an
                # unexplained broker mismatch and must not deadlock exits.
                warnings.append("aggregate_open_risk_breach_observed")

        expected_cash = self._expected_cash_from_ledger()
        if (
            expected_cash is not None
            and account.cash.is_finite()
            and abs(account.cash - expected_cash) > accounting_tolerance
        ):
            issues.append("cash_ledger_mismatch")

        unique_issues = tuple(dict.fromkeys(issues))
        if unique_issues and not self.journal.kill_switch_latched():
            self.journal._append_state(
                "kill_switch_latched",
                {"reason": "reconciliation_mismatch", "issues": list(unique_issues)},
                occurred_at=now,
            )
        return ReconciliationReport(
            ok=not unique_issues,
            issues=unique_issues,
            warnings=tuple(dict.fromkeys(warnings)),
            broker_position_count=len(positions),
            managed_position_count=len(state.positions),
            working_order_count=len(working),
        )

    def _recover_started_submissions(
        self,
        orders: list[PaperOrder],
        now: datetime,
        *,
        known_statuses: set[str],
        working_statuses: set[str],
        terminal_statuses: set[str],
    ) -> list[str]:
        issues: list[str] = []
        state = reduce_events(self.journal.events())
        for client_id, attempt in state.submission_attempts_by_client_id.items():
            if client_id in state.submitted_by_client_id:
                continue
            if not self.journal.permit_stage_claimed_for_proposal(
                attempt.proposal_id, "submit_order"
            ):
                continue
            matches = [order for order in orders if order.client_order_id == client_id]
            if len(matches) != 1:
                issues.append(f"claimed_submission_has_uncertain_broker_outcome:{client_id}")
                continue
            order = matches[0]
            proposal = self.journal.get_proposal(attempt.proposal_id)
            if not self._recovered_order_matches(
                proposal, order, known_statuses, working_statuses
            ):
                issues.append(f"recovered_order_mismatch:{client_id}")
                continue
            self.journal._append_state(
                "order_submitted",
                {
                    "action": proposal.action,
                    "symbol": proposal.symbol,
                    "client_order_id": proposal.client_order_id,
                    "broker_order_id": order.order_id,
                    "status": order.status,
                    "filled_quantity": decimal_string(order.filled_quantity),
                    "filled_average_price": decimal_string(order.filled_average_price)
                    if order.filled_average_price is not None else None,
                    "filled_at": order.filled_at.isoformat()
                    if order.filled_at is not None else None,
                    "planned_loss": decimal_string(proposal.planned_loss),
                    "recovered_after_restart": True,
                },
                proposal_id=proposal.proposal_id,
                occurred_at=now,
            )
            if order.status in terminal_statuses - {"filled"}:
                issues.append(
                    f"recovered_broker_order_not_working:{order.order_id}:{order.status}"
                )
        return issues

    @staticmethod
    def _recovered_order_matches(
        proposal: OrderProposal,
        order: PaperOrder,
        known_statuses: set[str],
        working_statuses: set[str],
    ) -> bool:
        common = (
            order.client_order_id == proposal.client_order_id
            and order.symbol == proposal.symbol
            and order.quantity == proposal.quantity
            and order.status in known_statuses
            and not order.extended_hours
        )
        if not common:
            return False
        if proposal.action == "entry_oto":
            if (
                order.side != "buy"
                or order.order_type != "market"
                or order.time_in_force != "gtc"
                or order.order_class != "oto"
                or len(order.legs) != 1
            ):
                return False
            stop = order.legs[0]
            return (
                stop.symbol == proposal.symbol
                and stop.side == "sell"
                and stop.order_type == "stop"
                and stop.time_in_force == "gtc"
                and stop.quantity == proposal.quantity
                and stop.stop_price == proposal.stop_price
                and (
                    stop.status in working_statuses
                    or (order.status == "filled" and stop.status == "filled")
                )
                and not stop.extended_hours
                and not stop.legs
            )
        if proposal.action == "close_position":
            return (
                order.side == "sell"
                and order.order_type == "market"
                and order.time_in_force == "day"
                and order.order_class == "simple"
                and not order.legs
            )
        return False

    def _observe_known_orders(
        self,
        orders: list[PaperOrder],
        now: datetime,
        *,
        known_statuses: set[str],
    ) -> list[str]:
        issues: list[str] = []
        state = reduce_events(self.journal.events())
        by_client: dict[str, list[PaperOrder]] = {}
        for order in orders:
            if order.client_order_id:
                by_client.setdefault(order.client_order_id, []).append(order)
        terminal = set(self.paper_config["monitoring"]["order_terminal_statuses"])
        for client_id, submitted in state.submitted_by_client_id.items():
            matches = by_client.get(client_id, [])
            if not matches:
                continue
            if len(matches) != 1:
                issues.append(f"duplicate_known_client_order_id:{client_id}")
                continue
            order = matches[0]
            if order.order_id != submitted.broker_order_id:
                issues.append(f"broker_order_id_changed_for_client:{client_id}")
                continue
            if order.filled_quantity > 0 and order.filled_quantity < order.quantity:
                issues.append(
                    f"partially_filled_{'entry_unprotected' if submitted.action == 'entry_oto' else 'exit_unprotected'}:{submitted.symbol}"
                )
            proposal = self.journal.get_proposal(submitted.proposal_id)
            if not self._observed_order_matches(proposal, order, known_statuses):
                issues.append(f"observed_order_mismatch:{client_id}")
                continue
            prior = state.last_order_status.get(submitted.broker_order_id)
            prior_filled = state.last_filled_quantity.get(
                submitted.broker_order_id, Decimal("0")
            )
            prior_average = state.last_filled_average_price.get(submitted.broker_order_id)
            prior_filled_at = state.last_filled_at.get(submitted.broker_order_id)
            current_filled_at = (
                order.filled_at.isoformat() if order.filled_at is not None else None
            )
            observation_changed = (
                prior != order.status
                or prior_filled != order.filled_quantity
                or prior_average != order.filled_average_price
                or prior_filled_at != current_filled_at
            )
            invalid_transition = False
            if prior in terminal and observation_changed:
                issues.append(
                    f"terminal_order_state_changed:{order.order_id}:{prior}:{order.status}"
                )
                invalid_transition = True
            if order.filled_quantity < prior_filled or order.filled_quantity > order.quantity:
                issues.append(f"order_filled_quantity_invalid:{order.order_id}")
                invalid_transition = True
            if (
                order.filled_quantity == prior_filled
                and prior_average is not None
                and order.filled_average_price != prior_average
            ):
                issues.append(f"order_filled_average_changed:{order.order_id}")
                invalid_transition = True
            if prior_filled_at is not None and current_filled_at != prior_filled_at:
                issues.append(f"order_filled_timestamp_changed:{order.order_id}")
                invalid_transition = True
            if observation_changed and not invalid_transition:
                self.journal._append_state(
                    "order_status_observed",
                    {
                        "broker_order_id": order.order_id,
                        "client_order_id": client_id,
                        "status": order.status,
                        "filled_quantity": decimal_string(order.filled_quantity),
                        "filled_average_price": decimal_string(order.filled_average_price)
                        if order.filled_average_price is not None else None,
                        "filled_at": order.filled_at.isoformat()
                        if order.filled_at is not None else None,
                        "leg_order_ids": [
                            leg.order_id for leg in flatten_orders(list(order.legs))
                        ],
                    },
                    proposal_id=submitted.proposal_id,
                    occurred_at=now,
                )
            if invalid_transition:
                continue
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
        if order.status == "partially_filled" or (
            order.filled_quantity > 0 and order.filled_quantity < order.quantity
        ):
            return [f"partially_filled_entry_unprotected:{proposal.symbol}"]
        if (
            proposal.client_order_id not in state.entry_filled_client_order_ids
            and order.status == "filled"
        ):
            if (
                order.filled_average_price is None
                or not order.filled_average_price.is_finite()
                or order.filled_average_price <= 0
            ):
                return [f"filled_entry_missing_average_price:{proposal.symbol}"]
            if (
                order.filled_at is None
                or order.filled_at.tzinfo is None
                or order.filled_at > now
            ):
                return [f"filled_entry_missing_or_invalid_timestamp:{proposal.symbol}"]
            if len(order.legs) != 1:
                return [f"filled_entry_without_single_native_stop:{proposal.symbol}"]
            stop = order.legs[0]
            working_statuses = set(
                self.paper_config["monitoring"]["order_working_statuses"]
            )
            active_stop = (
                stop.status in working_statuses
                and stop.status not in NON_PROTECTIVE_STOP_STATUSES
            )
            completed_stop = stop.status == "filled"
            if (
                stop.symbol != proposal.symbol
                or stop.side != "sell"
                or stop.order_type != "stop"
                or stop.time_in_force != "gtc"
                or stop.quantity != proposal.quantity
                or stop.stop_price != proposal.stop_price
                or stop.extended_hours
                or bool(stop.legs)
                or not (active_stop or completed_stop)
            ):
                return [f"filled_entry_stop_not_active:{proposal.symbol}:{stop.status}"]
            if completed_stop:
                stop_issue = self._order_fill_state_issue(stop, now)
                if stop_issue is not None:
                    return [
                        f"filled_entry_stop_has_invalid_fill:{proposal.symbol}:{stop_issue}"
                    ]
                assert stop.filled_at is not None and order.filled_at is not None
                if stop.filled_at < order.filled_at:
                    return [f"filled_entry_stop_precedes_entry:{proposal.symbol}"]
            if order.filled_quantity != proposal.quantity:
                return [f"filled_entry_quantity_mismatch:{proposal.symbol}"]
            actual_planned_loss = order.filled_quantity * (
                order.filled_average_price - (proposal.stop_price or Decimal("0"))
            )
            if actual_planned_loss <= 0:
                issues.append(f"filled_entry_invalid_actual_risk:{proposal.symbol}")
            if actual_planned_loss > proposal.risk_limit + Decimal("0.00000001"):
                issues.append(f"filled_entry_risk_limit_breach:{proposal.symbol}")
                self.journal._append_state(
                    "risk_limit_breach_observed",
                    {
                        "symbol": proposal.symbol,
                        "actual_planned_loss": decimal_string(actual_planned_loss),
                        "approved_risk_limit": decimal_string(proposal.risk_limit),
                    },
                    proposal_id=proposal.proposal_id,
                    occurred_at=now,
                )
            self.journal._append_state(
                "entry_filled",
                {
                    "symbol": proposal.symbol,
                    "quantity": decimal_string(order.filled_quantity),
                    "entry_price": decimal_string(order.filled_average_price),
                    "entry_date": order.filled_at.date().isoformat(),
                    "planned_loss": decimal_string(actual_planned_loss),
                    "proposal_planned_loss": decimal_string(proposal.planned_loss),
                    "stop_price": decimal_string(proposal.stop_price or Decimal("0")),
                    "parent_order_id": order.order_id,
                    "stop_order_id": stop.order_id,
                    "client_order_id": proposal.client_order_id,
                },
                proposal_id=proposal.proposal_id,
                occurred_at=order.filled_at,
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
            if stop_order.order_id not in state.closed_broker_order_ids:
                issues.extend(
                    self._record_close(
                        managed, stop_order, "protective_stop", now, proposal.proposal_id
                    )
                )
        return issues

    def _sync_close(
        self, proposal: OrderProposal, order: PaperOrder, now: datetime
    ) -> list[str]:
        if order.status == "partially_filled" or (
            order.filled_quantity > 0 and order.filled_quantity < order.quantity
        ):
            return [f"partially_filled_exit_unprotected:{proposal.symbol}"]
        state = reduce_events(self.journal.events())
        managed = state.positions.get(proposal.symbol)
        if (
            managed
            and order.status == "filled"
            and order.order_id not in state.closed_broker_order_ids
        ):
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
        if (
            order.filled_average_price is None
            or not order.filled_average_price.is_finite()
            or order.filled_average_price <= 0
        ):
            return [f"filled_exit_missing_average_price:{managed.symbol}"]
        if (
            order.filled_at is None
            or order.filled_at.tzinfo is None
            or order.filled_at > now
        ):
            return [f"filled_exit_missing_or_invalid_timestamp:{managed.symbol}"]
        if order.filled_quantity != managed.quantity:
            return [f"filled_exit_quantity_mismatch:{managed.symbol}"]
        # The entry may have been imported on an earlier poll. Validate causality
        # here, in the shared stop/approved-exit close path, before changing state.
        entry = next((
            event for event in reversed(self.journal.events())
            if event["event_type"] == "entry_filled"
            and event["payload"].get("client_order_id") == managed.entry_client_order_id
        ), None)
        if entry is None:
            return [f"filled_exit_missing_entry_timestamp:{managed.symbol}"]
        if order.filled_at < parse_timestamp(str(entry["occurred_at"])):
            return [f"filled_exit_precedes_entry:{managed.symbol}"]
        pnl = (order.filled_average_price - managed.entry_price) * order.filled_quantity
        self.journal._append_state(
            "position_closed",
            {
                "symbol": managed.symbol,
                "quantity": decimal_string(order.filled_quantity),
                "exit_price": decimal_string(order.filled_average_price),
                "closed_date": order.filled_at.date().isoformat(),
                "realized_pnl": decimal_string(pnl),
                "reason": reason,
                "broker_order_id": order.order_id,
            },
            proposal_id=proposal_id,
            occurred_at=order.filled_at,
        )
        return []

    def _record_account_snapshot(
        self,
        account: PaperAccount,
        positions: list[PaperPosition],
        now: datetime,
    ) -> None:
        previous = self.journal.latest_payload("account_snapshot_observed")
        prior_cash = Decimal(str(previous["cash"])) if previous else account.cash
        prior_equity = Decimal(str(previous["equity"])) if previous else account.equity
        observed_day_start = (
            self.journal.first_observed_equity_for_day(now) or account.equity
        )
        self.journal._append_state(
            "account_snapshot_observed",
            {
                "account_number_suffix": account.account_number[-4:],
                "status": account.status,
                "currency": account.currency,
                "equity": decimal_string(account.equity),
                "last_equity": decimal_string(account.last_equity),
                "observed_day_start_equity": decimal_string(observed_day_start),
                "cash": decimal_string(account.cash),
                "non_marginable_buying_power": decimal_string(
                    account.non_marginable_buying_power
                ),
                "long_market_value": decimal_string(account.long_market_value),
                "short_market_value": decimal_string(account.short_market_value),
                "day_pnl": decimal_string(account.equity - account.last_equity),
                "observed_day_pnl": decimal_string(
                    account.equity - observed_day_start
                ),
                "cash_change_since_prior_snapshot": decimal_string(
                    account.cash - prior_cash
                ),
                "equity_change_since_prior_snapshot": decimal_string(
                    account.equity - prior_equity
                ),
                "positions": [
                    {
                        "symbol": position.symbol,
                        "side": position.side,
                        "quantity": decimal_string(position.quantity),
                        "average_entry_price": decimal_string(
                            position.average_entry_price
                        ),
                        "current_price": decimal_string(position.current_price),
                        "market_value": decimal_string(position.market_value),
                    }
                    for position in sorted(positions, key=lambda item: item.symbol)
                ],
            },
            occurred_at=now,
        )

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

    @staticmethod
    def _observed_order_matches(
        proposal: OrderProposal,
        order: PaperOrder,
        known_statuses: set[str],
    ) -> bool:
        if (
            not order.order_id
            or order.client_order_id != proposal.client_order_id
            or order.symbol != proposal.symbol
            or order.quantity != proposal.quantity
            or order.status not in known_statuses
            or order.extended_hours
        ):
            return False
        if proposal.action == "entry_oto":
            if (
                order.side != "buy"
                or order.order_type != "market"
                or order.time_in_force != "gtc"
                or order.order_class != "oto"
                or len(order.legs) != 1
            ):
                return False
            stop = order.legs[0]
            return (
                bool(stop.order_id)
                and stop.symbol == proposal.symbol
                and stop.side == "sell"
                and stop.order_type == "stop"
                and stop.time_in_force == "gtc"
                and stop.quantity == proposal.quantity
                and stop.stop_price == proposal.stop_price
                and stop.status in known_statuses
                and not stop.extended_hours
                and not stop.legs
            )
        if proposal.action == "close_position":
            return (
                order.side == "sell"
                and order.order_type == "market"
                and order.time_in_force == "day"
                and order.order_class == "simple"
                and not order.legs
            )
        return False

    @staticmethod
    def _order_fill_state_issue(order: PaperOrder, now: datetime) -> str | None:
        if (
            not order.order_id
            or not order.symbol
            or not order.quantity.is_finite()
            or order.quantity <= 0
            or not order.filled_quantity.is_finite()
            or order.filled_quantity < 0
            or order.filled_quantity > order.quantity
        ):
            return "invalid_identity_or_quantity"
        if order.stop_price is not None and (
            not order.stop_price.is_finite() or order.stop_price <= 0
        ):
            return "invalid_stop_price"
        if order.filled_average_price is not None and (
            not order.filled_average_price.is_finite()
            or order.filled_average_price <= 0
        ):
            return "invalid_average_price"
        if order.filled_at is not None and (
            order.filled_at.tzinfo is None or order.filled_at > now
        ):
            return "invalid_fill_timestamp"
        if order.status == "filled":
            if (
                order.filled_quantity != order.quantity
                or order.filled_average_price is None
                or order.filled_at is None
            ):
                return "incomplete_filled_evidence"
        elif order.filled_quantity == order.quantity:
            return "fully_filled_quantity_with_nonfilled_status"
        elif order.filled_quantity == 0:
            if order.status == "partially_filled":
                return "partial_status_without_partial_quantity"
            if order.filled_average_price is not None or order.filled_at is not None:
                return "unfilled_order_has_fill_evidence"
        elif (
            order.status != "partially_filled"
            or order.filled_average_price is None
            or order.filled_at is None
        ):
            return "inconsistent_partial_fill_evidence"
        return None

    def _expected_cash_from_ledger(self) -> Decimal | None:
        events = self.journal.events()
        bindings = [
            event for event in events
            if event["event_type"] in {"account_bound", "paper_run_rebaselined"}
        ]
        if not bindings:
            return None
        binding = bindings[-1]
        payload = binding["payload"]
        initial = payload.get("initial_cash", payload.get("initial_equity"))
        if initial is None:
            return None
        expected = Decimal(str(initial))
        for event in events:
            if event["seq"] <= binding["seq"]:
                continue
            payload = event["payload"]
            if event["event_type"] == "entry_filled":
                expected -= Decimal(str(payload["quantity"])) * Decimal(
                    str(payload["entry_price"])
                )
            elif event["event_type"] == "position_closed":
                expected += Decimal(str(payload["quantity"])) * Decimal(
                    str(payload["exit_price"])
                )
        return expected
