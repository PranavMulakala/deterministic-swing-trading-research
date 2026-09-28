"""Offline tests for the SPY bull put spread paper bot: simulated broker, chain, clock and HTTP only."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
import tempfile
import unittest
import uuid

from research.spy_put_spread_v1 import bot

MONDAY = date(2026, 10, 5)
NO_KILL = Path("/nonexistent-spy-bot/KILL")


class Clock:
    def __init__(self, day=MONDAY, hour=10, minute=30):
        self.t = datetime(day.year, day.month, day.day, hour, minute, tzinfo=bot.NY)

    def now(self):
        return self.t.astimezone(timezone.utc)

    def sleep(self, seconds):
        self.t += timedelta(seconds=seconds)


def symbol(exp, strike):
    return f"SPY{exp:%y%m%d}P{int(Decimal(str(strike)) * 1000):08d}"


class FakeBroker:
    """Simulated Alpaca paper account with one SPY put expiration about 30 days out."""

    def __init__(self, clock, trend="up", iv=0.14, price_scale=20.0, fill="fill", close_debit="3.00", last=765.0):
        self.time, self.trend, self.iv, self.scale, self.fill = clock, trend, iv, price_scale, fill
        self.close_debit, self.last = Decimal(close_debit), last
        self.today = clock.t.date()
        self.exp = self.today + timedelta(days=30)
        self.pos, self.orders, self.submits = {}, {}, []
        self.account_id, self.is_open = "acct-opt", True

    def account(self):
        return {"id": self.account_id, "status": "ACTIVE", "equity": "100000", "options_trading_level": 3}

    def clock(self):
        return {"timestamp": self.time.now().isoformat(), "is_open": self.is_open}

    def calendar(self, start, end):
        out, day = [], start
        while day <= end:
            if day.weekday() < 5:
                out.append({"date": day.isoformat(), "open": "09:30", "close": "16:00"})
            day += timedelta(days=1)
        return out

    def daily_bars(self, start, end):
        days = [d["date"] for d in self.calendar(self.today - timedelta(days=120), self.today - timedelta(days=1))]
        closes, price = [], self.last
        for i in range(len(days)):  # Build backwards so the last close equals self.last.
            closes.append(price)
            step = 0.006 if i % 2 else -0.005
            price = price / (1 + step) if self.trend == "up" else price * (1 + abs(step))
        closes.reverse()
        return [{"t": f"{d}T04:00:00Z", "c": c} for d, c in zip(days, closes)]

    def _mid(self, strike):
        m = (self.last - strike) / self.last
        return round(self.scale * math.exp(-40 * max(m, -0.05)), 2)

    def put_snapshots(self, exp_from, exp_to, strike_from, strike_to):
        rows = {}
        if not exp_from <= self.exp <= exp_to:
            return rows
        for k in range(int(strike_from) + 1, int(strike_to) + 1):
            m = (self.last - k) / self.last
            mid = self._mid(k)
            rows[symbol(self.exp, k)] = {"latestQuote": {"bp": round(mid - 0.02, 2), "ap": round(mid + 0.02, 2)},
                                         "greeks": {"delta": -max(0.02, 0.5 - 8 * m)}, "impliedVolatility": self.iv}
        return rows

    def positions(self):
        return [{"symbol": s, "qty": str(q), "avg_entry_price": str(p)} for s, (q, p) in self.pos.items() if q]

    def open_orders(self):
        return [dict(o) for o in self.orders.values() if o["status"] in ("new", "partially_filled")]

    def order(self, order_id):
        return dict(self.orders[order_id])

    def order_by_client_id(self, client_order_id):
        return dict(next(o for o in self.orders.values() if o["client_order_id"] == client_order_id))

    def _legs(self, short, long, short_price, long_price, opening):
        return [{"symbol": short, "side": "sell" if opening else "buy", "filled_avg_price": str(short_price)},
                {"symbol": long, "side": "buy" if opening else "sell", "filled_avg_price": str(long_price)}]

    def submit_spread(self, short, long, qty, limit_price, intent, tif, client_order_id):
        if any(o["client_order_id"] == client_order_id for o in self.orders.values()):
            raise RuntimeError("HTTP 422 duplicate client_order_id")
        self.submits.append((intent, str(limit_price), tif, qty, client_order_id))
        order = {"id": str(uuid.uuid4()), "client_order_id": client_order_id, "status": "new", "filled_qty": "0",
                 "intent": intent, "tif": tif, "qty": str(qty), "limit": limit_price, "short": short, "long": long,
                 "legs": []}
        self.orders[order["id"]] = order
        if intent == "open" and self.fill == "fill":
            short_price = Decimal("4.00")
            self._fill(order, short_price, short_price + limit_price, opening=True)
        elif intent == "close" and tif == "day":
            self._fill(order, self.close_debit + Decimal("1.00"), Decimal("1.00"), opening=False)
        return dict(order)

    def _fill(self, order, short_price, long_price, opening):
        qty = Decimal(order["qty"])
        order.update(status="filled", filled_qty=str(qty),
                     legs=self._legs(order["short"], order["long"], short_price, long_price, opening))
        if opening:
            self.pos[order["short"]] = (-qty, short_price)
            self.pos[order["long"]] = (qty, long_price)
        else:
            self.pos[order["short"]] = (Decimal(0), 0)
            self.pos[order["long"]] = (Decimal(0), 0)

    def fill_resting_take_profit(self):
        tp = next(o for o in self.orders.values() if o["intent"] == "close" and o["status"] == "new")
        self._fill(tp, tp["limit"] + Decimal("0.30"), Decimal("0.30"), opening=False)

    def cancel(self, order_id):
        order = self.orders[order_id]
        if order["status"] == "filled":
            raise RuntimeError("HTTP 422 order already filled")
        order["status"] = "canceled"


def bound(**extra):
    return {"account_id": "acct-opt", "position": None, "closed": [], **extra}


def run(broker, state, clock, action=bot.run, kill=NO_KILL):
    events = []
    action(broker, state, clock.now, clock.sleep, events.append, lambda: None, kill)
    return [e["type"] for e in events], events


def opened(clock=None, **kwargs):
    """A broker and state holding a freshly opened 5-lot spread with its resting profit-take."""
    clock = clock or Clock()
    broker = FakeBroker(clock, **kwargs)
    state = bound()
    run(broker, state, clock)
    return broker, state, clock


class EntryTests(unittest.TestCase):
    def test_monday_entry_sells_020_delta_and_buys_5_lower_for_a_credit(self):
        broker, state, _ = opened()
        held = state["position"]
        self.assertTrue(held["short"].endswith("P00736000") and held["long"].endswith("P00731000"))
        # 20 x exp(-40m) mids: 736 -> 4.39, 731 -> 3.38, so the mid credit is 1.01.
        self.assertEqual(broker.submits[0][:4], ("open", "-1.01", "day", 5))   # negative = credit
        self.assertEqual(held["credit"], "1.01")
        self.assertEqual(held["breakeven"], "734.99")
        self.assertEqual(broker.submits[1][:4], ("close", "0.50", "gtc", 5))  # 50% profit-take, positive = debit
        self.assertEqual(held["max_loss"], "1995.00")

    def test_filters_block_entry(self):
        for kwargs, reason in (({"trend": "down"}, "trend_ok"), ({"iv": 0.09}, "vol_ok"),
                               ({"price_scale": 8.0}, "credit_ok")):
            with self.subTest(reason=reason):
                clock = Clock()
                broker = FakeBroker(clock, **kwargs)
                kinds, events = run(broker, bound(), clock)
                self.assertEqual(kinds, ["SIGNAL_CHECK", "NO_ENTRY"])
                self.assertIn(reason, events[-1]["reason"])
                self.assertEqual(broker.submits, [])

    def test_only_mondays_open(self):
        clock = Clock(day=MONDAY + timedelta(days=1))
        broker = FakeBroker(clock)
        self.assertEqual(run(broker, bound(), clock)[0], [])
        self.assertEqual(broker.submits, [])

    def test_unfilled_entry_tries_twice_then_cancels(self):
        clock = Clock()
        broker = FakeBroker(clock, fill="none")
        state = bound()
        kinds, _ = run(broker, state, clock)
        self.assertEqual([s[1] for s in broker.submits], ["-1.01", "-0.96"])
        self.assertEqual(kinds[-1], "OPEN_UNFILLED")
        self.assertTrue(all(o["status"] == "canceled" for o in broker.orders.values()))
        self.assertIsNone(state["position"])
        self.assertIsNone(state["pending_open"])

    def test_debit_fill_or_missing_leg_halts(self):
        clock = Clock()
        broker = FakeBroker(clock)
        original = broker._fill

        def wrong_sign(order, short_price, long_price, opening):
            original(order, long_price, short_price, opening) if opening else original(order, short_price, long_price, opening)
        broker._fill = wrong_sign
        with self.assertRaises(bot.Halt):
            run(broker, bound(), clock)


class ManagementTests(unittest.TestCase):
    def test_profit_take_filled_between_runs_is_recorded(self):
        broker, state, clock = opened()
        broker.fill_resting_take_profit()
        clock.t += timedelta(days=1)
        kinds, events = run(broker, state, clock)
        self.assertEqual(kinds[0], "SPREAD_CLOSED")
        self.assertEqual(events[0]["reason"], "profit_take")
        self.assertEqual(events[0]["realized_pnl"], "255.00")  # (1.01 - 0.50) x 100 x 5
        self.assertIsNone(state["position"])

    def test_breakeven_exit_cancels_profit_take_and_closes_for_a_debit(self):
        broker, state, clock = opened()
        clock.t += timedelta(days=1)
        broker.last = 730.0
        kinds, events = run(broker, state, clock)
        self.assertEqual(kinds, ["SPREAD_CLOSED"])
        self.assertEqual(events[0]["reason"], "breakeven")
        self.assertEqual(broker.submits[-1][:3], ("close", "5", "day"))
        self.assertEqual(events[0]["realized_pnl"], "-995.00")  # (1.01 - 3.00) x 100 x 5
        self.assertEqual([o["status"] for o in broker.orders.values() if o["tif"] == "gtc"], ["canceled"])
        self.assertEqual(broker.positions(), [])

    def test_time_exit_within_five_sessions(self):
        broker, state, clock = opened()
        clock.t += timedelta(days=1)
        state["position"]["expiration"] = (clock.t.date() + timedelta(days=6)).isoformat()
        kinds, events = run(broker, state, clock)
        self.assertEqual(events[0]["reason"], "time")

    def test_missing_profit_take_is_replaced(self):
        broker, state, clock = opened()
        for order in broker.orders.values():
            if order["intent"] == "close":
                order["status"] = "expired"
        clock.t += timedelta(days=1)
        kinds, _ = run(broker, state, clock)
        self.assertEqual(kinds, ["PROFIT_TAKE_PLACED", "HOLDING"])
        self.assertTrue(broker.submits[-1][4].endswith("-tp-2"))

    def test_no_same_day_replacement_after_exit(self):
        broker, state, clock = opened()
        clock.t += timedelta(days=7)  # the next Monday
        broker.last = 730.0
        kinds, _ = run(broker, state, clock)
        self.assertEqual(kinds, ["SPREAD_CLOSED", "NO_ENTRY"])

    def test_unknown_position_or_order_halts(self):
        broker, state, clock = opened()
        broker.pos["SPY"] = (Decimal(100), Decimal("735"))  # e.g. an assignment
        with self.assertRaises(bot.Halt):
            run(broker, state, clock)
        clock = Clock()
        broker = FakeBroker(clock)
        broker.orders["x"] = {"id": "x", "client_order_id": "manual-1", "status": "new", "intent": "close"}
        with self.assertRaises(bot.Halt):
            run(broker, bound(), clock)

    def test_kill_file_and_closed_market_do_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            kill = Path(folder) / "KILL"
            kill.write_text("owner review\n")
            clock = Clock()
            broker = FakeBroker(clock)
            self.assertEqual(run(broker, bound(), clock, kill=kill)[0], ["HALTED"])
        broker.is_open = False
        self.assertEqual(run(broker, bound(), clock)[0], ["MARKET_CLOSED"])
        self.assertEqual(broker.submits, [])


class PlumbingTests(unittest.TestCase):
    def test_plumbing_opens_one_checks_signs_cancels_take_profit_and_closes(self):
        clock = Clock(day=MONDAY + timedelta(days=2))  # any weekday
        broker = FakeBroker(clock, trend="down")        # filters are logged, not enforced
        state = bound()
        kinds, events = run(broker, state, clock, action=bot.plumbing_test)
        self.assertEqual(broker.submits[0][:4], ("open", "-0.97", "day", 1))  # natural credit 4.37 - 3.40
        self.assertIn("PLUMBING_OPENED", kinds)
        self.assertIn("PROFIT_TAKE_CANCEL_CHECK", kinds)
        self.assertEqual(kinds[-1], "SPREAD_CLOSED")
        self.assertEqual(len(state["plumbing_tests"]), 1)
        self.assertEqual(state["closed"], [])
        self.assertIsNone(state["position"])


class ClientGuardTests(unittest.TestCase):
    class Opener:
        def __init__(self):
            self.requests = []

        def open(self, request, timeout):
            self.requests.append((request.get_method(), request.full_url, request.data))

            class Reply:
                def __enter__(self):
                    return self

                def __exit__(self, *exc):
                    return False

                def read(self, limit):
                    return b'{"id": "x"}'
            return Reply()

    def test_only_bull_put_spreads_can_be_sent(self):
        opener = self.Opener()
        client = bot.PaperBroker("k", "s", opener)
        s, l = "SPY261104P00736000", "SPY261104P00731000"
        bad = [
            (s.replace("P", "C"), l, 1, Decimal("-1.00"), "open"),          # calls
            ("QQQ261104P00736000", l, 1, Decimal("-1.00"), "open"),         # other underlying
            (s, "SPY261104P00732000", 1, Decimal("-1.00"), "open"),         # not $5 wide
            (l, s, 1, Decimal("-1.00"), "open"),                            # short strike below long
            (s, "SPY261111P00731000", 1, Decimal("-1.00"), "open"),         # different expirations
            (s, l, 1, Decimal("1.00"), "open"),                             # opening for a debit
            (s, l, 1, Decimal("-1.00"), "close"),                           # closing for a credit
            (s, l, 6, Decimal("-1.00"), "open"),                            # too many contracts
            (s, l, 1, Decimal("-1.005"), "open"),                           # sub-cent price
            (s, l, 1, Decimal("-5.00"), "open"),                            # credit equal to width
        ]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ValueError):
                client.submit_spread(*args, "day", "spy-bps-x")
        with self.assertRaises(ValueError):
            client.submit_spread(s, l, 1, Decimal("-1.00"), "open", "day", "manual-x")
        for method, base, path in (("POST", bot.PAPER, "/v2/positions"), ("DELETE", bot.PAPER, "/v2/positions"),
                                   ("PATCH", bot.PAPER, "/v2/account/configurations"),
                                   ("GET", "https://api.alpaca.markets", "/v2/account"),
                                   ("GET", bot.DATA, "/v1beta1/options/snapshots/QQQ")):
            with self.assertRaises(ValueError):
                client._call(method, base, path)
        self.assertEqual(opener.requests, [])
        client.submit_spread(s, l, 2, Decimal("-1.01"), "open", "day", "spy-bps-2026-10-05-open-1")
        method, url, data = opener.requests[0]
        body = json.loads(data)
        self.assertEqual((method, url, body["order_class"], body["limit_price"], body["qty"]),
                         ("POST", bot.PAPER + "/v2/orders", "mleg", "-1.01", "2"))
        self.assertEqual([(leg["symbol"], leg["side"], leg["position_intent"]) for leg in body["legs"]],
                         [(s, "sell", "sell_to_open"), (l, "buy", "buy_to_open")])

    def test_credentials_need_a_private_file_with_both_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env.options"
            path.write_text("OPTIONS_PAPER_API_KEY=k\nOPTIONS_PAPER_API_SECRET=s\n")
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                bot.credentials(path)
            path.chmod(0o600)
            self.assertEqual(bot.credentials(path), ("k", "s"))


if __name__ == "__main__":
    unittest.main()
