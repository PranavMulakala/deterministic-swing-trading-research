"""Stock paper alert outbox; transport must be injected, no built-in network."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from research.alpaca_stock_paper_v1.alerts import Draft


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("""CREATE TABLE IF NOT EXISTS stock_alert_outbox (
        key TEXT PRIMARY KEY, subject TEXT NOT NULL, body TEXT NOT NULL,
        priority TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        last_attempt_at TEXT, provider_id TEXT, error TEXT)""")
    return db


def _utc(value):
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("naive_time")
    return value.astimezone(timezone.utc).isoformat()


def enqueue(db, draft: Draft, now: datetime, expires_at: datetime):
    if not isinstance(draft, Draft) or not draft.key or not draft.subject.startswith("[PAPER STOCK] "):
        raise ValueError("invalid_stock_draft")
    created, expiry = _utc(now), _utc(expires_at)
    if not created < expiry <= _utc(now + timedelta(hours=24)):
        raise ValueError("invalid_alert_expiry")
    with db:
        db.execute("""INSERT OR IGNORE INTO stock_alert_outbox
            (key,subject,body,priority,state,created_at,expires_at)
            VALUES (?,?,?,?,?,?,?)""",
            (draft.key,draft.subject,draft.body,draft.priority,"pending",
             created,expiry))


def expire(db, now: datetime):
    timestamp = _utc(now)
    with db:
        return db.execute("""UPDATE stock_alert_outbox SET state='expired'
            WHERE state IN ('pending','sending') AND expires_at<=?""",
            (timestamp,)).rowcount


def send_one(db, key: str, now: datetime, transport):
    """Call an injected test/approved transport with a stable idempotency key.

    `transport(subject, body, idempotency_key)` returns a nonempty provider ID.
    There is deliberately no default network or credential loader.
    """
    if not callable(transport):
        raise ValueError("invalid_transport_or_time")
    timestamp = _utc(now)
    expire(db, now)
    with db:
        changed = db.execute("""UPDATE stock_alert_outbox
            SET state='sending',attempts=attempts+1,last_attempt_at=?
            WHERE key=? AND state='pending' AND expires_at>? AND attempts<12""",
            (timestamp,key,timestamp)).rowcount
    if not changed:
        return False
    subject, body = db.execute("SELECT subject,body FROM stock_alert_outbox WHERE key=?",(key,)).fetchone()
    try:
        provider_id = transport(subject, body, "paper-stock-" + key)
        if not isinstance(provider_id, str) or not provider_id:
            raise ValueError("missing_provider_receipt")
    except Exception as exc:
        with db:
            db.execute("""UPDATE stock_alert_outbox SET state='pending',error=?
                WHERE key=? AND state='sending'""", (type(exc).__name__,key))
        return False
    with db:
        db.execute("""UPDATE stock_alert_outbox SET state='accepted',provider_id=?,error=NULL
            WHERE key=? AND state='sending'""",(provider_id,key))
    return True


def recover_ambiguous(db, now: datetime):
    """Retry only while the same provider idempotency key is under 24 hours old."""
    timestamp = _utc(now)
    expire(db,now)
    cutoff = _utc(now - timedelta(minutes=2))
    with db:
        return db.execute("""UPDATE stock_alert_outbox SET state='pending'
            WHERE state='sending' AND last_attempt_at<? AND expires_at>? AND attempts<12""",
            (cutoff,timestamp)).rowcount


def dispatch_pending(db, now: datetime, transport, *, limit: int = 25):
    """Send queued, unexpired drafts even when the latest read has no new event."""
    if not callable(transport) or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("invalid_dispatch")
    timestamp = _utc(now)
    recover_ambiguous(db, now)
    expire(db, now)
    keys = [row[0] for row in db.execute("""SELECT key FROM stock_alert_outbox
        WHERE state='pending' AND expires_at>? AND attempts<12
        ORDER BY CASE priority WHEN 'urgent' THEN 0 ELSE 1 END, created_at, key
        LIMIT ?""", (timestamp, limit)).fetchall()]
    return sum(bool(send_one(db, key, now, transport)) for key in keys)


def delivery_backlog(db, now: datetime) -> tuple[int, int]:
    """Return pending and expired-unsent counts for external health monitoring."""
    timestamp = _utc(now)
    expire(db, now)
    pending = db.execute("""SELECT COUNT(*) FROM stock_alert_outbox
        WHERE state IN ('pending','sending') AND expires_at>?""", (timestamp,)).fetchone()[0]
    expired = db.execute("""SELECT COUNT(*) FROM stock_alert_outbox
        WHERE state='expired'""").fetchone()[0]
    return pending, expired
