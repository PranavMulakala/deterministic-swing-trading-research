"""Daily forward tracker for OWLS analysts AB, TT and Eli (owner request Oct 8, 2026; follows test #28's rules).
Each trading day the day's alerts are read from the owner's all-alerts feed in the Claude browser pane and written to
outputs/owls_alerts/forward/events_YYYY-MM-DD.csv (private, gitignored). This scores every day's file with the test #28
follower rules under three fill assumptions, keeps a running dollars log, and (without --print) emails the summary.
Paper research only; no orders here (live paper copies are in copier.py).

  PYTHONPATH=src:. .venv/bin/python -m research.owls_alerts_v1.forward --print
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
from pathlib import Path

from research.owls_alerts_v1 import score as s
from research.owls_alerts_v1.sensitivity import follower_pct

FWD = s.DATA / "forward"
LOG = FWD / "forward_log.json"
TRACKED = ("ab", "tt", "eli-alerts")
MODES = ("conservative", "close", "close_no_runners")


def load_day(path):
    with open(path, newline="") as f:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    events = []
    for p in sorted(glob.glob(str(FWD / "events_*.csv"))):
        events += load_day(p)
    events = [e for e in events if e["analyst"].split(":")[0] in TRACKED]
    positions, unmatched = s.build_positions(sorted(events, key=lambda e: e["ts"]))
    rows = []
    for p in positions:
        if not p["strike"] or p["cp"] not in ("C", "P"):
            continue
        r = {"analyst": p["analyst"], "ts": p["ts"], "contract": f"{p['und']} {p['strike']}{p['cp']} {p['expiry']}",
             "posted_entry": p["posted_entry"], "exits_posted": len(p["exits"]), "closed": p["closed"]}
        for m in MODES:
            pct = follower_pct(p, m)
            r[m] = None if pct is None else round(10 * pct, 2)  # $ on $1,000
        rows.append(r)
    totals = {a: {m: round(sum(r[m] for r in rows if r["analyst"] == a and r[m] is not None), 2) for m in MODES}
              | {"alerts": sum(r["analyst"] == a for r in rows)} for a in TRACKED}
    LOG.write_text(json.dumps({"rows": rows, "totals": totals, "unmatched": unmatched}, indent=1) + "\n")
    lines = ["OWLS forward tracker (paper, $1,000 per alert, follower 1 minute late). Research only, not advice.", ""]
    for a in TRACKED:
        t = totals[a]
        lines.append(f"{a}: {t['alerts']} alerts | strict {t['conservative']:+,.0f} | mid {t['close']:+,.0f} | mid, runners sold {t['close_no_runners']:+,.0f}")
    lines.append("")
    for r in rows[-15:]:
        lines.append(f"  {r['ts'][:16]} {r['analyst']:10s} {r['contract']:24s} strict {r['conservative']} | mid {r['close']} | open={not r['closed']}")
    body = "\n".join(lines)
    if args.print:
        print(body)
        return
    from research.real_position_alert_v1.monitor import resend_key, send
    day = max(r["ts"][:10] for r in rows) if rows else "none"
    send(f"OWLS tracker through {day}: AB {totals['ab']['close']:+,.0f} | TT {totals['tt']['close']:+,.0f} | Eli {totals['eli-alerts']['close']:+,.0f} (mid fills)",
         body, resend_key(), f"owls-forward|{day}|{len(rows)}")
    print("emailed")


if __name__ == "__main__":
    main()
