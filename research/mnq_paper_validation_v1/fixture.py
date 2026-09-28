"""Explicitly synthetic records for software checks, never broker evidence."""
from copy import deepcopy
import hashlib

from compare import EXECUTION_MODEL, frozen_fingerprint


def bundles(root):
    content = b"SYNTHETIC FIXTURE ONLY. No broker account, orders, or fills exist.\n"
    (root / "synthetic-source.txt").write_bytes(content)
    common = {
        "schema_version": 1,
        "evidence_kind": "SYNTHETIC_FIXTURE",
        "strategy_fingerprint": frozen_fingerprint(),
        "execution_model": deepcopy(EXECUTION_MODEL),
        "execution_model_source": "synthetic-source.txt",
        "symbol": "MNQU6",
        "window": {"start": "2026-09-09T13:30:00Z", "end": "2026-09-09T14:00:00Z"},
        "exported_at": "2026-09-09T14:01:00Z",
        "complete": True,
        "source_files": [{"path": "synthetic-source.txt", "sha256": hashlib.sha256(content).hexdigest()}],
    }
    decision = {"signal_id": "FIXTURE-ONLY-signal-1", "at": "2026-09-09T13:45:00Z",
                "direction": 1, "decision": "ENTER", "reason": "ENTERED"}
    paper = dict(deepcopy(common), account_mode="PAPER", broker="SYNTHETIC-NO-BROKER",
                 account_alias="FIXTURE-NO-ACCOUNT", fees_complete=True,
                 clock_alignment_verified=True, clock_alignment_source="synthetic-source.txt",
                 cash_ledger_complete=True, cash_flows=[], cash_snapshots=[],
                 decisions=[deepcopy(decision)], orders=[], fills=[], positions=[])
    sim = dict(deepcopy(common), clock_basis="EXCHANGE_EVENT_UTC",
               market_data_complete=True, signals=[])
    for identity, leg, side, submitted, ack, filled, price, trigger in (
        ("fixture-entry", "ENTRY", "BUY", "13:45:01", "13:45:01.010", "13:45:01.020", "22000.00", None),
        ("fixture-exit", "EXIT", "SELL", "13:46:00", "13:46:00.010", "13:46:00.020", "22004.00", "13:45:59.900"),
    ):
        at = lambda value: "2026-09-09T" + value + "Z"
        paper["orders"].append({
            "order_id": identity, "signal_id": decision["signal_id"], "leg": leg,
            "symbol": "MNQU6", "side": side, "quantity": 1, "filled_quantity": 1,
            "order_type": "MARKET", "submitted_at": at(submitted), "acknowledgement_received_at": at(ack),
            "broker_acknowledged_at": at(ack),
            "reference_quote_at": at(submitted), "reference_quote_received_at": at(submitted),
            "trigger_at": at(trigger) if trigger else None,
            "trigger_basis": "LIQUIDATION_SIDE_BBO" if trigger else "SIGNAL_CONFIRMATION",
            "status": "FILLED",
        })
        paper["fills"].append({"fill_id": identity + "-fill", "order_id": identity, "at": at(filled),
                               "quantity": 1, "price": price, "fee_usd": "1.00", "fee_source": "BROKER_EXPORT",
                               "fee_source_reference": "synthetic-source.txt"})
        decision[leg.lower()] = {"at": at(filled), "price": price, "quantity": 1, "fee_usd": "1.00"}
    paper["positions"] = [
        {"snapshot_id": "fixture-start", "symbol": "MNQU6", "at": common["window"]["start"], "quantity": 0},
        {"snapshot_id": "fixture-end", "symbol": "MNQU6", "at": common["window"]["end"], "quantity": 0},
    ]
    paper["cash_snapshots"] = [
        {"snapshot_id": "fixture-start-cash", "at": common["window"]["start"], "currency": "USD", "cash_usd": "5000.00"},
        {"snapshot_id": "fixture-end-cash", "at": common["window"]["end"], "currency": "USD", "cash_usd": "5006.00"},
    ]
    sim["signals"].append(decision)
    return paper, sim
