"""Live paper copier for OWLS analysts AB, TT and Eli (owner request Oct 8, 2026: "Do both please").
Places PAPER orders only, in the covered-call practice account (...U036, keys ALPACA_PAPER_API_* in .env). Runs only
while the owner's Claude session is open: alerts are read from the Discord all-alerts feed in the browser pane, then
this script is called per alert. Entries are copied only if the alert is at most 10 minutes old when processed.

  ... -m research.owls_alerts_v1.copier buy --analyst eli --symbol SPXW261008P07755000 --alert-ts 2026-10-08T13:50:22
  ... -m research.owls_alerts_v1.copier sell --symbol SPXW261008P07755000 --fraction 0.5 --alert-ts ...
  ... -m research.owls_alerts_v1.copier status
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "outputs/owls_alerts/copier_state.json"
PAPER, DATA = "https://paper-api.alpaca.markets", "https://data.alpaca.markets"
STAKE, MAX_STAKE, MAX_AGE_MIN, MAX_OPEN_DOLLARS = 500.0, 800.0, 10, 3000.0


def keys():
    vals = {}
    for line in (ROOT / ".env").read_text().splitlines():
        m = re.fullmatch(r"\s*(?:export\s+)?(ALPACA_PAPER_API_KEY|ALPACA_PAPER_API_SECRET)\s*=\s*(.*?)\s*", line)
        if m:
            vals[m[1]] = m[2].strip("\"'")
    return {"APCA-API-KEY-ID": vals["ALPACA_PAPER_API_KEY"], "APCA-API-SECRET-KEY": vals["ALPACA_PAPER_API_SECRET"],
            "Content-Type": "application/json"}


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=keys(), method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"positions": {}, "log": []}


def save(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=1) + "\n")


def quote(symbol):
    q = call("GET", f"{DATA}/v1beta1/options/quotes/latest?symbols={symbol}&feed=indicative")["quotes"][symbol]
    return float(q["bp"]), float(q["ap"])


def guard():
    acct = call("GET", f"{PAPER}/v2/account")
    if "paper-api" not in PAPER or not acct["account_number"].endswith("U036"):
        raise SystemExit("Not the ...U036 paper account; refusing")
    return acct


def buy(analyst, symbol, alert_ts):
    guard()
    st = state()
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(alert_ts).replace(tzinfo=timezone.utc)).total_seconds() / 60
    if age > MAX_AGE_MIN:
        st["log"].append({"at": datetime.now(timezone.utc).isoformat(), "analyst": analyst, "symbol": symbol, "skipped": f"alert {age:.0f} min old"})
        save(st)
        return print(json.dumps({"skipped": "too old", "age_min": round(age, 1)}))
    open_dollars = sum(p["cost"] for p in st["positions"].values() if p["qty_open"] > 0)
    bid, ask = quote(symbol)
    qty = math.floor(STAKE / (ask * 100)) or (1 if ask * 100 <= MAX_STAKE else 0)
    if qty < 1 or open_dollars + qty * ask * 100 > MAX_OPEN_DOLLARS:
        return print(json.dumps({"skipped": "size", "ask": ask, "open_dollars": open_dollars}))
    o = call("POST", f"{PAPER}/v2/orders", {"symbol": symbol, "qty": str(qty), "side": "buy", "type": "limit",
                                             "limit_price": f"{ask:.2f}", "time_in_force": "day", "position_intent": "buy_to_open",
                                             "client_order_id": f"owls-{analyst}-{uuid.uuid4().hex[:8]}"})
    st["positions"][symbol] = {"analyst": analyst, "alert_ts": alert_ts, "qty": qty, "qty_open": qty, "limit": ask,
                               "cost": qty * ask * 100, "order_id": o["id"], "sells": []}
    st["log"].append({"at": datetime.now(timezone.utc).isoformat(), "buy": symbol, "qty": qty, "limit": ask, "alert_ts": alert_ts})
    save(st)
    print(json.dumps({"bought": symbol, "qty": qty, "limit": ask, "status": o["status"]}))


def sell(symbol, fraction, alert_ts):
    guard()
    st = state()
    p = st["positions"].get(symbol)
    if not p or p["qty_open"] < 1:
        return print(json.dumps({"skipped": "no open copy of " + symbol}))
    qty = p["qty_open"] if fraction >= 0.999 else max(1, round(p["qty"] * fraction))
    qty = min(qty, p["qty_open"])
    bid, ask = quote(symbol)
    o = call("POST", f"{PAPER}/v2/orders", {"symbol": symbol, "qty": str(qty), "side": "sell", "type": "limit",
                                             "limit_price": f"{max(bid, 0.05):.2f}", "time_in_force": "day",
                                             "position_intent": "sell_to_close", "client_order_id": f"owls-x-{uuid.uuid4().hex[:8]}"})
    p["qty_open"] -= qty
    p["sells"].append({"alert_ts": alert_ts, "qty": qty, "limit": bid, "order_id": o["id"]})
    st["log"].append({"at": datetime.now(timezone.utc).isoformat(), "sell": symbol, "qty": qty, "limit": bid, "alert_ts": alert_ts})
    save(st)
    print(json.dumps({"sold": symbol, "qty": qty, "limit": bid, "status": o["status"]}))


def status():
    acct = guard()
    st = state()
    pos = {p["symbol"]: p for p in call("GET", f"{PAPER}/v2/positions")}
    out = {"cash": acct["cash"], "copies": {}}
    for sym, p in st["positions"].items():
        live = pos.get(sym, {})
        out["copies"][sym] = {"analyst": p["analyst"], "qty_open": p["qty_open"], "entry_limit": p["limit"],
                              "unrealized_pl": live.get("unrealized_pl"), "sells": len(p["sells"])}
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("buy"); b.add_argument("--analyst", required=True); b.add_argument("--symbol", required=True); b.add_argument("--alert-ts", required=True)
    s_ = sub.add_parser("sell"); s_.add_argument("--symbol", required=True); s_.add_argument("--fraction", type=float, required=True); s_.add_argument("--alert-ts", required=True)
    sub.add_parser("status")
    a = ap.parse_args()
    if a.cmd == "buy":
        buy(a.analyst, a.symbol, a.alert_ts)
    elif a.cmd == "sell":
        sell(a.symbol, a.fraction, a.alert_ts)
    else:
        status()


if __name__ == "__main__":
    main()
