from __future__ import annotations

import json
import http.client
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable, Optional

from .models import Bar
from .paper_config import (
    ALPACA_DATA_BASE_URL,
    CANCEL_VERIFICATION_ATTEMPTS,
    CANCEL_VERIFICATION_INTERVAL_SECONDS,
    PAPER_TRADING_BASE_URL,
    QUOTE_FUTURE_TOLERANCE_SECONDS,
)
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
PermitValidator = Callable[[OrderProposal, ApprovalPermit, str, datetime], bool]
_MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
_ALLOWED_METHODS = _MUTATING_METHODS | {"GET"}
_MUTATION_TOKEN = object()


class AlpacaPaperError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        raise AlpacaPaperError("broker redirects are prohibited")


class _GuardedHTTPSConnection(http.client.HTTPSConnection):
    """Check after connection/TLS setup, before each HTTP socket write."""

    def __init__(self, host: str, *, before_send: Callable[[], None], **kwargs: Any):
        super().__init__(host, **kwargs)
        self._before_send = before_send

    def send(self, data: Any) -> None:
        if self.sock is None:
            self.connect()
        self._before_send()
        super().send(data)


class _GuardedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, before_send: Callable[[], None]):
        super().__init__()
        self._before_send = before_send

    def https_open(self, request: Any) -> Any:
        def connection(host: str, **kwargs: Any) -> _GuardedHTTPSConnection:
            return _GuardedHTTPSConnection(
                host, before_send=self._before_send, **kwargs
            )
        return self.do_open(
            connection, request,
            context=self._context,
        )


def _default_transport(
    method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: int,
    *, before_send: Callable[[], None] | None = None,
) -> Any:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        handlers: list[Any] = [urllib.request.ProxyHandler({}), _NoRedirect]
        if before_send is not None:
            handlers.append(_GuardedHTTPSHandler(before_send))
        opener = urllib.request.build_opener(*handlers)
        if before_send is not None:
            before_send()
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
        cancel_verification_attempts: int = CANCEL_VERIFICATION_ATTEMPTS,
        cancel_verification_interval_seconds: float = CANCEL_VERIFICATION_INTERVAL_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        utc_now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        if trading_base_url != PAPER_TRADING_BASE_URL:
            raise AlpacaPaperError("live or alternate trading endpoints are prohibited")
        if data_base_url != ALPACA_DATA_BASE_URL:
            raise AlpacaPaperError("alternate market-data endpoints are prohibited")
        if not api_key or not api_secret:
            raise AlpacaPaperError("paper API credentials are missing")
        if cancel_verification_attempts < 1 or cancel_verification_interval_seconds < 0:
            raise AlpacaPaperError("cancel verification settings are invalid")
        self._key = api_key
        self._secret = api_secret
        self._trading_base = PAPER_TRADING_BASE_URL
        self._data_base = ALPACA_DATA_BASE_URL
        self._timeout = timeout
        self._transport = transport or _default_transport
        self._default_transport_selected = transport is None
        self._permit_validator = permit_validator
        self._cancel_verification_attempts = cancel_verification_attempts
        self._cancel_verification_interval_seconds = cancel_verification_interval_seconds
        self._sleep = sleep
        self._utc_now = utc_now or (lambda: datetime.now(timezone.utc))
        self._monotonic = monotonic
        self._clock_anchor: tuple[datetime, float] | None = None
        self._verified_exit_permits: set[tuple[str, str, str]] = set()

    def _request(
        self,
        method: str,
        path: str,
        *,
        data_api: bool = False,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        _mutation_token: object | None = None,
        _proposal: OrderProposal | None = None,
        _permit: ApprovalPermit | None = None,
        _stage: str = "",
    ) -> Any:
        method = method.strip().upper()
        if method not in _ALLOWED_METHODS:
            raise AlpacaPaperError("unsupported broker HTTP method")
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
        before_send = None
        if method in _MUTATING_METHODS:
            if _proposal is None or _permit is None:
                raise AlpacaPaperError("broker mutation requires exact authorization terms")
            # Serialization and request construction must not outlive an earlier
            # permit check. Claim only once; subsequent socket checks never claim.
            self._require_permit(_proposal, _permit, _stage)
            before_send = lambda: self._require_transport_window(_permit)
        try:
            if self._default_transport_selected:
                return self._transport(
                    method, url, headers, encoded, self._timeout,
                    before_send=before_send,
                )
            if before_send is not None:
                before_send()
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
            trading_blocked=_boolean(value.get("trading_blocked", False)),
            account_blocked=_boolean(value.get("account_blocked", False)),
            trade_suspended_by_user=_boolean(
                value.get("trade_suspended_by_user", False)
            ),
        )

    def get_clock(self) -> PaperClock:
        started = self._monotonic()
        value = self._request("GET", "/v2/clock")
        clock = PaperClock(
            timestamp=parse_timestamp(str(value["timestamp"])),
            is_open=_boolean(value["is_open"]),
            next_open=parse_timestamp(str(value["next_open"])),
            next_close=parse_timestamp(str(value["next_close"])),
        )
        # Anchoring at request START conservatively includes the entire request
        # latency. A backwards local wall-clock step cannot extend authorization.
        anchor = clock.timestamp
        if self._clock_anchor is not None:
            previous, previous_started = self._clock_anchor
            elapsed = started - previous_started
            if elapsed < 0 or not math.isfinite(elapsed):
                raise AlpacaPaperError("monotonic mutation clock regressed")
            anchor = max(anchor, previous + timedelta(seconds=elapsed))
        self._clock_anchor = (anchor, started)
        return clock

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
            tradable=_boolean(value["tradable"]),
            fractionable=_boolean(value.get("fractionable", False)),
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
        if status not in {"open", "closed", "all"}:
            raise AlpacaPaperError("unsupported order-status filter")
        orders: list[PaperOrder] = []
        seen: set[str] = set()
        before_order_id: str | None = None
        while True:
            query: dict[str, Any] = {
                "status": status,
                "nested": "true",
                "limit": 500,
                "direction": "desc",
            }
            if before_order_id is not None:
                query["before_order_id"] = before_order_id
            values = self._request("GET", "/v2/orders", query=query)
            if not isinstance(values, list):
                raise AlpacaPaperError("broker order list is not an array")
            page = [_paper_order(value) for value in values]
            for order in page:
                if order.order_id in seen:
                    raise AlpacaPaperError("broker order pagination repeated an order")
                seen.add(order.order_id)
                orders.append(order)
            if len(page) < 500:
                return orders
            before_order_id = page[-1].order_id
            if not before_order_id:
                raise AlpacaPaperError("broker order pagination made no progress")

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
            _proposal=proposal, _permit=permit, _stage="submit_order",
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
        if (
            proposal.stop_price is not None
            or proposal.maximum_entry_reference is not None
            or not proposal.protective_stop_order_id
            or proposal.protective_stop_price is None
            or not proposal.protective_stop_price.is_finite()
            or proposal.protective_stop_price <= 0
        ):
            raise AlpacaPaperError(
                "close proposal has invalid entry or protective-stop binding terms"
            )
        permit_key = self._permit_key(proposal, permit)
        if permit_key not in self._verified_exit_permits:
            raise AlpacaPaperError(
                "close submission requires broker-verified protective-stop cancellation"
            )
        self._verified_exit_permits.discard(permit_key)
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
            _proposal=proposal, _permit=permit, _stage="submit_order",
        )
        return _paper_order(value)

    def cancel_order(
        self,
        order_id: str,
        expected_stop_price: Decimal,
        proposal: OrderProposal,
        permit: ApprovalPermit,
    ) -> PaperOrder:
        if proposal.action != "close_position":
            raise AlpacaPaperError("order cancellation requires an approved exit proposal")
        if (
            proposal.side != "sell"
            or proposal.quantity <= 0
            or proposal.order_type != "market"
            or proposal.time_in_force != "day"
            or proposal.order_class != "simple"
            or proposal.extended_hours
            or proposal.stop_price is not None
            or proposal.maximum_entry_reference is not None
        ):
            raise AlpacaPaperError("order cancellation requires valid approved exit terms")
        if not order_id:
            raise AlpacaPaperError("order cancellation requires a broker order id")
        if proposal.protective_stop_order_id != order_id:
            raise AlpacaPaperError(
                "order cancellation is not bound to the approved protective stop id"
            )
        if (
            not expected_stop_price.is_finite()
            or expected_stop_price <= 0
            or proposal.protective_stop_price != expected_stop_price
        ):
            raise AlpacaPaperError("protective stop price is invalid")
        self._request(
            "DELETE",
            f"/v2/orders/{urllib.parse.quote(order_id, safe='')}",
            _mutation_token=_MUTATION_TOKEN,
            _proposal=proposal, _permit=permit, _stage="cancel_protective_stop",
        )
        terminal = {"canceled", "expired", "filled", "rejected", "replaced"}
        order: PaperOrder | None = None
        for attempt in range(self._cancel_verification_attempts):
            order = self.get_order(order_id)
            self._validate_canceled_stop_envelope(
                order, order_id, expected_stop_price, proposal
            )
            if order.status in terminal:
                break
            if attempt + 1 < self._cancel_verification_attempts:
                self._sleep(self._cancel_verification_interval_seconds)
        assert order is not None
        if (
            order.status in {"canceled", "expired"}
            and order.filled_quantity == 0
            and order.filled_average_price is None
            and order.filled_at is None
        ):
            self._verified_exit_permits.add(self._permit_key(proposal, permit))
        return order

    @staticmethod
    def _validate_canceled_stop_envelope(
        order: PaperOrder,
        order_id: str,
        expected_stop_price: Decimal,
        proposal: OrderProposal,
    ) -> None:
        if (
            order.order_id != order_id
            or order.symbol != proposal.symbol
            or order.side != "sell"
            or order.order_type != "stop"
            or order.time_in_force != "gtc"
            or order.quantity != proposal.quantity
            or order.stop_price != expected_stop_price
            or order.extended_hours
            or bool(order.legs)
        ):
            raise AlpacaPaperError(
                "broker protective-stop acknowledgement differs from the managed stop"
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
        seen_dates: dict[str, set[date]] = {symbol: set() for symbol in clean_symbols}
        seen_page_tokens: set[str] = set()
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
            if not isinstance(value, dict) or not isinstance(value.get("bars"), dict):
                raise AlpacaPaperError("broker bar page has an invalid shape")
            page_rows = 0
            for symbol, rows in value["bars"].items():
                clean = _symbol(symbol)
                if clean not in bars or not isinstance(rows, list):
                    raise AlpacaPaperError("broker bar page contains an unexpected symbol or rows")
                for row in rows:
                    bar = _validated_bar(clean, row, start=start, end=end)
                    if bar.date in seen_dates[clean]:
                        raise AlpacaPaperError(
                            "broker bar pagination repeated a symbol/date"
                        )
                    seen_dates[clean].add(bar.date)
                    bars[clean].append(bar)
                    page_rows += 1
            next_page_token = value.get("next_page_token")
            if next_page_token in (None, ""):
                break
            if not isinstance(next_page_token, str):
                raise AlpacaPaperError("broker bar pagination token is invalid")
            if page_rows == 0:
                raise AlpacaPaperError("broker bar pagination made no row progress")
            if next_page_token in seen_page_tokens:
                raise AlpacaPaperError("broker bar pagination made no progress")
            seen_page_tokens.add(next_page_token)
            page_token = next_page_token
        for symbol in bars:
            bars[symbol].sort(key=lambda bar: bar.date)
        return bars

    def _require_permit(
        self, proposal: OrderProposal, permit: ApprovalPermit, stage: str
    ) -> None:
        mutation_at = self._effective_now()
        basic = (
            isinstance(permit, ApprovalPermit)
            and permit.proposal_id == proposal.proposal_id
            and permit.content_hash == proposal.content_hash
            and bool(permit.approval_event_id)
            and bool(permit.review_event_id)
            and bool(permit.session_id)
            and permit.issued_at.tzinfo is not None
            and permit.mutation_deadline.tzinfo is not None
            and mutation_at.tzinfo is not None
            and mutation_at < permit.mutation_deadline
        )
        if (
            not basic
            or self._permit_validator is None
            or not self._permit_validator(proposal, permit, stage, mutation_at)
        ):
            raise AlpacaPaperError("broker mutation lacks an unused journal-backed approval permit")
        self._require_transport_window(permit)

    def _effective_now(self) -> datetime:
        local = self._utc_now()
        if local.tzinfo is None:
            raise AlpacaPaperError("mutation clock must be timezone-aware")
        if self._clock_anchor is not None:
            broker_time, started = self._clock_anchor
            elapsed = self._monotonic() - started
            if elapsed < 0 or not math.isfinite(elapsed):
                raise AlpacaPaperError("monotonic mutation clock regressed")
            return max(local, broker_time + timedelta(seconds=elapsed))
        if self._default_transport_selected:
            raise AlpacaPaperError("broker clock must be sampled before mutation")
        return local  # Explicitly injected offline transports retain a test clock.

    def _require_transport_window(self, permit: ApprovalPermit) -> None:
        # Reserve the entire tolerated clock uncertainty, never use it to extend
        # a deadline. Equality is expired. Network arrival time is not guaranteed.
        if self._effective_now() + timedelta(
            seconds=QUOTE_FUTURE_TOLERANCE_SECONDS
        ) >= permit.mutation_deadline:
            raise AlpacaPaperError("broker mutation approval expired before transport")

    @staticmethod
    def _permit_key(
        proposal: OrderProposal, permit: ApprovalPermit
    ) -> tuple[str, str, str]:
        return (
            proposal.proposal_id,
            proposal.content_hash,
            permit.approval_event_id,
        )


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _boolean(value: Any) -> bool:
    if type(value) is not bool:
        raise AlpacaPaperError("broker returned a non-boolean boolean field")
    return value


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
        # Alpaca's own simple-order examples use an empty string even though the
        # documented enum names this class "simple". Normalize the wire value so
        # exact exit acknowledgement checks work with either representation.
        order_class=str(value.get("order_class") or "simple"),
        status=str(value["status"]),
        quantity=_decimal(value.get("qty", "0")),
        filled_quantity=_decimal(value.get("filled_qty", "0")),
        filled_average_price=_decimal(value["filled_avg_price"])
        if value.get("filled_avg_price") is not None else None,
        stop_price=_decimal(value["stop_price"]) if value.get("stop_price") is not None else None,
        parent_order_id=str(value["parent_order_id"])
        if value.get("parent_order_id") else None,
        legs=legs,
        filled_at=parse_timestamp(str(value["filled_at"]))
        if value.get("filled_at") else None,
        extended_hours=_boolean(value.get("extended_hours", False)),
    )


def _validated_bar(
    symbol: str, value: Any, *, start: date, end: date
) -> Bar:
    if not isinstance(value, dict):
        raise AlpacaPaperError("broker bar row is not an object")
    try:
        bar_date = parse_timestamp(str(value["t"])).date()
        open_price = _finite_float(value["o"])
        high = _finite_float(value["h"])
        low = _finite_float(value["l"])
        close = _finite_float(value["c"])
        volume = _finite_float(value["v"])
    except (KeyError, TypeError, ValueError, OverflowError):
        raise AlpacaPaperError("broker bar row contains invalid numeric or time data") from None
    prices = (open_price, high, low, close)
    if (
        not start <= bar_date <= end
        or any(price <= 0 for price in prices)
        or volume < 0
        or low > min(open_price, close)
        or high < max(open_price, close)
        or low > high
    ):
        raise AlpacaPaperError("broker bar row violates date or OHLCV constraints")
    return Bar(symbol, bar_date, open_price, high, low, close, volume)


def _finite_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not a numeric market value")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("market value is not finite")
    return parsed
