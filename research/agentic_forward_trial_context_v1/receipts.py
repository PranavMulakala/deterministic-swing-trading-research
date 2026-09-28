"""Strict immutable receipts for data already archived by an external collector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any


KINDS = frozenset({"STOCK_PRICE_INPUT", "OPTION_CHAIN_INPUT", "MARKET_CONTEXT", "NEWS_ARCHIVE"})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ReceiptError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ReceiptError("receipt must contain only finite JSON data") from exc


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def aware_utc(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    except (TypeError, ValueError) as exc:
        raise ReceiptError(f"{field} must be an ISO-8601 timestamp") from exc
    if not isinstance(parsed, datetime) or parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReceiptError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def decimal_string(value: Any, field: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ReceiptError(f"{field} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ReceiptError(f"{field} must be a finite decimal string") from exc
    if not parsed.is_finite() or (positive and parsed <= 0):
        raise ReceiptError(f"{field} must be {'positive ' if positive else ''}finite")
    return parsed


def plain_object(value: Any, field: str) -> dict[str, Any]:
    if type(value) is not dict or not all(isinstance(key, str) for key in value):
        raise ReceiptError(f"{field} must be a plain JSON object")
    return value


@dataclass(frozen=True)
class ArchiveReceipt:
    schema_version: str
    receipt_id: str
    kind: str
    provider: str
    observed_at: datetime
    retrieved_at: datetime
    archived_at: datetime
    payload: dict[str, Any]
    receipt_hash: str

    @classmethod
    def build(
        cls, *, receipt_id: str, kind: str, provider: str, observed_at: datetime,
        retrieved_at: datetime, archived_at: datetime, payload: dict[str, Any],
    ) -> "ArchiveReceipt":
        unsigned = {
            "schema_version": "1.0", "receipt_id": receipt_id, "kind": kind,
            "provider": provider, "observed_at": aware_utc(observed_at, "observed_at").isoformat(),
            "retrieved_at": aware_utc(retrieved_at, "retrieved_at").isoformat(),
            "archived_at": aware_utc(archived_at, "archived_at").isoformat(),
            "payload": json.loads(canonical_json(plain_object(payload, "payload"))),
        }
        return cls.from_dict({**unsigned, "receipt_hash": sha256_json(unsigned)})

    @classmethod
    def from_dict(cls, raw: Any) -> "ArchiveReceipt":
        data = plain_object(raw, "receipt")
        expected = {
            "schema_version", "receipt_id", "kind", "provider", "observed_at",
            "retrieved_at", "archived_at", "payload", "receipt_hash",
        }
        if set(data) != expected:
            raise ReceiptError("receipt fields do not match schema 1.0")
        if data["schema_version"] != "1.0" or data["kind"] not in KINDS:
            raise ReceiptError("unsupported receipt schema or kind")
        for field in ("receipt_id", "provider"):
            if not isinstance(data[field], str) or not data[field].strip() or len(data[field]) > 200:
                raise ReceiptError(f"{field} must be a bounded non-empty string")
        supplied = data["receipt_hash"]
        if not isinstance(supplied, str) or not _HEX64.fullmatch(supplied):
            raise ReceiptError("receipt_hash must be lowercase SHA-256")
        unsigned = {key: data[key] for key in expected if key != "receipt_hash"}
        if sha256_json(unsigned) != supplied:
            raise ReceiptError("receipt hash mismatch")
        observed = aware_utc(data["observed_at"], "observed_at")
        retrieved = aware_utc(data["retrieved_at"], "retrieved_at")
        archived = aware_utc(data["archived_at"], "archived_at")
        for field, parsed in (("observed_at", observed), ("retrieved_at", retrieved), ("archived_at", archived)):
            if data[field] != parsed.isoformat():
                raise ReceiptError(f"{field} must use canonical UTC ISO-8601 form")
        if observed > retrieved or retrieved > archived:
            raise ReceiptError("require observed_at <= retrieved_at <= archived_at")
        payload = json.loads(canonical_json(plain_object(data["payload"], "payload")))
        return cls(
            schema_version="1.0", receipt_id=data["receipt_id"], kind=data["kind"],
            provider=data["provider"], observed_at=observed, retrieved_at=retrieved,
            archived_at=archived, payload=payload, receipt_hash=supplied,
        )

    def validate_at(self, cutoff: datetime, *, max_age: timedelta | None = None) -> None:
        point = aware_utc(cutoff, "receipt_cutoff")
        if self.archived_at > point:
            raise ReceiptError("receipt was not archived by the decision cutoff")
        if max_age is not None:
            age = point - self.observed_at
            if age < timedelta(0) or age > max_age:
                raise ReceiptError("receipt is stale or future-dated at the cutoff")
        # Rebuild to detect mutation of nested objects after construction.
        rebuilt = ArchiveReceipt.build(
            receipt_id=self.receipt_id, kind=self.kind, provider=self.provider,
            observed_at=self.observed_at, retrieved_at=self.retrieved_at,
            archived_at=self.archived_at, payload=self.payload,
        )
        if rebuilt.receipt_hash != self.receipt_hash:
            raise ReceiptError("receipt hash mismatch after construction")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "receipt_id": self.receipt_id,
            "kind": self.kind, "provider": self.provider,
            "observed_at": self.observed_at.isoformat(), "retrieved_at": self.retrieved_at.isoformat(),
            "archived_at": self.archived_at.isoformat(),
            "payload": json.loads(canonical_json(self.payload)), "receipt_hash": self.receipt_hash,
        }
