"""Separate $1,000 long-option shadow experiment with no order capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from .common import ValidationError, aware_datetime, decimal_value
from .council import validate_council
from .decisions import PaperDecision
from .evidence import EvidencePacket
from .risk import RiskLedger, RiskRejected


STRATEGY = "long_option_shadow_v2"
VERSION = "2.0.0"
UNDERLYINGS = frozenset({"SPY", "QQQ"})


@dataclass(frozen=True)
class OptionPlan:
    contract: str
    entry_premium: Decimal
    opened_at: datetime
    entry_session: date
    stop_premium: Decimal
    target_premium: Decimal
    evidence_hash: str


class OptionShadowEngine:
    def __init__(self, ledger: RiskLedger, *, mode: str = "baseline"):
        if mode not in {"baseline", "council"}:
            raise ValidationError("mode must be baseline or council")
        self.ledger = ledger
        self.mode = mode

    def evaluate_entry(
        self, packet: EvidencePacket, decision_at: datetime, idempotency_key: str,
        *, analyst: Any = None, critic: Any = None,
    ) -> PaperDecision:
        symbol, evidence_hash = self._safe_packet_identity(packet)
        try:
            self.ledger.expire_reservations(decision_at)
        except (ValidationError, RiskRejected, TypeError, ValueError, ArithmeticError) as exc:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, symbol, (str(exc),), evidence_hash)
        try:
            data = self._validate(packet, decision_at)
        except (ValidationError, KeyError, TypeError, ValueError, ArithmeticError, AttributeError) as exc:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, symbol, (str(exc),), evidence_hash)
        if self.ledger.open_positions() or self.ledger.has_active_reservation(
            asset_type="OPTION", excluding_idempotency_key=idempotency_key
        ):
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, symbol, ("one-position limit already reached",), evidence_hash)
        if self.mode == "baseline":
            trend = decimal_value(data["trend_3bar_bps"], field="trend_3bar_bps")
            action = "CALL" if trend >= 30 else "PUT" if trend <= -30 else "ABSTAIN"
            reason = "deterministic three-bar baseline"
        else:
            council = validate_council(analyst, critic, packet, decision_at)
            action, reason = council.action, council.reason
            if not council.accepted:
                action = "ABSTAIN"
        if action == "ABSTAIN":
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, symbol, (reason,), evidence_hash)
        if action != data["right"]:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, symbol, ("signal and listed contract right conflict",), evidence_hash)
        ask = decimal_value(data["ask"], field="ask", positive=True)
        entry_premium = ask + Decimal("0.01")
        fee = Decimal("0.65")
        contractual_loss = entry_premium * 100 + fee
        contract = f"{symbol}:{data['expiration']}:{data['right']}:{data['strike']}"
        try:
            reservation = self.ledger.reserve(
                idempotency_key=idempotency_key, strategy=STRATEGY, symbol=contract,
                asset_type="OPTION", notional=contractual_loss,
                contractual_loss=contractual_loss, now=decision_at, quantity=Decimal("1"),
                evidence_hash=evidence_hash, strategy_version=VERSION,
            )
        except (RiskRejected, ValidationError) as exc:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, contract, (str(exc),), evidence_hash,
                                 {"contractual_loss": str(contractual_loss), "budget_note": "one contract is indivisible"})
        if reservation["replay"] or reservation["status"] not in {"OPEN", "PARTIAL"}:
            return PaperDecision(
                "ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, contract,
                (f"reservation replay/status {reservation['status']} creates no new intent",), evidence_hash,
                {"reservation": reservation, "paper_only": True},
            )
        return PaperDecision(
            "PAPER_ENTRY_INTENT", STRATEGY, VERSION, self.ledger.account_id, contract,
            (reason, "all deterministic option and liquidity filters passed"), evidence_hash,
            {"contracts": 1, "modeled_entry_premium": str(entry_premium),
             "contractual_loss": str(contractual_loss), "stop_premium": str(entry_premium * Decimal("0.70")),
             "target_premium": str(entry_premium * Decimal("1.50")), "max_hold_sessions": 2,
             "invalidation": "30% premium decline or two-session maximum hold",
             "review_conditions": "every fresh packet; exit at stop, target, or session limit",
             "reservation": reservation, "research_assumption": True},
        )

    @staticmethod
    def _safe_packet_identity(packet: Any) -> tuple[str, str | None]:
        symbol = getattr(packet, "symbol", "UNKNOWN")
        evidence_hash = getattr(packet, "evidence_hash", None)
        return (
            symbol if isinstance(symbol, str) and symbol else "UNKNOWN",
            evidence_hash if isinstance(evidence_hash, str) else None,
        )

    @staticmethod
    def _validate(packet: EvidencePacket, decision_at: datetime) -> dict[str, Any]:
        if not isinstance(packet, EvidencePacket):
            raise ValidationError("option evidence must be an EvidencePacket")
        if packet.kind != "option_entry" or packet.strategy != STRATEGY or packet.version != VERSION:
            raise ValidationError("wrong option evidence kind, strategy, or version")
        if packet.symbol not in UNDERLYINGS:
            raise ValidationError("underlying outside SPY/QQQ")
        packet.validate_at(decision_at, timedelta(seconds=30))
        required = {"underlying_price", "bid", "ask", "open_interest", "volume", "expiration", "strike", "right", "trend_3bar_bps"}
        if set(packet.data) != required:
            raise ValidationError("option evidence fields do not match protocol")
        data = packet.data
        underlying = decimal_value(data["underlying_price"], field="underlying_price", positive=True)
        bid = decimal_value(data["bid"], field="bid", nonnegative=True)
        ask = decimal_value(data["ask"], field="ask", positive=True)
        strike = decimal_value(data["strike"], field="strike", positive=True)
        decimal_value(data["trend_3bar_bps"], field="trend_3bar_bps")
        for name in ("open_interest", "volume"):
            if isinstance(data[name], bool) or not isinstance(data[name], int) or data[name] < 0:
                raise ValidationError(f"{name} must be a nonnegative integer")
        if not isinstance(data["right"], str) or data["right"] not in {"CALL", "PUT"}:
            raise ValidationError("right must be CALL or PUT")
        try:
            expiration = date.fromisoformat(data["expiration"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("expiration must be YYYY-MM-DD") from exc
        dte = (expiration - packet.observed_at.date()).days
        if not 14 <= dte <= 30:
            raise ValidationError("DTE outside 14-30")
        if abs(strike / underlying - Decimal("1")) > Decimal("0.05"):
            raise ValidationError("strike more than 5% from underlying")
        spread = ask - bid
        if bid > ask or spread > Decimal("0.05") or spread / ask > Decimal("0.15"):
            raise ValidationError("liquidity spread filter failed")
        if data["open_interest"] < 500 or data["volume"] < 100:
            raise ValidationError("open-interest or volume floor failed")
        return data

    def plan_from_fill(self, contract: str) -> OptionPlan:
        """Construct management economics only from the verified durable fill."""
        state = self.ledger.get_open_option_entry_state(
            STRATEGY, contract, strategy_version=VERSION,
        )
        premium = decimal_value(state["entry_premium"], field="entry_premium", positive=True)
        opened = aware_datetime(state["opened_at"], field="opened_at")
        return OptionPlan(
            contract=contract, entry_premium=premium, opened_at=opened, entry_session=opened.date(),
            stop_premium=premium * Decimal("0.70"), target_premium=premium * Decimal("1.50"),
            evidence_hash=state["evidence_hash"],
        )

    @staticmethod
    def _completed_weekday_sessions(opened: date, decision: date) -> int:
        """Conservative offline proxy: count weekdays after entry through decision."""
        return len(OptionShadowEngine._completed_weekday_dates(opened, decision))

    @staticmethod
    def _completed_weekday_dates(opened: date, decision: date) -> list[date]:
        """Return the deterministic UTC weekday approximation used by v2."""
        completed: list[date] = []
        cursor = opened + timedelta(days=1)
        while cursor <= decision:
            if cursor.weekday() < 5:
                completed.append(cursor)
            cursor += timedelta(days=1)
        return completed

    def evaluate_position(self, plan: OptionPlan, packet: EvidencePacket, decision_at: datetime) -> PaperDecision:
        symbol, evidence_hash = self._safe_packet_identity(packet)
        try:
            if not isinstance(plan, OptionPlan) or not isinstance(packet, EvidencePacket):
                raise ValidationError("option management requires a plan and EvidencePacket")
            durable = self.ledger.get_open_option_entry_state(
                STRATEGY, plan.contract, strategy_version=VERSION,
            )
            durable_premium = decimal_value(durable["entry_premium"], field="durable.entry_premium", positive=True)
            durable_opened = aware_datetime(durable["opened_at"], field="durable.opened_at")
            if (
                plan.entry_premium != durable_premium or aware_datetime(plan.opened_at) != durable_opened
                or plan.entry_session != durable_opened.date()
                or plan.stop_premium != durable_premium * Decimal("0.70")
                or plan.target_premium != durable_premium * Decimal("1.50")
                or plan.evidence_hash != durable["evidence_hash"] or durable["contract"] != plan.contract
            ):
                raise ValidationError("option plan economics are not bound to the durable entry/fill")
            if packet.kind != "option_management" or packet.strategy != STRATEGY or packet.version != VERSION:
                raise ValidationError("wrong option-management evidence identity")
            decision = aware_datetime(decision_at, field="decision_at")
            packet.validate_at(decision, timedelta(seconds=30))
            if decision < durable_opened or any(
                evidence_time < durable_opened
                for evidence_time in (packet.feature_as_of, packet.observed_at, packet.retrieved_at)
            ):
                raise ValidationError("option management evidence predates the durable fill")
            parts = plan.contract.split(":")
            if len(parts) != 4 or packet.symbol != parts[0] or parts[2] not in {"CALL", "PUT"}:
                raise ValidationError("management underlying does not match contract")
            date.fromisoformat(parts[1])
            decimal_value(parts[3], field="contract.strike", positive=True)
            required = {"contract", "premium", "sessions_held", "entry_evidence_hash", "opened_at", "position_quantity"}
            if set(packet.data) not in {frozenset(required), frozenset(required | {"completed_session_dates"})}:
                raise ValidationError("option-management evidence fields do not match protocol")
            if (
                packet.data["contract"] != plan.contract
                or packet.data["entry_evidence_hash"] != plan.evidence_hash
                or aware_datetime(packet.data["opened_at"], field="opened_at") != aware_datetime(plan.opened_at)
            ):
                raise ValidationError("management packet is not bound to the exact option plan")
            px = decimal_value(packet.data["premium"], field="premium", nonnegative=True)
            sessions_held = packet.data["sessions_held"]
            if isinstance(sessions_held, bool) or not isinstance(sessions_held, int) or sessions_held < 0:
                raise ValidationError("sessions_held must be a nonnegative integer")
            opened = aware_datetime(plan.opened_at, field="plan.opened_at")
            if plan.entry_session != opened.date() or decision < opened:
                raise ValidationError("option plan entry time/session is invalid")
            completed_weekdays = self._completed_weekday_dates(opened.date(), decision.date())
            derived_sessions = len(completed_weekdays)
            completed_session_dates: list[date] | None = None
            if "completed_session_dates" in packet.data:
                raw_dates = packet.data["completed_session_dates"]
                if type(raw_dates) is not list or not all(isinstance(value, str) for value in raw_dates):
                    raise ValidationError("completed_session_dates must be a list of ISO dates")
                completed_session_dates = [date.fromisoformat(value) for value in raw_dates]
                if (
                    completed_session_dates != completed_weekdays
                    or sessions_held != len(completed_weekdays)
                ):
                    raise ValidationError("completed session calendar conflicts with durable UTC timestamps")
            if decimal_value(packet.data["position_quantity"], field="position_quantity", positive=True) != 1:
                raise ValidationError("management packet must identify exactly one contract")
            expiration = date.fromisoformat(parts[1])
        except (ValidationError, RiskRejected, KeyError, TypeError, ValueError, ArithmeticError, AttributeError) as exc:
            return PaperDecision(
                "ABSTAIN", STRATEGY, VERSION, self.ledger.account_id,
                plan.contract if isinstance(plan, OptionPlan) else symbol, (str(exc),), evidence_hash,
            )
        if decision.date() >= expiration:
            action, reason = "PAPER_EXIT_INTENT", "contract expiration reached; exit enforced independently"
        elif px <= plan.stop_premium:
            action, reason = "PAPER_EXIT_INTENT", "30% premium stop reached"
        elif px >= plan.target_premium:
            action, reason = "PAPER_EXIT_INTENT", "50% premium target reached"
        elif derived_sessions >= 2:
            action, reason = "PAPER_EXIT_INTENT", "two-session conservative weekday upper bound reached"
        else:
            action, reason = "HOLD", "no option management condition fired"
        return PaperDecision(action, STRATEGY, VERSION, self.ledger.account_id, plan.contract, (reason,), evidence_hash,
                             {"premium": str(px), "sessions_held": derived_sessions,
                              "reported_sessions_held": sessions_held,
                              "session_basis": "durable open time plus conservative UTC weekday upper bound",
                              "calendar_cross_check": completed_session_dates is not None,
                              "expiration": expiration.isoformat()})
