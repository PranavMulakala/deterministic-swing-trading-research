"""Find big, liquid stocks that have moved like LITE: a strong 1-2 year trend plus large daily swings. Research only.

  PYTHONPATH=src:. .venv/bin/python -m research.lite_like_screener_v1.screen [--output output/LITE_LIKE_SCREEN.md]

Reads the daily bars already on disk (outputs/breakout_data, Alpaca SIP, split/dividend adjusted, through the last
date in the files) and the S&P 500 list saved from Wikipedia (outputs/screener/sp500.json). Descriptive only: past
trend and volatility are not a forecast, and a screen built from winners is hindsight by construction.

Filters (all must hold):
- "Big and liquid": average daily dollar volume over the last 60 days of at least $300 million, and price >= $20.
- "Big sweeping moves": average daily range (high - low) / previous close over the last 60 days of at least 3%.
- "A strong trend": up at least 50% over the last 252 trading days.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.breakout_test_v1.backtest import DATA, load

ROOT = Path(__file__).resolve().parents[2]
MIN_DOLLAR_VOL_M, MIN_PRICE, MIN_RANGE_PCT, MIN_RET_1Y = 300.0, 20.0, 3.0, 50.0


def metrics(bars):
    o, h, l, c, v = bars["open"], bars["high"], bars["low"], bars["close"], bars["volume"]
    n = len(c)
    if n < 300:
        return None
    last60 = range(n - 60, n)
    year = range(n - 252, n)
    peak, worst = 0.0, 0.0
    for i in year:
        peak = max(peak, c[i])
        worst = min(worst, c[i] / peak - 1)
    dips = [i for i in year if l[i] <= o[i] * 0.99]
    return {
        "price": c[-1], "last_date": bars["date"][-1],
        "dollar_vol_60d_m": sum(c[i] * v[i] for i in last60) / 60 / 1e6,
        "range_60d_pct": 100 * sum((h[i] - l[i]) / c[i - 1] for i in last60) / 60,
        "gap_60d_pct": 100 * sum(abs(o[i] / c[i - 1] - 1) for i in last60) / 60,
        "ret_1y_pct": 100 * (c[-1] / c[n - 253] - 1),
        "ret_2y_pct": 100 * (c[-1] / c[n - 505] - 1) if n > 505 else None,
        "max_drop_1y_pct": 100 * worst,
        "dip_days_1y_pct": 100 * len(dips) / 252,  # days that traded 1%+ below the open at some point
        "dip_recovered_pct": 100 * sum(c[i] >= o[i] for i in dips) / len(dips) if dips else None,
    }


def screen():
    sp = {row["symbol"]: row for row in json.loads((ROOT / "outputs/screener/sp500.json").read_text())}
    rows = []
    for path in sorted(DATA.glob("*.csv.gz")):
        sym = path.name[:-7]
        if not sym.replace("-", "").isalpha():
            continue
        try:
            m = metrics(load(sym))
        except Exception:
            continue
        if m and m["price"] >= MIN_PRICE and m["dollar_vol_60d_m"] >= MIN_DOLLAR_VOL_M:
            info = sp.get(sym, {})
            rows.append({"symbol": sym, "sp500": sym in sp, "name": info.get("name", ""),
                         "industry": info.get("industry", ""), **m})
    picks = [r for r in rows if r["range_60d_pct"] >= MIN_RANGE_PCT and r["ret_1y_pct"] >= MIN_RET_1Y]
    return sorted(picks, key=lambda r: -r["ret_1y_pct"]), len(rows)


def markdown(picks, liquid):
    f = lambda x, d=0: "n/a" if x is None else f"{x:,.{d}f}"
    head = ("| # | Stock | S&P 500 | Industry | Price | 1-yr | 2-yr | Avg daily range | Avg open gap | "
            "Worst drop (1 yr) | $ volume/day | 1%+ dip days | Dips that closed ≥ open |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    lines = [head]
    for i, r in enumerate(picks, 1):
        lines.append(f"| {i} | **{r['symbol']}** {r['name']} | {'yes' if r['sp500'] else 'no'} | {r['industry'] or '-'} | "
                     f"${f(r['price'], 2)} | {f(r['ret_1y_pct'])}% | {f(r['ret_2y_pct'])}% | {f(r['range_60d_pct'], 1)}% | "
                     f"{f(r['gap_60d_pct'], 1)}% | {f(r['max_drop_1y_pct'])}% | ${f(r['dollar_vol_60d_m'])}M | "
                     f"{f(r['dip_days_1y_pct'])}% | {f(r['dip_recovered_pct'])}% |")
    return (f"{len(picks)} of {liquid} big, liquid stocks (price ≥ $20, ≥ $300M traded a day) passed: up ≥ 50% in a year "
            f"and an average daily range ≥ 3%.\n\n" + "\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args()
    picks, liquid = screen()
    text = markdown(picks, liquid)
    if args.output:
        Path(args.output).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
