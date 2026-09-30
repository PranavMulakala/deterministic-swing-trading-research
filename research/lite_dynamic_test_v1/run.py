"""Replay of the pre-declared LITE dynamic-rule test (output/LITE_DYNAMIC_TEST_PLAN_20260930.md). Research only.

  PYTHONPATH=src:. .venv/bin/python -m research.lite_dynamic_test_v1.run

Reads the cached LITE five-minute bars and calendar in outputs/lite_history/ (no network) and writes
output/lite-dynamic-test-results.json. One bar-by-bar engine runs all five versions; version 0 must match
research/lite_dip_history_v1's replay exactly (plan check 1).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import ROUND_HALF_UP, ROUND_UP, Decimal
import gzip
import json
from pathlib import Path

from research.breakout_test_v1.backtest import load as load_daily
from research.lite_dip_history_v1.run import CACHE, FIRST, LAST, WINDOWS, D, regular, replay, summarize
from research.lite_paper_bot_v1.bot import BUY_BUFFER, CENT, TARGET_MULTIPLIER, evaluate, mornings

ROOT = Path(__file__).resolve().parents[2]
TICKET, TRAIL, SLIP, DIP = Decimal("60000"), Decimal("0.99"), Decimal("0.999"), Decimal("0.99")
TIERS = ((Decimal("-3"), Decimal("80000")), (Decimal("-2"), Decimal("60000")), (Decimal("-1"), Decimal("40000")))
VERSIONS = {"0_baseline": ("fixed", "target", "flat"), "1_first_hour": ("turn", "target", "flat"),
            "2_let_winners_run": ("fixed", "trail", "flat"), "3_bigger_dip_bigger_buy": ("fixed", "target", "tiered"),
            "4_all_three": ("turn", "trail", "tiered")}
PUBLISHED = {"year_2026": (79946, 59), "year_2025": (38403, 28)}  # realized $, sales in LITE_DIP_BOT_HISTORY_20260928.md
cents = lambda value: value.quantize(CENT, rounding=ROUND_HALF_UP)


def ticket_for(dip_pct, sizing):
    """Rule 3: dollars to spend, from how far the morning low was below the open (dip_pct is negative)."""
    if sizing == "flat":
        return TICKET
    return next((dollars for floor, dollars in TIERS if dip_pct <= floor), TIERS[-1][1])


def turn_trigger(bars):
    """Rule 1: index of the first 09:35-10:25 bar that closes above the prior bar's high after a 1% dip,
    while still below the open; returns (index, dip_pct at that bar) or None."""
    if not bars or bars[0][0] != "09:30":
        return None
    opening, low = bars[0][1], bars[0][3]
    for i in range(1, len(bars)):
        clock, _, _, bar_low, close = bars[i]
        low = min(low, bar_low)
        if clock > "10:25":
            break
        if low <= opening * DIP and close > bars[i - 1][2] and close < opening:
            return i, (low / opening - 1) * 100
    return None


def check_exit(held, bar, exit_mode, through):
    """Returns the sale price if this bar sells the holding, else None. Updates the holding's low/arm/peak."""
    clock, opening, high, low, _ = bar
    held["low"] = min(held["low"], low)
    if exit_mode == "target":
        if high >= held["target"] * (1 + through):  # a gap above the target at the open sells at the open
            return max(opening, held["target"]) if clock == "09:30" else held["target"]
        return None
    if held["armed"]:  # rule 2: only the level set by earlier bars can trigger
        level = held["peak"] * TRAIL
        if opening <= level:
            return cents(opening * SLIP)
        if low <= level:
            return cents(level * SLIP)
        held["peak"] = max(held["peak"], high)
    elif high >= held["target"]:
        held["armed"], held["peak"] = True, high
    return None


def simulate(signals, sip, days, version, through=Decimal(0)):
    """signals: date -> evaluate() of the six morning bars (missing when incomplete). One engine for all versions."""
    entry_mode, exit_mode, sizing = VERSIONS[version]
    held, trades, daily, counts, realized, dollar_days = None, [], [], defaultdict(int), Decimal(0), Decimal(0)
    for index, day in enumerate(days):
        bars = sip.get(day, [])
        result, bought_today, buy_at = signals.get(day), False, None
        if entry_mode == "fixed":
            if result is None:
                counts["no_data"] += 1
            elif result["signal"]:
                counts["signals"] += 1
                buy_at = ("10:00", D(result["dip_pct"]), D(result["close_0955"]))
        else:
            found = turn_trigger(bars)
            if found and found[0] + 1 < len(bars):
                counts["signals"] += 1
                buy_at = (bars[found[0] + 1][0], found[1], None)
        for bar in bars:
            clock, opening = bar[0], bar[1]
            if buy_at and clock == buy_at[0] and not bought_today:
                bought_today = True  # the decision is made once, at this bar's open
                if held:
                    counts["skipped_holding"] += 1
                elif buy_at[2] is not None and abs(opening / buy_at[2] - 1) > Decimal("0.02"):
                    counts["no_price"] += 1
                else:
                    fill = cents(opening * BUY_BUFFER)
                    held = {"entry_day": day, "index": index, "fill": fill, "low": fill, "armed": False, "peak": None,
                            "shares": int(ticket_for(buy_at[1], sizing) / fill),
                            "target": (fill * TARGET_MULTIPLIER).quantize(CENT, rounding=ROUND_UP)}
                    counts["buys"] += 1
                    continue  # exits are checked from the bar after the entry bar
            if held:
                price = check_exit(held, bar, exit_mode, through)
                if price is not None:
                    pnl = (price - held["fill"]) * held["shares"]
                    realized += pnl
                    trades.append({**held, "exit_day": day, "exit_time": clock, "exit": price, "pnl": pnl,
                                   "sessions": index - held["index"] + 1})
                    held = None
        if buy_at and entry_mode == "fixed" and not bought_today and result and result["signal"]:
            counts["skipped_holding" if held else "no_price"] += 1  # no 10:00 bar that day
        unrealized = (bars[-1][4] - held["fill"]) * held["shares"] if held and bars else Decimal(0)
        dollar_days += held["fill"] * held["shares"] if held else Decimal(0)
        daily.append({"day": day, "realized": realized, "equity": realized + unrealized, "holding": bool(held)})
    return {"trades": trades, "daily": daily, "counts": dict(counts), "open": held, "dollar_days": dollar_days}


def load_inputs():
    read = lambda name: json.loads(gzip.decompress((CACHE / name).read_bytes()))
    calendar = read(f"calendar_{FIRST}_{LAST}.json.gz")
    closes = {row["date"]: row["close"] for row in calendar if row["open"] == "09:30"}
    rows = read(f"LITE_5min_sip_{FIRST}_{LAST}.json.gz")
    signals = {day: evaluate(bars, []) for day, bars in mornings(rows).items() if day in closes}
    return sorted(closes), regular(rows, closes), signals


def benchmarks(sip, window):
    start = next(opening for clock, opening, *_ in sip[window[0]] if clock == "10:00")
    lite = int((TICKET / start) * sip[window[-1]][-1][4] - TICKET)
    spy = load_daily("SPY")
    at = {d: i for i, d in enumerate(spy["date"])}
    spy_pnl = int(60000 / spy["open"][at[window[0]]] * spy["close"][at[window[-1]]] - 60000)
    return {"hold_60k_LITE_pnl": lite, "hold_60k_SPY_pnl": spy_pnl}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/lite-dynamic-test-results.json")
    args = parser.parse_args()
    days, sip, signals = load_inputs()
    report = {"plan": "output/LITE_DYNAMIC_TEST_PLAN_20260930.md", "windows": {}, "versions": {}}
    original = {}
    for name, (start, end) in WINDOWS.items():
        window = [day for day in days if start <= day <= end]
        report["windows"][name] = {"from": window[0], "to": window[-1], **benchmarks(sip, window)}
        original[name] = summarize(replay(signals, sip, window))
    for version in VERSIONS:
        report["versions"][version] = {}
        for name, (start, end) in WINDOWS.items():
            window = [day for day in days if start <= day <= end]
            result = simulate(signals, sip, window, version)
            row = summarize(result)
            row["marked_pnl_per_1000_dollar_days"] = (round(float(Decimal(row["marked_pnl_at_end"]) /
                                                                   (result["dollar_days"] / 1000)), 3)
                                                      if result["dollar_days"] else None)
            strict = summarize(simulate(signals, sip, window, version, through=Decimal("0.001")))
            row["strict_sale_marked_pnl_at_end"] = strict["marked_pnl_at_end"]
            report["versions"][version][name] = row
    base = report["versions"]["0_baseline"]
    same = lambda a, b: all(a[k] == b[k] for k in ("realized_pnl", "sales", "marked_pnl_at_end", "buys"))
    report["engine_checks"] = {
        "1a_original_replay_matches_published": {w: (original[w]["realized_pnl"], original[w]["sales"]) == PUBLISHED[w]
                                                 for w in PUBLISHED},
        "1b_version_0_matches_original_replay": {w: same(base[w], original[w]) for w in WINDOWS}}
    report["verdicts"] = {}
    for version in list(VERSIONS)[1:]:
        v = report["versions"][version]
        checks = {"1_more_profit_2025": v["year_2025"]["marked_pnl_at_end"] > base["year_2025"]["marked_pnl_at_end"],
                  "2_more_profit_2026": v["year_2026"]["marked_pnl_at_end"] > base["year_2026"]["marked_pnl_at_end"],
                  "3_worst_drop_within_10pct": v["boom_2025_2026"]["worst_drop_from_peak_marked"]
                  >= 1.1 * base["boom_2025_2026"]["worst_drop_from_peak_marked"],
                  "4_stress_within_5000": v["stress_2022_2024"]["marked_pnl_at_end"]
                  >= base["stress_2022_2024"]["marked_pnl_at_end"] - 5000}
        report["verdicts"][version] = {**checks, "beats_baseline": all(checks.values())}
    (ROOT / args.output).write_text(json.dumps(report, indent=1, default=str) + "\n")
    keep = ("buys", "sales", "realized_pnl", "marked_pnl_at_end", "strict_sale_marked_pnl_at_end",
            "weeks_realized_1000_plus", "weeks", "average_realized_per_week", "longest_run_of_weeks_without_a_sale",
            "worst_drop_from_peak_marked", "marked_pnl_per_1000_dollar_days")
    brief = {v: {w: {k: r.get(k) for k in keep} | {"worst_holding": (r["worst_paper_loss_on_one_holding"] or {}).get("dollars")}
                 for w, r in rows.items()} for v, rows in report["versions"].items()}
    print(json.dumps({"engine_checks": report["engine_checks"], "windows": report["windows"],
                      "verdicts": report["verdicts"], "versions": brief}, indent=1))


if __name__ == "__main__":
    main()
