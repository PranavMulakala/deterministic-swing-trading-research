"""Descriptive look (Oct 6, owner's question; NOT a pre-declared test, and Plan B is unchanged): the same LITE dip
signals and buys as run.py, with different sell targets: +2% (today's rule), +3%, +4%, and splits that sell 60% at +2%
and 40% at +3% or +4%. One position at a time (a new buy only once every part is sold), no stop, $60,000 per buy.
Goes on the parked-ideas list under the formula freeze. Research only; places no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.lite_dip_history_v1.target_compare
"""
from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, ROUND_UP, Decimal
import json
from pathlib import Path

from research.lite_dip_history_v1.run import (FIRST, LAST, PAPER, TICKET, WINDOWS, cached, fetch, history, regular,
                                              weekly)
from research.lite_paper_bot_v1.bot import BUY_BUFFER, CENT, credentials, evaluate, mornings

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/lite-target-compare-20261006.json"
VARIANTS = {"all at +2% (today's rule)": [(1.0, "1.02")], "all at +3%": [(1.0, "1.03")], "all at +4%": [(1.0, "1.04")],
            "60% at +2%, 40% at +3%": [(0.6, "1.02"), (0.4, "1.03")],
            "60% at +2%, 40% at +4%": [(0.6, "1.02"), (0.4, "1.04")]}


def replay_parts(signals, sip, days, parts, ticket=TICKET):
    held, sales, daily, realized, buys = None, [], [], Decimal(0), 0
    for index, day in enumerate(days):
        bars = sip.get(day, [])

        def sell(start, end="24:00"):
            nonlocal held, realized
            for part in held["parts"]:
                if part["sold"]:
                    continue
                for clock, opening, high, _, _ in bars:
                    if start <= clock < end and high >= part["target"]:
                        price = max(opening, part["target"]) if clock == "09:30" else part["target"]
                        realized += (price - held["fill"]) * part["shares"]
                        part["sold"] = day
                        break
            if all(p["sold"] for p in held["parts"]):
                sales.append({"entry_day": held["entry_day"], "exit_day": day, "sessions": index - held["index"] + 1})
                held = None

        if held:
            sell("09:30", "10:00")
        result = signals.get(day)
        if result and result["signal"] and not held:
            reference = next((opening for clock, opening, *_ in bars if clock == "10:00"), None)
            if reference is not None and abs(reference / Decimal(str(result["close_0955"])) - 1) <= Decimal("0.02"):
                fill = (reference * BUY_BUFFER).quantize(CENT, rounding=ROUND_HALF_UP)
                shares, left = int(ticket / fill), int(ticket / fill)
                held = {"entry_day": day, "index": index, "fill": fill, "parts": []}
                for k, (fraction, mult) in enumerate(parts):
                    n = left if k == len(parts) - 1 else round(shares * fraction)
                    left -= n
                    held["parts"].append({"shares": n, "sold": None,
                                          "target": (fill * Decimal(mult)).quantize(CENT, rounding=ROUND_UP)})
                buys += 1
        if held:
            sell("10:05" if held["entry_day"] == day else "10:00")
        unrealized = sum((bars[-1][4] - held["fill"]) * p["shares"] for p in held["parts"] if not p["sold"]) \
            if held and bars else Decimal(0)
        daily.append({"day": day, "realized": realized, "equity": realized + unrealized, "holding": bool(held)})
    weeks = weekly(daily)
    peak, worst = Decimal(0), Decimal(0)
    for row in daily:
        peak = max(peak, row["equity"])
        worst = min(worst, row["equity"] - peak)
    money = lambda v: int(v.quantize(Decimal(1)))
    return {"buys": buys, "completed_sales": len(sales), "realized_profit": money(realized),
            "marked_profit_at_end": money(daily[-1]["equity"]),
            "weeks_with_1000_plus_realized": sum(w["realized"] >= 1000 for w in weeks), "weeks": len(weeks),
            "worst_drop_from_peak": money(worst),
            "average_days_held": round(sum(s["sessions"] for s in sales) / max(len(sales), 1), 1),
            "still_open_at_end": bool(held)}


def main():
    key, secret = credentials()
    calendar = cached(f"calendar_{FIRST}_{LAST}.json.gz", lambda: fetch(f"{PAPER}/v2/calendar?start={FIRST}&end={LAST}", key, secret))
    closes = {row["date"]: row["close"] for row in calendar if row["open"] == "09:30"}
    days = sorted(closes)
    sip = regular(history("sip", key, secret, "LITE", FIRST, LAST), closes)
    signals = {d: evaluate(b, []) for d, b in mornings(history("iex", key, secret, "LITE", FIRST, LAST)).items() if d in closes}
    out = {"note": "descriptive look, not a pre-declared test; Plan B unchanged (formula freeze)", "windows": {}}
    for name, (start, end) in WINDOWS.items():
        window = [d for d in days if start <= d <= end]
        out["windows"][name] = {v: replay_parts(signals, sip, window, [(f, m) for f, m in parts])
                                for v, parts in VARIANTS.items()}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
