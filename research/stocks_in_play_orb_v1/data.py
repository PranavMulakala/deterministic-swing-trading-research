"""Test #21 data access shared by the download and the backtest: file paths, the trading calendar, each stock's daily
filter numbers, and the day-by-day "in play" selection. Files are written by fetch.py (outputs/, gitignored)."""
from __future__ import annotations

from array import array
from collections import deque
import gzip
import json
from pathlib import Path

from research.stocks_in_play_orb_v1.rules import LOOKBACK, NAN, daily_metrics, in_play, relative_volume, tradeable

ROOT = Path(__file__).resolve().parents[2]


def base_dir(pilot=False):
    return ROOT / ("outputs/orb_play_pilot" if pilot else "outputs/orb_play_data")


def load(path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with gzip.open(tmp, "wt") as f:
        json.dump(obj, f)
    tmp.replace(path)


def calendar(base):
    return load(base / "SPY_all.json.gz")["date"]


def metric_table(base, symbols, cal):
    """{symbol: (calendar positions, avg volume, ATR, split factor, raw daily open)} as compact arrays, one entry per
    day the stock traded (filter numbers from the previous 14 days, in that day's units)."""
    pos = {d: i for i, d in enumerate(cal)}
    table = {}
    for s in symbols:
        p = base / "daily" / f"{s}.json.gz"
        if not p.exists():
            continue
        b = load(p)
        m = daily_metrics(b["raw"], b["split"])
        keep = [k for k, d in enumerate(b["date"]) if d in pos]
        table[s] = (array("H", [pos[b["date"][k]] for k in keep]), array("d", [m[k][0] for k in keep]),
                    array("d", [m[k][1] for k in keep]), array("d", [m[k][2] for k in keep]),
                    array("d", [b["raw"][k][0] for k in keep]))
    return table


def need_by_day(table, cal, first_day, min_price):
    """[set of symbols per calendar day]: every stock passing the daily filters (opening price > min_price, from the
    daily bar) on a day >= first_day, plus its previous 14 trading days (relative volume's history)."""
    need = [set() for _ in cal]
    for s, (gi, vol, atr, _, opn) in table.items():
        last = -1
        for k in range(len(gi)):
            if cal[gi[k]] >= first_day and tradeable(opn[k], vol[k], atr[k], min_price):
                for j in range(max(last + 1, k - LOOKBACK), k + 1):
                    need[gi[j]].add(s)
                last = k
    return need


def selections(base, table, cal, n, first_day):
    """{day: [(symbol, relative volume, avg volume, ATR, first 5-minute bar [o, h, l, c, v])]}: the n stocks in play,
    best first, from first_day on. A stock's opening volume on a day it was fetched but had no 9:30 bar counts as 0;
    a day it wasn't fetched is unknown, and an unknown in the 14-day history means no relative volume that day."""
    hist = {s: deque(maxlen=LOOKBACK) for s in table}
    ptr = dict.fromkeys(table, 0)
    out = {}
    for g, day in enumerate(cal):
        p = base / "open5" / f"{day}.json.gz"
        f5 = load(p) if p.exists() else {"requested": [], "bars": {}}
        requested, bars, cands = set(f5["requested"]), f5["bars"], {}
        for s, (gi, vol, atr, fac, _) in table.items():
            k = ptr[s]
            if k >= len(gi) or gi[k] != g:
                continue
            ptr[s] = k + 1
            bar = bars.get(s)
            v = bar[4] if bar else (0.0 if s in requested else NAN)
            if bar and day >= first_day and tradeable(bar[0], vol[k], atr[k]):
                rv = relative_volume(v, [x * fj / fac[k] for x, fj in hist[s]])
                if rv == rv:
                    cands[s] = (rv, vol[k], atr[k], bar)
            hist[s].append((v, fac[k]))
        if day >= first_day:
            out[day] = [(s,) + cands[s] for s in in_play([(s, c[0]) for s, c in cands.items()], n)]
    return out
