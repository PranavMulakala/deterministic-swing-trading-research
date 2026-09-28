"""Frozen configuration loader with an immutable execution prohibition."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import ValidationError
from . import ORDERS_ENABLED


ROOT = Path(__file__).resolve().parent


def load_config(path: Path | None = None) -> dict[str, Any]:
    target = path or ROOT / "config.json"
    raw = json.loads(target.read_text(encoding="utf-8"))
    if type(raw) is not dict:
        raise ValidationError("config must be an object")
    if raw.get("orders_enabled") is not False or ORDERS_ENABLED is not False:
        raise ValidationError("orders_enabled is an immutable false invariant")
    if raw.get("mode") != "PAPER_ONLY_NO_ORDER":
        raise ValidationError("mode must remain PAPER_ONLY_NO_ORDER")
    return raw

