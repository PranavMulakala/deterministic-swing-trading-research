"""Paper-only controller that emits decision cards and immutable receipts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from .common import ValidationError, aware_datetime, sha256_json
from .decisions import PaperDecision
from .evidence import EvidencePacket


@dataclass(frozen=True)
class DecisionCard:
    banner: str
    strategy: str
    version: str
    virtual_account: str
    symbol: str
    decision: str
    reasons: tuple[str, ...]
    target: str
    invalidation: str
    review_conditions: str
    modeled_downside: str
    source: str
    source_observed_at: str
    source_retrieved_at: str
    decided_at: str
    evidence_hash: str
    validation_hash: str

    def human_text(self) -> str:
        return (
            f"PAPER ONLY / NO ORDER\n{self.symbol} — {self.decision}\n"
            f"Why: {'; '.join(self.reasons)}\nTarget: {self.target}\n"
            f"Invalidation: {self.invalidation}\nReview: {self.review_conditions}\n"
            f"Modeled downside: {self.modeled_downside}\n"
            f"Evidence: {self.source} observed {self.source_observed_at} retrieved {self.source_retrieved_at}"
        )


def make_card(
    decision: PaperDecision, evidence: EvidencePacket, decided_at: datetime,
    *, expected_virtual_account: str | None = None,
) -> DecisionCard:
    if not isinstance(decision, PaperDecision) or not isinstance(evidence, EvidencePacket):
        raise ValidationError("controller requires typed decision and evidence")
    if decision.paper_only is not True or decision.no_order is not True:
        raise ValidationError("controller accepts only PAPER_ONLY/NO_ORDER decisions")
    timestamp = aware_datetime(decided_at, field="decided_at")
    max_age = timedelta(seconds=30) if evidence.strategy == "long_option_shadow_v2" else timedelta(minutes=5)
    evidence.validate_at(timestamp, max_age)
    if decision.evidence_hash != evidence.evidence_hash:
        raise ValidationError("decision/evidence hash mismatch")
    if decision.strategy != evidence.strategy or decision.version != evidence.version:
        raise ValidationError("decision strategy/version is not bound to evidence")
    expected_symbols = {evidence.symbol}
    if evidence.strategy == "long_option_shadow_v2" and evidence.kind == "option_entry":
        try:
            contract_symbol = (
                f"{evidence.symbol}:{evidence.data['expiration']}:{evidence.data['right']}:{evidence.data['strike']}"
            )
        except (KeyError, TypeError) as exc:
            raise ValidationError("option decision contract cannot be derived from evidence") from exc
        expected_symbols = {contract_symbol} if decision.action == "PAPER_ENTRY_INTENT" else {evidence.symbol, contract_symbol}
    elif evidence.strategy == "long_option_shadow_v2" and evidence.kind == "option_management":
        expected_symbols = {evidence.data.get("contract")} if type(evidence.data) is dict else set()
    if decision.symbol not in expected_symbols:
        raise ValidationError("decision symbol is not bound to evidence")
    if not isinstance(expected_virtual_account, str) or not expected_virtual_account.strip():
        raise ValidationError("expected virtual account binding is required")
    if decision.virtual_account != expected_virtual_account:
        raise ValidationError("decision virtual account does not match controller binding")
    if decision.action not in {"ABSTAIN", "PAPER_ENTRY_INTENT", "PAPER_EXIT_INTENT", "HOLD", "REVIEW_REQUIRED"}:
        raise ValidationError("unsupported paper decision action")
    if type(decision.reasons) is not tuple or not decision.reasons or not all(
        isinstance(reason, str) and reason.strip() for reason in decision.reasons
    ):
        raise ValidationError("decision reasons must be non-empty strings")
    if type(decision.details) is not dict:
        raise ValidationError("decision details must be an object")
    details = decision.details
    fields = dict(
        banner="PAPER_ONLY/NO_ORDER", strategy=decision.strategy, version=decision.version,
        virtual_account=decision.virtual_account, symbol=decision.symbol, decision=decision.action,
        reasons=decision.reasons, target=str(details.get("target_price", details.get("target_premium", "not applicable"))),
        invalidation=str(details.get("invalidation", "frozen management rules")),
        review_conditions=str(details.get("review_conditions", "strategy-specific frozen schedule")),
        modeled_downside=str(details.get("contractual_loss", details.get("modeled_entry_debit", "no new exposure"))),
        source=evidence.source, source_observed_at=evidence.observed_at.isoformat(),
        source_retrieved_at=evidence.retrieved_at.isoformat(), decided_at=timestamp.isoformat(),
        evidence_hash=evidence.evidence_hash,
    )
    return DecisionCard(**fields, validation_hash=sha256_json(fields))


def make_receipt(card: DecisionCard) -> dict[str, Any]:
    if not isinstance(card, DecisionCard) or card.banner != "PAPER_ONLY/NO_ORDER":
        raise ValidationError("receipt requires a validated paper-only decision card")
    unsigned_card = asdict(card)
    validation_hash = unsigned_card.pop("validation_hash")
    if validation_hash != sha256_json(unsigned_card):
        raise ValidationError("decision card validation hash mismatch")
    observed = aware_datetime(card.source_observed_at, field="source_observed_at")
    retrieved = aware_datetime(card.source_retrieved_at, field="source_retrieved_at")
    decided = aware_datetime(card.decided_at, field="decided_at")
    if observed > retrieved or retrieved > decided:
        raise ValidationError("decision card timestamps are not causal")
    if not all(isinstance(value, str) and value.strip() for value in (
        card.strategy, card.version, card.virtual_account, card.symbol, card.decision,
        card.source, card.evidence_hash,
    )):
        raise ValidationError("decision card identity is malformed")
    payload = {
        "receipt_type": "PAPER_DECISION", "paper_only": True, "no_order": True,
        **asdict(card), "human_text": card.human_text(),
    }
    return {**payload, "receipt_hash": sha256_json(payload)}
