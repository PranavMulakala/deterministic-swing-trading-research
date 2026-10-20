"""Parse EdwardAlerts' Discord posts into entries, updates, trims, exits and notes, plus the owner's tailing ticket.

Pure functions, no I/O. Only two channels count: VIP #🚨|alerts and free #🚨|trade-ideas. Formats seen Sept 9 - Oct 19, 2026:
  entry:  "$QQQ 720 PUT 10/19 @ 0.73 0DTE LOTTO", "$TSLA 375 CALL 10/16 @ 1.00\\n\\nLOTTO",
          "$HOOD 113 CALL 10/16 @ 1.27 SIZED IN FOR 0", "$SPY 777C 10/7 @ 1.20"
  update: "$QQQ +25% here", "$QQQ UP 94% AT 1.42", "$TSLA @ 1.60 | 60%"
  trim:   "$QQQ @ 1.08 | 47% trimming", "trim most", "out majority", "SOLD MAJORITY"
  exit:   "stopped out", "Gap filled you can sell all"
Owner's tailing rules (output/MONDAY_GAME_PLAN_20261012.md): $300 max per alert, pay at most his price x 1.2,
contracts = $300 / (price x 100) rounded down, then a good-till-canceled sell at the fill x 1.5.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import math
import re

CHANNELS = {  # channel id -> (label, guild id)
    "1324790086885314670": ("vip", "1180233578467053659"),   # "EdwardAlerts" VIP #🚨|alerts
    "1549505694863069297": ("free", "1549505693529411614"),  # "EdwardAlerts A+" free #🚨|trade-ideas
}
BUDGET, CHASE, TARGET = 300.0, 1.2, 1.5
OCC_ROOT = {"SPX": "SPXW"}  # SPX weeklies and 0DTE trade under SPXW

_SYM = r"\$(?P<sym>[A-Za-z]{1,6})\b"
ENTRY = re.compile(_SYM + r"\s+\$?(?P<strike>\d+(?:\.\d+)?)\s*(?P<cp>calls?|puts?|c|p)\b[\s,]*"
                   r"(?P<exp>\d{1,2}/\d{1,2}(?:/\d{2,4})?)[^@\n]{0,24}@\s*\$?(?P<price>\d*\.\d+|\d+)", re.I)
SYM = re.compile(r"\$([A-Za-z]{1,6})\b")
PCT = re.compile(r"(?<![\d.])([+-]?\d+(?:\.\d+)?)\s*%")
AT_PRICE = re.compile(r"(?:@|\bAT\b)\s*\$?(\d*\.\d+|\d+)(?![\d.])(?!\s*%)", re.I)
TAGS = {"0DTE": r"\b0\s?DTE\b", "LOTTO": r"\bLOTTO\b", "SWING": r"\bSWINGS?\b", "HIGH RISK": r"\bHIGH[\s-]?RISK\b",
        "LIGHT": r"\bLIGHT\b", "SIZED FOR 0": r"\bSIZED\b.{0,12}?\b(?:0|ZERO)\b", "LEAPS": r"\bLEAPS?\b"}
TRIM = re.compile(r"\btrim\w*|\bscal(?:e|ing)\s*out\b|\b(?:took|taking)\s*(?:some\s*)?profits?\b"
                  r"|\b(?:out|sold|sell|selling)\s*(?:the\s*)?(?:majority|most|half)\b"
                  r"|\b(?:majority|most|half)\s*(?:out|sold|off)\b", re.I)
EXIT = re.compile(r"\bstop(?:ped)?\s*(?:out|hit)\b|\b(?:sell|sold)\s*(?:it\s*|them\s*)?(?:all|everything|the\s*rest)\b"
                  r"|\b(?:all|fully|completely)\s*out\b|\b(?:i'?m|im|we'?re|were)\s*(?:all\s*)?out\b"
                  r"|\bclosed?\s*(?:it\s*|them\s*)?out\b|\bcut\s*(?:it|the\s*loss|losses)\b"
                  r"|^\s*(?:\$[A-Za-z]{1,6}\s*)?out\b", re.I)


def clean(text):
    """Drop Discord's @everyone / @here pings and direction-isolate marks; collapse whitespace runs."""
    text = re.sub(r"[⁦-⁩​]", "", text or "")
    text = re.sub(r"@(?:everyone|here)\b", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def posted_at(message_id):
    """A Discord message id (snowflake) encodes its post time."""
    return datetime.fromtimestamp(((int(message_id) >> 22) + 1420070400000) / 1000, timezone.utc)


def expiry(text, posted):
    parts = [int(p) for p in text.split("/")]
    if len(parts) == 3:
        return date(parts[2] + (2000 if parts[2] < 100 else 0), parts[0], parts[1])
    guess = date(posted.year, parts[0], parts[1])
    return guess if guess >= posted - timedelta(days=3) else date(posted.year + 1, parts[0], parts[1])


def occ(underlying, exp, cp, strike):
    return f"{OCC_ROOT.get(underlying, underlying)}{exp:%y%m%d}{cp}{round(strike * 1000):08d}"


def tick(price, up=False):
    """Round to a valid option price step: $0.01 under $3, $0.05 from $3."""
    step = 0.01 if price < 3 else 0.05
    n = price / step
    return round((math.ceil(n - 1e-9) if up else math.floor(n + 1e-9)) * step, 2)


def parse(text, posted):
    """One post -> dict with kind in entry / update / trim / exit / note. `posted` is the post date (ET)."""
    t = clean(text)
    m = ENTRY.search(t)
    if m:
        try:
            exp = expiry(m["exp"], posted)
        except ValueError:
            return {"kind": "note", "text": t, "error": f"bad expiry {m['exp']}"}
        sym, cp, strike = m["sym"].upper(), m["cp"][0].upper(), float(m["strike"])
        return {"kind": "entry", "text": t, "underlying": sym, "strike": strike, "cp": cp, "expiry": exp.isoformat(),
                "price": float(m["price"]), "symbol": occ(sym, exp, cp, strike),
                "tags": [k for k, rx in TAGS.items() if re.search(rx, t, re.I)], "zero_dte": exp == posted}
    sym = SYM.search(t)
    pct, price = PCT.search(t), AT_PRICE.search(t)
    kind = "trim" if TRIM.search(t) else "exit" if EXIT.search(t) else "update" if (sym and (pct or price)) else "note"
    return {"kind": kind, "text": t, "underlying": sym[1].upper() if sym else None,
            "pct": float(pct[1]) if pct else None, "price": float(price[1]) if price else None}


def ticket(price):
    """The owner's rules for one alert at his posted price: the most to pay and how many contracts."""
    cap = tick(price * CHASE)
    at_his = math.floor(BUDGET / (price * 100) + 1e-9)
    at_cap = math.floor(BUDGET / (cap * 100) + 1e-9)
    if at_his == 0:
        line = f"Skip: 1 contract costs ${price * 100:,.0f}, over your ${BUDGET:,.0f} limit."
    elif at_cap == at_his:
        line = f"Buy {at_cap} at up to ${cap:.2f} (max ${at_cap * cap * 100:,.0f}). Skip above ${cap:.2f}."
    else:
        more = tick(BUDGET / (at_his * 100))
        rest = f"else {at_cap} up to ${cap:.2f}" if at_cap else "skip above that"
        line = f"Buy {at_his} if you can get ≤ ${more:.2f}, {rest}."
    return {"max_price": cap, "contracts_at_his_price": at_his, "contracts_at_max": at_cap, "line": line}


def contracts(ask):
    return math.floor(BUDGET / (ask * 100) + 1e-9)


def push_text(ev, label, author=""):
    """(title, message, Pushover priority) for one parsed post. Entries repeat until acknowledged."""
    who = label.upper()
    if ev["kind"] == "entry":
        t = ticket(ev["price"])
        cp = "CALL" if ev["cp"] == "C" else "PUT"
        exp = date.fromisoformat(ev["expiry"])
        title = f"🚨 {who}: {ev['underlying']} {ev['strike']:g} {cp} {exp.month}/{exp.day} @ {ev['price']:.2f}"
        tags = " · ".join(ev["tags"])
        lines = [tags] if tags else []
        lines += [t["line"]]
        if t["contracts_at_his_price"]:
            lines += [f"Then sell GTC at your fill × {TARGET:g}."]
        return title, "\n".join(lines + ["", f"Edward: {ev['text']}"]), 2
    icon = {"update": "📈", "trim": "✂️", "exit": "🛑", "note": "💬"}[ev["kind"]]
    head = ev["underlying"] or (author or "Edward")
    bits = [f"+{ev['pct']:g}%" if ev.get("pct") and ev["pct"] > 0 else f"{ev['pct']:g}%" if ev.get("pct") else "",
            f"at {ev['price']:.2f}" if ev.get("price") else ""]
    title = f"{icon} {who} {ev['kind'].upper()}: {head} {' '.join(b for b in bits if b)}".strip()
    return title, ev["text"] or "(no text)", 0 if ev["kind"] == "note" else 1
