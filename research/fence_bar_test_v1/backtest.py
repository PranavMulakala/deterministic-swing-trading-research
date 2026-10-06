"""Backtest of pre-declared test #18, the "fence bar" opening setup (output/FENCE_BAR_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.fence_bar_test_v1.backtest

Long rule: fence = the 9:30 bar's high/low; a later 5-minute close above the high arms it (a close back at or below
disarms); entry at the close of a bar that opens above the high, trades back to or below it and closes above it,
starting by 10:55, with the 20-bar average of closes flat or rising; stop at the fence midpoint, target 2R, else exit
at the day's last close. Shorts are the same code on mirrored prices. Sizing, costs, loader and mirroring are test
#8's (research/crt_sweep_test_v1/backtest.py). Research only; no orders.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path

from research.crt_sweep_test_v1.backtest import (MAX_WEIGHT, RISK, SLIP, START_EQUITY, down, drawdown, load, mirror,
                                                 up)
from research.crt_sweep_test_v1.fetch import path_for
from research.provenance_v1.provenance import same_bar_ambiguity, write_manifest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/fence-bar-test-results.json"
SMA_N, LAST_ENTRY, LATE_ENTRY = 20, 655, 895          # bar starts 10:55 and 14:55
MAIN, STRESS = ("2020-01-02", "2026-12-31"), ("2016-01-01", "2026-12-31")
HALVES = {"main": (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2026", "2023-01-01", "2026-12-31")),
          "stress": (("2016-2020", "2016-01-01", "2020-12-31"), ("2021-2026", "2021-01-01", "2026-12-31"))}


def day_trade(day, history, last_entry=LAST_ENTRY, use_filter=True, stop_rule="mid", same_bar="stop"):
    """The day's first fence-bar long on (possibly mirrored) bars, or None. `history`: earlier days' closes."""
    if not day or day[0]["m"] != 570:
        return None
    hi, lo = day[0]["h"], day[0]["l"]
    closes = list(history[-(SMA_N + 1):]) + [day[0]["c"]]
    armed = day[0]["c"] > hi                          # can't happen (close <= high); kept for clarity
    for i in range(1, len(day)):
        b = day[i]
        closes.append(b["c"])
        if armed and b["m"] <= last_entry and b["o"] > hi and b["l"] <= hi and b["c"] > hi:
            ok = True
            if use_filter:
                ok = len(closes) >= SMA_N + 1 and sum(closes[-SMA_N:]) >= sum(closes[-SMA_N - 1:-1])
            if ok:
                entry = b["c"]
                stop = (hi + lo) / 2 if stop_rule == "mid" else b["l"]
                target = entry + 2 * (entry - stop)
                after = day[i + 1:]
                exit_px, reason, exit_i = None, None, None
                for j, a in enumerate(after):
                    hit_stop, hit_target = a["l"] <= stop, a["h"] >= target
                    if hit_stop and hit_target:
                        exit_px, reason = (stop, "stop_same_bar") if same_bar == "stop" else (target, "target_same_bar")
                    elif hit_stop:
                        exit_px, reason = stop, "stop"
                    elif hit_target:
                        exit_px, reason = target, "target"
                    if reason:
                        exit_i = i + 1 + j
                        break
                if reason is None:
                    exit_i = len(day) - 1
                    exit_px, reason = day[exit_i]["c"], "close"
                return {"entry_m": b["m"], "exit_m": day[exit_i]["m"], "entry": entry, "stop": stop, "target": target,
                        "exit": exit_px, "reason": reason, "fence": (hi, lo),
                        "bars_after": [{"h": a["h"], "l": a["l"], "c": a["c"]} for a in after]}
        armed = b["c"] > hi
    return None


def simulate(days, side, window, slip=SLIP, **rule):
    """One account per symbol and side: trades and the daily equity curve inside `window`."""
    sign, equity, trades, curve, history = (1 if side == "long" else -1), START_EQUITY, [], [], []
    for date, day in days.items():
        bars = day if side == "long" else mirror(day)
        if window[0] <= date <= window[1]:
            t = day_trade(bars, history, **rule)
            if t:
                fill, out = up(t["entry"], slip), down(t["exit"], slip)
                risk = fill - t["stop"]
                shares = math.floor(min(RISK * equity / risk, MAX_WEIGHT * equity / abs(fill))) if risk > 0 else 0
                if shares >= 1:
                    pnl = shares * (out - fill)
                    equity += pnl
                    trades.append({"date": date, "side": side, "entry_time": f"{t['entry_m'] // 60}:{t['entry_m'] % 60:02d}",
                                   "exit_time": f"{t['exit_m'] // 60}:{t['exit_m'] % 60:02d}", "shares": shares,
                                   "entry": round(sign * t["entry"], 4), "stop": round(sign * t["stop"], 4),
                                   "target": round(sign * t["target"], 4), "exit": round(sign * t["exit"], 4),
                                   "reason": t["reason"], "pnl": pnl, "r_multiple": pnl / (shares * risk),
                                   "_amb": {"stop": t["stop"], "target": t["target"], "bars": t["bars_after"]}})
            curve.append((date, equity))
        history.extend(b["c"] for b in bars)
        del history[:-(SMA_N + 1)]
    return trades, curve


def benchmark(spy_days, window):
    closes = [(d, bars[-1]["c"]) for d, bars in spy_days.items() if window[0] <= d <= window[1]]
    years = len(closes) / 252
    total = closes[-1][1] / closes[0][1]
    cagr = total ** (1 / years) - 1
    dd = drawdown([c for _, c in closes])
    return {"total_return_pct": round((total - 1) * 100, 1), "cagr_pct": round(cagr * 100, 2),
            "max_drawdown_pct": round(dd * 100, 1), "cagr_over_dd": round(cagr / abs(dd), 3)}


def summarize(trades, curve, bench, halves):
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gain, loss = sum(t["pnl"] for t in wins), -sum(t["pnl"] for t in losses)
    value, dates = dict(curve), [d for d, _ in curve]
    years = len(dates) / 252
    final = curve[-1][1]
    cagr = (final / START_EQUITY) ** (1 / years) - 1
    dd = drawdown([START_EQUITY] + [e for _, e in curve])

    def change(a, b):
        inside = [d for d in dates if a <= d <= b]
        before = [d for d in dates if d < inside[0]]
        return value[inside[-1]] / (value[before[-1]] if before else START_EQUITY) - 1

    half = {name: round(change(a, b) * 100, 1) for name, a, b in halves}
    by_year = defaultdict(float)
    for t in trades:
        by_year[t["date"][:4]] += t["pnl"]
    targets = sum(1 for t in trades if t["reason"].startswith("target"))
    out = {"trades": len(trades), "trades_per_year": round(len(trades) / years, 1),
           "days_with_trade_pct": round(100 * len(trades) / max(len(dates), 1), 1),
           "target_hit_rate_pct": round(100 * targets / max(len(trades), 1), 1),
           "win_rate_pct": round(100 * len(wins) / max(len(trades), 1), 1),
           "avg_win_usd": round(gain / max(len(wins), 1)), "avg_loss_usd": round(loss / max(len(losses), 1)),
           "avg_r_multiple": round(sum(t["r_multiple"] for t in trades) / max(len(trades), 1), 3),
           "exit_reasons": dict(Counter(t["reason"] for t in trades)),
           "profit_factor": round(gain / loss, 3) if loss else None,
           "final_equity": round(final), "total_return_pct": round((final / START_EQUITY - 1) * 100, 1),
           "cagr_pct": round(cagr * 100, 2), "max_drawdown_pct": round(dd * 100, 1),
           "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None, "halves_return_pct": half,
           "pnl_by_year": {y: round(v) for y, v in sorted(by_year.items())},
           "same_bar_ambiguity": same_bar_ambiguity([t["_amb"] for t in trades])}
    out["checks"] = {"A1_profit_factor_at_least_1.3": (out["profit_factor"] or 0) >= 1.3,
                     "A2_profitable_in_both_halves": all(v > 0 for v in half.values()),
                     "A3_max_drawdown_at_most_25pct": out["max_drawdown_pct"] >= -25.0,
                     "B1_drawdown_5pts_smaller_than_spy": out["max_drawdown_pct"] >= bench["max_drawdown_pct"] + 5,
                     "B2_cagr_over_dd_beats_spy": (out["cagr_over_dd"] or -9) > bench["cagr_over_dd"]}
    out["passes"] = all(out["checks"].values())
    return out


def run(days, side, window, bench, halves, **kw):
    trades, curve = simulate(days, side, window, **kw)
    return summarize(trades, curve, bench, halves), trades


def main():
    data = {s: load(s) for s in ("QQQ", "SPY")}
    bench = {"main": benchmark(data["SPY"], MAIN), "stress": benchmark(data["SPY"], STRESS)}
    res, trade_lists = {}, {}
    for s, days in data.items():
        main_res, trades = run(days, "long", MAIN, bench["main"], HALVES["main"])
        stress_res, _ = run(days, "long", STRESS, bench["stress"], HALVES["stress"])
        info = {}
        for name, kw in (("no_anchor_filter", {"use_filter": False}), ("stop_at_retest_low", {"stop_rule": "retest_low"}),
                         ("entries_until_3pm", {"last_entry": LATE_ENTRY}), ("before_costs", {"slip": 0.0}),
                         ("same_bar_counted_as_target", {"same_bar": "target"})):
            info[name], _ = run(days, "long", MAIN, bench["main"], HALVES["main"], **kw)
        info["short_side"], _ = run(days, "short", MAIN, bench["main"], HALVES["main"])
        res[s] = {"main_long": main_res, "stress_long": stress_res, "info": info}
        trade_lists[s] = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in t.items() if k != "_amb"}
                          for t in trades]
    main_pass = all(res[s]["main_long"]["passes"] for s in res)
    stress_pass = all(res[s]["stress_long"]["passes"] for s in res)
    verdict = ("PASS (robust)" if stress_pass else "PASS (post-COVID only)") if main_pass else "FAIL"
    out = {"plan": "output/FENCE_BAR_TEST_PLAN_20261005.md", "verdict": verdict, "spy_benchmark": bench,
           "results": res, "trades_main_long": trade_lists}
    OUT.write_text(json.dumps(out, default=str) + "\n")
    write_manifest(OUT, code=["research/fence_bar_test_v1/backtest.py", "research/crt_sweep_test_v1/backtest.py",
                              "research/crt_sweep_test_v1/fetch.py"],
                   data=[str(path_for(s)) for s in ("QQQ", "SPY")],
                   params={"sma": SMA_N, "last_entry_bar_start": "10:55", "stop": "fence midpoint", "target_r": 2,
                           "risk": RISK, "slip": SLIP, "main": MAIN, "stress": STRESS})
    keys = ("trades", "trades_per_year", "days_with_trade_pct", "target_hit_rate_pct", "win_rate_pct", "avg_r_multiple",
            "profit_factor", "final_equity", "cagr_pct", "max_drawdown_pct", "cagr_over_dd", "halves_return_pct",
            "exit_reasons", "checks")
    show = {s: {"main_long": {k: r["main_long"][k] for k in keys},
                "stress_long": {k: r["stress_long"][k] for k in ("final_equity", "cagr_pct", "max_drawdown_pct",
                                                                  "profit_factor", "passes")},
                "info": {n: {k: v[k] for k in ("trades", "profit_factor", "final_equity", "cagr_pct", "max_drawdown_pct")}
                         for n, v in r["info"].items()},
                "same_bar": r["main_long"]["same_bar_ambiguity"], "pnl_by_year": r["main_long"]["pnl_by_year"]}
            for s, r in res.items()}
    print(json.dumps({"verdict": verdict, "spy": bench, **show}, indent=1))


if __name__ == "__main__":
    main()
