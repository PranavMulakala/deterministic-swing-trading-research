"""Test #21 1-minute re-check data (plan section "1-minute re-check", declared before this download): Alpaca SIP
1-minute bars (raw), 9:35-16:00, for each day's top-20 picks from the 5-minute run
(outputs/orb_play_data/results_detail.json.gz). Read-only data keys; places no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.stocks_in_play_orb_v1.fetch1m

One request per day, stored as outputs/orb_play_data/day1/<date>.json.gz =
{"symbols": [...], "bars": {symbol: [[minute_of_day_ET, o, h, l, c, v], ...]}}. Resumable and top-up safe like fetch.py.
"""
from __future__ import annotations

import json

from research.stocks_in_play_orb_v1.data import base_dir, load, save
from research.stocks_in_play_orb_v1.fetch import Client, minute_et, ohlcv, pool, utc


def main():
    base, client = base_dir(), Client()
    picks = load(base / "results_detail.json.gz")["picks"]

    def have(day):
        path = base / "day1" / f"{day}.json.gz"
        return set(load(path)["symbols"]) if path.exists() else set()

    def one(day):
        path = base / "day1" / f"{day}.json.gz"
        old = load(path) if path.exists() else {"symbols": [], "bars": {}}
        syms, out = [p[0] for p in picks[day] if p[0] not in old["symbols"]], dict(old["bars"])
        for s, rows in client.bars(syms, "1Min", utc(day, 575), utc(day, 959), "raw").items():
            out[s] = [[minute_et(r["t"])] + ohlcv(r) for r in rows if 575 <= minute_et(r["t"]) < 960]
        save(path, {"symbols": sorted(set(old["symbols"]) | set(syms)), "bars": out})

    days = [d for d, rows in sorted(picks.items()) if rows and {p[0] for p in rows} - have(d)]
    failed = pool(client, one, days, "1-minute")
    print(json.dumps({"finished": not failed, "days": len(days), "requests": client.requests}), flush=True)


if __name__ == "__main__":
    main()
