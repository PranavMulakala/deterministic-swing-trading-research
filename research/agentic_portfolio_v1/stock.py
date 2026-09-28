"""Deterministic +10% net-return stock swing shadow strategy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import median
from typing import Any

from .common import ValidationError, aware_datetime, ceil_cent, decimal_value, floor_units
from .decisions import PaperDecision
from .evidence import EvidencePacket
from .risk import RiskLedger, RiskRejected


STRATEGY = "stock_swing_net10_v1"
VERSION = "1.0.0"
UNIVERSE = frozenset({"LITE", "COHR", "CIEN", "FN", "AAOI"})


@dataclass(frozen=True)
class CostModel:
    entry_bps: Decimal = Decimal("10")
    exit_bps: Decimal = Decimal("10")
    entry_fixed: Decimal = Decimal("0")
    exit_fixed: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        for name in ("entry_bps", "exit_bps", "entry_fixed", "exit_fixed"):
            decimal_value(getattr(self, name), field=name, nonnegative=True)
        if self.exit_bps >= Decimal("10000"):
            raise ValidationError("exit_bps must be below 10000")


@dataclass(frozen=True)
class StockPlan:
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    actual_entry_debit: Decimal
    target_price: Decimal
    opened_at: datetime
    thesis: str
    invalidation: str
    evidence_hash: str
    reunderwritten_at: datetime | None = None


def entry_cost(quantity: Decimal, price: Decimal, costs: CostModel) -> Decimal:
    gross = quantity * price
    return costs.entry_fixed + gross * costs.entry_bps / Decimal("10000")


def target_for_net_return(
    *, quantity: Decimal, actual_entry_debit: Decimal, costs: CostModel,
    target_return: Decimal = Decimal("0.10"),
) -> Decimal:
    qty = decimal_value(quantity, field="quantity", positive=True)
    debit = decimal_value(actual_entry_debit, field="actual_entry_debit", positive=True)
    goal = decimal_value(target_return, field="target_return", positive=True)
    denominator = qty * (Decimal("1") - costs.exit_bps / Decimal("10000"))
    # The ledger floors exit credits to cents. Require the next whole cent at or
    # above the economic goal before solving for price, then round price upward.
    required_cash_credit = ceil_cent(debit * (Decimal("1") + goal))
    raw = (required_cash_credit + costs.exit_fixed) / denominator
    return ceil_cent(raw)


def net_return_at(price: Decimal, quantity: Decimal, debit: Decimal, costs: CostModel) -> Decimal:
    gross = quantity * price
    exit_cost = costs.exit_fixed + gross * costs.exit_bps / Decimal("10000")
    return (gross - exit_cost - debit) / debit


class StockSwingEngine:
    """Creates reservations and paper plans; it cannot submit an order."""

    def __init__(self, ledger: RiskLedger, costs: CostModel | None = None):
        self.ledger = ledger
        self.costs = costs or CostModel()

    @staticmethod
    def _validate_features(packet: EvidencePacket, decision_at: datetime) -> dict[str, Any]:
        if packet.kind != "stock_entry" or packet.strategy != STRATEGY or packet.version != VERSION:
            raise ValidationError("wrong stock evidence kind, strategy, or version")
        if packet.symbol not in UNIVERSE:
            raise ValidationError("symbol is outside the frozen universe")
        packet.validate_at(decision_at, timedelta(minutes=5))
        required = {
            "price", "next_ask", "entry_limit", "dollar_volumes_20", "atr14", "session_return",
            "session_vwap", "sma50", "earnings_sessions_away", "hard_adverse_news",
            "thesis_broken", "thesis", "invalidation",
        }
        if set(packet.data) != required:
            raise ValidationError("stock evidence data fields do not match the frozen protocol")
        data = packet.data
        for name in ("price", "next_ask", "entry_limit", "atr14", "session_return", "session_vwap", "sma50"):
            decimal_value(data[name], field=name)
        volumes = data["dollar_volumes_20"]
        if type(volumes) is not list or len(volumes) != 20:
            raise ValidationError("dollar_volumes_20 must contain exactly 20 observations")
        for index, value in enumerate(volumes):
            decimal_value(value, field=f"dollar_volumes_20[{index}]", nonnegative=True)
        earnings = data["earnings_sessions_away"]
        if earnings is not None and (isinstance(earnings, bool) or not isinstance(earnings, int) or earnings < 0):
            raise ValidationError("earnings_sessions_away must be null or a nonnegative integer")
        for field in ("hard_adverse_news", "thesis_broken"):
            if type(data[field]) is not bool:
                raise ValidationError(f"{field} must be boolean")
        for field in ("thesis", "invalidation"):
            if not isinstance(data[field], str) or not data[field].strip():
                raise ValidationError(f"{field} must be non-empty")
        return data

    def evaluate_entry(self, packet: EvidencePacket, decision_at: datetime, idempotency_key: str) -> PaperDecision:
        symbol = packet.symbol if isinstance(packet, EvidencePacket) else "UNKNOWN"
        evidence_hash = packet.evidence_hash if isinstance(packet, EvidencePacket) else None
        try:
            self.ledger.expire_reservations(decision_at)
        except (ValidationError, RiskRejected, TypeError, ValueError, ArithmeticError) as exc:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, symbol, (str(exc),), evidence_hash)
        try:
            data = self._validate_features(packet, decision_at)
        except (ValidationError, KeyError, TypeError, ValueError, ArithmeticError, AttributeError) as exc:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, symbol, (str(exc),), evidence_hash)
        px = decimal_value(data["price"], field="price")
        ask = decimal_value(data["next_ask"], field="next_ask")
        limit_px = decimal_value(data["entry_limit"], field="entry_limit")
        atr = decimal_value(data["atr14"], field="atr14")
        session_return = decimal_value(data["session_return"], field="session_return")
        vwap = decimal_value(data["session_vwap"], field="session_vwap")
        sma50 = decimal_value(data["sma50"], field="sma50")
        volumes = [decimal_value(v, field="volume", nonnegative=True) for v in data["dollar_volumes_20"]]
        failures: list[str] = []
        if px < 10:
            failures.append("price below $10")
        if Decimal(str(median(volumes))) < Decimal("50000000"):
            failures.append("20-day median dollar volume below $50m")
        if px <= 0 or not Decimal("0.03") <= atr / px <= Decimal("0.10"):
            failures.append("ATR14/price outside 3%-10%")
        if not Decimal("-0.10") <= session_return <= Decimal("-0.02"):
            failures.append("session return outside -10% to -2%")
        if px < vwap:
            failures.append("close did not reclaim session VWAP")
        if px < sma50:
            failures.append("close below SMA50")
        earnings = data["earnings_sessions_away"]
        if earnings is not None and earnings <= 3:
            failures.append("earnings within three sessions")
        if data["hard_adverse_news"] or data["thesis_broken"]:
            failures.append("hard-adverse news or thesis flag")
        if ask <= 0 or limit_px <= 0 or ask > limit_px:
            failures.append("next executable ask is absent or above limit")
        if self.ledger.has_position(STRATEGY, packet.symbol):
            failures.append("position already exists; averaging down is prohibited")
        if failures:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, packet.symbol, tuple(failures), packet.evidence_hash)
        try:
            snapshot = self.ledger.snapshot(decision_at)
        except RiskRejected as exc:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, packet.symbol, (str(exc),), packet.evidence_hash)
        budget = Decimal(snapshot["equity_cents"]) / 100 * Decimal("0.20")
        qty = floor_units((budget - self.costs.entry_fixed) / (ask * (Decimal("1") + self.costs.entry_bps / Decimal("10000"))))
        if qty <= 0:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, packet.symbol, ("zero quantity",), packet.evidence_hash)
        modeled_cost = entry_cost(qty, ask, self.costs)
        debit = qty * ask + modeled_cost
        target = target_for_net_return(quantity=qty, actual_entry_debit=debit, costs=self.costs)
        try:
            reservation = self.ledger.reserve(
                idempotency_key=idempotency_key, strategy=STRATEGY, symbol=packet.symbol,
                asset_type="EQUITY", notional=debit, contractual_loss=debit, now=decision_at,
                quantity=qty, evidence_hash=packet.evidence_hash, strategy_version=VERSION,
            )
        except RiskRejected as exc:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, packet.symbol, (str(exc),), packet.evidence_hash)
        if reservation["replay"] or reservation["status"] not in {"OPEN", "PARTIAL"}:
            return PaperDecision(
                "ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, packet.symbol,
                (f"reservation replay/status {reservation['status']} creates no new intent",), packet.evidence_hash,
                {"reservation": reservation, "paper_only": True},
            )
        return PaperDecision(
            "PAPER_ENTRY_INTENT", STRATEGY, VERSION, self.ledger.account_id, packet.symbol,
            ("all frozen entry filters passed", "next executable ask is at or below limit"), packet.evidence_hash,
            {"quantity": str(qty), "modeled_entry_price": str(ask), "modeled_entry_debit": str(debit),
             "target_price": str(target), "reservation": reservation, "thesis": data["thesis"],
             "invalidation": data["invalidation"],
             "review_conditions": "review at -10% from basis or 21 sessions; exit if missing at 42; max 126",
             "modeled_downside": str(debit), "research_assumption": True},
        )

    def plan_from_fills(
        self, *, symbol: str, opened_at: datetime, thesis: str, invalidation: str,
        evidence_hash: str,
    ) -> StockPlan:
        """Recalculate the target from durable simulated fills, including partial fills and costs."""
        state = self.ledger.get_open_stock_entry_state(
            STRATEGY, symbol, strategy_version=VERSION,
        )
        durable_opened = aware_datetime(state["opened_at"], field="position.opened_at")
        supplied_opened = aware_datetime(opened_at, field="opened_at")
        if supplied_opened != durable_opened:
            raise ValidationError("supplied opened_at does not match the durable stock position")
        if not isinstance(evidence_hash, str) or len(evidence_hash) != 64:
            raise ValidationError("evidence_hash must be a SHA-256 string")
        if state["external_evidence_bound"] and evidence_hash != state["evidence_hash"]:
            raise ValidationError("supplied evidence hash does not match the durable stock reservation")
        qty = decimal_value(state["quantity"], field="position.quantity", positive=True)
        actual_debit = Decimal(int(state["basis_cents"])) / 100
        average_entry = actual_debit / qty
        return StockPlan(
            symbol=symbol, quantity=qty, entry_price=average_entry,
            actual_entry_debit=actual_debit,
            target_price=target_for_net_return(
                quantity=qty, actual_entry_debit=actual_debit, costs=self.costs
            ),
            opened_at=durable_opened, thesis=thesis,
            invalidation=invalidation, evidence_hash=state["evidence_hash"],
        )

    @staticmethod
    def _completed_weekday_sessions(opened_at: datetime, decision_at: datetime) -> int:
        opened = aware_datetime(opened_at, field="opened_at").date()
        decision = aware_datetime(decision_at, field="decision_at").date()
        count = 0
        cursor = opened + timedelta(days=1)
        while cursor <= decision:
            if cursor.weekday() < 5:
                count += 1
            cursor += timedelta(days=1)
        return count

    def evaluate_position(
        self, plan: StockPlan, packet: EvidencePacket, *, sessions_held: int,
        decision_at: datetime, reunderwritten_at: datetime | None = None,
    ) -> PaperDecision:
        symbol = getattr(plan, "symbol", getattr(packet, "symbol", "UNKNOWN"))
        packet_hash = getattr(packet, "evidence_hash", None)
        try:
            if not isinstance(plan, StockPlan) or not isinstance(packet, EvidencePacket):
                raise ValidationError("stock management requires a StockPlan and EvidencePacket")
            durable = self.ledger.get_open_stock_entry_state(
                STRATEGY, plan.symbol, strategy_version=VERSION,
            )
            durable_qty = decimal_value(durable["quantity"], field="durable.quantity", positive=True)
            durable_debit = Decimal(int(durable["basis_cents"])) / 100
            durable_opened = aware_datetime(durable["opened_at"], field="durable.opened_at")
            durable_last_fill = aware_datetime(durable["last_fill_at"], field="durable.last_fill_at")
            durable_entry = durable_debit / durable_qty
            durable_target = target_for_net_return(
                quantity=durable_qty, actual_entry_debit=durable_debit, costs=self.costs,
            )
            if (
                plan.quantity != durable_qty or plan.actual_entry_debit != durable_debit
                or plan.entry_price != durable_entry or plan.target_price != durable_target
                or aware_datetime(plan.opened_at, field="plan.opened_at") != durable_opened
                or plan.evidence_hash != durable["evidence_hash"]
            ):
                raise ValidationError("stock plan economics are not bound to the durable position and fills")
            if (
                packet.kind != "stock_management" or packet.strategy != STRATEGY
                or packet.version != VERSION or packet.symbol != plan.symbol
            ):
                raise ValidationError("invalid management evidence")
            decision = aware_datetime(decision_at, field="decision_at")
            packet.validate_at(decision, timedelta(minutes=5))
            if decision < durable_last_fill or any(
                evidence_time < durable_last_fill
                for evidence_time in (packet.feature_as_of, packet.observed_at, packet.retrieved_at)
            ):
                raise ValidationError("stock management evidence predates the latest durable fill")
            price = decimal_value(packet.data["price"], field="price", positive=True)
            thesis_broken = packet.data["thesis_broken"]
            if type(thesis_broken) is not bool or set(packet.data) != {"price", "thesis_broken"}:
                raise ValidationError("malformed management evidence")
            if isinstance(sessions_held, bool) or not isinstance(sessions_held, int) or sessions_held < 0:
                raise ValidationError("invalid reported sessions_held")
            derived_sessions = self._completed_weekday_sessions(durable_opened, decision)
            if reunderwritten_at is not None:
                reviewed = aware_datetime(reunderwritten_at, field="reunderwritten_at")
                if reviewed > decision or reviewed < plan.opened_at:
                    raise ValidationError("re-underwrite timestamp outside position lifetime")
        except (ValidationError, RiskRejected, KeyError, TypeError, ValueError, ArithmeticError, AttributeError) as exc:
            return PaperDecision("ABSTAIN", STRATEGY, VERSION, self.ledger.account_id, symbol, (str(exc),), packet_hash)
        if thesis_broken:
            action, reasons = "PAPER_EXIT_INTENT", ("explicit thesis_broken flag",)
        elif price >= plan.target_price:
            action, reasons = "PAPER_EXIT_INTENT", ("10% net target reached under modeled exit costs",)
        elif derived_sessions >= 126:
            action, reasons = "PAPER_EXIT_INTENT", ("absolute 126-session paper hold reached",)
        elif derived_sessions >= 42 and reunderwritten_at is None:
            action, reasons = "PAPER_EXIT_INTENT", ("required 42-session re-underwrite absent",)
        elif (derived_sessions >= 21 and reunderwritten_at is None) or price <= plan.entry_price * Decimal("0.90"):
            action, reasons = "REVIEW_REQUIRED", ("21-session or -10% basis review threshold", "this is not an automatic stop")
        else:
            action, reasons = "HOLD", ("no frozen management condition fired",)
        return PaperDecision(action, STRATEGY, VERSION, self.ledger.account_id, plan.symbol, reasons, packet.evidence_hash,
                             {"price": str(price), "target_price": str(plan.target_price),
                              "sessions_held": derived_sessions,
                              "reported_sessions_held": sessions_held,
                              "session_basis": "durable open time plus conservative UTC weekdays"})
