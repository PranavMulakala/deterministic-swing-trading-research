"""Hash-bound, point-in-time evidence packet validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from typing import Any

from .common import ValidationError, aware_datetime, canonical_json, require_plain_dict, sha256_json


@dataclass(frozen=True)
class EvidencePacket:
    kind: str
    strategy: str
    version: str
    symbol: str
    source: str
    feature_as_of: datetime
    observed_at: datetime
    retrieved_at: datetime
    data: dict[str, Any]
    evidence_hash: str

    @classmethod
    def build(
        cls,
        *,
        kind: str,
        strategy: str,
        version: str,
        symbol: str,
        source: str,
        feature_as_of: datetime,
        observed_at: datetime,
        retrieved_at: datetime,
        data: dict[str, Any],
    ) -> "EvidencePacket":
        unsigned = {
            "kind": kind,
            "strategy": strategy,
            "version": version,
            "symbol": symbol,
            "source": source,
            "feature_as_of": aware_datetime(feature_as_of).isoformat(),
            "observed_at": aware_datetime(observed_at).isoformat(),
            "retrieved_at": aware_datetime(retrieved_at).isoformat(),
            "data": data,
        }
        return cls.from_dict({**unsigned, "evidence_hash": sha256_json(unsigned)})

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvidencePacket":
        payload = require_plain_dict(raw, field="evidence")
        expected = {
            "kind", "strategy", "version", "symbol", "source",
            "feature_as_of", "observed_at", "retrieved_at", "data", "evidence_hash",
        }
        if set(payload) != expected:
            raise ValidationError("evidence fields do not match the frozen protocol")
        unsigned = {key: payload[key] for key in expected if key != "evidence_hash"}
        supplied_hash = payload["evidence_hash"]
        if not isinstance(supplied_hash, str) or supplied_hash != sha256_json(unsigned):
            raise ValidationError("evidence hash mismatch")
        for field in ("kind", "strategy", "version", "symbol", "source"):
            if not isinstance(payload[field], str) or not payload[field].strip():
                raise ValidationError(f"{field} must be a non-empty string")
        symbol = payload["symbol"].upper()
        if symbol != payload["symbol"] or not symbol.isascii() or not symbol.replace(".", "").isalnum():
            raise ValidationError("symbol must be an uppercase ASCII ticker")
        feature = aware_datetime(payload["feature_as_of"], field="feature_as_of")
        observed = aware_datetime(payload["observed_at"], field="observed_at")
        retrieved = aware_datetime(payload["retrieved_at"], field="retrieved_at")
        if feature > observed or observed > retrieved:
            raise ValidationError("future-data leakage: require feature_as_of <= observed_at <= retrieved_at")
        data = json.loads(canonical_json(require_plain_dict(payload["data"], field="data")))
        return cls(
            kind=payload["kind"], strategy=payload["strategy"], version=payload["version"],
            symbol=symbol, source=payload["source"], feature_as_of=feature,
            observed_at=observed, retrieved_at=retrieved, data=data, evidence_hash=supplied_hash,
        )

    def validate_at(self, decision_at: datetime, max_age: timedelta) -> None:
        current_unsigned = {
            "kind": self.kind, "strategy": self.strategy, "version": self.version,
            "symbol": self.symbol, "source": self.source,
            "feature_as_of": self.feature_as_of.isoformat(), "observed_at": self.observed_at.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat(), "data": self.data,
        }
        if sha256_json(current_unsigned) != self.evidence_hash:
            raise ValidationError("evidence hash mismatch after construction")
        decision = aware_datetime(decision_at, field="decision_at")
        if self.retrieved_at > decision:
            raise ValidationError("future-data leakage: evidence retrieved after decision")
        age = decision - self.observed_at
        if age < timedelta(0) or age > max_age:
            raise ValidationError("evidence is stale or future-dated")

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "strategy": self.strategy, "version": self.version,
            "symbol": self.symbol, "source": self.source,
            "feature_as_of": self.feature_as_of.isoformat(),
            "observed_at": self.observed_at.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat(),
            "data": json.loads(canonical_json(self.data)), "evidence_hash": self.evidence_hash,
        }
