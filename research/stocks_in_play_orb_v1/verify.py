"""Independent recount for test #21, written separately from backtest.py / data.py / rules.py (own parsing, plain loops).

1. Selection: for 15 random days in the main window, rebuild the top 20 from the raw daily and 9:30-bar files.
2. Trades: for the same days, redo every long trade from the full-day 5-minute files (entry, exit, shares, dollars).
3. Account: re-chain the whole main-window equity path from the logged trades with fresh sizing and cost maths.
4. SPY over the same dates.

  PYTHONPATH=src:. .venv/bin/python -m research.stocks_in_play_orb_v1.verify
"""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "outputs/orb_play_data"
RESULTS = ROOT / "output/stocks-in-play-orb-test-results.json"


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


class Files:
    def __init__(self):
        self.daily, self.open5 = {}, {}

    def stock(self, sym):
        if sym not in self.daily:
            b = read(BASE / "daily" / f"{sym}.json.gz")
            self.daily[sym] = (b["date"], {d: i for i, d in enumerate(b["date"])}, b["raw"], b["split"])
        return self.daily[sym]

    def opening(self, day):
        if day not in self.open5:
            p = BASE / "open5" / f"{day}.json.gz"
            self.open5[day] = read(p) if p.exists() else {"requested": [], "bars": {}}
        return self.open5[day]


def top20(files, day):
    found = []
    today = files.opening(day)
    for sym, bar in today["bars"].items():
        dates, where, raw, split = files.stock(sym)
        k = where.get(day)
        if k is None or k < 15:
            continue
        f = raw[k][3] / split[k][3]
        ranges = []
        for j in range(k - 14, k):
            hi, lo, prev = split[j][1], split[j][2], split[j - 1][3]
            ranges.append(max(hi - lo, abs(hi - prev), abs(lo - prev)))
        atr = f * sum(ranges) / 14
        shares = sum(split[j][4] for j in range(k - 14, k)) / 14 / f
        if not (bar[0] > 5 and shares >= 1_000_000 and atr > 0.5):
            continue
        history, known = [], True
        for j in range(k - 14, k):
            o5 = files.opening(dates[j])
            if sym in o5["bars"]:
                v = o5["bars"][sym][4]
            elif sym in o5["requested"]:
                v = 0.0
            else:
                known = False
                break
            history.append(v * (raw[j][3] / split[j][3]) / f)
        if not known or sum(history) <= 0:
            continue
        rv = bar[4] / (sum(history) / 14)
        if rv >= 1.0:
            found.append((-rv, sym, atr, bar))
    found.sort(key=lambda t: (t[0], t[1]))
    return found[:20]


def long_trade(first, bars, atr):
    """Long side only (the verdict): buy stop at the first candle's high, stop 10% of ATR below the fill."""
    if not first[3] > first[0]:
        return None
    level = first[1]
    after = [b for b in bars if b[0] > 570]
    for i, (m, o, h, l, c, v) in enumerate(after):
        if h < level:
            continue
        fill = o if o >= level else level
        stop = fill - 0.1 * atr
        if l <= stop:                       # the plan: any touch of the stop on the entry bar counts as stopped out
            return fill, stop, m, m
        for m2, o2, h2, l2, c2, v2 in after[i + 1:]:
            if l2 <= stop:
                return fill, (o2 if o2 < stop else stop), m, m2
        return fill, after[-1][4], m, after[-1][0]
    return None


def dollars(fill, out, shares):
    return shares * (out * (1 - 0.0001) - fill * (1 + 0.0001)) - 2 * 0.0035 * shares


def main():
    res = json.loads(RESULTS.read_text())
    detail = read(BASE / "results_detail.json.gz")
    trades, curve = detail["main_trades"], detail["main_curve"]
    picks = detail["picks"]
    files = Files()
    report, ok = {}, True
    main_days = [d for d, _ in curve]
    rng = random.Random(21)
    sample = sorted(rng.sample([d for d in main_days if picks.get(d)], 15))
    equity_before = {}
    prev = 100_000.0
    for d, e in curve:
        equity_before[d] = prev
        prev = e
    by_day = {}
    for t in trades:
        by_day.setdefault(t["date"], []).append(t)
    sel_ok = trade_ok = True
    checked = 0
    for day in sample:
        mine = top20(files, day)
        theirs = [p[0] for p in picks[day]]
        same = [s for _, s, _, _ in mine] == theirs
        sel_ok &= same
        if not same:
            report[f"selection {day}"] = {"independent": [s for _, s, _, _ in mine], "backtest": theirs}
        bars = read(BASE / "day5" / f"{day}.json.gz")["bars"]
        expected = []
        for _, sym, atr, first in mine:
            t = long_trade(first, bars.get(sym, []), atr)
            if t is None:
                continue
            fill, out, m_in, m_out = t
            e = equity_before[day]
            shares = math.floor(min(0.01 * e / (0.1 * atr), 0.05 * e / fill))
            if shares >= 1:
                expected.append((sym, round(fill, 6), round(out, 6), shares, round(dollars(fill, out, shares), 4)))
        logged = [(t["symbol"], round(t["entry"], 6), round(t["exit"], 6), t["shares"], round(t["pnl"], 4))
                  for t in by_day.get(day, [])]
        same_trades = sorted(expected) == sorted(logged)
        trade_ok &= same_trades
        checked += len(expected)
        if not same_trades:
            report[f"trades {day}"] = {"independent": sorted(expected), "backtest": sorted(logged)}
    ok &= sel_ok and trade_ok
    report["selection_15_days"] = {"match": sel_ok, "days": sample}
    report["trades_on_those_days"] = {"match": trade_ok, "trades_checked": checked}
    equity, worst, i = 100_000.0, 0.0, 0
    for d, logged_equity in curve:
        start = equity
        for t in by_day.get(d, []):
            shares = math.floor(min(0.01 * start / (0.1 * t["atr"]), 0.05 * start / t["entry"]))
            if shares != t["shares"]:
                worst = max(worst, 1.0)                                     # a sizing difference fails the check
            equity += dollars(t["entry"], t["exit"], shares)
            i += 1
        worst = max(worst, abs(equity / logged_equity - 1))
    path_ok = worst <= 0.0005
    ok &= path_ok
    report["account_rechain"] = {"match": path_ok, "max_relative_gap_pct": round(100 * worst, 5),
                                 "independent_final": round(equity), "backtest_final": round(curve[-1][1]), "trades": i}
    spy = read(BASE / "SPY_all.json.gz")
    closes = [b[3] for d, b in zip(spy["date"], spy["bars"]) if main_days[0] <= d <= main_days[-1]]
    spy_final = 100_000 * closes[-1] / closes[0]
    spy_ok = abs(spy_final - res["main_long_cash"]["spy"]["final"]) <= 1
    ok &= spy_ok
    report["spy"] = {"match": spy_ok, "independent": round(spy_final), "backtest": res["main_long_cash"]["spy"]["final"]}
    print(json.dumps({"all_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
