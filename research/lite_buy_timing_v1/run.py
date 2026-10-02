"""LITE: buy now or wait for a dip? Descriptive history only (not a trading rule, not a formula test).

  PYTHONPATH=src:. .venv/bin/python -m research.lite_buy_timing_v1.run

Answers three questions with free Alpaca SIP data (LITE paper account's read-only keys; places no orders):
  1. If I wait for LITE to fall X% below today's price, how often does that dip come within 20 / 60 trading
     days, and what happens to me when it doesn't? (2025-26 boom window, plus 2016-24 as a stress window.)
  2. Same question, only on days LITE closed within 3% of its 52-week high (today's situation).
  3. Days shaped like today's open: fell >=1% below the open by 9:55, then was back above the open at 9:55.
     What did the rest of the day and the next 1 / 5 days do? (5-minute bars, 2022-26.)
Plus a summary of today's 1-minute bars.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import gzip
import json
from pathlib import Path
import statistics
import urllib.parse
from zoneinfo import ZoneInfo

from research.lite_dip_history_v1.run import CACHE, DATA, fetch
from research.lite_paper_bot_v1.bot import credentials

NY = ZoneInfo("America/New_York")
OUT = Path("output/lite-buy-timing-20261002.json")
DIPS = (3, 5, 10, 15, 20)


def bars(symbol, timeframe, start, end, key, secret, adjustment="all"):
    rows, token = [], None
    while True:
        query = {"timeframe": timeframe, "feed": "sip", "adjustment": adjustment, "sort": "asc", "limit": 10000,
                 "start": start, "end": end}
        if token:
            query["page_token"] = token
        page = fetch(f"{DATA}/v2/stocks/{symbol}/bars?{urllib.parse.urlencode(query)}", key, secret)
        rows += page.get("bars") or []
        token = page.get("next_page_token")
        if not token:
            return rows


def pct(x):
    return round(100 * x, 1)


def wait_table(daily, first, last, horizon, near_high_only=False):
    """For each close in [first, last] with `horizon` days of future: does the low reach close*(1-dip)?"""
    closes = [b["c"] for b in daily]
    out = {}
    starts = []
    for i, b in enumerate(daily):
        day = b["t"][:10]
        if not (first <= day <= last) or i + horizon >= len(daily):
            continue
        if near_high_only:
            year = closes[max(0, i - 251):i + 1]
            if closes[i] < 0.97 * max(year):
                continue
        starts.append(i)
    for dip in DIPS:
        hit_days, miss_returns, buy_now, wait_result = [], [], [], []
        for i in starts:
            ref, limit = closes[i], closes[i] * (1 - dip / 100)
            end_close = closes[i + horizon]
            now_return = end_close / ref - 1
            buy_now.append(now_return)
            hit = next((k for k in range(1, horizon + 1) if daily[i + k]["l"] <= limit), None)
            if hit is None:
                miss_returns.append(now_return)
                wait_result.append(0.0)  # never bought: sat in cash
            else:
                hit_days.append(hit)
                wait_result.append(end_close / limit - 1)
        n = len(starts)
        out[f"-{dip}%"] = {
            "start_days": n,
            "dip_came_pct": pct(len(hit_days) / n) if n else None,
            "median_days_to_dip": statistics.median(hit_days) if hit_days else None,
            "when_missed_median_lite_move_pct": pct(statistics.median(miss_returns)) if miss_returns else None,
            "buy_now_avg_return_pct": pct(statistics.mean(buy_now)) if n else None,
            "wait_avg_return_pct": pct(statistics.mean(wait_result)) if n else None,
            "wait_beat_buy_now_pct_of_days": pct(sum(w > b for w, b in zip(wait_result, buy_now)) / n) if n else None,
        }
    return out


def ny(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(NY)


def by_session(rows):
    days = {}
    for r in rows:
        t = ny(r["t"])
        if (t.hour, t.minute) < (9, 30) or t.hour >= 16:
            continue
        days.setdefault(t.date().isoformat(), []).append((t.strftime("%H:%M"), r))
    return days


def opening_shape(sessions, daily_close):
    """Days that dipped >=1% below the open before 9:55, then closed the 9:50 bar at or above the open."""
    names = sorted(sessions)
    matches, everyone = [], []
    for j, day in enumerate(names):
        bars_ = sessions[day]
        if not bars_ or bars_[0][0] != "09:30":
            continue
        open_ = bars_[0][1]["o"]
        early = [r for hm, r in bars_ if hm < "09:55"]
        at_955 = next((r["c"] for hm, r in bars_ if hm == "09:50"), None)
        at_1100 = next((r["c"] for hm, r in bars_ if hm == "10:55"), None)
        close = bars_[-1][1]["c"]
        if at_955 is None or at_1100 is None or day not in daily_close:
            continue
        later = [d for d in sorted(daily_close) if d > day]
        if len(later) < 5:
            continue
        row = {"day": day,
               "rest_of_day_from_11am": close / at_1100 - 1,
               "next_day_close": daily_close[later[0]] / close - 1,
               "five_day_close": daily_close[later[4]] / close - 1,
               "low_after_11am_vs_11am": min(r["l"] for hm, r in bars_ if hm >= "11:00") / at_1100 - 1
               if any(hm >= "11:00" for hm, _ in bars_) else 0.0}
        everyone.append(row)
        if min(r["l"] for r in early) <= open_ * 0.99 and at_955 >= open_:
            matches.append(row)

    def summary(rows):
        if not rows:
            return {"days": 0}
        return {
            "days": len(rows),
            "rest_of_day_up_pct": pct(sum(r["rest_of_day_from_11am"] > 0 for r in rows) / len(rows)),
            "rest_of_day_median_pct": pct(statistics.median(r["rest_of_day_from_11am"] for r in rows)),
            "fell_2pct_below_11am_price_later_that_day_pct":
                pct(sum(r["low_after_11am_vs_11am"] <= -0.02 for r in rows) / len(rows)),
            "next_day_up_pct": pct(sum(r["next_day_close"] > 0 for r in rows) / len(rows)),
            "next_day_median_pct": pct(statistics.median(r["next_day_close"] for r in rows)),
            "five_day_up_pct": pct(sum(r["five_day_close"] > 0 for r in rows) / len(rows)),
            "five_day_median_pct": pct(statistics.median(r["five_day_close"] for r in rows)),
        }

    boom = [r for r in matches if r["day"] >= "2025-01-01"]
    return {"all_days_2022_26": summary(everyone),
            "all_days_2025_26": summary([r for r in everyone if r["day"] >= "2025-01-01"]),
            "today_shape_2022_26": summary(matches),
            "today_shape_2025_26": summary(boom),
            "today_shape_dates_2025_26": [r["day"] for r in boom]}


def today_summary(minute):
    rows = [r for hm, r in minute]
    open_, last = rows[0]["o"], rows[-1]["c"]
    hi = max(rows, key=lambda r: r["h"])
    lo = min(rows, key=lambda r: r["l"])
    volume = sum(r["v"] for r in rows)
    vwap = sum(r["vw"] * r["v"] for r in rows) / volume
    return {"bars": len(rows), "first": minute[0][0], "last": minute[-1][0], "open": open_,
            "high": hi["h"], "high_at": ny(hi["t"]).strftime("%H:%M"),
            "low": lo["l"], "low_at": ny(lo["t"]).strftime("%H:%M"),
            "last": last, "vwap": round(vwap, 2), "volume": volume,
            "last_vs_open_pct": pct(last / open_ - 1), "range_pct": pct(hi["h"] / lo["l"] - 1)}


def main():
    key, secret = credentials()
    now = datetime.now(timezone.utc)
    delayed = (now - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")  # free plan: SIP needs >15 min delay
    today = now.astimezone(NY).date().isoformat()

    daily = [b for b in bars("LITE", "1Day", "2015-01-01", delayed, key, secret) if b["t"][:10] < today]
    daily_close = {b["t"][:10]: b["c"] for b in daily}
    last_full = daily[-1]["t"][:10]
    year_high = max(b["c"] for b in daily[-252:])

    cached_5m = json.loads(gzip.decompress((CACHE / "LITE_5min_sip_2022-01-01_2026-09-28.json.gz").read_bytes()))
    recent_5m = bars("LITE", "5Min", "2026-09-29T00:00:00Z", f"{today}T00:00:00Z", key, secret, adjustment="raw")
    sessions = by_session(cached_5m + recent_5m)

    minute = by_session(bars("LITE", "1Min", f"{today}T13:30:00Z", delayed, key, secret, adjustment="raw")).get(today, [])

    result = {
        "generated_utc": now.isoformat(timespec="seconds"),
        "last_full_session": last_full,
        "last_close": daily[-1]["c"],
        "close_52wk_high": year_high,
        "last_close_vs_52wk_high_pct": pct(daily[-1]["c"] / year_high - 1),
        "today_1min_delayed_16min": today_summary(minute) if minute else None,
        "waiting_for_dip": {
            "boom_2025_26_within_20d": wait_table(daily, "2025-01-01", last_full, 20),
            "boom_2025_26_within_60d": wait_table(daily, "2025-01-01", last_full, 60),
            "boom_2025_26_near_52wk_high_within_20d": wait_table(daily, "2025-01-01", last_full, 20, True),
            "stress_2016_24_within_20d": wait_table(daily, "2016-01-01", "2024-12-31", 20),
            "stress_2016_24_near_52wk_high_within_20d": wait_table(daily, "2016-01-01", "2024-12-31", 20, True),
        },
        "opening_shape": opening_shape(sessions, daily_close),
        "notes": ["Entry price in the dip tables is each day's close; 'wait' buys exactly at the dip price the "
                  "first day the low touches it and holds to the horizon, otherwise stays in cash (0%).",
                  "Overlapping start days: these are not independent samples.",
                  "Descriptive only. Not a rule, not a recommendation."],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
