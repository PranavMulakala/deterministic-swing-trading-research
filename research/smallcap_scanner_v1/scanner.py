"""Paper small-cap momentum scanner: Ross Cameron's "5 pillars" on free data. Research only; places no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.smallcap_scanner_v1.scanner            # one scan now
  PYTHONPATH=src:. .venv/bin/python -m research.smallcap_scanner_v1.scanner --review 2026-10-01

The rules (fixed, from output/ROSS_CAMERON_NOTES_20261001.md and his Stock Selection PDF):
  1. price $2-$20            2. up at least 10% from yesterday's close
  3. relative volume >= 5x   4. a news headline in the last 24 hours
  5. float under 20 million shares
Grade A = all five, B = four of five. Common stocks on NYSE/Nasdaq/NYSE American only (warrants, units, rights,
funds and SPACs are dropped). A pass is a stock to watch, not a buy signal.

Data limits:
- Candidates come from Alpaca's free movers and most-actives screeners.
- Prices and volume come from the IEX feed (a few percent of all trading). Relative volume compares IEX volume today
  with IEX volume on past days, and is not adjusted for time of day.
- Float comes from Alpha Vantage OVERVIEW (SharesFloat), cached for 7 days. The free key allows 5 calls a minute
  and about 25 a day, so lookups are paced 13 s apart and capped at 8 per run; past that, float shows as unknown.
- News counts only headlines about at most 3 symbols that are not market wraps ("stocks moving", "Nasdaq gains").
Every scan is appended to outputs/smallcap_scanner/scans.jsonl (gitignored). --review scores each symbol's first
A/B appearance that day against what the price did afterwards.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
import time
import urllib.parse
from urllib.request import ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

from research.breakout_test_v1.fetch import EXCHANGES, NOT_STOCKS
from research.lite_dip_history_v1.run import DATA, PAPER, fetch
from research.lite_paper_bot_v1.bot import credentials
from research.lite_paper_bot_v1.news import URL as AV_URL, api_key as av_key

NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/smallcap_scanner"
PRICE_MIN, PRICE_MAX, GAIN_MIN, RVOL_MIN, FLOAT_MAX = 2.0, 20.0, 10.0, 5.0, 20_000_000
FLOAT_CACHE_DAYS, AV_CALLS_PER_RUN, AV_CALLS_PER_DAY, AV_PAUSE_SECONDS = 7, 8, 20, 13


def pillars(price, change_pct, rvol, has_news, float_shares):
    """The five checks: True, False, or None when the data is missing. Grade A = 5 true, B = 4 true."""
    checks = {"price_2_20": PRICE_MIN <= price <= PRICE_MAX,
              "up_10pct": change_pct >= GAIN_MIN,
              "rvol_5x": None if rvol is None else rvol >= RVOL_MIN,
              "news_24h": has_news,
              "float_under_20m": None if float_shares is None else float_shares < FLOAT_MAX}
    passed = sum(v is True for v in checks.values())
    return checks, ("A" if passed == 5 else "B" if passed == 4 else None)


ROUNDUP = re.compile(r"stocks? (moving|making|to watch)|movers|gainers|losers|mid-day|midday|pre-market|premarket|"
                     r"after-hours|nasdaq (gains|falls|dips|surges)|dow (jumps|falls|gains)|s&p 500", re.I)


def is_roundup(item):
    """A market wrap or "stocks moving" list is not a catalyst for any one stock."""
    return len(item.get("symbols") or []) > 3 or bool(ROUNDUP.search(item.get("headline") or ""))


def traded_today(stamp, now):
    """The latest trade must be from today's New York date; pre-market lists can still show yesterday's movers."""
    if not stamp:
        return False
    return datetime.fromisoformat(stamp[:19] + "+00:00").astimezone(NY).date() == now.astimezone(NY).date()


def is_common_stock(asset):
    return (asset.get("exchange") in EXCHANGES and asset.get("tradable") and asset.get("class") == "us_equity"
            and re.fullmatch(r"[A-Z]{1,5}", asset.get("symbol", "")) is not None
            and not NOT_STOCKS.search(asset.get("name") or ""))


class Data:
    def __init__(self):
        self.key, self.secret = credentials()

    def get(self, url):
        return fetch(url, self.key, self.secret)

    def candidates(self):
        movers = self.get(f"{DATA}/v1beta1/screener/stocks/movers?top=50")
        actives = self.get(f"{DATA}/v1beta1/screener/stocks/most-actives?by=volume&top=100")
        rows = {m["symbol"]: m for m in movers.get("gainers", [])}
        for a in actives.get("most_actives", []):
            rows.setdefault(a["symbol"], {"symbol": a["symbol"]})
        return rows

    def asset(self, symbol):
        try:
            return self.get(f"{PAPER}/v2/assets/{urllib.parse.quote(symbol)}")
        except Exception:
            return {}

    def snapshots(self, symbols):
        return self.get(f"{DATA}/v2/stocks/snapshots?feed=iex&symbols={','.join(symbols)}") if symbols else {}

    def avg_volume(self, symbols, today):
        """IEX 50-day average daily volume before today."""
        if not symbols:
            return {}
        start = (today - timedelta(days=80)).isoformat()
        rows, token = {}, None
        while True:
            url = (f"{DATA}/v2/stocks/bars?timeframe=1Day&feed=iex&limit=10000&start={start}&end={today.isoformat()}"
                   f"&symbols={','.join(symbols)}" + (f"&page_token={token}" if token else ""))
            page = self.get(url)
            for sym, bars in (page.get("bars") or {}).items():
                rows.setdefault(sym, []).extend(b for b in bars if b["t"][:10] < today.isoformat())
            token = page.get("next_page_token")
            if not token:
                break
        return {s: sum(b["v"] for b in bars[-50:]) / len(bars[-50:]) for s, bars in rows.items() if bars}

    def news(self, symbols, now):
        if not symbols:
            return {}
        start = (now - timedelta(hours=24)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        page = self.get(f"{DATA}/v1beta1/news?limit=50&start={start}&symbols={','.join(symbols)}")
        found = {}
        for item in page.get("news", []):
            if is_roundup(item):
                continue
            for sym in item.get("symbols", []):
                found.setdefault(sym, item["headline"][:120])
        return found


def float_shares(symbols, cache_path=None, opener=None):
    """Alpha Vantage SharesFloat, cached; None when unknown or past the per-run call budget."""
    cache_path = cache_path or OUT / "float_cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    today = date.today().isoformat()
    used = cache.get("_calls", {}).get(today, 0)
    key, calls, out = av_key(), 0, {}
    for sym in symbols:
        hit = cache.get(sym) if sym != "_calls" else None
        if hit and (date.today() - date.fromisoformat(hit["on"])).days < FLOAT_CACHE_DAYS:
            out[sym] = hit["float"]
            continue
        if not key or calls >= AV_CALLS_PER_RUN or used + calls >= AV_CALLS_PER_DAY:
            out[sym] = None
            continue
        if calls:
            time.sleep(AV_PAUSE_SECONDS)  # the free key allows 5 calls a minute
        calls += 1
        query = urllib.parse.urlencode({"function": "OVERVIEW", "symbol": sym, "apikey": key})
        try:
            with (opener or build_opener(ProxyHandler({}))).open(Request(f"{AV_URL}?{query}"), timeout=20) as r:
                data = json.loads(r.read())
            value = int(data["SharesFloat"]) if str(data.get("SharesFloat", "")).isdigit() else None
            if value == 0:
                value = None
        except Exception:
            value = None
        out[sym] = value
        if value is not None:
            cache[sym] = {"float": value, "on": date.today().isoformat()}
    cache["_calls"] = {today: used + calls}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=1))
    return out


def scan(data=None, now=None):
    data, now = data or Data(), now or datetime.now(NY)
    rows = data.candidates()
    snaps = data.snapshots(sorted(rows))
    keep = []
    for sym in sorted(rows):
        s = snaps.get(sym) or {}
        trade = s.get("latestTrade") or {}
        price, prev = trade.get("p"), (s.get("prevDailyBar") or {}).get("c")
        if not price or not prev or not traded_today(trade.get("t"), now):
            continue
        change = 100 * (price / prev - 1)
        if PRICE_MIN <= price <= PRICE_MAX and change >= GAIN_MIN:  # cheap pre-filter before slower lookups
            keep.append({"symbol": sym, "price": price, "prev_close": prev, "change_pct": round(change, 1),
                         "volume_iex": (s.get("dailyBar") or {}).get("v", 0)})
    keep = [k for k in keep if is_common_stock(data.asset(k["symbol"]))]
    symbols = [k["symbol"] for k in keep]
    avg, news = data.avg_volume(symbols, now.date()), data.news(symbols, now)
    floats = float_shares(symbols)
    results = []
    for k in keep:
        sym = k["symbol"]
        rvol = round(k["volume_iex"] / avg[sym], 1) if avg.get(sym) else None
        checks, grade = pillars(k["price"], k["change_pct"], rvol, sym in news, floats.get(sym))
        results.append({**k, "rvol": rvol, "float": floats.get(sym), "news": news.get(sym), "checks": checks,
                        "grade": grade})
    results.sort(key=lambda r: (r["grade"] or "Z", -r["change_pct"]))
    record = {"at": now.isoformat(timespec="seconds"), "screened": len(rows), "results": results}
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "scans.jsonl").open("a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def table(record):
    lines = [f"Scan {record['at']} - {record['screened']} movers screened, {len(record['results'])} passed price and gain"]
    for r in record["results"]:
        fl = f"{r['float'] / 1e6:.1f}M" if r["float"] else "?"
        lines.append(f"  {r['grade'] or '-':1} {r['symbol']:6} ${r['price']:<8.2f} {r['change_pct']:+6.1f}%  "
                     f"rvol {r['rvol'] if r['rvol'] is not None else '?':>6}  float {fl:>7}  "
                     f"news: {(r['news'] or 'none')[:70]}")
    return "\n".join(lines)


def review(day, data=None):
    """For each symbol's first A/B appearance on `day`, what the price did afterwards (IEX 1-minute bars)."""
    data = data or Data()
    first = {s: {"at": r["at"], "grade": r["grade"], "price": r["price"]} for s, r in first_seen(day)[0].items()}
    out = []
    for sym, f in first.items():
        start = datetime.fromisoformat(f["at"]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = datetime.combine(date.fromisoformat(day), datetime.min.time(), NY).replace(hour=16)
        bars = data.get(f"{DATA}/v2/stocks/{sym}/bars?timeframe=1Min&feed=iex&limit=10000&start={start}"
                        f"&end={end.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}").get("bars") or []
        if not bars:
            continue
        p = f["price"]
        out.append({"symbol": sym, **f, "max_up_pct": round(100 * (max(b["h"] for b in bars) / p - 1), 1),
                    "max_down_pct": round(100 * (min(b["l"] for b in bars) / p - 1), 1),
                    "close_pct": round(100 * (bars[-1]["c"] / p - 1), 1)})
    return out


def first_seen(day):
    """Each symbol's first A/B appearance on `day`, in order."""
    path, first = OUT / "scans.jsonl", {}
    if not path.exists():
        return first, 0
    scans = 0
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        if rec["at"][:10] != day:
            continue
        scans += 1
        for r in rec["results"]:
            if r["grade"] and r["symbol"] not in first:
                first[r["symbol"]] = {**r, "at": rec["at"]}
    return first, scans


def summary_text(day):
    first, scans = first_seen(day)
    lines = [f"Paper small-cap scanner, {day}: {scans} scans from 07:00 to 10:00 ET.",
             "Watch list only. Nothing was bought; this is a paper test of Ross Cameron's 5 pillars.", ""]
    if not first:
        lines.append("No stock met 4 or 5 of the pillars today.")
    for sym, r in sorted(first.items(), key=lambda kv: (kv[1]["grade"], kv[1]["at"])):
        fl = f"{r['float'] / 1e6:.1f}M" if r.get("float") else "?"
        lines.append(f"{r['grade']}  {sym:6} first seen {r['at'][11:16]} ET at ${r['price']:.2f} "
                     f"({r['change_pct']:+.0f}% on the day), rvol {r['rvol']}, float {fl}")
        lines.append(f"     news: {r.get('news') or 'none'}")
    lines += ["", "Tonight's email scores how each one moved after it first appeared."]
    return "\n".join(lines)


def review_text(day, rows):
    lines = [f"Paper small-cap scanner review, {day}",
             "From each stock's first appearance to the 4 PM close (IEX 1-minute bars):", ""]
    if not rows:
        lines.append("Nothing to review today.")
    for r in rows:
        lines.append(f"{r['grade']}  {r['symbol']:6} seen {r['at'][11:16]} at ${r['price']:.2f}: best {r['max_up_pct']:+.1f}%, "
                     f"worst {r['max_down_pct']:+.1f}%, close {r['close_pct']:+.1f}%")
    if rows:
        ups = sum(r["close_pct"] > 0 for r in rows)
        lines += ["", f"Closed above the first-seen price: {ups} of {len(rows)}."]
    return "\n".join(lines)


def email(subject, body, idempotency):
    from research.real_position_alert_v1.monitor import resend_key, send
    return send(subject, body, resend_key(), idempotency)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", metavar="YYYY-MM-DD")
    parser.add_argument("--summary-email", action="store_true", help="email today's watch list (10:05 ET)")
    parser.add_argument("--review-email", action="store_true", help="score today's picks and email them (16:15 ET)")
    args = parser.parse_args()
    today = datetime.now(NY).date().isoformat()
    if args.summary_email:
        body = summary_text(today)
        print(body)
        email(f"Paper scanner {today}: watch list", body, f"scanner-summary-{today}")
    elif args.review_email:
        rows = review(today)
        with (OUT / "reviews.jsonl").open("a") as f:
            f.write(json.dumps({"day": today, "rows": rows}) + "\n")
        body = review_text(today, rows)
        print(body)
        email(f"Paper scanner {today}: how the picks did", body, f"scanner-review-{today}")
    elif args.review:
        print(json.dumps(review(args.review), indent=1))
    else:
        print(table(scan()))


if __name__ == "__main__":
    main()
