"""Independent recount for test #16, written separately from backtest.py (own parsing, own loops).

For 10 random qualifying events: recompute gap, volumes, the earnings window, the opening-range breakout, fill, stop,
same-bar flag and every exit from the raw files, and compare with the backtest's event record. For 10 random rejected
candidate days: confirm they don't qualify.

  PYTHONPATH=src:. .venv/bin/python -m research.ep_test_v1.verify
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import gzip
import io
import json
import random
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DAILY = ROOT / "outputs/breakout_data"
EP = ROOT / "outputs/ep_data"
ET = ZoneInfo("America/New_York")
C = 0.001


def read_daily(sym, end):
    text = gzip.decompress((DAILY / f"{sym}.csv.gz").read_bytes()).decode()
    rows = [r for r in csv.DictReader(io.StringIO(text)) if r["date"] <= end]
    return [(r["date"], float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["volume"]))
            for r in rows]


def read_bars(sym, day):
    with gzip.open(EP / "intraday" / f"{day}.json.gz", "rt") as f:
        return json.load(f).get(sym) or []


def to_et(stamp):
    return datetime.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(ET)


def recount(sym, day, filings, end):
    rows = read_daily(sym, end)
    n = [r[0] for r in rows].index(day)
    prev = rows[n - 1]
    window = rows[n - 20:n]
    avg_vol = sum(r[5] for r in window) / 20
    avg_usd = sum(r[4] * r[5] for r in window) / 20
    avg_rng = sum((rows[m][2] - rows[m][3]) / rows[m - 1][4] for m in range(n - 20, n)) / 20
    if avg_usd < 20e6 or rows[n][1] < 1.10 * prev[4]:
        return {"qualifies": False, "why": "liquidity/gap"}
    start = datetime(*map(int, prev[0].split("-")), 16, 0, tzinfo=ET)
    stop_t = datetime(*map(int, day.split("-")), 10, 30, tzinfo=ET)
    if not any(start <= to_et(f[0]) < stop_t for f in filings):
        return {"qualifies": False, "why": "earnings"}
    bars = read_bars(sym, day)
    if bars and bars[0][0] < 600 and abs(bars[0][1] / rows[n][1] - 1) > 0.05:
        return {"qualifies": False, "why": "scale"}
    if not [x for x in bars if x[0] < 630]:
        return {"qualifies": False, "why": "intraday"}
    if sum(x[5] for x in bars if 570 <= x[0] < 600) < avg_vol:
        return {"qualifies": False, "why": "volume"}
    top = max(x[2] for x in bars if x[0] < 630)
    pick = None
    for idx in range(len(bars)):
        if 630 <= bars[idx][0] <= 955 and bars[idx][2] > top:
            pick = idx
            break
    if pick is None:
        return {"qualifies": False, "why": "breakout"}
    buy = max(top, bars[pick][1]) * (1 + C)
    floor = min(x[3] for x in bars[:pick])
    amb = bars[pick][3] <= floor
    if (buy - floor) / buy > avg_rng:
        return {"qualifies": False, "why": "range"}
    out = {"qualifies": True, "minute": bars[pick][0], "fill": buy, "stop": floor, "ambiguous": amb, "parts": []}
    if amb:
        out["parts"] = [[day, floor * (1 - C), 1.0, "stop_entry_bar"]]
        return out
    for x in bars[pick + 1:]:
        if x[1] <= floor or x[3] <= floor:
            out["parts"] = [[day, (x[1] if x[1] <= floor else floor) * (1 - C), 1.0, "stop_entry_day"]]
            return out
    remaining, half_done = 1.0, False
    for m in range(n + 1, len(rows)):
        d, o, h, lo, c, v = rows[m]
        if o <= floor:
            out["parts"].append([d, o * (1 - C), remaining, "stop_open"])
            return out
        if lo <= floor:
            out["parts"].append([d, floor * (1 - C), remaining, "stop"])
            return out
        if m == n + 3 and not half_done:
            out["parts"].append([d, c * (1 - C), remaining / 2, "half_day3"])
            remaining, half_done, floor = remaining / 2, True, max(floor, buy)
        if c < sum(r[4] for r in rows[m - 9:m + 1]) / 10:
            out["parts"].append([d, c * (1 - C), remaining, "trail"])
            return out
    out["parts"].append([rows[-1][0], rows[-1][4], remaining, "open_end"])
    return out


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main():
    res = json.loads((ROOT / "output/ep-test-results.json").read_text())
    edgar = json.loads((EP / "edgar_item_202.json").read_text())["rows"]
    end = res["last"]
    rng = random.Random(16)
    events = rng.sample(res["events_main"], min(10, len(res["events_main"])))
    report, ok_all = {}, True
    for e in events:
        mine = recount(e["symbol"], e["day"], edgar.get(e["symbol"], []), end)
        match = (mine["qualifies"] and mine["minute"] == e["minute"] and close(mine["fill"], e["fill"], 1e-4)
                 and close(mine["stop"], e["stop"], 1e-4) and mine["ambiguous"] == e["ambiguous"]
                 and len(mine["parts"]) == len(e["parts"])
                 and all(p[0] == q[0] and p[3] == q[3] and close(p[1], q[1], 1e-4) and close(p[2], q[2])
                         for p, q in zip(mine["parts"], e["parts"])))
        ok_all &= match
        report[f'{e["symbol"]} {e["day"]}'] = {"match": match, "kinds": [p[3] for p in mine["parts"]]}
    rejected = rng.sample(res["rejected_sample"], min(10, len(res["rejected_sample"])))
    for sym, day, why in rejected:
        try:
            mine = recount(sym, day, edgar.get(sym, []), end)
            match = not mine["qualifies"]
        except (ValueError, IndexError):
            mine, match = {"why": "no daily bar / warmup"}, why in ("no_daily_bar", "warmup")
        ok_all &= match
        report[f"{sym} {day} (rejected: {why})"] = {"match": match, "independent_reason": mine.get("why")}
    print(json.dumps({"all_match": ok_all, **report}, indent=1))


if __name__ == "__main__":
    main()
