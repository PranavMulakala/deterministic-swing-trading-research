from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .paper_models import ApprovalPermit, OrderProposal, canonical_json


GENESIS_HASH = "0" * 64


class JournalError(RuntimeError):
    pass


class PaperJournal:
    """Durable append-only operational journal with an integrity hash chain."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        self._initialize()
        os.chmod(self.path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    occurred_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    proposal_id TEXT,
                    payload_json TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_proposal ON events(proposal_id, seq)"
            )

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def mutation_lock(self) -> Iterator[None]:
        """Serialize the complete broker-mutation critical section across processes."""
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @staticmethod
    def _event_hash(
        *, event_id: str, occurred_at: str, event_type: str,
        proposal_id: str | None, payload_json: str, prev_hash: str,
    ) -> str:
        envelope = canonical_json(
            {
                "event_id": event_id,
                "occurred_at": occurred_at,
                "event_type": event_type,
                "proposal_id": proposal_id,
                "payload_json": payload_json,
                "prev_hash": prev_hash,
            }
        )
        return hashlib.sha256(envelope.encode("utf-8")).hexdigest()

    def _append_in(
        self,
        connection: sqlite3.Connection,
        event_type: str,
        payload: dict[str, Any],
        *,
        proposal_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> dict[str, Any]:
        now = occurred_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise JournalError("journal timestamps must be timezone-aware")
        last = connection.execute(
            "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        prev_hash = str(last["event_hash"]) if last else GENESIS_HASH
        event_id = str(uuid.uuid4())
        timestamp = now.isoformat()
        payload_json = canonical_json(payload)
        digest = self._event_hash(
            event_id=event_id,
            occurred_at=timestamp,
            event_type=event_type,
            proposal_id=proposal_id,
            payload_json=payload_json,
            prev_hash=prev_hash,
        )
        cursor = connection.execute(
            """
            INSERT INTO events(
                event_id, occurred_at, event_type, proposal_id,
                payload_json, prev_hash, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, timestamp, event_type, proposal_id, payload_json, prev_hash, digest),
        )
        return {
            "seq": cursor.lastrowid,
            "event_id": event_id,
            "occurred_at": timestamp,
            "event_type": event_type,
            "proposal_id": proposal_id,
            "payload": json.loads(payload_json),
            "prev_hash": prev_hash,
            "event_hash": digest,
        }

    def append(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        proposal_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> dict[str, Any]:
        with self._transaction() as connection:
            return self._append_in(
                connection, event_type, payload,
                proposal_id=proposal_id, occurred_at=occurred_at,
            )

    def events(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM events ORDER BY seq").fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "seq": int(row["seq"]),
            "event_id": str(row["event_id"]),
            "occurred_at": str(row["occurred_at"]),
            "event_type": str(row["event_type"]),
            "proposal_id": row["proposal_id"],
            "payload": json.loads(str(row["payload_json"])),
            "prev_hash": str(row["prev_hash"]),
            "event_hash": str(row["event_hash"]),
        }

    def verify_integrity(self) -> None:
        previous = GENESIS_HASH
        expected_seq = 1
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM events ORDER BY seq").fetchall()
        for row in rows:
            if int(row["seq"]) != expected_seq:
                raise JournalError("journal sequence has a gap")
            if str(row["prev_hash"]) != previous:
                raise JournalError(f"journal hash chain broken at seq {expected_seq}")
            expected = self._event_hash(
                event_id=str(row["event_id"]),
                occurred_at=str(row["occurred_at"]),
                event_type=str(row["event_type"]),
                proposal_id=row["proposal_id"],
                payload_json=str(row["payload_json"]),
                prev_hash=str(row["prev_hash"]),
            )
            if str(row["event_hash"]) != expected:
                raise JournalError(f"journal event digest mismatch at seq {expected_seq}")
            previous = expected
            expected_seq += 1

    def record_proposal(self, proposal: OrderProposal) -> None:
        with self._transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM events WHERE proposal_id = ? LIMIT 1",
                (proposal.proposal_id,),
            ).fetchone()
            if exists:
                raise JournalError(f"proposal id already exists: {proposal.proposal_id}")
            self._append_in(
                connection,
                "proposal_created",
                {"proposal": proposal.to_payload(), "content_hash": proposal.content_hash},
                proposal_id=proposal.proposal_id,
                occurred_at=proposal.created_at,
            )

    def get_proposal(self, proposal_id: str) -> OrderProposal:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM events
                WHERE proposal_id = ? AND event_type = 'proposal_created'
                ORDER BY seq DESC LIMIT 1
                """,
                (proposal_id,),
            ).fetchone()
        if row is None:
            raise JournalError(f"proposal not found: {proposal_id}")
        payload = json.loads(str(row["payload_json"]))
        proposal = OrderProposal.from_payload(payload["proposal"])
        if proposal.content_hash != payload["content_hash"]:
            raise JournalError("proposal content hash mismatch")
        return proposal

    def record_review(
        self,
        proposal: OrderProposal,
        *,
        quote_timestamp: datetime,
        bid: str,
        ask: str,
        reviewed_at: datetime,
    ) -> None:
        self.append(
            "proposal_reviewed",
            {
                "content_hash": proposal.content_hash,
                "quote_timestamp": quote_timestamp.isoformat(),
                "bid": bid,
                "ask": ask,
                "full_order_restatement": True,
            },
            proposal_id=proposal.proposal_id,
            occurred_at=reviewed_at,
        )

    def proposal_event_types(self, proposal_id: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_type FROM events WHERE proposal_id = ? ORDER BY seq",
                (proposal_id,),
            ).fetchall()
        return [str(row["event_type"]) for row in rows]

    def approve_and_consume(
        self,
        proposal: OrderProposal,
        confirmation_code: str,
        *,
        session_id: str,
        now: datetime,
    ) -> ApprovalPermit:
        if confirmation_code != proposal.confirmation_code:
            raise JournalError("confirmation code does not match the exact proposal")
        if not session_id.strip():
            raise JournalError("approval requires a non-empty current session id")
        if now.tzinfo is None:
            raise JournalError("approval timestamp must be timezone-aware")
        if now < proposal.created_at:
            raise JournalError("approval timestamp precedes proposal creation")
        if now > proposal.expires_at:
            raise JournalError("proposal approval window expired")
        with self._transaction() as connection:
            rows = connection.execute(
                "SELECT event_type FROM events WHERE proposal_id = ? ORDER BY seq",
                (proposal.proposal_id,),
            ).fetchall()
            event_types = [str(row["event_type"]) for row in rows]
            if event_types.count("proposal_created") != 1:
                raise JournalError("proposal journal record is missing or duplicated")
            if "proposal_reviewed" not in event_types:
                raise JournalError("proposal has not received a fresh full-order review")
            if "approval_consumed" in event_types or "order_submitted" in event_types:
                raise JournalError("this proposal approval has already been used")
            approval = self._append_in(
                connection,
                "owner_approved",
                {
                    "content_hash": proposal.content_hash,
                    "session_id": session_id,
                    "one_order_only": True,
                },
                proposal_id=proposal.proposal_id,
                occurred_at=now,
            )
            self._append_in(
                connection,
                "approval_consumed",
                {"content_hash": proposal.content_hash},
                proposal_id=proposal.proposal_id,
                occurred_at=now,
            )
            return ApprovalPermit(
                proposal_id=proposal.proposal_id,
                content_hash=proposal.content_hash,
                approval_event_id=str(approval["event_id"]),
                session_id=session_id,
            )

    def claim_permit(
        self,
        proposal: OrderProposal,
        permit: ApprovalPermit,
        stage: str,
    ) -> bool:
        if stage not in {"cancel_protective_stop", "submit_order"}:
            return False
        with self._transaction() as connection:
            approval = connection.execute(
                """
                SELECT payload_json, proposal_id FROM events
                WHERE event_id = ? AND event_type = 'owner_approved'
                """,
                (permit.approval_event_id,),
            ).fetchone()
            if approval is None or str(approval["proposal_id"]) != proposal.proposal_id:
                return False
            payload = json.loads(str(approval["payload_json"]))
            if (
                permit.proposal_id != proposal.proposal_id
                or permit.content_hash != proposal.content_hash
                or payload.get("content_hash") != proposal.content_hash
                or payload.get("session_id") != permit.session_id
            ):
                return False
            consumed = connection.execute(
                """
                SELECT 1 FROM events
                WHERE proposal_id = ? AND event_type = 'approval_consumed'
                LIMIT 1
                """,
                (proposal.proposal_id,),
            ).fetchone()
            claimed_rows = connection.execute(
                """
                SELECT payload_json FROM events
                WHERE proposal_id = ? AND event_type = 'broker_mutation_claimed'
                """,
                (proposal.proposal_id,),
            ).fetchall()
            already_claimed = any(
                json.loads(str(row["payload_json"])).get("stage") == stage
                for row in claimed_rows
            )
            if consumed is None or already_claimed:
                return False
            self._append_in(
                connection,
                "broker_mutation_claimed",
                {
                    "content_hash": proposal.content_hash,
                    "approval_event_id": permit.approval_event_id,
                    "stage": stage,
                },
                proposal_id=proposal.proposal_id,
            )
            return True

    def account_binding(self) -> dict[str, Any] | None:
        return self.latest_payload("account_bound")

    def kill_switch_latched(self) -> bool:
        events = [
            event for event in self.events()
            if event["event_type"] in {"kill_switch_latched", "kill_switch_cleared"}
        ]
        return bool(events and events[-1]["event_type"] == "kill_switch_latched")

    def latest_payload(self, event_type: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM events WHERE event_type = ? ORDER BY seq DESC LIMIT 1",
                (event_type,),
            ).fetchone()
        return json.loads(str(row["payload_json"])) if row else None
