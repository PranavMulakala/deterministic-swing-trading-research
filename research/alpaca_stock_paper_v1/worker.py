"""One-shot PAPER alert worker. No schedule, order method, or default send."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from research.alpaca_stock_paper_v1.alerts import Draft
from research.alpaca_stock_paper_v1.monitor import PositionCard
from research.alpaca_stock_paper_v1.outbox import connect, enqueue, send_one
from research.alpaca_stock_paper_v1.pipeline import collect
from research.alpaca_stock_paper_v1.read_only import HttpsGet, PaperReader
from research.alpaca_stock_paper_v1.resend_transport import ResendTransport, strict_opener
from research.alpaca_stock_paper_v1.service import run_once


class WorkerConfigError(Exception):
    pass


@dataclass(frozen=True)
class WorkerConfig:
    paper_account_id: str | None
    email_enabled: bool
    sender: str | None
    recipient: str | None
    card: PositionCard | None
    news_since: datetime | None


def _private_json(path: str, *, systemd_credential: bool = False) -> dict:
    """Read an explicitly supplied private file without following symlinks."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            private_owner = info.st_uid == os.getuid() and not info.st_mode & 0o077
            service_credential = (systemd_credential and info.st_uid in (0, os.getuid())
                                  and not info.st_mode & 0o027)
            if not stat.S_ISREG(info.st_mode) or not (private_owner or service_credential):
                raise WorkerConfigError("private_file_permissions")
            with os.fdopen(fd, "r", encoding="utf-8") as handle:
                fd = -1
                raw = handle.read(8193)
        finally:
            if fd >= 0:
                os.close(fd)
    except WorkerConfigError:
        raise
    except (OSError, UnicodeError):
        raise WorkerConfigError("private_file_unavailable") from None
    if len(raw) > 8192:
        raise WorkerConfigError("private_file_too_large")
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        raise WorkerConfigError("invalid_private_json") from None
    if not isinstance(data, dict):
        raise WorkerConfigError("invalid_private_json")
    return data


def _timestamp(raw) -> datetime:
    if not isinstance(raw, str):
        raise WorkerConfigError("invalid_timestamp")
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise WorkerConfigError("invalid_timestamp") from None
    if value.tzinfo is None or value.utcoffset() is None:
        raise WorkerConfigError("invalid_timestamp")
    return value


def _positive(raw) -> Decimal:
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        raise WorkerConfigError("invalid_positive_amount") from None
    if not value.is_finite() or value <= 0:
        raise WorkerConfigError("invalid_positive_amount")
    return value


def _route(raw) -> bool:
    return isinstance(raw, str) and re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", raw) is not None


def load_config(path: str, *, require_paper_account: bool = True,
                systemd_credential: bool = False) -> WorkerConfig:
    if systemd_credential and path != str(Path(os.environ.get("CREDENTIALS_DIRECTORY", "/")) / "stock-config"):
        raise WorkerConfigError("systemd_config_path_invalid")
    data = _private_json(path, systemd_credential=systemd_credential)
    allowed = {"version", "paper_account_id", "email_enabled", "sender", "recipient", "position_card"}
    if set(data) - allowed or data.get("version") != 1:
        raise WorkerConfigError("unsupported_config")
    account_id = data.get("paper_account_id")
    if require_paper_account and (not isinstance(account_id, str) or not account_id.strip()):
        raise WorkerConfigError("paper_account_lock_required")
    if account_id is not None and (not isinstance(account_id, str) or not account_id.strip()):
        raise WorkerConfigError("paper_account_lock_invalid")
    email_enabled = data.get("email_enabled", False)
    if type(email_enabled) is not bool:
        raise WorkerConfigError("invalid_email_flag")
    sender, recipient = data.get("sender"), data.get("recipient")
    if email_enabled and (not _route(sender) or not _route(recipient)):
        raise WorkerConfigError("verified_email_route_required")
    card = None
    news_since = None
    raw_card = data.get("position_card")
    if raw_card is not None:
        if account_id is None:
            raise WorkerConfigError("paper_account_lock_required")
        expected = {"asset_id", "position_id", "quantity", "target_price", "opened_at",
                    "news_since", "drawdown_levels", "review_every_sessions",
                    "explicitly_approved"}
        if not isinstance(raw_card, dict) or set(raw_card) != expected or raw_card["explicitly_approved"] is not True:
            raise WorkerConfigError("approved_position_card_required")
        if (not isinstance(raw_card["asset_id"], str) or not raw_card["asset_id"] or
            not isinstance(raw_card["position_id"], str) or
            not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", raw_card["position_id"])):
            raise WorkerConfigError("position_identity_required")
        opened_at = _timestamp(raw_card["opened_at"])
        news_since = _timestamp(raw_card["news_since"])
        levels = raw_card["drawdown_levels"]
        review_interval = raw_card["review_every_sessions"]
        if (not isinstance(levels, list) or not levels or
            any(type(v) is not int or not 0 < v <= 100 for v in levels) or
            len(set(levels)) != len(levels) or type(review_interval) is not int or
            not 0 < review_interval <= 252):
            raise WorkerConfigError("review_thresholds_required")
        card = PositionCard(account_id, raw_card["asset_id"], raw_card["position_id"],
                            _positive(raw_card["quantity"]), _positive(raw_card["target_price"]),
                            0, False, True, opened_at, tuple(levels), review_interval)
    return WorkerConfig(account_id, email_enabled, sender, recipient, card, news_since)


def _outbox_path(path: str):
    value = Path(path)
    if not value.is_absolute():
        raise WorkerConfigError("outbox_absolute_path_required")
    parent = value.parent
    try:
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode):
            if parent != Path(os.environ.get("STATE_DIRECTORY", "/")):
                raise WorkerConfigError("outbox_directory_not_private")
            info = parent.resolve(strict=True).stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise WorkerConfigError("outbox_directory_not_private")
        if value.exists() or value.is_symlink():
            db_info = value.lstat()
            if not stat.S_ISREG(db_info.st_mode) or db_info.st_uid != os.getuid() or db_info.st_mode & 0o077:
                raise WorkerConfigError("outbox_file_not_private")
    except WorkerConfigError:
        raise
    except OSError:
        raise WorkerConfigError("outbox_directory_unavailable") from None
    return str(value)


def _systemd_secrets(*, require_alpaca: bool = True) -> dict:
    """Map only the named per-service credentials needed for this invocation."""
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if not directory or not Path(directory).is_absolute():
        raise WorkerConfigError("systemd_credentials_unavailable")
    mail = _private_json(str(Path(directory) / "resend-send"), systemd_credential=True)
    if (set(mail) != {"provider", "api_key"} or mail["provider"] != "resend" or
        not isinstance(mail["api_key"], str) or not mail["api_key"].startswith("re_")):
        raise WorkerConfigError("systemd_credentials_invalid")
    result = {"resend_api_key": mail["api_key"]}
    if require_alpaca:
        alpaca = _private_json(str(Path(directory) / "alpaca-paper"), systemd_credential=True)
        if (set(alpaca) != {"key", "secret"} or
            not isinstance(alpaca["key"], str) or not alpaca["key"].startswith("PK") or
            not isinstance(alpaca["secret"], str) or not alpaca["secret"]):
            raise WorkerConfigError("systemd_credentials_invalid")
        result.update(alpaca_key_id=alpaca["key"], alpaca_secret_key=alpaca["secret"])
    return result


def _send_delivery_test(db, delivery, test_id: str, now: datetime) -> str:
    """Send only the named test item; never drain position alerts."""
    if not isinstance(test_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", test_id):
        raise WorkerConfigError("test_id_required")
    key = hashlib.sha256(f"paper-stock-delivery-test|{test_id}".encode()).hexdigest()
    draft = Draft(key, "[PAPER STOCK] Delivery test — no market signal",
                  "This is one paper-stock email delivery test. It does not indicate "
                  "a position, price signal, or order. No trade was placed.\n",
                  "normal")
    from datetime import timedelta
    enqueue(db, draft, now, now + timedelta(hours=24))
    if send_one(db, key, now, delivery):
        return "accepted_by_provider"
    state = db.execute("SELECT state FROM stock_alert_outbox WHERE key=?", (key,)).fetchone()
    return "already_accepted" if state and state[0] == "accepted" else "not_accepted"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Explicit one-shot Alpaca paper alert read")
    parser.add_argument("--config", required=True, help="private worker config JSON")
    parser.add_argument("--secrets", required=True,
                        help="private credentials JSON or @systemd; never pass keys directly")
    parser.add_argument("--outbox", help="SQLite outbox in a private directory; required with --send")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--send", action="store_true", help="enable alert delivery for this one invocation")
    action.add_argument("--test-email", action="store_true", help="send exactly one named delivery test")
    parser.add_argument("--test-id", help="idempotency label required with --test-email")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config, require_paper_account=not args.test_email,
                             systemd_credential=args.secrets == "@systemd")
        if (args.send or args.test_email) and not config.email_enabled:
            raise WorkerConfigError("email_not_enabled_in_config")
        if args.test_email and not args.test_id:
            raise WorkerConfigError("test_id_required")
        if args.test_id and not args.test_email:
            raise WorkerConfigError("test_id_without_test_email")
        secret = (_systemd_secrets(require_alpaca=not args.test_email)
                  if args.secrets == "@systemd" else _private_json(args.secrets))
        if set(secret) - {"alpaca_key_id", "alpaca_secret_key", "resend_api_key"}:
            raise WorkerConfigError("unexpected_secret_field")
        if args.test_email:
            if not args.outbox:
                raise WorkerConfigError("outbox_required_for_test_email")
            db_path = _outbox_path(args.outbox)
            delivery = ResendTransport(api_key=secret.get("resend_api_key"),
                                       sender=config.sender, recipient=config.recipient,
                                       opener=strict_opener())
            os.umask(0o077)
            db = connect(db_path)
            try:
                outcome = _send_delivery_test(db, delivery, args.test_id,
                                              datetime.now(timezone.utc))
            finally:
                db.close()
            print(json.dumps({"mode": "test_email", "status": outcome}, sort_keys=True))
            return 0 if outcome in ("accepted_by_provider", "already_accepted") else 3
        key_id, secret_key = secret.get("alpaca_key_id"), secret.get("alpaca_secret_key")
        if not isinstance(key_id, str) or not isinstance(secret_key, str):
            raise WorkerConfigError("paper_api_credentials_missing")
        reader = PaperReader(HttpsGet(key_id=key_id, secret_key=secret_key))
        started_at = datetime.now(timezone.utc)
        if not args.send:
            evaluation = collect(reader, expected_account_id=config.paper_account_id,
                                 card=config.card, now=started_at,
                                 news_since=config.news_since)
            print(json.dumps({"mode": "check_only", "status": evaluation.status,
                              "drafted": len(evaluation.drafts),
                              "accepted_by_provider": 0}, sort_keys=True))
            return 0 if evaluation.status != "read_blocked" else 2
        if not args.outbox:
            raise WorkerConfigError("outbox_required_for_send")
        db_path = _outbox_path(args.outbox)
        delivery = ResendTransport(api_key=secret.get("resend_api_key"),
                                   sender=config.sender, recipient=config.recipient,
                                   opener=strict_opener())
        os.umask(0o077)
        db = connect(db_path)
        try:
            result = run_once(reader, expected_account_id=config.paper_account_id,
                              card=config.card, now=started_at,
                              outbox_db=db, news_since=config.news_since,
                              delivery=delivery)
        finally:
            db.close()
        print(json.dumps({"status": result.status, "drafted": result.drafted,
                          "accepted_by_provider": result.accepted_by_provider,
                          "pending_delivery": result.pending_delivery,
                          "expired_unsent": result.expired_unsent}, sort_keys=True))
        if args.send and (result.pending_delivery or result.expired_unsent):
            return 3
        return 0 if result.status != "read_blocked" else 2
    except WorkerConfigError as exc:
        print(json.dumps({"status": "config_blocked", "code": str(exc)}), file=sys.stderr)
        return 2
    except Exception:
        print(json.dumps({"status": "worker_failed"}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
