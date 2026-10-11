"""Wheel candidate screen (research only, no returns of any strategy are computed here).

As of a date D, from daily bars on disk (`outputs/orb_play_data/daily`, Alpaca SIP, raw + split-adjusted, through
Oct 2, 2026; optionally topped up from Alpaca for the finalists), keep common stocks that are:
  - priced at or under $500 (raw close on D), and say whether under $250;
  - liquid: 60-day average dollar volume >= $200M;
  - in an uptrend: close > 50-day average > 200-day average (split-adjusted);
  - strong this year: return since the last close of the prior year >= +30%  (the "YTD" filter);
  - near the top: within 15% of the 252-day high.
Then rank by 60-day realized volatility (the LITE/MU-like movers pay the biggest weekly option fees) and report an
estimated weekly fee for a ~1-week 0.30-delta put: about 0.03 x annual volatility x strike (Black-Scholes, checked on
LITE/MU), shown per $50,000 of collateral. Realized volatility is not implied volatility; real quotes differ.

  PYTHONPATH=src:. .venv/bin/python -m research.wheel_screen_v1.screen --as-of 2025-12-31
  PYTHONPATH=src:. .venv/bin/python -m research.wheel_screen_v1.screen --as-of latest --options
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAILY = ROOT / "outputs/orb_play_data/daily"
FUND_WORDS = ("ETF", " FUND", "TRUST", "ETN", "PROSHARES", "DIREXION", "2X", "3X", " BULL", " BEAR", "ISHARES",
              "SPDR", "INVESCO QQQ", "VANECK", "GRANITESHARES", "LEVERAGE", "DAILY TARGET", "YIELDMAX", "TRADR")


def load(symbol):
    with gzip.open(DAILY / f"{symbol}.json.gz", "rt") as f:
        return json.load(f)


def metrics(d, as_of):
    dates = d["date"]
    idx = max((i for i, x in enumerate(dates) if x <= as_of), default=None)
    if idx is None or idx < 252 or dates[idx] < as_of[:8] + "01":   # need a year of history and a recent bar
        return None
    raw = d["raw"][idx]
    adj = [row[3] for row in d["split"][: idx + 1]]
    close, price = adj[-1], raw[3]
    sma50, sma200 = sum(adj[-50:]) / 50, sum(adj[-200:]) / 200
    year = as_of[:4]
    prior = max((i for i, x in enumerate(dates[: idx + 1]) if x[:4] < year), default=None)
    if prior is None:
        return None
    ytd = close / adj[prior] - 1
    hi = max(row[1] for row in d["split"][idx - 251: idx + 1])
    dollar_vol = sum(d["raw"][i][3] * d["raw"][i][4] for i in range(idx - 59, idx + 1)) / 60
    rets = [math.log(adj[i] / adj[i - 1]) for i in range(len(adj) - 60, len(adj))]
    mean = sum(rets) / len(rets)
    vol = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1) * 252)
    return {"date": dates[idx], "price": round(price, 2), "ytd_pct": round(100 * ytd, 1),
            "from_high_pct": round(100 * (close / hi - 1), 1), "above_50_200": close > sma50 > sma200,
            "dollar_vol_m": round(dollar_vol / 1e6), "vol_pct": round(100 * vol), "contract_cost": round(price * 100),
            "est_weekly_fee_per_50k": round(50_000 * 0.03 * vol)}


def latest_date():
    return load("SPY")["date"][-1] if (DAILY / "SPY.json.gz").exists() else load("AAPL")["date"][-1]


def passes(m):
    return (m and m["price"] <= 500 and m["dollar_vol_m"] >= 200 and m["above_50_200"] and m["ytd_pct"] >= 30
            and m["from_high_pct"] >= -15)


def names():
    """{symbol: name} for active US equities from Alpaca's asset list (used only to drop funds/ETFs)."""
    from research.forward_watch_v1.watch import get
    assets = get("https://paper-api.alpaca.markets/v2/assets?status=active&asset_class=us_equity")
    return {a["symbol"]: a.get("name") or "" for a in assets}


def weekly_expirations(symbol, start, end):
    from research.forward_watch_v1.watch import get
    exps, token = set(), None
    for _ in range(20):
        url = (f"https://paper-api.alpaca.markets/v2/options/contracts?underlying_symbols={symbol}&type=put"
               f"&expiration_date_gte={start}&expiration_date_lte={end}&limit=1000" + (f"&page_token={token}" if token else ""))
        r = get(url)
        exps |= {c["expiration_date"] for c in r.get("option_contracts", [])}
        token = r.get("next_page_token")
        if not token:
            break
    return sorted(exps)


def screen(as_of, top=25, with_names=True):
    nm = names() if with_names else {}
    rows = []
    for p in sorted(DAILY.glob("*.json.gz")):
        sym = p.name.split(".")[0]
        if with_names and (sym not in nm or any(w in nm[sym].upper() for w in FUND_WORDS)):
            continue
        m = metrics(load(sym), as_of)
        if passes(m):
            rows.append({"symbol": sym, "name": nm.get(sym, ""), **m})
    rows.sort(key=lambda r: (-r["vol_pct"], r["symbol"]))
    return rows[:top], len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True, help="YYYY-MM-DD, or 'latest' for the last date on disk")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--options", action="store_true", help="also count put expirations in the next ~3 weeks (Alpaca)")
    ap.add_argument("--start", default="2026-10-12")
    ap.add_argument("--end", default="2026-10-31")
    a = ap.parse_args()
    as_of = latest_date() if a.as_of == "latest" else a.as_of
    rows, n = screen(as_of, a.top)
    if a.options:
        for r in rows:
            r["expirations_next_3wk"] = len(weekly_expirations(r["symbol"], a.start, a.end))
    print(json.dumps({"as_of": a.as_of, "passed_filters": n, "top_by_volatility": rows}, indent=1))


if __name__ == "__main__":
    main()
