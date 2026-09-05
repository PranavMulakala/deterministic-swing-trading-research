from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import BacktestResult


def validate_results(
    results: list[BacktestResult], output_dir: Path, config: dict[str, Any]
) -> dict[str, object]:
    checks: list[dict[str, object]] = []

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    all_trades = [trade for result in results for trade in result.trades]
    record(
        "next_bar_entries",
        all(trade.entry_date > trade.signal_date for trade in all_trades),
        f"checked {len(all_trades)} trades",
    )
    signaled_exits = [trade for trade in all_trades if trade.exit_signal_date is not None]
    record(
        "next_bar_signal_exits",
        all(trade.exit_date > trade.exit_signal_date for trade in signaled_exits),
        f"checked {len(signaled_exits)} close-derived exits",
    )
    record(
        "per_trade_risk",
        all(trade.planned_loss <= trade.risk_limit + 1e-8 for trade in all_trades),
        f"maximum observed {max((trade.planned_risk_pct for trade in all_trades), default=0):.8f}%",
    )
    sequence_ok = all(
        [int(event["seq"]) for event in result.events] == list(range(1, len(result.events) + 1))
        for result in results
    )
    record("ledger_sequences", sequence_ok, "all run-local event sequences are contiguous")
    buy_events = [
        event for result in results for event in result.events
        if event["event_type"] == "order_filled" and event.get("side") == "buy"
    ]
    sell_events = [
        event for result in results for event in result.events
        if event["event_type"] == "order_filled" and event.get("side") == "sell"
    ]
    record(
        "fill_trade_reconciliation",
        len(buy_events) == len(sell_events) == len(all_trades),
        f"buys={len(buy_events)}, sells={len(sell_events)}, trades={len(all_trades)}",
    )
    aggregate_limit = float(config["risk"]["max_aggregate_open_risk_pct"])
    aggregate_ok = all(
        float(event["aggregate_open_risk_after"])
        <= float(event["equity_at_entry"]) * aggregate_limit + 1e-8
        for event in buy_events
    )
    record(
        "aggregate_entry_risk", aggregate_ok,
        f"checked {len(buy_events)} accepted entries against configured {aggregate_limit:.4%} limit",
    )
    cash_marks = [
        float(event["cash"]) for result in results for event in result.events
        if event["event_type"] == "pnl_mark"
    ]
    record("cash_only", all(cash >= -1e-8 for cash in cash_marks), f"minimum cash ${min(cash_marks):.8f}")
    terminal_replay_ok = True
    terminal_details: list[str] = []
    for result in results:
        open_symbols: set[str] = set()
        replay_ok = True
        for event in result.events:
            if event["event_type"] != "position_changed":
                continue
            symbol = str(event["symbol"])
            if event["state"] == "opened":
                if symbol in open_symbols:
                    replay_ok = False
                open_symbols.add(symbol)
            elif event["state"] == "closed":
                if symbol not in open_symbols:
                    replay_ok = False
                open_symbols.discard(symbol)
        terminal_replay_ok = terminal_replay_ok and replay_ok and not open_symbols
        terminal_details.append(
            f"{result.split}: replay_valid={replay_ok}, remaining={sorted(open_symbols)}"
        )
    record("terminal_flat_ledger_replay", terminal_replay_ok, "; ".join(terminal_details))
    observations = []
    for result in results:
        signals = sum(event["event_type"] == "entry_signal" for event in result.events)
        attempts = sum(
            event["event_type"] == "order_filled" and event.get("side") == "buy"
            or event["event_type"] == "order_rejected" and "client_order_id" in event
            for event in result.events
        )
        zero_quantity = sum(
            event["event_type"] == "order_rejected" and event.get("reason") == "zero_quantity"
            for event in result.events
        )
        daily_halts = sum(
            event["event_type"] == "order_rejected" and event.get("reason") == "daily_loss_halt"
            for event in result.events
        )
        observations.append(
            {
                "split": result.split,
                "entry_signals": signals,
                "entry_attempts": attempts,
                "zero_quantity_rejections": zero_quantity,
                "zero_quantity_pct_of_attempts": round(zero_quantity / attempts * 100, 8)
                if attempts else 0.0,
                "daily_loss_halt_rejections": daily_halts,
            }
        )
    report = {
        "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "checks": checks,
        "observations": observations,
    }
    (output_dir / "validation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if report["status"] != "PASS":
        raise AssertionError("result validation failed; see validation_report.json")
    return report
