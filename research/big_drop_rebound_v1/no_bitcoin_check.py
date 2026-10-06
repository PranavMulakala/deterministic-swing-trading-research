"""Test #19, written AFTER the result (Oct 6), information only.

outputs/breakout_data/ also holds two bitcoin price files (BTCUSD, BTCUSD_BITSTAMP, saved there on Sep 30). Test #19's
universe read every file in the folder, so bitcoin counted as a "stock": 3 qualifying drops and 2 trades. This re-runs
the unchanged rule without them.

  PYTHONPATH=src:. .venv/bin/python -m research.big_drop_rebound_v1.no_bitcoin_check
"""
from __future__ import annotations

import json

from research.big_drop_rebound_v1.backtest import (DATA, HALVES, MAIN, ROOT, STRESS, evaluate, events, load, prepare)

NOT_STOCKS = {"SPY", "BTCUSD", "BTCUSD_BITSTAMP"}


def main():
    stocks = {p.name[:-7]: prepare(load(p.name[:-7])) for p in sorted(DATA.glob("*.csv.gz")) if p.name[:-7] not in NOT_STOCKS}
    spy = load("SPY")
    main_evts = events(stocks, MAIN)
    res, spy_main, trades, _ = evaluate(main_evts, stocks, spy["date"], MAIN, HALVES["main"], spy)
    stress, _, _, _ = evaluate(events(stocks, STRESS), stocks, spy["date"], STRESS, HALVES["stress"], spy)
    keys = ("final", "cagr_pct", "max_drawdown_pct", "cagr_over_dd", "halves_return_pct", "trades", "profit_factor_incl_open",
            "win_rate_pct", "checks", "passes")
    out = {"note": "after the result, information only: bitcoin files excluded", "events": len(main_evts),
           "main": {k: res[k] for k in keys}, "spy_main": spy_main,
           "stress": {k: stress[k] for k in ("final", "cagr_pct", "max_drawdown_pct", "passes")}}
    (ROOT / "output/big-drop-rebound-no-bitcoin-check.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
