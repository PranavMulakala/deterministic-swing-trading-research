"""Offline tests for the LITE paper dip bot: simulated broker, clock, and HTTP only."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from research.lite_paper_bot_v1 import bot

TODAY = date(2026, 9, 29)
PRIOR = [TODAY - timedelta(days=n) for n in range(1, 40) if (TODAY - timedelta(days=n)).weekday() < 5][:20][::-1]
NO_KILL = Path("/nonexistent-lite-bot/KILL")


class Clock:
    def __init__(self, hour=10, minute=0):
        self.t = datetime(2026, 9, 29, hour, minute, tzinfo=bot.NY)

    def now(self):
        return self.t.astimezone(timezone.utc)

    def sleep(self, seconds):
        self.t += timedelta(seconds=seconds)


def morning(day, closes, opening=100.0, low=None, volume=100):
    rows = []
    for index, close in enumerate(closes):
        first = opening if index == 0 else closes[index - 1]
        bar_low = min(first, close) if low is None or index else min(low, first, close)
        rows.append({"t": f"{day}T09:{30 + 5 * index:02}:00-04:00", "o": first, "h": max(first, close),
                     "l": bar_low, "c": close, "v": volume})
    return rows


DIP = (99.5, 99.0, 98.8, 98.7, 98.6, 98.5)        # low 98.5 = -1.5%, still below the 100 open
FLAT = (100.2, 100.1, 99.9, 100.0, 100.1, 100.2)  # never 1% below the open


class FakeBroker:
    def __init__(self, clock, today=DIP, fill="fill", ask=98.6, quote_age=5, trade=98.62, trade_age=5):
        self.time, self.today, self.fill = clock, today, fill
        self.ask, self.quote_age, self.trade, self.trade_age = ask, quote_age, trade, trade_age
        self.account_id, self.cash, self.is_open = "acct-1", "100000", True
        self.held, self.orders, self.calls = Decimal(0), {}, []

    def account(self):
        return {"id": self.account_id, "status": "ACTIVE", "cash": self.cash}

    def clock(self):
        return {"timestamp": self.time.now().isoformat(), "is_open": self.is_open}

    def calendar(self, start, end):
        return [{"date": d.isoformat(), "open": "09:30", "close": "16:00"} for d in PRIOR + [TODAY]]

    def bars(self, start, end):
        rows = [bar for d in PRIOR for bar in morning(d.isoformat(), FLAT)]
        return rows + morning(TODAY.isoformat(), self.today, low=min(self.today))

    def latest_quote(self):
        return {"t": (self.time.now() - timedelta(seconds=self.quote_age)).isoformat(), "ap": self.ask}

    def latest_trade(self):
        return {"t": (self.time.now() - timedelta(seconds=self.trade_age)).isoformat(), "p": self.trade}

    def positions(self):
        return [{"symbol": "LITE", "qty": str(self.held), "side": "long"}] if self.held else []

    def open_orders(self):
        return [dict(o) for o in self.orders.values() if o["status"] in ("new", "partially_filled")]

    def order(self, order_id):
        return dict(self.orders[order_id])

    def order_by_client_id(self, client_order_id):
        return dict(next(o for o in self.orders.values() if o["client_order_id"] == client_order_id))

    def _new(self, side, qty, limit, client_order_id, tif):
        if any(o["client_order_id"] == client_order_id for o in self.orders.values()):
            raise RuntimeError("HTTP 422: client_order_id must be unique")
        order = {"id": str(uuid.uuid4()), "client_order_id": client_order_id, "symbol": "LITE", "side": side,
                 "type": "limit", "time_in_force": tif, "qty": str(qty), "limit_price": str(limit),
                 "status": "new", "filled_qty": "0", "filled_avg_price": None}
        self.orders[order["id"]] = order
        self.calls.append((side, qty, str(limit), tif, client_order_id))
        return order

    def submit_buy(self, qty, limit, client_order_id):
        order = self._new("buy", qty, limit, client_order_id, "day")
        price = str(min(Decimal(str(self.ask)), limit))
        if self.fill == "fill":
            order.update(status="filled", filled_qty=str(qty), filled_avg_price=price)
            self.held += qty
        elif self.fill == "partial":
            order.update(status="partially_filled", filled_qty="3", filled_avg_price=price)
            self.held += 3
        return dict(order)

    def submit_sell(self, qty, limit, client_order_id):
        return dict(self._new("sell", qty, limit, client_order_id, "gtc"))

    def cancel(self, order_id):
        order = self.orders[order_id]
        if order["status"] == "filled":
            raise RuntimeError("HTTP 422: order is already filled")
        order["status"] = "canceled"

    def fill_sell(self):
        sell = next(o for o in self.orders.values() if o["side"] == "sell" and o["status"] == "new")
        sell.update(status="filled", filled_qty=sell["qty"], filled_avg_price=sell["limit_price"],
                    filled_at="2026-09-29T15:00:00Z")
        self.held -= Decimal(sell["qty"])


def bound(**extra):
    return {"account_id": "acct-1", "position": None, "closed": [], **extra}


def run(broker, state, clock, kill=NO_KILL):
    events = []
    bot.run(broker, state, clock.now, clock.sleep, events.append, lambda: None, kill)
    return [event["type"] for event in events], events


def holding(broker, target="100.58"):
    """Prepare a filled position with its resting target sell."""
    broker.held = Decimal(bot.SHARES)
    buy = broker._new("buy", bot.SHARES, Decimal("98.70"), "lite-dip-2026-09-28-buy", "day")
    buy.update(status="filled", filled_qty=str(bot.SHARES), filled_avg_price="98.6")
    sell = broker._new("sell", bot.SHARES, Decimal(target), "lite-dip-2026-09-28-sell", "gtc")
    broker.calls.clear()
    return {"entry_date": "2026-09-28", "qty": str(bot.SHARES), "avg_fill": "98.6", "target": target,
            "buy_order_id": buy["id"], "sell_order_id": sell["id"],
            "sell_client_order_id": "lite-dip-2026-09-28-sell", "sell_replacements": 0}


class DecisionTests(unittest.TestCase):
    def test_not_bound_places_nothing(self):
        clock = Clock()
        broker = FakeBroker(clock)
        self.assertEqual(run(broker, {}, clock)[0], ["NOT_BOUND"])
        self.assertEqual(broker.calls, [])

    def test_wrong_account_and_clock_skew_halt(self):
        clock = Clock()
        broker = FakeBroker(clock)
        broker.account_id = "someone-else"
        with self.assertRaises(bot.Halt):
            run(broker, bound(), clock)
        broker = FakeBroker(clock)
        broker.clock = lambda: {"timestamp": (clock.now() + timedelta(seconds=90)).isoformat(), "is_open": True}
        with self.assertRaises(bot.Halt):
            run(broker, bound(), clock)

    def test_market_closed_and_no_signal_place_nothing(self):
        clock = Clock()
        broker = FakeBroker(clock)
        broker.is_open = False
        self.assertEqual(run(broker, bound(), clock)[0], ["MARKET_CLOSED"])
        broker = FakeBroker(clock, today=FLAT)
        kinds, events = run(broker, bound(), clock)
        self.assertEqual(kinds, ["NO_SIGNAL"])
        self.assertEqual(broker.calls, [])

    def test_signal_buys_seven_and_rests_plus_two_percent_sell(self):
        clock = Clock()
        broker = FakeBroker(clock)
        state = bound()
        kinds, events = run(broker, state, clock)
        self.assertEqual(kinds, ["SIGNAL", "BUY_SUBMITTED", "FILLED_AND_TARGET_PLACED"])
        # Limit = 98.60 ask x 1.001 = 98.6986 -> 98.70; fill 98.60; target 98.60 x 1.02 = 100.572 -> up to 100.58.
        self.assertEqual(broker.calls[0], ("buy", bot.SHARES, "98.70", "day", "lite-dip-2026-09-29-buy"))
        self.assertEqual(broker.calls[1], ("sell", bot.SHARES, "100.58", "gtc", "lite-dip-2026-09-29-sell"))
        self.assertEqual(state["position"]["target"], "100.58")
        self.assertIsNone(state["pending_buy"])
        self.assertFalse(events[0]["rebound_learning_only"])
        self.assertEqual(events[0]["volume_ratio_learning_only"], "1.00")
        self.assertGreaterEqual(Decimal(state["position"]["target"]), Decimal("98.6") * Decimal("1.02"))

    def test_partial_fill_cancels_rest_at_1005_and_sells_only_filled_shares(self):
        clock = Clock()
        broker = FakeBroker(clock, fill="partial")
        state = bound()
        kinds, _ = run(broker, state, clock)
        self.assertEqual(kinds[-1], "FILLED_AND_TARGET_PLACED")
        self.assertGreaterEqual(clock.t, datetime(2026, 9, 29, 10, 5, tzinfo=bot.NY))
        self.assertEqual(broker.calls[-1][:2], ("sell", 3))
        self.assertEqual(state["position"]["qty"], "3")

    def test_unfilled_buy_is_cancelled_with_no_sell(self):
        clock = Clock()
        broker = FakeBroker(clock, fill="none")
        state = bound()
        kinds, _ = run(broker, state, clock)
        self.assertEqual(kinds[-1], "BUY_UNFILLED")
        self.assertEqual([c[0] for c in broker.calls], ["buy"])
        self.assertIsNone(state["position"])
        self.assertIsNone(state["pending_buy"])

    def test_monitoring_failure_cancels_the_open_buy(self):
        clock = Clock()
        broker = FakeBroker(clock, fill="none")
        broker.order = lambda order_id: (_ for _ in ()).throw(RuntimeError("network down"))
        state = bound()
        with self.assertRaises(RuntimeError):
            run(broker, state, clock)
        self.assertEqual([o["status"] for o in broker.orders.values()], ["canceled"])
        self.assertEqual(state["pending_buy"]["client_order_id"], "lite-dip-2026-09-29-buy")

    def test_late_start_and_stale_prices_do_not_buy(self):
        clock = Clock(10, 6)
        broker = FakeBroker(clock)
        self.assertEqual(run(broker, bound(), clock)[0], ["LATE_START"])
        clock = Clock()
        broker = FakeBroker(clock, quote_age=100, trade_age=5)
        kinds, events = run(broker, bound(), clock)
        self.assertEqual(events[1]["source"], "iex_trade")
        clock = Clock()
        broker = FakeBroker(clock, quote_age=100, trade_age=100)
        kinds, _ = run(broker, bound(), clock)
        self.assertEqual(kinds[-1], "NO_FRESH_PRICE")
        self.assertEqual(broker.calls, [])


class HoldingTests(unittest.TestCase):
    def test_holding_skips_signal_and_keeps_the_sell(self):
        clock = Clock()
        broker = FakeBroker(clock)
        state = bound(position=holding(broker))
        kinds, _ = run(broker, state, clock)
        self.assertEqual(kinds, ["SIGNAL", "SIGNAL_SKIPPED_HOLDING"])
        self.assertEqual(broker.calls, [])

    def test_missing_target_sell_is_replaced_at_the_same_price(self):
        clock = Clock()
        broker = FakeBroker(clock, today=FLAT)
        state = bound(position=holding(broker))
        for order in broker.orders.values():
            if order["side"] == "sell":
                order["status"] = "expired"
        kinds, _ = run(broker, state, clock)
        self.assertEqual(kinds[0], "TARGET_SELL_REPLACED")
        self.assertEqual(broker.calls[0], ("sell", bot.SHARES, "100.58", "gtc", "lite-dip-2026-09-28-sell-r1"))

    def test_filled_sell_records_realized_profit(self):
        clock = Clock()
        broker = FakeBroker(clock, today=FLAT)
        state = bound(position=holding(broker))
        broker.fill_sell()
        kinds, events = run(broker, state, clock)
        self.assertEqual(kinds[0], "SOLD_AT_TARGET")
        self.assertEqual(events[0]["realized_pnl"], f"{bot.SHARES * Decimal('1.98'):.2f}")  # shares x (100.58 - 98.60)
        self.assertIsNone(state["position"])
        self.assertEqual(len(state["closed"]), 1)

    def test_unrecorded_shares_or_mismatched_sell_halt(self):
        clock = Clock()
        broker = FakeBroker(clock)
        broker.held = Decimal(bot.SHARES)
        with self.assertRaises(bot.Halt):
            run(broker, bound(), clock)
        broker = FakeBroker(clock)
        state = bound(position=holding(broker, target="100.58"))
        state["position"]["target"] = "101.00"
        with self.assertRaises(bot.Halt):
            run(broker, state, clock)

    def test_interrupted_buy_is_adopted_and_gets_its_sell(self):
        clock = Clock()
        broker = FakeBroker(clock)
        buy = broker._new("buy", bot.SHARES, Decimal("98.70"), "lite-dip-2026-09-29-buy", "day")
        buy.update(status="filled", filled_qty=str(bot.SHARES), filled_avg_price="98.6")
        broker.held = Decimal(bot.SHARES)
        broker.calls.clear()
        state = bound(pending_buy={"date": "2026-09-29", "client_order_id": "lite-dip-2026-09-29-buy"})
        kinds, _ = run(broker, state, clock)
        self.assertEqual(kinds[:2], ["ADOPTED_INTERRUPTED_BUY", "SIGNAL"])
        self.assertEqual(broker.calls[0], ("sell", bot.SHARES, "100.58", "gtc", "lite-dip-2026-09-29-sell"))
        self.assertEqual(kinds[-1], "SIGNAL_SKIPPED_HOLDING")

    def test_kill_file_stops_everything(self):
        with tempfile.TemporaryDirectory() as folder:
            kill = Path(folder) / "KILL"
            kill.write_text("owner review\n")
            clock = Clock()
            broker = FakeBroker(clock)
            self.assertEqual(run(broker, bound(), clock, kill)[0], ["HALTED"])
            self.assertEqual(broker.calls, [])


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

    def test_only_listed_requests_and_order_shapes_are_sent(self):
        opener = self.Opener()
        client = bot.PaperBroker("key", "secret", opener)
        for method, base, path in (("POST", bot.PAPER, "/v2/positions"), ("DELETE", bot.PAPER, "/v2/positions"),
                                   ("GET", "https://api.alpaca.markets", "/v2/account"),
                                   ("PATCH", bot.PAPER, "/v2/account/configurations"),
                                   ("DELETE", bot.PAPER, "/v2/orders")):
            with self.assertRaises(ValueError):
                client._call(method, base, path)
        with self.assertRaises(ValueError):
            client.submit_buy(bot.SHARES + 1, Decimal("98.70"), "lite-dip-x")
        with self.assertRaises(ValueError):
            client.submit_buy(bot.SHARES, Decimal("98.705"), "lite-dip-x")
        with self.assertRaises(ValueError):
            client.submit_sell(7, Decimal("100.58"), "manual-x")
        self.assertEqual(opener.requests, [])
        client.submit_buy(bot.SHARES, Decimal("98.70"), "lite-dip-2026-09-29-buy")
        method, url, data = opener.requests[0]
        body = json.loads(data)
        self.assertEqual((method, url), ("POST", bot.PAPER + "/v2/orders"))
        self.assertEqual((body["type"], body["time_in_force"], body["qty"], body["symbol"]), ("limit", "day", str(bot.SHARES), "LITE"))

    def test_credentials_need_a_private_file_with_both_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env.lite"
            path.write_text("LITE_PAPER_API_KEY=k\nLITE_PAPER_API_SECRET=s\n")
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                bot.credentials(path)
            path.chmod(0o600)
            self.assertEqual(bot.credentials(path), ("k", "s"))
            path.write_text("LITE_PAPER_API_KEY=k\nLITE_PAPER_API_SECRET=\n")
            with self.assertRaises(ValueError):
                bot.credentials(path)


class SizingTests(unittest.TestCase):
    def test_buy_is_about_60000_and_never_more_than_shares(self):
        self.assertEqual(bot.buy_size(Decimal("1102.45")), 54)  # Oct 7: 66 shares would have been $72,762
        self.assertEqual(bot.buy_size(Decimal("98.70")), bot.SHARES)


if __name__ == "__main__":
    unittest.main()
