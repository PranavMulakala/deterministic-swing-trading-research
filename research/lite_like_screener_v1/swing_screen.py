"""Big stocks that swing about as much as LITE each day, regardless of trend (descriptive only; not a buy list).

  PYTHONPATH=src:. .venv/bin/python -m research.lite_like_screener_v1.swing_screen

Daily bars on disk (outputs/breakout_data, through the last date in the files); last 60 trading days.
"Big": average dollar volume >= $300M a day and price >= $10, common stocks only (Alpaca asset names, one read-only
request). "Swings like LITE": average absolute daily close-to-close move >= 4% (LITE: 4.9%). Writes
output/volatile-stocks-screen-20261005.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import statistics

from research.breakout_test_v1.backtest import DATA, load

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/volatile-stocks-screen-20261005.json"
MIN_DOLLAR_VOL_M, MIN_PRICE, MIN_MOVE_PCT, WINDOW = 300.0, 10.0, 4.0, 60
THEMES = {
    "AI chips, optics, memory and servers (the LITE/MU bet)":
        ["AXTI", "AAOI", "SNDK", "CRDO", "SMTC", "ALAB", "COHR", "TSEM", "MRVL", "DELL", "ARM", "SMCI"],
    "AI cloud and data centers (many are ex-bitcoin miners)": ["NBIS", "CRWV", "IREN", "CIFR", "HUT", "WULF", "APLD", "DOCN"],
    "Crypto": ["MARA", "RIOT", "MSTR", "CRCL", "BMNR"],
    "Power for AI": ["BE", "OKLO"],
    "Quantum and space": ["QBTS", "ASTS"],
    "Health and biotech": ["MRNA", "TEM", "HIMS"],
    "Software": ["HUBS", "TEAM"],
}


def metrics(b):
    c, h, l, v = b["close"], b["high"], b["low"], b["volume"]
    n = len(c)
    w = range(n - WINDOW, n)
    moves = [abs(c[i] / c[i - 1] - 1) for i in w]
    peak, worst = 0.0, 0.0
    for i in range(n - 252, n):
        peak = max(peak, c[i])
        worst = min(worst, c[i] / peak - 1)
    return {"avg_move_pct": round(100 * statistics.mean(moves), 2),
            "days_5pct_plus_pct": round(100 * sum(m >= 0.05 for m in moves) / WINDOW),
            "avg_range_pct": round(100 * sum((h[i] - l[i]) / c[i - 1] for i in w) / WINDOW, 2),
            "dollar_vol_m": round(sum(c[i] * v[i] for i in w) / WINDOW / 1e6),
            "ret_1y_pct": round(100 * (c[-1] / c[n - 253] - 1)), "worst_drop_1y_pct": round(100 * worst),
            "price": round(c[-1], 2), "last_date": b["date"][-1]}


def main():
    from research.lite_dip_history_v1.run import PAPER, fetch
    from research.lite_paper_bot_v1.bot import credentials
    from research.smallcap_scanner_v1.scanner import is_common_stock
    key, secret = credentials()
    assets = {a["symbol"]: a for a in fetch(f"{PAPER}/v2/assets?status=active&asset_class=us_equity", key, secret)}
    big = {}
    for path in sorted(DATA.glob("*.csv.gz")):
        s = path.name[:-7]
        a = assets.get(s)
        if s == "SPY" or not a or not is_common_stock(a):
            continue
        b = load(s)
        if len(b["close"]) < 260:
            continue
        m = metrics(b)
        if m["dollar_vol_m"] >= MIN_DOLLAR_VOL_M and m["price"] >= MIN_PRICE and m["last_date"] >= "2026-09-25":
            big[s] = {**m, "name": a.get("name", "")}
    swing = {s: m for s, m in big.items() if m["avg_move_pct"] >= MIN_MOVE_PCT}
    theme_of = {s: t for t, syms in THEMES.items() for s in syms}
    others = [s for s in swing if s != "LITE"]
    out = {"big_stocks": len(big), "median_avg_move_pct": round(statistics.median(m["avg_move_pct"] for m in big.values()), 2),
           "lite": big.get("LITE"), "lite_like_count_excl_lite": len(others),
           "up_1y": sum(swing[s]["ret_1y_pct"] > 0 for s in others),
           "median_ret_1y_pct": statistics.median(swing[s]["ret_1y_pct"] for s in others),
           "median_worst_drop_1y_pct": statistics.median(swing[s]["worst_drop_1y_pct"] for s in others),
           "worst_drop_40_plus": sum(swing[s]["worst_drop_1y_pct"] <= -40 for s in others),
           "unthemed": sorted(s for s in others if s not in theme_of),
           "stocks": {s: {**m, "theme": theme_of.get(s)} for s, m in sorted(swing.items(), key=lambda kv: -kv[1]["avg_move_pct"])}}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "stocks"}, indent=1))


if __name__ == "__main__":
    main()
