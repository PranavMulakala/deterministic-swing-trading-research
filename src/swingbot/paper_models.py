from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def decimal_string(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    return parsed


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return decimal_string(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def canonical_json(value: Any) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    return json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class PaperAccount:
    account_id: str
    account_number: str
    status: str
    currency: str
    equity: Decimal
    last_equity: Decimal
    cash: Decimal
    non_marginable_buying_power: Decimal
    buying_power: Decimal
    multiplier: Decimal
    long_market_value: Decimal
    short_market_value: Decimal
    trading_blocked: bool
    account_blocked: bool
    trade_suspended_by_user: bool


@dataclass(frozen=True)
class PaperClock:
    timestamp: datetime
    is_open: bool
    next_open: datetime
    next_close: datetime


@dataclass(frozen=True)
class PaperAsset:
    symbol: str
    status: str
    asset_class: str
    exchange: str
    tradable: bool
    fractionable: bool


@dataclass(frozen=True)
class PaperQuote:
    symbol: str
    bid: Decimal
    ask: Decimal
    timestamp: datetime

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")


@dataclass(frozen=True)
class PaperPosition:
    symbol: str
    quantity: Decimal
    side: str
    average_entry_price: Decimal
    current_price: Decimal
    market_value: Decimal


@dataclass(frozen=True)
class PaperOrder:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    order_class: str
    status: str
    quantity: Decimal
    filled_quantity: Decimal
    filled_average_price: Decimal | None = None
    stop_price: Decimal | None = None
    parent_order_id: str | None = None
    legs: tuple["PaperOrder", ...] = field(default_factory=tuple)
    filled_at: datetime | None = None
    extended_hours: bool = False


@dataclass(frozen=True)
class LiveSignal:
    symbol: str
    signal_date: date
    close: Decimal
    sma20: Decimal
    sma200: Decimal
    rsi2: Decimal
    atr14: Decimal
    reason: str
    invalidation: str


@dataclass(frozen=True)
class OrderProposal:
    proposal_id: str
    client_order_id: str
    action: str
    account_id: str
    symbol: str
    side: str
    quantity: Decimal
    order_type: str
    time_in_force: str
    order_class: str
    extended_hours: bool
    created_at: datetime
    expires_at: datetime
    quote_timestamp: datetime
    bid: Decimal
    ask: Decimal
    maximum_entry_reference: Decimal | None
    stop_price: Decimal | None
    estimated_cost: Decimal
    planned_loss: Decimal
    risk_limit: Decimal
    signal_date: date | None
    thesis: str
    invalidation: str
    strategy_config_sha256: str
    fractional: bool
    exit_reason: str | None = None
    protective_stop_order_id: str | None = None
    protective_stop_price: Decimal | None = None

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(canonical_json(self).encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, Any]:
        return json.loads(canonical_json(self))

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "OrderProposal":
        return cls(
            proposal_id=str(payload["proposal_id"]),
            client_order_id=str(payload["client_order_id"]),
            action=str(payload["action"]),
            account_id=str(payload["account_id"]),
            symbol=str(payload["symbol"]),
            side=str(payload["side"]),
            quantity=Decimal(str(payload["quantity"])),
            order_type=str(payload["order_type"]),
            time_in_force=str(payload["time_in_force"]),
            order_class=str(payload["order_class"]),
            extended_hours=bool(payload["extended_hours"]),
            created_at=parse_timestamp(str(payload["created_at"])),
            expires_at=parse_timestamp(str(payload["expires_at"])),
            quote_timestamp=parse_timestamp(str(payload["quote_timestamp"])),
            bid=Decimal(str(payload["bid"])),
            ask=Decimal(str(payload["ask"])),
            maximum_entry_reference=Decimal(str(payload["maximum_entry_reference"]))
            if payload.get("maximum_entry_reference") is not None else None,
            stop_price=Decimal(str(payload["stop_price"]))
            if payload.get("stop_price") is not None else None,
            estimated_cost=Decimal(str(payload["estimated_cost"])),
            planned_loss=Decimal(str(payload["planned_loss"])),
            risk_limit=Decimal(str(payload["risk_limit"])),
            signal_date=date.fromisoformat(str(payload["signal_date"]))
            if payload.get("signal_date") else None,
            thesis=str(payload["thesis"]),
            invalidation=str(payload["invalidation"]),
            strategy_config_sha256=str(payload["strategy_config_sha256"]),
            fractional=bool(payload["fractional"]),
            exit_reason=str(payload["exit_reason"]) if payload.get("exit_reason") else None,
            protective_stop_order_id=str(payload["protective_stop_order_id"])
            if payload.get("protective_stop_order_id") else None,
            protective_stop_price=Decimal(str(payload["protective_stop_price"]))
            if payload.get("protective_stop_price") is not None else None,
        )


@dataclass(frozen=True)
class ApprovalPermit:
    proposal_id: str
    content_hash: str
    approval_event_id: str
    review_event_id: str
    session_id: str
