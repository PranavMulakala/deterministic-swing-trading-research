"""Code check from the SMA50 plan: does our backtest reproduce the video's Bitcoin numbers? Not part of any verdict.

  PYTHONPATH=src:. .venv/bin/python -m research.sma50_test_v1.bitcoin_check

Video setup [0:55-1:00]: BTC/USD Bitstamp daily, $10,000, full equity, long only, trades from May 15, 2015,
0% and 0.1% commission per side. Writes output/sma50-bitcoin-check.json.
The video's "today" is taken as 2026-07-09: our Bitstamp close that day is $63,185.92, and the video reads the
live price as $63,187 [0:22]. Every day from 2026-06-03 to 2026-07-13 gives the same trade results.
"""
from __future__ import annotations

import json

from research.breakout_test_v1.backtest import load
from research.sma50_test_v1.backtest import ROOT, max_drawdown, simulate

VIDEO = {"net_profit_no_cost": 5_854_816, "net_profit_0.1pct": 4_796_186, "trades": 100,
         "win_rate_pct_no_cost": 30, "win_rate_pct_0.1pct": 29, "profit_factor_no_cost": 2.28,
         "profit_factor_0.1pct": 2.12, "max_drawdown_pct_0.1pct": -53.7, "buy_hold_return_pct": 26_876}


def run(bars, cost):
    trades, curve = simulate(bars, cost=cost, start=10_000.0)
    wins = [t for t in trades if t["pnl"] > 0]
    gain, loss = sum(t["pnl"] for t in wins), -sum(t["pnl"] for t in trades if t["pnl"] <= 0)
    return {"net_profit": round(curve[-1][1] - 10_000), "trades": len(trades),
            "open_at_end": any(t.get("open_at_end") for t in trades),
            "win_rate_pct": round(100 * len(wins) / len(trades), 1), "profit_factor": round(gain / loss, 2),
            "max_drawdown_pct": round(100 * max_drawdown(curve), 1)}


def main():
    btc = load("BTCUSD_BITSTAMP")
    start = btc["date"].index("2015-05-15") - 50  # keep 50 earlier closes so the first fill is on May 15, 2015
    ours = {}
    for name, last in (("video_window_to_2026-07-09", "2026-07-09"), ("to_2026-09-28_info", btc["date"][-1])):
        end = btc["date"].index(last) + 1
        bars = {k: v[start:end] for k, v in btc.items()}
        ours[name] = {"no_cost": run(bars, 0.0), "0.1pct": run(bars, 0.001),
                      "buy_hold_return_pct": round(100 * (bars["close"][-1] / bars["open"][50] - 1)),
                      "first_fill_day": bars["date"][50], "last_day": bars["date"][-1]}
    out = {"video": VIDEO, "ours": ours}
    (ROOT / "output/sma50-bitcoin-check.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
