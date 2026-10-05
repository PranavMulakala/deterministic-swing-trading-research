"""65% SPY / 35% T-bills comparison check (output/MIX_65_35_CHECK_PLAN_20261005.md). Research only, no network.

  PYTHONPATH=src:. .venv/bin/python -m research.mix_65_35_v1.run

Uses the same trading days, dividend-adjusted SPY closes and T-bill rates as test #10 (cash-secured puts).
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from research.breakout_test_v1.backtest import load as load_daily
from research.csp_spy_test_v1.backtest import FIRST, LAST, halves, stats_for
from research.provenance_v1.provenance import write_manifest
from research.spy_put_spread_backtest_v1.backtest import available_days, load_rates

OUT = Path("output/mix-65-35-check.json")
SPY_WEIGHT, START = 0.65, 100_000.0


def run(days, close, rates, rebalance):
    """rebalance: 'monthly', 'yearly' or 'never'. Returns the daily value curve [(iso, value)]."""
    shares = START * SPY_WEIGHT / close[days[0]]
    cash = START * (1 - SPY_WEIGHT)
    curve, prev = [], None
    for d in days:
        if prev is not None:
            cash += cash * rates.get(d.strftime("%Y-%m"), 0.0) * (d - prev).days / 365
        value = shares * close[d] + cash
        first_of_month = prev is not None and d.month != prev.month
        if (rebalance == "monthly" and first_of_month) or (rebalance == "yearly" and prev is not None
                                                           and d.year != prev.year):
            shares, cash = value * SPY_WEIGHT / close[d], value * (1 - SPY_WEIGHT)
        curve.append((d.isoformat(), value))
        prev = d
    return curve


def main():
    rates = load_rates()
    spy = load_daily("SPY")
    close = {date.fromisoformat(d): c for d, c in zip(spy["date"], spy["close"])}
    days = [d for d in available_days() if FIRST <= d <= LAST]
    missing = [d.isoformat() for d in days if d not in close]
    days = [d for d in days if d in close]
    years = len(days) / 252
    out = {"plan": "output/MIX_65_35_CHECK_PLAN_20261005.md", "first": days[0].isoformat(),
           "last": days[-1].isoformat(), "days": len(days), "spy_missing_days": missing, "results": {}}
    for name in ("monthly", "yearly", "never"):
        curve = run(days, close, rates, name)
        by_year, last = {}, START
        for y in sorted({d[:4] for d, _ in curve}):
            end = [v for d, v in curve if d[:4] == y][-1]
            by_year[y] = round((end / last - 1) * 100, 1)
            last = end
        out["results"][f"mix_65_35_{name}"] = {**stats_for([("start", START)] + curve, years),
                                               "final_value": round(curve[-1][1]), "halves_return_pct": halves(curve),
                                               "return_by_year_pct": by_year}
    spy_curve = [(d.isoformat(), START * close[d] / close[days[0]]) for d in days]
    out["results"]["spy_only"] = {**stats_for([("start", START)] + spy_curve, years), "final_value": round(spy_curve[-1][1])}
    csp = json.load(open("output/csp-spy-test-results.json"))["results"]["main_delta30_bid"]
    out["results"]["cash_secured_puts_test10"] = {k: csp[k] for k in ("final_equity", "cagr_pct", "max_drawdown_pct",
                                                                      "cagr_over_dd", "halves_return_pct")}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    write_manifest(OUT, code=["research/mix_65_35_v1/run.py"],
                   data=["outputs/breakout_data/SPY.csv.gz", "research/spy_put_spread_backtest_v1/tbill_3m_monthly.csv",
                         "output/csp-spy-test-results.json"], params={"spy_weight": SPY_WEIGHT})
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
