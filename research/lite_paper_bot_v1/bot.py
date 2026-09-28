"""LITE paper dip bot v1. Paper trading only; the frozen rules are in PROTOCOL.md.

From the repository root:
  PYTHONPATH=src:. .venv/bin/python -m research.lite_paper_bot_v1.bot --bind    # one-time account lock
  PYTHONPATH=src:. .venv/bin/python -m research.lite_paper_bot_v1.bot --status  # read-only summary
  PYTHONPATH=src:. .venv/bin/python -m research.lite_paper_bot_v1.bot           # the weekday 10:00 run
Credentials come only from the owner-only .env.lite (LITE_PAPER_API_KEY/SECRET).
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time as dtime, timedelta, timezone
import fcntl
from decimal import ROUND_HALF_UP, ROUND_UP, Decimal
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/lite_paper_bot"
KEY_FILE = ROOT / ".env.lite"
KEY_NAMES = ("LITE_PAPER_API_KEY", "LITE_PAPER_API_SECRET")
PAPER = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"
SYMBOL = "LITE"
SHARES = 66  # owner change Sept 28 evening: about $60,000 per trade (paper)
TARGET_MULTIPLIER = Decimal("1.02")
BUY_BUFFER = Decimal("1.001")
MAX_DEBIT = Decimal("72000")
PREFIX = "lite-dip-"
DECIDE_AT, LAST_SUBMIT, CANCEL_AT = dtime(10, 0, 30), dtime(10, 4), dtime(10, 5)
FINAL = {"filled", "canceled", "expired", "rejected"}
CENT = Decimal("0.01")
ORDER_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
D = lambda value: Decimal(str(value))


class Halt(Exception):
    """Unexpected broker state: stop trading until the owner reviews and deletes KILL."""


def ts(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def at(day, clock_time):
    return datetime.combine(day, clock_time, NY)


def iso(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def credentials(path=KEY_FILE):
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise PermissionError("Owner-only .env.lite required (chmod 600 .env.lite)")
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        name, _, value = line.strip().partition("=")
        if name.strip() in KEY_NAMES:
            values[name.strip()] = value.strip().strip("\"'")
    if not all(values.get(name) for name in KEY_NAMES):
        raise ValueError("Set both LITE_PAPER_API_KEY and LITE_PAPER_API_SECRET in .env.lite")
    return values[KEY_NAMES[0]], values[KEY_NAMES[1]]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("redirect_refused")


class PaperBroker:
    """LITE-only Alpaca paper client: reads, one DAY limit buy shape, one GTC limit sell shape, cancel."""

    READS = {(PAPER, "/v2/account"), (PAPER, "/v2/clock"), (PAPER, "/v2/calendar"), (PAPER, "/v2/positions"),
             (PAPER, "/v2/orders"), (PAPER, "/v2/orders:by_client_order_id"), (DATA, "/v2/stocks/LITE/bars"),
             (DATA, "/v2/stocks/LITE/quotes/latest"), (DATA, "/v2/stocks/LITE/trades/latest")}

    def __init__(self, key, secret, opener=None):
        self._key, self._secret = key, secret
        self._opener = opener or build_opener(ProxyHandler({}), NoRedirect())

    def _call(self, method, base, path, query=None, body=None):
        one_order = (base == PAPER and path.startswith("/v2/orders/")
                     and ORDER_ID.fullmatch(path.removeprefix("/v2/orders/")) is not None)
        allowed = ((method == "GET" and ((base, path) in self.READS or one_order))
                   or (method == "POST" and (base, path) == (PAPER, "/v2/orders"))
                   or (method == "DELETE" and one_order))
        if not allowed:
            raise ValueError(f"Blocked request {method} {path}")
        url = base + path + ("?" + urllib.parse.urlencode(query) if query else "")
        request = Request(url, data=None if body is None else json.dumps(body).encode(), method=method, headers={
            "APCA-API-KEY-ID": self._key, "APCA-API-SECRET-KEY": self._secret, "Accept": "application/json",
            "Content-Type": "application/json", "User-Agent": "lite-paper-bot/1"})
        try:
            with self._opener.open(request, timeout=20) as response:
                raw = response.read(5_000_000)
        except urllib.error.HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", "replace").replace(self._key, "[key]").replace(self._secret, "[secret]")
            raise RuntimeError(f"HTTP {exc.code} on {method} {path}: {detail[:300]}") from None
        return json.loads(raw) if raw else None

    def account(self):
        return self._call("GET", PAPER, "/v2/account")

    def clock(self):
        return self._call("GET", PAPER, "/v2/clock")

    def calendar(self, start, end):
        return self._call("GET", PAPER, "/v2/calendar", {"start": start, "end": end})

    def positions(self):
        return self._call("GET", PAPER, "/v2/positions")

    def open_orders(self):
        return self._call("GET", PAPER, "/v2/orders", {"status": "open", "limit": 500})

    def order(self, order_id):
        return self._call("GET", PAPER, "/v2/orders/" + order_id)

    def order_by_client_id(self, client_order_id):
        return self._call("GET", PAPER, "/v2/orders:by_client_order_id", {"client_order_id": client_order_id})

    def bars(self, start, end):
        rows, token = [], None
        for _ in range(5):
            query = {"feed": "iex", "adjustment": "raw", "timeframe": "5Min", "sort": "asc", "limit": 10000,
                     "start": iso(start), "end": iso(end), **({"page_token": token} if token else {})}
            reply = self._call("GET", DATA, "/v2/stocks/LITE/bars", query)
            if reply.get("symbol") != SYMBOL or not isinstance(reply.get("bars"), list):
                raise ValueError("Wrong bar response")
            rows.extend(reply["bars"])
            token = reply.get("next_page_token")
            if not token:
                return rows
        raise ValueError("Bar pages exhausted")

    def latest_quote(self):
        return self._call("GET", DATA, "/v2/stocks/LITE/quotes/latest", {"feed": "iex"})["quote"]

    def latest_trade(self):
        return self._call("GET", DATA, "/v2/stocks/LITE/trades/latest", {"feed": "iex"})["trade"]

    def submit_buy(self, qty, limit, client_order_id):
        if qty != SHARES or limit <= 0 or limit != limit.quantize(CENT) or not client_order_id.startswith(PREFIX):
            raise ValueError(f"Buy must be exactly {SHARES} LITE shares at a positive cent limit")
        return self._call("POST", PAPER, "/v2/orders", body={
            "symbol": SYMBOL, "qty": str(qty), "side": "buy", "type": "limit", "time_in_force": "day",
            "limit_price": str(limit), "client_order_id": client_order_id, "extended_hours": False})

    def submit_sell(self, qty, limit, client_order_id):
        if not 1 <= qty <= SHARES or limit <= 0 or limit != limit.quantize(CENT) or not client_order_id.startswith(PREFIX):
            raise ValueError(f"Sell must be 1-{SHARES} LITE shares at a positive cent limit")
        return self._call("POST", PAPER, "/v2/orders", body={
            "symbol": SYMBOL, "qty": str(qty), "side": "sell", "type": "limit", "time_in_force": "gtc",
            "limit_price": str(limit), "client_order_id": client_order_id, "extended_hours": False})

    def cancel(self, order_id):
        self._call("DELETE", PAPER, "/v2/orders/" + order_id)


def mornings(bars):
    """Complete 09:30-09:55 IEX mornings, by New York date."""
    days = {}
    for bar in bars:
        moment = ts(bar["t"]).astimezone(NY)
        minute = moment.hour * 60 + moment.minute
        if 570 <= minute < 600 and not minute % 5 and not moment.second:
            days.setdefault(moment.date().isoformat(), {})[minute] = bar
    return {day: [rows[m] for m in range(570, 600, 5)] for day, rows in days.items() if len(rows) == 6}


def evaluate(today, prior):
    """Frozen dip rule; rebound and volume are learning-only fields that never change the decision."""
    opening = D(today[0]["o"])
    low = min(D(bar["l"]) for bar in today)
    closes = [D(bar["c"]) for bar in today]
    ratio = None
    if len(prior) == 20:
        base = sum(sum(D(bar["v"]) for bar in morning) for morning in prior) / 20
        ratio = str((sum(D(bar["v"]) for bar in today) / base).quantize(CENT)) if base > 0 else None
    return {"open": str(opening), "low": str(low), "close_0955": str(closes[-1]),
            "dip_pct": str(((low / opening - 1) * 100).quantize(CENT)),
            "signal": low <= opening * Decimal("0.99") and closes[-1] < opening,
            "rebound_learning_only": closes[-3] < closes[-2] < closes[-1],
            "volume_ratio_learning_only": ratio}


def reference_price(broker, now, close, log):
    """Fresh IEX ask, else fresh IEX trade; both must be within 2% of the 09:55 close."""
    for kind, fetch, field, max_age in (("iex_ask", broker.latest_quote, "ap", 30),
                                        ("iex_trade", broker.latest_trade, "p", 60)):
        try:
            row = fetch()
            price, age = D(row.get(field) or 0), (now - ts(row["t"])).total_seconds()
        except Exception as exc:
            log({"type": "PRICE_READ_FAILED", "source": kind, "error": type(exc).__name__})
            continue
        if price > 0 and age <= max_age and abs(price / close - 1) <= Decimal("0.02"):
            return price, kind
    return None, None


def reconcile(broker, state, log, persist=lambda: None):
    """Match the broker to the bot's record; re-place a missing target sell; record a completed sale."""
    positions = broker.positions()
    if any(p.get("symbol") != SYMBOL for p in positions):
        raise Halt("The account holds a position the bot did not create")
    lite = next((p for p in positions if p.get("symbol") == SYMBOL), None)
    orders = broker.open_orders()
    if any(not str(o.get("client_order_id", "")).startswith(PREFIX) or o.get("symbol") != SYMBOL for o in orders):
        raise Halt("The account has an open order the bot did not create")
    held = state.get("position")
    pending = state.get("pending_buy")
    if held is None and pending:
        # An earlier run submitted a buy but stopped before recording the result.
        buy = broker.order_by_client_id(pending["client_order_id"])
        if buy.get("status") not in FINAL:
            raise Halt("An earlier buy order is still open")
        if D(buy.get("filled_qty") or 0) == 0:
            state["pending_buy"] = None
        elif orders:
            raise Halt("An interrupted buy filled, but other bot orders are open")
        else:
            place_target(broker, state, buy, lite, pending["date"], log, persist, "ADOPTED_INTERRUPTED_BUY")
            return
    if held is None:
        if lite is not None or orders:
            raise Halt("LITE shares or a bot order exist without a recorded position")
        return
    if any(o.get("side") == "buy" for o in orders):
        raise Halt("A buy order is open while the bot holds a position")
    sells = [o for o in orders if o.get("side") == "sell"]
    if len(sells) > 1:
        raise Halt("More than one open sell order")
    if lite is None:
        sell = broker.order_by_client_id(held["sell_client_order_id"])
        if sell.get("status") != "filled":
            raise Halt("The LITE position is gone but its target sell did not fill")
        realized = D(sell["filled_qty"]) * D(sell["filled_avg_price"]) - D(held["qty"]) * D(held["avg_fill"])
        closed = {**held, "exit_price": sell["filled_avg_price"], "exit_at": sell.get("filled_at"),
                  "realized_pnl": str(realized.quantize(CENT))}
        state.setdefault("closed", []).append(closed)
        state["position"] = None
        log({"type": "SOLD_AT_TARGET", **closed})
        return
    sell = sells[0] if sells else None
    sold = D(sell.get("filled_qty") or 0) if sell else D(0)
    if lite.get("side") != "long" or D(lite["qty"]) != D(held["qty"]) - sold:
        raise Halt(f"Broker shows {lite['qty']} LITE shares; the bot expected {D(held['qty']) - sold}")
    target = D(held["target"])
    if sell is not None:
        if sell.get("type") != "limit" or D(sell.get("limit_price") or 0) != target or D(sell["qty"]) != D(held["qty"]):
            raise Halt("The open sell order does not match the recorded target")
        return
    count = held.get("sell_replacements", 0) + 1
    client_order_id = f"{PREFIX}{held['entry_date']}-sell-r{count}"
    order = broker.submit_sell(int(D(held["qty"])), target, client_order_id)
    held.update(sell_client_order_id=client_order_id, sell_order_id=order["id"], sell_replacements=count)
    log({"type": "TARGET_SELL_REPLACED", "client_order_id": client_order_id, "target": str(target)})


def enter(broker, state, account, now, sleep, log, persist):
    """At 10:00:30 ET evaluate the dip rule; if flat, buy SHARES, cancel the rest at 10:05, place the +2% sell."""
    today = now().astimezone(NY).date()
    wait = (at(today, DECIDE_AT) - now()).total_seconds()
    if wait > 0:
        sleep(wait)
    if now() > at(today, LAST_SUBMIT):
        log({"type": "LATE_START", "detail": "Started after 10:04 ET; no buy today"})
        return
    calendar = broker.calendar((today - timedelta(days=45)).isoformat(), today.isoformat())
    sessions = [row["date"] for row in calendar if row.get("open") == "09:30"]
    if not sessions or sessions[-1] != today.isoformat():
        log({"type": "NO_STANDARD_SESSION", "detail": "Today is not a standard 09:30 session"})
        return
    prior_days = sessions[:-1][-20:]
    start = at(date.fromisoformat(prior_days[0]), dtime(9, 30)) if prior_days else at(today, dtime(9, 30))
    found = mornings(broker.bars(start, at(today, dtime(9, 59, 59))))
    if today.isoformat() not in found:
        log({"type": "NO_DATA", "detail": "Six complete IEX bars 09:30-09:55 were not available"})
        return
    prior = [found[day] for day in prior_days if day in found]
    result = evaluate(found[today.isoformat()], prior if len(prior) == 20 else [])
    log({"type": "SIGNAL" if result["signal"] else "NO_SIGNAL", **result})
    if not result["signal"]:
        return
    if state.get("position"):
        log({"type": "SIGNAL_SKIPPED_HOLDING"})
        return
    reference, source = reference_price(broker, now(), D(result["close_0955"]), log)
    if reference is None:
        log({"type": "NO_FRESH_PRICE", "detail": "No fresh IEX ask or trade within 2% of the 09:55 close"})
        return
    limit = (reference * BUY_BUFFER).quantize(CENT, rounding=ROUND_HALF_UP)
    debit = limit * SHARES
    if debit > MAX_DEBIT or D(account["cash"]) < debit * Decimal("1.01"):
        log({"type": "INSUFFICIENT_CASH_OR_CAP", "debit": str(debit), "cash": str(account["cash"])})
        return
    if now() > at(today, LAST_SUBMIT):
        log({"type": "LATE_START", "detail": "Passed 10:04 ET before submitting; no buy today"})
        return
    buy_id = f"{PREFIX}{today}-buy"
    state["pending_buy"] = {"date": today.isoformat(), "client_order_id": buy_id}
    persist()
    order = broker.submit_buy(SHARES, limit, buy_id)
    log({"type": "BUY_SUBMITTED", "limit": str(limit), "reference": str(reference), "source": source,
         "order_id": order["id"]})
    deadline = at(today, CANCEL_AT)
    try:
        while order.get("status") not in FINAL and now() < deadline:
            sleep(3)
            order = broker.order(order["id"])
    except Exception:
        try:  # Never leave a buy resting past the 10:00-10:05 window because monitoring failed.
            broker.cancel(order["id"])
        except Exception:
            pass
        raise
    if order.get("status") not in FINAL:
        try:
            broker.cancel(order["id"])
        except RuntimeError as exc:  # For example, it filled just before the cancel arrived.
            log({"type": "CANCEL_REFUSED", "detail": str(exc)[:200]})
        for _ in range(15):
            order = broker.order(order["id"])
            if order.get("status") in FINAL:
                break
            sleep(1)
        else:
            raise Halt("The buy order did not reach a final state after cancelling")
    if D(order.get("filled_qty") or 0) == 0:
        state["pending_buy"] = None
        log({"type": "BUY_UNFILLED", "status": order.get("status")})
        return
    lite = next((p for p in broker.positions() if p.get("symbol") == SYMBOL), None)
    place_target(broker, state, order, lite, today.isoformat(), log, persist, "FILLED_AND_TARGET_PLACED")


def place_target(broker, state, order, lite, entry_date, log, persist, event_type):
    """Record the filled buy, then rest a GTC limit sell at average fill x 1.02, rounded up to the cent."""
    filled = D(order.get("filled_qty") or 0)
    if lite is None or lite.get("side") != "long" or D(lite["qty"]) != filled:
        raise Halt("The filled quantity does not match the broker position")
    average = D(order["filled_avg_price"])
    target = (average * TARGET_MULTIPLIER).quantize(CENT, rounding=ROUND_UP)
    sell_id = f"{PREFIX}{entry_date}-sell"
    state["position"] = {"entry_date": entry_date, "qty": str(filled), "avg_fill": str(average),
                         "target": str(target), "buy_order_id": order["id"], "sell_client_order_id": sell_id,
                         "sell_replacements": 0}
    state["pending_buy"] = None
    persist()
    sell = broker.submit_sell(int(filled), target, sell_id)
    state["position"]["sell_order_id"] = sell["id"]
    log({"type": event_type, "qty": str(filled), "avg_fill": str(average), "target": str(target),
         "sell_order_id": sell["id"]})


def run(broker, state, now, sleep, log, persist, kill_path):
    if kill_path.exists():
        log({"type": "HALTED", "detail": "KILL file present: " + kill_path.read_text().strip()[:300]})
        return
    if not state.get("account_id"):
        log({"type": "NOT_BOUND", "detail": "Run --bind once after creating the LITE bot paper account"})
        return
    account = broker.account()
    if account.get("id") != state["account_id"]:
        raise Halt("These keys belong to a different paper account than the bound one")
    if account.get("status") != "ACTIVE" or account.get("trading_blocked") or account.get("account_blocked"):
        raise Halt("The paper account is not active or is blocked")
    clock = broker.clock()
    if abs((ts(clock["timestamp"]) - now()).total_seconds()) > 60:
        raise Halt("The Mac clock differs from the broker clock by more than 60 seconds")
    if clock.get("is_open") is not True:
        log({"type": "MARKET_CLOSED"})
        return
    reconcile(broker, state, log, persist)
    persist()
    enter(broker, state, account, now, sleep, log, persist)


def holding_line(broker, state):
    held = state.get("position")
    if not held:
        return "Holding: nothing (flat)."
    try:
        price = D(broker.latest_trade()["p"])
    except Exception:
        return f"Holding: {held['qty']} LITE bought {held['entry_date']} at ${held['avg_fill']}; target ${held['target']}."
    change = D(held["qty"]) * (price - D(held["avg_fill"]))
    return (f"Holding: {held['qty']} LITE bought {held['entry_date']} at ${held['avg_fill']} "
            f"(cash tied up ${D(held['qty']) * D(held['avg_fill']):,.2f}). Now ${price}: "
            f"{'+' if change >= 0 else '-'}${abs(change):,.2f}. Target sell waiting at ${held['target']}.")


def summary(events, holding):
    order = ("HALTED", "ERROR", "FILLED_AND_TARGET_PLACED", "ADOPTED_INTERRUPTED_BUY", "SOLD_AT_TARGET",
             "BUY_UNFILLED", "TARGET_SELL_REPLACED", "SIGNAL_SKIPPED_HOLDING", "NO_FRESH_PRICE",
             "INSUFFICIENT_CASH_OR_CAP", "LATE_START", "NO_DATA", "NO_SIGNAL", "MARKET_CLOSED", "NOT_BOUND",
             "NOT_SET_UP")
    kinds = [event["type"] for event in events]
    headline = next((kind for kind in order if kind in kinds), kinds[-1] if kinds else "NO_EVENTS")
    lines = [f"- {event['type']}: " + ", ".join(f"{k}={v}" for k, v in event.items() if k not in ("type", "at"))
             for event in events]
    body = "\n".join(lines + ["", holding, "",
                              "PAPER TRADING ONLY: no real money. Rules: research/lite_paper_bot_v1/PROTOCOL.md"])
    return headline.replace("_", " ").title(), body


def load_state(path):
    return json.loads(path.read_text()) if path.exists() else {}


def save_state(state, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def bind(broker, state, now, etf_key=None, lite_key=None):
    if state.get("account_id"):
        raise SystemExit("Already bound to a paper account; not rebinding")
    if etf_key and lite_key and etf_key == lite_key:
        raise SystemExit(".env.lite holds the ETF bot's paper key; create a separate LITE bot paper account")
    account = broker.account()
    problems = []
    if account.get("status") != "ACTIVE" or account.get("trading_blocked") or account.get("account_blocked"):
        problems.append("account not active or blocked")
    if D(account.get("cash") or 0) < MAX_DEBIT:
        problems.append(f"cash {account.get('cash')} is below ${MAX_DEBIT}")
    if broker.positions():
        problems.append("account already holds positions")
    if broker.open_orders():
        problems.append("account has open orders")
    if problems:
        raise SystemExit("Not binding: " + "; ".join(problems))
    return {"account_id": account["id"], "bound_at": now.isoformat(), "position": None, "closed": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--bind", action="store_true")
    group.add_argument("--status", action="store_true")
    args = parser.parse_args()
    state_path, events_path, kill_path = OUT / "state.json", OUT / "events.jsonl", OUT / "KILL"
    state = load_state(state_path)
    now = lambda: datetime.now(timezone.utc)
    if args.bind or args.status:
        key, secret = credentials()
        broker = PaperBroker(key, secret)
        if args.bind:
            from research.lite_volume_rebound_v1.refresh import credentials as etf_credentials
            state = bind(broker, state, now(), etf_credentials()[0], key)
            save_state(state, state_path)
            print(json.dumps({"bound": True, "bound_at": state["bound_at"]}))
        else:
            account = broker.account()
            print(json.dumps({"bound": bool(state.get("account_id")),
                              "matches_bound_account": account.get("id") == state.get("account_id"),
                              "cash": account.get("cash"), "positions": [(p["symbol"], p["qty"]) for p in broker.positions()],
                              "open_orders": len(broker.open_orders()), "killed": kill_path.exists(),
                              "position": state.get("position"), "closed_trades": len(state.get("closed", []))}, indent=2))
        return
    events = []

    def log(event):
        event = {"at": now().isoformat(), **event}
        events.append(event)
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / "run.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps({"headline": "another run is active; exiting"}))
        return
    broker = None
    try:
        try:
            key, secret = credentials()
        except (OSError, ValueError) as exc:
            log({"type": "NOT_SET_UP", "detail": f"{exc}. Create the LITE bot paper account, save its keys "
                                                 "in .env.lite, then run --bind."})
        else:
            broker = PaperBroker(key, secret)
            run(broker, state, now, time.sleep, log, lambda: save_state(state, state_path), kill_path)
    except Halt as exc:
        kill_path.parent.mkdir(parents=True, exist_ok=True)
        kill_path.write_text(f"{now().isoformat()} {exc}\n")
        log({"type": "HALTED", "detail": str(exc)})
    except Exception as exc:
        log({"type": "ERROR", "detail": f"{type(exc).__name__}: {str(exc)[:300]}"})
    finally:
        if state.get("account_id"):
            save_state(state, state_path)
    holding = holding_line(broker, state) if broker else "Holding: unknown (no broker connection)."
    headline, body = summary(events, holding)
    try:
        from research.real_position_alert_v1.monitor import resend_key, send
        send(f"LITE paper bot {datetime.now(NY):%a %b %d}: {headline}", body, resend_key(),
             f"lite-paper-bot|{datetime.now(NY):%Y-%m-%d}|{len(events)}|{headline}")
    except Exception as exc:
        log({"type": "EMAIL_FAILED", "detail": type(exc).__name__})
    print(json.dumps({"headline": headline, "events": [event["type"] for event in events]}))


if __name__ == "__main__":
    main()
