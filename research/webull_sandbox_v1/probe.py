"""Bounded read-only Webull MNQ probe. No order-writing endpoint is permitted."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlsplit
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_webull_sandbox import credentials

HOST = "api.sandbox.webull.com"
SYMBOL = "MNQU6"
PATHS = {
    "/openapi/config": set(),
    "/trading/accounts/list": set(),
    "/trading/assets/balances/get": {"account_id"},
    "/trading/assets/positions/list": {"account_id"},
    "/trading/orders/open-orders/list": {"account_id"},
    "/trading/instruments/futures/contracts/list": {"symbols", "category"},
    "/market-data/futures/snapshots/list": {"symbols", "category"},
    "/market-data/futures/depths/list": {"symbol", "category", "depth"},
}
PUBLIC_FIELDS = {
    "symbol", "name", "category", "code", "status", "account_type", "account_status",
    "account_class", "account_label", "contract_month", "settlement_date", "unit",
    "last_trade_time", "quote_time", "settlement",
    "trade_permissions", "trading_permissions", "currency", "exchange_code",
    "contract_type", "contract_multiplier", "multiplier", "min_tick", "tick_size",
    "tick_value", "expiration_date", "expire_date", "trading_status", "last_trading_date",
    "timestamp", "trade_time", "update_time", "latest_price", "price", "close",
    "bid", "ask", "bid_price", "ask_price", "bid_size", "ask_size", "volume",
    "total_volume", "trade_status", "is_delayed", "delay", "time", "size",
    "positions", "orders", "items", "data", "bids", "asks", "quote", "quotes",
    "tick", "lot_size", "product_code", "min_order_quantity", "security_type",
    "initial_margin", "maintenance_margin", "quantity", "position", "total_asset",
    "cash_balance", "net_liquidation", "buying_power", "available_cash", "cash",
}


def public(value):
    """Whitelist fields; never persist account IDs, raw errors or auth material."""
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items() if k in PUBLIC_FIELDS}
    if isinstance(value, list):
        return [public(v) for v in value[:100]]
    return value


def rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "accounts", "account_list", "items", "positions", "orders"):
            if isinstance(payload.get(key), list):
                return payload[key]
            if isinstance(payload.get(key), dict):
                nested = rows(payload[key])
                if nested is not None:
                    return nested
    return None


def guard(original, trace, account_ids, secret_values=()):
    def send(session, request, **kwargs):
        u = urlsplit(request.url)
        query = parse_qsl(u.query, keep_blank_values=True)
        q = dict(query)
        if (u.scheme != "https" or u.netloc != HOST or u.fragment or
                request.method != "GET" or request.body or u.path not in PATHS or
                set(q) != PATHS[u.path] or len(q) != len(query) or kwargs.get("verify") is not True):
            raise ValueError("blocked_request")
        if "account_id" in q and q["account_id"] not in account_ids:
            raise ValueError("unverified_account")
        if any(q[k] != SYMBOL for k in ("symbols", "symbol") if k in q):
            raise ValueError("wrong_symbol")
        if "category" in q and q["category"] != "US_FUTURES":
            raise ValueError("wrong_category")
        if "depth" in q and q["depth"] != "1":
            raise ValueError("wrong_depth")
        if len(trace) >= 16:
            raise ValueError("request_budget_exceeded")
        event = {"path": u.path, "sent_at_utc": datetime.now(timezone.utc).isoformat()}
        trace.append(event)
        kwargs["allow_redirects"] = False
        try:
            result = original(session, request, **kwargs)
            event["status"] = result.status_code
            event["received_at_utc"] = datetime.now(timezone.utc).isoformat()
            if result.status_code != 200:
                try:
                    body = result.json()
                    code = body.get("code", body.get("error_code"))
                    if isinstance(code, str) and re.fullmatch(r"[A-Za-z_][A-Za-z_.-]{0,80}", code):
                        event["error_code"] = code
                    message = str(body.get("msg", body.get("message", ""))).lower()
                    for value in (*secret_values, *account_ids):
                        if value:
                            message = message.replace(str(value).lower(), "[redacted]")
                    message = re.sub(r"[a-z0-9_./+=-]{24,}", "[redacted]", message)
                    event["error_message"] = message[:300]
                    event["mentions_permission"] = "permission" in message
                    event["mentions_subscription"] = "subscri" in message
                except Exception:
                    pass
            return result
        except Exception as exc:
            event["error_type"] = type(exc).__name__
            raise
    return send


def request_result(response):
    result = {"http_status": response.status_code,
              "observed_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        payload = response.json()
    except Exception:
        return {**result, "result": "NON_JSON_RESPONSE"}, None
    if not isinstance(payload, (dict, list)):
        return {**result, "result": "INVALID_RESPONSE_STRUCTURE"}, None
    if response.status_code != 200:
        code = payload.get("code", payload.get("error_code")) if isinstance(payload, dict) else None
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z_][A-Za-z_.-]{0,80}", code):
            result["error_code"] = code
        return result, None
    result["response_sha256"] = hashlib.sha256(response.content).hexdigest()
    result["public_fields"] = public(payload)
    result["top_level_field_names"] = sorted(payload) if isinstance(payload, dict) else []
    if isinstance(payload, dict):
        result["more_pages_indicated"] = any(bool(payload.get(k)) for k in
            ("pagination_key", "next_page", "next", "has_more", "next_cursor"))
    data_rows = rows(payload)
    if data_rows is not None:
        result["row_count"] = len(data_rows)
        result["row_field_names"] = sorted({k for r in data_rows if isinstance(r, dict) for k in r})
    return result, payload


def access_blockers(report):
    required = ("accounts", "futures_balance", "futures_positions", "futures_open_orders",
                "contract", "snapshot", "depth")
    blockers = [name.upper() + "_UNAVAILABLE" for name in required
                if report["checks"].get(name, {}).get("http_status") != 200
                or report["checks"].get(name, {}).get("result")]
    if report.get("futures_account_count") != 1:
        blockers.append("EXACTLY_ONE_FUTURES_ACCOUNT_REQUIRED")
    return blockers


def main():
    logging.disable(logging.CRITICAL)
    from dotenv import dotenv_values
    from requests import Session
    from webull.core.client import ApiClient
    from webull.trade.trade_client import TradeClient
    from webull.data.data_client import DataClient

    report = {"schema_version": 1, "evidence_kind": "ACTUAL_SANDBOX_READ_ONLY_PROBE",
              "checked_at_utc": datetime.now(timezone.utc).isoformat(), "symbol": SYMBOL,
              "environment": "SANDBOX", "orders_enabled": False, "orders_submitted": 0,
              "live_trial_authorized": False, "requests": [], "checks": {},
              "execution_readiness": "NOT_READY"}
    verified_ids = set()
    def check(label, fn):
        before = len(report["requests"])
        try:
            result, payload = request_result(fn())
            report["checks"][label] = result
            return payload
        except Exception as exc:
            report["checks"][label] = {"error_type": type(exc).__name__, "result": "REQUEST_FAILED"}
            if len(report["requests"]) > before:
                last = report["requests"][-1]
                report["checks"][label].update({k: last[k] for k in
                    ("status", "error_code", "error_message", "mentions_permission", "mentions_subscription") if k in last})
            return None
    try:
        _, _, key, secret = credentials(dotenv_values(ROOT / ".env", interpolate=False))
        api = ApiClient(key, secret, "us", connect_timeout=8, timeout=15,
                        auto_retry=False, verify=True)
        api.add_endpoint("us", HOST)
        api.set_stream_logger(stream=io.StringIO(), log_level=logging.CRITICAL)
        with patch.object(Session, "send", guard(Session.send, report["requests"], verified_ids, (key, secret))):
            trade = TradeClient(api)
            payload = check("accounts", trade.account_v2.get_account_list)
            accounts = rows(payload) or []
            futures = [r for r in accounts if isinstance(r, dict) and
                       r.get("account_class") == "FUTURES"]
            report["futures_account_count"] = len(futures)
            if len(futures) == 1 and futures[0].get("account_id"):
                account_id = futures[0]["account_id"]
                verified_ids.add(account_id)
                for label, fn in (("futures_balance", trade.account_v2.get_account_balance),
                                  ("futures_positions", trade.account_v2.get_account_position),
                                  ("futures_open_orders", trade.order_v3.list_order_open)):
                    check(label, lambda fn=fn: fn(account_id))
            data = DataClient(api)
            for label, fn in (
                ("contract", lambda: data.instrument.get_futures_instrument(symbols=SYMBOL, category="US_FUTURES")),
                ("snapshot", lambda: data.futures_market_data.get_futures_snapshot(SYMBOL, "US_FUTURES")),
                ("depth", lambda: data.futures_market_data.get_futures_depth(SYMBOL, "US_FUTURES", depth=1)),
            ):
                check(label, fn)
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["result"] = "PROBE_INCOMPLETE"
    report["access_blockers"] = access_blockers(report)
    if report.get("result") != "PROBE_INCOMPLETE":
        report["result"] = "ACCESS_BLOCKED" if report["access_blockers"] else "READ_ACCESS_VERIFIED_ONLY"
    out = ROOT / "outputs/paper/webull_sandbox"
    out.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    path = out / name
    with path.open("x") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    tmp = out / (name + ".tmp")
    tmp.write_text(json.dumps({"report": name}, indent=2) + "\n")
    os.replace(tmp, out / "latest.json")
    print(json.dumps(report, indent=2))
    return 1 if report["result"] == "PROBE_INCOMPLETE" else 2 if report["access_blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
