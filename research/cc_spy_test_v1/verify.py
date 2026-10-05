"""Independent check for test #13: rebuild the cash + share path from the saved buy list and call list (plus
interest and dividends recomputed here), then compare with the backtest's final equity. Also confirms each call's
sale price equals that strike's 10:30 bid in the raw file.

  PYTHONPATH=src:. .venv/bin/python -m research.cc_spy_test_v1.verify
"""
from __future__ import annotations

import csv
import gzip
import json
from datetime import date

from research.cc_spy_test_v1.backtest import dividends_per_share
from research.spy_put_spread_backtest_v1.backtest import DATA, available_days, load_day, load_rates, parity_spot


def bid_at(day, expiration, strike):
    with gzip.open(DATA / day[:4] / f"{day}.csv.gz", "rt") as handle:
        for row in csv.DictReader(handle):
            if row["window"] == "t1030" and row["type"] == "C" and row["expiration"] == expiration \
                    and float(row["strike"]) == strike:
                return float(row["bid"])
    return None


def main():
    out = json.load(open("output/cc-spy-test-results.json"))
    res = out["results"]["main_delta30_bid"]
    days = [d for d in available_days() if out["first"] <= d.isoformat() <= out["last"]]
    rates, divs = load_rates(), dividends_per_share(days)
    buys = {b["day"]: b for b in res["buy_list"]}
    sells = {t["entry_day"]: t for t in res["trade_list"]}
    settles = {t["settle_day"]: t for t in res["trade_list"]}
    cash, shares, prev = 100_000.0, 0, None
    for d in days:
        iso = d.isoformat()
        if prev:
            cash += cash * rates.get(d.strftime("%Y-%m"), 0.0) * (d - prev).days / 365
        prev = d
        cash += shares * divs.get(iso, 0.0)
        if iso in settles and settles[iso]["called_away"]:
            t = settles[iso]
            cash += t["strike"] * 100 * t["contracts"]
            shares -= 100 * t["contracts"]
        if iso in buys:
            cash -= buys[iso]["shares"] * buys[iso]["price"]
            shares += buys[iso]["shares"]
        if iso in sells:
            cash += sells[iso]["premium"] - sells[iso]["fees"]
    # open call at the end (sold after the last settlement), if any: not in trade_list
    last = days[-1]
    snap = load_day(DATA / str(last.year) / f"{last.isoformat()}.csv.gz")
    spot = parity_spot(snap["close"], last, rates.get(last.strftime("%Y-%m"), 0.0), 0)
    bad_bids = sum(abs((bid_at(t["entry_day"], t["expiration"], t["strike"]) or -1) - t["sale_price"]) > 1e-9
                   for t in res["trade_list"])
    print(json.dumps({"rebuilt_cash_plus_shares_before_open_call": round(cash + shares * spot),
                      "backtest_final_equity": res["final_equity"], "shares_end": shares,
                      "calls_checked": len(res["trade_list"]), "sale_price_mismatches": bad_bids,
                      "note": "difference = the last open call (sold after the final settlement): its premium is in "
                              "the backtest cash and its mark is subtracted"}, indent=1))


if __name__ == "__main__":
    main()
