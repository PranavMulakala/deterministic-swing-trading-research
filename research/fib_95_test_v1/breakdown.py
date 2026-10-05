"""Information-only breakdown for test #11, written after the main run (does not change the pre-declared verdict).

Splits 2-close signals by whether the signal candle had ALREADY closed beyond the start of the move (the
"reversal" was effectively done before the signal) or was still between the level and the start (a genuine
forecast). Also reports a signed version of the counter-trend trade for genuine-forecast signals only.

  PYTHONPATH=src:. .venv/bin/python -m research.fib_95_test_v1.breakdown
"""
from __future__ import annotations

import json
import statistics

from research.crt_sweep_test_v1.backtest import load
from research.crt_sweep_test_v1.fetch import SYMBOLS
from research.fib_95_test_v1.run import MIN_MOVE, build, mirror, signal_and_outcome, up_moves

COST_ROUND_TRIP_PCT = 0.02


def main():
    report = {}
    for symbol in SYMBOLS:
        days = load(symbol)
        for tf in ("1h", "daily"):
            c = build(days, tf)
            row = {}
            for x in (0.85, 0.887, 0.90):
                already = inside_rev = inside_cont = 0
                pnl = []
                for series in (c, mirror(c)):
                    for li, hi_i in up_moves(series, MIN_MOVE[tf]):
                        r = signal_and_outcome(series, li, hi_i, x)
                        if r is None or r["outcome"] in ("unresolved",):
                            continue
                        if r["entry"] <= r["lo"]:
                            already += 1
                            continue
                        e = abs(r["entry"])
                        if r["outcome"] == "reversal":
                            inside_rev += 1
                            pnl.append((r["entry"] - r["lo"]) / e * 100)
                        else:  # continuation or ambiguous -> stop at the move's end
                            inside_cont += 1
                            pnl.append(-(r["hi"] - r["entry"]) / e * 100)
                n = inside_rev + inside_cont
                row[str(x)] = {"signals_already_beyond_start": already, "genuine_signals": n,
                               "genuine_reversal_rate_pct": round(100 * inside_rev / n, 1) if n else None,
                               "trade_avg_pct_before_costs": round(statistics.mean(pnl), 3) if pnl else None,
                               "trade_avg_pct_after_costs": round(statistics.mean(pnl) - COST_ROUND_TRIP_PCT, 3)
                               if pnl else None,
                               "trade_avg_win_pct": round(statistics.mean([p for p in pnl if p > 0]), 3)
                               if any(p > 0 for p in pnl) else None,
                               "trade_avg_loss_pct": round(statistics.mean([p for p in pnl if p <= 0]), 3)
                               if any(p <= 0 for p in pnl) else None}
            report[f"{symbol}_{tf}"] = row
    print(json.dumps(report, indent=1))
    open("output/fib-95-breakdown.json", "w").write(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
