"""Offline five-share LITE profit-only diagnostic; no broker or network calls."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from research.lite_funded_comparison_v1.run import D, ROOT, inputs, signal

PROTOCOL = Path(__file__).with_name("PROTOCOL.md")
ARMS = ("dip_30", "rebound_30")
STARTING_CASH = D("10000")
SHARES = D("5")
COST = D("0.001")  # 10 basis points per side, a model rather than a quote.


def simulate(days, arm):
    if arm not in ARMS or not days:
        raise ValueError("Unknown arm or empty data")
    cash = STARTING_CASH
    position = None
    closed = []
    daily = []
    counts = Counter()
    for day in sorted(days):
        bars = days[day]
        entry_index = signal(arm, bars)
        if entry_index is not None:
            counts["candidate_days"] += 1
        exited_today = False
        for index, bar in enumerate(bars):
            # A target order can become active only after the entry bar.  This
            # deliberately discards an unknowable entry-bar high/low sequence.
            if position is not None and not position["entry_bar_active"]:
                position["low"] = min(position["low"], D(bar.l))
                if D(bar.h) > position["target"]:
                    exit_price = position["target"] * (1 - COST)
                    proceeds = SHARES * exit_price
                    cash += proceeds
                    closed.append({
                        "entry_date": position["entry_date"], "exit_date": day,
                        "entry_bar_index": position["entry_bar_index"],
                        "exit_bar_index": index,
                        "entry_price_proxy": str(position["entry_price"]),
                        "target_price": str(position["target"]),
                        "exit_price_net_cost": str(exit_price),
                        "shares": str(SHARES),
                        "pnl": str(proceeds - position["debit"]),
                        "lowest_observed_price_after_entry": str(position["low"]),
                    })
                    position = None
                    exited_today = True
            if index == entry_index:
                if position is not None or exited_today:
                    counts["skipped_occupied"] += 1
                else:
                    entry_price = D(bar.o) * (1 + COST)
                    target = D(bars[0].o)
                    debit = SHARES * entry_price
                    if target * (1 - COST) <= entry_price:
                        counts["skipped_target_not_profitable"] += 1
                    elif debit > cash:
                        counts["skipped_cash"] += 1
                    else:
                        cash -= debit
                        position = {
                            "entry_date": day, "entry_bar_index": index,
                            "entry_price": entry_price, "target": target,
                            "debit": debit, "low": D(bar.o),
                            "entry_bar_active": True,
                        }
                        counts["entries"] += 1
            if position is not None and position["entry_bar_active"]:
                # Advance past the entry bar without using its later high or low.
                position["entry_bar_active"] = False
                position["low"] = min(position["low"], D(bar.c))
        mark = SHARES * D(bars[-1].c) * (1 - COST) if position else D(0)
        daily.append({"date": day, "equity": str(cash + mark),
                      "holding": position is not None})
    peak = STARTING_CASH
    worst_drawdown = D(0)
    for row in daily:
        equity = D(row["equity"])
        peak = max(peak, equity)
        worst_drawdown = min(worst_drawdown, (equity / peak - 1) * 100)
    ending_equity = D(daily[-1]["equity"])
    unresolved = None
    if position is not None:
        unresolved = {
            "entry_date": position["entry_date"],
            "entry_price_proxy": str(position["entry_price"]),
            "target_price": str(position["target"]),
            "shares": str(SHARES),
            "entry_debit": str(position["debit"]),
            "estimated_exit_value": str(SHARES * D(days[sorted(days)[-1]][-1].c) * (1 - COST)),
            "lowest_observed_price_after_entry": str(position["low"]),
        }
    return {
        "arm": arm, "first_session": min(days), "last_session": max(days),
        "session_count": len(days), "candidate_days": counts["candidate_days"],
        "skipped_occupied": counts["skipped_occupied"],
        "skipped_target_not_profitable": counts["skipped_target_not_profitable"],
        "skipped_cash": counts["skipped_cash"], "entries": counts["entries"],
        "closed_trades": len(closed), "unresolved_positions": int(unresolved is not None),
        "net_marked_pnl": str(ending_equity - STARTING_CASH),
        "worst_daily_ledger_drawdown_pct": str(worst_drawdown),
        "worst_observed_position_low_vs_entry_pct": str(min(
            ((D(t["lowest_observed_price_after_entry"]) / D(t["entry_price_proxy"]) - 1) * 100
             for t in closed + ([unresolved] if unresolved else [])), default=D(0))),
        "unresolved": unresolved, "trades": closed, "daily": daily,
    }


def run():
    loaded, hashes = inputs()
    all_days = loaded["LITE"]
    cutoff = max(all_days)
    recent_start = (date.fromisoformat(cutoff) - timedelta(days=90)).isoformat()
    recent = {day: bars for day, bars in all_days.items() if day >= recent_start}
    return {
        "status": "OFFLINE_DEVELOPMENT_NOT_PAPER_OR_LIVE_ORDER_EVIDENCE",
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "source_hashes": hashes, "data_through": cutoff,
        "recent_window_start": recent_start,
        "assumptions": "See protocol. Entry definitions lack volume/news; modeled bar prices are not fills.",
        "scenarios": [simulate(sample, arm) for sample in (all_days, recent) for arm in ARMS],
    }


if __name__ == "__main__":
    result = run()
    output = ROOT / "output/lite-profit-only-development-20260927.json"
    if output.exists():
        raise SystemExit(f"Output already exists: {output}")
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(output)
