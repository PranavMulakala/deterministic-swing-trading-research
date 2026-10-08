"""Test #28, information only (written after the main result): how much the follower result depends on the fill
assumption and on how un-exited "runners" are valued. Re-uses score.py and its cached bars.

Variants: conservative (main: high in / low out), close (minute close in and out), and close_no_runners (minute close,
and when the analyst never posts a full exit, the remainder is sold with the last posted trim instead of being held).

  PYTHONPATH=src:. .venv/bin/python -m research.owls_alerts_v1.sensitivity
"""
from __future__ import annotations

import json
import statistics

from research.owls_alerts_v1 import score as s

ENTRY_COL = {"conservative": 2, "close": 4, "close_no_runners": 4}
EXIT_COL = {"conservative": 3, "close": 4, "close_no_runners": 4}


def follower_pct(p, mode):
    exps, how = s.resolve_expiry(p)
    t0 = s.minute_after(p["ts"])
    best = None
    for exp in exps:
        occ = s.occ_symbol(p["und"], exp, p["cp"], p["strike"])
        bars = s.get_bars(occ, p["ts"][:10] + "T13:00:00Z", min(exp, s.LAST_DAY).isoformat() + "T21:00:00Z")
        e = s.bar_at_or_after(bars, t0, 5)
        if not e:
            continue
        posted = float(p["posted_entry"]) if p["posted_entry"] else None
        gap = abs(e[4] / posted - 1) if posted else 0.0
        if best is None or gap < best[3]:
            best = (exp, occ, bars, gap, e)
        if how != "inferred":
            break
    if best is None or best[3] > 0.5:
        return None
    exp, occ, bars, gap, e = best
    fill = e[ENTRY_COL[mode]]
    exits = p["exits"]
    has_x = any(x["kind"] == "X" for x in exits)
    if mode == "close_no_runners" and exits:
        has_x = True
    n = len(exits) if has_x else len(exits) + 1
    total = 0.0
    for x in exits:
        b = s.bar_at_or_after(bars, s.minute_after(x["ts"]), 30) or ([b for b in bars if b[0] >= s.minute_after(x["ts"])] or [bars[-1]])[0]
        total += b[EXIT_COL[mode]] / n
    if not has_x:
        last = [b for b in bars if b[0][:10] <= min(exp, s.LAST_DAY).isoformat()]
        total += (last[-1][4] if last else 0.0) / n
    return 100 * (total / fill - 1) if fill > 0 else None


def main():
    positions, _ = s.build_positions(s.load_events())
    positions = [p for p in positions if not p["pre_existing"] and p["strike"] and p["cp"] in ("C", "P")]
    out = {}
    for mode in ENTRY_COL:
        by = {}
        for p in positions:
            r = follower_pct(p, mode)
            if r is not None:
                by.setdefault(p["analyst"].split(":")[0], []).append(10 * r)  # $ on a $1,000 stake
        out[mode] = {a: {"alerts": len(v), "total_$": round(sum(v)), "per_alert_$": round(statistics.mean(v)),
                         "win_pct": round(100 * sum(x > 0 for x in v) / len(v))} for a, v in sorted(by.items())}
    print(json.dumps(out, indent=1))
    (s.ROOT / "output/owls-alerts-sensitivity.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
