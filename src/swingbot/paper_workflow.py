from __future__ import annotations

import copy
import hashlib
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from functools import wraps
from typing import Any, Callable, Mapping, Protocol, TypeVar

from .config import validate_config
from .paper_config import (
    FROZEN_STRATEGY_CONFIG_SHA256,
    FROZEN_STRATEGY_VALUE_SHA256,
    _validate as validate_paper_config,
)
from .paper_journal import PaperJournal
from .paper_models import (
    ApprovalPermit,
    LiveSignal,
    OrderProposal,
    PaperAccount,
    PaperAsset,
    PaperClock,
    PaperOrder,
    PaperPosition,
    PaperQuote,
    canonical_json,
    decimal_string,
    parse_timestamp,
)
from .paper_policy import (
    authorize_entry_risk,
    is_fractional,
    require_account_binding,
    require_asset,
    require_initial_account,
    require_market_open,
    require_no_symbol_conflict,
    require_operable_account,
    require_quote,
    size_entry,
)
from .paper_reconcile import (
    NON_PROTECTIVE_STOP_STATUSES,
    PaperReconciler,
    ReconciliationReport,
    flatten_orders,
)
from .paper_signals import latest_entry_decision, latest_exit_reason
from .paper_state import reduce_events


class Broker(Protocol):
    def get_account(self) -> PaperAccount: ...
    def get_clock(self) -> PaperClock: ...
    def trading_days(self, *, start: date, end: date) -> list[date]: ...
    def get_asset(self, symbol: str) -> PaperAsset: ...
    def latest_quote(self, symbol: str, *, feed: str) -> PaperQuote: ...
    def list_positions(self) -> list[PaperPosition]: ...
    def list_orders(self, *, status: str = "all") -> list[PaperOrder]: ...
    def get_order(self, order_id: str) -> PaperOrder: ...
    def get_order_by_client_id(self, client_order_id: str) -> PaperOrder: ...
    def submit_entry(self, proposal: OrderProposal, permit: ApprovalPermit) -> PaperOrder: ...
    def close_position(self, proposal: OrderProposal, permit: ApprovalPermit) -> PaperOrder: ...
    def cancel_order(
        self, order_id: str, expected_stop_price: Decimal,
        proposal: OrderProposal, permit: ApprovalPermit,
    ) -> PaperOrder: ...
    def historical_daily_bars(
        self, symbols: list[str], *, start: date, end: date, feed: str, adjustment: str
    ) -> dict[str, list[Any]]: ...


class PaperWorkflowError(RuntimeError):
    pass


_Result = TypeVar("_Result")
REBASELINE_CONFIRMATION = "REBASELINE-PAPER-RUN-AT-CLEAN-500"


def _serialized(method: Callable[..., _Result]) -> Callable[..., _Result]:
    """Keep broker snapshots, journal transitions, and approvals process-serial."""
    @wraps(method)
    def wrapper(self: "PaperWorkflow", *args: Any, **kwargs: Any) -> _Result:
        with self.journal.mutation_lock():
            try:
                return method(self, *args, **kwargs)
            except Exception as exc:
                self._record_operation_failure_best_effort(method.__name__, exc)
                raise

    return wrapper


class PaperWorkflow:
    def __init__(
        self,
        broker: Broker,
        journal: PaperJournal,
        strategy_config: dict[str, Any],
        paper_config: dict[str, Any],
    ):
        self.broker = broker
        self.journal = journal
        self.strategy_config = copy.deepcopy(strategy_config)
        self.paper_config = copy.deepcopy(paper_config)
        validate_config(self.strategy_config)
        validate_paper_config(self.paper_config, FROZEN_STRATEGY_CONFIG_SHA256)
        if self._config_hash(self.strategy_config) != FROZEN_STRATEGY_VALUE_SHA256:
            raise PaperWorkflowError("runtime strategy does not match frozen v1")
        self._strategy_runtime_hash = self._config_hash(self.strategy_config)
        self._paper_runtime_hash = self._config_hash(self.paper_config)
        self.reconciler = PaperReconciler(
            journal, self.paper_config, self.strategy_config
        )
        self.universe = tuple(str(item) for item in self.strategy_config["universe"])

    @_serialized
    def bind_clean_account(self, *, now: datetime | None = None) -> dict[str, Any]:
        self._require_runtime_config()
        self.journal.verify_integrity()
        account = self._broker_read(self.broker.get_account)
        positions = self._broker_read(self.broker.list_positions)
        orders = self._broker_read(self.broker.list_orders, status="all")
        existing = self.journal.account_binding()
        if existing:
            try:
                require_account_binding(account, existing)
            except Exception:
                timestamp = now or datetime.now(timezone.utc)
                self._latch(
                    "account_binding_mismatch",
                    [account.account_id[-4:]],
                    timestamp,
                )
                raise
            return existing
        require_initial_account(account, positions, orders, self.paper_config)
        timestamp = now or datetime.now(timezone.utc)
        payload = {
            "account_id": account.account_id,
            "account_number_suffix": account.account_number[-4:],
            "initial_equity": decimal_string(account.equity),
            "initial_cash": decimal_string(account.cash),
            "currency": account.currency,
            "clean_positions": True,
            "clean_working_orders": True,
            "run_number": 1,
        }
        self.journal._append_state("account_bound", payload, occurred_at=timestamp)
        return payload

    @_serialized
    def reconcile_now(self, *, now: datetime | None = None) -> ReconciliationReport:
        self._require_runtime_config()
        account = self._broker_read(self.broker.get_account)
        positions = self._broker_read(self.broker.list_positions)
        orders = self._broker_read(self.broker.list_orders, status="all")
        timestamp = now or self._broker_read(self.broker.get_clock).timestamp
        report = self.reconciler.reconcile(
            account=account,
            positions=positions,
            orders=orders,
            now=timestamp,
        )
        require_operable_account(account, self.paper_config)
        return report

    @_serialized
    def scan_entries(self) -> list[dict[str, Any]]:
        account, clock, positions, orders = self._clean_snapshot()
        del account, positions, orders
        start = clock.timestamp.date() - timedelta(days=500)
        bars = self._broker_read(self.broker.historical_daily_bars,
            list(self.universe),
            start=start,
            end=clock.timestamp.date(),
            feed=self.paper_config["broker"]["market_data_feed"],
            adjustment=self.paper_config["broker"]["historical_adjustment"],
        )
        expected_bar_date = self._expected_signal_date(clock)
        results: list[dict[str, Any]] = []
        for symbol in self.universe:
            decision = latest_entry_decision(
                bars.get(symbol, []),
                session_date=clock.timestamp.date(),
                strategy_config=self.strategy_config,
            )
            payload = {
                "symbol": symbol,
                "bar_date": decision.bar_date.isoformat() if decision.bar_date else None,
                "qualified": decision.signal is not None,
                "reason": decision.signal.reason if decision.signal else decision.rejection_reason,
            }
            if decision.bar_date != expected_bar_date:
                payload["qualified"] = False
                payload["reason"] = "latest_completed_trading_day_bar_missing"
            self.journal.append(
                "live_entry_signal" if payload["qualified"] else "live_entry_rejected",
                payload,
                occurred_at=clock.timestamp,
            )
            results.append(payload)
        return results

    @_serialized
    def scan_exits(self) -> list[dict[str, Any]]:
        account, clock, positions, orders = self._clean_snapshot()
        del account, positions, orders
        state = reduce_events(self.journal.events())
        if not state.positions:
            return []
        bars = self._broker_read(self.broker.historical_daily_bars,
            sorted(state.positions),
            start=clock.timestamp.date() - timedelta(days=500),
            end=clock.timestamp.date(),
            feed=self.paper_config["broker"]["market_data_feed"],
            adjustment=self.paper_config["broker"]["historical_adjustment"],
        )
        expected_bar_date = self._expected_signal_date(clock)
        results: list[dict[str, Any]] = []
        for symbol, managed in sorted(state.positions.items()):
            symbol_bars = bars.get(symbol, [])
            completed = [bar for bar in symbol_bars if bar.date < clock.timestamp.date()]
            if not completed or completed[-1].date != expected_bar_date:
                payload = {
                    "symbol": symbol,
                    "bar_date": None,
                    "exit_required": False,
                    "reason": "latest_completed_trading_day_bar_missing",
                }
                self._record_exit_check("live_exit_rejected", payload, clock.timestamp)
                results.append(payload)
                continue
            reason = latest_exit_reason(
                symbol_bars,
                session_date=clock.timestamp.date(),
                entry_date=managed.entry_date,
                strategy_config=self.strategy_config,
            )
            payload = {
                "symbol": symbol,
                "bar_date": expected_bar_date.isoformat(),
                "exit_required": reason is not None,
                "reason": reason,
            }
            self._record_exit_check(
                "live_exit_signal" if reason else "live_exit_not_triggered",
                payload,
                clock.timestamp,
            )
            results.append(payload)
        return results

    @_serialized
    def propose_entry(self, symbol: str) -> OrderProposal:
        clean_symbol = self._universe_symbol(symbol)
        account, clock, positions, orders = self._clean_snapshot()
        require_market_open(clock)
        start = clock.timestamp.date() - timedelta(days=500)
        bars_by_symbol = self._broker_read(self.broker.historical_daily_bars,
            [clean_symbol],
            start=start,
            end=clock.timestamp.date(),
            feed=self.paper_config["broker"]["market_data_feed"],
            adjustment=self.paper_config["broker"]["historical_adjustment"],
        )
        decision = latest_entry_decision(
            bars_by_symbol.get(clean_symbol, []),
            session_date=clock.timestamp.date(),
            strategy_config=self.strategy_config,
        )
        expected_bar_date = self._expected_signal_date(clock)
        if decision.bar_date != expected_bar_date:
            raise PaperWorkflowError(
                f"latest completed bar is {decision.bar_date}; expected {expected_bar_date}"
            )
        if decision.signal is None:
            self.journal.append(
                "live_entry_rejected",
                {
                    "symbol": clean_symbol,
                    "bar_date": decision.bar_date.isoformat() if decision.bar_date else None,
                    "reason": decision.rejection_reason,
                },
                occurred_at=clock.timestamp,
            )
            raise PaperWorkflowError(f"entry fails strategy filter: {decision.rejection_reason}")
        quote = self._broker_read(self.broker.latest_quote,
            clean_symbol, feed=self.paper_config["broker"]["market_data_feed"]
        )
        require_quote(quote, now=clock.timestamp, paper_config=self.paper_config)
        quantity, stop, maximum_entry, planned_loss, risk_limit = size_entry(
            account=account,
            quote=quote,
            atr14=decision.signal.atr14,
            strategy_config=self.strategy_config,
            paper_config=self.paper_config,
        )
        fractional = is_fractional(quantity)
        asset = self._broker_read(self.broker.get_asset, clean_symbol)
        require_asset(asset, clean_symbol, fractional=fractional)
        terminal = set(self.paper_config["monitoring"]["order_terminal_statuses"])
        require_no_symbol_conflict(clean_symbol, positions, orders, terminal)
        fingerprint = self._fingerprint(
            "entry_oto",
            account.account_id,
            clean_symbol,
            decision.signal.signal_date.isoformat(),
            quote.timestamp.isoformat(),
            decimal_string(quantity),
            decimal_string(stop),
            str(len(self.journal.events()) + 1),
        )
        client_id = f"swing-e-{fingerprint[:32]}"
        state = reduce_events(self.journal.events())
        authorize_entry_risk(
            client_order_id=client_id,
            symbol=clean_symbol,
            account=account,
            quote=quote,
            now=clock.timestamp,
            planned_loss=planned_loss,
            state=state,
            day_start_equity=self._day_start_equity(clock.timestamp),
            strategy_config=self.strategy_config,
            kill_switch=self._effective_kill_switch(),
        )
        if fractional:
            raise PaperWorkflowError("Alpaca paper swing entries must be whole-share GTC orders")
        proposal = self._entry_proposal(
            fingerprint=fingerprint,
            client_id=client_id,
            account=account,
            clock=clock,
            quote=quote,
            signal=decision.signal,
            quantity=quantity,
            stop=stop,
            maximum_entry=maximum_entry,
            planned_loss=planned_loss,
            risk_limit=risk_limit,
        )
        self._require_proposal_config(proposal)
        self.journal.record_proposal(proposal)
        return proposal

    @_serialized
    def propose_exit(self, symbol: str, *, reason: str = "auto") -> OrderProposal:
        clean_symbol = self._universe_symbol(symbol)
        account, clock, positions, orders = self._clean_snapshot()
        require_market_open(clock)
        state = reduce_events(self.journal.events())
        managed = state.positions.get(clean_symbol)
        broker_position = next((item for item in positions if item.symbol == clean_symbol), None)
        if managed is None or broker_position is None:
            raise PaperWorkflowError("no reconciled managed position exists for symbol")
        if any(
            order.symbol == clean_symbol
            and order.order_id != managed.stop_order_id
            and order.status not in set(self.paper_config["monitoring"]["order_terminal_statuses"])
            for order in flatten_orders(orders)
        ):
            raise PaperWorkflowError("another working order already exists for symbol")
        selected_reason = reason
        if reason == "auto":
            bars = self._broker_read(self.broker.historical_daily_bars,
                [clean_symbol],
                start=clock.timestamp.date() - timedelta(days=500),
                end=clock.timestamp.date(),
                feed=self.paper_config["broker"]["market_data_feed"],
                adjustment=self.paper_config["broker"]["historical_adjustment"],
            )
            expected_bar_date = self._expected_signal_date(clock)
            completed = [
                bar for bar in bars.get(clean_symbol, [])
                if bar.date < clock.timestamp.date()
            ]
            if not completed or completed[-1].date != expected_bar_date:
                raise PaperWorkflowError("latest completed trading-day bar is missing")
            selected_reason = latest_exit_reason(
                bars.get(clean_symbol, []),
                session_date=clock.timestamp.date(),
                entry_date=managed.entry_date,
                strategy_config=self.strategy_config,
            ) or ""
            if not selected_reason:
                raise PaperWorkflowError("position has no deterministic exit signal")
        if selected_reason not in {"recovery_target", "time_stop", "manual_owner_exit"}:
            raise PaperWorkflowError("unsupported exit reason")
        quote = self._broker_read(self.broker.latest_quote,
            clean_symbol, feed=self.paper_config["broker"]["market_data_feed"]
        )
        require_quote(quote, now=clock.timestamp, paper_config=self.paper_config)
        fingerprint = self._fingerprint(
            "close_position",
            account.account_id,
            clean_symbol,
            selected_reason,
            quote.timestamp.isoformat(),
            decimal_string(broker_position.quantity),
            str(len(self.journal.events()) + 1),
        )
        created = clock.timestamp
        proposal = OrderProposal(
            proposal_id=f"prop-x-{fingerprint[:24]}",
            client_order_id=f"swing-x-{fingerprint[:32]}",
            action="close_position",
            account_id=account.account_id,
            symbol=clean_symbol,
            side="sell",
            quantity=broker_position.quantity,
            order_type="market",
            time_in_force="day",
            order_class="simple",
            extended_hours=False,
            created_at=created,
            expires_at=created + timedelta(seconds=int(self.paper_config["execution"]["approval_ttl_seconds"])),
            quote_timestamp=quote.timestamp,
            bid=quote.bid,
            ask=quote.ask,
            maximum_entry_reference=None,
            stop_price=None,
            estimated_cost=broker_position.quantity * quote.bid,
            planned_loss=Decimal("0"),
            risk_limit=Decimal("0"),
            signal_date=None,
            thesis=f"Close the managed position because {selected_reason} fired.",
            invalidation="Do not execute if position quantity, account, quote, or exit reason changes.",
            strategy_config_sha256=self.paper_config["strategy_config_sha256"],
            fractional=is_fractional(broker_position.quantity),
            exit_reason=selected_reason,
            protective_stop_order_id=managed.stop_order_id,
            protective_stop_price=managed.stop_price,
        )
        self._require_proposal_config(proposal)
        self.journal.record_proposal(proposal)
        return proposal

    @_serialized
    def execute(
        self,
        proposal_id: str,
        confirmation_code: str,
        *,
        session_id: str,
        environment: Mapping[str, str] | None = None,
    ) -> PaperOrder:
        env = environment if environment is not None else os.environ
        self._require_runtime_enable(env)
        return self._execute_locked(
            proposal_id, confirmation_code, session_id=session_id
        )

    def _execute_locked(
        self, proposal_id: str, confirmation_code: str, *, session_id: str
    ) -> PaperOrder:
        self.journal.verify_integrity()
        self._require_runtime_config()
        proposal = self.journal.get_proposal(proposal_id)
        self._require_proposal_config(proposal)
        account, clock, positions, orders = self._clean_snapshot()
        require_market_open(clock)
        if proposal.account_id != account.account_id:
            raise PaperWorkflowError("proposal belongs to a different paper account")
        review = self.journal.latest_review(proposal)
        review_timestamp = parse_timestamp(str(review["occurred_at"]))
        review_quote_timestamp = parse_timestamp(str(review["quote_timestamp"]))
        asset: PaperAsset | None = None
        if proposal.action == "entry_oto":
            # Asset lookup can be a slow network request. Complete it before the
            # final state/quote/clock snapshot used to authorize a mutation.
            asset = self._broker_read(self.broker.get_asset, proposal.symbol)
        elif proposal.action != "close_position":
            raise PaperWorkflowError("unknown proposal action")

        # Sample the clock last so every potentially slow preflight request is
        # bounded by the final broker timestamp rather than the initial snapshot.
        account = self._broker_read(self.broker.get_account)
        positions = self._broker_read(self.broker.list_positions)
        orders = self._broker_read(self.broker.list_orders, status="all")
        quote = self._broker_read(self.broker.latest_quote,
            proposal.symbol, feed=self.paper_config["broker"]["market_data_feed"]
        )
        clock = self._broker_read(self.broker.get_clock)
        report = self.reconciler.reconcile(
            account=account, positions=positions, orders=orders, now=clock.timestamp
        )
        if not report.ok:
            raise PaperWorkflowError(
                "reconciliation failed during final execution refresh: "
                + ", ".join(report.issues)
            )
        require_operable_account(account, self.paper_config)
        require_account_binding(account, self.journal.account_binding())
        require_market_open(clock)
        if self.journal.kill_switch_latched():
            raise PaperWorkflowError("durable kill switch is latched")
        if proposal.account_id != account.account_id:
            raise PaperWorkflowError("proposal belongs to a different paper account")
        future_tolerance = timedelta(
            seconds=int(
                self.paper_config["execution"]["quote_future_tolerance_seconds"]
            )
        )
        if (
            review_timestamp > clock.timestamp + future_tolerance
            or review_quote_timestamp > clock.timestamp + future_tolerance
        ):
            raise PaperWorkflowError("full-order review evidence is in the future")
        if quote.timestamp < review_quote_timestamp:
            raise PaperWorkflowError("execution quote is older than the approved review quote")
        require_quote(
            quote,
            now=clock.timestamp,
            paper_config=self.paper_config,
            prior_ask=Decimal(str(review["ask"]))
            if proposal.action == "entry_oto" else None,
            prior_bid=Decimal(str(review["bid"]))
            if proposal.action == "close_position" else None,
        )
        if proposal.action == "entry_oto":
            self._revalidate_entry(
                proposal, account, clock, quote, positions, orders, asset=asset
            )
        elif proposal.action == "close_position":
            self._revalidate_exit(proposal, positions)
            seconds_before_close = (clock.next_close - clock.timestamp).total_seconds()
            cutoff = int(
                self.paper_config["execution"]["exit_cancel_cutoff_seconds_before_close"]
            )
            if seconds_before_close <= cutoff:
                raise PaperWorkflowError(
                    "approved exit is too close to the regular-session close to cancel protection safely"
                )

        mutation_deadline = self._mutation_deadline(proposal, quote, clock)

        permit = self.journal.approve_and_consume(
            proposal,
            confirmation_code,
            review_event_id=str(review["event_id"]),
            session_id=session_id,
            now=clock.timestamp,
            mutation_deadline=mutation_deadline,
        )
        self.journal._append_state(
            "order_submission_started",
            {
                "action": proposal.action,
                "symbol": proposal.symbol,
                "client_order_id": proposal.client_order_id,
            },
            proposal_id=proposal.proposal_id,
            occurred_at=clock.timestamp,
        )
        if proposal.action == "close_position":
            self._cancel_native_stop_before_exit(proposal, permit, clock.timestamp)
        try:
            if proposal.action == "entry_oto":
                order = self.broker.submit_entry(proposal, permit)
            else:
                order = self.broker.close_position(proposal, permit)
        except Exception as exc:
            order = self._resolve_uncertain_submission(proposal, clock.timestamp, exc)
        try:
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
                },
                proposal_id=proposal.proposal_id,
                occurred_at=clock.timestamp,
            )
        except Exception as exc:
            self._latch_best_effort(
                "order_submission_journal_failure",
                [proposal.client_order_id, type(exc).__name__],
                clock.timestamp,
            )
            raise PaperWorkflowError(
                "broker order may exist but its submission could not be journaled; do not retry"
            ) from None
        acknowledgement_clock: PaperClock | None = None
        try:
            order = self._broker_read(self.broker.get_order, order.order_id)
            acknowledgement_clock = self._broker_read(self.broker.get_clock)
            if proposal.action == "entry_oto":
                self._validate_entry_ack(
                    proposal, order, acknowledgement_clock.timestamp
                )
            else:
                self._validate_exit_ack(
                    proposal, order, acknowledgement_clock.timestamp
                )
        except Exception as exc:
            failure_time = (
                acknowledgement_clock.timestamp
                if acknowledgement_clock is not None
                else clock.timestamp
            )
            self._latch("post_submission_validation_failed", [str(exc)], failure_time)
            raise
        if order.status in {"canceled", "expired", "rejected", "replaced"}:
            self._latch(
                "broker_order_not_working",
                [order.order_id, order.status],
                acknowledgement_clock.timestamp,
            )
            raise PaperWorkflowError(
                f"broker paper order is not working: {order.status}"
            )
        return order

    @_serialized
    def status(self) -> dict[str, Any]:
        self._require_runtime_config()
        self.journal.verify_integrity()
        account = self._broker_read(self.broker.get_account)
        positions = self._broker_read(self.broker.list_positions)
        orders = self._broker_read(self.broker.list_orders, status="all")
        clock = self._broker_read(self.broker.get_clock)
        report = self.reconciler.reconcile(
            account=account,
            positions=positions,
            orders=orders,
            now=clock.timestamp,
        )
        state = reduce_events(self.journal.events())
        binding = self.journal.account_binding() or {}
        run_number = int(binding.get("run_number", 1))
        broker_by_symbol = {position.symbol: position for position in positions}
        observed_day_start = self.journal.first_observed_equity_for_day(
            clock.timestamp
        )
        return {
            "paper_only": True,
            "paper_run_number": run_number,
            "paper_gate_restarted": run_number > 1,
            "broker_timestamp": clock.timestamp.isoformat(),
            "market_open": clock.is_open,
            "account_number_suffix": account.account_number[-4:],
            "equity": decimal_string(account.equity),
            "cash": decimal_string(account.cash),
            "day_pnl": decimal_string(account.equity - account.last_equity),
            "observed_day_start_equity": decimal_string(observed_day_start)
            if observed_day_start is not None else None,
            "observed_day_pnl": decimal_string(account.equity - observed_day_start)
            if observed_day_start is not None and account.equity.is_finite()
            else None,
            "alpaca_previous_close_pnl": decimal_string(
                account.equity - account.last_equity
            ),
            "kill_switch_latched": self.journal.kill_switch_latched(),
            "alpaca_fractional_swing_orders": "prohibited_day_only",
            "reconciliation": {
                "ok": report.ok,
                "issues": list(report.issues),
                "warnings": list(report.warnings),
                "broker_positions": report.broker_position_count,
                "managed_positions": report.managed_position_count,
                "working_orders": report.working_order_count,
            },
            "managed_positions": {
                symbol: {
                    "quantity": decimal_string(item.quantity),
                    "entry_price": decimal_string(item.entry_price),
                    "stop_price": decimal_string(item.stop_price),
                    "planned_loss": decimal_string(item.planned_loss),
                    "current_price": decimal_string(broker_by_symbol[symbol].current_price)
                    if symbol in broker_by_symbol else None,
                    "unrealized_pnl": decimal_string(
                        (broker_by_symbol[symbol].current_price - item.entry_price) * item.quantity
                    ) if symbol in broker_by_symbol else None,
                }
                for symbol, item in sorted(state.positions.items())
            },
            "monitoring_honesty": "This is a point-in-time poll; no monitoring occurs when the process is not running.",
        }

    @_serialized
    def clear_kill_switch(self, confirmation: str) -> None:
        self._require_runtime_config()
        if confirmation != "CLEAR-PAPER-KILL-SWITCH":
            raise PaperWorkflowError("kill-switch clear confirmation is incorrect")
        if not self.journal.kill_switch_latched():
            return
        account = self._broker_read(self.broker.get_account)
        positions = self._broker_read(self.broker.list_positions)
        orders = self._broker_read(self.broker.list_orders, status="all")
        clock = self._broker_read(self.broker.get_clock)
        report = self.reconciler.reconcile(
            account=account,
            positions=positions,
            orders=orders,
            now=clock.timestamp,
        )
        if not report.ok:
            raise PaperWorkflowError(
                "kill switch cannot clear while reconciliation fails: "
                + ", ".join(report.issues)
            )
        self.journal._append_state(
            "kill_switch_cleared",
            {"owner_confirmation": True, "clean_reconciliation": True},
            occurred_at=clock.timestamp,
        )

    @_serialized
    def rebaseline_clean_account(
        self, confirmation: str, *, now: datetime | None = None
    ) -> dict[str, Any]:
        """Start a new audited paper run after an external manual recovery."""
        self._require_runtime_config()
        self.journal.verify_integrity()
        if confirmation != REBASELINE_CONFIRMATION:
            raise PaperWorkflowError("paper-run rebaseline confirmation is incorrect")
        if not self.journal.kill_switch_latched():
            raise PaperWorkflowError("paper-run rebaseline requires a latched kill switch")
        binding = self.journal.account_binding()
        account = self._broker_read(self.broker.get_account)
        require_account_binding(account, binding)
        positions = self._broker_read(self.broker.list_positions)
        orders = self._broker_read(self.broker.list_orders, status="all")
        require_initial_account(account, positions, orders, self.paper_config)
        timestamp = now or self._broker_read(self.broker.get_clock).timestamp
        prior_runs = sum(
            event["event_type"] in {"account_bound", "paper_run_rebaselined"}
            for event in self.journal.events()
        )
        payload = {
            "account_id": account.account_id,
            "account_number_suffix": account.account_number[-4:],
            "initial_equity": decimal_string(account.equity),
            "initial_cash": decimal_string(account.cash),
            "currency": account.currency,
            "clean_positions": True,
            "clean_working_orders": True,
            "owner_confirmation": True,
            "prior_run_terminated": True,
            "run_number": prior_runs + 1,
        }
        self.journal._append_state(
            "paper_run_rebaselined", payload, occurred_at=timestamp
        )
        return payload

    @_serialized
    def review(self, proposal_id: str) -> dict[str, Any]:
        self._require_runtime_config()
        proposal = self.journal.get_proposal(proposal_id)
        self._require_proposal_config(proposal)
        account, clock, positions, orders = self._clean_snapshot()
        del orders
        if proposal.account_id != account.account_id:
            raise PaperWorkflowError("proposal belongs to a different paper account")
        if clock.timestamp > proposal.expires_at:
            raise PaperWorkflowError("proposal has expired; create a fresh proposal")
        quote = self._broker_read(self.broker.latest_quote,
            proposal.symbol, feed=self.paper_config["broker"]["market_data_feed"]
        )
        require_quote(
            quote,
            now=clock.timestamp,
            paper_config=self.paper_config,
            prior_ask=proposal.ask if proposal.action == "entry_oto" else None,
            prior_bid=proposal.bid if proposal.action == "close_position" else None,
        )
        if proposal.action == "entry_oto":
            if proposal.maximum_entry_reference is None or quote.ask > proposal.maximum_entry_reference:
                raise PaperWorkflowError("current ask exceeds the proposal's entry guard")
        elif proposal.action == "close_position":
            self._revalidate_exit(proposal, positions)
        review_event = self.journal.record_review(
            proposal,
            quote_timestamp=quote.timestamp,
            bid=decimal_string(quote.bid),
            ask=decimal_string(quote.ask),
            reviewed_at=clock.timestamp,
        )
        return {
            "paper_only": True,
            "proposal_id": proposal.proposal_id,
            "review_event_id": review_event["event_id"],
            "confirmation_code": self.journal.confirmation_code_for_review(
                proposal, review_event
            ),
            "expires_at": proposal.expires_at.isoformat(),
            "account_suffix": proposal.account_id[-4:],
            "ticker": proposal.symbol,
            "action": proposal.action,
            "side": proposal.side,
            "quantity": decimal_string(proposal.quantity),
            "order_type": proposal.order_type,
            "time_in_force": proposal.time_in_force,
            "order_class": proposal.order_class,
            "bid": decimal_string(proposal.bid),
            "ask": decimal_string(proposal.ask),
            "quote_timestamp": proposal.quote_timestamp.isoformat(),
            "review_requote_bid": decimal_string(quote.bid),
            "review_requote_ask": decimal_string(quote.ask),
            "review_requote_timestamp": quote.timestamp.isoformat(),
            "maximum_entry_reference": decimal_string(proposal.maximum_entry_reference)
            if proposal.maximum_entry_reference is not None else None,
            "protective_stop": decimal_string(
                proposal.stop_price
                if proposal.stop_price is not None
                else proposal.protective_stop_price
            )
            if proposal.stop_price is not None or proposal.protective_stop_price is not None
            else None,
            "estimated_cost_or_proceeds": decimal_string(proposal.estimated_cost),
            "planned_loss": decimal_string(proposal.planned_loss),
            "risk_limit": decimal_string(proposal.risk_limit),
            "thesis": proposal.thesis,
            "invalidation": proposal.invalidation,
            "exit_reason": proposal.exit_reason,
            "protective_stop_order_id": proposal.protective_stop_order_id,
            "client_order_id": proposal.client_order_id,
            "one_order_only": True,
            "market_order_warning": "The maximum entry reference is a pre-submit guard, not a broker limit price; the actual market fill can be worse.",
        }

    def _entry_proposal(
        self,
        *,
        fingerprint: str,
        client_id: str,
        account: PaperAccount,
        clock: PaperClock,
        quote: PaperQuote,
        signal: LiveSignal,
        quantity: Decimal,
        stop: Decimal,
        maximum_entry: Decimal,
        planned_loss: Decimal,
        risk_limit: Decimal,
    ) -> OrderProposal:
        created = clock.timestamp
        return OrderProposal(
            proposal_id=f"prop-e-{fingerprint[:24]}",
            client_order_id=client_id,
            action="entry_oto",
            account_id=account.account_id,
            symbol=signal.symbol,
            side="buy",
            quantity=quantity,
            order_type="market",
            time_in_force="gtc",
            order_class="oto",
            extended_hours=False,
            created_at=created,
            expires_at=created + timedelta(seconds=int(self.paper_config["execution"]["approval_ttl_seconds"])),
            quote_timestamp=quote.timestamp,
            bid=quote.bid,
            ask=quote.ask,
            maximum_entry_reference=maximum_entry,
            stop_price=stop,
            estimated_cost=quantity * maximum_entry,
            planned_loss=planned_loss,
            risk_limit=risk_limit,
            signal_date=signal.signal_date,
            thesis=signal.reason,
            invalidation=signal.invalidation,
            strategy_config_sha256=self.paper_config["strategy_config_sha256"],
            fractional=is_fractional(quantity),
            protective_stop_order_id=None,
            protective_stop_price=None,
        )

    def _clean_snapshot(
        self,
    ) -> tuple[PaperAccount, PaperClock, list[PaperPosition], list[PaperOrder]]:
        self.journal.verify_integrity()
        self._require_runtime_config()
        account = self._broker_read(self.broker.get_account)
        positions = self._broker_read(self.broker.list_positions)
        orders = self._broker_read(self.broker.list_orders, status="all")
        clock = self._broker_read(self.broker.get_clock)
        report = self.reconciler.reconcile(
            account=account, positions=positions, orders=orders, now=clock.timestamp
        )
        if not report.ok:
            raise PaperWorkflowError(
                "reconciliation failed: " + ", ".join(report.issues)
            )
        require_operable_account(account, self.paper_config)
        if self.journal.kill_switch_latched():
            raise PaperWorkflowError("durable kill switch is latched")
        return account, clock, positions, orders

    def _revalidate_entry(
        self,
        proposal: OrderProposal,
        account: PaperAccount,
        clock: PaperClock,
        quote: PaperQuote,
        positions: list[PaperPosition],
        orders: list[PaperOrder],
        *,
        asset: PaperAsset | None = None,
    ) -> None:
        terminal = set(self.paper_config["monitoring"]["order_terminal_statuses"])
        require_no_symbol_conflict(proposal.symbol, positions, orders, terminal)
        asset = asset or self._broker_read(self.broker.get_asset, proposal.symbol)
        require_asset(asset, proposal.symbol, fractional=proposal.fractional)
        if proposal.fractional:
            raise PaperWorkflowError("Alpaca fractional DAY orders cannot protect a swing overnight")
        if proposal.maximum_entry_reference is None or quote.ask > proposal.maximum_entry_reference:
            raise PaperWorkflowError("current ask exceeds the approved maximum entry reference")
        available_cash = min(account.cash, account.non_marginable_buying_power)
        if (
            proposal.quantity * proposal.maximum_entry_reference
            > available_cash + Decimal("0.00000001")
        ):
            raise PaperWorkflowError(
                "current cash-only buying power no longer covers the approved entry"
            )
        state = reduce_events(self.journal.events())
        authorize_entry_risk(
            client_order_id=proposal.client_order_id,
            symbol=proposal.symbol,
            account=account,
            quote=quote,
            now=clock.timestamp,
            planned_loss=proposal.planned_loss,
            state=state,
            day_start_equity=self._day_start_equity(clock.timestamp),
            strategy_config=self.strategy_config,
            kill_switch=self._effective_kill_switch(),
        )

    def _mutation_deadline(
        self, proposal: OrderProposal, quote: PaperQuote, clock: PaperClock
    ) -> datetime:
        quote_deadline = quote.timestamp + timedelta(
            seconds=int(self.paper_config["execution"]["quote_max_age_seconds"])
        )
        session_deadline = clock.next_close
        if proposal.action == "close_position":
            session_deadline -= timedelta(
                seconds=int(
                    self.paper_config["execution"][
                        "exit_cancel_cutoff_seconds_before_close"
                    ]
                )
            )
        deadline = min(proposal.expires_at, quote_deadline, session_deadline)
        if deadline <= clock.timestamp:
            raise PaperWorkflowError(
                "approval, quote, or regular-session mutation window expired"
            )
        return deadline

    def _revalidate_exit(
        self, proposal: OrderProposal, positions: list[PaperPosition]
    ) -> None:
        position = next((item for item in positions if item.symbol == proposal.symbol), None)
        if position is None:
            raise PaperWorkflowError("broker position is already closed")
        if abs(position.quantity - proposal.quantity) > Decimal("0.000001"):
            raise PaperWorkflowError("broker position quantity changed; approve a fresh exit")
        if proposal.exit_reason not in {"recovery_target", "time_stop", "manual_owner_exit"}:
            raise PaperWorkflowError("exit proposal has no approved reason")

    def _cancel_native_stop_before_exit(
        self, proposal: OrderProposal, permit: ApprovalPermit, now: datetime
    ) -> None:
        state = reduce_events(self.journal.events())
        managed = state.positions.get(proposal.symbol)
        if managed is None:
            raise PaperWorkflowError("managed position disappeared before exit")
        if proposal.protective_stop_order_id != managed.stop_order_id:
            raise PaperWorkflowError(
                "exit approval is not bound to the currently managed protective stop"
            )
        try:
            stop = self.broker.cancel_order(
                managed.stop_order_id,
                managed.stop_price,
                proposal,
                permit,
            )
        except Exception as exc:
            self._latch(
                "protective_stop_cancel_uncertain",
                [managed.stop_order_id, type(exc).__name__],
                now,
            )
            raise PaperWorkflowError("protective stop cancellation outcome is uncertain") from None
        if stop.status not in {"canceled", "filled", "expired"}:
            self._latch("protective_stop_cancel_unconfirmed", [managed.stop_order_id], now)
            raise PaperWorkflowError("protective stop cancellation was not confirmed")
        if stop.status == "filled":
            self._latch("protective_stop_filled_during_exit", [managed.stop_order_id], now)
            raise PaperWorkflowError("protective stop filled; close order was not submitted")
        if (
            stop.filled_quantity != 0
            or stop.filled_average_price is not None
            or stop.filled_at is not None
        ):
            self._latch(
                "protective_stop_partially_filled_during_exit",
                [managed.stop_order_id, decimal_string(stop.filled_quantity)],
                now,
            )
            raise PaperWorkflowError(
                "protective stop partially filled before cancellation; close order was not submitted"
            )
        try:
            account = self._broker_read(self.broker.get_account)
            positions = self._broker_read(self.broker.list_positions)
            post_cancel_clock = self._broker_read(self.broker.get_clock)
            require_operable_account(account, self.paper_config)
            require_account_binding(account, self.journal.account_binding())
            require_market_open(post_cancel_clock)
            self._revalidate_exit(proposal, positions)
            seconds_before_close = (
                post_cancel_clock.next_close - post_cancel_clock.timestamp
            ).total_seconds()
            cutoff = int(
                self.paper_config["execution"][
                    "exit_cancel_cutoff_seconds_before_close"
                ]
            )
            if seconds_before_close <= cutoff:
                raise PaperWorkflowError(
                    "approved exit became too close to the regular-session close"
                )
        except Exception as exc:
            self._latch(
                "post_cancel_exit_revalidation_failed",
                [managed.stop_order_id, type(exc).__name__, str(exc)],
                now,
            )
            raise PaperWorkflowError(
                "broker state changed after stop cancellation; close order was not submitted"
            ) from None
        try:
            self.journal.record_protective_stop_cancellation_verified(
                proposal,
                permit,
                stop_order_id=managed.stop_order_id,
                verified_at=post_cancel_clock.timestamp,
            )
        except Exception as exc:
            self._latch_best_effort(
                "protective_stop_cancel_journal_failure",
                [managed.stop_order_id, type(exc).__name__],
                now,
            )
            raise PaperWorkflowError(
                "protective stop was canceled but verification could not be journaled; exit blocked"
            ) from None

    def _validate_entry_ack(
        self, proposal: OrderProposal, order: PaperOrder, now: datetime
    ) -> None:
        known_statuses = set(self.paper_config["monitoring"]["order_terminal_statuses"]) | set(
            self.paper_config["monitoring"]["order_working_statuses"]
        )
        if (
            order.client_order_id != proposal.client_order_id
            or order.symbol != proposal.symbol
            or order.side != "buy"
            or order.order_type != "market"
            or order.time_in_force != "gtc"
            or order.order_class != "oto"
            or order.quantity != proposal.quantity
            or order.extended_hours
            or order.status not in known_statuses
        ):
            raise PaperWorkflowError("broker entry acknowledgement differs from approved order")
        if order.status == "partially_filled" or (
            order.filled_quantity > 0 and order.filled_quantity < order.quantity
        ):
            raise PaperWorkflowError("broker entry is partially filled and not fully protected")
        if order.status == "filled":
            self._require_complete_fill(proposal, order, "entry", now)
        elif (
            order.filled_quantity != 0
            or order.filled_at is not None
            or order.filled_average_price is not None
        ):
            raise PaperWorkflowError("unfilled broker entry reports inconsistent fill fields")
        stops = list(order.legs)
        working_statuses = set(
            self.paper_config["monitoring"]["order_working_statuses"]
        )
        if (
            len(stops) != 1
            or stops[0].symbol != proposal.symbol
            or stops[0].side != "sell"
            or stops[0].order_type != "stop"
            or stops[0].stop_price != proposal.stop_price
            or stops[0].quantity != proposal.quantity
            or stops[0].time_in_force != "gtc"
            or stops[0].extended_hours
            or bool(stops[0].legs)
            or (
                stops[0].status not in working_statuses
                and stops[0].status != "filled"
            )
            or (
                stops[0].status in working_statuses
                and stops[0].status in NON_PROTECTIVE_STOP_STATUSES - {"held"}
            )
            or (order.status == "filled" and stops[0].status == "held")
            or (order.status != "filled" and stops[0].status == "filled")
        ):
            raise PaperWorkflowError("broker-native protective stop is missing or mismatched")
        if stops[0].status == "filled":
            self._require_complete_fill(proposal, stops[0], "protective stop", now)
            assert order.filled_at is not None and stops[0].filled_at is not None
            if stops[0].filled_at < order.filled_at:
                raise PaperWorkflowError(
                    "broker-native protective stop fill predates the entry fill"
                )
        elif (
            not stops[0].order_id
            or not stops[0].filled_quantity.is_finite()
            or stops[0].filled_quantity != 0
            or stops[0].filled_average_price is not None
            or stops[0].filled_at is not None
        ):
            raise PaperWorkflowError(
                "working broker-native protective stop reports invalid fill evidence"
            )

    def _validate_exit_ack(
        self, proposal: OrderProposal, order: PaperOrder, now: datetime
    ) -> None:
        known_statuses = set(self.paper_config["monitoring"]["order_terminal_statuses"]) | set(
            self.paper_config["monitoring"]["order_working_statuses"]
        )
        if (
            order.client_order_id != proposal.client_order_id
            or order.symbol != proposal.symbol
            or order.side != "sell"
            or order.order_type != "market"
            or order.time_in_force != "day"
            or order.order_class != "simple"
            or order.quantity != proposal.quantity
            or bool(order.legs)
            or order.extended_hours
            or order.status not in known_statuses
        ):
            raise PaperWorkflowError("broker exit acknowledgement differs from approved order")
        if order.status == "partially_filled" or (
            order.filled_quantity > 0 and order.filled_quantity < order.quantity
        ):
            raise PaperWorkflowError("broker exit is partially filled after stop cancellation")
        if order.status == "filled":
            self._require_complete_fill(proposal, order, "exit", now)
        elif (
            order.filled_quantity != 0
            or order.filled_at is not None
            or order.filled_average_price is not None
        ):
            raise PaperWorkflowError("unfilled broker exit reports inconsistent fill fields")

    @staticmethod
    def _require_complete_fill(
        proposal: OrderProposal, order: PaperOrder, label: str, now: datetime
    ) -> None:
        if (
            order.filled_quantity != proposal.quantity
            or order.filled_average_price is None
            or not order.filled_average_price.is_finite()
            or order.filled_average_price <= 0
            or order.filled_at is None
            or order.filled_at.tzinfo is None
            or order.filled_at > now
        ):
            raise PaperWorkflowError(
                f"filled broker {label} has incomplete or inconsistent fill evidence"
            )

    def _resolve_uncertain_submission(
        self, proposal: OrderProposal, now: datetime, original_error: Exception
    ) -> PaperOrder:
        try:
            return self._broker_read(self.broker.get_order_by_client_id, proposal.client_order_id)
        except Exception:
            self._latch(
                "order_submission_uncertain",
                [proposal.client_order_id, type(original_error).__name__],
                now,
            )
            raise PaperWorkflowError(
                "order submission outcome is uncertain; do not retry until broker reconciliation"
            ) from None

    def _require_runtime_enable(self, env: Mapping[str, str]) -> None:
        expected = self.paper_config["execution"]["runtime_enable_phrase"]
        if env.get("SWINGBOT_PAPER_EXECUTION") != expected:
            raise PaperWorkflowError("paper execution runtime enable phrase is absent")
        if env.get("SWINGBOT_KILL_SWITCH", "1") != "0":
            raise PaperWorkflowError("runtime kill switch is active")
        for name in ("APCA_API_BASE_URL", "ALPACA_API_BASE_URL"):
            value = env.get(name)
            if value and value != self.paper_config["broker"]["trading_base_url"]:
                raise PaperWorkflowError(f"{name} points outside the paper endpoint")

    def _effective_kill_switch(self) -> bool:
        return self.journal.kill_switch_latched()

    def _latch(self, reason: str, issues: list[str], now: datetime) -> None:
        if not self.journal.kill_switch_latched():
            self.journal._append_state(
                "kill_switch_latched",
                {"reason": reason, "issues": issues},
                occurred_at=now,
            )

    def _latch_best_effort(self, reason: str, issues: list[str], now: datetime) -> None:
        try:
            self._latch(reason, issues, now)
        except Exception:
            # A broken/unwritable journal already stops the command. Preserve
            # the original uncertainty error rather than masking it here.
            pass

    def _record_operation_failure_best_effort(
        self, operation: str, error: Exception
    ) -> None:
        try:
            self.journal.append(
                "paper_operation_failed",
                {
                    "operation": operation,
                    "error_type": type(error).__name__,
                    "reason": str(error),
                },
                occurred_at=datetime.now(timezone.utc),
            )
        except Exception:
            # A broken journal must never replace the original fail-closed error.
            pass

    def _broker_read(
        self, method: Callable[..., _Result], *args: Any, **kwargs: Any
    ) -> _Result:
        try:
            return method(*args, **kwargs)
        except Exception as exc:
            # Malformed wire data may raise before reconciliation can inspect a
            # typed snapshot. A later clean response must not erase that failure.
            self._latch_best_effort(
                "broker_read_failed",
                [getattr(method, "__name__", "broker_read"), type(exc).__name__],
                datetime.now(timezone.utc),
            )
            raise

    def _universe_symbol(self, symbol: str) -> str:
        clean = symbol.strip().upper()
        if clean not in self.universe:
            raise PaperWorkflowError("symbol is outside the frozen ETF universe")
        return clean

    def _require_proposal_config(self, proposal: OrderProposal) -> None:
        if proposal.strategy_config_sha256 != FROZEN_STRATEGY_CONFIG_SHA256:
            raise PaperWorkflowError("proposal is bound to a different frozen strategy config")
        numeric = (
            proposal.quantity,
            proposal.bid,
            proposal.ask,
            proposal.estimated_cost,
            proposal.planned_loss,
            proposal.risk_limit,
        )
        if not all(value.is_finite() for value in numeric):
            raise PaperWorkflowError("proposal contains a non-finite numeric value")
        if (
            proposal.symbol not in self.universe
            or proposal.symbol != proposal.symbol.upper()
            or not proposal.account_id
            or proposal.quantity <= 0
            or proposal.bid <= 0
            or proposal.ask < proposal.bid
            or proposal.estimated_cost <= 0
            or proposal.planned_loss < 0
            or proposal.risk_limit < 0
            or not proposal.thesis.strip()
            or not proposal.invalidation.strip()
            or proposal.created_at.tzinfo is None
            or proposal.expires_at.tzinfo is None
            or proposal.quote_timestamp.tzinfo is None
            or proposal.quote_timestamp
            > proposal.created_at
            + timedelta(
                seconds=int(
                    self.paper_config["execution"]["quote_future_tolerance_seconds"]
                )
            )
            or proposal.expires_at <= proposal.created_at
            or proposal.expires_at - proposal.created_at
            != timedelta(
                seconds=int(self.paper_config["execution"]["approval_ttl_seconds"])
            )
        ):
            raise PaperWorkflowError("proposal has invalid identity, timing, quote, or value fields")
        if proposal.action == "entry_oto":
            if (
                proposal.side != "buy"
                or proposal.order_type != "market"
                or proposal.time_in_force != "gtc"
                or proposal.order_class != "oto"
                or proposal.extended_hours
                or proposal.fractional
                or proposal.quantity != proposal.quantity.to_integral_value()
                or proposal.maximum_entry_reference is None
                or proposal.stop_price is None
                or not proposal.maximum_entry_reference.is_finite()
                or not proposal.stop_price.is_finite()
                or proposal.maximum_entry_reference <= 0
                or proposal.stop_price <= 0
                or proposal.stop_price >= proposal.maximum_entry_reference
                or proposal.estimated_cost
                != proposal.quantity * proposal.maximum_entry_reference
                or proposal.planned_loss
                != proposal.quantity
                * (proposal.maximum_entry_reference - proposal.stop_price)
                or proposal.planned_loss > proposal.risk_limit
                or proposal.signal_date is None
                or proposal.exit_reason is not None
                or proposal.protective_stop_order_id is not None
                or proposal.protective_stop_price is not None
                or not proposal.proposal_id.startswith("prop-e-")
                or not proposal.client_order_id.startswith("swing-e-")
            ):
                raise PaperWorkflowError("entry proposal terms are internally inconsistent")
        elif proposal.action == "close_position":
            if (
                proposal.side != "sell"
                or proposal.order_type != "market"
                or proposal.time_in_force != "day"
                or proposal.order_class != "simple"
                or proposal.extended_hours
                or proposal.maximum_entry_reference is not None
                or proposal.stop_price is not None
                or proposal.estimated_cost != proposal.quantity * proposal.bid
                or proposal.planned_loss != 0
                or proposal.risk_limit != 0
                or proposal.signal_date is not None
                or proposal.exit_reason
                not in {"recovery_target", "time_stop", "manual_owner_exit"}
                or not proposal.protective_stop_order_id
                or proposal.protective_stop_price is None
                or not proposal.protective_stop_price.is_finite()
                or proposal.protective_stop_price <= 0
                or not proposal.proposal_id.startswith("prop-x-")
                or not proposal.client_order_id.startswith("swing-x-")
            ):
                raise PaperWorkflowError("exit proposal terms are internally inconsistent")
        else:
            raise PaperWorkflowError("proposal action is unsupported")

    def _require_runtime_config(self) -> None:
        if (
            self._config_hash(self.strategy_config) != self._strategy_runtime_hash
            or self._config_hash(self.paper_config) != self._paper_runtime_hash
        ):
            raise PaperWorkflowError("runtime configuration changed after workflow initialization")

    def _day_start_equity(self, timestamp: datetime) -> Decimal:
        equity = self.journal.first_observed_equity_for_day(timestamp)
        if equity is None:
            raise PaperWorkflowError(
                "no broker equity snapshot exists for the current trading day"
            )
        return equity

    @staticmethod
    def _config_hash(config: dict[str, Any]) -> str:
        return hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()

    def _expected_signal_date(self, clock: PaperClock) -> date:
        days = self._broker_read(self.broker.trading_days,
            start=clock.timestamp.date() - timedelta(days=10),
            end=clock.timestamp.date(),
        )
        completed = [day for day in days if day < clock.timestamp.date()]
        if not completed:
            raise PaperWorkflowError("broker calendar has no completed trading day")
        return max(completed)

    def _record_exit_check(
        self, event_type: str, payload: dict[str, Any], occurred_at: datetime
    ) -> None:
        for event in reversed(self.journal.events()):
            if event["event_type"].startswith("live_exit_") and (
                event["payload"].get("symbol") == payload["symbol"]
            ):
                if event["event_type"] == event_type and event["payload"] == payload:
                    return
                break
        self.journal.append(event_type, payload, occurred_at=occurred_at)

    @staticmethod
    def _fingerprint(*parts: str) -> str:
        return hashlib.sha256(canonical_json(list(parts)).encode("utf-8")).hexdigest()
