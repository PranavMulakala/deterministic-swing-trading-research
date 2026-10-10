"""Independent recount for test #30 (strict VWAP-trend rule, QQQ 5-min, LONG main rule), written from the plan
(output/VWAP_TREND_TEST_PLAN_20261010.md) alone, without reading backtest.py.

Adopted judgment calls (where the plan is silent), so the comparison is apples-to-apples:
  * EMA(n) seeded with the simple average of its first n regular closes; Wilder ATR(14) seeded with the average of
    the first 14 true ranges; TR uses the previous regular close (overnight gaps count). Both run across days over
    regular bars only (bars starting 9:30..15:55 ET, half-days included under the same filter).
  * A signal bar needs >= 200 regular bars before it.
  * Stop/target from the RAW next-bar open (open -/+ 1.5/3 x ATR at the signal bar).
  * The entry bar is checked for stop/target (stop first); the gap-at-open rule applies from the next bar on.
  * One position at a time; a fresh alignment at the exit bar's close may enter on the next bar.
  * Every outside-session bar belongs to the next trading day's overnight window. pdVWAP is anchored at the previous
    trading day's 9:30 (regular bars only). The first day can't trade; a day with zero overnight volume can't trade.
  * Day-end exit at the close of the day's last regular bar.

Compares 15 random main-window days (random.Random(3030)) plus 5 random days with a trade (by this recount) against
`trades_main_long` in output/vwap-trend-test-results.json, and the whole-window trade count and sum of raw points.
Prints a JSON summary; exits 1 on any mismatch.

  PYTHONPATH=src:. .venv/bin/python -m research.vwap_trend_test_v1.verify
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path
import random
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/crt_sweep_data/QQQ_5min_sip_2016-01-01_2026-10-02.json.gz"
RESULTS = ROOT / "output/vwap-trend-test-results.json"
NY = ZoneInfo("America/New_York")
MAIN_START, MAIN_END = "2020-01-02", "2026-10-02"
OPEN_MIN, LAST_REG_MIN = 9 * 60 + 30, 15 * 60 + 55
SIG_FIRST, SIG_LAST = 9 * 60 + 45, 15 * 60
PRICE_TOL = 0.005


def load():
    """Returns (regular bars list, overnight (sum pv, sum v) per trading day)."""
    raw = json.loads(gzip.decompress(DATA.read_bytes()))
    reg, ext = [], []
    for r in raw:
        t = datetime.strptime(r["t"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(NY)
        m = t.hour * 60 + t.minute
        rec = (t.strftime("%Y-%m-%d"), m, float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"]),
               float(r["v"]), float(r["vw"]))
        (reg if OPEN_MIN <= m <= LAST_REG_MIN else ext).append(rec)
    reg.sort(key=lambda b: (b[0], b[1]))
    days = sorted({b[0] for b in reg})
    overnight = {d: [0.0, 0.0] for d in days}
    for d, m, o, h, l, c, v, vw in ext:
        # before the open -> today's (or the next trading day's) window; after 16:00 -> the next trading day's
        k = bisect_left(days, d) if m < OPEN_MIN else bisect_right(days, d)
        if k < len(days):
            overnight[days[k]][0] += vw * v
            overnight[days[k]][1] += v
    return reg, days, overnight


def ema_series(closes, n):
    out = [None] * len(closes)
    if len(closes) < n:
        return out
    a = 2.0 / (n + 1)
    e = sum(closes[:n]) / n
    out[n - 1] = e
    for i in range(n, len(closes)):
        e = a * closes[i] + (1 - a) * e
        out[i] = e
    return out


def atr_series(bars, n=14):
    out = [None] * len(bars)
    trs = [None]
    for i in range(1, len(bars)):
        h, l, pc = bars[i][3], bars[i][4], bars[i - 1][5]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(bars) <= n:
        return out
    a = sum(trs[1:n + 1]) / n
    out[n] = a
    for i in range(n + 1, len(bars)):
        a = (a * (n - 1) + trs[i]) / n
        out[i] = a
    return out


def fmt(m):
    return f"{m // 60}:{m % 60:02d}"


def recount():
    reg, days, overnight = load()
    closes = [b[5] for b in reg]
    e20, e50, e100, e200 = (ema_series(closes, n) for n in (20, 50, 100, 200))
    atr = atr_series(reg)

    # per-bar session VWAP and pdVWAP
    n = len(reg)
    svwap, pdvwap = [None] * n, [None] * n
    day_tot = {}
    i = 0
    while i < n:
        d = reg[i][0]
        j = i
        while j < n and reg[j][0] == d:
            j += 1
        day_tot[d] = (i, j)
        i = j
    prev_tot = {}  # day -> (pv, v) of the whole previous trading day
    for k, d in enumerate(days):
        s, e = day_tot[d]
        pv = vv = 0.0
        prev = prev_tot.get(d)
        for idx in range(s, e):
            b = reg[idx]
            pv += b[7] * b[6]
            vv += b[6]
            svwap[idx] = pv / vv if vv > 0 else None
            if prev is not None and prev[1] + vv > 0:
                pdvwap[idx] = (prev[0] + pv) / (prev[1] + vv)
        if k + 1 < len(days):
            prev_tot[days[k + 1]] = (pv, vv)

    def ovwap(d):
        pv, v = overnight[d]
        return pv / v if v > 0 else None

    def aligned(idx):
        if idx < 199 or e200[idx] is None:
            return False
        b = reg[idx]
        c = b[5]
        ov = ovwap(b[0])
        if svwap[idx] is None or pdvwap[idx] is None or ov is None:
            return False
        return (c > svwap[idx] and c > pdvwap[idx] and c > ov
                and c > e20[idx] > e50[idx] > e100[idx] > e200[idx])

    al = [aligned(idx) for idx in range(n)]
    trades = []
    for d in days:
        if not (MAIN_START <= d <= MAIN_END):
            continue
        s, e = day_tot[d]
        if ovwap(d) is None:
            continue
        i = s
        while i < e:
            m = reg[i][1]
            fresh = al[i] and i >= 1 and not al[i - 1]
            if not (fresh and SIG_FIRST <= m <= SIG_LAST and i >= 200 and i + 1 < e and atr[i] is not None):
                i += 1
                continue
            j = i + 1
            entry = reg[j][2]
            stop, target = entry - 1.5 * atr[i], entry + 3.0 * atr[i]
            ex = None
            for k in range(j, e):
                _, mk, o, h, l, c, _, _ = reg[k]
                if k > j:
                    if o <= stop:
                        ex = (k, o, "stop")
                        break
                    if o >= target:
                        ex = (k, o, "target")
                        break
                if l <= stop:
                    ex = (k, stop, "stop")
                    break
                if h >= target:
                    ex = (k, target, "target")
                    break
            if ex is None:
                ex = (e - 1, reg[e - 1][5], "close")
            k, px, why = ex
            trades.append({"date": d, "signal_time": fmt(m), "entry_time": fmt(reg[j][1]), "entry": entry,
                           "stop": stop, "target": target, "exit_time": fmt(reg[k][1]), "exit": px, "reason": why})
            i = k  # a fresh alignment at the exit bar's close may trigger the next entry
    return trades, [d for d in days if MAIN_START <= d <= MAIN_END]


def size_and_chain(trades, equity=100_000.0, slip=0.0001):
    for t in trades:
        fill = t["entry"] * (1 + slip)
        risk = fill - t["stop"]
        sh = math.floor(0.01 * equity / risk) if risk > 0 else 0
        sh = min(sh, math.floor(equity / fill))
        t["shares"] = sh
        equity += sh * (t["exit"] * (1 - slip) - fill)
    return equity


def same(a, b, key):
    if key in ("entry", "exit", "stop", "target"):
        return abs(float(a) - float(b)) <= PRICE_TOL
    return a == b


def main():
    mine, main_days = recount()
    final_eq = size_and_chain(mine)
    res = json.loads(RESULTS.read_text())
    theirs_all = [t for t in res["trades_main_long"] if MAIN_START <= t["date"] <= MAIN_END]
    by_day_m, by_day_t = {}, {}
    for t in mine:
        by_day_m.setdefault(t["date"], []).append(t)
    for t in theirs_all:
        by_day_t.setdefault(t["date"], []).append(t)

    rng = random.Random(3030)
    random_days = sorted(rng.sample(main_days, 15))
    trade_days = sorted(rng.sample(sorted(set(by_day_m) - set(random_days)), 5))

    keys = ["entry_time", "entry", "exit_time", "exit", "reason"]
    info_keys = ["signal_time", "stop", "target", "shares"]
    day_reports, mismatches = [], 0
    for kind, dlist in (("random", random_days), ("trade_day", trade_days)):
        for d in dlist:
            m, t = by_day_m.get(d, []), by_day_t.get(d, [])
            rep = {"date": d, "kind": kind, "my_trades": len(m), "their_trades": len(t), "ok": True, "diffs": []}
            if len(m) != len(t):
                rep["ok"] = False
                rep["diffs"].append({"field": "trade_count", "mine": len(m), "theirs": len(t)})
            for a, b in zip(m, t):
                for k in keys:
                    if not same(a[k], b[k], k):
                        rep["ok"] = False
                        rep["diffs"].append({"field": k, "entry_time": a["entry_time"], "mine": a[k], "theirs": b[k]})
                for k in info_keys:
                    if k in b and not same(a[k], b[k], k):
                        rep["diffs"].append({"field": k, "info_only": True, "entry_time": a["entry_time"],
                                             "mine": a[k], "theirs": b[k]})
            rep["trades"] = [{k: (round(x[k], 4) if isinstance(x[k], float) else x[k]) for k in
                              ["signal_time"] + keys} for x in m]
            mismatches += not rep["ok"]
            day_reports.append(rep)

    my_pts = sum(t["exit"] - t["entry"] for t in mine)
    their_pts = sum(t["exit"] - t["entry"] for t in theirs_all)
    count_ok = len(mine) == len(theirs_all)
    pts_ok = abs(my_pts - their_pts) <= max(0.01, 0.0001 * len(mine))  # file prices are rounded to 4 dp
    reasons_m, reasons_t = {}, {}
    for t in mine:
        reasons_m[t["reason"]] = reasons_m.get(t["reason"], 0) + 1
    for t in theirs_all:
        reasons_t[t["reason"]] = reasons_t.get(t["reason"], 0) + 1

    # whole-window trade-by-trade diff (information for diagnosis)
    km = {(t["date"], t["entry_time"]) for t in mine}
    kt = {(t["date"], t["entry_time"]) for t in theirs_all}
    only_m, only_t = sorted(km - kt), sorted(kt - km)

    summary = {
        "days_checked": len(day_reports),
        "days_matching": sum(r["ok"] for r in day_reports),
        "day_mismatches": mismatches,
        "trade_count": {"mine": len(mine), "theirs": len(theirs_all), "ok": count_ok},
        "sum_raw_points": {"mine": round(my_pts, 4), "theirs": round(their_pts, 4), "ok": pts_ok},
        "exit_reasons": {"mine": reasons_m, "theirs": reasons_t},
        "final_equity_info": {"mine": round(final_eq, 2),
                              "theirs": res.get("main_long", {}).get("final_equity")},
        "whole_window_entry_keys": {"only_mine": len(only_m), "only_theirs": len(only_t),
                                    "only_mine_first10": only_m[:10], "only_theirs_first10": only_t[:10]},
        "days": day_reports,
    }
    print(json.dumps(summary, indent=1, default=str))
    sys.exit(0 if (mismatches == 0 and count_ok and pts_ok) else 1)


if __name__ == "__main__":
    main()
