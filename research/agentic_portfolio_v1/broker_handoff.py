"""Validation-only broker handoff. No brokerage library or endpoint is accepted."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from .common import ValidationError, aware_datetime, decimal_value, require_plain_dict, sha256_json


RECEIPT_FIELDS = {
    "ACCOUNT_READ": {"receipt_type", "account_ref", "status", "buying_power", "observed_at", "retrieved_at", "receipt_hash"},
    "QUOTE_READ": {"receipt_type", "symbol", "bid", "ask", "source", "observed_at", "retrieved_at", "receipt_hash"},
    "ORDER_REVIEW": {
        "receipt_type", "intent_hash", "account_ref", "symbol", "side", "quantity", "order_type",
        "limit_price", "time_in_force", "estimated_cost", "warnings", "reviewed_at", "status", "receipt_hash",
        "quote_receipt_hash", "quote_symbol", "quote_observed_at", "quote_retrieved_at",
    },
}


def sign_receipt(unsigned: dict[str, Any]) -> dict[str, Any]:
    unsigned = require_plain_dict(unsigned, field="unsigned_receipt")
    if "receipt_hash" in unsigned:
        raise ValidationError("unsigned receipt must not contain receipt_hash")
    return {**unsigned, "receipt_hash": sha256_json(unsigned)}


def validate_receipt(
    raw: Any, *, now: Any, max_age: timedelta = timedelta(minutes=2),
    quote_receipt: Any = None,
) -> dict[str, Any]:
    receipt = require_plain_dict(raw, field="broker_receipt")
    kind = receipt.get("receipt_type")
    if kind not in RECEIPT_FIELDS or set(receipt) != RECEIPT_FIELDS[kind]:
        raise ValidationError("broker receipt fields do not match read-only schema")
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if not isinstance(receipt["receipt_hash"], str) or len(receipt["receipt_hash"]) != 64 or any(
        char not in "0123456789abcdef" for char in receipt["receipt_hash"]
    ) or receipt["receipt_hash"] != sha256_json(unsigned):
        raise ValidationError("broker receipt hash mismatch")
    current = aware_datetime(now, field="now")
    if not isinstance(max_age, timedelta) or max_age <= timedelta(0):
        raise ValidationError("max_age must be a positive timedelta")
    for forbidden in ("endpoint", "url", "order_id", "cancel", "replace", "submit", "transmit"):
        if forbidden in receipt:
            raise ValidationError("broker receipt contains an execution field")
    if kind in {"ACCOUNT_READ", "QUOTE_READ"}:
        if not isinstance(receipt["observed_at"], str) or not isinstance(receipt["retrieved_at"], str):
            raise ValidationError("broker timestamps must be ISO-8601 strings")
        observed = aware_datetime(receipt["observed_at"], field="observed_at")
        retrieved = aware_datetime(receipt["retrieved_at"], field="retrieved_at")
        if observed > retrieved or retrieved > current or current - observed > max_age:
            raise ValidationError("broker read receipt is stale or future-dated")
    if kind == "ACCOUNT_READ":
        if receipt["status"] != "READ_ONLY" or not isinstance(receipt["account_ref"], str) or not receipt["account_ref"].strip():
            raise ValidationError("account receipt must be READ_ONLY")
        if not isinstance(receipt["buying_power"], str):
            raise ValidationError("buying_power must be a decimal string")
        decimal_value(receipt["buying_power"], field="buying_power", nonnegative=True)
    elif kind == "QUOTE_READ":
        if (
            not isinstance(receipt["symbol"], str) or not receipt["symbol"].strip()
            or receipt["symbol"] != receipt["symbol"].upper()
            or not receipt["symbol"].isascii() or not receipt["symbol"].replace(".", "").isalnum()
            or not isinstance(receipt["source"], str) or not receipt["source"].strip()
        ):
            raise ValidationError("invalid quote identity")
        if not isinstance(receipt["bid"], str) or not isinstance(receipt["ask"], str):
            raise ValidationError("quote prices must be decimal strings")
        bid = decimal_value(receipt["bid"], field="bid", nonnegative=True)
        ask = decimal_value(receipt["ask"], field="ask", positive=True)
        if bid > ask:
            raise ValidationError("crossed quote")
    else:
        for field in ("intent_hash", "quote_receipt_hash"):
            value = receipt[field]
            if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValidationError(f"{field} must be a lowercase SHA-256 hash")
        for field in ("account_ref", "symbol", "quote_symbol"):
            if not isinstance(receipt[field], str) or not receipt[field].strip():
                raise ValidationError(f"{field} must be a non-empty string")
        if (
            receipt["symbol"] != receipt["symbol"].upper()
            or receipt["quote_symbol"] != receipt["symbol"]
            or not receipt["symbol"].isascii()
            or not receipt["symbol"].replace(".", "").replace(":", "").replace("-", "").isalnum()
        ):
            raise ValidationError("order review is not bound to the quoted symbol")
        if not all(isinstance(receipt[field], str) for field in (
            "quantity", "limit_price", "estimated_cost", "reviewed_at",
            "quote_observed_at", "quote_retrieved_at",
        )):
            raise ValidationError("order review numbers and timestamps must be strings")
        quote_observed = aware_datetime(receipt["quote_observed_at"], field="quote_observed_at")
        quote_retrieved = aware_datetime(receipt["quote_retrieved_at"], field="quote_retrieved_at")
        reviewed = aware_datetime(receipt["reviewed_at"], field="reviewed_at")
        if quote_observed > quote_retrieved or quote_retrieved > reviewed or reviewed > current:
            raise ValidationError("order review timestamps are not causal")
        if current - quote_observed > max_age:
            raise ValidationError("order review quote is stale")
        if quote_receipt is None:
            raise ValidationError("actual signed QUOTE_READ receipt is required for order review")
        quote = validate_receipt(quote_receipt, now=current, max_age=max_age)
        if quote["receipt_type"] != "QUOTE_READ":
            raise ValidationError("order review requires a QUOTE_READ receipt")
        if (
            receipt["quote_receipt_hash"] != quote["receipt_hash"]
            or receipt["symbol"] != quote["symbol"]
            or receipt["quote_symbol"] != quote["symbol"]
            or receipt["quote_observed_at"] != quote["observed_at"]
            or receipt["quote_retrieved_at"] != quote["retrieved_at"]
        ):
            raise ValidationError("order review is not bound to the supplied signed quote receipt")
        if receipt["status"] != "REVIEW_ONLY" or receipt["side"] not in {"BUY", "SELL"}:
            raise ValidationError("order review cannot authorize execution")
        if receipt["order_type"] != "LIMIT" or receipt["time_in_force"] not in {"DAY", "GTC"}:
            raise ValidationError("unsupported review shape")
        decimal_value(receipt["quantity"], field="quantity", positive=True)
        decimal_value(receipt["limit_price"], field="limit_price", positive=True)
        decimal_value(receipt["estimated_cost"], field="estimated_cost", nonnegative=True)
        if type(receipt["warnings"]) is not list or not all(isinstance(v, str) and v.strip() for v in receipt["warnings"]):
            raise ValidationError("warnings must be a list of strings")
    return receipt
