"""Explicitly invoked one-shot stock-paper alert workflow; no schedule or defaults."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from research.alpaca_stock_paper_v1.monitor import PositionCard
from research.alpaca_stock_paper_v1.outbox import delivery_backlog, dispatch_pending, enqueue
from research.alpaca_stock_paper_v1.pipeline import collect
from research.alpaca_stock_paper_v1.read_only import PaperReader


@dataclass(frozen=True)
class RunResult:
    status: str
    drafted: int
    accepted_by_provider: int
    pending_delivery: int
    expired_unsent: int


def run_once(reader: PaperReader, *, expected_account_id: str, card: PositionCard | None,
             now: datetime, outbox_db, news_since: datetime | None = None,
             delivery=None) -> RunResult:
    """Read, enqueue and optionally deliver with an explicitly injected transport.

    Provider acceptance is not inbox delivery or a trade. There is no timer,
    credential loader, or broker mutation. Omit delivery for queue-only review.
    """
    evaluation = collect(reader, expected_account_id=expected_account_id,
                         card=card, now=now, news_since=news_since)
    for draft in evaluation.drafts:
        expiry = now + (timedelta(minutes=30) if draft.priority == "urgent"
                        else timedelta(hours=24))
        enqueue(outbox_db, draft, now, expiry)
    accepted = dispatch_pending(outbox_db, now, delivery) if delivery is not None else 0
    pending, expired = delivery_backlog(outbox_db, now)
    return RunResult(evaluation.status, len(evaluation.drafts), accepted, pending, expired)
