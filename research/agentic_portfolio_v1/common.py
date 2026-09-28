"""Strict primitives shared by the paper-only research engines."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
from typing import Any


class ValidationError(ValueError):
    """Input did not satisfy a frozen research contract."""


def aware_datetime(value: str | datetime, *, field: str = "timestamp") -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be an ISO-8601 timestamp") from exc
    if not isinstance(parsed, datetime) or parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def decimal_value(value: Any, *, field: str, positive: bool = False, nonnegative: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise ValidationError(f"{field} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be a finite decimal") from exc
    if not result.is_finite():
        raise ValidationError(f"{field} must be a finite decimal")
    if positive and result <= 0:
        raise ValidationError(f"{field} must be positive")
    if nonnegative and result < 0:
        raise ValidationError(f"{field} must be nonnegative")
    return result


def integer_value(value: Any, *, field: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{field} must be >= {minimum}")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def ceil_cent(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_CEILING)


def floor_units(value: Decimal, precision: str = "0.000001") -> Decimal:
    return value.quantize(Decimal(precision), rounding=ROUND_FLOOR)


def require_plain_dict(value: Any, *, field: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValidationError(f"{field} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise ValidationError(f"{field} keys must be strings")
    return value
