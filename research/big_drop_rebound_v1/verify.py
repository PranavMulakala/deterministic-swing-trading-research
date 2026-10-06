"""Independent recount for test #19, written separately from backtest.py (own parsing, plain loops, own portfolio).

1. Every qualifying drop in the main window, recounted from the raw CSV files; the count must match.
2. For 6 random stocks with events: each event's exit day, reason and return must match.
3. The whole account re-simulated from the independently found events; final value within 0.5%.

  PYTHONPATH=src:. .venv/bin/python -m research.big_drop_rebound_v1.verify
"""
from __future__ import annotations

import csv
import gzip
import io
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
DAILY = ROOT / "outputs/breakout_data"
LO, HI = "2020-01-02", "2026-09-28"


def read(path):
    rows = list(csv.DictReader(io.StringIO(gzip.decompress(path.read_bytes()).decode())))
    return [(r["date"], float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["volume"]))
            for r in rows if r["date"] <= HI]


def find(rows):
    found = []
    for k in range(201, len(rows)):
        d, o, h, l, c, v = rows[k]
        if not (LO <= d <= HI):
            continue
        prev = rows[k - 1][4]
        if c / prev > 0.90:
            continue
        if sum(rows[j][4] * rows[j][5] for j in range(k - 60, k)) / 60 < 200e6:
            continue
        if prev <= sum(rows[j][4] for j in range(k - 200, k)) / 200:
            continue
        buy = c * 1.001
        goal, result = buy * 1.2, None
        for j in range(k + 1, min(k + 10, len(rows) - 1) + 1):
            if rows[j][1] >= goal:
                result = (rows[j][0], rows[j][1] * 0.999, "target_gap")
                break
            if rows[j][2] >= goal:
                result = (rows[j][0], goal * 0.999, "target")
                break
        if result is None:
            if k + 10 <= len(rows) - 1:
                result = (rows[k + 10][0], rows[k + 10][4] * 0.999, "time")
            else:
                result = (rows[-1][0], rows[-1][4], "open_end")
        found.append({"day": d, "drop": c / prev - 1, "buy": buy, "exit_day": result[0], "exit": result[1], "reason": result[2]})
    return found


def account(all_events, closes_by_symbol, calendar):
    cash, held, prev_value = 100_000.0, {}, 100_000.0
    todays = {}
    for s, evs in all_events.items():
        for e in evs:
            todays.setdefault(e["day"], []).append((e["drop"], s, e))
    last = {}
    for d in calendar:
        for s in [s for s, p in held.items() if p["exit_day"] == d and p["reason"] != "open_end"]:
            p = held.pop(s)
            cash += p["n"] * p["exit"]
        for _, s, e in sorted(todays.get(d, []), key=lambda t: (t[0] * 100, t[1])):
            spend = min(0.10 * prev_value, cash)
            if s in held or len(held) >= 10 or spend < 1000:
                continue
            cash -= spend
            held[s] = {**e, "n": spend / e["buy"]}
        for s in held:
            if d in closes_by_symbol[s]:
                last[s] = closes_by_symbol[s][d]
        prev_value = cash + sum(p["n"] * last.get(s, p["buy"]) for s, p in held.items())
    return prev_value


def main():
    res = json.loads((ROOT / "output/big-drop-rebound-test-results.json").read_text())
    theirs = {}
    for e in res["events_main"]:
        theirs.setdefault(e["symbol"], []).append(e)
    all_events, closes = {}, {}
    for path in sorted(DAILY.glob("*.csv.gz")):
        s = path.name[:-7]
        if s == "SPY":
            continue
        rows = read(path)
        evs = find(rows)
        if evs:
            all_events[s] = evs
            closes[s] = {r[0]: r[4] for r in rows}
    count_ok = sum(len(v) for v in all_events.values()) == len(res["events_main"])
    report, ok = {"event count": {"match": count_ok, "independent": sum(len(v) for v in all_events.values()),
                                  "backtest": len(res["events_main"])}}, count_ok
    for s in random.Random(19).sample(sorted(all_events), 6):
        mine, bt = all_events[s], sorted(theirs.get(s, []), key=lambda e: e["signal_day"])
        match = len(mine) == len(bt) and all(
            a["day"] == b["signal_day"] and a["exit_day"] == b["exit_day"] and a["reason"] == b["reason"]
            and abs(100 * (a["exit"] / a["buy"] - 1) - b["ret_pct"]) < 0.01 for a, b in zip(mine, bt))
        ok &= match
        report[s] = {"match": match, "events": len(mine)}
    spy_dates = [r[0] for r in read(DAILY / "SPY.csv.gz") if LO <= r[0] <= HI]
    final = account(all_events, closes, spy_dates)
    their_final = res["main"]["final"]
    acct_ok = abs(final / their_final - 1) <= 0.005
    ok &= acct_ok
    report["account value"] = {"match": acct_ok, "independent": round(final), "backtest": their_final}
    print(json.dumps({"all_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
