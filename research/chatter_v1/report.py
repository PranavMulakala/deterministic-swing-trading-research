"""Daily "LITE chatter" email: what Stocktwits and WallStreetBets said about LITE and its peers since the prior close.
Read-only public feeds (Stocktwits symbol streams, Reddit's public RSS for the WSB daily thread) plus Alpaca price
snapshots for context. Counts are keyword-based and rough; crowd mood is context, not a signal (owner approval
"yes build the daily LITE chatter email", 2026-10-08).

  PYTHONPATH=src:. .venv/bin/python -m research.chatter_v1.report --print   # print today's report
  PYTHONPATH=src:. .venv/bin/python -m research.chatter_v1.report           # email it (server, 16:15 ET)
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, time as dtime, timedelta, timezone
import html
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/chatter"
NY = ZoneInfo("America/New_York")
SYMBOLS = ["LITE", "MU", "COHR", "AAOI"]
PAGES = 8  # 30 posts per page; Stocktwits allows ~200 unauthenticated requests an hour
AGENT = "personal-feed-reader/0.1 (read-only, low volume)"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
WSB_WORDS = re.compile(r"\b(lite|lumentum|optic\w*|photonic\w*|mu|micron|cohr|coherent|aaoi)\b", re.I)

BUY = re.compile(r"\b(bought|buying|buy(ing)? (the|this) dip|btd|adding|added|add(ed)? more|loading|loaded|load(ing)? up|"
                 r"reload|scoop\w*|averag\w*|dca|gift|discount|on sale|back in|opened (a )?position|accumulat\w*)\b", re.I)
SELL = re.compile(r"\b(sold|selling|took profits?|trimm?(ed|ing)?|cash(ed)? out|went to cash|exit(ed)?|bought puts|"
                  r"loaded puts|puts printing|shorted|shorting)\b", re.I)
AHEAD = re.compile(r"\b(tomorrow|tmrw|tmr|monday|friday|next week|this week|cpi|earnings|eow)\b", re.I)
UP = re.compile(r"\b(green|rip|bounce|rally|higher|moon|recover\w*|squeeze|gap up|rebound|pump)\b|🚀", re.I)
DOWN = re.compile(r"\b(red|dump|lower|crash|drop|tank|bleed|flush|gap down|black friday|sell ?off|more pain|capitulat\w*)\b", re.I)
TARGET = re.compile(r"price target|\b(upgrade|downgrade)[sd]?\b.{0,60}\b(buy|sell|hold|outperform|"
                    r"overweight|neutral|underperform|underweight)\b", re.I)


def fetch_json(url, opener=None, tries=3):
    for attempt in range(tries):
        try:
            with (opener or urllib.request.build_opener()).open(
                    urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=30) as reply:
                return json.load(reply)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == tries - 1:
                raise
            time.sleep(20 * (attempt + 1))


def fetch_text(url, tries=3):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=30) as reply:
                return reply.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == tries - 1:
                raise
            time.sleep(15 * (attempt + 1))


def window_start(now):
    """The prior weekday's 4:00 PM New York time (holidays ignored)."""
    day = now.astimezone(NY).date() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return datetime.combine(day, dtime(16), NY)


def stocktwits(symbol, since, get=fetch_json):
    posts, max_id = [], None
    for _ in range(PAGES):
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json" + (f"?max={max_id}" if max_id else "")
        messages = get(url).get("messages") or []
        if not messages:
            break
        for m in messages:
            at = datetime.fromisoformat(m["created_at"].replace("Z", "+00:00"))
            if at >= since:
                posts.append({"at": at.isoformat(), "user": m["user"]["username"], "followers": m["user"].get("followers", 0),
                              "likes": (m.get("likes") or {}).get("total", 0),
                              "tag": ((m.get("entities") or {}).get("sentiment") or {}).get("basic"),
                              "text": html.unescape(m["body"]).replace("\n", " ")})
        max_id = messages[-1]["id"] - 1
        if datetime.fromisoformat(messages[-1]["created_at"].replace("Z", "+00:00")) < since:
            break
        time.sleep(1)
    return posts


def classify(texts):
    ahead = [t for t in texts if AHEAD.search(t)]
    return {"posts": len(texts),
            "buying": sum(bool(BUY.search(t)) for t in texts),
            "selling": sum(bool(SELL.search(t)) for t in texts),
            "ahead": len(ahead),
            "ahead_up": sum(bool(UP.search(t)) and not DOWN.search(t) for t in ahead),
            "ahead_down": sum(bool(DOWN.search(t)) and not UP.search(t) for t in ahead)}


def snippet(text, match, before=60, after=160):
    start = max(0, match.start() - before)
    return ("…" if start else "") + text[start:match.end() + after].strip()


def summarize(symbol, posts):
    tags = Counter(p["tag"] for p in posts)
    users = Counter(p["user"] for p in posts)
    top, seen = [], set()
    for p in sorted(posts, key=lambda p: (-p["likes"], p["at"])):
        if p["user"] not in seen:
            seen.add(p["user"])
            top.append(p)
        if len(top) == 5:
            break
    loudest = users.most_common(1)[0] if users else None
    return {"symbol": symbol, **classify([p["text"] for p in posts]), "users": len(users),
            "bullish": tags.get("Bullish", 0), "bearish": tags.get("Bearish", 0),
            "loudest": {"user": loudest[0], "posts": loudest[1]} if loudest and loudest[1] >= 5 else None,
            "targets": [snippet(p["text"], m) for p in posts if (m := TARGET.search(p["text"]))][:4],
            "top": [{k: p[k] for k in ("at", "user", "followers", "likes", "tag", "text")} for p in top]}


def wsb_thread(day, text=fetch_text):
    """Link of WSB's 'Daily Discussion Thread for October 8, 2026' via Reddit's public search RSS, or None."""
    title = f"Daily Discussion Thread for {day:%B} {day.day}, {day.year}"
    url = "https://www.reddit.com/r/wallstreetbets/search.rss?" + urllib.parse.urlencode(
        {"q": title, "restrict_sr": 1, "sort": "new"})
    for entry in ET.fromstring(text(url)).findall("a:entry", ATOM):
        if entry.findtext("a:title", "", ATOM).strip() == title:
            return entry.find("a:link", ATOM).get("href")
    return None


def wsb_comments(link, text=fetch_text):
    root = ET.fromstring(text(link.rstrip("/") + "/.rss?limit=100"))
    comments = []
    for entry in root.findall("a:entry", ATOM)[1:]:  # the first entry is the post itself
        body = re.sub(r"<[^>]+>", " ", html.unescape(entry.findtext("a:content", "", ATOM)))
        body = re.sub(r"\s+", " ", body).strip()
        if body:
            comments.append({"user": entry.findtext("a:author/a:name", "", ATOM).removeprefix("/u/"), "text": body})
    return comments


def prices(symbols):
    from research.covered_call_practice_v1.report import credentials
    key, secret = credentials()
    url = "https://data.alpaca.markets/v2/stocks/snapshots?" + urllib.parse.urlencode({"symbols": ",".join(symbols), "feed": "iex"})
    req = urllib.request.Request(url, headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
    with urllib.request.urlopen(req, timeout=20) as reply:
        snaps = json.load(reply)
    out = {}
    for s, v in snaps.items():
        last, prev = (v.get("latestTrade") or {}).get("p"), (v.get("prevDailyBar") or {}).get("c")
        if last and prev:
            out[s] = {"price": last, "change_pct": 100 * (last / prev - 1)}
    return out


def render(day, rows, wsb, quotes, history):
    lines = [f"LITE chatter, {day:%a %b %d, %Y} (Stocktwits since yesterday 4 PM ET + WallStreetBets daily thread)",
             "Crowd mood is context, not a signal. Keyword counts are rough.", ""]
    lines.append(f"{'':6}{'price':>10}{'today':>8}{'posts':>7}{'users':>7}{'bull/bear':>11}{'buying':>8}{'selling':>9}{'next up/down':>14}")
    for r in rows:
        q = quotes.get(r["symbol"], {})
        price = f"${q['price']:,.2f}" if q else "n/a"
        change = f"{q['change_pct']:+.1f}%" if q else ""
        lines.append(f"{r['symbol']:6}{price:>10}{change:>8}{r['posts']:>7}{r['users']:>7}{r['bullish']:>6}/{r['bearish']:<4}"
                     f"{r['buying']:>8}{r['selling']:>9}{r['ahead_up']:>8}/{r['ahead_down']:<5}")
    lite = next((r for r in rows if r["symbol"] == "LITE"), None)
    prior = history.get((day - timedelta(days=1)).isoformat()) or (history[max(history)] if history else None)
    if lite and prior and prior.get("LITE"):
        p = prior["LITE"]
        lines.append(f"\nLITE vs the previous report: posts {p['posts']} -> {lite['posts']}, "
                     f"bullish tags {p['bullish']} -> {lite['bullish']}, bearish {p['bearish']} -> {lite['bearish']}.")
    for r in rows:
        lines += ["", f"== {r['symbol']}: most-liked posts (one per person)"]
        lines += [f"  [{t['likes']} likes, {t['followers']:,} followers{', ' + t['tag'] if t['tag'] else ''}] {t['text'][:240]}"
                  for t in r["top"]] or ["  (no posts)"]
        if r["targets"]:
            lines.append("  Price-target / rating mentions (unverified, from posts):")
            lines += [f"   - {t}" for t in r["targets"]]
        if r["loudest"]:
            lines.append(f"  Note: one account ({r['loudest']['user']}) wrote {r['loudest']['posts']} of these posts.")
    lines += ["", "== WallStreetBets daily thread"]
    if wsb.get("error"):
        lines.append(f"  Not available today ({wsb['error']}).")
    else:
        c = wsb["counts"]
        lines.append(f"  {c['posts']} comments read: buying {c['buying']}, selling {c['selling']}, "
                     f"talking about what's next {c['ahead']} (up {c['ahead_up']} / down {c['ahead_down']}).")
        lines.append(f"  Comments naming LITE, MU, COHR, AAOI or optics: {len(wsb['relevant'])}")
        lines += [f"   - {c['text'][:240]}" for c in wsb["relevant"][:8]]
        lines.append(f"  Thread: {wsb['link']}")
    lines += ["", "Research only, not advice. You decide every trade."]
    return "\n".join(lines)


def run(now=None):
    now = now or datetime.now(timezone.utc)
    day, since = now.astimezone(NY).date(), window_start(now)
    rows = [summarize(s, stocktwits(s, since)) for s in SYMBOLS]
    try:
        link = wsb_thread(day)
        if not link:
            raise LookupError("thread not found")
        time.sleep(10)
        comments = wsb_comments(link)
        wsb = {"link": link, "counts": classify([c["text"] for c in comments]),
               "relevant": [c for c in comments if WSB_WORDS.search(c["text"])]}
    except Exception as exc:  # Reddit often rate-limits; the email still goes out
        wsb = {"error": type(exc).__name__ + (f": {exc}" if isinstance(exc, LookupError) else "")}
    try:
        quotes = prices(SYMBOLS)
    except Exception:
        quotes = {}
    OUT.mkdir(parents=True, exist_ok=True)
    hist_path = OUT / "history.json"
    history = json.loads(hist_path.read_text()) if hist_path.exists() else {}
    body = render(day, rows, wsb, quotes, {k: v for k, v in history.items() if k < day.isoformat()})
    history[day.isoformat()] = {r["symbol"]: {k: r[k] for k in ("posts", "users", "bullish", "bearish", "buying", "selling")}
                                for r in rows}
    hist_path.write_text(json.dumps(history, indent=1) + "\n")
    (OUT / f"chatter_{day.isoformat()}.json").write_text(json.dumps({"rows": rows, "wsb": wsb, "quotes": quotes}, indent=1) + "\n")
    return body, rows, day


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args()
    body, rows, day = run()
    if args.print:
        print(body)
        return
    from research.real_position_alert_v1.monitor import resend_key, send
    lite = next(r for r in rows if r["symbol"] == "LITE")
    subject = (f"LITE chatter {day.isoformat()}: {lite['posts']} posts, {lite['bullish']} bull / {lite['bearish']} bear, "
               f"buying {lite['buying']} vs selling {lite['selling']}")
    send(subject, body, resend_key(), f"chatter|{day.isoformat()}")
    print(json.dumps({"emailed": True, "lite_posts": lite["posts"]}))


if __name__ == "__main__":
    main()
