"""Read-only Webull sandbox authentication check. Never submits orders.

Run with outputs/tmp/webull-check-venv/bin/python scripts/check_webull_sandbox.py.
Loads the project's .env without modifying it or exporting its credentials.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT_LIST_URL = "https://api.sandbox.webull.com/trading/accounts/list"
CONFIG_URL = "https://api.sandbox.webull.com/openapi/config"
KEY_PAIRS = (
    ("PAPER_TRADING_APP_KEY", "PAPER_TRADING_APP_SECRET"),
    ("PAPER_TRADING_API_KEY", "PAPER_TRADING_API_SECRET"),
)


def credentials(values):
    pairs = []
    for key_name, secret_name in KEY_PAIRS:
        key, secret = values.get(key_name), values.get(secret_name)
        if bool(key) != bool(secret):
            raise ValueError("incomplete_credential_pair")
        if key and secret:
            pairs.append((key_name, secret_name, key, secret))
    if not pairs:
        raise ValueError("missing_credentials")
    if len({(p[2], p[3]) for p in pairs}) > 1:
        raise ValueError("conflicting_credential_aliases")
    return pairs[0]


def guarded_send(original_send, trace=None):
    def send(session, request, **kwargs):
        if request.method != "GET" or request.url not in {ACCOUNT_LIST_URL, CONFIG_URL}:
            raise ValueError("blocked_endpoint_or_method")
        if request.body:
            raise ValueError("blocked_request_body")
        if kwargs.get("verify") is not True:
            raise ValueError("tls_verification_required")
        kwargs["allow_redirects"] = False
        event = {"path": request.url.removeprefix("https://api.sandbox.webull.com")}
        if trace is not None:
            trace.append(event)
        try:
            response = original_send(session, request, **kwargs)
            event["http_status"] = response.status_code
            return response
        except Exception as exc:
            event["transport_error_type"] = type(exc).__name__
            message = str(exc).lower()
            for category, clues in {
                "dns_failure": ("nameresolutionerror", "name or service not known", "nodename nor servname"),
                "permission_denied": ("operation not permitted", "permission denied"),
                "tls_failure": ("certificate verify failed", "sslerror"),
                "timeout": ("timed out", "timeout"),
            }.items():
                if any(clue in message for clue in clues):
                    event["transport_diagnosis"] = category
                    break
            raise

    return send


def main():
    # SDK debug output can contain authentication headers. Disable it entirely.
    logging.disable(logging.CRITICAL)
    from dotenv import dotenv_values
    from requests import Session
    from webull.core.client import ApiClient
    from webull.trade.trade_client import TradeClient

    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "webull_sandbox",
        "operation": "GET /trading/accounts/list",
        "sdk_preflight": "GET /openapi/config",
        "orders_submitted": 0,
        "authentication": "unverified",
        "requests": [],
    }
    try:
        names_and_values = credentials(dotenv_values(ROOT / ".env", interpolate=False))
        report["credential_variable_names"] = list(names_and_values[:2])
        key, secret = names_and_values[2:]
        api = ApiClient(key, secret, "us", connect_timeout=8, timeout=15,
                        auto_retry=False, verify=True)
        api.add_endpoint("us", "api.sandbox.webull.com")
        with patch.object(Session, "send", guarded_send(Session.send, report["requests"])):
            response = TradeClient(api).account_v2.get_account_list()
        report["http_status"] = response.status_code
        if response.status_code == 200:
            payload = response.json()
            # Retain no account identifiers, balances, or raw server messages.
            if isinstance(payload, dict):
                accounts = payload.get("data")
                if isinstance(accounts, dict):
                    accounts = accounts.get("accounts", accounts.get("account_list"))
            else:
                accounts = payload
            if isinstance(accounts, list):
                report["account_count"] = len(accounts)
                report["authentication"] = "verified"
            else:
                report["result"] = "unexpected_response_structure"
        else:
            report["result"] = "sandbox_request_rejected"
    except Exception as exc:
        # Do not print exception text: SDK errors can include signed requests.
        report["error_type"] = type(exc).__name__
        if isinstance(exc, ValueError) and str(exc) in {
            "incomplete_credential_pair", "missing_credentials",
            "conflicting_credential_aliases", "blocked_endpoint_or_method",
            "blocked_request_body", "tls_verification_required",
        }:
            report["result"] = str(exc)
        else:
            report["result"] = "connection_check_failed"
    output = ROOT / "outputs" / "paper" / "webull_sandbox_connection.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["authentication"] == "verified" else 1


if __name__ == "__main__":
    sys.exit(main())
