"""Read-only market snapshot for one stock: price range, volume, options positioning and news sentiment.

  PYTHONPATH=src:. .venv/bin/python -m research.market_snapshot_v1.snapshot MU [--output output/x.md]

Descriptive information only. None of these numbers has been tested as a buy or sell signal.
Sources: Alpaca free data (IEX stock feed, indicative options feed, option open interest) with the LITE paper
account's read-only keys; Alpha Vantage news sentiment with the owner's .env.news key. Places no orders.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import urllib.parse
from urllib.request import ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

from research.lite_dip_history_v1.run import DATA, PAPER, fetch
from research.lite_paper_bot_v1.bot import credentials
from research.lite_paper_bot_v1.news import URL, api_key, label

NY = ZoneInfo("America/New_York")
D = lambda value: Decimal(str(value))


def all_pages(url, key, secret, field):
    rows, token = [], None
    while True:
        page = fetch(url + (f"&page_token={token}" if token else ""), key, secret)
        part = page.get(field) or []
        rows.extend(part.values() if isinstance(part, dict) else part)
        if isinstance(part, dict):
            rows[-len(part):] = [{"symbol": s, **v} for s, v in part.items()] if part else []
        token = page.get("next_page_token")
        if not token:
            return rows


def price_block(symbol, key, secret, today):
    start = (today - timedelta(days=380)).isoformat()
    daily = all_pages(f"{DATA}/v2/stocks/{symbol}/bars?timeframe=1Day&feed=iex&limit=10000&start={start}", key, secret, "bars")
    now_day = [b for b in daily if b["t"][:10] == today.isoformat()]
    past = [b for b in daily if b["t"][:10] < today.isoformat()]
    intraday = all_pages(f"{DATA}/v2/stocks/{symbol}/bars?timeframe=5Min&feed=iex&limit=10000&start={today}T13:30:00Z",
                         key, secret, "bars")
    last = fetch(f"{DATA}/v2/stocks/{symbol}/trades/latest?feed=iex", key, secret)["trade"]
    volume = sum(b["v"] for b in intraday)
    vwap = sum(b["vw"] * b["v"] for b in intraday) / volume if volume else None
    minutes = len(intraday) * 5
    avg20 = sum(b["v"] for b in past[-20:]) / min(len(past), 20)
    year = past[-252:]
    return {"last": last["p"], "last_time_et": datetime.fromisoformat(last["t"][:19] + "+00:00").astimezone(NY).strftime("%H:%M"),
            "prev_close": past[-1]["c"], "today_open": now_day[0]["o"] if now_day else None,
            "today_high": max(b["h"] for b in intraday) if intraday else None,
            "today_low": min(b["l"] for b in intraday) if intraday else None, "today_vwap": vwap,
            "volume_so_far_vs_20d_avg_pace": (volume / (avg20 * min(minutes, 390) / 390)) if avg20 and minutes else None,
            "high_20d": max(b["h"] for b in past[-20:]), "low_20d": min(b["l"] for b in past[-20:]),
            "high_52w": max(b["h"] for b in year), "low_52w": min(b["l"] for b in year),
            "close_50d_avg": sum(b["c"] for b in past[-50:]) / min(len(past), 50)}


def options_block(symbol, key, secret, today, spot):
    """Nearest standard monthly expiration at least 7 days out: open interest by strike and the at-the-money straddle."""
    contracts = all_pages(f"{PAPER}/v2/options/contracts?underlying_symbols={symbol}&status=active&limit=10000"
                          f"&expiration_date_gte={today + timedelta(days=7)}&expiration_date_lte={today + timedelta(days=45)}",
                          key, secret, "option_contracts")
    monthly = sorted({c["expiration_date"] for c in contracts
                      if date.fromisoformat(c["expiration_date"]).weekday() == 4 and 15 <= int(c["expiration_date"][8:]) <= 21})
    expiry = monthly[0] if monthly else sorted({c["expiration_date"] for c in contracts})[0]
    chain = [c for c in contracts if c["expiration_date"] == expiry and c.get("open_interest")]
    oi = defaultdict(lambda: {"call": 0, "put": 0})
    for c in chain:
        oi[D(c["strike_price"])][c["type"]] += int(c["open_interest"])
    calls, puts = sum(v["call"] for v in oi.values()), sum(v["put"] for v in oi.values())
    top = lambda side: [(str(k), v[side]) for k, v in sorted(oi.items(), key=lambda kv: -kv[1][side])[:3]]
    atm = min(oi, key=lambda k: abs(k - D(spot))) if oi else None
    straddle = None
    if atm is not None:
        snaps = fetch(f"{DATA}/v1beta1/options/snapshots/{symbol}?feed=indicative&expiration_date={expiry}"
                      f"&strike_price_gte={atm}&strike_price_lte={atm}", key, secret).get("snapshots") or {}
        mids = [(q["ap"] + q["bp"]) / 2 for q in (s.get("latestQuote") for s in snaps.values()) if q and q.get("ap") and q.get("bp")]
        straddle = sum(mids) if len(mids) == 2 else None
    return {"expiration": expiry, "open_interest_date": chain[0]["open_interest_date"] if chain else None,
            "call_oi": calls, "put_oi": puts, "put_call_oi_ratio": round(puts / calls, 2) if calls else None,
            "top_call_strikes": top("call"), "top_put_strikes": top("put"), "atm_strike": str(atm),
            "atm_straddle": straddle, "implied_move_pct": round(100 * straddle / spot, 1) if straddle else None}


def news_block(symbol, hours=24):
    key = api_key()
    if not key:
        return {"error": "no Alpha Vantage key in .env.news"}
    start = datetime.now(timezone.utc).astimezone(NY) - timedelta(hours=hours)
    query = urllib.parse.urlencode({"function": "NEWS_SENTIMENT", "tickers": symbol, "sort": "LATEST", "limit": 200,
                                    "time_from": f"{start:%Y%m%dT%H%M}", "apikey": key})
    with build_opener(ProxyHandler({})).open(Request(f"{URL}?{query}", headers={"User-Agent": "snapshot/1"}), timeout=30) as r:
        feed = json.loads(r.read()).get("feed")
    if not isinstance(feed, list):
        return {"error": "Alpha Vantage refused the request (limit reached)"}
    rows = []
    for a in feed:
        t = next((x for x in a.get("ticker_sentiment") or [] if x.get("ticker") == symbol), None)
        if t and D(t["relevance_score"]) >= D("0.5"):  # articles mainly about this stock
            rows.append((D(t["relevance_score"]), D(t["ticker_sentiment_score"]), a))
    if not rows:
        return {"articles": 0}
    avg = sum(r * v for r, v, _ in rows) / sum(r for r, _, _ in rows)
    top = sorted(rows, key=lambda x: -x[0])[:5]
    return {"articles": len(rows), "score": round(float(avg), 3), "label": label(avg),
            "top": [f"{v:+.2f} {a.get('source')}: {a.get('title', '')[:110]}" for _, v, a in top]}


def markdown(symbol, p, o, n, at):
    f = lambda x, d=2: "n/a" if x is None else f"{x:,.{d}f}"
    change = 100 * (p["last"] / p["prev_close"] - 1)
    lines = [f"# {symbol} market snapshot, {at:%a %b %d, %Y %I:%M %p} ET", "",
             "Information only. None of these numbers has been tested as a buy or sell signal.", "",
             "## Price", "| | |", "|---|---|",
             f"| Last (IEX, {p['last_time_et']} ET) | ${f(p['last'])} ({change:+.1f}% vs yesterday's ${f(p['prev_close'])}) |",
             f"| Today open / high / low | ${f(p['today_open'])} / ${f(p['today_high'])} / ${f(p['today_low'])} |",
             f"| Today's average traded price (VWAP, IEX) | ${f(p['today_vwap'])} |",
             f"| 20-day high / low | ${f(p['high_20d'])} / ${f(p['low_20d'])} |",
             f"| 52-week high / low | ${f(p['high_52w'])} / ${f(p['low_52w'])} |",
             f"| 50-day average close | ${f(p['close_50d_avg'])} (last is {100 * (p['last'] / p['close_50d_avg'] - 1):+.0f}% vs that) |",
             f"| Volume so far vs a normal day's pace | {f(p['volume_so_far_vs_20d_avg_pace'])}× (IEX only, about 2–3% of all trading) |", "",
             f"## Options positioning (expiration {o['expiration']}, open interest as of {o['open_interest_date']})",
             f"- Put/call open interest: {o['put_oi']:,} puts vs {o['call_oi']:,} calls = **{f(o['put_call_oi_ratio'])}**",
             f"- Biggest call strikes: " + ", ".join(f"${s} ({n_:,})" for s, n_ in o["top_call_strikes"]),
             f"- Biggest put strikes: " + ", ".join(f"${s} ({n_:,})" for s, n_ in o["top_put_strikes"]),
             f"- At-the-money ${o['atm_strike']} straddle ≈ ${f(o['atm_straddle'])}: options price a move of about "
             f"**±{f(o['implied_move_pct'], 1)}%** by {o['expiration']} (indicative quotes, approximate)", "",
             "## News sentiment (last 24 hours, articles mainly about this stock)"]
    if n.get("error"):
        lines.append(f"- Not available: {n['error']}")
    else:
        lines.append(f"- {n['articles']} articles, average score {n.get('score')} = **{n.get('label', 'none')}**")
        lines += [f"  - {t}" for t in n.get("top", [])]
    lines += ["", "## What our research says about using these",
              "- **News sentiment:** skipping LITE dip buys on bearish news did not help (pre-declared test, Sept 28).",
              "- **Big strikes / 'liquidity' levels:** no evidence they act as reliable floors or ceilings.",
              "- **Earnings timing (MU):** beat 39 of 42 times since 2016, but rose the next day only 19 times."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("--output")
    args = parser.parse_args()
    key, secret = credentials()
    now = datetime.now(NY)
    p = price_block(args.symbol, key, secret, now.date())
    o = options_block(args.symbol, key, secret, now.date(), p["last"])
    n = news_block(args.symbol)
    text = markdown(args.symbol, p, o, n, now)
    if args.output:
        open(args.output, "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
