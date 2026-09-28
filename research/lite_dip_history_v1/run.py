"""Replay the LITE paper bot's rule on Alpaca five-minute history. Research only; places no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.lite_dip_history_v1.run

The signal uses IEX morning bars, as the bot does (or SIP with --signal-feed sip). Buys, the
+2% sale and daily marks use regular-session SIP bars. Each buy spends $60,000: 66 shares at
about $910, the bot's size since the evening of September 28, 2026. No stop, no time limit,
one position at a time. Every replay window starts flat on its first day.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, ROUND_UP, Decimal
import gzip
import json
from pathlib import Path
import urllib.parse
from urllib.request import ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

from research.lite_paper_bot_v1.bot import BUY_BUFFER, CENT, TARGET_MULTIPLIER, credentials, evaluate, mornings, ts

NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "outputs/lite_history"
DATA, PAPER = "https://data.alpaca.markets", "https://paper-api.alpaca.markets"
FIRST, LAST = "2022-01-01", "2026-09-28"
TICKET = Decimal("60000")
WINDOWS = {
    "boom_2025_2026": ("2025-01-01", LAST),
    "year_2025": ("2025-01-01", "2025-12-31"),
    "year_2026": ("2026-01-01", LAST),
    "stress_2022_2024": ("2022-01-01", "2024-12-31"),
}
D = lambda value: Decimal(str(value))


def fetch(url, key, secret):
    request = Request(url, headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
    with build_opener(ProxyHandler({})).open(request, timeout=60) as reply:
        return json.load(reply)


def cached(name, load):
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(json.dumps(load()).encode()))
    return json.loads(gzip.decompress(path.read_bytes()))


def history(feed, key, secret, symbol="LITE", first=FIRST, last=LAST):
    def load():
        rows, token = [], None
        while True:
            query = {"timeframe": "5Min", "feed": feed, "adjustment": "raw", "sort": "asc", "limit": 10000,
                     "start": f"{first}T00:00:00Z", "end": f"{last}T20:00:00Z"}
            if token:
                query["page_token"] = token
            reply = fetch(f"{DATA}/v2/stocks/{symbol}/bars?{urllib.parse.urlencode(query)}", key, secret)
            rows.extend(reply.get("bars") or [])
            token = reply.get("next_page_token")
            if not token:
                return rows
    return cached(f"{symbol}_5min_{feed}_{first}_{last}.json.gz", load)


def regular(rows, closes):
    """Regular-session bars per New York date as (hh:mm, open, high, low, close)."""
    days = defaultdict(list)
    for bar in rows:
        moment = ts(bar["t"]).astimezone(NY)
        day, clock = moment.date().isoformat(), f"{moment:%H:%M}"
        if day in closes and "09:30" <= clock < closes[day]:
            days[day].append((clock, D(bar["o"]), D(bar["h"]), D(bar["l"]), D(bar["c"])))
    return days


def scan(held, bars, start, end="24:00", through=Decimal(0)):
    """Track the holding's lowest price; return (time, price) of the +2% sale, if it happens.

    through > 0 requires trading that far beyond the target, since a touch need not fill a resting order.
    """
    for clock, opening, high, low, _ in bars:
        if start <= clock < end:
            held["low"] = min(held["low"], low)
            if high >= held["target"] * (1 + through):  # A gap above the target at the open sells at the open.
                return clock, max(opening, held["target"]) if clock == "09:30" else held["target"]
    return None


def replay(signals, sip, days, ticket=TICKET, through=Decimal(0)):
    """signals: date -> evaluate() result, or missing when the six morning bars were incomplete."""
    held, trades, daily, counts, realized = None, [], [], defaultdict(int), Decimal(0)
    for index, day in enumerate(days):
        bars = sip.get(day, [])

        def sell(hit):
            nonlocal held, realized
            pnl = (hit[1] - held["fill"]) * held["shares"]
            realized += pnl
            trades.append({**held, "exit_day": day, "exit_time": hit[0], "exit": hit[1], "pnl": pnl,
                           "sessions": index - held["index"] + 1})
            held = None

        if held and (hit := scan(held, bars, "09:30", "10:00", through)):
            sell(hit)  # Sold before the 10:00:30 decision, so today's signal can buy again.
        result = signals.get(day)
        if result is None:
            counts["no_data"] += 1
        elif result["signal"]:
            counts["signals"] += 1
            reference = next((opening for clock, opening, *_ in bars if clock == "10:00"), None)
            if held:
                counts["skipped_holding"] += 1
            elif reference is None or abs(reference / D(result["close_0955"]) - 1) > Decimal("0.02"):
                counts["no_price"] += 1
            else:
                fill = (reference * BUY_BUFFER).quantize(CENT, rounding=ROUND_HALF_UP)
                held = {"entry_day": day, "index": index, "fill": fill, "shares": int(ticket / fill), "low": fill,
                        "target": (fill * TARGET_MULTIPLIER).quantize(CENT, rounding=ROUND_UP)}
                counts["buys"] += 1
        if held and (hit := scan(held, bars, "10:05" if held["entry_day"] == day else "10:00", through=through)):
            sell(hit)
        unrealized = (bars[-1][4] - held["fill"]) * held["shares"] if held and bars else Decimal(0)
        daily.append({"day": day, "realized": realized, "equity": realized + unrealized, "holding": bool(held)})
    return {"trades": trades, "daily": daily, "counts": dict(counts), "open": held}


def weekly(daily):
    """Realized and marked (realized + paper) change per Monday-Friday week."""
    ends = {}
    for row in daily:
        ends[date.fromisoformat(row["day"]).isocalendar()[:2]] = row
    weeks, previous = [], {"realized": Decimal(0), "equity": Decimal(0)}
    for key in sorted(ends):
        row = ends[key]
        weeks.append({"week": f"{key[0]}-W{key[1]:02d}", "realized": row["realized"] - previous["realized"],
                      "marked": row["equity"] - previous["equity"], "holding_at_end": row["holding"]})
        previous = row
    return weeks


def summarize(result):
    trades, daily, held = result["trades"], result["daily"], result["open"]
    weeks = weekly(daily)
    streak = longest = 0
    for week in weeks:
        streak = 0 if week["realized"] > 0 else streak + 1
        longest = max(longest, streak)
    peak, worst_drop = Decimal(0), Decimal(0)
    for row in daily:
        peak = max(peak, row["equity"])
        worst_drop = min(worst_drop, row["equity"] - peak)
    holdings = trades + ([{**held, "sessions": len(daily) - held["index"]}] if held else [])
    worst = min(holdings, key=lambda t: (t["low"] - t["fill"]) * t["shares"], default=None)
    longest_hold = max(holdings, key=lambda t: t["sessions"], default=None)
    money = lambda value: int(value.quantize(Decimal(1)))
    return {
        "sessions": len(daily), **result["counts"], "sales": len(trades),
        "realized_pnl": money(result["daily"][-1]["realized"]) if daily else 0,
        "marked_pnl_at_end": money(daily[-1]["equity"]) if daily else 0,
        "weeks": len(weeks), "weeks_realized_1000_plus": sum(w["realized"] >= 1000 for w in weeks),
        "weeks_marked_1000_plus": sum(w["marked"] >= 1000 for w in weeks),
        "weeks_marked_minus_1000_or_worse": sum(w["marked"] <= -1000 for w in weeks),
        "worst_marked_week": money(min((w["marked"] for w in weeks), default=Decimal(0))),
        "average_realized_per_week": money(sum((w["realized"] for w in weeks), Decimal(0)) / max(len(weeks), 1)),
        "longest_run_of_weeks_without_a_sale": longest,
        "worst_drop_from_peak_marked": money(worst_drop),
        "worst_paper_loss_on_one_holding": worst and {
            "entry_day": worst["entry_day"], "fill": str(worst["fill"]), "low": str(worst["low"]),
            "percent": float(((worst["low"] / worst["fill"] - 1) * 100).quantize(Decimal("0.1"))),
            "dollars": money((worst["low"] - worst["fill"]) * worst["shares"])},
        "longest_hold": longest_hold and {"entry_day": longest_hold["entry_day"],
                                          "exit_day": longest_hold.get("exit_day", "still open"),
                                          "sessions": longest_hold["sessions"]},
        "same_day_sales": sum(t["exit_day"] == t["entry_day"] for t in trades),
        "sales_within_5_sessions": sum(t["sessions"] <= 5 for t in trades),
        "open_at_end": held and {"entry_day": held["entry_day"], "fill": str(held["fill"]), "shares": held["shares"],
                                 "marked_pnl": money(daily[-1]["equity"] - daily[-1]["realized"])},
    }


def start_month_table(signals, sip, days, years, last, through=Decimal(0)):
    """If the bot had been switched on at the start of each month of these years: its first buy's fate."""
    rows = []
    for year in years:
        for month in range(1, 13):
            start = f"{year}-{month:02d}-01"
            result = replay(signals, sip, [day for day in days if day >= start], through=through)
            first = result["trades"][0] if result["trades"] else result["open"]
            if not first:
                continue
            exit_day = first.get("exit_day")
            span = (date.fromisoformat(exit_day or last) - date.fromisoformat(first["entry_day"])).days
            rows.append({"switched_on": start[:7], "first_buy": first["entry_day"], "price": str(first["fill"]),
                         "sold": exit_day or f"not by {last}", "months_waiting": round(span / 30.44, 1),
                         "worst_paper_loss": int(((first["low"] - first["fill"]) * first["shares"]).quantize(1))})
    return rows


def first_year_table(signals, sip, days, first_month, last_month, through=Decimal(0)):
    """Switch the bot on at the start of each month and follow it for one year."""
    rows, month = [], date.fromisoformat(f"{first_month}-01")
    while f"{month:%Y-%m}" <= last_month:
        end = month.replace(year=month.year + 1) - timedelta(days=1)
        window = [day for day in days if month.isoformat() <= day <= end.isoformat()]
        summary = summarize(replay(signals, sip, window, through=through))
        rows.append({"switched_on": f"{month:%Y-%m}", "sales": summary["sales"],
                     "realized_pnl": summary["realized_pnl"], "marked_pnl_at_end": summary["marked_pnl_at_end"],
                     "weeks": summary["weeks"], "weeks_realized_1000_plus": summary["weeks_realized_1000_plus"],
                     "longest_run_of_weeks_without_a_sale": summary["longest_run_of_weeks_without_a_sale"],
                     "worst_drop_from_peak_marked": summary["worst_drop_from_peak_marked"]})
        month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="LITE")
    parser.add_argument("--first", default=FIRST)
    parser.add_argument("--last", default=LAST)
    parser.add_argument("--window", action="append", help="name:YYYY-MM-DD:YYYY-MM-DD (default: the LITE windows)")
    parser.add_argument("--switch-on-years", default="2022,2023,2024")
    parser.add_argument("--first-year-months", default="2022-01:2025-09",
                        help="switch-on months to follow for one year, as YYYY-MM:YYYY-MM")
    parser.add_argument("--signal-feed", choices=("iex", "sip"), default="iex")
    parser.add_argument("--through-pct", default="0", help="require trading this %% beyond the target to sell")
    parser.add_argument("--output", default="output/lite-dip-history-2022-2026.json")
    args = parser.parse_args()
    through = D(args.through_pct) / 100
    windows = dict((w.split(":")[0], tuple(w.split(":")[1:])) for w in args.window) if args.window else WINDOWS
    key, secret = credentials()
    calendar = cached(f"calendar_{args.first}_{args.last}.json.gz",
                      lambda: fetch(f"{PAPER}/v2/calendar?start={args.first}&end={args.last}", key, secret))
    closes = {row["date"]: row["close"] for row in calendar if row["open"] == "09:30"}
    days = sorted(closes)
    sip_rows = history("sip", key, secret, args.symbol, args.first, args.last)
    sip = regular(sip_rows, closes)
    morning_rows = sip_rows if args.signal_feed == "sip" else history("iex", key, secret, args.symbol, args.first, args.last)
    signals = {day: evaluate(bars, []) for day, bars in mornings(morning_rows).items() if day in closes}
    report = {"symbol": args.symbol, "signal_feed": args.signal_feed, "ticket_dollars": str(TICKET),
              "sale_needs_trading_beyond_target_pct": args.through_pct,
              "missing_sip_sessions": sum(day not in sip for day in days), "windows": {}}
    for name, (start, end) in windows.items():
        window = [day for day in days if start <= day <= end]
        report["windows"][name] = {"from": window[0], "to": window[-1],
                                   **summarize(replay(signals, sip, window, through=through))}
    years = [int(year) for year in args.switch_on_years.split(",")]
    report["switched_on_each_month"] = start_month_table(signals, sip, days, years, args.last, through)
    report["first_year_after_switch_on"] = first_year_table(signals, sip, days, *args.first_year_months.split(":"),
                                                            through=through)
    Path(args.output).write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
