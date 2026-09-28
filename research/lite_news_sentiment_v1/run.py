"""Pre-declared test: does skipping LITE dip buys on bearish-news mornings help? Research only; no orders.

Plan (committed before any news was pulled): output/LITE_NEWS_SENTIMENT_TEST_PLAN_20260928.md
  PYTHONPATH=src:. .venv/bin/python -m research.lite_news_sentiment_v1.run

News: Alpha Vantage LITE articles cached in outputs/lite_news_history/ (gitignored third-party text).
Each morning's reading is the paper bot's own (research/lite_paper_bot_v1/news.py). Trades are the
history replay (research/lite_dip_history_v1/run.py) with SIP signals and $60,000 per buy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, time as dtime
from decimal import Decimal
import json
from pathlib import Path

from research.lite_dip_history_v1.run import FIRST, LAST, cached, history, regular, replay, scan, summarize
from research.lite_paper_bot_v1.bot import BUY_BUFFER, CENT, TARGET_MULTIPLIER, credentials, evaluate, mornings
from research.lite_paper_bot_v1.news import NY, score, window

ROOT = Path(__file__).resolve().parents[2]
NEWS = ROOT / "outputs/lite_news_history"
PERIODS = {"main_2025_2026": ("2025-01-01", LAST), "stress_2022_2024": ("2022-03-01", "2024-12-31")}
CUTOFF = Decimal("-0.15")  # Somewhat-Bearish or worse
D = lambda value: Decimal(str(value))


def readings(feed, days):
    """The bot's 10:00 reading for every session day."""
    return {day: score(feed, *window(datetime.combine(datetime.fromisoformat(day).date(), dtime(10, 5), NY)))
            for day in days}


def bucket(reading):
    if not reading.get("articles"):
        return "no news"
    value = D(reading["score"])
    return "bearish" if value <= CUTOFF else "bullish" if value >= Decimal("0.15") else "neutral"


def forward(day, days, sip, sessions=5):
    """A hypothetical 10:00 buy: was the +2% sale reached within `sessions` days, and the worst drop before it."""
    index = days.index(day)
    reference = next((opening for clock, opening, *_ in sip.get(day, []) if clock == "10:00"), None)
    if reference is None:
        return None
    fill = (reference * BUY_BUFFER).quantize(CENT)
    held = {"fill": fill, "low": fill, "target": (fill * TARGET_MULTIPLIER).quantize(CENT, rounding="ROUND_UP")}
    for offset, later in enumerate(days[index:index + sessions]):
        if scan(held, sip.get(later, []), "10:05" if offset == 0 else "09:30"):
            return {"hit": True, "worst_pct": float((held["low"] / fill - 1) * 100)}
    return {"hit": False, "worst_pct": float((held["low"] / fill - 1) * 100)}


def describe(signal_days, marks, days, sip):
    groups = {}
    for day in signal_days:
        outcome = forward(day, days, sip)
        if outcome:
            groups.setdefault(bucket(marks[day]), []).append(outcome)
    table = {}
    for name in ("bearish", "neutral", "bullish", "no news"):
        rows = groups.get(name, [])
        worst = sorted(row["worst_pct"] for row in rows)
        table[name] = {"signal_days": len(rows),
                       "hit_2pct_within_5_days": f"{sum(row['hit'] for row in rows)} of {len(rows)}",
                       "median_worst_drop_pct": round(worst[len(worst) // 2], 1) if worst else None}
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/lite-news-sentiment-test.json")
    args = parser.parse_args()
    feed = [article for name in ("2022_2024", "2025", "2026")
            for article in json.loads((NEWS / f"lite_{name}.json").read_text())]
    key, secret = credentials()
    calendar = cached(f"calendar_{FIRST}_{LAST}.json.gz", lambda: None)
    closes = {row["date"]: row["close"] for row in calendar if row["open"] == "09:30"}
    days = sorted(closes)
    rows = history("sip", key, secret)
    sip = regular(rows, closes)
    signals = {day: evaluate(bars, []) for day, bars in mornings(rows).items() if day in closes}
    marks = readings(feed, days)
    filtered = {day: ({**result, "signal": False} if marks[day].get("articles") and D(marks[day]["score"]) <= CUTOFF
                      else result) for day, result in signals.items()}
    report = {"articles": len(feed), "periods": {}}
    for name, (start, end) in PERIODS.items():
        window_days = [day for day in days if start <= day <= end]
        signal_days = [day for day in window_days if signals.get(day, {}).get("signal")]
        base, news = summarize(replay(signals, sip, window_days)), summarize(replay(filtered, sip, window_days))
        report["periods"][name] = {
            "from": window_days[0], "to": window_days[-1], "sessions": len(window_days),
            "mornings_with_any_news": sum(bool(marks[day].get("articles")) for day in window_days),
            "signal_days": len(signal_days),
            "signal_days_with_any_news": sum(bool(marks[day].get("articles")) for day in signal_days),
            "signal_days_skipped_by_filter": sum(not filtered[day]["signal"] for day in signal_days),
            "skipped_days": [day for day in signal_days if not filtered[day]["signal"]],
            "without_filter": base, "with_filter": news,
            "descriptive_by_morning_news": describe(signal_days, marks, days, sip)}
    main_, stress = report["periods"]["main_2025_2026"], report["periods"]["stress_2022_2024"]
    checks = {
        "1_smaller_worst_drop_in_both_periods": all(
            p["with_filter"]["worst_drop_from_peak_marked"] > p["without_filter"]["worst_drop_from_peak_marked"]
            for p in (main_, stress)),
        "2_main_realized_down_no_more_than_10pct":
            main_["with_filter"]["realized_pnl"] >= Decimal("0.9") * main_["without_filter"]["realized_pnl"],
        "3_stress_marked_end_no_worse":
            stress["with_filter"]["marked_pnl_at_end"] >= stress["without_filter"]["marked_pnl_at_end"]}
    report["pre_declared_checks"] = checks
    report["news_filter_helped"] = all(checks.values())
    Path(args.output).write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
