"""Independent recount for test #18, written separately from backtest.py (own parsing, own loops, no mirroring).

1. For 15 random QQQ days in the main window (with and without trades): trade or not, entry time and price, exit
   reason and price, compared with the backtest's QQQ long trade list.
2. The QQQ long account value re-chained from the trade list with the plan's sizing (1% risk, 100% cap, whole shares,
   0.01% slippage); it must match the backtest's final equity within 0.5%.

  PYTHONPATH=src:. .venv/bin/python -m research.fence_bar_test_v1.verify
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import random
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
EASTERN = ZoneInfo("America/New_York")


def bars_by_day():
    raw = json.loads(gzip.decompress((ROOT / "outputs/crt_sweep_data/QQQ_5min_sip_2016-01-01_2026-10-02.json.gz")
                                     .read_bytes()))
    days = {}
    for r in raw:
        t = datetime.strptime(r["t"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(EASTERN)
        minute = t.hour * 60 + t.minute
        if 570 <= minute < 960:
            days.setdefault(t.strftime("%Y-%m-%d"), []).append((minute, r["o"], r["h"], r["l"], r["c"]))
    return {d: sorted(v) for d, v in sorted(days.items())}


def check_day(all_closes, start_index, bars):
    """all_closes: every regular-session close in order; start_index: position of this day's first bar in it."""
    top, bottom = bars[0][2], bars[0][3]
    above = False
    for k in range(1, len(bars)):
        minute, o, h, l, c = bars[k]
        g = start_index + k
        if above and minute <= 655 and o > top and l <= top and c > top:
            if g >= 20 and sum(all_closes[g - 19:g + 1]) >= sum(all_closes[g - 20:g]):
                stop = (top + bottom) / 2
                goal = c + 2 * (c - stop)
                for m2, o2, h2, l2, c2 in bars[k + 1:]:
                    if l2 <= stop:
                        return {"entry_time": minute, "entry": c, "reason": "stop" if h2 < goal else "stop_same_bar", "exit": stop}
                    if h2 >= goal:
                        return {"entry_time": minute, "entry": c, "reason": "target", "exit": goal}
                return {"entry_time": minute, "entry": c, "reason": "close", "exit": bars[-1][4]}
        above = c > top
    return None


def main():
    res = json.loads((ROOT / "output/fence-bar-test-results.json").read_text())
    theirs = {t["date"]: t for t in res["trades_main_long"]["QQQ"]}
    days = bars_by_day()
    closes, starts = [], {}
    for d, bars in days.items():
        starts[d] = len(closes)
        closes.extend(b[4] for b in bars)
    window = [d for d in days if "2020-01-02" <= d]
    rng = random.Random(18)
    picks = rng.sample([d for d in window if d in theirs], 8) + rng.sample([d for d in window if d not in theirs], 7)
    report, ok = {}, True
    for d in sorted(picks):
        mine, t = check_day(closes, starts[d], days[d]), theirs.get(d)
        if mine is None or t is None:
            match = mine is None and t is None
        else:
            hh, mm = map(int, t["entry_time"].split(":"))
            match = (mine["entry_time"] == hh * 60 + mm and abs(mine["entry"] - t["entry"]) < 1e-3
                     and mine["reason"] == t["reason"] and abs(mine["exit"] - t["exit"]) < 1e-3)
        ok &= match
        report[d] = {"match": match, "independent": mine and {k: mine[k] for k in ("entry", "reason")},
                     "backtest": t and {k: t[k] for k in ("entry", "reason")}}
    equity = 100_000.0
    for t in sorted(res["trades_main_long"]["QQQ"], key=lambda x: x["date"]):
        buy, sell = t["entry"] * 1.0001, t["exit"] * 0.9999
        n = int(min(0.01 * equity / (buy - t["stop"]), equity / buy))
        equity += n * (sell - buy)
    final = res["results"]["QQQ"]["main_long"]["final_equity"]
    chain_ok = abs(equity / final - 1) <= 0.005
    ok &= chain_ok
    report["QQQ account value"] = {"match": chain_ok, "independent": round(equity), "backtest": final}
    print(json.dumps({"all_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
