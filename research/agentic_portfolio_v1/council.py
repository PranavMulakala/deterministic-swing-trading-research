"""Model-free analyst/critic proposal protocol inspired by role separation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from .common import ValidationError, aware_datetime, decimal_value, require_plain_dict, sha256_json
from .evidence import EvidencePacket


PROPOSAL_FIELDS = {
    "schema_version", "role", "producer", "action", "symbol", "right", "expiration",
    "strike", "evidence_hash", "grounded_fields", "observed_at", "proposal_hash",
}


@dataclass(frozen=True)
class CouncilResult:
    accepted: bool
    action: str
    reason: str


def build_proposal(
    *, role: str, producer: str, action: str, symbol: str, right: str,
    expiration: str, strike: str, evidence: EvidencePacket,
    grounded_fields: list[str], observed_at: datetime,
) -> dict[str, Any]:
    unsigned = {
        "schema_version": "1.0", "role": role, "producer": producer, "action": action,
        "symbol": symbol, "right": right, "expiration": expiration, "strike": strike,
        "evidence_hash": evidence.evidence_hash, "grounded_fields": grounded_fields,
        "observed_at": aware_datetime(observed_at).isoformat(),
    }
    return {**unsigned, "proposal_hash": sha256_json(unsigned)}


def no_op_proposal(evidence: EvidencePacket, observed_at: datetime) -> dict[str, Any]:
    return build_proposal(
        role="analyst", producer="deterministic-noop", action="ABSTAIN", symbol=evidence.symbol,
        right="NONE", expiration="NONE", strike="0", evidence=evidence,
        grounded_fields=[], observed_at=observed_at,
    )


def _validate_proposal(raw: Any, evidence: EvidencePacket, decision_at: datetime) -> dict[str, Any]:
    proposal = require_plain_dict(raw, field="proposal")
    if set(proposal) != PROPOSAL_FIELDS:
        raise ValidationError("proposal fields do not match protocol")
    unsigned = {key: proposal[key] for key in PROPOSAL_FIELDS if key != "proposal_hash"}
    if proposal["proposal_hash"] != sha256_json(unsigned):
        raise ValidationError("proposal hash mismatch")
    if proposal["schema_version"] != "1.0" or proposal["evidence_hash"] != evidence.evidence_hash:
        raise ValidationError("proposal is not bound to this evidence")
    for field in ("role", "producer", "action", "symbol", "right", "expiration", "strike"):
        if not isinstance(proposal[field], str) or not proposal[field].strip():
            raise ValidationError(f"proposal {field} must be a non-empty string")
    if proposal["symbol"] != evidence.symbol or proposal["role"] not in {"analyst", "critic"}:
        raise ValidationError("proposal identity conflict")
    observed = aware_datetime(proposal["observed_at"], field="proposal.observed_at")
    decision = aware_datetime(decision_at, field="decision_at")
    if observed > decision or decision - observed > timedelta(minutes=5):
        raise ValidationError("proposal is stale or future-dated")
    grounded = proposal["grounded_fields"]
    if type(grounded) is not list or not all(isinstance(v, str) for v in grounded):
        raise ValidationError("grounded_fields must be a string list")
    if any(field not in evidence.data for field in grounded):
        raise ValidationError("proposal cites an unavailable evidence field")
    if proposal["action"] != "ABSTAIN" and not grounded:
        raise ValidationError("non-abstain proposal is ungrounded")
    return proposal


def _contract_identity(raw: dict[str, Any], *, source: str) -> tuple[str, str, date, Any]:
    try:
        symbol = raw["symbol"] if source == "proposal" else raw.get("underlying", raw["symbol"])
        right = raw["right"]
        expiration = raw["expiration"]
        strike = raw["strike"]
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValidationError(f"{source} contract identity is malformed") from exc
    if not isinstance(symbol, str) or not symbol.strip() or not isinstance(right, str):
        raise ValidationError(f"{source} contract identity is malformed")
    if not isinstance(expiration, str):
        raise ValidationError(f"{source} expiration is malformed")
    try:
        expiry = date.fromisoformat(expiration)
    except ValueError as exc:
        raise ValidationError(f"{source} expiration is malformed") from exc
    return symbol, right, expiry, decimal_value(strike, field=f"{source}.strike", positive=True)


def validate_council(analyst_raw: Any, critic_raw: Any, evidence: EvidencePacket, decision_at: datetime) -> CouncilResult:
    try:
        analyst = _validate_proposal(analyst_raw, evidence, decision_at)
        critic = _validate_proposal(critic_raw, evidence, decision_at)
    except (ValidationError, KeyError, TypeError, ValueError, ArithmeticError) as exc:
        return CouncilResult(False, "ABSTAIN", str(exc))
    if analyst["role"] != "analyst" or critic["role"] != "critic":
        return CouncilResult(False, "ABSTAIN", "required analyst and critic roles absent")
    if analyst["action"] not in {"CALL", "PUT"}:
        return CouncilResult(False, "ABSTAIN", "analyst abstained or action invalid")
    if critic["action"] != "AGREE":
        return CouncilResult(False, "ABSTAIN", "critic disagreed or abstained")
    if analyst["producer"] == critic["producer"]:
        return CouncilResult(False, "ABSTAIN", "analyst and critic producers must be distinct")
    identity_fields = ("symbol", "right", "expiration", "strike", "evidence_hash")
    if any(analyst[field] != critic[field] for field in identity_fields):
        return CouncilResult(False, "ABSTAIN", "analyst and critic conflict")
    if analyst["right"] != analyst["action"]:
        return CouncilResult(False, "ABSTAIN", "action and option right conflict")
    try:
        packet_identity = _contract_identity({"symbol": evidence.symbol, **evidence.data}, source="evidence")
        analyst_identity = _contract_identity(analyst, source="proposal")
        critic_identity = _contract_identity(critic, source="proposal")
    except (ValidationError, KeyError, TypeError, ValueError, ArithmeticError) as exc:
        return CouncilResult(False, "ABSTAIN", str(exc))
    if analyst_identity != packet_identity or critic_identity != packet_identity:
        return CouncilResult(False, "ABSTAIN", "council contract does not match the hash-bound evidence contract")
    return CouncilResult(True, analyst["action"], "analyst and critic agree; deterministic validator passed")
