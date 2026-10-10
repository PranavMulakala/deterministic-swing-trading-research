"""Backtest of pre-declared test #30, the strict VWAP-trend rule on QQQ 5-minute bars
(output/VWAP_TREND_TEST_PLAN_20261010.md).

  PYTHONPATH=src:. .venv/bin/python -m research.vwap_trend_test_v1.backtest          # full test
  PYTHONPATH=src:. .venv/bin/python -m research.vwap_trend_test_v1.backtest --pilot  # pilot only (no returns)

Long rule: at a regular-session bar's close, close > session VWAP, > pdVWAP (anchored at the previous trading day's
9:30) and > overnight VWAP (extended-hours bars from the previous trading day's 16:00 to today's 9:25 bar), and
close > EMA20 > EMA50 > EMA100 > EMA200; the trigger is a FRESH alignment (not all true at the previous bar's close)
on a signal bar starting 9:45-15:00 ET; entry at the next bar's open; stop entry - 1.5 x ATR(14), target entry +
3 x ATR(14); gaps fill at the open, a bar touching both is a stop, otherwise out at the day's last (15:55) close.
One position at a time. Shorts are the exact mirror (prices and indicators negated; ATR unchanged).
Sizing, costs and slippage helpers are test #8's (research/crt_sweep_test_v1/backtest.py). Research only; no orders.
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date as Date, datetime
import gzip
import json
import math
from pathlib import Path
import random
import statistics
from zoneinfo import ZoneInfo

from research.crt_sweep_test_v1.backtest import MAX_WEIGHT, RISK, SLIP, START_EQUITY, down, drawdown, up
from research.crt_sweep_test_v1.fetch import path_for
from research.provenance_v1.provenance import write_manifest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/vwap-trend-test-results.json"
PLAN = "output/VWAP_TREND_TEST_PLAN_20261010.md"
NY = ZoneInfo("America/New_York")

OPEN_MIN, LAST_BAR_MIN = 570, 955                      # regular session = bars starting 9:30 .. 15:55 ET
SIGNAL_FIRST, SIGNAL_LAST = 585, 900                   # signal bars starting 9:45 .. 15:00
RANDOM_FIRST, RANDOM_LAST = 590, 905                   # placebo entry bars starting 9:50 .. 15:05
EMA_LENS, ATR_N, WARMUP = (20, 50, 100, 200), 14, 200
STOP_ATR, TARGET_ATR = 1.5, 3.0
MNQ_USD_PER_QQQ_POINT = 2 * 41                         # approximate: 1 MNQ = $2 x NDX, NDX ~ 41 x QQQ
PLACEBO_SEED, PLACEBO_REPEATS = 30, 20
GOOD_WEEK_USD = 1000.0

MAIN, STRESS = ("2020-01-02", "2026-10-02"), ("2016-01-04", "2026-10-02")
HALVES = {"main": (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2026", "2023-01-01", "2026-12-31")),
          "stress": (("2016-2020", "2016-01-01", "2020-12-31"), ("2021-2026", "2021-01-01", "2026-12-31"))}
BAD_YEARS = {"main": ("2022",), "stress": ("2018", "2022")}


# ----------------------------------------------------------------------------------------------- data + indicators
@dataclass
class Ind:
    """Regular-session bars (continuous across days) with every indicator, indexed by bar position."""
    date: list
    m: list
    o: list
    h: list
    l: list
    c: list
    ema: dict          # length -> list (None until defined)
    atr: list          # Wilder ATR(14) (None until defined)
    svwap: list        # session VWAP through this bar
    pdvwap: list       # VWAP anchored at the previous trading day's 9:30 (None on the first day)
    onvwap: list       # the day's overnight VWAP (None if no extended-hours volume)
    days: dict         # date -> (first index, one past last index)
    cond: dict = None  # side (+1 / -1) -> list of bools: all trend conditions true at this bar's close

    @property
    def dates(self):
        return list(self.days)


def load_rows(path=None):
    with gzip.open(path or path_for("QQQ"), "rt") as handle:
        return json.load(handle)


def ema_series(values, n):
    """EMA seeded with the simple average of the first n values (None before that)."""
    out, k = [None] * len(values), 2 / (n + 1)
    if len(values) < n:
        return out
    e = sum(values[:n]) / n
    out[n - 1] = e
    for i in range(n, len(values)):
        e += k * (values[i] - e)
        out[i] = e
    return out


def wilder_atr(h, l, c, n=ATR_N):
    """Wilder ATR: true range uses the previous bar's close (across days); seeded with the mean of the first n."""
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(h))]
    out = [None] * len(h)
    if len(h) < n:
        return out
    a = sum(tr[:n]) / n
    out[n - 1] = a
    for i in range(n, len(h)):
        a = (a * (n - 1) + tr[i]) / n
        out[i] = a
    return out


def prepare(rows):
    """rows: raw bars {t (UTC ISO), o, h, l, c, v, vw}, extended hours included. Returns Ind."""
    parsed = []
    for r in rows:
        t = datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(NY)
        parsed.append((t, t.date().isoformat(), t.hour * 60 + t.minute, r))
    parsed.sort(key=lambda p: p[0])
    reg = [p for p in parsed if OPEN_MIN <= p[2] <= LAST_BAR_MIN]
    ext = [p for p in parsed if not OPEN_MIN <= p[2] <= LAST_BAR_MIN]

    date, m = [p[1] for p in reg], [p[2] for p in reg]
    o, h, l, c = ([p[3][k] for p in reg] for k in ("o", "h", "l", "c"))
    days = {}
    for i, d in enumerate(date):
        a, _ = days.get(d, (i, i))
        days[d] = (a, i + 1)
    tdays = list(days)

    # overnight VWAP: each extended-hours bar belongs to the first trading day whose 9:30 comes after it
    on_pv, on_v = defaultdict(float), defaultdict(float)
    for _, d, mm, r in ext:
        if mm < OPEN_MIN and d in days:
            owner = d
        else:
            k = bisect.bisect_right(tdays, d)
            if k == len(tdays):
                continue
            owner = tdays[k]
        on_pv[owner] += r["vw"] * r["v"]
        on_v[owner] += r["v"]

    n = len(reg)
    svwap, pdvwap, onvwap = [None] * n, [None] * n, [None] * n
    prev_pv = prev_v = None
    for d in tdays:
        a, b = days[d]
        day_on = on_pv[d] / on_v[d] if on_v.get(d, 0) > 0 else None
        cpv = cv = 0.0
        for i in range(a, b):
            r = reg[i][3]
            cpv += r["vw"] * r["v"]
            cv += r["v"]
            svwap[i] = cpv / cv if cv > 0 else None
            if prev_pv is not None and prev_v + cv > 0:
                pdvwap[i] = (prev_pv + cpv) / (prev_v + cv)
            onvwap[i] = day_on
        prev_pv, prev_v = cpv, cv

    ind = Ind(date=date, m=m, o=o, h=h, l=l, c=c, ema={k: ema_series(c, k) for k in EMA_LENS},
              atr=wilder_atr(h, l, c), svwap=svwap, pdvwap=pdvwap, onvwap=onvwap, days=days)
    ind.cond = {s: conditions(ind, s) for s in (1, -1)}
    return ind


def conditions(ind, s):
    """All trend conditions at each bar's close, in signed space (s = +1 long, -1 short = negated prices)."""
    out = []
    for i in range(len(ind.c)):
        vals = (ind.svwap[i], ind.pdvwap[i], ind.onvwap[i]) + tuple(ind.ema[k][i] for k in EMA_LENS)
        if any(v is None for v in vals):
            out.append(False)
            continue
        c = s * ind.c[i]
        sv, pd, on, e20, e50, e100, e200 = (s * v for v in vals)
        out.append(c > sv and c > pd and c > on and c > e20 > e50 > e100 > e200)
    return out


def signed_bar(ind, i, s):
    if s == 1:
        return ind.o[i], ind.h[i], ind.l[i], ind.c[i]
    return -ind.o[i], -ind.l[i], -ind.h[i], -ind.c[i]


# ----------------------------------------------------------------------------------------------- rule
def walk(ind, s, e, b, atr_val, stop_mult=STOP_ATR, target_mult=TARGET_ATR, same_bar="stop"):
    """Enter at bar e's open (signed space), manage to stop/target/day end (bar b-1's close). Returns a raw trade."""
    entry = signed_bar(ind, e, s)[0]
    stop, target = entry - stop_mult * atr_val, entry + target_mult * atr_val
    for j in range(e, b):
        o, hh, ll, _ = signed_bar(ind, j, s)
        reason = px = None
        if j > e and o <= stop:
            reason, px = "stop_gap", o
        elif j > e and o >= target:
            reason, px = "target_gap", o
        else:
            hit_stop, hit_target = ll <= stop, hh >= target
            if hit_stop and hit_target:
                reason, px = ("stop_same_bar", stop) if same_bar == "stop" else ("target_same_bar", target)
            elif hit_stop:
                reason, px = "stop", stop
            elif hit_target:
                reason, px = "target", target
        if reason:
            return {"e": e, "x": j, "entry": entry, "stop": stop, "target": target, "exit": px, "reason": reason,
                    "ambiguous": reason.endswith("same_bar")}
    x = b - 1
    return {"e": e, "x": x, "entry": entry, "stop": stop, "target": target, "exit": signed_bar(ind, x, s)[3],
            "reason": "close", "ambiguous": False}


def rule_trades(ind, s, window, trigger="fresh", stop_mult=STOP_ATR, target_mult=TARGET_ATR, same_bar="stop",
                warmup=WARMUP):
    """Raw trades (signed space, bar indices) for side s on days inside `window`, one position at a time."""
    cond, trades = ind.cond[s], []
    for d, (a, b) in ind.days.items():
        if not window[0] <= d <= window[1]:
            continue
        free = a
        for i in range(a, b - 1):                       # the entry bar i + 1 must be the same day
            if i < free or i < warmup or not SIGNAL_FIRST <= ind.m[i] <= SIGNAL_LAST or not cond[i]:
                continue
            if trigger == "fresh":
                if i == 0 or cond[i - 1]:
                    continue
            elif trigger == "bounce":
                if not signed_bar(ind, i, s)[2] <= s * ind.svwap[i]:   # low touched VWAP (close above is in cond)
                    continue
            else:
                raise ValueError(trigger)
            atr_val = ind.atr[i]
            if not atr_val or atr_val <= 0:
                continue
            t = walk(ind, s, i + 1, b, atr_val, stop_mult, target_mult, same_bar)
            t.update(date=d, signal=i)
            trades.append(t)
            free = t["x"]                               # a new signal may come at the exit bar's close
    return trades


# ----------------------------------------------------------------------------------------------- account
def hhmm(m):
    return f"{m // 60}:{m % 60:02d}"


def account(raw, ind, s, window, slip=SLIP):
    """Size and chain raw trades on a $100k compounding cash account. Returns (trades, daily equity curve)."""
    sign, equity, out, curve = s, START_EQUITY, [], []
    by_date = defaultdict(list)
    for t in raw:
        assert window[0] <= t["date"] <= window[1], "raw trade outside window"
        by_date[t["date"]].append(t)
    last_exit = -1
    for d in ind.days:
        if not window[0] <= d <= window[1]:
            continue
        for t in sorted(by_date.get(d, []), key=lambda x: x["e"]):
            assert t["e"] > last_exit and t["x"] >= t["e"], "overlapping positions"
            last_exit = t["x"]
            fill, sell = up(t["entry"], slip), down(t["exit"], slip)
            risk = fill - t["stop"]
            shares = math.floor(min(RISK * equity / risk, MAX_WEIGHT * equity / abs(fill))) if risk > 0 else 0
            shares = max(shares, 0)
            pnl = shares * (sell - fill)
            alt = shares * (down(t["target"], slip) - fill) if t["ambiguous"] else pnl
            equity += pnl
            out.append({"date": d, "side": "long" if s == 1 else "short",
                        "signal_time": hhmm(ind.m[t["signal"]]), "entry_time": hhmm(ind.m[t["e"]]),
                        "exit_time": hhmm(ind.m[t["x"]]), "shares": shares, "entry": sign * t["entry"],
                        "stop": sign * t["stop"], "target": sign * t["target"], "exit": sign * t["exit"],
                        "reason": t["reason"], "pnl": pnl, "r_multiple": pnl / (shares * risk) if shares else 0.0,
                        "qqq_points": t["exit"] - t["entry"], "ambiguous": t["ambiguous"],
                        "pnl_if_target_first": alt, "unsized": shares < 1})
        curve.append((d, equity))
    assert len(out) == len(raw), f"entered {len(raw)} trades but recorded {len(out)}"
    return out, curve


# ----------------------------------------------------------------------------------------------- report
def summarize(trades, curve, window_kind, target_r=TARGET_ATR / STOP_ATR):
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gain, loss = sum(t["pnl"] for t in wins), -sum(t["pnl"] for t in losses)
    dates = [d for d, _ in curve]
    years = len(dates) / 252
    final = curve[-1][1] if curve else START_EQUITY
    daily, prev = [], START_EQUITY
    for d, e in curve:
        daily.append((d, e - prev))
        prev = e
    weeks, months, by_year = defaultdict(float), defaultdict(float), defaultdict(float)
    for d, p in daily:
        iso = Date.fromisoformat(d).isocalendar()
        weeks[f"{iso[0]}-W{iso[1]:02d}"] += p
        months[d[:7]] += p
        by_year[d[:4]] += p
    week_vals = list(weeks.values())
    worst_week = min(weeks.items(), key=lambda kv: kv[1]) if weeks else (None, 0.0)
    worst_month = min(months.items(), key=lambda kv: kv[1]) if months else (None, 0.0)

    value = dict(curve)
    halves = {}
    for name, a, b in HALVES[window_kind]:
        inside = [d for d in dates if a <= d <= b]
        if not inside:
            halves[name] = {"pnl_usd": 0.0, "return_pct": 0.0}
            continue
        before = [d for d in dates if d < inside[0]]
        start = value[before[-1]] if before else START_EQUITY
        halves[name] = {"pnl_usd": round(value[inside[-1]] - start), "return_pct": round((value[inside[-1]] / start - 1) * 100, 2)}

    reasons = Counter(t["reason"] for t in trades)
    split = {"stop": sum(v for k, v in reasons.items() if k.startswith("stop")),
             "target": sum(v for k, v in reasons.items() if k.startswith("target")), "close": reasons.get("close", 0)}
    n = len(trades)
    amb = [t for t in trades if t["ambiguous"]]
    flips = [t for t in amb if (t["pnl"] > 0) != (t["pnl_if_target_first"] > 0)]
    pts = [t["qqq_points"] for t in trades]
    mnq_by_year = defaultdict(float)
    for t in trades:
        mnq_by_year[t["date"][:4]] += MNQ_USD_PER_QQQ_POINT * t["qqq_points"]
    dd = drawdown([START_EQUITY] + [e for _, e in curve])
    pf = round(gain / loss, 3) if loss else None
    pnl_by_year = {y: round(by_year.get(y, 0.0)) for y in sorted(by_year)}

    out = {
        "trades": n, "trading_days": len(dates), "trades_per_year": round(n / years, 1) if years else None,
        "win_rate_pct": round(100 * len(wins) / max(n, 1), 1),
        "target_hit_rate_pct": round(100 * split["target"] / max(n, 1), 1),
        "break_even_target_hit_rate_pct_before_costs": round(100 / (1 + target_r), 1),
        "avg_win_usd": round(gain / max(len(wins), 1)), "avg_loss_usd": round(loss / max(len(losses), 1)),
        "avg_r_multiple": round(sum(t["r_multiple"] for t in trades) / max(n, 1), 3),
        "exit_split": split, "exit_reasons": dict(reasons), "profit_factor": pf,
        "final_equity": round(final), "total_pnl_usd": round(final - START_EQUITY),
        "total_return_pct": round((final / START_EQUITY - 1) * 100, 2), "max_drawdown_pct": round(dd * 100, 2),
        "usd_per_week_avg": round(statistics.mean(week_vals)) if week_vals else 0,
        "usd_per_week_median": round(statistics.median(week_vals)) if week_vals else 0,
        "weeks": len(week_vals),
        "weeks_at_least_1000_pct": round(100 * sum(v >= GOOD_WEEK_USD for v in week_vals) / max(len(week_vals), 1), 1),
        "worst_week": {"week": worst_week[0], "usd": round(worst_week[1])},
        "worst_month": {"month": worst_month[0], "usd": round(worst_month[1])},
        "halves": halves, "pnl_by_year": pnl_by_year,
        "same_bar_ambiguity": {"ambiguous_trades": len(amb), "ambiguity_rate": round(len(amb) / n, 4) if n else None,
                               "flips_if_target_first": len(flips),
                               "flip_rate_among_ambiguous": round(len(flips) / len(amb), 4) if amb else None,
                               "flip_rate_of_all_trades": round(len(flips) / n, 4) if n else None},
        "unsized_trades": sum(t["unsized"] for t in trades),
        "mnq_translation_approx": {
            "note": "approximate: 1 MNQ ~ $2 x Nasdaq-100 ~ $2 x 41 x QQQ points; before costs, ignores futures "
                    "commissions/slippage and the QQQ/NDX ratio drift",
            "avg_qqq_points_per_trade": round(statistics.mean(pts), 4) if pts else None,
            "median_qqq_points_per_trade": round(statistics.median(pts), 4) if pts else None,
            "avg_usd_per_trade_1_mnq": round(MNQ_USD_PER_QQQ_POINT * statistics.mean(pts), 2) if pts else None,
            "usd_per_week_avg_1_mnq": round(MNQ_USD_PER_QQQ_POINT * sum(pts) / max(len(week_vals), 1), 2),
            "usd_by_year_1_mnq": {y: round(v) for y, v in sorted(mnq_by_year.items())}},
    }
    out["checks"] = {"C1_profit_factor_at_least_1.3": (pf or 0) >= 1.3,
                     "C2_profitable_in_both_halves": all(v["pnl_usd"] > 0 for v in halves.values()),
                     "C3_worst_drop_no_worse_than_25pct": out["max_drawdown_pct"] >= -25.0,
                     "C4_profitable_in_" + "_and_".join(BAD_YEARS[window_kind]):
                         all(by_year.get(y, 0.0) > 0 for y in BAD_YEARS[window_kind])}
    out["passes"] = all(out["checks"].values())
    return out


def run(ind, s, window, window_kind, slip=SLIP, **rule):
    raw = rule_trades(ind, s, window, **rule)
    trades, curve = account(raw, ind, s, window, slip)
    target_r = rule.get("target_mult", TARGET_ATR) / rule.get("stop_mult", STOP_ATR)
    return summarize(trades, curve, window_kind, target_r), trades, raw


# ----------------------------------------------------------------------------------------------- placebo + pilot
def placebo(ind, main_trades, window=MAIN, slip=SLIP, seed=PLACEBO_SEED, repeats=PLACEBO_REPEATS, warmup=WARMUP):
    """Random long entries: per calendar year the main long's trade count, at random bar opens 9:50-15:05, same
    stop/target/exit rules, non-overlapping (one position at a time). Mean and spread over `repeats` runs."""
    need = Counter(t["date"][:4] for t in main_trades)
    eligible = defaultdict(list)
    for e in range(1, len(ind.c)):
        d = ind.date[e]
        if (window[0] <= d <= window[1] and d[:4] in need and RANDOM_FIRST <= ind.m[e] <= RANDOM_LAST
                and e - 1 >= warmup and ind.date[e - 1] == d and ind.atr[e - 1] and ind.atr[e - 1] > 0):
            eligible[d[:4]].append(e)
    rng = random.Random(seed)
    runs = []
    for _ in range(repeats):
        raw = []
        for y in sorted(need):
            cand = list(eligible[y])
            rng.shuffle(cand)
            starts, ends, got = [], [], []
            for e in cand:
                if len(got) >= need[y]:
                    break
                k = bisect.bisect_right(starts, e)
                if k > 0 and ends[k - 1] >= e:
                    continue
                d = ind.date[e]
                t = walk(ind, 1, e, ind.days[d][1], ind.atr[e - 1])
                if k < len(starts) and starts[k] <= t["x"]:
                    continue
                starts.insert(k, e)
                ends.insert(k, t["x"])
                t.update(date=d, signal=e - 1)
                got.append(t)
            raw.extend(got)
        raw.sort(key=lambda t: t["e"])
        trades, curve = account(raw, ind, 1, window, slip)
        s = summarize(trades, curve, "main")
        runs.append({k: s[k] for k in ("trades", "profit_factor", "total_pnl_usd", "final_equity", "usd_per_week_avg",
                                       "max_drawdown_pct", "win_rate_pct", "target_hit_rate_pct", "avg_r_multiple")})

    def spread(key):
        vals = [r[key] for r in runs if r[key] is not None]
        return {"mean": round(statistics.mean(vals), 3), "stdev": round(statistics.stdev(vals), 3) if len(vals) > 1 else 0.0,
                "min": min(vals), "max": max(vals)}

    return {"seed": seed, "repeats": repeats, "target_trades": sum(need.values()), "target_trades_by_year": dict(need),
            "summary": {k: spread(k) for k in runs[0]} if runs else {}, "runs": runs}


def pilot(ind, window=MAIN, warmup=WARMUP):
    """No returns: the stop distance (1.5 x ATR at the signal bar) versus the typical 5-minute bar range."""
    idx = [i for i in range(len(ind.c)) if window[0] <= ind.date[i] <= window[1]]
    ranges = [ind.h[i] - ind.l[i] for i in idx]
    med_range = statistics.median(ranges)
    sig = [i for i in idx if SIGNAL_FIRST <= ind.m[i] <= SIGNAL_LAST and i >= warmup and ind.atr[i]]
    med_range_sig = statistics.median(ind.h[i] - ind.l[i] for i in sig)
    stops = [STOP_ATR * ind.atr[i] for i in sig]
    med_stop = statistics.median(stops)
    ratios = [x / med_range for x in stops]
    dec = statistics.quantiles(ratios, n=10)
    nxt = [i for i in sig if i + 1 < len(ind.c) and ind.date[i + 1] == ind.date[i]]
    wider = sum((ind.h[i + 1] - ind.l[i + 1]) > STOP_ATR * ind.atr[i] for i in nxt) / len(nxt)
    wider_1x = sum((ind.h[i + 1] - ind.l[i + 1]) > 1.0 * ind.atr[i] for i in nxt) / len(nxt)
    return {"window": window, "regular_bars": len(idx), "signal_window_bars": len(sig),
            "median_bar_range_all_regular": round(med_range, 4), "median_bar_range_signal_window": round(med_range_sig, 4),
            "median_atr14": round(statistics.median(ind.atr[i] for i in sig), 4),
            "median_stop_distance_1.5atr": round(med_stop, 4),
            "stop_over_median_range": round(med_stop / med_range, 3),
            "stop_over_median_range_p10_p90": [round(dec[0], 3), round(dec[-1], 3)],
            "stop_1atr_over_median_range": round(med_stop / STOP_ATR / med_range, 3),
            "share_next_bar_range_wider_than_1.5atr_stop": round(wider, 4),
            "share_next_bar_range_wider_than_1atr_stop": round(wider_1x, 4)}


# ----------------------------------------------------------------------------------------------- main
def clean(t):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in t.items()}


def main():
    ind = prepare(load_rows())
    main_long, trades_main, _ = run(ind, 1, MAIN, "main")
    stress_long, _, _ = run(ind, 1, STRESS, "stress")
    variants = {
        "vwap_bounce": run(ind, 1, MAIN, "main", trigger="bounce")[0],
        "stop_1atr_target_2atr": run(ind, 1, MAIN, "main", stop_mult=1.0, target_mult=2.0)[0],
        "before_costs": run(ind, 1, MAIN, "main", slip=0.0)[0],
        "same_bar_counted_as_target": run(ind, 1, MAIN, "main", same_bar="target")[0],
        "short_side": run(ind, -1, MAIN, "main")[0],
        "short_side_stress": run(ind, -1, STRESS, "stress")[0],
    }
    stress_before = run(ind, 1, STRESS, "stress", slip=0.0)[0]
    plc = placebo(ind, trades_main)
    pil = pilot(ind)
    verdict = ("PASS (robust)" if stress_long["passes"] else "PASS (post-COVID only)") if main_long["passes"] else "FAIL"
    out = {"plan": PLAN, "verdict": verdict, "pilot_no_returns": pil, "main_long": main_long, "stress_long": stress_long,
           "stress_long_before_costs": stress_before, "variants_info": variants, "random_entry_placebo": plc,
           "trades_main_long": [clean(t) for t in trades_main]}
    OUT.write_text(json.dumps(out, default=str) + "\n")
    write_manifest(OUT, code=["research/vwap_trend_test_v1/backtest.py", "research/crt_sweep_test_v1/backtest.py",
                              "research/crt_sweep_test_v1/fetch.py", "research/provenance_v1/provenance.py"],
                   data=[str(path_for("QQQ"))],
                   params={"ema": EMA_LENS, "atr": ATR_N, "warmup_bars": WARMUP, "stop_atr": STOP_ATR,
                           "target_atr": TARGET_ATR, "signal_bars": "9:45-15:00", "placebo_entry_bars": "9:50-15:05",
                           "risk": RISK, "max_weight": MAX_WEIGHT, "slip": SLIP, "main": MAIN, "stress": STRESS,
                           "placebo_seed": PLACEBO_SEED, "placebo_repeats": PLACEBO_REPEATS,
                           "mnq_usd_per_qqq_point_approx": MNQ_USD_PER_QQQ_POINT})
    keys = ("trades", "trades_per_year", "win_rate_pct", "target_hit_rate_pct",
            "break_even_target_hit_rate_pct_before_costs", "avg_win_usd", "avg_loss_usd", "avg_r_multiple",
            "exit_split", "profit_factor", "final_equity", "total_pnl_usd", "max_drawdown_pct", "usd_per_week_avg",
            "usd_per_week_median", "weeks_at_least_1000_pct", "worst_week", "worst_month", "halves", "pnl_by_year",
            "same_bar_ambiguity", "mnq_translation_approx", "checks", "passes")
    short = ("trades", "trades_per_year", "profit_factor", "total_pnl_usd", "max_drawdown_pct", "usd_per_week_avg",
             "target_hit_rate_pct", "pnl_by_year", "checks")
    print(json.dumps({"verdict": verdict, "pilot": pil, "main_long": {k: main_long[k] for k in keys},
                      "stress_long": {k: stress_long[k] for k in short},
                      "variants_info": {n: {k: v[k] for k in short} for n, v in variants.items()},
                      "placebo": plc["summary"]}, indent=1, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true", help="only the no-returns stop-vs-bar-range pilot")
    if ap.parse_args().pilot:
        print(json.dumps(pilot(prepare(load_rows())), indent=1))
    else:
        main()
