from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ManagedPosition:
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    entry_date: date
    planned_loss: Decimal
    stop_price: Decimal
    parent_order_id: str
    stop_order_id: str
    entry_client_order_id: str


@dataclass(frozen=True)
class SubmittedOrder:
    proposal_id: str
    action: str
    symbol: str
    broker_order_id: str
    client_order_id: str
    planned_loss: Decimal


@dataclass
class OperationalState:
    positions: dict[str, ManagedPosition] = field(default_factory=dict)
    submitted_by_client_id: dict[str, SubmittedOrder] = field(default_factory=dict)
    last_order_status: dict[str, str] = field(default_factory=dict)
    realized_pnl_by_day: dict[date, Decimal] = field(default_factory=dict)
    known_broker_order_ids: set[str] = field(default_factory=set)
    pending_entry_risk_by_symbol: dict[str, Decimal] = field(default_factory=dict)

    def realized_pnl(self, day: date) -> Decimal:
        return self.realized_pnl_by_day.get(day, Decimal("0"))


def reduce_events(events: list[dict[str, Any]]) -> OperationalState:
    state = OperationalState()
    for event in events:
        event_type = event["event_type"]
        payload = event["payload"]
        if event_type == "order_submitted":
            submitted = SubmittedOrder(
                proposal_id=str(event["proposal_id"]),
                action=str(payload["action"]),
                symbol=str(payload["symbol"]),
                broker_order_id=str(payload["broker_order_id"]),
                client_order_id=str(payload["client_order_id"]),
                planned_loss=Decimal(str(payload.get("planned_loss", "0"))),
            )
            state.submitted_by_client_id[submitted.client_order_id] = submitted
            state.known_broker_order_ids.add(submitted.broker_order_id)
            state.last_order_status[submitted.broker_order_id] = str(payload["status"])
        elif event_type == "order_status_observed":
            order_id = str(payload["broker_order_id"])
            state.last_order_status[order_id] = str(payload["status"])
            state.known_broker_order_ids.add(order_id)
            for child_id in payload.get("leg_order_ids", []):
                state.known_broker_order_ids.add(str(child_id))
        elif event_type == "entry_filled":
            managed = ManagedPosition(
                symbol=str(payload["symbol"]),
                quantity=Decimal(str(payload["quantity"])),
                entry_price=Decimal(str(payload["entry_price"])),
                entry_date=date.fromisoformat(str(payload["entry_date"])),
                planned_loss=Decimal(str(payload["planned_loss"])),
                stop_price=Decimal(str(payload["stop_price"])),
                parent_order_id=str(payload["parent_order_id"]),
                stop_order_id=str(payload["stop_order_id"]),
                entry_client_order_id=str(payload["client_order_id"]),
            )
            state.positions[managed.symbol] = managed
            state.known_broker_order_ids.update(
                {managed.parent_order_id, managed.stop_order_id}
            )
        elif event_type == "position_closed":
            state.positions.pop(str(payload["symbol"]), None)
            pnl = Decimal(str(payload.get("realized_pnl", "0")))
            day = date.fromisoformat(str(payload["closed_date"]))
            state.realized_pnl_by_day[day] = state.realized_pnl(day) + pnl
    terminal = {"filled", "canceled", "expired", "rejected", "replaced"}
    for submitted in state.submitted_by_client_id.values():
        status = state.last_order_status.get(submitted.broker_order_id, "")
        if (
            submitted.action == "entry_oto"
            and submitted.symbol not in state.positions
            and status not in terminal
        ):
            state.pending_entry_risk_by_symbol[submitted.symbol] = submitted.planned_loss
    return state
