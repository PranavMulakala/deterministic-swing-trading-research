from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from swingbot.alpaca_paper import AlpacaPaperClient, AlpacaPaperError


TIMESTAMP = "2026-01-05T15:00:00Z"


def _order_payload(
    order_id: str = "parent-1", *, client_id: str = "swing-e-1"
) -> dict:
    return {
        "id": order_id,
        "client_order_id": client_id,
        "symbol": "SPY",
        "side": "buy",
        "type": "market",
        "time_in_force": "gtc",
        "order_class": "oto",
        "status": "filled",
        "qty": "1",
        "filled_qty": "1",
        "filled_avg_price": "501.25",
        "filled_at": TIMESTAMP,
        "extended_hours": False,
        "legs": [
            {
                "id": "stop-1",
                "client_order_id": "",
                "symbol": "SPY",
                "side": "sell",
                "type": "stop",
                "time_in_force": "gtc",
                "order_class": "",
                "status": "new",
                "qty": "1",
                "filled_qty": "0",
                "stop_price": "490",
                "parent_order_id": order_id,
                "extended_hours": False,
                "legs": [],
            }
        ],
    }


class _RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str], bytes | None, int]] = []
        self.bar_pages = 0

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers, body, timeout))
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        endpoint = (parsed.netloc, parsed.path)

        if endpoint == ("paper-api.alpaca.markets", "/v2/account"):
            return {
                "id": "paper-account-1",
                "account_number": "PA001234",
                "status": "ACTIVE",
                "currency": "USD",
                "equity": "500.00",
                "last_equity": "499.50",
                "cash": "100.00",
                "non_marginable_buying_power": "100.00",
                "buying_power": "100.00",
                "multiplier": "1",
                "long_market_value": "400.00",
                "short_market_value": "0",
                "trading_blocked": False,
                "account_blocked": False,
                "trade_suspended_by_user": False,
            }
        if endpoint == ("paper-api.alpaca.markets", "/v2/clock"):
            return {
                "timestamp": TIMESTAMP,
                "is_open": True,
                "next_open": "2026-01-06T14:30:00Z",
                "next_close": "2026-01-05T21:00:00Z",
            }
        if endpoint == ("paper-api.alpaca.markets", "/v2/calendar"):
            self._require_query(
                query, start=["2026-01-05"], end=["2026-01-06"]
            )
            return [{"date": "2026-01-05"}, {"date": "2026-01-06"}]
        if endpoint == ("paper-api.alpaca.markets", "/v2/assets/BRK.B"):
            return {
                "symbol": "brk.b",
                "status": "active",
                "class": "us_equity",
                "exchange": "NYSE",
                "tradable": True,
                "fractionable": False,
            }
        if endpoint == ("data.alpaca.markets", "/v2/stocks/SPY/quotes/latest"):
            self._require_query(query, feed=["iex"])
            return {"quote": {"bp": "500.10", "ap": "500.20", "t": TIMESTAMP}}
        if endpoint == ("paper-api.alpaca.markets", "/v2/positions"):
            return [
                {
                    "symbol": "spy",
                    "qty": "1",
                    "side": "long",
                    "avg_entry_price": "499.00",
                    "current_price": "500.00",
                    "market_value": "500.00",
                }
            ]
        if endpoint == ("paper-api.alpaca.markets", "/v2/orders"):
            self._require_query(
                query,
                status=["all"],
                nested=["true"],
                limit=["500"],
                direction=["desc"],
            )
            return [_order_payload()]
        if endpoint == ("paper-api.alpaca.markets", "/v2/orders/order%2F1"):
            self._require_query(query, nested=["true"])
            return _order_payload("order/1")
        if endpoint == (
            "paper-api.alpaca.markets",
            "/v2/orders:by_client_order_id",
        ):
            self._require_query(query, client_order_id=["client/id ? 1"])
            return _order_payload("lookup-1", client_id="client/id ? 1")
        if endpoint == ("data.alpaca.markets", "/v2/stocks/bars"):
            self._require_query(
                query,
                symbols=["SPY,QQQ"],
                timeframe=["1Day"],
                start=["2026-01-01"],
                end=["2026-01-05"],
                feed=["iex"],
                adjustment=["all"],
                sort=["asc"],
                limit=["10000"],
            )
            self.bar_pages += 1
            if self.bar_pages == 1:
                if "page_token" in query:
                    raise AssertionError("first bar page unexpectedly included a token")
                return {
                    "bars": {
                        "SPY": [self._bar("2026-01-02T05:00:00Z", 500)],
                        "QQQ": [self._bar("2026-01-03T05:00:00Z", 400)],
                    },
                    "next_page_token": "page 2/+",
                }
            self._require_query(query, page_token=["page 2/+"])
            return {
                "bars": {"SPY": [self._bar("2026-01-03T05:00:00Z", 501)]},
                "next_page_token": None,
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    @staticmethod
    def _require_query(actual, **expected) -> None:
        for key, value in expected.items():
            if actual.get(key) != value:
                raise AssertionError(
                    f"query {key}: expected {value!r}, got {actual.get(key)!r}"
                )

    @staticmethod
    def _bar(timestamp: str, close: float) -> dict:
        return {
            "t": timestamp,
            "o": close - 1,
            "h": close + 1,
            "l": close - 2,
            "c": close,
            "v": 1_000_000,
        }


class AlpacaReadContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = _RecordingTransport()
        self.client = AlpacaPaperClient(
            "contract-key", "contract-secret", transport=self.transport
        )

    def test_all_read_endpoints_nested_orders_and_bar_pagination(self) -> None:
        account = self.client.get_account()
        self.assertEqual(account.account_id, "paper-account-1")
        self.assertEqual(account.equity, Decimal("500.00"))
        self.assertEqual(account.long_market_value, Decimal("400.00"))
        self.assertFalse(account.trading_blocked)

        clock = self.client.get_clock()
        self.assertEqual(
            clock.timestamp, datetime(2026, 1, 5, 15, tzinfo=timezone.utc)
        )
        self.assertTrue(clock.is_open)
        self.assertEqual(
            self.client.trading_days(
                start=date(2026, 1, 5), end=date(2026, 1, 6)
            ),
            [date(2026, 1, 5), date(2026, 1, 6)],
        )

        asset = self.client.get_asset(" brk.b ")
        self.assertEqual(
            (asset.symbol, asset.asset_class, asset.exchange),
            ("BRK.B", "us_equity", "NYSE"),
        )
        self.assertTrue(asset.tradable)
        self.assertFalse(asset.fractionable)

        quote = self.client.latest_quote("spy", feed="iex")
        self.assertEqual(
            (quote.symbol, quote.bid, quote.ask),
            ("SPY", Decimal("500.10"), Decimal("500.20")),
        )
        self.assertEqual(
            quote.timestamp, datetime(2026, 1, 5, 15, tzinfo=timezone.utc)
        )

        positions = self.client.list_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(
            (positions[0].symbol, positions[0].quantity, positions[0].side),
            ("SPY", Decimal("1"), "long"),
        )

        orders = self.client.list_orders(status="all")
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].order_id, "parent-1")
        self.assertEqual(
            orders[0].filled_at,
            datetime(2026, 1, 5, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(len(orders[0].legs), 1)
        stop = orders[0].legs[0]
        self.assertEqual(
            (
                stop.order_id,
                stop.order_type,
                stop.stop_price,
                stop.parent_order_id,
                stop.order_class,
            ),
            ("stop-1", "stop", Decimal("490"), "parent-1", "simple"),
        )

        self.assertEqual(self.client.get_order("order/1").order_id, "order/1")
        self.assertEqual(
            self.client.get_order_by_client_id("client/id ? 1").client_order_id,
            "client/id ? 1",
        )

        bars = self.client.historical_daily_bars(
            ["spy", "QQQ"],
            start=date(2026, 1, 1),
            end=date(2026, 1, 5),
            feed="iex",
            adjustment="all",
        )
        self.assertEqual(self.transport.bar_pages, 2)
        self.assertEqual(
            [bar.date for bar in bars["SPY"]],
            [date(2026, 1, 2), date(2026, 1, 3)],
        )
        self.assertEqual([bar.close for bar in bars["SPY"]], [500.0, 501.0])
        self.assertEqual([bar.date for bar in bars["QQQ"]], [date(2026, 1, 3)])

        self.assertTrue(all(call[0] == "GET" for call in self.transport.calls))
        self.assertTrue(all(call[3] is None for call in self.transport.calls))
        self.assertTrue(
            all(
                call[2]["APCA-API-KEY-ID"] == "contract-key"
                and call[2]["APCA-API-SECRET-KEY"] == "contract-secret"
                for call in self.transport.calls
            )
        )

    def test_read_input_validation_and_host_boundaries(self) -> None:
        with self.assertRaisesRegex(AlpacaPaperError, "alternate market-data"):
            AlpacaPaperClient(
                "key", "secret", data_base_url="https://example.invalid"
            )
        with self.assertRaisesRegex(AlpacaPaperError, "unsupported quote feed"):
            self.client.latest_quote("SPY", feed="bad")
        with self.assertRaisesRegex(AlpacaPaperError, "order-status filter"):
            self.client.list_orders(status="pending")
        with self.assertRaisesRegex(AlpacaPaperError, "unsupported historical feed"):
            self.client.historical_daily_bars(
                ["SPY"],
                start=date(2026, 1, 1),
                end=date(2026, 1, 5),
                feed="bad",
                adjustment="all",
            )
        with self.assertRaisesRegex(AlpacaPaperError, "adjustment=all"):
            self.client.historical_daily_bars(
                ["SPY"],
                start=date(2026, 1, 1),
                end=date(2026, 1, 5),
                feed="iex",
                adjustment="raw",
            )
        with self.assertRaisesRegex(AlpacaPaperError, "invalid asset symbol"):
            self.client.get_asset("../account")
        with self.assertRaisesRegex(AlpacaPaperError, "unsafe broker path"):
            self.client._request("GET", "/v2/../account")

    def test_order_history_paginates_without_truncating_at_500(self) -> None:
        calls = []

        def transport(method, url, headers, body, timeout):
            del headers, body, timeout
            query = parse_qs(urlparse(url).query)
            calls.append(query)
            if "before_order_id" not in query:
                return [
                    _order_payload(f"order-{index}", client_id=f"client-{index}")
                    for index in range(500)
                ]
            self.assertEqual(query["before_order_id"], ["order-499"])
            return [_order_payload("order-500", client_id="client-500")]

        client = AlpacaPaperClient("key", "secret", transport=transport)
        orders = client.list_orders(status="all")
        self.assertEqual(len(orders), 501)
        self.assertEqual(orders[-1].order_id, "order-500")
        self.assertEqual(len(calls), 2)

    def test_order_history_rejects_malformed_or_nonprogressing_pages(self) -> None:
        client = AlpacaPaperClient("key", "secret", transport=lambda *_: {})
        with self.assertRaisesRegex(AlpacaPaperError, "not an array"):
            client.list_orders(status="all")

        def duplicate_transport(method, url, headers, body, timeout):
            del method, headers, body, timeout
            query = parse_qs(urlparse(url).query)
            if "before_order_id" not in query:
                return [
                    _order_payload(f"order-{index}", client_id=f"client-{index}")
                    for index in range(500)
                ]
            return [_order_payload("order-0", client_id="duplicate")]

        duplicate = AlpacaPaperClient("key", "secret", transport=duplicate_transport)
        with self.assertRaisesRegex(AlpacaPaperError, "repeated an order"):
            duplicate.list_orders(status="all")

        def stalled_transport(*_):
            values = [
                _order_payload(f"order-{index}", client_id=f"client-{index}")
                for index in range(499)
            ]
            values.append(_order_payload("", client_id="client-empty"))
            return values

        stalled = AlpacaPaperClient("key", "secret", transport=stalled_transport)
        with self.assertRaisesRegex(AlpacaPaperError, "made no progress"):
            stalled.list_orders(status="all")


if __name__ == "__main__":
    unittest.main()
