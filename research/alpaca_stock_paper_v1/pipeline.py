"""One-shot read and draft creation. Never sends email or an order."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.alpaca_stock_paper_v1.calendar import completed_sessions
from research.alpaca_stock_paper_v1.monitor import Evaluation, PositionCard, _health, evaluate
from research.alpaca_stock_paper_v1.read_only import PaperReader, ReadError

NY = ZoneInfo("America/New_York")


def collect(reader: PaperReader, *, expected_account_id: str, card: PositionCard | None,
            now: datetime, news_since: datetime | None = None) -> Evaluation:
    """Return operational warnings when a paper read fails, without leaking raw errors."""
    if not expected_account_id or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("account_lock_and_aware_time_required")
    try:
        snapshot = reader.snapshot(expected_account_id=expected_account_id,
                                   include_news=card is not None, news_since=news_since)
        decision_at = max(now, snapshot.observed_at)
        review_warning = None
        if card is not None and any(p.symbol == "LITE" for p in snapshot.positions):
            if card.opened_at is None:
                review_warning = "No reviewed paper entry time is configured; holding-session reviews are unavailable."
                card = replace(card, completed_sessions_held=0, review_due=False)
            elif (not isinstance(card.opened_at, datetime) or
                  card.opened_at.tzinfo is None or card.opened_at.utcoffset() is None or
                  card.opened_at > decision_at):
                review_warning = "The reviewed paper entry time is invalid; holding-session reviews are unavailable."
                card = replace(card, completed_sessions_held=0, review_due=False)
            else:
                try:
                    start = card.opened_at.astimezone(NY).date()
                    end = decision_at.astimezone(NY).date()
                    rows = []
                    while start <= end:
                        last = min(start + timedelta(days=366), end)
                        rows.extend(reader.trading_calendar(start, last))
                        start = last + timedelta(days=1)
                    count = completed_sessions(card.opened_at, decision_at, rows)
                    card = replace(card, completed_sessions_held=count,
                                   review_due=(card.review_every_sessions > 0 and count > 0 and
                                               count % card.review_every_sessions == 0))
                except (ReadError, ValueError):
                    review_warning = "The paper market calendar could not be verified; holding-session reviews are unavailable."
                    card = replace(card, completed_sessions_held=0, review_due=False)
        result = evaluate(snapshot, card, now=decision_at, news_since=news_since)
        if review_warning and result.status == "ready_for_email_drafts":
            return Evaluation(result.status, result.drafts +
                (_health("holding_calendar", decision_at, review_warning),))
        return result
    except ReadError as exc:
        return Evaluation("read_blocked", (_health(str(exc), now,
            f"Alpaca paper read is blocked ({exc}). Check paper account, data and position directly."),))
