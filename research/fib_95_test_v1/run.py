"""Pre-declared test #11: Kevin's "95% Fibonacci rule" and "Faker level" (output/FIB_95_RULE_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.fib_95_test_v1.run

QQQ and SPY 5-minute bars (outputs/crt_sweep_data/) built into 9:30-aligned 1-hour candles and daily candles.
Down moves reuse the up-move code on mirrored candles (high <-> -low), so each rule is written once. Research only.
"""
from __future__ import annotations

import json
from pathlib import Path
import statistics

from research.crt_1h_test_v1.backtest import candles60
from research.crt_sweep_test_v1.backtest import load
from research.crt_sweep_test_v1.fetch import SYMBOLS, path_for
from research.provenance_v1.provenance import write_manifest

OUT = Path("output/fib-95-test-results.json")
K, HORIZON = 5, 120
MIN_MOVE = {"1h": 0.010, "daily": 0.050}
LEVELS_95 = (0.80, 0.85, 0.887, 0.90, 0.95)
LEVELS_FAKER = (0.70, 0.764, 0.80)
SNAP, INVALID = 0.618, 0.887


def build(days, tf):
    out = []
    for date, day in days.items():
        if tf == "daily":
            out.append({"d": date, "o": day[0]["o"], "h": max(b["h"] for b in day), "l": min(b["l"] for b in day),
                        "c": day[-1]["c"]})
        else:
            for k, c in sorted(candles60(day).items()):
                out.append({"d": f"{date} {c['start'] // 60}:{c['start'] % 60:02d}", "o": c["o"], "h": c["h"],
                            "l": c["l"], "c": c["c"]})
    return out


def mirror(candles):
    return [{"d": c["d"], "o": -c["o"], "h": -c["l"], "l": -c["h"], "c": -c["c"]} for c in candles]


def pivots(c, k=K):
    highs, lows = [], []
    for i in range(k, len(c) - k):
        h, l = c[i]["h"], c[i]["l"]
        if all(h > c[j]["h"] for j in range(i - k, i)) and all(h > c[j]["h"] for j in range(i + 1, i + k + 1)):
            highs.append(i)
        if all(l < c[j]["l"] for j in range(i - k, i)) and all(l < c[j]["l"] for j in range(i + 1, i + k + 1)):
            lows.append(i)
    return highs, lows


def up_moves(c, min_move, k=K):
    """(L index, H index): for each pivot high, the lowest pivot low since the previous pivot high."""
    highs, lows = pivots(c, k)
    events = sorted([(i, "H") for i in highs] + [(i, "L") for i in lows])
    moves, pending = [], []
    for i, kind in events:
        if kind == "L":
            pending.append(i)
            continue
        if pending:
            lo = min(pending, key=lambda j: (c[j]["l"], -j))
            # size is judged against the move's starting price (|L| real, or the real high H when mirrored)
            if c[i]["h"] > c[lo]["l"] and (c[i]["h"] - c[lo]["l"]) / abs(c[lo]["l"]) >= min_move:
                moves.append((lo, i))
        pending = []
    return moves


def level(lo, hi, x):
    return hi - x * (hi - lo)


def signal_and_outcome(c, li, hi_i, x, closes=2, k=K, horizon=HORIZON):
    """Claim 1 on an up move. Returns None (no signal) or dict with outcome reversal/continuation/ambiguous/unresolved."""
    lo, hi = c[li]["l"], c[hi_i]["h"]
    lvl, start = level(lo, hi, x), hi_i + k + 1
    t = start
    streak = 0
    while t < len(c):
        if c[t]["h"] > hi:
            return None
        streak = streak + 1 if c[t]["c"] < lvl else 0
        if streak >= closes:
            break
        t += 1
    else:
        return None
    entry = c[t]["c"]
    for j in range(t + 1, min(t + 1 + horizon, len(c))):
        rev, cont = c[j]["l"] <= lo, c[j]["h"] >= hi
        if rev or cont:
            outcome = "ambiguous" if rev and cont else "reversal" if rev else "continuation"
            return {"t": t, "end": j, "outcome": outcome, "entry": entry, "lo": lo, "hi": hi}
    return {"t": t, "end": None, "outcome": "unresolved", "entry": entry, "lo": lo, "hi": hi}


def faker_outcome(c, li, hi_i, x, k=K, horizon=HORIZON):
    """Claim 2 on an up move: first close beyond x, then snap back inside 61.8% vs 2 closes beyond 88.7%."""
    lo, hi = c[li]["l"], c[hi_i]["h"]
    lvl, snap, inval, start = level(lo, hi, x), level(lo, hi, SNAP), level(lo, hi, INVALID), hi_i + k + 1
    t = start
    while t < len(c):
        if c[t]["h"] > hi:
            return None
        if c[t]["c"] < lvl:
            break
        t += 1
    else:
        return None
    streak = 1 if c[t]["c"] < inval else 0
    for j in range(t + 1, min(t + 1 + horizon, len(c))):
        if c[j]["c"] > snap:
            return "snap"
        streak = streak + 1 if c[j]["c"] < inval else 0
        if streak >= 2:
            return "invalid"
    return "unresolved"


def rate(counts, good, bad):
    n = counts.get(good, 0) + counts.get(bad, 0)
    return round(100 * counts.get(good, 0) / n, 1) if n else None


def analyse(c):
    """Both directions: up moves on real candles, down moves on mirrored candles."""
    res95 = {x: {"2": {}, "3": {}} for x in LEVELS_95}
    resF = {x: {} for x in LEVELS_FAKER}
    trades, waits = [], []
    for series in (c, mirror(c)):
        for li, hi_i in up_moves(series, MIN_MOVE_NOW[0]):
            for x in LEVELS_95:
                for n in (2, 3):
                    r = signal_and_outcome(series, li, hi_i, x, closes=n)
                    if r is None:
                        continue
                    bucket = res95[x][str(n)]
                    bucket[r["outcome"]] = bucket.get(r["outcome"], 0) + 1
                    if x == 0.887 and n == 2 and r["outcome"] != "unresolved":
                        waits.append(r["end"] - r["t"])
                        e = abs(r["entry"])
                        if r["outcome"] == "reversal":
                            trades.append(abs(r["entry"] - r["lo"]) / e * 100)
                        else:
                            trades.append(-abs(r["hi"] - r["entry"]) / e * 100)
            for x in LEVELS_FAKER:
                f = faker_outcome(series, li, hi_i, x)
                if f is not None:
                    resF[x][f] = resF[x].get(f, 0) + 1
    out = {"claim1": {}, "claim2": {}}
    for x in LEVELS_95:
        out["claim1"][str(x)] = {n: {**res95[x][n], "reversal_rate_pct": rate(res95[x][n], "reversal", "continuation")}
                                 for n in ("2", "3")}
    for x in LEVELS_FAKER:
        out["claim2"][str(x)] = {**resF[x], "snap_rate_pct": rate(resF[x], "snap", "invalid")}
    out["median_candles_to_resolve_887"] = statistics.median(waits) if waits else None
    out["info_trade_887"] = {"trades": len(trades), "win_pct": round(100 * sum(t > 0 for t in trades) / len(trades), 1)
                             if trades else None, "avg_pct_per_trade_before_costs": round(statistics.mean(trades), 3)
                             if trades else None}
    return out


MIN_MOVE_NOW = [0.0]


def main():
    out = {"plan": "output/FIB_95_RULE_TEST_PLAN_20261005.md", "combos": {}}
    for symbol in SYMBOLS:
        days = load(symbol)
        for tf in ("1h", "daily"):
            MIN_MOVE_NOW[0] = MIN_MOVE[tf]
            c = build(days, tf)
            out["combos"][f"{symbol}_{tf}"] = {"candles": len(c), **analyse(c)}
    counted = {}
    for name, r in out["combos"].items():
        b = r["claim1"]["0.887"]["2"]
        resolved = b.get("reversal", 0) + b.get("continuation", 0)
        if resolved >= 30:
            counted[name] = r
    gaps_b, gaps_c, a_ok = [], [], []
    for name, r in counted.items():
        c1 = {x: r["claim1"][x]["2"]["reversal_rate_pct"] for x in r["claim1"]}
        line = c1["0.85"] + (c1["0.9"] - c1["0.85"]) * (0.887 - 0.85) / 0.05
        gaps_b.append(c1["0.887"] - line)
        a_ok.append(c1["0.887"] >= 90.0)
        c2 = {x: r["claim2"][x]["snap_rate_pct"] for x in r["claim2"]}
        if None not in c2.values():
            line2 = c2["0.7"] + (c2["0.8"] - c2["0.7"]) * (0.764 - 0.70) / 0.10
            gaps_c.append(c2["0.764"] - line2)
        r["vs_placebo_line_pts"] = {"claim1_887": round(c1["0.887"] - line, 2),
                                    "claim2_764": round(c2["0.764"] - line2, 2) if gaps_c else None}
    out["counted_combos"] = list(counted)
    out["verdict"] = {"A_rate_at_least_90_everywhere": all(a_ok) and bool(a_ok),
                      "B_887_beats_placebo_line_by_2pts": bool(gaps_b) and statistics.mean(gaps_b) >= 2.0,
                      "B_avg_gap_pts": round(statistics.mean(gaps_b), 2) if gaps_b else None,
                      "C_764_beats_placebo_line_by_2pts": bool(gaps_c) and statistics.mean(gaps_c) >= 2.0,
                      "C_avg_gap_pts": round(statistics.mean(gaps_c), 2) if gaps_c else None}
    v = out["verdict"]
    out["verdict"]["supported"] = v["A_rate_at_least_90_everywhere"] and v["B_887_beats_placebo_line_by_2pts"] and \
        v["C_764_beats_placebo_line_by_2pts"]
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    write_manifest(OUT, code=["research/fib_95_test_v1/run.py", "research/crt_1h_test_v1/backtest.py"],
                   data=[str(path_for(s)) for s in SYMBOLS], params={"k": K, "horizon": HORIZON, "min_move": MIN_MOVE})
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
