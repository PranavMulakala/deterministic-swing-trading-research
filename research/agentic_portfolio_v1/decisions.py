"""Internal paper decision type; it deliberately contains no execution method."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PaperDecision:
    action: str
    strategy: str
    version: str
    virtual_account: str
    symbol: str
    reasons: tuple[str, ...]
    evidence_hash: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    paper_only: bool = True
    no_order: bool = True

