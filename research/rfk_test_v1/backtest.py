"""Backtest of pre-declared test #23, GAnderson's "range, fakeout, killshot" (plan: output/RFK_SETUP_TEST_PLAN_20261006.md).
Research only; no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.rfk_test_v1.backtest

Daily split-adjusted bars for the 5,259 stocks on disk (raw prices only for the $10 filter). A range of 20 days with
at least 2 swing lows within 2% of its low; a red fakeout day that undercuts that low and closes in its bottom 25%;
the next day closes above the fakeout day's high: buy at that close, stop at the fakeout low, target 1:1, 20-day limit.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path

from research.provenance_v1.provenance import write_manifest
from research.stocks_in_play_orb_v1.fetch import NOT_STOCKS

ROOT = Path(__file__).resolve().parents[2]
DAILY = ROOT / "outputs/orb_play_data/daily"
SPY_FILE = ROOT / "outputs/orb_play_data/SPY_all.json.gz"
OUT = ROOT / "output/rfk-test-results.json"
DETAIL = ROOT / "outputs/orb_play_data/rfk_detail.json.gz"

MIN_PRICE, MIN_DVOL, DVOL_DAYS, RANGE_DAYS, MAX_RANGE, LOW_BAND = 10.0, 50e6, 60, 20, 0.25, 0.02
CLOSE_ZONE, MAX_RISK, HOLD = 0.25, 0.20, 20
START, RISK, CAP, MAX_POS, SLIP = 100_000.0, 0.01, 0.10, 10, 0.001
MAIN, STRESS, LAST = "2020-01-02", "2016-01-04", "2026-10-02"
HALVES = (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2026", "2023-01-01", "2026-12-31"))


def read(path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def liquidity(raw):
    """Per day k, known at the close before it: the 60-day average dollar volume if raw close > $10 and it's >= $50M,
    else None."""
    pdv = [0.0]
    for r in raw:
        pdv.append(pdv[-1] + r[3] * r[4])
    out = [None] * len(raw)
    for k in range(DVOL_DAYS + 1, len(raw)):
        j = k - 1
        dvol = (pdv[j + 1] - pdv[j + 1 - DVOL_DAYS]) / DVOL_DAYS
        out[k] = dvol if raw[j][3] > MIN_PRICE and dvol >= MIN_DVOL else None
    return out


def swing_lows(bars, start, end):
    """Indexes j in [start, end - 2) whose low is below the 2 lows before and not above the 2 after (all < end)."""
    out = []
    for j in range(max(start, 2), end - 2):
        lo = bars[j][2]
        if lo < min(bars[j - 1][2], bars[j - 2][2]) and lo <= min(bars[j + 1][2], bars[j + 2][2]):
            out.append(j)
    return out


def fakeout(bars, f, need_range=True, close_below=False):
    """True if day f is a fakeout: (range + undercut, unless need_range=False) + red + close in the bottom 25%."""
    o, h, l, c = bars[f][:4]
    if h <= l or c >= o or (c - l) / (h - l) > CLOSE_ZONE:
        return False
    if not need_range:
        return True
    w = range(f - RANGE_DAYS, f)
    low = min(bars[i][2] for i in w)
    if max(bars[i][1] for i in w) / low - 1 > MAX_RANGE or l >= low or (close_below and c >= low):
        return False
    return sum(bars[j][2] <= low * (1 + LOW_BAND) for j in swing_lows(bars, f - RANGE_DAYS, f)) >= 2


def path(bars, entry_k, entry, stop, target, entry_at_open=False):
    """Exit (index, price, reason) from day entry_k+1 on (or from entry_k itself when entering at its open)."""
    first = entry_k if entry_at_open else entry_k + 1
    last = min(entry_k + HOLD, len(bars) - 1)
    for i in range(first, last + 1):
        o, h, l, c = bars[i][:4]
        if not (entry_at_open and i == entry_k):
            if o <= stop:
                return i, o, "stop_gap"
            if o >= target:
                return i, o, "target_gap"
        if l <= stop:
            return i, stop, "stop"
        if h >= target:
            return i, target, "target"
        if i == entry_k + HOLD:
            return i, c, "time"
    return last, bars[last][3], "end_of_data"


def signals(sym, b, need_range=True, close_below=False, r_mult=1.0, entry_at_open=False, liq=None):
    raw, bars, dates = b["raw"], b["split"], b["date"]
    liq = liq if liq is not None else liquidity(raw)
    out = []
    for f in range(DVOL_DAYS + 1, len(bars) - 1):
        k = f + 1
        dvol = liq[f]
        if dvol is None or bars[k][3] <= bars[f][1] or not fakeout(bars, f, need_range, close_below):
            continue
        if entry_at_open:
            if k + 1 >= len(bars):
                continue
            k_entry, entry = k + 1, bars[k + 1][0]
        else:
            k_entry, entry = k, bars[k][3]
        stop = bars[f][2]
        risk = entry - stop
        if risk <= 0 or risk / entry > MAX_RISK:
            continue
        target = entry + r_mult * risk
        xi, xp, why = path(bars, k_entry, entry, stop, target, entry_at_open)
        out.append({"symbol": sym, "fakeout": dates[f], "date": dates[k_entry], "entry": entry, "stop": stop,
                    "target": target, "exit_date": dates[xi], "exit": xp, "reason": why, "dvol": dvol,
                    "r": (xp - entry) / risk, "r_after_costs": (xp * (1 - SLIP) - entry * (1 + SLIP)) / risk})
    return out


def drawdown(values):
    peak, worst = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst


def simulate(sigs, closes, calendar, start, end=LAST):
    """Cash account: at each close, exits first, then new entries by most-traded first."""
    by_day = defaultdict(list)
    for s in sigs:
        if start <= s["date"] <= end:
            by_day[s["date"]].append(s)
    cash, held, curve, trades = START, {}, [], []
    days = [d for d in calendar if start <= d <= end]
    for d in days:
        for sym in [s for s, p in held.items() if p["exit_date"] == d]:
            p = held.pop(sym)
            proceeds = p["shares"] * p["exit"] * (1 - SLIP)
            cash += proceeds
            trades.append({**{k: p[k] for k in ("symbol", "date", "exit_date", "reason", "shares", "entry", "exit")},
                           "pnl": proceeds - p["cost"], "r": p["r_after_costs"]})
        for sym, p in held.items():
            p["last"] = closes[sym].get(d, p.get("last", p["entry"]))
        equity = cash + sum(p["shares"] * p["last"] for p in held.values())
        for s in sorted(by_day.get(d, []), key=lambda s: (-s["dvol"], s["symbol"])):
            if len(held) >= MAX_POS or s["symbol"] in held:
                continue
            price = s["entry"] * (1 + SLIP)
            shares = math.floor(min(RISK * equity / (s["entry"] - s["stop"]), CAP * equity / price, cash / price))
            if shares < 1:
                continue
            cost = shares * price
            cash -= cost
            if s["exit_date"] == d:                    # bought at the open and exited the same day (next-open variant)
                proceeds = shares * s["exit"] * (1 - SLIP)
                cash += proceeds
                trades.append({**{k: s[k] for k in ("symbol", "date", "exit_date", "reason", "entry", "exit")},
                               "shares": shares, "pnl": proceeds - cost, "r": s["r_after_costs"]})
                continue
            held[s["symbol"]] = {**s, "shares": shares, "cost": cost, "last": s["entry"]}
        curve.append((d, cash + sum(p["shares"] * p["last"] for p in held.values())))
    return trades, curve, len(held)


def stats(trades, curve, spy, halves=HALVES):
    vals = [v for _, v in curve]
    years = len(vals) / 252
    cagr = (vals[-1] / START) ** (1 / years) - 1
    dd = drawdown([START] + vals)
    value, dates = dict(curve), [d for d, _ in curve]

    def change(a, b):
        inside = [d for d in dates if a <= d <= b]
        before = [d for d in dates if d < inside[0]] if inside else []
        return round(100 * (value[inside[-1]] / (value[before[-1]] if before else START) - 1), 1) if inside else None

    gains = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    losses = -sum(t["pnl"] for t in trades if t["pnl"] <= 0)
    sc = [spy[d] for d in dates if d in spy]
    s_years = len(sc) / 252
    s_cagr = (sc[-1] / sc[0]) ** (1 / s_years) - 1
    s_dd = drawdown(sc)
    out = {"final": round(vals[-1]), "cagr_pct": round(100 * cagr, 2), "max_drawdown_pct": round(100 * dd, 1),
           "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None, "trades": len(trades),
           "win_rate_pct": round(100 * sum(t["pnl"] > 0 for t in trades) / max(len(trades), 1), 1),
           "profit_factor": round(gains / losses, 3) if losses else None,
           "avg_r_after_costs": round(sum(t["r"] for t in trades) / max(len(trades), 1), 3),
           "exit_reasons": dict(Counter(t["reason"] for t in trades)),
           "halves_return_pct": {n: change(a, b) for n, a, b in halves},
           "spy": {"final": round(START * sc[-1] / sc[0]), "cagr_pct": round(100 * s_cagr, 2),
                   "max_drawdown_pct": round(100 * s_dd, 1), "cagr_over_dd": round(s_cagr / abs(s_dd), 3)}}
    out["checks"] = {"A1_profit_factor_1.3": (out["profit_factor"] or 0) >= 1.3,
                     "A2_both_halves_profitable": all((v or 0) > 0 for v in out["halves_return_pct"].values()),
                     "A3_drawdown_within_25": out["max_drawdown_pct"] >= -25.0,
                     "B1_drawdown_5pts_smaller_than_spy": out["max_drawdown_pct"] >= out["spy"]["max_drawdown_pct"] + 5,
                     "B2_cagr_over_dd_beats_spy": (out["cagr_over_dd"] or -9) > out["spy"]["cagr_over_dd"]}
    out["passes"] = all(out["checks"].values())
    return out


def event_stats(sigs, start=MAIN):
    xs = [s for s in sigs if s["date"] >= start]
    if not xs:
        return None
    return {"signals": len(xs), "hit_target_pct": round(100 * sum(s["reason"].startswith("target") for s in xs) / len(xs), 1),
            "hit_stop_pct": round(100 * sum(s["reason"].startswith("stop") for s in xs) / len(xs), 1),
            "avg_r": round(sum(s["r"] for s in xs) / len(xs), 3),
            "avg_r_after_costs": round(sum(s["r_after_costs"] for s in xs) / len(xs), 3),
            "median_risk_pct": round(100 * sorted((s["entry"] - s["stop"]) / s["entry"] for s in xs)[len(xs) // 2], 2)}


def main():
    spy_b = read(SPY_FILE)
    spy = {d: x[3] for d, x in zip(spy_b["date"], spy_b["bars"])}
    calendar = spy_b["date"]
    variants = {"main": {}, "target_2r": {"r_mult": 2.0}, "close_below_range_low": {"close_below": True},
                "buy_next_open": {"entry_at_open": True}, "baseline_no_range": {"need_range": False}}
    sigs = {v: [] for v in variants}
    closes = {}
    for p in sorted(DAILY.glob("*.json.gz")):
        sym = p.name[:-8]
        if sym in NOT_STOCKS:
            continue
        b = read(p)
        liq = liquidity(b["raw"])
        before = sum(len(x) for x in sigs.values())
        for v, kw in variants.items():
            sigs[v] += signals(sym, b, liq=liq, **kw)
        if sum(len(x) for x in sigs.values()) > before:
            closes[sym] = {d: x[3] for d, x in zip(b["date"], b["split"])}
    main_trades, main_curve, open_end = simulate(sigs["main"], closes, calendar, MAIN)
    res = stats(main_trades, main_curve, spy)
    res["open_at_end"] = open_end
    st_trades, st_curve, _ = simulate(sigs["main"], closes, calendar, STRESS)
    stress = stats(st_trades, st_curve, spy, (("2016-2019", "2016-01-01", "2019-12-31"), ("2020-2026", "2020-01-01", "2026-12-31")))
    verdict = ("PASS (robust)" if stress["checks"]["B2_cagr_over_dd_beats_spy"] else "PASS (post-COVID only)") if res["passes"] else "FAIL"
    info = {}
    for v in ("target_2r", "close_below_range_low", "buy_next_open"):
        t, c, _ = simulate(sigs[v], closes, calendar, MAIN)
        info[v] = stats(t, c, spy)
    by_year = defaultdict(float)
    for t in main_trades:
        by_year[t["exit_date"][:4]] += t["pnl"]
    examples = [s for s in sigs["main"] if s["symbol"] in ("AVGO", "APP", "CRWV", "QQQ") and s["date"] >= "2026-06-01"]
    out = {"plan": "output/RFK_SETUP_TEST_PLAN_20261006.md", "verdict": verdict, "main": res,
           "stress_2016_2026": stress, "info_accounts": info,
           "events": {v: event_stats(sigs[v]) for v in variants},
           "events_stress_2016_2019": event_stats([s for s in sigs["main"] if s["date"] < MAIN], STRESS),
           "pnl_by_year": {y: round(v) for y, v in sorted(by_year.items())},
           "most_traded": Counter(t["symbol"] for t in main_trades).most_common(12),
           "his_examples_in_data": examples}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    with gzip.open(DETAIL, "wt") as f:
        json.dump({"signals_main": sigs["main"], "trades_main": main_trades, "curve_main": main_curve}, f)
    write_manifest(OUT, code=["research/rfk_test_v1/backtest.py"], data=[str(SPY_FILE), str(DETAIL)],
                   params={"range_days": RANGE_DAYS, "max_range": MAX_RANGE, "low_band": LOW_BAND, "close_zone": CLOSE_ZONE,
                           "max_risk": MAX_RISK, "hold": HOLD, "risk": RISK, "cap": CAP, "max_pos": MAX_POS, "slip": SLIP})
    print(json.dumps({k: out[k] for k in ("verdict", "main", "events", "events_stress_2016_2019", "pnl_by_year", "most_traded")}, indent=1))
    print(json.dumps({"stress": {k: stress[k] for k in ("final", "cagr_pct", "max_drawdown_pct", "spy")},
                      "info": {v: {k: r[k] for k in ("final", "cagr_pct", "max_drawdown_pct", "profit_factor", "passes")} for v, r in info.items()},
                      "examples": examples}, indent=1))


if __name__ == "__main__":
    main()
