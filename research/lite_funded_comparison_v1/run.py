"""Offline, price-only, separately funded LITE comparison. No broker or network."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, ROUND_DOWN
import hashlib
import json
from pathlib import Path

from research.lite_execution_data.study import load_bars

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research/lite_execution_data/runs/sip-bars-01"
SNAPSHOT = ROOT / "research/lite_2026/snapshot.json"
ARMS = ("dip_10", "dip_15", "dip_30", "rebound_30", "late_1500")
D = lambda value: Decimal(str(value))


def inputs():
    manifest = json.loads((DATA / "manifest.json").read_text())
    hashes = {item["file"]: item["sha256"] for item in manifest["files"]}
    cfg = json.loads((ROOT / "research/lite_reversal_v1/config.json").read_text())
    if hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() != cfg["snapshot_sha256"]:
        raise ValueError("Calendar snapshot hash mismatch")
    calendar = json.loads(SNAPSHOT.read_text())["calendar"]
    loaded = {}
    for symbol in ("LITE", "SPY"):
        path = DATA / f"{symbol}_5Min.json"
        if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[path.name]:
            raise ValueError(f"{symbol} bar hash mismatch")
        loaded[symbol], coverage = load_bars(path, symbol, 5, calendar)
        if coverage["complete_sessions"] != 170:
            raise ValueError(f"{symbol} session coverage changed")
    if set(loaded["LITE"]) != set(loaded["SPY"]):
        raise ValueError("Control and candidate dates differ")
    return loaded, hashes


def signal(arm, bars):
    """Return a next-bar index, based only on bars completed before that index."""
    if arm not in ARMS:
        raise ValueError("Unknown arm")
    if arm == "late_1500":
        return 66 if D(bars[65].c) <= D(bars[0].o) * D("0.98") else None
    window = {"dip_10": 2, "dip_15": 3, "dip_30": 6,
              "rebound_30": 6}[arm]
    observed = bars[:window]
    opening = D(bars[0].o)
    if min(D(b.l) for b in observed) > opening * D("0.99"):
        return None
    if D(observed[-1].c) >= opening:
        return None
    if arm == "rebound_30" and not (
        D(observed[-3].c) < D(observed[-2].c) < D(observed[-1].c)
    ):
        return None
    return window


def quantity(cash, price, cost):
    """Four-decimal fractional proxy with all-in debit at most $1,000."""
    budget = min(cash, D("1000"))
    return (budget / (D(price) * (1 + D(cost)))).quantize(D("0.0001"), rounding=ROUND_DOWN)


def simulate(days, arm, cost_bps=10, deadline=10, target_pct=3):
    if arm not in ARMS or cost_bps not in (10, 25) or deadline < 1:
        raise ValueError("Invalid research scenario")
    cost = D(cost_bps) / D(10000)
    cash = D("4000")
    position = None
    pending_exit = None
    closed = []
    daily = []
    counts = Counter()
    ordered = sorted(days)
    for day_number, day in enumerate(ordered):
        bars = days[day]
        entry_index = signal(arm, bars)
        if entry_index is not None:
            counts["candidate_days"] += 1
        exited_today = False
        for index, bar in enumerate(bars):
            if pending_exit and position:
                price = D(bar.o) * (1 - cost)
                proceeds = position["qty"] * price
                cash += proceeds
                closed.append({"entry_date": position["entry_date"], "exit_date": day,
                               "entry_bar_index": position["entry_bar_index"],
                               "exit_bar_index": index,
                               "entry_price": str(position["price"]),
                               "exit_price": str(price), "quantity": str(position["qty"]),
                               "pnl": str(proceeds - position["debit"]),
                               "exit_reason": pending_exit,
                               "max_adverse_pct": float(position["max_adverse_pct"]),
                               "max_favorable_pct": float(position["max_favorable_pct"])})
                position = None
                pending_exit = None
                exited_today = True
            if index == entry_index:
                if position or exited_today:
                    counts["skipped_occupied"] += 1
                else:
                    price = D(bar.o) * (1 + cost)
                    qty = quantity(cash, bar.o, cost)
                    if qty <= 0:
                        counts["skipped_cash"] += 1
                    else:
                        debit = qty * price
                        if debit > D("1000") or debit > cash:
                            raise AssertionError("Cash cap breached")
                        cash -= debit
                        position = {"entry_date": day, "entry_day_number": day_number,
                                    "entry_bar_index": index,
                                    "price": price, "qty": qty, "debit": debit,
                                    "max_adverse_pct": D(0), "max_favorable_pct": D(0)}
                        counts["entries"] += 1
            if position:
                reference = position["price"]
                adverse = (D(bar.l) * (1 - cost) / reference - 1) * 100
                favorable = (D(bar.h) * (1 - cost) / reference - 1) * 100
                position["max_adverse_pct"] = min(position["max_adverse_pct"], adverse)
                position["max_favorable_pct"] = max(position["max_favorable_pct"], favorable)
                if not pending_exit and D(bar.c) * (1 - cost) >= reference * (1 + D(target_pct) / 100):
                    pending_exit = "target_close_then_next_open"
                if not pending_exit and index == len(bars) - 1 and day_number - position["entry_day_number"] + 1 >= deadline:
                    pending_exit = "deadline_next_session_open"
        mark = position["qty"] * D(bars[-1].c) * (1 - cost) if position else D(0)
        daily.append({"date": day, "equity": float(cash + mark), "cash": float(cash),
                      "holding": bool(position)})
    peak = D("4000")
    worst_drawdown = D(0)
    for row in daily:
        equity = D(row["equity"])
        peak = max(peak, equity)
        worst_drawdown = min(worst_drawdown, (equity / peak - 1) * 100)
    ending_equity = D(daily[-1]["equity"])
    return {"arm": arm, "cost_bps_per_side": cost_bps, "deadline_sessions": deadline,
            "target_pct": target_pct, "candidate_days": counts["candidate_days"],
            "skipped_occupied": counts["skipped_occupied"], "skipped_cash": counts["skipped_cash"],
            "entries": counts["entries"], "closed_trades": len(closed),
            "unresolved_positions": int(position is not None),
            "ending_marked_equity": float(ending_equity),
            "net_marked_pnl": float(ending_equity - D("4000")),
            "worst_daily_drawdown_pct": float(worst_drawdown),
            "worst_closed_trade_adverse_pct": min((t["max_adverse_pct"] for t in closed), default=None),
            "unresolved": ({"entry_date": position["entry_date"],
                            "entry_bar_index": position["entry_bar_index"],
                            "quantity": str(position["qty"]),
                            "entry_debit": str(position["debit"]),
                            "estimated_exit_value": str(position["qty"] * D(days[ordered[-1]][-1].c) * (1 - cost)),
                            "max_adverse_pct": float(position["max_adverse_pct"]),
                            "max_favorable_pct": float(position["max_favorable_pct"])} if position else None),
            "trades": closed, "daily": daily}


def buy_hold(days, symbol, cost_bps=10):
    cost = D(cost_bps) / D(10000)
    ordered = sorted(days)
    first, last = days[ordered[0]][6], days[ordered[-1]][-1]
    qty = quantity(D("4000"), first.o, cost)
    debit = qty * D(first.o) * (1 + cost)
    marked = D("4000") - debit + qty * D(last.c) * (1 - cost)
    return {"arm": f"{symbol}_buy_hold", "entry_date": ordered[0],
            "unresolved_positions": 1, "closed_trades": 0,
            "ending_marked_equity": float(marked), "net_marked_pnl": float(marked - D("4000"))}


def run():
    loaded, hashes = inputs()
    scenarios = [simulate(loaded["LITE"], arm, cost, deadline)
                 for arm in ARMS for cost in (10, 25) for deadline in (5, 10, 20)]
    return {"status": "OFFLINE_DEVELOPMENT_NOT_LIVE_OR_PAPER_ORDER_EVIDENCE",
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "protocol_sha256": hashlib.sha256((Path(__file__).parent / "PROTOCOL.md").read_bytes()).hexdigest(),
            "source_hashes": hashes, "data_through": max(loaded["LITE"]),
            "session_count": len(loaded["LITE"]),
            "assumptions": ["All arms are independent $4,000 ledgers with one $1,000 LITE ticket.",
                            "Raw SIP five-minute opens plus fixed cost are not executable quotes.",
                            "No historical decision-time news or corporate action reconciliation.",
                            "Five/ten/twenty-session deadlines are research sensitivity, not approved exit rules."],
            "controls": [buy_hold(loaded["LITE"], "LITE"),
                         buy_hold(loaded["SPY"], "SPY"),
                         {"arm": "cash", "ending_marked_equity": 4000, "net_marked_pnl": 0}],
            "scenarios": scenarios}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output path already exists")
    result = run()
    args.output.mkdir(parents=True)
    (args.output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "sessions": result["session_count"],
                      "scenarios": len(result["scenarios"])}, indent=2))
