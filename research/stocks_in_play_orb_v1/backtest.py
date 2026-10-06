"""Backtest of pre-declared test #21, the "Stocks in Play" 5-minute opening-range breakout (Zarattini, Barbon & Aziz
2024), as published (plan: output/STOCKS_IN_PLAY_ORB_TEST_PLAN_20261005.md). Research only; no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.stocks_in_play_orb_v1.backtest

Each day: the 20 stocks with the highest opening relative volume (>= 1.0) among those with an opening price > $5,
14-day average volume >= 1M shares and 14-day ATR > $0.50 (rules.py, data.py). The first 5-minute candle's direction
picks the side; a stop order at its high (long) or low (short) enters; the stop is 10% of the ATR from the fill; exit at
the stop or the day's close. 1% of the day's starting equity at risk per trade, capped at 5% of equity per position
(cash account; 20% = the paper's 4x leverage, information only). $0.0035/share commission and 0.01% slippage per side.
The main verdict counts long trades only (the owner's accounts can't short).
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import math

from research.provenance_v1.provenance import write_manifest
from research.stocks_in_play_orb_v1.data import ROOT, base_dir, calendar, load, metric_table, save, selections
from research.stocks_in_play_orb_v1.fetch import FIRST, LAST, TEST_START
from research.stocks_in_play_orb_v1.rules import TOP_N, direction

OUT = ROOT / "output/stocks-in-play-orb-test-results.json"
START_EQUITY, RISK, STOP_ATR, CAP, LEVERED_CAP = 100_000.0, 0.01, 0.10, 0.05, 0.20
COMMISSION, SLIP = 0.0035, 0.0001
MAIN = ("2020-01-02", LAST)
PAPER, AFTER = ("2016-01-04", "2023-12-29"), ("2024-01-02", LAST)
HALVES = (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2026", "2023-01-01", "2026-12-31"))
INFO_HALVES = {PAPER: (("2016-2019", "2016-01-01", "2019-12-31"), ("2020-2023", "2020-01-01", "2023-12-31")),
               AFTER: (("2024", "2024-01-01", "2024-12-31"), ("2025-2026", "2025-01-01", "2026-12-31")), MAIN: HALVES}


def trade_path(first, later, atr, side, same_bar="stop"):
    """One stock-day. first: the 9:30 bar [o, h, l, c, v]; later: [[minute, o, h, l, c, v], ...] after 9:35;
    side: +1 long (stop order at the first candle's high) or -1 short (at its low). Returns None if never entered.

    The fill is the level, or the bar's open if it opens past it. The stop is 10% of the ATR from the fill. On the
    entry bar a stop hit is certain if the fill was at the open (the whole bar came after it) or the bar closed past the
    stop; if only its low (high, for shorts) reached the stop after a mid-bar fill, the order is unknown: same_bar="stop"
    assumes the stop (the plan's rule), "flip" assumes it came first and keeps the trade. Later bars stop out at the stop,
    or at the open if they gap past it; otherwise the exit is the last bar's close."""
    level, dist = (first[1] if side > 0 else first[2]), STOP_ATR * atr
    for k, (m, o, h, l, c, _) in enumerate(later):
        if not (h >= level if side > 0 else l <= level):
            continue
        at_open = o >= level if side > 0 else o <= level
        fill = o if at_open else level
        stop = fill - side * dist
        reached = l <= stop if side > 0 else h >= stop
        closed_past = c <= stop if side > 0 else c >= stop
        ambiguous = reached and not at_open and not closed_past
        base = {"side": side, "entry": fill, "stop": stop, "entry_m": m, "ambiguous": ambiguous}
        if reached and (at_open or closed_past or same_bar == "stop"):
            return {**base, "exit": stop, "exit_m": m, "reason": "stop_same_bar"}
        for m2, o2, h2, l2, _, _ in later[k + 1:]:
            if l2 <= stop if side > 0 else h2 >= stop:
                return {**base, "exit": min(stop, o2) if side > 0 else max(stop, o2), "exit_m": m2, "reason": "stop"}
        return {**base, "exit": later[-1][4], "exit_m": later[-1][0], "reason": "close"}
    return None


def size(equity, atr, price, cap):
    """Whole shares: 1% of equity at risk over a stop of 10% of the ATR, capped at `cap` of equity."""
    return math.floor(min(RISK * equity / (STOP_ATR * atr), cap * equity / price))


def pnl(t, shares, slip=SLIP, commission=COMMISSION):
    """Dollar result after slippage on both fills and per-share commission on both sides."""
    s = t["side"]
    entry, exit_ = t["entry"] * (1 + s * slip), t["exit"] * (1 - s * slip)
    return s * shares * (exit_ - entry) - 2 * commission * shares


def plans(base, picks):
    """{day: [(symbol, atr, rv, main path, flip path)]} for every pick with a first-candle direction, plus data checks."""
    out, checks = {}, Counter()
    for day, rows in picks.items():
        p = base / "day5" / f"{day}.json.gz"
        bars = load(p)["bars"] if p.exists() else {}
        out[day] = []
        for sym, rv, _, atr, first in rows:
            checks["picks"] += 1
            day_bars = bars.get(sym)
            if not day_bars:
                checks["picks_without_day_bars"] += 1
                continue
            if day_bars[0][0] == 570 and [round(x, 6) for x in day_bars[0][1:5]] != [round(x, 6) for x in first[:4]]:
                checks["first_bar_mismatch"] += 1
            side = direction(first)
            if side == 0:
                checks["doji_no_trade"] += 1
                continue
            later = [b for b in day_bars if b[0] > 570]
            if not later:
                checks["no_bars_after_first"] += 1
                continue
            out[day].append((sym, atr, rv, trade_path(first, later, atr, side, "stop"),
                             trade_path(first, later, atr, side, "flip")))
    return out, dict(checks)


def account(days, plan, window, sides=(1,), cap=CAP, slip=SLIP, commission=COMMISSION, same_bar="stop"):
    """Daily equity, trades, and entries too small for one share: every trade is sized on the day's starting equity."""
    equity, curve, trades, too_small = START_EQUITY, [], [], 0
    for day in days:
        if not window[0] <= day <= window[1]:
            continue
        start, total = equity, 0.0
        for sym, atr, rv, main, flip in plan.get(day, []):
            t = flip if same_bar == "flip" else main
            if t is None or t["side"] not in sides:
                continue
            shares = size(start, atr, t["entry"], cap)
            if shares < 1:
                too_small += 1
                continue
            result = pnl(t, shares, slip, commission)
            total += result
            trades.append({"date": day, "symbol": sym, "side": t["side"], "rv": round(rv, 2), "atr": atr,
                           "shares": shares, "entry": t["entry"], "stop": round(t["stop"], 4), "exit": t["exit"],
                           "entry_m": t["entry_m"], "exit_m": t["exit_m"], "reason": t["reason"],
                           "ambiguous": t["ambiguous"], "pnl": result})
        equity = start + total
        curve.append((day, equity))
    return trades, curve, too_small


def drawdown(values):
    peak, worst = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst


def benchmark(spy, window):
    closes = [c for d, c in zip(spy["date"], spy["close"]) if window[0] <= d <= window[1]]
    years, total = len(closes) / 252, closes[-1] / closes[0]
    cagr, dd = total ** (1 / years) - 1, drawdown(closes)
    return {"final": round(START_EQUITY * total), "total_return_pct": round((total - 1) * 100, 1),
            "cagr_pct": round(cagr * 100, 2), "max_drawdown_pct": round(dd * 100, 1), "cagr_over_dd": round(cagr / abs(dd), 3)}


def summarize(trades, curve, bench, halves=HALVES):
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [-t["pnl"] for t in trades if t["pnl"] <= 0]
    value, dates = dict(curve), [d for d, _ in curve]
    years, final = len(dates) / 252, curve[-1][1]
    cagr = (final / START_EQUITY) ** (1 / years) - 1 if final > 0 else -1.0
    dd = drawdown([START_EQUITY] + [e for _, e in curve])

    def change(a, b):
        inside = [d for d in dates if a <= d <= b]
        if not inside:
            return None
        before = [d for d in dates if d < inside[0]]
        return round((value[inside[-1]] / (value[before[-1]] if before else START_EQUITY) - 1) * 100, 1)

    by_year = defaultdict(float)
    for t in trades:
        by_year[t["date"][:4]] += t["pnl"]
    amb = sum(t["ambiguous"] for t in trades)
    out = {"trades": len(trades), "trades_per_day": round(len(trades) / max(len(dates), 1), 2),
           "win_rate_pct": round(100 * len(wins) / max(len(trades), 1), 1),
           "avg_trade_usd": round(sum(t["pnl"] for t in trades) / max(len(trades), 1), 2),
           "profit_factor": round(sum(wins) / sum(losses), 3) if losses and sum(losses) else None,
           "exit_reasons": dict(Counter(t["reason"] for t in trades)),
           "same_bar_ambiguous": amb, "same_bar_ambiguous_pct": round(100 * amb / max(len(trades), 1), 1),
           "final_equity": round(final), "total_return_pct": round((final / START_EQUITY - 1) * 100, 1),
           "cagr_pct": round(cagr * 100, 2), "max_drawdown_pct": round(dd * 100, 1),
           "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None,
           "halves_return_pct": {name: change(a, b) for name, a, b in halves},
           "pnl_by_year": {y: round(v) for y, v in sorted(by_year.items())}, "spy": bench}
    out["checks"] = {"A1_profit_factor_at_least_1.3": (out["profit_factor"] or 0) >= 1.3,
                     "A2_profitable_in_both_halves": all((v or 0) > 0 for v in out["halves_return_pct"].values()),
                     "A3_max_drawdown_at_most_25pct": out["max_drawdown_pct"] >= -25.0,
                     "B1_drawdown_5pts_smaller_than_spy": out["max_drawdown_pct"] >= bench["max_drawdown_pct"] + 5,
                     "B2_cagr_over_dd_beats_spy": (out["cagr_over_dd"] or -9) > bench["cagr_over_dd"]}
    out["passes"] = all(out["checks"].values())
    return out


def main():
    base = base_dir()
    cal = calendar(base)
    spy = load(base / "SPY_all.json.gz")
    spy = {"date": spy["date"], "close": [b[3] for b in spy["bars"]]}
    symbols = sorted(p.name[:-8] for p in (base / "daily").glob("*.json.gz"))
    table = metric_table(base, symbols, cal)
    picks = selections(base, table, cal, TOP_N, TEST_START)
    plan, data_checks = plans(base, picks)
    days = [d for d in cal if d >= TEST_START]

    def run(window, **kw):
        trades, curve, too_small = account(days, plan, window, **kw)
        return summarize(trades, curve, benchmark(spy, window), INFO_HALVES[window]), trades, curve, too_small

    main_res, main_trades, curve, too_small = run(MAIN)
    entered = sum(1 for d in days if MAIN[0] <= d <= MAIN[1] for r in plan.get(d, []) if r[3] and r[3]["side"] == 1)
    assert entered == len(main_trades) + too_small, "entered != recorded + too small"
    main_res["entries_too_small_for_one_share"] = too_small
    after, _, _, _ = run(AFTER)
    if main_res["passes"]:
        verdict = "PASS (robust)" if (after["cagr_over_dd"] or -9) > after["spy"]["cagr_over_dd"] else "PASS (2020-2023 only)"
    else:
        verdict = "FAIL"
    info = {}
    for name, window, kw in (
            ("both_sides", MAIN, {"sides": (1, -1)}),
            ("shorts_only", MAIN, {"sides": (-1,)}),
            ("long_4x_leverage", MAIN, {"cap": LEVERED_CAP}),
            ("paper_version_both_sides_4x", MAIN, {"sides": (1, -1), "cap": LEVERED_CAP}),
            ("long_before_costs", MAIN, {"slip": 0.0, "commission": 0.0}),
            ("long_slippage_0.05pct", MAIN, {"slip": 0.0005}),
            ("long_same_bar_flip", MAIN, {"same_bar": "flip"}),
            ("paper_version_same_bar_flip", MAIN, {"sides": (1, -1), "cap": LEVERED_CAP, "same_bar": "flip"}),
            ("long_2016_2023_paper_period", PAPER, {}),
            ("paper_version_2016_2023", PAPER, {"sides": (1, -1), "cap": LEVERED_CAP}),
            ("paper_version_2016_2023_before_costs", PAPER, {"sides": (1, -1), "cap": LEVERED_CAP, "slip": 0.0, "commission": 0.0}),
            ("paper_version_2024_2026", AFTER, {"sides": (1, -1), "cap": LEVERED_CAP})):
        info[name] = run(window, **kw)[0]
    info["long_2024_2026_after_paper"] = after
    top = Counter(t["symbol"] for t in main_trades).most_common(15)
    out = {"plan": "output/STOCKS_IN_PLAY_ORB_TEST_PLAN_20261005.md", "verdict": verdict, "main_long_cash": main_res,
           "info": info, "data_checks": data_checks, "most_traded_main": top,
           "pick_days": sum(1 for d in picks if picks[d]), "symbols_with_daily_data": len(table)}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    detail = base / "results_detail.json.gz"
    save(detail, {"picks": {d: [[s, rv, av, atr, first] for s, rv, av, atr, first in rows] for d, rows in picks.items()},
                  "main_trades": main_trades, "main_curve": curve})
    write_manifest(OUT, code=["research/stocks_in_play_orb_v1/backtest.py", "research/stocks_in_play_orb_v1/rules.py",
                              "research/stocks_in_play_orb_v1/data.py", "research/stocks_in_play_orb_v1/fetch.py"],
                   data=[str(base / "SPY_all.json.gz"), str(detail)],
                   params={"top_n": TOP_N, "risk": RISK, "stop_atr": STOP_ATR, "cap": CAP, "commission": COMMISSION,
                           "slip": SLIP, "main": MAIN, "data_first": FIRST})
    brief = {k: v for k, v in main_res.items() if k != "pnl_by_year"}
    print(json.dumps({"verdict": verdict, "main_long_cash": brief, "pnl_by_year": main_res["pnl_by_year"],
                      "data_checks": data_checks, "most_traded": top,
                      "info": {k: {x: v[x] for x in ("trades", "win_rate_pct", "profit_factor", "final_equity", "cagr_pct",
                                                     "max_drawdown_pct", "passes")} for k, v in info.items()}}, indent=1))


if __name__ == "__main__":
    main()
