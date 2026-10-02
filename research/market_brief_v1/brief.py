"""Daily market brief for the owner's real positions (MU now; LITE under Plan B). Read-only; places no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.market_brief_v1.brief            # print today's brief
  PYTHONPATH=src:. .venv/bin/python -m research.market_brief_v1.brief --email    # also email it (owner-approved job only)

What it does, after the close:
  - prices for the positions and the stocks that move with them (memory/storage peers, chips, the market)
  - each position against its sell-note levels (+target, -10%, limit)
  - warning flags with thresholds fixed here in advance (below). A flag means "something is happening",
    not "something will happen"; nothing here predicts the future.
  - headlines from the last 24 hours (Alpaca's free news feed, so the Alpha Vantage quota stays with the bots)
  - the next two weeks from calendar.json
DRAM prices are linked, not read: TrendForce's terms forbid automated collection, so the owner checks that page by hand.

Data: Alpaca SIP daily bars (free plan, 16+ minutes delayed) with the LITE paper account's read-only keys.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import urllib.parse
from zoneinfo import ZoneInfo

from research.lite_dip_history_v1.run import DATA, fetch
from research.lite_paper_bot_v1.bot import credentials

NY = ZoneInfo("America/New_York")
HERE = Path(__file__).resolve().parent
DRAM_PAGE = "https://www.trendforce.com/price/dram/dram_spot"

GROUPS = {
    "Memory/storage": ["MU", "SNDK", "WDC", "STX"],
    "AI / optics": ["LITE", "NVDA"],
    "Chips and market": ["SMH", "QQQ", "SPY"],
}
WORST_DROP = {"MU": 0.41, "LITE": 0.55}  # worst 2025-26 drop from a peak (MU) / worst replayed Plan B hold (LITE)

# Warning thresholds, fixed in advance (day = close vs the previous close).
HOLDING_DAY_DROP = -5.0      # a position falls 5%+ in a day
HOLDING_5DAY_DROP = -10.0    # a position falls 10%+ over 5 trading days
PEERS_DAY_DROP = -5.0        # memory/storage peers (SNDK, WDC, STX) average -5% or worse
CHIPS_DAY_DROP = -3.0        # SMH -3% or worse
MARKET_DAY_DROP = -2.0       # SPY -2% or worse
FROM_HIGH_DROP = -20.0       # a position closes 20%+ below its 52-week closing high
NEAR_LEVEL_PCT = 3.0         # within 3% of a sell-note level
EVENT_HEADS_UP_DAYS = 3      # calendar events in the next 3 days


def daily_bars(symbols, key, secret, end):
    start = (datetime.now(timezone.utc) - timedelta(days=400)).strftime("%Y-%m-%d")
    out, token = {s: [] for s in symbols}, None
    while True:
        query = {"symbols": ",".join(symbols), "timeframe": "1Day", "feed": "sip", "adjustment": "all",
                 "start": start, "end": end, "limit": 10000}
        if token:
            query["page_token"] = token
        page = fetch(f"{DATA}/v2/stocks/bars?{urllib.parse.urlencode(query)}", key, secret)
        for symbol, rows in (page.get("bars") or {}).items():
            out[symbol] += rows
        token = page.get("next_page_token")
        if not token:
            return out


def stats(rows):
    closes = [r["c"] for r in rows]
    if len(closes) < 6:
        return None
    year = closes[-252:]
    return {"day": rows[-1]["t"][:10], "close": closes[-1],
            "day_pct": 100 * (closes[-1] / closes[-2] - 1),
            "five_day_pct": 100 * (closes[-1] / closes[-6] - 1),
            "from_high_pct": 100 * (closes[-1] / max(year) - 1)}


def position_lines(positions, prices):
    lines, flags = [], []
    for p in positions:
        s = prices.get(p["symbol"])
        if not s:
            continue
        value, cost = p["shares"] * s["close"], p["shares"] * p["cost"]
        pnl, pnl_pct = value - cost, 100 * (s["close"] / p["cost"] - 1)
        target = p["cost"] * (1 + p["target_pct"] / 100)
        limit = p["cost"] * (1 + p["limit_pct"] / 100)
        minus10 = p["cost"] * 0.90
        lines.append(f"{p['symbol']}: {p['shares']} sh @ ${p['cost']:,.2f} -> close ${s['close']:,.2f}  "
                     f"{pnl:+,.0f} ({pnl_pct:+.1f}%)")
        lines.append(f"   target +{p['target_pct']}% ${target:,.2f} | -10% ${minus10:,.2f} | "
                     f"limit {p['limit_pct']}% ${limit:,.2f}")
        if s["close"] >= target:
            flags.append(("RED", f"{p['symbol']} closed at/above your +{p['target_pct']}% target. "
                                 "Sell note: sell, or sell half and write down why you keep the rest."))
        elif s["close"] <= limit:
            flags.append(("RED", f"{p['symbol']} closed at/below your {p['limit_pct']}% limit. "
                                 "Sell note: decide tonight; sell, or write one sentence why you hold."))
        elif s["close"] <= minus10:
            flags.append(("YELLOW", f"{p['symbol']} is 10%+ below your buy: 'a normal week' per your note. "
                                    "Re-read it; no action required."))
        for name, level in (("target", target), ("limit", limit)):
            if s["close"] < level <= s["close"] * (1 + NEAR_LEVEL_PCT / 100) or \
                    s["close"] * (1 - NEAR_LEVEL_PCT / 100) <= level < s["close"]:
                flags.append(("YELLOW", f"{p['symbol']} is within {NEAR_LEVEL_PCT:.0f}% of your {name} "
                                        f"(${level:,.2f})."))
        if s["day_pct"] <= HOLDING_DAY_DROP:
            flags.append(("YELLOW", f"{p['symbol']} fell {s['day_pct']:.1f}% today."))
        if s["five_day_pct"] <= HOLDING_5DAY_DROP:
            flags.append(("YELLOW", f"{p['symbol']} is {s['five_day_pct']:.1f}% over 5 days."))
        if s["from_high_pct"] <= FROM_HIGH_DROP:
            flags.append(("YELLOW", f"{p['symbol']} is {s['from_high_pct']:.1f}% below its 52-week closing high."))
    return lines, flags


def market_flags(prices):
    flags = []
    peers = [prices[s]["day_pct"] for s in ("SNDK", "WDC", "STX") if s in prices]
    if peers and sum(peers) / len(peers) <= PEERS_DAY_DROP:
        flags.append(("YELLOW", f"Memory/storage peers averaged {sum(peers) / len(peers):.1f}% today "
                                "(SNDK, WDC, STX). Check the headlines and DRAM prices."))
    if "SMH" in prices and prices["SMH"]["day_pct"] <= CHIPS_DAY_DROP:
        flags.append(("YELLOW", f"Chip index SMH {prices['SMH']['day_pct']:.1f}% today."))
    if "SPY" in prices and prices["SPY"]["day_pct"] <= MARKET_DAY_DROP:
        flags.append(("YELLOW", f"S&P 500 (SPY) {prices['SPY']['day_pct']:.1f}% today."))
    return flags


def upcoming(events, today, days=14):
    end = today + timedelta(days=days)
    rows = [e for e in events if today <= date.fromisoformat(e["date"]) <= end]
    flags = [("HEADS-UP", f"{e['date']}: {e['what']}") for e in rows
             if (date.fromisoformat(e["date"]) - today).days <= EVENT_HEADS_UP_DAYS]
    return rows, flags


def headlines(key, secret, symbols, since):
    query = {"symbols": ",".join(symbols), "start": since, "limit": 50, "sort": "desc"}
    news = fetch(f"{DATA}/v1beta1/news?{urllib.parse.urlencode(query)}", key, secret).get("news") or []
    focused = [n for n in news if len(n.get("symbols") or []) <= 3]  # skip "12 stocks moving" roundups
    return focused[:8]


def build(now=None):
    now = now or datetime.now(timezone.utc)
    key, secret = credentials()
    book = json.loads((HERE / "positions.json").read_text())
    events = json.loads((HERE / "calendar.json").read_text())["events"]
    symbols = sorted({s for group in GROUPS.values() for s in group} | {p["symbol"] for p in book["positions"]})
    end = (now - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
    prices = {s: st for s, rows in daily_bars(symbols, key, secret, end).items() if (st := stats(rows))}
    today = now.astimezone(NY).date()

    pos_lines, flags = position_lines(book["positions"], prices)
    flags += market_flags(prices)
    soon, event_flags = upcoming(events, today)
    flags += event_flags
    news = headlines(key, secret, ["MU", "LITE", "SNDK", "WDC", "STX", "NVDA"],
                     (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"))

    open_loss = sum(min(0.0, p["shares"] * (prices[p["symbol"]]["close"] - p["cost"]))
                    for p in book["positions"] if p["symbol"] in prices)
    bad_case = sum(p["shares"] * p["cost"] * WORST_DROP.get(p["symbol"], 0.5) for p in book["positions"])

    reds = sum(1 for level, _ in flags if level == "RED")
    yellows = sum(1 for level, _ in flags if level == "YELLOW")
    mood = "RED: decision per your sell note" if reds else (f"{yellows} to watch" if yellows else "quiet")
    out = [f"Market brief {today:%a %b %d}: {mood}", "",
           "Read-only research brief. Not advice, not a prediction. You make every real decision.", ""]
    out += ["== Flags =="] + ([f"[{level}] {text}" for level, text in flags] or ["None. Nothing crossed a preset line."])
    out += ["", "== Your positions =="] + (pos_lines or ["(none recorded)"])
    out += [f"Combined: open loss -${abs(open_loss):,.0f}; bad case from cost about -${bad_case:,.0f} "
            f"vs your ~${book['combined_limit_usd']:,} limit."]
    out += ["", "== Prices (close, day, 5 days, from 52-wk high) =="]
    for group, members in GROUPS.items():
        out.append(group + ":")
        for s in members:
            if s in prices:
                p = prices[s]
                out.append(f"  {s:5} ${p['close']:>9,.2f}  {p['day_pct']:+6.1f}%  {p['five_day_pct']:+6.1f}%  "
                           f"{p['from_high_pct']:+6.1f}%")
    out += ["", "== Headlines (last 24 h) =="]
    out += [f"- {n['created_at'][5:16].replace('T', ' ')} UTC [{','.join(n['symbols'][:3])}] {n['headline']}"
            for n in news] or ["(none)"]
    out += ["", "== Next 2 weeks =="]
    out += [f"- {e['date']} ({e['status']}): {e['what']}. Why: {e['why']}" for e in soon] or ["(nothing listed)"]
    out += ["", "== Check by hand ==",
            f"- DRAM spot prices (TrendForce, free page; its terms forbid automated reading): {DRAM_PAGE}",
            "  Watch the DDR5 16Gb 'Session Average' and the arrow: a run of down days is the early sign bears talk about.",
            "", "Reminder: flags tell you something is happening, not what happens next. Our tests found news",
            "and chart signals did not predict LITE's next move. Your sell notes decide, on closing prices."]
    return "\n".join(out), f"Market brief {today:%a %b %d}: {mood}", today.isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", action="store_true", help="email the brief (only for the owner-approved job)")
    args = parser.parse_args()
    body, subject, day = build()
    print(body)
    if args.email:
        from research.real_position_alert_v1.monitor import resend_key, send
        send(subject, body, resend_key(), f"market-brief-{day}")


if __name__ == "__main__":
    main()
