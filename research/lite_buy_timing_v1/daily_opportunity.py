"""Does LITE offer +2-3% every day? Descriptive history only (not a rule, not a formula test).

  PYTHONPATH=src:. .venv/bin/python -m research.lite_buy_timing_v1.daily_opportunity

Per regular session (5-minute SIP bars, 2022-01 .. yesterday):
  - hindsight: best buy-low-then-sell-higher move inside the day (only knowable after the close)
  - from the open: did the high reach open +2% / +3%?
  - from 10:00 (9:55 bar close): did a later high reach +2% / +3%? Did +2% come before -2%?
    On days +2% never came, where did it close vs the 10:00 price?
  - "buy every day at 10:00, hold until +2%" (one position at a time): how many sales, how long held, worst dip.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import gzip
import json
from pathlib import Path
import statistics

from research.lite_buy_timing_v1.run import CACHE, bars, by_session, pct
from research.lite_paper_bot_v1.bot import credentials

OUT = Path("output/lite-daily-opportunity-20261002.json")


def day_row(day, session):
    rows = [r for _, r in session]
    open_ = rows[0]["o"]
    best, low_so_far = 0.0, float("inf")
    for r in rows:  # hindsight: buy at the lowest low so far, sell at a later high
        low_so_far = min(low_so_far, r["l"])
        best = max(best, r["h"] / low_so_far - 1)
    after = [(hm, r) for hm, r in session if hm >= "10:00"]
    entry = next((r["c"] for hm, r in session if hm == "09:55"), None)
    row = {"day": day, "hindsight_best": best, "open_to_high": max(r["h"] for r in rows) / open_ - 1}
    if entry and after:
        first_up = next((i for i, (_, r) in enumerate(after) if r["h"] >= entry * 1.02), None)
        first_down = next((i for i, (_, r) in enumerate(after) if r["l"] <= entry * 0.98), None)
        row.update({
            "entry_1000": entry,
            "from_1000_high": max(r["h"] for _, r in after) / entry - 1,
            "up2_before_down2": first_up is not None and (first_down is None or first_up < first_down),
            "close_vs_1000": after[-1][1]["c"] / entry - 1,
        })
    return row


def share(rows, test):
    return pct(sum(1 for r in rows if test(r)) / len(rows)) if rows else None


def summary(rows):
    tenam = [r for r in rows if "entry_1000" in r]
    missed2 = [r for r in tenam if r["from_1000_high"] < 0.02]
    return {
        "sessions": len(rows),
        "hindsight_best_move_2pct_plus": share(rows, lambda r: r["hindsight_best"] >= 0.02),
        "hindsight_best_move_3pct_plus": share(rows, lambda r: r["hindsight_best"] >= 0.03),
        "hindsight_best_move_median": pct(statistics.median(r["hindsight_best"] for r in rows)),
        "open_reached_plus2": share(rows, lambda r: r["open_to_high"] >= 0.02),
        "open_reached_plus3": share(rows, lambda r: r["open_to_high"] >= 0.03),
        "from_1000_reached_plus2_same_day": share(tenam, lambda r: r["from_1000_high"] >= 0.02),
        "from_1000_reached_plus3_same_day": share(tenam, lambda r: r["from_1000_high"] >= 0.03),
        "from_1000_plus2_came_before_minus2": share(tenam, lambda r: r["up2_before_down2"]),
        "when_plus2_missed_median_close_vs_1000": pct(statistics.median(r["close_vs_1000"] for r in missed2))
        if missed2 else None,
        "when_plus2_missed_worst_close_vs_1000": pct(min(r["close_vs_1000"] for r in missed2)) if missed2 else None,
    }


def buy_daily_hold_to_target(sessions, days, target=1.02):
    """Buy at 10:00 whenever flat; sell when a later high reaches entry*target. Descriptive only."""
    sales, held, worst, holding = [], [], 0.0, None
    longest = 0
    for day in days:
        session = sessions[day]
        if holding is None:
            entry = next((r["c"] for hm, r in session if hm == "09:55"), None)
            if entry is None:
                continue
            holding = {"entry": entry, "day": day, "days": 0}
            todays = [r for hm, r in session if hm >= "10:00"]
        else:
            todays = [r for _, r in session]
        holding["days"] += 1
        for r in todays:
            worst = min(worst, r["l"] / holding["entry"] - 1)
            if r["h"] >= holding["entry"] * target:
                sales.append(holding["day"])
                held.append(holding["days"])
                holding = None
                break
        if holding:
            longest = max(longest, holding["days"])
    return {"sales": len(sales), "sessions": len(days),
            "sales_per_week": round(len(sales) / (len(days) / 5), 2),
            "median_sessions_held": statistics.median(held) if held else None,
            "longest_sessions_held": max(held + [longest]) if held or longest else 0,
            "worst_dip_while_holding_pct": pct(worst),
            "still_holding_at_end": holding is not None}


def main():
    key, secret = credentials()
    now = datetime.now(timezone.utc)
    delayed = (now - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cached = json.loads(gzip.decompress((CACHE / "LITE_5min_sip_2022-01-01_2026-09-28.json.gz").read_bytes()))
    recent = bars("LITE", "5Min", "2026-09-29T00:00:00Z", delayed, key, secret, adjustment="raw")
    sessions = {d: s for d, s in by_session(cached + recent).items() if s and s[0][0] == "09:30"}
    today = now.date().isoformat()
    full = sorted(d for d in sessions if d < today and len(sessions[d]) >= 70)  # skip half days
    rows = [day_row(d, sessions[d]) for d in full]

    result = {
        "generated_utc": now.isoformat(timespec="seconds"),
        "boom_2025_26": summary([r for r in rows if r["day"] >= "2025-01-01"]),
        "stress_2022_24": summary([r for r in rows if r["day"] < "2025-01-01"]),
        "buy_every_day_hold_to_plus2_2025_26":
            buy_daily_hold_to_target(sessions, [d for d in full if d >= "2025-01-01"]),
        "buy_every_day_hold_to_plus2_2022_24":
            buy_daily_hold_to_target(sessions, [d for d in full if d < "2025-01-01"]),
        "today_so_far": day_row(today, sessions[today]) if today in sessions else None,
        "notes": ["Hindsight best move needs knowing the day's low and high in advance; nobody can trade it.",
                  "10:00 entry = close of the 9:55 five-minute bar. No fees or slippage.",
                  "Descriptive only. Turning any of this into a rule would be a new formula (parked until late Nov)."],
    }
    OUT.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
