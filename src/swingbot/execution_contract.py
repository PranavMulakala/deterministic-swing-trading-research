from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BracketOrderIntent:
    client_order_id: str
    symbol: str
    quantity: float
    entry_type: str
    time_in_force: str
    protective_stop_price: float


@dataclass(frozen=True)
class BrokerAcknowledgement:
    broker_order_id: str
    client_order_id: str
    entry_status: str
    protective_stop_status: str


class PaperBroker(Protocol):
    def submit_native_bracket(self, order: BracketOrderIntent) -> BrokerAcknowledgement:
        """Submit an entry whose protective stop is native at the broker."""

    def position_is_closed(self, symbol: str) -> bool:
        """Return broker-confirmed state; local state must not lead this state."""


class ExecutionDisabled(RuntimeError):
    pass


def submit_paper_order(*_: object, **__: object) -> None:
    """Historical milestone-1 boundary; the separate paper adapter never calls it."""
    raise ExecutionDisabled(
        "the legacy milestone-1 research submission function remains disabled"
    )
