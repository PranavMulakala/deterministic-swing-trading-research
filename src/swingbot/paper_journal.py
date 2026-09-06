from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

from .paper_models import ApprovalPermit, OrderProposal, canonical_json, parse_timestamp


GENESIS_HASH = "0" * 64
_RESERVED_AUTH_EVENTS = {
    "proposal_created",
    "proposal_reviewed",
    "owner_approved",
    "approval_consumed",
    "broker_mutation_claimed",
    "protective_stop_canceled_for_approved_exit",
}


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
            # Authorization capabilities live outside the generic event append
            # API. This prevents a fabricated event name from becoming a valid
            # broker-mutation permit while retaining the hash-chained audit log.
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_permits (
                    approval_event_id TEXT PRIMARY KEY,
                    review_event_id TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    FOREIGN KEY (approval_event_id) REFERENCES events(event_id),
                    FOREIGN KEY (review_event_id) REFERENCES events(event_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS permit_claims (
                    approval_event_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    PRIMARY KEY (approval_event_id, stage),
                    FOREIGN KEY (approval_event_id)
                        REFERENCES approval_permits(approval_event_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS permit_verifications (
                    approval_event_id TEXT NOT NULL,
                    verification_type TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    verified_at TEXT NOT NULL,
                    PRIMARY KEY (approval_event_id, verification_type),
                    FOREIGN KEY (approval_event_id)
                        REFERENCES approval_permits(approval_event_id)
                )
                """
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
        if event_type in _RESERVED_AUTH_EVENTS:
            raise JournalError(
                f"{event_type} may be written only by its validated journal operation"
            )
        self.verify_integrity()
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
        with self._connect() as connection:
            self._verify_authorization_state(connection)

    def record_proposal(self, proposal: OrderProposal) -> None:
        self.verify_integrity()
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
    ) -> dict[str, Any]:
        self.verify_integrity()
        stored = self.get_proposal(proposal.proposal_id)
        if stored.content_hash != proposal.content_hash:
            raise JournalError("review does not match the stored exact proposal")
        payload = {
            "content_hash": proposal.content_hash,
            "quote_timestamp": quote_timestamp.isoformat(),
            "bid": bid,
            "ask": ask,
            "full_order_restatement": True,
        }
        self._validate_review(proposal, payload, reviewed_at=reviewed_at)
        with self._transaction() as connection:
            return self._append_in(
                connection,
                "proposal_reviewed",
                payload,
                proposal_id=proposal.proposal_id,
                occurred_at=reviewed_at,
            )

    def latest_review(self, proposal: OrderProposal) -> dict[str, Any]:
        stored = self.get_proposal(proposal.proposal_id)
        if stored.content_hash != proposal.content_hash:
            raise JournalError("review lookup does not match the stored exact proposal")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT event_id, occurred_at, payload_json FROM events
                WHERE proposal_id = ? AND event_type = 'proposal_reviewed'
                ORDER BY seq DESC LIMIT 1
                """,
                (proposal.proposal_id,),
            ).fetchone()
        if row is None:
            raise JournalError("proposal has not received a fresh full-order review")
        payload = json.loads(str(row["payload_json"]))
        self._validate_review(
            proposal,
            payload,
            reviewed_at=parse_timestamp(str(row["occurred_at"])),
        )
        return {
            "event_id": str(row["event_id"]),
            "occurred_at": str(row["occurred_at"]),
            **payload,
        }

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
        review_event_id: str,
        session_id: str,
        now: datetime,
    ) -> ApprovalPermit:
        self.verify_integrity()
        if not session_id.strip():
            raise JournalError("approval requires a non-empty current session id")
        if not review_event_id:
            raise JournalError("approval requires the exact fresh review event")
        if now.tzinfo is None:
            raise JournalError("approval timestamp must be timezone-aware")
        if now < proposal.created_at:
            raise JournalError("approval timestamp precedes proposal creation")
        if now > proposal.expires_at:
            raise JournalError("proposal approval window expired")
        with self._transaction() as connection:
            rows = connection.execute(
                """
                SELECT seq, event_id, occurred_at, event_type, payload_json
                FROM events WHERE proposal_id = ? ORDER BY seq
                """,
                (proposal.proposal_id,),
            ).fetchall()
            event_types = [str(row["event_type"]) for row in rows]
            if event_types.count("proposal_created") != 1:
                raise JournalError("proposal journal record is missing or duplicated")
            created_row = next(
                row for row in rows if str(row["event_type"]) == "proposal_created"
            )
            created_payload = json.loads(str(created_row["payload_json"]))
            stored = OrderProposal.from_payload(created_payload["proposal"])
            if (
                stored.content_hash != created_payload.get("content_hash")
                or stored.content_hash != proposal.content_hash
            ):
                raise JournalError("approval does not match the stored exact proposal")
            reviews = [
                row for row in rows if str(row["event_type"]) == "proposal_reviewed"
            ]
            if not reviews:
                raise JournalError("proposal has not received a fresh full-order review")
            review = reviews[-1]
            if str(review["event_id"]) != review_event_id:
                raise JournalError("a newer or different full-order review must be approved")
            review_payload = json.loads(str(review["payload_json"]))
            self._validate_review(
                proposal,
                review_payload,
                reviewed_at=parse_timestamp(str(review["occurred_at"])),
                approval_at=now,
            )
            review_evidence = {
                "event_id": str(review["event_id"]),
                "occurred_at": str(review["occurred_at"]),
                **review_payload,
            }
            if confirmation_code != self.confirmation_code_for_review(
                proposal, review_evidence
            ):
                raise JournalError(
                    "confirmation code does not match the exact latest full-order review"
                )
            if "approval_consumed" in event_types or "order_submitted" in event_types:
                raise JournalError("this proposal approval has already been used")
            approval = self._append_in(
                connection,
                "owner_approved",
                {
                    "content_hash": proposal.content_hash,
                    "review_event_id": review_event_id,
                    "session_id": session_id,
                    "action": proposal.action,
                    "one_order_only": True,
                },
                proposal_id=proposal.proposal_id,
                occurred_at=now,
            )
            self._append_in(
                connection,
                "approval_consumed",
                {
                    "content_hash": proposal.content_hash,
                    "approval_event_id": str(approval["event_id"]),
                    "review_event_id": review_event_id,
                },
                proposal_id=proposal.proposal_id,
                occurred_at=now,
            )
            connection.execute(
                """
                INSERT INTO approval_permits(
                    approval_event_id, review_event_id, proposal_id,
                    content_hash, session_id, action
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(approval["event_id"]),
                    review_event_id,
                    proposal.proposal_id,
                    proposal.content_hash,
                    session_id,
                    proposal.action,
                ),
            )
            return ApprovalPermit(
                proposal_id=proposal.proposal_id,
                content_hash=proposal.content_hash,
                approval_event_id=str(approval["event_id"]),
                review_event_id=review_event_id,
                session_id=session_id,
            )

    @staticmethod
    def confirmation_code_for_review(
        proposal: OrderProposal, review: dict[str, Any]
    ) -> str:
        payload = review.get("payload", review)
        review_event_id = str(review.get("event_id", ""))
        if not review_event_id:
            raise JournalError("review confirmation requires an exact review event id")
        material = canonical_json(
            {
                "proposal_content_hash": proposal.content_hash,
                "review_event_id": review_event_id,
                "quote_timestamp": payload.get("quote_timestamp"),
                "bid": payload.get("bid"),
                "ask": payload.get("ask"),
            }
        )
        return f"CONFIRM-{hashlib.sha256(material.encode('utf-8')).hexdigest()[:12].upper()}"

    def claim_permit(
        self,
        proposal: OrderProposal,
        permit: ApprovalPermit,
        stage: str,
    ) -> bool:
        valid_stages = {
            "entry_oto": {"submit_order"},
            "close_position": {"cancel_protective_stop", "submit_order"},
        }
        if stage not in valid_stages.get(proposal.action, set()):
            return False
        self.verify_integrity()
        with self._transaction() as connection:
            self._verify_authorization_state(connection)
            approval = connection.execute(
                """
                SELECT p.*, e.payload_json AS approval_payload
                FROM approval_permits p
                JOIN events e ON e.event_id = p.approval_event_id
                WHERE p.approval_event_id = ? AND e.event_type = 'owner_approved'
                """,
                (permit.approval_event_id,),
            ).fetchone()
            if approval is None:
                return False
            payload = json.loads(str(approval["approval_payload"]))
            if (
                str(approval["proposal_id"]) != proposal.proposal_id
                or str(approval["content_hash"]) != proposal.content_hash
                or str(approval["review_event_id"]) != permit.review_event_id
                or str(approval["session_id"]) != permit.session_id
                or str(approval["action"]) != proposal.action
                or permit.proposal_id != proposal.proposal_id
                or permit.content_hash != proposal.content_hash
                or payload.get("content_hash") != proposal.content_hash
                or payload.get("review_event_id") != permit.review_event_id
                or payload.get("session_id") != permit.session_id
            ):
                return False
            consumed_rows = connection.execute(
                """
                SELECT payload_json FROM events
                WHERE proposal_id = ? AND event_type = 'approval_consumed'
                """,
                (proposal.proposal_id,),
            ).fetchall()
            consumed = any(
                json.loads(str(row["payload_json"])).get("approval_event_id")
                == permit.approval_event_id
                for row in consumed_rows
            )
            already_claimed = connection.execute(
                """
                SELECT 1 FROM permit_claims
                WHERE approval_event_id = ? AND stage = ?
                """,
                (permit.approval_event_id, stage),
            ).fetchone()
            if not consumed or already_claimed:
                return False
            if proposal.action == "close_position" and stage == "submit_order":
                canceled = connection.execute(
                    """
                    SELECT 1 FROM permit_claims
                    WHERE approval_event_id = ? AND stage = 'cancel_protective_stop'
                    """,
                    (permit.approval_event_id,),
                ).fetchone()
                verified = connection.execute(
                    """
                    SELECT 1 FROM permit_verifications
                    WHERE approval_event_id = ?
                      AND verification_type = 'protective_stop_canceled'
                    """,
                    (permit.approval_event_id,),
                ).fetchone()
                if canceled is None or verified is None:
                    return False
            claimed_at = datetime.now(timezone.utc)
            connection.execute(
                """
                INSERT INTO permit_claims(approval_event_id, stage, claimed_at)
                VALUES (?, ?, ?)
                """,
                (permit.approval_event_id, stage, claimed_at.isoformat()),
            )
            self._append_in(
                connection,
                "broker_mutation_claimed",
                {
                    "content_hash": proposal.content_hash,
                    "approval_event_id": permit.approval_event_id,
                    "stage": stage,
                },
                proposal_id=proposal.proposal_id,
                occurred_at=claimed_at,
            )
            return True

    def record_protective_stop_cancellation_verified(
        self,
        proposal: OrderProposal,
        permit: ApprovalPermit,
        *,
        stop_order_id: str,
        verified_at: datetime,
    ) -> None:
        if proposal.action != "close_position" or not stop_order_id:
            raise JournalError("stop-cancellation verification requires an exact exit proposal")
        if verified_at.tzinfo is None:
            raise JournalError("stop-cancellation verification timestamp must be timezone-aware")
        self.verify_integrity()
        with self._transaction() as connection:
            self._verify_authorization_state(connection)
            approval = connection.execute(
                """
                SELECT * FROM approval_permits WHERE approval_event_id = ?
                """,
                (permit.approval_event_id,),
            ).fetchone()
            if approval is None or any(
                (
                    str(approval["proposal_id"]) != proposal.proposal_id,
                    str(approval["content_hash"]) != proposal.content_hash,
                    str(approval["review_event_id"]) != permit.review_event_id,
                    str(approval["session_id"]) != permit.session_id,
                    str(approval["action"]) != proposal.action,
                )
            ):
                raise JournalError("stop-cancellation verification has no valid approval permit")
            canceled = connection.execute(
                """
                SELECT 1 FROM permit_claims
                WHERE approval_event_id = ? AND stage = 'cancel_protective_stop'
                """,
                (permit.approval_event_id,),
            ).fetchone()
            submitted = connection.execute(
                """
                SELECT 1 FROM permit_claims
                WHERE approval_event_id = ? AND stage = 'submit_order'
                """,
                (permit.approval_event_id,),
            ).fetchone()
            if canceled is None or submitted is not None:
                raise JournalError("stop cancellation must be claimed before exit submission")
            try:
                connection.execute(
                    """
                    INSERT INTO permit_verifications(
                        approval_event_id, verification_type, detail_json, verified_at
                    ) VALUES (?, 'protective_stop_canceled', ?, ?)
                    """,
                    (
                        permit.approval_event_id,
                        canonical_json({"stop_order_id": stop_order_id}),
                        verified_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError:
                raise JournalError("protective-stop cancellation was already verified") from None
            self._append_in(
                connection,
                "protective_stop_canceled_for_approved_exit",
                {
                    "symbol": proposal.symbol,
                    "stop_order_id": stop_order_id,
                    "content_hash": proposal.content_hash,
                    "approval_event_id": permit.approval_event_id,
                },
                proposal_id=proposal.proposal_id,
                occurred_at=verified_at,
            )

    @staticmethod
    def _verify_authorization_state(connection: sqlite3.Connection) -> None:
        event_rows = connection.execute(
            """
            SELECT event_id, occurred_at, event_type, proposal_id, payload_json
            FROM events
            WHERE event_type IN (
                'owner_approved', 'approval_consumed',
                'broker_mutation_claimed',
                'protective_stop_canceled_for_approved_exit'
            )
            """
        ).fetchall()
        events = {
            str(row["event_id"]): {
                "occurred_at": str(row["occurred_at"]),
                "event_type": str(row["event_type"]),
                "proposal_id": str(row["proposal_id"]),
                "payload": json.loads(str(row["payload_json"])),
            }
            for row in event_rows
        }
        permits = connection.execute("SELECT * FROM approval_permits").fetchall()
        permit_ids = {str(row["approval_event_id"]) for row in permits}
        owner_ids = {
            event_id for event_id, event in events.items()
            if event["event_type"] == "owner_approved"
        }
        if permit_ids != owner_ids:
            raise JournalError("authorization permit table does not match approval events")
        consumed = [
            event for event in events.values()
            if event["event_type"] == "approval_consumed"
        ]
        for permit in permits:
            approval_id = str(permit["approval_event_id"])
            owner = events[approval_id]
            if (
                owner["proposal_id"] != str(permit["proposal_id"])
                or owner["payload"].get("content_hash") != str(permit["content_hash"])
                or owner["payload"].get("review_event_id")
                != str(permit["review_event_id"])
                or owner["payload"].get("session_id") != str(permit["session_id"])
                or owner["payload"].get("action") != str(permit["action"])
                or not any(
                    event["proposal_id"] == str(permit["proposal_id"])
                    and event["payload"].get("approval_event_id") == approval_id
                    and event["payload"].get("content_hash")
                    == str(permit["content_hash"])
                    and event["payload"].get("review_event_id")
                    == str(permit["review_event_id"])
                    for event in consumed
                )
            ):
                raise JournalError("authorization permit content does not match its audit events")

        claim_rows = connection.execute("SELECT * FROM permit_claims").fetchall()
        claim_events = [
            event for event in events.values()
            if event["event_type"] == "broker_mutation_claimed"
        ]
        expected_claims = {
            (event["payload"].get("approval_event_id"), event["payload"].get("stage"))
            for event in claim_events
        }
        actual_claims = {
            (str(row["approval_event_id"]), str(row["stage"])) for row in claim_rows
        }
        if actual_claims != expected_claims:
            raise JournalError("authorization claim table does not match claim events")
        for row in claim_rows:
            matching = [
                event for event in claim_events
                if event["payload"].get("approval_event_id")
                == str(row["approval_event_id"])
                and event["payload"].get("stage") == str(row["stage"])
            ]
            if len(matching) != 1 or matching[0]["occurred_at"] != str(row["claimed_at"]):
                raise JournalError("authorization claim timestamp mismatch")

        verification_rows = connection.execute(
            "SELECT * FROM permit_verifications"
        ).fetchall()
        verification_events = [
            event for event in events.values()
            if event["event_type"] == "protective_stop_canceled_for_approved_exit"
        ]
        if len(verification_rows) != len(verification_events):
            raise JournalError("authorization verification table does not match audit events")
        for row in verification_rows:
            detail = json.loads(str(row["detail_json"]))
            matching = [
                event for event in verification_events
                if event["payload"].get("approval_event_id")
                == str(row["approval_event_id"])
                and event["payload"].get("stop_order_id")
                == detail.get("stop_order_id")
            ]
            if (
                str(row["verification_type"]) != "protective_stop_canceled"
                or len(matching) != 1
                or matching[0]["occurred_at"] != str(row["verified_at"])
            ):
                raise JournalError("authorization verification content mismatch")

    @staticmethod
    def _validate_review(
        proposal: OrderProposal,
        payload: dict[str, Any],
        *,
        reviewed_at: datetime,
        approval_at: datetime | None = None,
    ) -> None:
        if (
            payload.get("content_hash") != proposal.content_hash
            or payload.get("full_order_restatement") is not True
        ):
            raise JournalError("full-order review does not match the exact proposal")
        try:
            bid = Decimal(str(payload["bid"]))
            ask = Decimal(str(payload["ask"]))
            quote_timestamp = parse_timestamp(str(payload["quote_timestamp"]))
        except (KeyError, InvalidOperation, ValueError):
            raise JournalError("full-order review has invalid quote evidence") from None
        if (
            reviewed_at.tzinfo is None
            or quote_timestamp.tzinfo is None
            or reviewed_at < proposal.created_at
            or quote_timestamp > reviewed_at
            or not bid.is_finite()
            or not ask.is_finite()
            or bid <= 0
            or ask < bid
        ):
            raise JournalError("full-order review has invalid timing or quote evidence")
        if approval_at is not None and reviewed_at > approval_at:
            raise JournalError("full-order review occurs after the approval timestamp")

    def account_binding(self) -> dict[str, Any] | None:
        return self.latest_payload("account_bound")

    def permit_stage_claimed_for_proposal(self, proposal_id: str, stage: str) -> bool:
        self.verify_integrity()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM permit_claims c
                JOIN approval_permits p
                  ON p.approval_event_id = c.approval_event_id
                WHERE p.proposal_id = ? AND c.stage = ?
                LIMIT 1
                """,
                (proposal_id, stage),
            ).fetchone()
        return row is not None

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
