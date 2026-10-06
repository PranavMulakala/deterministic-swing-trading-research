"""Test #22 intraday data (plan: output/LEVELS_SWEEPS_VOLUME_STUDY_PLAN_20261006.md): Alpaca SIP 5-minute bars (raw),
premarket and regular session, Jan 3, 2022 - Oct 2, 2026, for test #15's corrected 100 volatile stocks (chosen with
data up to Dec 31, 2021) plus the 12 AI-hardware names. Also LITE's daily bars to Oct 5 (its latest volume).
Read-only data keys; places no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.levels_volume_v1.fetch

Stored per symbol as outputs/levels_volume_data/<SYM>.json.gz =
{"date": [...], "pre": [[high, low, volume] or null per day], "bars": [[[minute, o, h, l, c, v], ...] per day]}
(regular-session bars only; the premarket 4:00-9:29 is summarized). Resumable: finished symbols are skipped.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

from research.stocks_in_play_orb_v1.data import save
from research.stocks_in_play_orb_v1.fetch import Client, minute_et, ohlcv, pool

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/levels_volume_data"
FIRST, LAST = "2022-01-03", "2026-10-02"
HINDSIGHT = ["MU", "SNDK", "WDC", "STX", "DELL", "INTC", "TER", "MRVL", "COHR", "CIEN", "HPE", "LITE"]


def groups():
    main = json.loads((ROOT / "output/dip-many-test-info-raw-price.json").read_text())["corrected_top100"]
    return main, [s for s in HINDSIGHT if s not in main]


def summarize(rows):
    days = defaultdict(lambda: {"pre": None, "bars": []})
    for r in rows:
        day, m = r["t"][:10], minute_et(r["t"])
        if m < 240 or m >= 960:
            continue
        rec = days[day]
        if m < 570:
            h, l, v = r["h"], r["l"], r["v"]
            rec["pre"] = [max(rec["pre"][0], h), min(rec["pre"][1], l), rec["pre"][2] + v] if rec["pre"] else [h, l, v]
        else:
            rec["bars"].append([m] + ohlcv(r))
    keep = sorted(d for d, rec in days.items() if rec["bars"])
    return {"date": keep, "pre": [days[d]["pre"] for d in keep], "bars": [days[d]["bars"] for d in keep]}


def main():
    client = Client()
    main_group, extra = groups()
    todo = [s for s in main_group + extra if not (OUT / f"{s}.json.gz").exists()]

    def one(sym):
        rows = client.bars([sym], "5Min", f"{FIRST}T08:00:00Z", f"{LAST}T21:00:00Z", "raw").get(sym, [])
        save(OUT / f"{sym}.json.gz", summarize(rows))

    failed = pool(client, one, todo, "levels 5-minute")
    lite = OUT / "LITE_daily_recent.json.gz"
    if not lite.exists():
        rows = client.bars(["LITE"], "1Day", "2026-07-01T00:00:00Z", "2026-10-05T23:59:00Z", "split")["LITE"]
        save(lite, {"date": [r["t"][:10] for r in rows], "bars": [ohlcv(r) for r in rows]})
    print(json.dumps({"finished": not failed, "symbols": len(main_group) + len(extra), "requests": client.requests}), flush=True)


if __name__ == "__main__":
    main()
