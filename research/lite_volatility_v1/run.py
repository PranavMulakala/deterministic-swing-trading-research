"""How volatile is LITE vs other big stocks, and when in the day does it move? Descriptive only (not a rule).

  PYTHONPATH=src:. .venv/bin/python -m research.lite_volatility_v1.run

Part A: rank LITE among S&P 500 members and among all big, liquid US stocks ($300M+/day, $20+) by the last 252
trading days of daily moves (average absolute close-to-close change, annualized volatility, average high-low range).
Daily bars on disk (outputs/breakout_data, through the last file date).
Part B: LITE's trading day over the last year (Oct 3, 2025 - Oct 2, 2026), 5-minute SIP bars: how much it moves in
each half hour, when the day's high and low usually happen, and how big the swings are in the first three hours.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import gzip
import json
import math
from pathlib import Path
import statistics

from research.breakout_test_v1.backtest import DATA, load
from research.lite_buy_timing_v1.run import CACHE, bars, by_session, pct
from research.lite_paper_bot_v1.bot import credentials

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/lite-volatility-20261003.json"
FIRST_DAY, LAST_DAY = "2025-10-03", "2026-10-02"
BUCKETS = ["09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
           "15:00", "15:30"]


def daily_metrics(b):
    c, h, l, v = b["close"], b["high"], b["low"], b["volume"]
    n = len(c)
    if n < 260:
        return None
    rets = [c[i] / c[i - 1] - 1 for i in range(n - 252, n)]
    return {"price": c[-1], "last_date": b["date"][-1],
            "dollar_vol_m": sum(c[i] * v[i] for i in range(n - 60, n)) / 60 / 1e6,
            "avg_abs_daily_pct": 100 * statistics.mean(abs(r) for r in rets),
            "annual_vol_pct": 100 * statistics.stdev(rets) * math.sqrt(252),
            "avg_range_pct": 100 * statistics.mean((h[i] - l[i]) / c[i - 1] for i in range(n - 252, n)),
            "days_move_5pct_plus": sum(abs(r) >= 0.05 for r in rets)}


def part_a():
    sp = {row["symbol"] for row in json.loads((ROOT / "outputs/screener/sp500.json").read_text())}
    rows = []
    for path in sorted(DATA.glob("*.csv.gz")):
        sym = path.name[:-7]
        if not sym.replace("-", "").isalpha():
            continue
        try:
            m = daily_metrics(load(sym))
        except Exception:
            continue
        if m and m["price"] >= 20 and m["dollar_vol_m"] >= 300:
            rows.append({"symbol": sym, "sp500": sym in sp, **m})

    def rank(group, key):
        ordered = sorted(group, key=lambda r: -r[key])
        place = next((i + 1 for i, r in enumerate(ordered) if r["symbol"] == "LITE"), None)
        return {"rank": place, "of": len(ordered),
                "top_15": [(r["symbol"], round(r[key], 1)) for r in ordered[:15]],
                "median": round(statistics.median(r[key] for r in ordered), 2)}

    spx = [r for r in rows if r["sp500"]]
    lite = next(r for r in rows if r["symbol"] == "LITE")
    return {"data_through": lite["last_date"], "lite": {k: round(v, 2) if isinstance(v, float) else v
                                                         for k, v in lite.items()},
            "sp500_by_avg_abs_daily": rank(spx, "avg_abs_daily_pct"),
            "sp500_by_annual_vol": rank(spx, "annual_vol_pct"),
            "big_liquid_by_avg_abs_daily": rank(rows, "avg_abs_daily_pct"),
            "spy_qqq": {r["symbol"]: round(r["avg_abs_daily_pct"], 2) for r in rows if r["symbol"] in ("SPY", "QQQ")}}


def part_b():
    key, secret = credentials()
    cached = json.loads(gzip.decompress((CACHE / "LITE_5min_sip_2022-01-01_2026-09-28.json.gz").read_bytes()))
    end = (datetime.now(timezone.utc) - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent = bars("LITE", "5Min", "2026-09-29T00:00:00Z", end, key, secret, adjustment="raw")
    sessions = {d: s for d, s in by_session(cached + recent).items()
                if FIRST_DAY <= d <= LAST_DAY and s and s[0][0] == "09:30" and len(s) >= 70}
    bucket_move = {b: [] for b in BUCKETS}
    bucket_range = {b: [] for b in BUCKETS}
    bucket_volume = {b: [] for b in BUCKETS}
    high_at = {b: 0 for b in BUCKETS}
    low_at = {b: 0 for b in BUCKETS}
    first3_swing, up2_from_10, up3_from_10, down2_first, neither = [], 0, 0, 0, 0
    for day, s in sessions.items():
        day_volume = sum(r["v"] for _, r in s)
        for b in BUCKETS:
            end_b = (datetime.strptime(b, "%H:%M") + timedelta(minutes=30)).strftime("%H:%M")
            part = [r for hm, r in s if b <= hm < end_b]
            if not part:
                continue
            bucket_move[b].append(abs(part[-1]["c"] / part[0]["o"] - 1))
            bucket_range[b].append((max(r["h"] for r in part) - min(r["l"] for r in part)) / part[0]["o"])
            bucket_volume[b].append(sum(r["v"] for r in part) / day_volume)
        hi = max(s, key=lambda x: x[1]["h"])[0]
        lo = min(s, key=lambda x: x[1]["l"])[0]
        high_at[max(b for b in BUCKETS if b <= hi)] += 1
        low_at[max(b for b in BUCKETS if b <= lo)] += 1
        first3 = [r for hm, r in s if hm < "12:30"]
        first3_swing.append((max(r["h"] for r in first3) - min(r["l"] for r in first3)) / s[0][1]["o"])
        entry = next((r["c"] for hm, r in s if hm == "09:55"), None)
        window = [r for hm, r in s if "10:00" <= hm < "12:30"]
        if entry and window:
            up = next((i for i, r in enumerate(window) if r["h"] >= entry * 1.02), None)
            dn = next((i for i, r in enumerate(window) if r["l"] <= entry * 0.98), None)
            up2_from_10 += up is not None
            up3_from_10 += any(r["h"] >= entry * 1.03 for r in window)
            down2_first += dn is not None and (up is None or dn < up)
            neither += up is None and dn is None
    n = len(sessions)
    return {
        "sessions": n,
        "by_half_hour": {b: {"avg_abs_move_pct": pct(statistics.mean(bucket_move[b])),
                             "avg_range_pct": pct(statistics.mean(bucket_range[b])),
                             "share_of_day_volume_pct": pct(statistics.mean(bucket_volume[b])),
                             "day_high_here_pct": pct(high_at[b] / n), "day_low_here_pct": pct(low_at[b] / n)}
                         for b in BUCKETS},
        "first_3_hours": {
            "median_high_low_swing_pct": pct(statistics.median(first3_swing)),
            "swing_2pct_plus_days_pct": pct(sum(x >= 0.02 for x in first3_swing) / n),
            "swing_3pct_plus_days_pct": pct(sum(x >= 0.03 for x in first3_swing) / n),
            "swing_5pct_plus_days_pct": pct(sum(x >= 0.05 for x in first3_swing) / n),
            "buy_1000_hit_plus2_by_1230_pct": pct(up2_from_10 / n),
            "buy_1000_hit_plus3_by_1230_pct": pct(up3_from_10 / n),
            "buy_1000_hit_minus2_first_pct": pct(down2_first / n),
            "buy_1000_neither_by_1230_pct": pct(neither / n),
        },
    }


def main():
    result = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "part_a_rank": part_a(), "part_b_intraday": part_b(),
              "notes": ["Descriptive only. A time-of-day trading rule for LITE would be a new formula: parked until "
                        "the paper test ends (formula freeze)."]}
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
