"""Offline descriptive LITE study, not a trading simulation or sentiment model.

Run from repository root:
  .venv/bin/python -m research.lite_ytd_movement.analyze
Add --daily to include all session observations. No files, network or credentials
are written/accessed except the explicitly named historical cache/config inputs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from statistics import mean, median

from research.lite_execution_data.study import load_bars

ROOT = Path(__file__).resolve().parents[2]


def pct(value, reference):
    return 100 * (value / reference - 1)


def at_least(value, reference, percent):
    """Inclusive threshold comparison without binary float boundary drift."""
    return Decimal(str(value)) >= Decimal(str(reference)) * (1 + Decimal(str(percent)) / 100)


def at_most(value, reference, percent):
    return Decimal(str(value)) <= Decimal(str(reference)) * (1 + Decimal(str(percent)) / 100)


def describe_session(day, bars):
    if tuple(b.minute for b in bars) != tuple(range(570, 960, 5)):
        raise ValueError("Need exactly 78 ordered regular-session bars")
    opening, reference, close = bars[0].o, bars[6].o, bars[-1].c
    high, low = max(b.h for b in bars), min(b.l for b in bars)
    early_low = min(b.l for b in bars[:6])
    later = bars[6:]
    touch = next((b for b in later if b.h >= opening), None)
    return dict(date=day, opening=opening, close=close, high=high, low=low,
        ten_am_reference=reference, close_vs_open_pct=pct(close, opening),
        range_vs_open_pct=100*(high-low)/opening,
        high_vs_open_pct=pct(high, opening), low_vs_open_pct=pct(low, opening),
        early_low_vs_open_pct=pct(early_low, opening),
        opening_dip_1pct=at_most(early_low, opening, -1),
        below_open_at_ten=reference < opening,
        ten_to_close_pct=pct(close, reference),
        later_high=max(b.h for b in later), later_low=min(b.l for b in later),
        touched_open_after_ten=touch is not None,
        first_touch_bar_start=touch.timestamp.isoformat() if touch else None,
        touch_time_precision="within_five_minute_bar_not_an_execution",
        above_open_at_close=close >= opening,
        sentiment="unknown")


def rate(count, denominator):
    return dict(count=count, denominator=denominator,
                pct=100*count/denominator if denominator else None)


def group_summary(rows):
    n = len(rows)
    if not n:
        return dict(n=0)
    moves = [r["close_vs_open_pct"] for r in rows]
    dips = [r for r in rows if r["opening_dip_1pct"]]
    still_down = [r for r in dips if r["below_open_at_ten"]]
    return dict(n=n,
        close_above_open=rate(sum(r["close"] > r["opening"] for r in rows), n),
        close_below_open=rate(sum(r["close"] < r["opening"] for r in rows), n),
        close_equal_open=rate(sum(r["close"] == r["opening"] for r in rows), n),
        mean_close_vs_open_pct=mean(moves), median_close_vs_open_pct=median(moves),
        median_range_vs_open_pct=median(r["range_vs_open_pct"] for r in rows),
        worst_open_to_close=min(rows, key=lambda r:r["close_vs_open_pct"]),
        best_open_to_close=max(rows, key=lambda r:r["close_vs_open_pct"]),
        thresholds=[dict(threshold_pct=k,
            high_at_least=rate(sum(at_least(r["high"], r["opening"], k) for r in rows), n),
            low_at_most=rate(sum(at_most(r["low"], r["opening"], -k) for r in rows), n),
            both=rate(sum(at_least(r["high"], r["opening"], k) and
                          at_most(r["low"], r["opening"], -k) for r in rows), n),
            close_at_least=rate(sum(at_least(r["close"], r["opening"], k) for r in rows), n),
            close_at_most=rate(sum(at_most(r["close"], r["opening"], -k) for r in rows), n))
            for k in (1,2,3,5)],
        opening_dips=rate(len(dips), n),
        dip_touched_open_after_ten=rate(sum(r["touched_open_after_ten"] for r in dips), len(dips)),
        dip_closed_at_or_above_open=rate(sum(r["above_open_at_close"] for r in dips), len(dips)),
        dip_still_below_open_at_ten=len(still_down),
        still_down_touched_open=rate(sum(r["touched_open_after_ten"] for r in still_down),len(still_down)),
        still_down_not_touched_dates=[r["date"] for r in still_down if not r["touched_open_after_ten"]],
        dip_mean_ten_to_close_pct=mean(r["ten_to_close_pct"] for r in dips) if dips else None,
        dip_positive_ten_to_close=rate(sum(r["ten_to_close_pct"]>0 for r in dips),len(dips)),
        dip_rise_from_ten=[dict(threshold_pct=k,
            reached=rate(sum(at_least(r["later_high"],r["ten_am_reference"],k) for r in dips),len(dips)))
            for k in (1,2,3,5)])


def later_recovery(rows):
    """Raw price-level touches, NOT independent trades or an investable ledger.

    Fixed-horizon rates exclude every origin lacking the full observation window,
    even when it recovered early, to avoid outcome-dependent censoring.
    """
    observations=[]
    for i, day in enumerate(rows):
        if not (day["opening_dip_1pct"] and day["below_open_at_ten"]):
            continue
        target=day["opening"]
        offset=next((j-i for j in range(i,len(rows))
                     if (rows[j]["later_high"] if j==i else rows[j]["high"]) >= target), None)
        observations.append(dict(date=day["date"],raw_target=target,
            first_touch_session_offset=offset, subsequent_sessions_observed=len(rows)-1-i,
            first_touch_date=rows[i+offset]["date"] if offset is not None else None))
    horizons=[]
    for h in (0,1,5,20):
        eligible=[r for r in observations if r["subsequent_sessions_observed"]>=h]
        hits=sum(r["first_touch_session_offset"] is not None and r["first_touch_session_offset"]<=h
                 for r in eligible)
        horizons.append(dict(subsequent_sessions=h,full_window_rate=rate(hits,len(eligible)),
                             excluded_short_windows=len(observations)-len(eligible)))
    return dict(n=len(observations),fixed_horizons=horizons,
        unresolved_at_snapshot_end=[r for r in observations if r["first_touch_session_offset"] is None],
        slowest_observed=sorted((r for r in observations if r["first_touch_session_offset"] is not None),
                              key=lambda r:r["first_touch_session_offset"],reverse=True)[:5],
        limitations=["Overlapping signal dates are not independently fundable positions.",
            "Raw price levels only: corporate-action and dividend accounting not reconciled for multi-day holdings.",
            "Only regular-session highs checked, not overnight or extended-hours target touches.",
            "Unresolved means not observed by September 4, not proof of never recovering.",
            "No fills, downside path, cash occupation or costs simulated; not a no-stop backtest."],
        observations=observations)


def analyze():
    old = ROOT/"research/lite_2026/snapshot.json"
    cfg = json.loads((ROOT/"research/lite_reversal_v1/config.json").read_text())
    raw = old.read_bytes()
    if hashlib.sha256(raw).hexdigest() != cfg["snapshot_sha256"]:
        raise ValueError("Pinned calendar/news snapshot hash mismatch")
    snapshot = json.loads(raw)
    data_dir = ROOT/"research/lite_execution_data/runs/sip-bars-01"
    manifest = json.loads((data_dir/"manifest.json").read_text())
    source = data_dir/"LITE_5Min.json"
    expected = next(f["sha256"] for f in manifest["files"] if f["file"] == source.name)
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError("Pinned SIP bar hash mismatch")
    bars, coverage = load_bars(source,"LITE",5,snapshot["calendar"])
    rows = [describe_session(day, bs) for day,bs in sorted(bars.items())]
    news = {str(a["id"]):a for a in snapshot["news"]}
    return dict(status="EXPLORATORY_PRICE_ONLY_NOT_A_BACKTEST",
        source=str(source.relative_to(ROOT)), coverage=coverage,
        calendar_news_sha256=cfg["snapshot_sha256"],
        analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        start=rows[0]["date"], through=rows[-1]["date"],
        assumptions=["Raw SIP regular-hours 5-minute bars; close is last bar close, not 15:55 open or official auction close.",
            "High/low excursions can both occur on one day and do not establish which came first.",
            "10:00 open is a descriptive reference, not an assumed executable decision-time fill.",
            "Target is the 09:30 open, not a user-specified guaranteed sell price.",
            "No spreads, costs, sizing, capital constraints or trading P&L simulated.",
            "Full-day completeness is a retrospective coverage filter, not a live selection rule.",
            "Already-seen 2026 data; single-name selection; observed frequencies are not forecasts."],
        summary=group_summary(rows),
        later_regular_session_raw_price_recovery=later_recovery(rows),
        by_month={m:group_summary([r for r in rows if r["date"][:7]==m]) for m in sorted({r["date"][:7] for r in rows})},
        news=dict(cached_records=len(snapshot["news"]),unique_ids=len(news),
            sources=dict(Counter(a["source"] for a in news.values())),
            revised_after_creation=sum(a["updated_at"]!=a["created_at"] for a in news.values()),
            original_text_present=False,first_received_at_present=False,
            sentiment_status="BLOCKED_DATA: metadata is not sentiment; all session labels unknown"),
        daily=rows)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily", action="store_true")
    args=parser.parse_args()
    result=analyze()
    if not args.daily:
        result.pop("daily")
    print(json.dumps(result,indent=2,allow_nan=False))
