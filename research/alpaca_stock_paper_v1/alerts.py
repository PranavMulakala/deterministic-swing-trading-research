"""Pure paper-position alert drafts. No email delivery, network, or orders."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import re
from urllib.parse import urlsplit

PAPER_REVIEW_URL = "https://app.alpaca.markets/paper/dashboard/overview"


@dataclass(frozen=True)
class Position:
    position_id: str
    symbol: str
    entry_price: Decimal
    quantity: Decimal
    target_price: Decimal
    completed_sessions_held: int


@dataclass(frozen=True)
class News:
    article_id: str
    version: str
    headline: str
    source: str
    published_at: datetime
    received_at: datetime
    url: str


@dataclass(frozen=True)
class Draft:
    key: str
    subject: str
    body: str
    priority: str


def _aware(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _draft(position_id, kind, detail, subject, body, priority):
    key = hashlib.sha256(f"{position_id}|{kind}|{detail}".encode()).hexdigest()
    return Draft(key, "[PAPER STOCK] " + subject,
                 f"Paper position ID: {position_id}\n" + body +
                 f"\nReview paper account: {PAPER_REVIEW_URL}\n"
                 "No order was placed by this alert.\n", priority)


def drafts(position: Position, *, now: datetime, bid: Decimal | None = None,
           quote_at: datetime | None = None, quote_feed: str | None = None,
           drawdown_levels: tuple[int, ...] = (), review_every_sessions: int = 0,
           review_due: bool = False, news: tuple[News, ...] = (),
           known_keys: frozenset[str] = frozenset()) -> tuple[Draft, ...]:
    """Produce deduplicated review prompts; never makes a trade decision."""
    if (not _aware(now) or not isinstance(position.position_id, str) or
        not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", position.position_id) or
        position.symbol != "LITE"):
        raise ValueError("invalid_position_or_time")
    if any(not isinstance(v, Decimal) or not v.is_finite() or v <= 0
           for v in (position.entry_price, position.quantity, position.target_price)):
        raise ValueError("invalid_position_amount")
    if position.completed_sessions_held < 0 or review_every_sessions < 0:
        raise ValueError("invalid_review_interval")
    if any(type(v) is not int or not 0 < v <= 100 for v in drawdown_levels):
        raise ValueError("invalid_drawdown_level")
    if len(set(drawdown_levels)) != len(drawdown_levels):
        raise ValueError("duplicate_drawdown_level")
    out = []
    if bid is not None or quote_at is not None:
        fresh = (isinstance(bid, Decimal) and bid.is_finite() and bid > 0 and
                 _aware(quote_at) and timedelta(0) <= now - quote_at <= timedelta(seconds=5) and
                 quote_feed == "iex")
        if not fresh:
            out.append(_draft(position.position_id, "quote_unverified", now.date().isoformat(),
                              "Price unavailable for review",
                              f"LITE quote missing, stale, or unexpected at {now.isoformat()}. "
                              "Check the position and data feed. Paper only.", "urgent"))
        else:
            prefix = (f"LITE paper position; bid {bid}; IEX quote at {quote_at.isoformat()}; "
                      f"entry {position.entry_price}; quantity {position.quantity}. ")
            if bid >= position.target_price:
                out.append(_draft(position.position_id, "target", str(position.target_price),
                                  "Profit target observed — review now",
                                  prefix + f"Predeclared target {position.target_price} was observed. "
                                  "This is a bid observation, not an executable guarantee or sale.", "urgent"))
            drawdown = (Decimal(1) - bid / position.entry_price) * 100
            for level in sorted(drawdown_levels):
                if drawdown >= level:
                    out.append(_draft(position.position_id, "drawdown", str(level),
                                      f"{level}% drawdown level observed — review thesis",
                                      prefix + f"Observed price decline from entry is {drawdown:.2f}%. "
                                      "Review news and thesis; no stop order exists.", "urgent"))
    if review_due and review_every_sessions and position.completed_sessions_held and (
        position.completed_sessions_held % review_every_sessions == 0
    ):
        out.append(_draft(position.position_id, "review", str(position.completed_sessions_held),
                          "Holding review due",
                          f"LITE paper position has been held for {position.completed_sessions_held} "
                          "completed sessions. Review thesis, target, news, and tied-up capital. "
                          "There is no automatic time exit.", "normal"))
    for article in news:
        if not article.article_id or not article.version or not _aware(article.published_at) or not _aware(article.received_at):
            raise ValueError("invalid_news")
        if article.received_at > now or article.published_at > article.received_at:
            raise ValueError("news_not_available_at_decision")
        headline = " ".join(article.headline.split())[:160]
        source = " ".join(article.source.split())[:80]
        raw_url = article.url.strip()
        parsed = urlsplit(raw_url)
        url = (raw_url if parsed.scheme == "https" and parsed.hostname and
               not any(char.isspace() or ord(char) < 32 for char in raw_url)
               else "No verified HTTPS link")
        out.append(_draft(position.position_id, "news", f"{article.article_id}|{article.version}",
                          "New LITE news — review, sentiment unclassified",
                          f"Source: {source}\nPublished: {article.published_at.isoformat()}\n"
                          f"Received: {article.received_at.isoformat()}\nHeadline: {headline}\n"
                          f"Link: {url}\nTreat as unclassified until you review it.", "normal"))
    unique = {item.key: item for item in out if item.key not in known_keys}
    return tuple(unique.values())
