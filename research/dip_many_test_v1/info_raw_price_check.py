"""INFORMATION ONLY (written after test #15's results were seen): how much did the split-adjusted price filter bend the
universe? universe.py applied "close >= $20 on Dec 31, 2021" to split-ADJUSTED prices, so stocks that later did reverse
splits (often after collapsing) looked expensive and passed, and stocks that later did forward splits (often after
rising) looked cheap and were dropped. Both are hindsight, and both work against the rule.

This script re-applies the $20 filter to RAW Dec 31, 2021 closes (known at the time) and reports:
  1. the corrected top-100 universe and how it differs from the one tested;
  2. the unchanged portfolio backtest on (tested universe minus names whose raw price was under $20), i.e. no refill.
The official verdict stays the pre-declared one. Nothing about the rule changes.

  PYTHONPATH=src:. .venv/bin/python -m research.dip_many_test_v1.info_raw_price_check
"""
from __future__ import annotations

import json
from pathlib import Path
import time
import urllib.parse

from research.breakout_test_v1.backtest import DATA as DAILY, load as load_daily
from research.dip_many_test_v1 import backtest as bt
from research.dip_many_test_v1.universe import CUTOFF, LOOKBACK, MIN_DOLLAR_VOL, MIN_PRICE, TOP_N
from research.lite_dip_history_v1.run import DATA, fetch
from research.lite_paper_bot_v1.bot import credentials

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/dip-many-test-info-raw-price.json"


def split_invariant_candidates():
    """Everything universe.py checks except the price filter (dollar volume and range don't change with splits)."""
    rows = []
    for s in json.loads((DAILY / "universe.json").read_text()):
        if s == "SPY" or not (DAILY / f"{s}.csv.gz").exists():
            continue
        b = load_daily(s)
        idx = [i for i, d in enumerate(b["date"]) if d <= CUTOFF]
        if len(idx) < LOOKBACK + 1 or b["date"][idx[-1]] < "2021-12-20":
            continue
        t = idx[-1]
        w = range(t - LOOKBACK + 1, t + 1)
        dollar = sum(b["close"][i] * b["volume"][i] for i in w) / LOOKBACK
        if dollar < MIN_DOLLAR_VOL:
            continue
        rng = sum((b["high"][i] - b["low"][i]) / b["close"][i - 1] for i in w) / LOOKBACK
        rows.append({"symbol": s, "adj_close": round(b["close"][t], 2), "avg_range_pct": round(100 * rng, 2),
                     "last_date": b["date"][t]})
    return rows


def raw_closes(symbols, key, secret, batch=100):
    out = {}
    for i in range(0, len(symbols), batch):
        q = {"symbols": ",".join(symbols[i:i + batch]), "timeframe": "1Day", "start": "2021-12-20T00:00:00Z",
             "end": "2022-01-01T00:00:00Z", "adjustment": "raw", "feed": "sip", "limit": 10000}
        token = None
        while True:
            if token:
                q["page_token"] = token
            page = fetch(f"{DATA}/v2/stocks/bars?{urllib.parse.urlencode(q)}", key, secret)
            for sym, bars in (page.get("bars") or {}).items():
                for b in bars:
                    if b["t"][:10] <= CUTOFF:
                        out[sym] = (b["t"][:10], b["c"])   # last bar on/before the cutoff (bars are ascending)
            token = page.get("next_page_token")
            time.sleep(0.4)
            if not token:
                break
    return out


def main():
    key, secret = credentials()
    tested = json.loads((bt.HERE / "universe.json").read_text())
    tested_syms = [r["symbol"] for r in tested["main"]]
    cands = split_invariant_candidates()
    raw = raw_closes(sorted(r["symbol"] for r in cands), key, secret)
    for r in cands:
        d, c = raw.get(r["symbol"], (None, None))
        r["raw_close"], r["raw_date"] = c, d
    missing_raw = [r["symbol"] for r in cands if r["raw_close"] is None]
    eligible = [r for r in cands if r["raw_close"] is not None and r["raw_close"] >= MIN_PRICE]
    corrected = [r["symbol"] for r in sorted(eligible, key=lambda r: -r["avg_range_pct"])[:TOP_N]]
    by_sym = {r["symbol"]: r for r in cands}
    dropped = [s for s in tested_syms if s not in corrected]
    added = [s for s in corrected if s not in tested_syms]
    under_20 = [s for s in tested_syms if (by_sym.get(s, {}).get("raw_close") or 0) < MIN_PRICE]

    # Unchanged backtest on the tested universe minus names whose raw price was under $20 (no refill).
    spy_days = bt.load("SPY")
    calendar = sorted(spy_days)
    from research.lite_buy_timing_v1.run import bars as alpaca_bars
    daily = {r["t"][:10]: r["c"] for r in alpaca_bars("SPY", "1Day", "2021-12-31T00:00:00Z", "2026-10-01T00:00:00Z",
                                                      key, secret, adjustment="all")}
    base = daily[max(d for d in daily if d < calendar[0])]
    spy_curve = [(d, bt.START_CASH * daily[d] / base) for d in calendar if d in daily]
    subset = [s for s in tested_syms if s not in under_20]
    res = bt.run(subset, spy_curve, calendar)
    out = {"note": "INFORMATION ONLY, written after the official results; the pre-declared verdict stands",
           "candidates_split_invariant": len(cands), "missing_raw_price": missing_raw,
           "eligible_with_raw_price_filter": len(eligible),
           "tested_but_raw_price_under_20": [{"symbol": s, "adj_close": by_sym[s]["adj_close"],
                                              "raw_close": by_sym[s]["raw_close"]} for s in under_20],
           "corrected_top100_dropped": dropped, "corrected_top100_added": [
               {"symbol": s, "adj_close": by_sym[s]["adj_close"], "raw_close": by_sym[s]["raw_close"],
                "avg_range_pct": by_sym[s]["avg_range_pct"]} for s in added],
           "corrected_top100": corrected,
           "subset_backtest": {"stocks": len(subset), "portfolio": res["portfolio"], "checks": res["checks"],
                               "passes": res["passes"], "spy": res["spy"],
                               "profitable": res["stocks_profitable_unconstrained"],
                               "stuck_at_end": [t for t in res["trade_list"] if t["open"]]}}
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("corrected_top100",)}, indent=1, default=str))


if __name__ == "__main__":
    main()
