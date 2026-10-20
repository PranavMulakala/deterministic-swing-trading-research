"""Paper copy of EdwardAlerts entries in the ...U036 Alpaca paper account. Never real money.

The owner's tailing rules (output/MONDAY_GAME_PLAN_20261012.md), applied mechanically:
  - copy only alerts at most 10 minutes old, while the market is open, once per contract;
  - limit buy at the current ask if it is at most his price x 1.2 (else skip); $300 max: contracts = 300 / (ask x 100);
  - not filled within 60 s -> canceled; once filled, a sell at the fill x 1.5 (good-till-canceled; day on expiry day);
  - his explicit full exit ("stopped out", "sell all") closes the copy at the bid; trims are logged, not followed;
  - copies still open at 3:45 PM ET on expiry day are sold at the bid; no new copies once this week is at -$1,500.
State: outputs/edward_live/copier_state.json (gitignored). Client order ids start "edw-", so these orders never mix
with the covered-call practice or OWLS copies in the same account.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import re
import time as clock
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from research.edward_live_v1.parse import BUDGET, CHASE, TARGET, contracts, tick

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "outputs/edward_live/copier_state.json"
PAPER, DATA = "https://paper-api.alpaca.markets", "https://data.alpaca.markets"
ACCOUNT_SUFFIX = "U036"
NY = ZoneInfo("America/New_York")
MAX_AGE_MIN, FILL_WAIT_S, WEEK_STOP, CLOSE_OUT, RECHECK_S = 10, 60, -1500.0, time(15, 45), 20
LIVE = {"new", "accepted", "pending_new", "partially_filled", "held", "accepted_for_bidding", "pending_replace",
        "replaced", "calculated", "pending_cancel"}
ACTIVE = ("pending", "open", "exiting")


class Alpaca:
    """Minimal paper client. Refuses to send an order unless the account number ends in U036."""

    def __init__(self, env=ROOT / ".env", opener=urllib.request.urlopen):
        vals = {}
        for line in Path(env).read_text().splitlines():
            m = re.fullmatch(r"\s*(?:export\s+)?(ALPACA_PAPER_API_KEY|ALPACA_PAPER_API_SECRET)\s*=\s*(.*?)\s*", line)
            if m:
                vals[m[1]] = m[2].strip("\"'")
        self.headers = {"APCA-API-KEY-ID": vals["ALPACA_PAPER_API_KEY"],
                        "APCA-API-SECRET-KEY": vals["ALPACA_PAPER_API_SECRET"], "Content-Type": "application/json"}
        self.opener, self.checked = opener, False

    def call(self, method, url, body=None):
        req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                     headers=self.headers, method=method)
        with self.opener(req, timeout=15) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}

    def guard(self):
        if not self.checked:
            acct = self.call("GET", f"{PAPER}/v2/account")
            if not PAPER.startswith("https://paper-api.") or not acct["account_number"].endswith(ACCOUNT_SUFFIX):
                raise SystemExit(f"Not the ...{ACCOUNT_SUFFIX} paper account; refusing")
            self.checked = True

    def quote(self, symbol):
        q = self.call("GET", f"{DATA}/v1beta1/options/quotes/latest?"
                      + urllib.parse.urlencode({"symbols": symbol, "feed": "indicative"}))
        q = q.get("quotes", {}).get(symbol)
        return (float(q["bp"]), float(q["ap"])) if q else (None, None)

    def submit(self, payload):
        self.guard()
        return self.call("POST", f"{PAPER}/v2/orders", payload)

    def order(self, order_id):
        return self.call("GET", f"{PAPER}/v2/orders/{order_id}")

    def cancel(self, order_id):
        try:
            self.call("DELETE", f"{PAPER}/v2/orders/{order_id}")
        except urllib.error.HTTPError as exc:
            if exc.code not in (404, 422):  # already filled / canceled
                raise


def et(ts):
    return ts.astimezone(NY)


def market_open(now):
    t = et(now)
    return t.weekday() < 5 and time(9, 30) <= t.time() < time(16, 0)


def pretty(c):
    m = re.fullmatch(r"([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})", c["symbol"])
    return f"{c['underlying']} {int(m[6]) / 1000:g}{m[5]} {int(m[3])}/{int(m[4])}" if m else c["symbol"]


class Copier:
    def __init__(self, api, state_path=STATE, sleep=clock.sleep):
        self.api, self.path, self.sleep = api, Path(state_path), sleep
        self.st = json.loads(self.path.read_text()) if self.path.exists() else {"copies": {}, "log": []}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.st, indent=1) + "\n")
        tmp.replace(self.path)

    def log(self, now, **kv):
        self.st["log"] = (self.st["log"] + [{"at": now.isoformat(), **kv}])[-500:]

    def active(self):
        return [c for c in self.st["copies"].values() if c["status"] in ACTIVE]

    def week_pnl(self, now):
        start = et(now).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=et(now).weekday())
        total = 0.0
        for c in self.st["copies"].values():
            if c.get("fill") is None or datetime.fromisoformat(c["alert_ts"]) < start:
                continue
            total += c.get("realized", 0.0)
            if c["status"] in ("open", "exiting") and c.get("mark") is not None:
                total += (c["mark"] - c["fill"]) * c["qty_open"] * 100
        return round(total, 2)

    # ---- entries -------------------------------------------------------------------------------------------
    def entry(self, ev, msg_id, label, alert_ts, now):
        if msg_id in self.st["copies"]:
            return None
        c = {"msg_id": msg_id, "channel": label, "symbol": ev["symbol"], "underlying": ev["underlying"],
             "expiry": ev["expiry"], "posted": ev["price"], "alert_ts": alert_ts.isoformat(), "status": "skipped"}
        cap = tick(ev["price"] * CHASE)
        reason = self._skip(ev, alert_ts, now)
        ask = None
        if not reason:
            bid, ask = self.api.quote(ev["symbol"])
            c.update(bid_at_alert=bid, ask_at_alert=ask, cap=cap)
            if not ask:
                reason = "no quote for this contract"
            elif ask > cap:
                reason = f"ask {ask:.2f} is above your max {cap:.2f} (his {ev['price']:.2f} + 20%)"
            elif contracts(ask) < 1:
                reason = f"one contract costs ${ask * 100:,.0f}, over ${BUDGET:,.0f}"
        if reason:
            c["reason"] = reason
            self.st["copies"][msg_id] = c
            self.log(now, skip=c["symbol"], reason=reason)
            self.save()
            return {"summary": f"Paper copy skipped: {reason}.", "copy": c}
        qty, limit = contracts(ask), tick(ask)
        o = self.api.submit({"symbol": c["symbol"], "qty": str(qty), "side": "buy", "type": "limit",
                             "limit_price": f"{limit:.2f}", "time_in_force": "day", "position_intent": "buy_to_open",
                             "client_order_id": f"edw-b-{msg_id}"})
        c.update(status="pending", qty=qty, limit=limit, buy_id=o["id"], submitted_at=now.isoformat(), realized=0.0)
        self.st["copies"][msg_id] = c
        self.log(now, buy=c["symbol"], qty=qty, limit=limit)
        for _ in range(6):  # paper fills are usually instant; report the fill in the same push when it is
            self.sleep(0.5)
            self._check_buy(c, now)
            if c["status"] != "pending":
                break
        self.save()
        if c["status"] == "open":
            target = f"sell order at {c['tp_price']:.2f}" if c.get("tp_id") else "sell order FAILED, check the log"
            return {"summary": f"Paper copy: bought {c['qty']} {pretty(c)} at {c['fill']:.2f} "
                               f"(his {c['posted']:.2f}); {target}.", "copy": c}
        if c["status"] == "canceled":
            return {"summary": f"Paper copy failed: {c['reason']}.", "copy": c}
        return {"summary": f"Paper copy: buy order for {qty} {pretty(c)} at {limit:.2f} is working "
                           f"(canceled if not filled in {FILL_WAIT_S} s).", "copy": c}

    def _skip(self, ev, alert_ts, now):
        t, exp = et(now), date.fromisoformat(ev["expiry"])
        if not market_open(now):
            return "market closed"
        if (now - alert_ts).total_seconds() > MAX_AGE_MIN * 60:
            return f"alert is {(now - alert_ts).total_seconds() / 60:.0f} min old"
        if exp < t.date() or (exp == t.date() and t.time() >= CLOSE_OUT):
            return "too close to expiry"
        if any(c["symbol"] == ev["symbol"] for c in self.active()):
            return "already holding a copy of this contract"
        if self.week_pnl(now) <= WEEK_STOP:
            return f"this week is at ${self.week_pnl(now):,.0f}, past your -$1,500 stop"
        return None

    # ---- order follow-up (called every loop) ---------------------------------------------------------------
    def tick(self, now):
        changed = False
        for c in self.active():
            last = c.get("checked_at")
            if c["status"] != "pending" and last and (now - datetime.fromisoformat(last)).total_seconds() < RECHECK_S:
                continue
            c["checked_at"] = now.isoformat()
            if c["status"] == "pending":
                self._check_buy(c, now)
            else:
                self._check_open(c, now)
            changed = True
        if changed:
            self.save()

    def _check_buy(self, c, now):
        o = self.api.order(c["buy_id"])
        filled = int(float(o.get("filled_qty") or 0))
        if o["status"] == "filled" or (filled and o["status"] not in LIVE):
            self._opened(c, o, filled, now)
        elif o["status"] in LIVE:
            if (now - datetime.fromisoformat(c["submitted_at"])).total_seconds() > FILL_WAIT_S and not c.get("cancel_sent"):
                self.api.cancel(c["buy_id"])
                c["cancel_sent"] = True
        else:
            c.update(status="canceled", reason=f"buy {o['status']} without a fill")
            self.log(now, canceled=c["symbol"], why=o["status"])

    def _opened(self, c, o, filled, now):
        c.update(status="open", fill=float(o["filled_avg_price"]), qty=filled, qty_open=filled,
                 cost=round(float(o["filled_avg_price"]) * filled * 100, 2), filled_at=o.get("filled_at"),
                 mark=float(o["filled_avg_price"]))
        self.log(now, filled=c["symbol"], qty=filled, price=c["fill"])
        self._place_target(c, now)

    def _place_target(self, c, now):
        target = tick(c["fill"] * TARGET, up=True)
        n = c.get("tp_count", 0) + 1
        tifs = ["day"] if c["expiry"] == et(now).date().isoformat() else ["gtc", "day"]
        for tif in tifs:
            try:
                o = self.api.submit({"symbol": c["symbol"], "qty": str(c["qty_open"]), "side": "sell", "type": "limit",
                                     "limit_price": f"{target:.2f}", "time_in_force": tif,
                                     "position_intent": "sell_to_close", "client_order_id": f"edw-t-{c['msg_id']}-{n}"})
            except urllib.error.HTTPError as exc:
                c["tp_error"] = f"{tif}: HTTP {exc.code}"
                continue
            c.update(tp_id=o["id"], tp_price=target, tp_tif=tif, tp_count=n, tp_filled=0)
            return
        self.log(now, target_failed=c["symbol"], error=c.get("tp_error"))

    def _check_open(self, c, now):
        t = et(now)
        for key in ("tp_id", "exit_id"):
            if not c.get(key):
                continue
            o = self.api.order(c[key])
            if key == "exit_id" and o["status"] in LIVE and not c.get("exit_cancel_sent") and \
                    (now - datetime.fromisoformat(c["exit_at"])).total_seconds() > FILL_WAIT_S:
                self.api.cancel(c[key])  # stale exit price: the next check re-sends it at the new bid
                c["exit_cancel_sent"] = True
            done_key = key.replace("_id", "_filled")
            filled = int(float(o.get("filled_qty") or 0))
            new = filled - c.get(done_key, 0)
            if new > 0:
                c["realized"] = round(c.get("realized", 0.0) + (float(o["filled_avg_price"]) - c["fill"]) * new * 100, 2)
                c["qty_open"] -= new
                c[done_key] = filled
            if o["status"] not in LIVE:
                c[key] = None
        if c["qty_open"] <= 0:
            c.update(status="closed", closed_at=now.isoformat(), pnl=c["realized"])
            self.log(now, closed=c["symbol"], pnl=c["pnl"])
            return
        if c["expiry"] < t.date().isoformat():
            c.update(status="expired", pnl=None, reason="still open after expiry (Mac was off at 3:45 PM?); check the account")
            self.log(now, expired=c["symbol"])
            return
        bid, _ = self.api.quote(c["symbol"])
        if bid is not None:
            c["mark"] = bid
        if c["status"] == "exiting" and not c.get("exit_id") and market_open(now):
            self.close(c, c.get("exit_reason", "retry"), now)  # the exit order ended unfilled: try again at the new bid
        elif c["status"] == "open" and c["expiry"] == t.date().isoformat() and t.time() >= CLOSE_OUT and market_open(now):
            self.close(c, "expiry-day close-out at 3:45 PM", now)
        elif c["status"] == "open" and not c.get("tp_id") and market_open(now):
            self._place_target(c, now)  # a day target ended overnight: place it again

    # ---- exits ---------------------------------------------------------------------------------------------
    def exit(self, ev, label, now):
        """His full-exit post closes matching copies (by ticker; with no ticker, the channel's only open copy)."""
        hits = [c for c in self.active() if c["status"] in ("pending", "open")
                and (c["underlying"] == ev["underlying"] if ev["underlying"] else c["channel"] == label)]
        if not ev["underlying"] and len(hits) != 1:
            return None
        out = []
        for c in hits:
            if c["status"] == "pending":
                self.api.cancel(c["buy_id"])
                c["cancel_sent"] = True
                out.append(f"canceled the unfilled buy for {pretty(c)}")
            elif market_open(now):
                self.close(c, "his exit post", now)
                out.append(f"selling {c['qty_open']} {pretty(c)} at {c.get('exit_price', 0):.2f}")
        self.save()
        return {"summary": "Paper copy: " + "; ".join(out) + "."} if out else None

    def close(self, c, reason, now):
        if c.get("tp_id"):
            self.api.cancel(c["tp_id"])
            for _ in range(10):  # the shares stay reserved until the target order is really canceled
                o = self.api.order(c["tp_id"])
                if o["status"] not in LIVE:
                    break
                self.sleep(0.5)
            filled = int(float(o.get("filled_qty") or 0))
            new = filled - c.get("tp_filled", 0)
            if new > 0:
                c["realized"] = round(c["realized"] + (float(o["filled_avg_price"]) - c["fill"]) * new * 100, 2)
                c["qty_open"] -= new
                c["tp_filled"] = filled
            c["tp_id"] = None
        if c["qty_open"] <= 0:
            c.update(status="closed", closed_at=now.isoformat(), pnl=c["realized"])
            return
        bid, _ = self.api.quote(c["symbol"])
        c["exit_reason"] = reason
        if not bid:
            c.update(status="exiting", exit_id=None, exit_note="no bid; will retry")
            return
        n = c.get("exit_count", 0) + 1
        price = tick(bid)
        o = self.api.submit({"symbol": c["symbol"], "qty": str(c["qty_open"]), "side": "sell", "type": "limit",
                             "limit_price": f"{price:.2f}", "time_in_force": "day", "position_intent": "sell_to_close",
                             "client_order_id": f"edw-x-{c['msg_id']}-{n}"})
        c.update(status="exiting", exit_id=o["id"], exit_price=price, exit_count=n, exit_filled=0,
                 exit_at=now.isoformat(), exit_cancel_sent=False)
        self.log(now, exit=c["symbol"], qty=c["qty_open"], price=price, reason=reason)

    # ---- report --------------------------------------------------------------------------------------------
    def report(self, now):
        rows = sorted(self.st["copies"].values(), key=lambda c: c["alert_ts"])
        return {"week_pnl": self.week_pnl(now), "copies": [
            {"when": et(datetime.fromisoformat(c["alert_ts"])).strftime("%m/%d %H:%M"), "channel": c["channel"],
             "contract": pretty(c), "his": c["posted"], "ask_at_alert": c.get("ask_at_alert"), "fill": c.get("fill"),
             "qty": c.get("qty"), "status": c["status"], "pnl": c.get("pnl"),
             "open_pnl": round((c["mark"] - c["fill"]) * c["qty_open"] * 100, 2)
             if c["status"] in ("open", "exiting") and c.get("mark") is not None else None,
             "note": c.get("reason") or c.get("exit_reason")} for c in rows]}
