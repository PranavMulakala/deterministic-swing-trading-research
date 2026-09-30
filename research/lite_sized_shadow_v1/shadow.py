"""Shadow ledger for "bigger dip, bigger buy" (version 3 of output/LITE_DYNAMIC_TEST_RESULTS_20260930.md).

  PYTHONPATH=src:. .venv/bin/python -m research.lite_sized_shadow_v1.shadow events.jsonl [--mark 965.20]

Reads the LITE paper bot's own events.jsonl and re-sizes each real paper trade by that morning's dip:
$40,000 for a 1-2% dip, $60,000 for 2-3%, $80,000 for 3% or more. Entries, fill prices and sale prices are the
paper bot's actual ones, so the only difference from the running bot is the share count. Places no orders,
reads no keys, and never changes the running bot. --mark values an open position at that price.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import json
import sys

from research.lite_dynamic_test_v1.run import ticket_for

D = lambda value: Decimal(str(value))


def ledger(events, mark=None):
    """events: the bot's event dicts in order. Returns per-trade rows and totals for the bot and the shadow."""
    rows, dip, held = [], None, None
    for event in events:
        kind = event.get("type")
        if kind == "SIGNAL":
            dip = D(event["dip_pct"])
        elif kind == "FILLED_AND_TARGET_PLACED" and dip is not None:
            fill = D(event["avg_fill"])
            ticket = ticket_for(dip, "tiered")
            held = {"entry": event["at"][:10], "dip_pct": str(dip), "fill": str(fill), "target": event["target"],
                    "bot_shares": int(D(event["qty"])), "shadow_ticket": int(ticket), "shadow_shares": int(ticket / fill)}
            rows.append(held)
            dip = None
        elif kind == "SOLD_AT_TARGET" and held is not None:
            gain = D(event["exit_price"]) - D(held["fill"])
            held.update({"exit": event["exit_price"], "exit_at": (event.get("exit_at") or event["at"])[:10],
                         "bot_pnl": str(gain * held["bot_shares"]), "shadow_pnl": str(gain * held["shadow_shares"])})
            held = None
    if held is not None and mark is not None:
        gain = D(mark) - D(held["fill"])
        held.update({"marked_at": str(mark), "bot_open_pnl": str(gain * held["bot_shares"]),
                     "shadow_open_pnl": str(gain * held["shadow_shares"])})
    total = lambda key: str(sum((D(r[key]) for r in rows if key in r), Decimal(0)))
    return {"trades": rows, "sales": sum("exit" in r for r in rows),
            "bot_realized": total("bot_pnl"), "shadow_realized": total("shadow_pnl"),
            "bot_open": total("bot_open_pnl"), "shadow_open": total("shadow_open_pnl")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", help="path to the bot's events.jsonl, or - for stdin")
    parser.add_argument("--mark", help="LITE price to value an open position at")
    args = parser.parse_args()
    lines = sys.stdin if args.events == "-" else open(args.events)
    print(json.dumps(ledger([json.loads(line) for line in lines if line.strip()], args.mark), indent=1))


if __name__ == "__main__":
    main()
