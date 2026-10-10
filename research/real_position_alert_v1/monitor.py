"""Price-only email alerts for Pranav's real positions (LITE, plus any level with its own "symbol"). Never trades.

One-shot run (launchd calls this every two minutes):
PYTHONPATH=src:. .venv/bin/python -m research.real_position_alert_v1.monitor
Add --test-email to send one delivery test, or --status to print levels only.

Each run reads the market clock and IEX one-minute bars (LITE by default; a level may name
another symbol whose shares/average live under "positions") through the
allowlisted GET-only client. A level emails once, when a bar at or after its
arming time trades through it; a level with `requires` arms only after that
other level has fired. Email uses Resend's test sender, which delivers only to
the Resend account owner's address. No broker account, position, or order
endpoint is used, and Robinhood is never contacted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).resolve().parent / "position.json"
STATE = ROOT / "outputs/real_position_alert/state.json"
BAR_PATH = "/v2/stocks/LITE/bars"
SENDER = "LITE position alert <onboarding@resend.dev>"
RECIPIENT = "pranavm1104@gmail.com"
KEY_NAME = "TRADING_REPORT_RESEND_API_KEY"
MAX_PAGES = 10
D = lambda value: Decimal(str(value))


def resend_key(path=ROOT / ".env"):
    """Read only the Resend key from the owner-only .env; never print it."""
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise PermissionError("Owner-only .env required")
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"\s*(?:export\s+)?" + KEY_NAME + r"\s*=\s*(.*?)\s*", line)
        if match:
            values.append(match[1].strip().strip("\"'"))
    if len(values) != 1 or not re.fullmatch(r"re_[A-Za-z0-9_-]+", values[0]):
        raise ValueError("Exactly one valid Resend key is required")
    return values[0]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("mail_redirect_refused")


def send(subject, body, key, idempotency, opener=None):
    payload = json.dumps({"from": SENDER, "to": [RECIPIENT], "subject": subject,
                          "text": body}, sort_keys=True).encode()
    request = Request("https://api.resend.com/emails", data=payload, method="POST", headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json",
        "User-Agent": "lite-position-alert/1.0",
        "Idempotency-Key": "lite-alert-" + hashlib.sha256(idempotency.encode()).hexdigest()})
    opener = opener or build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=20) as response:
        reply = json.loads(response.read(16384))
    if not isinstance(reply.get("id"), str) or not reply["id"]:
        raise ValueError("mail_receipt_missing")
    return reply["id"]


def bar_time(bar):
    return datetime.fromisoformat(bar["t"].replace("Z", "+00:00"))


def bar_path(symbol):
    if not re.fullmatch(r"[A-Z]{1,5}", symbol):
        raise ValueError("Bad symbol")
    return f"/v2/stocks/{symbol}/bars"


def fetch_bars(client, start, end, symbol="LITE"):
    rows, token = [], None
    for _ in range(MAX_PAGES):
        query = {"feed": "iex", "adjustment": "raw", "timeframe": "1Min", "sort": "asc", "limit": 1000,
                 "start": start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "end": end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 **({"page_token": token} if token else {})}
        reply = client._request("GET", bar_path(symbol), data_api=True, query=query)
        if not isinstance(reply, dict) or reply.get("symbol") != symbol or not isinstance(reply.get("bars"), list):
            raise ValueError("Wrong bar response")
        rows.extend(reply["bars"])
        token = reply.get("next_page_token")
        if not token:
            return rows
    raise ValueError("Bar page budget exhausted")


def position_line(config, price):
    shares, average = D(config["shares"]), D(config["average_cost"])
    change = shares * (price - average)
    return (f"At ${price:,.2f}, your {shares} shares (average ${average:,.2f}) are worth "
            f"${shares * price:,.2f}: {'+' if change >= 0 else '-'}${abs(change):,.2f} "
            f"({(price / average - 1) * 100:+.2f}%).")


def symbol_of(config, level):
    return level.get("symbol", config.get("symbol", "LITE"))


def position_of(config, symbol):
    if symbol == config.get("symbol", "LITE"):
        return config
    return config["positions"][symbol]


def run(client, config, state, now, key, opener=None):
    """Check once; returns the updated state and the ids of levels emailed this run."""
    clock = client._request("GET", "/v2/clock")
    if clock.get("is_open") is not True:
        return state, []
    fired = state.setdefault("fired", {})
    pending = [level for level in config["levels"] if level["id"] not in fired]
    sent = []
    for symbol in sorted({symbol_of(config, level) for level in pending}):
        levels = [level for level in pending if symbol_of(config, level) == symbol]
        sent += check_symbol(client, config, state, now, key, opener, symbol, levels)
    return state, sent


def check_symbol(client, config, state, now, key, opener, symbol, pending):
    fired = state["fired"]
    default = symbol == config.get("symbol", "LITE")
    by_symbol = state.setdefault("checked_through_by_symbol", {})
    session_open = datetime.combine(now.astimezone(NY).date(), time(9, 30), NY)
    earliest = min(datetime.fromisoformat(level["armed_at"]) for level in pending)
    checked = by_symbol.get(symbol) or (state.get("checked_through") if default else None)
    start = max(earliest, datetime.fromisoformat(checked) if checked else earliest,
                session_open - timedelta(days=7))
    bars = [bar for bar in fetch_bars(client, start, now, symbol) if bar_time(bar) >= start]
    if not bars:
        return []
    sent = []
    for level in pending:
        requires = level.get("requires")
        armed = datetime.fromisoformat(level["armed_at"])
        if requires:
            if requires not in fired:
                continue
            armed = max(armed, datetime.fromisoformat(fired[requires]["bar_time"]))
        price = D(level["price"])
        hit = next((bar for bar in bars if bar_time(bar) >= armed and (
            D(bar["l"]) <= price if level["direction"] == "down" else D(bar["h"]) >= price)), None)
        if hit is None:
            continue
        when = bar_time(hit).astimezone(NY)
        last = D(bars[-1]["c"])
        subject = f"{symbol} {level['label']}: traded {'at/below' if level['direction'] == 'down' else 'at/above'} ${price:,.2f}"
        body = "\n".join((
            f"{symbol} traded {'at or below' if level['direction'] == 'down' else 'at or above'} ${price:,.2f} "
            f"in the minute starting {when:%H:%M} ET on {when:%a %b %d}.",
            f"Latest IEX price: ${last:,.2f} ({bar_time(bars[-1]).astimezone(NY):%H:%M} ET).",
            position_line(position_of(config, symbol), last),
            "",
            "Informational only. No order was placed; this alert cannot trade.",
            "Prices come from the IEX exchange feed and can differ slightly from Robinhood's.",
        ))
        try:
            email_id = send(subject, body, key, f"{level['id']}|{level['price']}|{level['armed_at']}", opener)
        except Exception as exc:  # Unsent levels stay pending; Resend's idempotency key prevents duplicates.
            state["last_send_error"] = {"level": level["id"], "at": now.isoformat(), "error": type(exc).__name__}
            continue
        fired[level["id"]] = {"bar_time": hit["t"], "sent_at": now.isoformat(), "email_id": email_id}
        sent.append(level["id"])
    by_symbol[symbol] = bars[-1]["t"]
    if default:
        state["checked_through"] = bars[-1]["t"]
    return sent


def save_state(state, path=STATE):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-email", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = datetime.now(timezone.utc)
    if args.status:
        for level in config["levels"]:
            print(f"{symbol_of(config, level):>4} {level['id']:>22} {level['direction']:>4} ${D(level['price']):,.2f}  "
                  f"{'FIRED ' + state['fired'][level['id']]['bar_time'] if level['id'] in state.get('fired', {}) else 'waiting'}")
        return
    if args.test_email:
        email_id = send("LITE alert test", "Delivery test for your LITE price alerts. No order was placed.",
                        resend_key(), f"test|{now.astimezone(NY):%Y-%m-%d}")
        print(json.dumps({"test_email": "accepted_by_resend", "has_receipt": bool(email_id)}))
        return
    from research.lite_volume_rebound_v1.refresh import client_from_local_keys
    state, sent = run(client_from_local_keys(), config, state, now, resend_key())
    save_state(state)
    print(json.dumps({"checked_at": now.astimezone(NY).isoformat(timespec="seconds"),
                      "checked_through": state.get("checked_through"), "sent": sent}))


if __name__ == "__main__":
    main()
