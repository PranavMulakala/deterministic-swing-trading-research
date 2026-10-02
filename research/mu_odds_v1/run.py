"""MU: odds of reaching $1,200 (and of falling to the sell-note levels) by December. Descriptive only.

  PYTHONPATH=src:. .venv/bin/python -m research.mu_odds_v1.run

Two independent views:
  1. History: from every MU close, how often did the price touch +X% / -Y% within N trading days?
     (2025-26 boom, 2016-24, all of 2016-26.) Horizons: 47 trading days (to Dec 9) and 53 (to about Dec 17).
  2. Options: what today's MU option prices imply (Alpaca indicative feed, free). Finishing above a strike is read
     from call spreads; the chance of touching a level is roughly twice the chance of finishing above it.
     Option prices are "risk-neutral": they bake in investors' fear premium, so read them as the market's
     priced-in odds, not a forecast.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import statistics
import urllib.parse

from research.lite_buy_timing_v1.run import bars, pct
from research.lite_dip_history_v1.run import DATA, fetch
from research.lite_paper_bot_v1.bot import credentials

OUT = Path("output/mu-odds-20261002.json")
BUY = 1079.08
TARGET = 1200.0
HORIZONS = {"to_dec_9": 47, "to_dec_17": 53}


def history(daily, first, last, horizon, start_price):
    up = TARGET / start_price - 1
    rows = []
    for i, b in enumerate(daily):
        if not (first <= b["t"][:10] <= last) or i + horizon >= len(daily):
            continue
        c = b["c"]
        future = daily[i + 1:i + horizon + 1]
        hit_up = next((k for k, f in enumerate(future) if f["h"] >= c * (1 + up)), None)
        hit_l20 = next((k for k, f in enumerate(future) if f["l"] <= c * 0.80), None)
        rows.append({
            "touch_up": hit_up is not None,
            "close_above_at_end": future[-1]["c"] >= c * (1 + up),
            "touch_minus10": any(f["l"] <= c * 0.90 for f in future),
            "touch_minus20": hit_l20 is not None,
            "up_before_minus20": hit_up is not None and (hit_l20 is None or hit_up < hit_l20),
            "end_return": future[-1]["c"] / c - 1,
            "worst_low": min(f["l"] for f in future) / c - 1,
        })
    n = len(rows)
    share = lambda key: pct(sum(r[key] for r in rows) / n)
    ends = sorted(r["end_return"] for r in rows)
    return {"start_days": n, "needed_rise_pct": pct(up),
            "touched_target_pct": share("touch_up"), "closed_above_target_at_end_pct": share("close_above_at_end"),
            "touched_minus10_pct": share("touch_minus10"), "touched_minus20_pct": share("touch_minus20"),
            "target_before_minus20_pct": share("up_before_minus20"),
            "median_worst_dip_pct": pct(statistics.median(r["worst_low"] for r in rows)),
            "end_return_p10_p50_p90_pct": [pct(ends[int(q * (n - 1))]) for q in (0.1, 0.5, 0.9)]}


def chain(key, secret, expiry, lo, hi):
    query = {"feed": "indicative", "expiration_date": expiry, "strike_price_gte": lo, "strike_price_lte": hi,
             "limit": 1000}
    snaps = fetch(f"{DATA}/v1beta1/options/snapshots/MU?{urllib.parse.urlencode(query)}", key, secret).get("snapshots") or {}
    out = {}
    for symbol, s in snaps.items():
        q = s.get("latestQuote") or {}
        if not (q.get("ap") and q.get("bp")):
            continue
        kind = "call" if symbol[-9] == "C" else "put"
        strike = int(symbol[-8:]) / 1000
        out.setdefault(strike, {})[kind] = {"mid": (q["ap"] + q["bp"]) / 2, "iv": s.get("impliedVolatility"),
                                             "delta": (s.get("greeks") or {}).get("delta")}
    return out


def implied(key, secret, expiry, spot, days_to_expiry):
    opts = chain(key, secret, expiry, 700, 1500)
    strikes = sorted(k for k, v in opts.items() if "call" in v)

    def finish_above(level):  # call-spread "digital": (C(k1) - C(k2)) / (k2 - k1) around the level
        below = max((k for k in strikes if k <= level), default=None)
        above = min((k for k in strikes if k > level), default=None)
        if below is None or above is None:
            return None
        return (opts[below]["call"]["mid"] - opts[above]["call"]["mid"]) / (above - below)

    def finish_below(level):
        puts = sorted(k for k, v in opts.items() if "put" in v)
        below = max((k for k in puts if k < level), default=None)
        above = min((k for k in puts if k >= level), default=None)
        if below is None or above is None:
            return None
        return (opts[above]["put"]["mid"] - opts[below]["put"]["mid"]) / (above - below)

    atm = min(strikes, key=lambda k: abs(k - spot))
    straddle = opts[atm]["call"]["mid"] + opts.get(atm, {}).get("put", {}).get("mid", float("nan"))
    iv = opts[atm]["call"]["iv"]
    years = days_to_expiry / 365
    result = {"expiry": expiry, "atm_strike": atm, "atm_iv_pct": pct(iv) if iv else None,
              "straddle_implied_move_pct": pct(straddle / spot) if straddle == straddle else None,
              "one_sigma_range": [round(spot * math.exp(-iv * math.sqrt(years))), round(spot * math.exp(iv * math.sqrt(years)))]
              if iv else None}
    for name, level in (("1200", TARGET), ("buy_minus10", BUY * 0.9), ("buy_minus20", BUY * 0.8)):
        p = finish_above(level) if name == "1200" else finish_below(level)
        result[f"finish_{'above' if name == '1200' else 'below'}_{name}_pct"] = pct(p) if p is not None else None
        result[f"touch_{name}_approx_pct"] = pct(min(1.0, 2 * p)) if p is not None else None
    return result


def main():
    key, secret = credentials()
    now = datetime.now(timezone.utc)
    delayed = (now - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
    daily = [b for b in bars("MU", "1Day", "2015-01-01", delayed, key, secret) if b["t"][:10] < now.date().isoformat()]
    spot = fetch(f"{DATA}/v2/stocks/MU/trades/latest?feed=iex", key, secret)["trade"]["p"]
    last_full = daily[-1]["t"][:10]

    result = {"generated_utc": now.isoformat(timespec="seconds"), "spot": spot, "buy": BUY, "target": TARGET,
              "history": {}, "options": {}}
    for name, n in HORIZONS.items():
        result["history"][name] = {
            "boom_2025_26": history(daily, "2025-01-01", last_full, n, spot),
            "stress_2016_24": history(daily, "2016-01-01", "2024-12-31", n, spot),
            "all_2016_26": history(daily, "2016-01-01", last_full, n, spot),
        }
    today = now.date()
    for expiry in ("2026-11-20", "2026-12-18"):
        days = (datetime.fromisoformat(expiry).date() - today).days
        try:
            result["options"][expiry] = implied(key, secret, expiry, spot, days)
        except Exception as error:  # report, don't hide
            result["options"][expiry] = {"error": repr(error)}
    result["notes"] = ["History: overlapping start days, not independent samples; the boom window is one long rally.",
                       "Options: Dec 18 expiry comes after Micron's mid-December earnings, so it includes that move.",
                       "Descriptive only. Not a forecast, not advice."]
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
