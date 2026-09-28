"""SPY bull put spread paper bot v1. Paper trading only; the frozen rules are in PROTOCOL.md.

From the repository root:
  PYTHONPATH=src:. .venv/bin/python -m research.spy_put_spread_v1.bot --bind            # one-time account lock
  PYTHONPATH=src:. .venv/bin/python -m research.spy_put_spread_v1.bot --status          # read-only summary
  PYTHONPATH=src:. .venv/bin/python -m research.spy_put_spread_v1.bot --plumbing-test   # one-contract open/close check
  PYTHONPATH=src:. .venv/bin/python -m research.spy_put_spread_v1.bot                   # the weekday 10:30 run
Credentials come only from the owner-only .env.options (OPTIONS_PAPER_API_KEY/SECRET).
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time as dtime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal
import fcntl
import json
import math
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
OUT = ROOT / "outputs/spy_put_spread_bot"
KEY_FILE = ROOT / ".env.options"
KEY_NAMES = ("OPTIONS_PAPER_API_KEY", "OPTIONS_PAPER_API_SECRET")
PAPER = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"
WIDTH = Decimal("5")
TARGET_DELTA = Decimal("0.20")
MIN_CREDIT = Decimal("0.75")
RISK = Decimal("0.02")
MAX_CONTRACTS = 5
IV_RV_MIN = Decimal("1.2")
DTE_MIN, DTE_MAX, DTE_TARGET = 21, 35, 30
TIME_EXIT_SESSIONS = 5
PREFIX = "spy-bps-"
FINAL = {"filled", "canceled", "expired", "rejected"}
CENT = Decimal("0.01")
OCC = re.compile(r"SPY(\d{2})(\d{2})(\d{2})P(\d{8})")
ORDER_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
D = lambda value: Decimal(str(value))


class Halt(Exception):
    """Unexpected broker state: stop trading until the owner reviews and deletes KILL."""


def ts(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def at(day, clock_time=dtime(0)):
    return datetime.combine(day, clock_time, NY)


def iso(moment):
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cents(value):
    return value.quantize(CENT, rounding=ROUND_DOWN)


def parse_occ(symbol):
    """SPY put OCC symbol -> (expiration date, strike). Anything else raises."""
    match = OCC.fullmatch(symbol or "")
    if not match:
        raise ValueError(f"Not a SPY put contract: {symbol}")
    yy, mm, dd, strike = match.groups()
    return date(2000 + int(yy), int(mm), int(dd)), D(int(strike)) / 1000


def credentials(path=KEY_FILE):
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise PermissionError("Owner-only .env.options required (chmod 600 .env.options)")
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        name, _, value = line.strip().partition("=")
        if name.strip() in KEY_NAMES:
            values[name.strip()] = value.strip().strip("\"'")
    if not all(values.get(name) for name in KEY_NAMES):
        raise ValueError("Set both OPTIONS_PAPER_API_KEY and OPTIONS_PAPER_API_SECRET in .env.options")
    return values[KEY_NAMES[0]], values[KEY_NAMES[1]]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("redirect_refused")


class PaperBroker:
    """SPY-put-spread-only Alpaca paper client: listed reads, one validated multi-leg order shape, cancel."""

    READS = {(PAPER, "/v2/account"), (PAPER, "/v2/clock"), (PAPER, "/v2/calendar"), (PAPER, "/v2/positions"),
             (PAPER, "/v2/orders"), (PAPER, "/v2/orders:by_client_order_id"), (DATA, "/v2/stocks/SPY/bars"),
             (DATA, "/v1beta1/options/snapshots/SPY")}

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
            "Content-Type": "application/json", "User-Agent": "spy-put-spread-bot/1"})
        try:
            with self._opener.open(request, timeout=20) as response:
                raw = response.read(10_000_000)
        except urllib.error.HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", "replace").replace(self._key, "[key]").replace(self._secret, "[secret]")
            raise RuntimeError(f"HTTP {exc.code} on {method} {path}: {detail[:300]}") from None
        return json.loads(raw) if raw else None

    def account(self):
        return self._call("GET", PAPER, "/v2/account")

    def clock(self):
        return self._call("GET", PAPER, "/v2/clock")

    def calendar(self, start, end):
        return self._call("GET", PAPER, "/v2/calendar", {"start": start.isoformat(), "end": end.isoformat()})

    def positions(self):
        return self._call("GET", PAPER, "/v2/positions")

    def open_orders(self):
        return self._call("GET", PAPER, "/v2/orders", {"status": "open", "limit": 500, "nested": "true"})

    def order(self, order_id):
        return self._call("GET", PAPER, "/v2/orders/" + order_id, {"nested": "true"})

    def order_by_client_id(self, client_order_id):
        return self._call("GET", PAPER, "/v2/orders:by_client_order_id", {"client_order_id": client_order_id})

    def daily_bars(self, start, end):
        query = {"feed": "sip", "adjustment": "all", "timeframe": "1Day", "sort": "asc", "limit": 1000,
                 "start": iso(start), "end": iso(end)}
        reply = self._call("GET", DATA, "/v2/stocks/SPY/bars", query)
        if reply.get("symbol") != "SPY" or not isinstance(reply.get("bars"), list) or reply.get("next_page_token"):
            raise ValueError("Unexpected SPY daily bar response")
        return reply["bars"]

    def put_snapshots(self, exp_from, exp_to, strike_from, strike_to):
        rows, token = {}, None
        for _ in range(10):
            query = {"feed": "indicative", "type": "put", "limit": 1000,
                     "expiration_date_gte": exp_from.isoformat(), "expiration_date_lte": exp_to.isoformat(),
                     "strike_price_gte": str(strike_from), "strike_price_lte": str(strike_to),
                     **({"page_token": token} if token else {})}
            reply = self._call("GET", DATA, "/v1beta1/options/snapshots/SPY", query)
            rows.update(reply.get("snapshots") or {})
            token = reply.get("next_page_token")
            if not token:
                return rows
        raise ValueError("Option snapshot pages exhausted")

    def submit_spread(self, short_symbol, long_symbol, qty, limit_price, intent, time_in_force, client_order_id):
        """The only order shape: a SPY bull put spread, opened for a credit or closed for a debit."""
        short_exp, short_strike = parse_occ(short_symbol)
        long_exp, long_strike = parse_occ(long_symbol)
        valid = (short_exp == long_exp and short_strike - long_strike == WIDTH
                 and isinstance(qty, int) and 1 <= qty <= MAX_CONTRACTS and time_in_force in ("day", "gtc")
                 and limit_price == limit_price.quantize(CENT) and client_order_id.startswith(PREFIX)
                 and ((intent == "open" and -WIDTH < limit_price < 0)
                      or (intent == "close" and 0 < limit_price <= WIDTH)))
        if not valid:
            raise ValueError("Refused: not a valid SPY bull put spread order")
        opening = intent == "open"
        legs = [{"symbol": short_symbol, "ratio_qty": "1", "side": "sell" if opening else "buy",
                 "position_intent": "sell_to_open" if opening else "buy_to_close"},
                {"symbol": long_symbol, "ratio_qty": "1", "side": "buy" if opening else "sell",
                 "position_intent": "buy_to_open" if opening else "sell_to_close"}]
        return self._call("POST", PAPER, "/v2/orders", body={
            "order_class": "mleg", "qty": str(qty), "type": "limit", "limit_price": str(limit_price),
            "time_in_force": time_in_force, "client_order_id": client_order_id, "legs": legs})

    def cancel(self, order_id):
        self._call("DELETE", PAPER, "/v2/orders/" + order_id)


def market_view(broker, today):
    """SPY's last completed close, 50-day average and 20-day realized volatility (annualized)."""
    bars = broker.daily_bars(at(today - timedelta(days=130)), at(today))
    closes = [D(bar["c"]) for bar in bars if ts(bar["t"]).astimezone(NY).date() < today]
    if len(closes) < 51:
        raise ValueError("Not enough SPY history")
    returns = [math.log(float(b / a)) for a, b in zip(closes[-21:], closes[-20:])]
    mean = sum(returns) / len(returns)
    rv20 = math.sqrt(sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)) * math.sqrt(252)
    return {"last_close": closes[-1], "sma50": sum(closes[-50:]) / 50, "rv20": D(round(rv20, 6))}


def choose_spread(broker, today, last_close):
    """Pick the expiration (21-35 DTE, nearest 30), the ~0.20-delta short put and the put $5 lower."""
    snaps = broker.put_snapshots(today + timedelta(days=DTE_MIN), today + timedelta(days=DTE_MAX),
                                 cents(last_close * Decimal("0.80")), cents(last_close * Decimal("1.02")))
    rows = []
    for symbol, snap in snaps.items():
        try:
            expiration, strike = parse_occ(symbol)
        except ValueError:
            continue
        quote = snap.get("latestQuote") or {}
        delta = (snap.get("greeks") or {}).get("delta")
        rows.append({"symbol": symbol, "expiration": expiration, "strike": strike,
                     "bid": D(quote.get("bp") or 0), "ask": D(quote.get("ap") or 0),
                     "delta": None if delta is None else D(delta), "iv": snap.get("impliedVolatility")})
    quoted = [r for r in rows if r["bid"] > 0 and r["ask"] >= r["bid"]]
    if not quoted:
        return None
    expiration = min({r["expiration"] for r in quoted}, key=lambda e: (abs((e - today).days - DTE_TARGET), e))
    chain = {r["strike"]: r for r in quoted if r["expiration"] == expiration}
    atm = min(chain.values(), key=lambda r: abs(r["strike"] - last_close))
    candidates = [r for r in chain.values() if r["delta"] is not None and r["strike"] - WIDTH in chain]
    if not candidates or atm["iv"] is None:
        return None
    short = min(candidates, key=lambda r: (abs(abs(r["delta"]) - TARGET_DELTA), -r["strike"]))
    long = chain[short["strike"] - WIDTH]
    mid = (short["bid"] + short["ask"]) / 2 - (long["bid"] + long["ask"]) / 2
    return {"expiration": expiration, "short": short, "long": long, "atm_iv": D(atm["iv"]),
            "mid_credit": cents(mid), "natural_credit": cents(short["bid"] - long["ask"])}


def settle(broker, order, now, sleep, log, seconds):
    """Wait for a final status; cancel at the deadline; never leave an order silently working."""
    deadline = now() + timedelta(seconds=seconds)
    try:
        while order.get("status") not in FINAL and now() < deadline:
            sleep(3)
            order = broker.order(order["id"])
    except Exception:
        try:
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
            raise Halt("An order did not reach a final state after cancelling")
    return order


def leg_qty(broker, held):
    positions = {p["symbol"]: p for p in broker.positions()}
    short, long = positions.get(held["short"]), positions.get(held["long"])
    return (D(short["qty"]) if short else D(0), D(long["qty"]) if long else D(0), short, long)


def net_price(order):
    """Per-spread price of a filled multi-leg order: sells minus buys, from the leg fills."""
    legs = order.get("legs") or []
    if legs and all(leg.get("filled_avg_price") is not None for leg in legs):
        return sum((D(l["filled_avg_price"]) if l.get("side") == "sell" else -D(l["filled_avg_price"])) for l in legs)
    return -D(order.get("filled_avg_price") or 0)


def place_profit_take(broker, held, log, count):
    limit = cents(D(held["credit"]) / 2)
    if limit <= 0:
        raise Halt("The recorded credit is too small for a profit-take order")
    client_order_id = f"{PREFIX}{held['entry_date']}-tp-{count}"
    order = broker.submit_spread(held["short"], held["long"], int(D(held["qty"])), limit, "close", "gtc", client_order_id)
    held.update(tp_order_id=order["id"], tp_client_order_id=client_order_id, tp_count=count, tp_limit=str(limit))
    log({"type": "PROFIT_TAKE_PLACED", "limit": str(limit), "qty": held["qty"]})
    return order


def record_open(broker, state, pick, order, entry_date, log, persist, plumbing):
    """Confirm short and long legs by position, compute the actual credit, and record the spread."""
    held = {"entry_date": entry_date, "expiration": pick["expiration"].isoformat(), "short": pick["short"]["symbol"],
            "long": pick["long"]["symbol"], "short_strike": str(pick["short"]["strike"]),
            "open_order_id": order["id"], "plumbing": plumbing}
    short_qty, long_qty, short_pos, long_pos = leg_qty(broker, held)
    if short_qty >= 0 or long_qty != -short_qty:
        raise Halt(f"Leg check failed after the fill: short {short_qty}, long {long_qty}")
    credit = D(short_pos["avg_entry_price"]) - D(long_pos["avg_entry_price"])
    if credit <= 0:
        raise Halt(f"The spread opened for a debit ({credit}), not a credit")
    qty = -short_qty
    held.update(qty=str(qty), credit=str(credit), breakeven=str(D(held["short_strike"]) - credit),
                max_loss=str((WIDTH - credit) * 100 * qty))
    state["position"], state["pending_open"] = held, None
    persist()
    log({"type": "PLUMBING_OPENED" if plumbing else "SPREAD_OPENED", "short": held["short"], "long": held["long"],
         "qty": str(qty), "credit": str(credit), "breakeven": held["breakeven"], "max_loss": held["max_loss"]})
    return held


def close_spread(broker, state, now, sleep, log, persist, reason):
    """Cancel the profit-take, buy the spread back at a marketable limit, and confirm the account is flat."""
    held = state["position"]
    if held.get("tp_order_id"):
        tp = broker.order(held["tp_order_id"])
        if tp.get("status") not in FINAL:
            try:
                broker.cancel(tp["id"])
            except RuntimeError as exc:
                log({"type": "CANCEL_REFUSED", "detail": str(exc)[:200]})
            tp = settle(broker, broker.order(tp["id"]), now, sleep, log, 20)
        if tp.get("status") == "filled" and leg_qty(broker, held)[0] == 0:
            return finish(state, held, net_price(tp), "profit_take", log, persist)
    short_qty, long_qty, _, _ = leg_qty(broker, held)
    if short_qty >= 0 or long_qty != -short_qty:
        raise Halt(f"Leg check failed before closing: short {short_qty}, long {long_qty}")
    count = held.get("close_count", 0) + 1
    held["close_count"] = count
    persist()
    order = broker.submit_spread(held["short"], held["long"], int(-short_qty), WIDTH, "close", "day",
                                 f"{PREFIX}{held['entry_date']}-close-{count}")
    order = settle(broker, order, now, sleep, log, 60)
    if order.get("status") != "filled" or leg_qty(broker, held)[:2] != (0, 0):
        raise Halt(f"The closing order did not leave the account flat (status {order.get('status')})")
    return finish(state, held, net_price(order), reason, log, persist)


def finish(state, held, close_net, reason, log, persist):
    debit = -close_net
    realized = (D(held["credit"]) - debit) * 100 * D(held["qty"])
    closed = {**held, "exit_reason": reason, "debit": str(debit), "realized_pnl": str(realized.quantize(CENT))}
    state.setdefault("plumbing_tests" if held.get("plumbing") else "closed", []).append(closed)
    state["position"] = None
    persist()
    log({"type": "SPREAD_CLOSED", "reason": reason, "debit": str(debit), "realized_pnl": closed["realized_pnl"],
         "plumbing": bool(held.get("plumbing"))})
    return closed


def reconcile(broker, state, log, persist):
    """Match the broker to the record; adopt an interrupted open; notice a filled profit-take."""
    held = state.get("position")
    legs = {held["short"], held["long"]} if held else set()
    positions = broker.positions()
    if any(p.get("symbol") not in legs for p in positions):
        raise Halt("The account holds a position the bot did not create (possible assignment)")
    orders = broker.open_orders()
    if any(not str(o.get("client_order_id", "")).startswith(PREFIX) for o in orders):
        raise Halt("The account has an open order the bot did not create")
    pending = state.get("pending_open")
    if held is None:
        if pending:
            order = broker.order_by_client_id(pending["client_order_id"])
            if order.get("status") not in FINAL:
                raise Halt("An earlier opening order is still working")
            if D(order.get("filled_qty") or 0) > 0:
                raise Halt("An earlier opening order filled while the bot was interrupted; review it")
            state["pending_open"] = None
            persist()
        if positions or orders:
            raise Halt("Positions or bot orders exist without a recorded spread")
        return
    short_qty, long_qty, _, _ = leg_qty(broker, held)
    if short_qty == 0 and long_qty == 0:
        tp = broker.order_by_client_id(held["tp_client_order_id"]) if held.get("tp_client_order_id") else {}
        if tp.get("status") == "filled":
            finish(state, held, net_price(tp), "profit_take", log, persist)
            return
        raise Halt("The spread disappeared without a recorded fill (expiration or assignment?)")
    if short_qty >= 0 or long_qty != -short_qty or -short_qty > D(held["qty"]):
        raise Halt(f"Leg quantities do not match the record: short {short_qty}, long {long_qty}")
    if -short_qty < D(held["qty"]):  # A partial profit-take fill: keep the remainder working.
        tp = broker.order(held["tp_order_id"])
        if D(held["qty"]) - D(tp.get("filled_qty") or 0) != -short_qty:
            raise Halt("A partial fill does not reconcile")


def manage(broker, state, view, today, now, sleep, log, persist):
    held = state["position"]
    sessions = [row["date"] for row in broker.calendar(today + timedelta(days=1), date.fromisoformat(held["expiration"]))]
    if view["last_close"] < D(held["breakeven"]):
        close_spread(broker, state, now, sleep, log, persist, "breakeven")
        return True
    if len(sessions) <= TIME_EXIT_SESSIONS:
        close_spread(broker, state, now, sleep, log, persist, "time")
        return True
    tp = broker.order(held["tp_order_id"]) if held.get("tp_order_id") else {}
    if tp.get("status") in FINAL or not tp:
        place_profit_take(broker, held, log, held.get("tp_count", 0) + 1)
        persist()
    log({"type": "HOLDING", "short": held["short"], "qty": held["qty"], "credit": held["credit"],
         "breakeven": held["breakeven"], "sessions_left": len(sessions)})
    return False


def open_spread(broker, state, account, view, today, now, sleep, log, persist, plumbing=False):
    pick = choose_spread(broker, today, view["last_close"])
    if pick is None:
        log({"type": "NO_ENTRY", "reason": "no usable quoted chain in the 21-35 day window"})
        return
    ratio = pick["atm_iv"] / view["rv20"] if view["rv20"] > 0 else Decimal(0)
    check = {"last_close": str(view["last_close"]), "sma50": str(cents(view["sma50"])),
             "trend_ok": view["last_close"] > view["sma50"], "atm_iv": str(pick["atm_iv"]), "rv20": str(view["rv20"]),
             "iv_rv": str(cents(ratio)), "vol_ok": ratio >= IV_RV_MIN, "expiration": pick["expiration"].isoformat(),
             "short": pick["short"]["symbol"], "short_delta": str(pick["short"]["delta"]), "long": pick["long"]["symbol"],
             "mid_credit": str(pick["mid_credit"]), "credit_ok": pick["mid_credit"] >= MIN_CREDIT}
    log({"type": "SIGNAL_CHECK", **check})
    if not plumbing and not (check["trend_ok"] and check["vol_ok"] and check["credit_ok"]):
        log({"type": "NO_ENTRY", "reason": ", ".join(k for k in ("trend_ok", "vol_ok", "credit_ok") if not check[k])})
        return
    if plumbing:
        qty, prices = 1, [max(pick["natural_credit"], CENT)]
    else:
        qty = min(MAX_CONTRACTS, int(D(account["equity"]) * RISK // ((WIDTH - pick["mid_credit"]) * 100)))
        prices = [p for p in (pick["mid_credit"], pick["mid_credit"] - Decimal("0.05")) if p >= MIN_CREDIT]
    if qty < 1 or not prices:
        log({"type": "NO_ENTRY", "reason": "size or price rule"})
        return
    for attempt, credit in enumerate(prices, 1):
        client_order_id = f"{PREFIX}{today}-{'test' if plumbing else 'open'}-{attempt}"
        state["pending_open"] = {"client_order_id": client_order_id, "date": today.isoformat()}
        persist()
        order = broker.submit_spread(pick["short"]["symbol"], pick["long"]["symbol"], qty, -credit, "open", "day",
                                     client_order_id)
        log({"type": "OPEN_SUBMITTED", "credit_limit": str(credit), "qty": qty, "attempt": attempt})
        order = settle(broker, order, now, sleep, log, 60)
        if D(order.get("filled_qty") or 0) > 0:
            held = record_open(broker, state, pick, order, today.isoformat(), log, persist, plumbing)
            if not plumbing:
                place_profit_take(broker, held, log, 1)
                persist()
            return held
    state["pending_open"] = None
    persist()
    log({"type": "OPEN_UNFILLED"})


def preflight(broker, state, now, kill_path, log):
    if kill_path.exists():
        log({"type": "HALTED", "detail": "KILL file present: " + kill_path.read_text().strip()[:300]})
        return None
    if not state.get("account_id"):
        log({"type": "NOT_BOUND", "detail": "Run --bind once after creating the Options bot paper account"})
        return None
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
        return None
    return account


def run(broker, state, now, sleep, log, persist, kill_path):
    account = preflight(broker, state, now, kill_path, log)
    if account is None:
        return
    reconcile(broker, state, log, persist)
    persist()
    today = now().astimezone(NY).date()
    view = market_view(broker, today)
    exited = manage(broker, state, view, today, now, sleep, log, persist) if state.get("position") else False
    if today.weekday() != 0:
        return
    if exited:
        log({"type": "NO_ENTRY", "reason": "a spread was closed today; no same-day replacement (no rolling)"})
    elif state.get("position") is None:
        open_spread(broker, state, account, view, today, now, sleep, log, persist)


def plumbing_test(broker, state, now, sleep, log, persist, kill_path):
    account = preflight(broker, state, now, kill_path, log)
    if account is None:
        return
    reconcile(broker, state, log, persist)
    if state.get("position"):
        raise SystemExit("A spread is open; the plumbing test needs a flat account")
    today = now().astimezone(NY).date()
    view = market_view(broker, today)
    held = open_spread(broker, state, account, view, today, now, sleep, log, persist, plumbing=True)
    if held is None:
        return
    tp = place_profit_take(broker, held, log, 1)
    persist()
    broker.cancel(tp["id"])
    tp = settle(broker, broker.order(tp["id"]), now, sleep, log, 20)
    log({"type": "PROFIT_TAKE_CANCEL_CHECK", "status": tp.get("status")})
    close_spread(broker, state, now, sleep, log, persist, "plumbing_test")


def bind(broker, state, now, other_keys, other_accounts=frozenset()):
    if state.get("account_id"):
        raise SystemExit("Already bound to a paper account; not rebinding")
    if other_keys:
        raise SystemExit(".env.options reuses another bot's paper key; use the separate Options bot account")
    account = broker.account()
    if account.get("id") in other_accounts:
        raise SystemExit("These keys open another bot's paper account (LITE or ETF). Select the Options bot "
                         "account in Alpaca before generating keys.")
    problems = []
    if account.get("status") != "ACTIVE" or account.get("trading_blocked") or account.get("account_blocked"):
        problems.append("account not active or blocked")
    level = account.get("options_trading_level", account.get("options_approved_level"))
    if level is not None and int(level) < 3:
        problems.append(f"options level {level} is below 3 (spreads need level 3)")
    if D(account.get("equity") or 0) < 10000:
        problems.append("equity below $10,000")
    if broker.positions():
        problems.append("account already holds positions")
    if broker.open_orders():
        problems.append("account has open orders")
    if problems:
        raise SystemExit("Not binding: " + "; ".join(problems))
    return {"account_id": account["id"], "bound_at": now.isoformat(), "position": None, "closed": []}


def summary(events, state):
    order = ("HALTED", "ERROR", "SPREAD_OPENED", "PLUMBING_OPENED", "SPREAD_CLOSED", "OPEN_UNFILLED",
             "PROFIT_TAKE_PLACED", "HOLDING", "NO_ENTRY", "MARKET_CLOSED", "NOT_BOUND", "NOT_SET_UP")
    kinds = [event["type"] for event in events]
    headline = next((kind for kind in order if kind in kinds), kinds[-1] if kinds else "NO_EVENTS")
    lines = [f"- {e['type']}: " + ", ".join(f"{k}={v}" for k, v in e.items() if k not in ("type", "at")) for e in events]
    held = state.get("position")
    status = (f"Open spread: {held['qty']} x {held['short']} / {held['long']}, credit ${held['credit']}, "
              f"break-even SPY ${held['breakeven']}, max loss ${held['max_loss']}." if held else "No open spread.")
    closed = state.get("closed", [])
    total = sum(D(c["realized_pnl"]) for c in closed)
    body = "\n".join(lines + ["", status, f"Closed strategy trades: {len(closed)}, total ${total:,.2f}.", "",
                              "PAPER TRADING ONLY: no real money. Rules: research/spy_put_spread_v1/PROTOCOL.md"])
    return headline.replace("_", " ").title(), body


def load_state(path):
    return json.loads(path.read_text()) if path.exists() else {}


def save_state(state, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True, default=str) + "\n")
    os.replace(temporary, path)


def other_bot_keys(key):
    """True if .env.options reuses the ETF/research or LITE paper key."""
    found = []
    try:
        from research.lite_volume_rebound_v1.refresh import credentials as etf_credentials
        found.append(etf_credentials()[0])
    except Exception:
        pass
    try:
        from research.lite_paper_bot_v1.bot import credentials as lite_credentials
        found.append(lite_credentials()[0])
    except Exception:
        pass
    return key in found


def other_bot_accounts():
    """Account IDs this bot must never bind to: the LITE bot's bound account and the ETF/research account."""
    ids = set()
    try:
        ids.add(json.loads((ROOT / "outputs/lite_paper_bot/state.json").read_text())["account_id"])
    except Exception:
        pass
    try:
        from research.lite_volume_rebound_v1.refresh import credentials as etf_credentials
        ids.add(PaperBroker(*etf_credentials()).account()["id"])
    except Exception:
        pass
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--bind", action="store_true")
    group.add_argument("--status", action="store_true")
    group.add_argument("--plumbing-test", action="store_true")
    args = parser.parse_args()
    state_path, events_path, kill_path = OUT / "state.json", OUT / "events.jsonl", OUT / "KILL"
    state = load_state(state_path)
    now = lambda: datetime.now(timezone.utc)
    if args.bind or args.status:
        key, secret = credentials()
        broker = PaperBroker(key, secret)
        if args.bind:
            state = bind(broker, state, now(), other_bot_keys(key), other_bot_accounts())
            save_state(state, state_path)
            print(json.dumps({"bound": True, "bound_at": state["bound_at"]}))
        else:
            account = broker.account()
            print(json.dumps({"bound": bool(state.get("account_id")),
                              "matches_bound_account": account.get("id") == state.get("account_id"),
                              "equity": account.get("equity"),
                              "options_level": account.get("options_trading_level", account.get("options_approved_level")),
                              "positions": [(p["symbol"], p["qty"]) for p in broker.positions()],
                              "open_orders": len(broker.open_orders()), "killed": kill_path.exists(),
                              "position": state.get("position"), "closed_trades": len(state.get("closed", [])),
                              "plumbing_tests": len(state.get("plumbing_tests", []))}, indent=2, default=str))
        return
    events = []

    def log(event):
        event = {"at": now().isoformat(), **event}
        events.append(event)
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")

    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / "run.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps({"headline": "another run is active; exiting"}))
        return
    persist = lambda: save_state(state, state_path)
    try:
        try:
            key, secret = credentials()
        except (OSError, ValueError) as exc:
            log({"type": "NOT_SET_UP", "detail": f"{exc}. Save the Options bot paper keys in .env.options, then run --bind."})
        else:
            broker = PaperBroker(key, secret)
            action = plumbing_test if args.plumbing_test else run
            action(broker, state, now, time.sleep, log, persist, kill_path)
    except Halt as exc:
        kill_path.parent.mkdir(parents=True, exist_ok=True)
        kill_path.write_text(f"{now().isoformat()} {exc}\n")
        log({"type": "HALTED", "detail": str(exc)})
    except Exception as exc:
        log({"type": "ERROR", "detail": f"{type(exc).__name__}: {str(exc)[:300]}"})
    finally:
        if state.get("account_id"):
            persist()
    headline, body = summary(events, state)
    try:
        from research.real_position_alert_v1.monitor import resend_key, send
        send(f"SPY spread paper bot {datetime.now(NY):%a %b %d}: {headline}", body, resend_key(),
             f"spy-bps|{datetime.now(NY):%Y-%m-%d %H}|{len(events)}|{headline}")
    except Exception as exc:
        log({"type": "EMAIL_FAILED", "detail": type(exc).__name__})
    print(json.dumps({"headline": headline, "events": [event["type"] for event in events]}))


if __name__ == "__main__":
    main()
