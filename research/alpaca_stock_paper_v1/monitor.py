"""Pure stock-paper alert evaluation from a read-only broker snapshot."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib

from research.alpaca_stock_paper_v1.alerts import PAPER_REVIEW_URL, Draft, News, Position, drafts
from research.alpaca_stock_paper_v1.read_only import PaperSnapshot


@dataclass(frozen=True)
class PositionCard:
    """Owner-reviewed paper position details; never inferred from a price test."""
    account_id: str
    asset_id: str
    position_id: str  # A new local ID is required for each reopen of LITE.
    quantity: Decimal
    target_price: Decimal
    completed_sessions_held: int
    review_due: bool
    explicitly_approved: bool = False
    opened_at: datetime | None = None
    drawdown_levels: tuple[int, ...] = ()
    review_every_sessions: int = 0


@dataclass(frozen=True)
class Evaluation:
    status: str
    drafts: tuple[Draft, ...]


def _health(kind: str, now: datetime, body: str) -> Draft:
    key = hashlib.sha256(f"health|{kind}|{now.date().isoformat()}".encode()).hexdigest()
    return Draft(key, "[PAPER STOCK] Paper position needs review", body +
                 f"\nReview paper account: {PAPER_REVIEW_URL}\n"
                 "No order was placed by this alert.\n", "urgent")


def evaluate(snapshot: PaperSnapshot, card: PositionCard | None, *, now: datetime,
             news_since: datetime | None = None) -> Evaluation:
    """Fail closed on missing card, exposure mismatch, or pending orders."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("aware_time_required")
    if abs((now - snapshot.observed_at).total_seconds()) > 30:
        return Evaluation("stale_snapshot", (_health("stale_snapshot", now,
            "The Alpaca paper snapshot is stale. Check the account directly."),))
    lite = [p for p in snapshot.positions if p.symbol == "LITE"]
    if snapshot.open_order_ids:
        return Evaluation("open_orders_present", (_health("open_orders", now,
            f"There are {len(snapshot.open_order_ids)} open Alpaca paper orders. "
            "Review order and fill state directly before relying on alerts."),))
    if not lite:
        if card is None:
            return Evaluation("no_paper_position", ())
        return Evaluation("card_without_position", (_health("card_without_position", now,
            "A configured LITE paper card has no matching broker position. Reconcile fills and card."),))
    if card is None or len(lite) != 1:
        return Evaluation("untracked_position", (_health("untracked_position", now,
            "LITE paper exposure exists without one reviewed position card. Check the broker directly."),))
    position = lite[0]
    if (card.explicitly_approved is not True or card.account_id != snapshot.account_id or
        card.asset_id != position.asset_id or
        position.side != "long" or card.quantity != position.quantity or
        not card.position_id or not isinstance(card.target_price, Decimal) or
        not card.target_price.is_finite() or card.target_price <= 0):
        return Evaluation("position_mismatch", (_health("position_mismatch", now,
            "The reviewed LITE card does not match paper account, asset, side, or quantity. "
            "Review any partial fill or manual activity."),))
    if news_since is not None and (news_since.tzinfo is None or news_since.utcoffset() is None):
        raise ValueError("aware_news_cutoff_required")
    articles = tuple(News(item.article_id, item.updated_at.isoformat(), item.headline,
                          item.source, item.published_at, snapshot.observed_at, item.url)
                     for item in snapshot.news
                     if news_since is not None and news_since <= item.updated_at <= snapshot.observed_at
                     and item.published_at <= snapshot.observed_at)
    quote = snapshot.quote
    result = list(drafts(Position(card.position_id, "LITE", position.average_entry,
                             position.quantity, card.target_price, card.completed_sessions_held),
                    now=now, bid=quote.bid if snapshot.market_open and quote else None,
                    quote_at=(quote.quoted_at if quote else now) if snapshot.market_open else None,
                    quote_feed=quote.feed if quote else None,
                    drawdown_levels=card.drawdown_levels,
                    review_every_sessions=card.review_every_sessions,
                    review_due=card.review_due, news=articles))
    if snapshot.news_problem:
        result.append(_health("news_data", now,
            f"LITE news could not be verified ({snapshot.news_problem}). Review news directly."))
    elif news_since is None:
        result.append(_health("news_cutoff", now,
            "No reviewed news first-seen cutoff is configured. News alerting is incomplete."))
    return Evaluation("ready_for_email_drafts", tuple(result))
