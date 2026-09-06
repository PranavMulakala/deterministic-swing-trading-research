from __future__ import annotations

import hashlib
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Mapping, Protocol

from .paper_journal import JournalError, PaperJournal
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
)
from .paper_policy import (
    PaperPolicyError,
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
from .paper_reconcile import PaperReconciler, ReconciliationReport, flatten_orders
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
        self, order_id: str, proposal: OrderProposal, permit: ApprovalPermit
    ) -> None: ...
    def historical_daily_bars(
        self, symbols: list[str], *, start: date, end: date, feed: str, adjustment: str
    ) -> dict[str, list[Any]]: ...


class PaperWorkflowError(RuntimeError):
    pass


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
        self.strategy_config = strategy_config
        self.paper_config = paper_config
        self.reconciler = PaperReconciler(journal, paper_config, strategy_config)
        self.universe = tuple(str(item) for item in strategy_config["universe"])

    def bind_clean_account(self, *, now: datetime | None = None) -> dict[str, Any]:
        self.journal.verify_integrity()
        account = self.broker.get_account()
        positions = self.broker.list_positions()
        orders = self.broker.list_orders(status="all")
        require_initial_account(account, positions, orders, self.paper_config)
        existing = self.journal.account_binding()
        if existing:
            require_account_binding(account, existing)
            return existing
        timestamp = now or datetime.now(timezone.utc)
        payload = {
            "account_id": account.account_id,
            "account_number_suffix": account.account_number[-4:],
            "initial_equity": decimal_string(account.equity),
            "currency": account.currency,
            "clean_positions": True,
            "clean_working_orders": True,
        }
        self.journal.append("account_bound", payload, occurred_at=timestamp)
        return payload

    def reconcile_now(self, *, now: datetime | None = None) -> ReconciliationReport:
        account = self.broker.get_account()
        require_account_binding(account, self.journal.account_binding())
        timestamp = now or datetime.now(timezone.utc)
        report = self.reconciler.reconcile(
            account=account,
            positions=self.broker.list_positions(),
            orders=self.broker.list_orders(status="all"),
            now=timestamp,
        )
        require_operable_account(account, self.paper_config)
        return report

    def scan_entries(self) -> list[dict[str, Any]]:
        account, clock, positions, orders = self._clean_snapshot()
        del account, positions, orders
        start = clock.timestamp.date() - timedelta(days=500)
        bars = self.broker.historical_daily_bars(
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

    def scan_exits(self) -> list[dict[str, Any]]:
        account, clock, positions, orders = self._clean_snapshot()
        del account, positions, orders
        state = reduce_events(self.journal.events())
        if not state.positions:
            return []
        bars = self.broker.historical_daily_bars(
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

    def propose_entry(self, symbol: str) -> OrderProposal:
        clean_symbol = self._universe_symbol(symbol)
        account, clock, positions, orders = self._clean_snapshot()
        require_market_open(clock)
        start = clock.timestamp.date() - timedelta(days=500)
        bars_by_symbol = self.broker.historical_daily_bars(
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
        quote = self.broker.latest_quote(
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
        asset = self.broker.get_asset(clean_symbol)
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
        self.journal.record_proposal(proposal)
        return proposal

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
            bars = self.broker.historical_daily_bars(
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
        quote = self.broker.latest_quote(
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
        )
        self.journal.record_proposal(proposal)
        return proposal

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
        with self.journal.mutation_lock():
            return self._execute_locked(
                proposal_id, confirmation_code, session_id=session_id
            )

    def _execute_locked(
        self, proposal_id: str, confirmation_code: str, *, session_id: str
    ) -> PaperOrder:
        self.journal.verify_integrity()
        proposal = self.journal.get_proposal(proposal_id)
        account, clock, positions, orders = self._clean_snapshot()
        require_market_open(clock)
        if proposal.account_id != account.account_id:
            raise PaperWorkflowError("proposal belongs to a different paper account")
        quote = self.broker.latest_quote(
            proposal.symbol, feed=self.paper_config["broker"]["market_data_feed"]
        )
        require_quote(
            quote,
            now=clock.timestamp,
            paper_config=self.paper_config,
            prior_ask=proposal.ask,
        )
        if proposal.action == "entry_oto":
            self._revalidate_entry(proposal, account, clock, quote, positions, orders)
        elif proposal.action == "close_position":
            self._revalidate_exit(proposal, positions)
        else:
            raise PaperWorkflowError("unknown proposal action")

        permit = self.journal.approve_and_consume(
            proposal,
            confirmation_code,
            session_id=session_id,
            now=clock.timestamp,
        )
        self.journal.append(
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
        self.journal.append(
            "order_submitted",
            {
                "action": proposal.action,
                "symbol": proposal.symbol,
                "client_order_id": proposal.client_order_id,
                "broker_order_id": order.order_id,
                "status": order.status,
                "planned_loss": decimal_string(proposal.planned_loss),
            },
            proposal_id=proposal.proposal_id,
            occurred_at=clock.timestamp,
        )
        try:
            if proposal.action == "entry_oto":
                order = self.broker.get_order(order.order_id)
                self._validate_entry_ack(proposal, order)
            else:
                self._validate_exit_ack(proposal, order)
        except Exception as exc:
            self._latch("post_submission_validation_failed", [str(exc)], clock.timestamp)
            raise
        if order.status in {"canceled", "expired", "rejected", "replaced"}:
            self._latch("broker_order_not_working", [order.order_id, order.status], clock.timestamp)
            raise PaperWorkflowError(
                f"broker paper order is not working: {order.status}"
            )
        return order

    def status(self) -> dict[str, Any]:
        self.journal.verify_integrity()
        account = self.broker.get_account()
        require_account_binding(account, self.journal.account_binding())
        clock = self.broker.get_clock()
        positions = self.broker.list_positions()
        orders = self.broker.list_orders(status="all")
        report = self.reconciler.reconcile(
            account=account,
            positions=positions,
            orders=orders,
            now=clock.timestamp,
        )
        state = reduce_events(self.journal.events())
        broker_by_symbol = {position.symbol: position for position in positions}
        return {
            "paper_only": True,
            "broker_timestamp": clock.timestamp.isoformat(),
            "market_open": clock.is_open,
            "account_number_suffix": account.account_number[-4:],
            "equity": decimal_string(account.equity),
            "cash": decimal_string(account.cash),
            "day_pnl": decimal_string(account.equity - account.last_equity),
            "kill_switch_latched": self.journal.kill_switch_latched(),
            "alpaca_fractional_swing_orders": "prohibited_day_only",
            "reconciliation": {
                "ok": report.ok,
                "issues": list(report.issues),
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

    def clear_kill_switch(self, confirmation: str) -> None:
        if confirmation != "CLEAR-PAPER-KILL-SWITCH":
            raise PaperWorkflowError("kill-switch clear confirmation is incorrect")
        if not self.journal.kill_switch_latched():
            return
        account = self.broker.get_account()
        clock = self.broker.get_clock()
        report = self.reconciler.reconcile(
            account=account,
            positions=self.broker.list_positions(),
            orders=self.broker.list_orders(status="all"),
            now=clock.timestamp,
        )
        if not report.ok:
            raise PaperWorkflowError(
                "kill switch cannot clear while reconciliation fails: "
                + ", ".join(report.issues)
            )
        self.journal.append(
            "kill_switch_cleared",
            {"owner_confirmation": True, "clean_reconciliation": True},
            occurred_at=clock.timestamp,
        )

    def review(self, proposal_id: str) -> dict[str, Any]:
        proposal = self.journal.get_proposal(proposal_id)
        account, clock, positions, orders = self._clean_snapshot()
        del orders
        if proposal.account_id != account.account_id:
            raise PaperWorkflowError("proposal belongs to a different paper account")
        if clock.timestamp > proposal.expires_at:
            raise PaperWorkflowError("proposal has expired; create a fresh proposal")
        quote = self.broker.latest_quote(
            proposal.symbol, feed=self.paper_config["broker"]["market_data_feed"]
        )
        require_quote(
            quote,
            now=clock.timestamp,
            paper_config=self.paper_config,
            prior_ask=proposal.ask,
        )
        if proposal.action == "entry_oto":
            if proposal.maximum_entry_reference is None or quote.ask > proposal.maximum_entry_reference:
                raise PaperWorkflowError("current ask exceeds the proposal's entry guard")
        elif proposal.action == "close_position":
            self._revalidate_exit(proposal, positions)
        self.journal.record_review(
            proposal,
            quote_timestamp=quote.timestamp,
            bid=decimal_string(quote.bid),
            ask=decimal_string(quote.ask),
            reviewed_at=clock.timestamp,
        )
        return {
            "paper_only": True,
            "proposal_id": proposal.proposal_id,
            "confirmation_code": proposal.confirmation_code,
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
            "protective_stop": decimal_string(proposal.stop_price)
            if proposal.stop_price is not None else None,
            "estimated_cost_or_proceeds": decimal_string(proposal.estimated_cost),
            "planned_loss": decimal_string(proposal.planned_loss),
            "risk_limit": decimal_string(proposal.risk_limit),
            "thesis": proposal.thesis,
            "invalidation": proposal.invalidation,
            "exit_reason": proposal.exit_reason,
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
        )

    def _clean_snapshot(
        self,
    ) -> tuple[PaperAccount, PaperClock, list[PaperPosition], list[PaperOrder]]:
        self.journal.verify_integrity()
        account = self.broker.get_account()
        require_account_binding(account, self.journal.account_binding())
        clock = self.broker.get_clock()
        positions = self.broker.list_positions()
        orders = self.broker.list_orders(status="all")
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
    ) -> None:
        terminal = set(self.paper_config["monitoring"]["order_terminal_statuses"])
        require_no_symbol_conflict(proposal.symbol, positions, orders, terminal)
        asset = self.broker.get_asset(proposal.symbol)
        require_asset(asset, proposal.symbol, fractional=proposal.fractional)
        if proposal.fractional:
            raise PaperWorkflowError("Alpaca fractional DAY orders cannot protect a swing overnight")
        if proposal.maximum_entry_reference is None or quote.ask > proposal.maximum_entry_reference:
            raise PaperWorkflowError("current ask exceeds the approved maximum entry reference")
        state = reduce_events(self.journal.events())
        authorize_entry_risk(
            client_order_id=proposal.client_order_id,
            symbol=proposal.symbol,
            account=account,
            quote=quote,
            now=clock.timestamp,
            planned_loss=proposal.planned_loss,
            state=state,
            strategy_config=self.strategy_config,
            kill_switch=self._effective_kill_switch(),
        )

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
        try:
            self.broker.cancel_order(managed.stop_order_id, proposal, permit)
        except Exception as exc:
            self._latch(
                "protective_stop_cancel_uncertain",
                [managed.stop_order_id, type(exc).__name__],
                now,
            )
            raise PaperWorkflowError("protective stop cancellation outcome is uncertain") from None
        stop = self.broker.get_order(managed.stop_order_id)
        if stop.status not in {"canceled", "filled", "expired"}:
            self._latch("protective_stop_cancel_unconfirmed", [managed.stop_order_id], now)
            raise PaperWorkflowError("protective stop cancellation was not confirmed")
        if stop.status == "filled":
            self._latch("protective_stop_filled_during_exit", [managed.stop_order_id], now)
            raise PaperWorkflowError("protective stop filled; close order was not submitted")
        self.journal.append(
            "protective_stop_canceled_for_approved_exit",
            {"symbol": proposal.symbol, "stop_order_id": managed.stop_order_id},
            proposal_id=proposal.proposal_id,
            occurred_at=now,
        )

    def _validate_entry_ack(self, proposal: OrderProposal, order: PaperOrder) -> None:
        if (
            order.client_order_id != proposal.client_order_id
            or order.symbol != proposal.symbol
            or order.side != "buy"
            or order.order_type != "market"
            or order.time_in_force != "gtc"
            or order.order_class != "oto"
            or order.quantity != proposal.quantity
        ):
            raise PaperWorkflowError("broker entry acknowledgement differs from approved order")
        stops = [
            leg for leg in flatten_orders(list(order.legs))
            if leg.side == "sell" and leg.order_type in {"stop", "stop_limit"}
        ]
        if (
            len(stops) != 1
            or stops[0].stop_price != proposal.stop_price
            or stops[0].quantity != proposal.quantity
            or stops[0].time_in_force != "gtc"
        ):
            raise PaperWorkflowError("broker-native protective stop is missing or mismatched")

    @staticmethod
    def _validate_exit_ack(proposal: OrderProposal, order: PaperOrder) -> None:
        if (
            order.client_order_id != proposal.client_order_id
            or order.symbol != proposal.symbol
            or order.side != "sell"
            or order.order_type != "market"
            or order.time_in_force != "day"
            or order.order_class != "simple"
            or order.quantity != proposal.quantity
            or bool(order.legs)
        ):
            raise PaperWorkflowError("broker exit acknowledgement differs from approved order")

    def _resolve_uncertain_submission(
        self, proposal: OrderProposal, now: datetime, original_error: Exception
    ) -> PaperOrder:
        try:
            return self.broker.get_order_by_client_id(proposal.client_order_id)
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
            self.journal.append(
                "kill_switch_latched",
                {"reason": reason, "issues": issues},
                occurred_at=now,
            )

    def _universe_symbol(self, symbol: str) -> str:
        clean = symbol.strip().upper()
        if clean not in self.universe:
            raise PaperWorkflowError("symbol is outside the frozen ETF universe")
        return clean

    def _expected_signal_date(self, clock: PaperClock) -> date:
        days = self.broker.trading_days(
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
