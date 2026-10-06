"""Test #21, the 1-minute re-check (plan section "1-minute re-check", declared after the 5-minute result and before any
1-minute data): the unchanged picks, opening range, stop and costs, with entries, stops and the close exit tracked on
1-minute bars after 9:35 instead of 5-minute bars. Same accounts and checks as backtest.py.

  PYTHONPATH=src:. .venv/bin/python -m research.stocks_in_play_orb_v1.backtest1m
"""
from __future__ import annotations

from collections import Counter
import json

from research.provenance_v1.provenance import write_manifest
from research.stocks_in_play_orb_v1.backtest import (AFTER, INFO_HALVES, LEVERED_CAP, MAIN, PAPER, account, benchmark,
                                                     summarize, trade_path)
from research.stocks_in_play_orb_v1.data import ROOT, base_dir, calendar, load, save
from research.stocks_in_play_orb_v1.fetch import TEST_START
from research.stocks_in_play_orb_v1.rules import direction

OUT = ROOT / "output/stocks-in-play-orb-1min-recheck-results.json"


def plans_1m(base, picks):
    """Like backtest.plans, but each pick's path after 9:35 is its 1-minute bars."""
    out, checks = {}, Counter()
    for day, rows in picks.items():
        p = base / "day1" / f"{day}.json.gz"
        bars = load(p)["bars"] if p.exists() else {}
        out[day] = []
        for sym, rv, _, atr, first in rows:
            checks["picks"] += 1
            side = direction(first)
            if side == 0:
                checks["doji_no_trade"] += 1
                continue
            later = [b for b in bars.get(sym, []) if b[0] >= 575]
            if not later:
                checks["picks_without_1min_bars"] += 1
                continue
            out[day].append((sym, atr, rv, trade_path(first, later, atr, side, "stop"),
                             trade_path(first, later, atr, side, "flip")))
    return out, dict(checks)


def main():
    base = base_dir()
    cal = calendar(base)
    spy = load(base / "SPY_all.json.gz")
    spy = {"date": spy["date"], "close": [b[3] for b in spy["bars"]]}
    detail = load(base / "results_detail.json.gz")
    picks = {d: [tuple(r) for r in rows] for d, rows in detail["picks"].items()}
    plan, data_checks = plans_1m(base, picks)
    days = [d for d in cal if d >= TEST_START]

    def run(window, **kw):
        trades, curve, too_small = account(days, plan, window, **kw)
        return summarize(trades, curve, benchmark(spy, window), INFO_HALVES[window]), trades, curve, too_small

    main_res, main_trades, curve, too_small = run(MAIN)
    entered = sum(1 for d in days if MAIN[0] <= d <= MAIN[1] for r in plan.get(d, []) if r[3] and r[3]["side"] == 1)
    assert entered == len(main_trades) + too_small, "entered != recorded + too small"
    main_res["entries_too_small_for_one_share"] = too_small
    flip, _, _, _ = run(MAIN, same_bar="flip")
    after, _, _, _ = run(AFTER)
    if main_res["passes"]:
        verdict = "PASS (robust)" if (after["cagr_over_dd"] or -9) > after["spy"]["cagr_over_dd"] else "PASS (2020-2023 only)"
    elif flip["passes"]:
        verdict = "FAIL (unresolved: passes only if ambiguous 1-minute bars are flipped)"
    else:
        verdict = "FAIL"
    info = {"long_same_bar_flip": flip, "long_2024_2026_after_paper": after}
    for name, window, kw in (
            ("both_sides", MAIN, {"sides": (1, -1)}),
            ("shorts_only", MAIN, {"sides": (-1,)}),
            ("long_4x_leverage", MAIN, {"cap": LEVERED_CAP}),
            ("paper_version_both_sides_4x", MAIN, {"sides": (1, -1), "cap": LEVERED_CAP}),
            ("long_before_costs", MAIN, {"slip": 0.0, "commission": 0.0}),
            ("long_slippage_0.05pct", MAIN, {"slip": 0.0005}),
            ("paper_version_same_bar_flip", MAIN, {"sides": (1, -1), "cap": LEVERED_CAP, "same_bar": "flip"}),
            ("long_2016_2023_paper_period", PAPER, {}),
            ("paper_version_2016_2023", PAPER, {"sides": (1, -1), "cap": LEVERED_CAP}),
            ("paper_version_2024_2026", AFTER, {"sides": (1, -1), "cap": LEVERED_CAP})):
        info[name] = run(window, **kw)[0]
    top = Counter(t["symbol"] for t in main_trades).most_common(15)
    out = {"plan": "output/STOCKS_IN_PLAY_ORB_TEST_PLAN_20261005.md (1-minute re-check)", "verdict": verdict,
           "main_long_cash": main_res, "info": info, "data_checks": data_checks, "most_traded_main": top}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    detail_1m = base / "results_detail_1min.json.gz"
    save(detail_1m, {"main_trades": main_trades, "main_curve": curve})
    write_manifest(OUT, code=["research/stocks_in_play_orb_v1/backtest1m.py", "research/stocks_in_play_orb_v1/backtest.py",
                              "research/stocks_in_play_orb_v1/fetch1m.py"],
                   data=[str(base / "SPY_all.json.gz"), str(base / "results_detail.json.gz"), str(detail_1m)],
                   params={"main": MAIN, "bars": "1Min after 9:35; opening range = 9:30-9:35 5-minute candle"})
    brief = {k: v for k, v in main_res.items() if k != "pnl_by_year"}
    print(json.dumps({"verdict": verdict, "main_long_cash": brief, "pnl_by_year": main_res["pnl_by_year"],
                      "data_checks": data_checks, "most_traded": top,
                      "info": {k: {x: v[x] for x in ("trades", "win_rate_pct", "profit_factor", "final_equity", "cagr_pct",
                                                     "max_drawdown_pct", "same_bar_ambiguous_pct", "passes")}
                               for k, v in info.items()}}, indent=1))


if __name__ == "__main__":
    main()
