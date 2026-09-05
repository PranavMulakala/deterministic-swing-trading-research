from __future__ import annotations

import json
from pathlib import Path

from .models import BacktestResult


def validate_results(results: list[BacktestResult], output_dir: Path) -> dict[str, object]:
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
    aggregate_ok = all(
        float(event["aggregate_open_risk_after"])
        <= float(event["equity_at_entry"]) * 0.03 + 1e-8
        for event in buy_events
    )
    record("aggregate_entry_risk", aggregate_ok, f"checked {len(buy_events)} accepted entries")
    cash_marks = [
        float(event["cash"]) for result in results for event in result.events
        if event["event_type"] == "pnl_mark"
    ]
    record("cash_only", all(cash >= -1e-8 for cash in cash_marks), f"minimum cash ${min(cash_marks):.8f}")
    record(
        "terminal_flat",
        all(not result.exposure_curve or result.exposure_curve[-1]["open_positions"] == 0 for result in results),
        "all evaluation windows end with zero positions",
    )
    report = {
        "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "checks": checks,
    }
    (output_dir / "validation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if report["status"] != "PASS":
        raise AssertionError("result validation failed; see validation_report.json")
    return report
