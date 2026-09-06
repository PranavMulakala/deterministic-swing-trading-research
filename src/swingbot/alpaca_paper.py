from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Optional

from .models import Bar
from .paper_config import ALPACA_DATA_BASE_URL, PAPER_TRADING_BASE_URL
from .paper_models import (
    ApprovalPermit,
    OrderProposal,
    PaperAccount,
    PaperAsset,
    PaperClock,
    PaperOrder,
    PaperPosition,
    PaperQuote,
    decimal_string,
    parse_timestamp,
)


Transport = Callable[[str, str, dict[str, str], Optional[bytes], int], Any]
PermitValidator = Callable[[OrderProposal, ApprovalPermit, str], bool]
_MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
_MUTATION_TOKEN = object()


class AlpacaPaperError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        raise AlpacaPaperError("broker redirects are prohibited")


def _default_transport(
    method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: int
) -> Any:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=timeout) as response:
            if response.geturl() != url:
                raise AlpacaPaperError("broker response URL differs from the requested paper endpoint")
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            detail = json.loads(raw).get("message", "broker request failed")
        except (json.JSONDecodeError, AttributeError):
            detail = "broker request failed"
        raise AlpacaPaperError(f"broker returned HTTP {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:
        raise AlpacaPaperError(f"broker connection failed: {exc.reason}") from None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise AlpacaPaperError("broker returned invalid JSON") from None


class AlpacaPaperClient:
    """Narrow Alpaca adapter with a non-configurable live-money boundary."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        trading_base_url: str = PAPER_TRADING_BASE_URL,
        data_base_url: str = ALPACA_DATA_BASE_URL,
        timeout: int = 20,
        transport: Transport | None = None,
        permit_validator: PermitValidator | None = None,
    ):
        if trading_base_url != PAPER_TRADING_BASE_URL:
            raise AlpacaPaperError("live or alternate trading endpoints are prohibited")
        if data_base_url != ALPACA_DATA_BASE_URL:
            raise AlpacaPaperError("alternate market-data endpoints are prohibited")
        if not api_key or not api_secret:
            raise AlpacaPaperError("paper API credentials are missing")
        self._key = api_key
        self._secret = api_secret
        self._trading_base = PAPER_TRADING_BASE_URL
        self._data_base = ALPACA_DATA_BASE_URL
        self._timeout = timeout
        self._transport = transport or _default_transport
        self._permit_validator = permit_validator

    def _request(
        self,
        method: str,
        path: str,
        *,
        data_api: bool = False,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        _mutation_token: object | None = None,
    ) -> Any:
        method = method.upper()
        if method in _MUTATING_METHODS and _mutation_token is not _MUTATION_TOKEN:
            raise AlpacaPaperError(
                "direct broker mutation is prohibited; use an approval-gated adapter method"
            )
        if not path.startswith("/") or ".." in path:
            raise AlpacaPaperError("unsafe broker path")
        base = self._data_base if data_api else self._trading_base
        url = f"{base}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"
        headers = {
            "APCA-API-KEY-ID": self._key,
            "APCA-API-SECRET-KEY": self._secret,
            "Accept": "application/json",
            "User-Agent": "deterministic-swing-paper/1",
        }
        encoded = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        try:
            return self._transport(method, url, headers, encoded, self._timeout)
        except Exception as exc:
            message = str(exc).replace(self._key, "[REDACTED]").replace(self._secret, "[REDACTED]")
            raise AlpacaPaperError(f"broker request failed: {message}") from None

    def get_account(self) -> PaperAccount:
        value = self._request("GET", "/v2/account")
        return PaperAccount(
            account_id=str(value["id"]),
            account_number=str(value.get("account_number", "")),
            status=str(value["status"]),
            currency=str(value["currency"]),
            equity=_decimal(value["equity"]),
            last_equity=_decimal(value.get("last_equity", value["equity"])),
            cash=_decimal(value["cash"]),
            non_marginable_buying_power=_decimal(
                value.get("non_marginable_buying_power", value["cash"])
            ),
            buying_power=_decimal(value.get("buying_power", value["cash"])),
            multiplier=_decimal(value.get("multiplier", "1")),
            long_market_value=_decimal(value.get("long_market_value", "0")),
            short_market_value=_decimal(value.get("short_market_value", "0")),
            trading_blocked=bool(value.get("trading_blocked", False)),
            account_blocked=bool(value.get("account_blocked", False)),
            trade_suspended_by_user=bool(value.get("trade_suspended_by_user", False)),
        )

    def get_clock(self) -> PaperClock:
        value = self._request("GET", "/v2/clock")
        return PaperClock(
            timestamp=parse_timestamp(str(value["timestamp"])),
            is_open=bool(value["is_open"]),
            next_open=parse_timestamp(str(value["next_open"])),
            next_close=parse_timestamp(str(value["next_close"])),
        )

    def trading_days(self, *, start: date, end: date) -> list[date]:
        values = self._request(
            "GET", "/v2/calendar",
            query={"start": start.isoformat(), "end": end.isoformat()},
        )
        return [date.fromisoformat(str(value["date"])) for value in values]

    def get_asset(self, symbol: str) -> PaperAsset:
        value = self._request("GET", f"/v2/assets/{_symbol(symbol)}")
        return PaperAsset(
            symbol=str(value["symbol"]).upper(),
            status=str(value["status"]),
            asset_class=str(value["class"]),
            exchange=str(value.get("exchange", "")),
            tradable=bool(value["tradable"]),
            fractionable=bool(value.get("fractionable", False)),
        )

    def latest_quote(self, symbol: str, *, feed: str) -> PaperQuote:
        if feed not in {"iex", "sip"}:
            raise AlpacaPaperError("unsupported quote feed")
        value = self._request(
            "GET",
            f"/v2/stocks/{_symbol(symbol)}/quotes/latest",
            data_api=True,
            query={"feed": feed},
        )
        quote = value["quote"]
        return PaperQuote(
            symbol=symbol.upper(),
            bid=_decimal(quote["bp"]),
            ask=_decimal(quote["ap"]),
            timestamp=parse_timestamp(str(quote["t"])),
        )

    def list_positions(self) -> list[PaperPosition]:
        values = self._request("GET", "/v2/positions")
        return [
            PaperPosition(
                symbol=str(value["symbol"]).upper(),
                quantity=_decimal(value["qty"]),
                side=str(value["side"]),
                average_entry_price=_decimal(value["avg_entry_price"]),
                current_price=_decimal(value.get("current_price", value["avg_entry_price"])),
                market_value=_decimal(value["market_value"]),
            )
            for value in values
        ]

    def list_orders(self, *, status: str = "all") -> list[PaperOrder]:
        values = self._request(
            "GET", "/v2/orders",
            query={"status": status, "nested": "true", "limit": 500, "direction": "desc"},
        )
        return [_paper_order(value) for value in values]

    def get_order(self, order_id: str) -> PaperOrder:
        value = self._request(
            "GET", f"/v2/orders/{urllib.parse.quote(order_id, safe='')}",
            query={"nested": "true"},
        )
        return _paper_order(value)

    def get_order_by_client_id(self, client_order_id: str) -> PaperOrder:
        value = self._request(
            "GET", "/v2/orders:by_client_order_id",
            query={"client_order_id": client_order_id},
        )
        return _paper_order(value)

    def submit_entry(self, proposal: OrderProposal, permit: ApprovalPermit) -> PaperOrder:
        if proposal.action != "entry_oto" or proposal.side != "buy":
            raise AlpacaPaperError("adapter only accepts validated entry OTO proposals")
        if proposal.order_type != "market" or proposal.time_in_force != "gtc":
            raise AlpacaPaperError("swing entry must be a whole-share market/GTC order")
        if proposal.fractional:
            raise AlpacaPaperError("Alpaca fractional orders are DAY-only and cannot protect a swing overnight")
        if proposal.order_class != "oto" or proposal.stop_price is None:
            raise AlpacaPaperError("entry must include an OTO broker-native stop")
        if proposal.extended_hours:
            raise AlpacaPaperError("extended-hours entry is prohibited")
        if proposal.quantity <= 0 or proposal.quantity != proposal.quantity.to_integral_value():
            raise AlpacaPaperError("entry quantity must be a positive whole-share amount")
        if (
            proposal.maximum_entry_reference is None
            or proposal.maximum_entry_reference <= 0
            or proposal.stop_price <= 0
            or proposal.stop_price >= proposal.maximum_entry_reference
        ):
            raise AlpacaPaperError("entry price guard or protective stop is invalid")
        self._require_permit(proposal, permit, "submit_order")
        value = self._request(
            "POST",
            "/v2/orders",
            body={
                "symbol": proposal.symbol,
                "qty": decimal_string(proposal.quantity),
                "side": "buy",
                "type": "market",
                "time_in_force": "gtc",
                "order_class": "oto",
                "stop_loss": {"stop_price": decimal_string(proposal.stop_price)},
                "client_order_id": proposal.client_order_id,
                "extended_hours": False,
            },
            _mutation_token=_MUTATION_TOKEN,
        )
        return _paper_order(value)

    def close_position(self, proposal: OrderProposal, permit: ApprovalPermit) -> PaperOrder:
        if proposal.action != "close_position" or proposal.side != "sell":
            raise AlpacaPaperError("adapter only accepts validated close proposals")
        if (
            proposal.quantity <= 0
            or proposal.order_type != "market"
            or proposal.time_in_force != "day"
            or proposal.order_class != "simple"
            or proposal.extended_hours
        ):
            raise AlpacaPaperError("close proposal has invalid execution terms")
        if proposal.stop_price is not None or proposal.maximum_entry_reference is not None:
            raise AlpacaPaperError("close proposal must not contain entry or stop terms")
        self._require_permit(proposal, permit, "submit_order")
        value = self._request(
            "POST",
            "/v2/orders",
            body={
                "symbol": proposal.symbol,
                "qty": decimal_string(proposal.quantity),
                "side": "sell",
                "type": "market",
                "time_in_force": "day",
                "client_order_id": proposal.client_order_id,
                "extended_hours": False,
            },
            _mutation_token=_MUTATION_TOKEN,
        )
        return _paper_order(value)

    def cancel_order(
        self, order_id: str, proposal: OrderProposal, permit: ApprovalPermit
    ) -> None:
        if proposal.action != "close_position":
            raise AlpacaPaperError("order cancellation requires an approved exit proposal")
        if not order_id:
            raise AlpacaPaperError("order cancellation requires a broker order id")
        self._require_permit(proposal, permit, "cancel_protective_stop")
        self._request(
            "DELETE",
            f"/v2/orders/{urllib.parse.quote(order_id, safe='')}",
            _mutation_token=_MUTATION_TOKEN,
        )

    def historical_daily_bars(
        self,
        symbols: list[str],
        *,
        start: date,
        end: date,
        feed: str,
        adjustment: str,
    ) -> dict[str, list[Bar]]:
        if feed not in {"iex", "sip"}:
            raise AlpacaPaperError("unsupported historical feed")
        if adjustment != "all":
            raise AlpacaPaperError("paper signal bars must use adjustment=all")
        clean_symbols = [_symbol(symbol) for symbol in symbols]
        bars: dict[str, list[Bar]] = {symbol: [] for symbol in clean_symbols}
        page_token: str | None = None
        while True:
            query: dict[str, Any] = {
                "symbols": ",".join(clean_symbols),
                "timeframe": "1Day",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "feed": feed,
                "adjustment": adjustment,
                "sort": "asc",
                "limit": 10000,
            }
            if page_token:
                query["page_token"] = page_token
            value = self._request("GET", "/v2/stocks/bars", data_api=True, query=query)
            for symbol, rows in value.get("bars", {}).items():
                clean = _symbol(symbol)
                bars.setdefault(clean, [])
                for row in rows:
                    bars[clean].append(
                        Bar(
                            symbol=clean,
                            date=parse_timestamp(str(row["t"])).date(),
                            open=float(row["o"]),
                            high=float(row["h"]),
                            low=float(row["l"]),
                            close=float(row["c"]),
                            volume=float(row["v"]),
                        )
                    )
            page_token = value.get("next_page_token")
            if not page_token:
                break
        for symbol in bars:
            bars[symbol].sort(key=lambda bar: bar.date)
        return bars

    def _require_permit(
        self, proposal: OrderProposal, permit: ApprovalPermit, stage: str
    ) -> None:
        basic = (
            isinstance(permit, ApprovalPermit)
            and permit.proposal_id == proposal.proposal_id
            and permit.content_hash == proposal.content_hash
            and bool(permit.approval_event_id)
            and bool(permit.session_id)
        )
        if (
            not basic
            or self._permit_validator is None
            or not self._permit_validator(proposal, permit, stage)
        ):
            raise AlpacaPaperError("broker mutation lacks an unused journal-backed approval permit")


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _symbol(value: str) -> str:
    symbol = value.strip().upper()
    if not symbol or not symbol.isascii() or not symbol.replace(".", "").isalnum():
        raise AlpacaPaperError("invalid asset symbol")
    return urllib.parse.quote(symbol, safe=".")


def _paper_order(value: dict[str, Any]) -> PaperOrder:
    legs = tuple(_paper_order(leg) for leg in value.get("legs") or [])
    return PaperOrder(
        order_id=str(value["id"]),
        client_order_id=str(value.get("client_order_id", "")),
        symbol=str(value["symbol"]).upper(),
        side=str(value["side"]),
        order_type=str(value.get("type") or value.get("order_type") or ""),
        time_in_force=str(value.get("time_in_force", "")),
        order_class=str(value.get("order_class", "simple")),
        status=str(value["status"]),
        quantity=_decimal(value.get("qty", "0")),
        filled_quantity=_decimal(value.get("filled_qty", "0")),
        filled_average_price=_decimal(value["filled_avg_price"])
        if value.get("filled_avg_price") is not None else None,
        stop_price=_decimal(value["stop_price"]) if value.get("stop_price") is not None else None,
        parent_order_id=str(value["parent_order_id"])
        if value.get("parent_order_id") else None,
        legs=legs,
    )
