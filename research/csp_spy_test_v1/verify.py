"""Independent checks for test #10.

1. Re-reads each trade's entry file and confirms the sale price is that put's bid (or mid) at 10:30.
2. Re-computes every trade's P&L and the whole cash path (premium, fees, settlement, T-bill interest) from the
   trade list alone, and confirms it lands on the backtest's final equity.
3. Cross-checks the put-call-parity SPY price used at settlement against Alpaca's actual raw SPY close
   (independent source) and reports how many trades would change outcome.

  PYTHONPATH=src:. .venv/bin/python -m research.csp_spy_test_v1.verify
"""
from __future__ import annotations

import csv
import gzip
import json
from datetime import date, timedelta

from research.lite_buy_timing_v1.run import bars
from research.lite_paper_bot_v1.bot import credentials
from research.spy_put_spread_backtest_v1.backtest import DATA, available_days, load_rates


def quote_at(day, expiration, strike):
    with gzip.open(DATA / day[:4] / f"{day}.csv.gz", "rt") as handle:
        for row in csv.DictReader(handle):
            if (row["window"] == "t1030" and row["type"] == "P" and row["expiration"] == expiration
                    and float(row["strike"]) == strike):
                return float(row["bid"]), float(row["ask"])
    return None


def main():
    out = json.load(open("output/csp-spy-test-results.json"))
    rates = load_rates()
    days = [d for d in available_days() if out["first"] <= d.isoformat() <= out["last"]]
    key, secret = credentials()
    raw = {b["t"][:10]: b["c"] for b in bars("SPY", "1Day", "2016-01-01T00:00:00Z", "2026-01-01T00:00:00Z",
                                              key, secret, adjustment="raw")}
    report = {}
    for name, res in out["results"].items():
        trades, mid = res["trade_list"], name.endswith("_mid")
        price_mismatch = 0
        if name in ("main_delta30_bid", "info_delta30_mid"):
            for t in trades:
                q = quote_at(t["entry_day"], t["expiration"], t["strike"])
                want = None if q is None else (q[1] + q[0]) / 2 if mid else q[0]
                price_mismatch += want is None or abs(want - t["sale_price"]) > 1e-9
        # Cash path from the trade list alone: interest daily on cash, premium in at entry, loss out at settlement.
        entries = {t["entry_day"]: t for t in trades}
        settles = {t["settle_day"]: t for t in trades}
        cash, prev, pnl_bad = 100_000.0, None, 0
        open_t = None
        for d in days:
            iso = d.isoformat()
            if prev is not None:
                cash += cash * rates.get(d.strftime("%Y-%m"), 0.0) * (d - prev).days / 365
            prev = d
            if iso in settles:
                t = settles[iso]
                loss = max(t["strike"] - t["settle_spot"], 0) * 100 * t["contracts"]
                pnl_bad += abs(t["premium"] - t["fees"] - loss - t["pnl"]) > 0.02
                cash -= loss
                open_t = None
            elif iso in entries:
                t = entries[iso]
                cash += t["sale_price"] * 100 * t["contracts"] - 0.03 * t["contracts"]
                open_t = t
        flips, diffs = 0, []
        for t in trades:
            real = raw.get(t["settle_day"])
            if real is None:
                continue
            diffs.append(abs(real - t["settle_spot"]))
            flips += (real >= t["strike"]) != (t["settle_spot"] >= t["strike"])
        diffs.sort()
        report[name] = {"trades": len(trades), "sale_price_mismatches": price_mismatch if name in
                        ("main_delta30_bid", "info_delta30_mid") else "not checked", "pnl_mismatches": pnl_bad,
                        "cash_path_final": round(cash), "backtest_final_equity": res["final_equity"],
                        "open_at_end": open_t is not None,
                        "parity_vs_actual_close_median_abs_usd": round(diffs[len(diffs) // 2], 3) if diffs else None,
                        "outcome_flips_using_actual_close": flips}
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
