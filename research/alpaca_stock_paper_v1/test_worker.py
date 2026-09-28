import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr
import io
from zoneinfo import ZoneInfo

from research.alpaca_stock_paper_v1.worker import WorkerConfigError, _outbox_path, _systemd_secrets, load_config, main
from research.alpaca_stock_paper_v1.read_only import URLS, calendar_url


class WorkerTests(unittest.TestCase):
    def _file(self, folder, payload, mode=0o600):
        path = Path(folder) / "worker-config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        os.chmod(path, mode)
        return str(path)

    def test_systemd_credentials_are_private_and_named(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            alpaca = directory / "alpaca-paper"
            mail = directory / "resend-send"
            alpaca.write_text(json.dumps({"key": "PK_fake", "secret": "paper-secret"}))
            mail.write_text(json.dumps({"provider": "resend", "api_key": "re_fake"}))
            os.chmod(alpaca, 0o440)
            os.chmod(mail, 0o440)
            with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": folder}):
                self.assertEqual(_systemd_secrets(), {
                    "alpaca_key_id": "PK_fake", "alpaca_secret_key": "paper-secret",
                    "resend_api_key": "re_fake"})
                alpaca.unlink()
                self.assertEqual(_systemd_secrets(require_alpaca=False),
                                 {"resend_api_key": "re_fake"})
                with self.assertRaisesRegex(WorkerConfigError, "private_file_unavailable"):
                    _systemd_secrets()
                os.chmod(mail, 0o644)
                with self.assertRaisesRegex(WorkerConfigError, "private_file_permissions"):
                    _systemd_secrets(require_alpaca=False)
                os.chmod(mail, 0o600)
                mail.write_text(json.dumps({"provider": "unexpected", "api_key": "re_fake"}))
                os.chmod(mail, 0o440)
                with self.assertRaisesRegex(WorkerConfigError, "systemd_credentials_invalid"):
                    _systemd_secrets(require_alpaca=False)

    def test_systemd_config_and_state_directory_are_scoped(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            creds = root / "credentials"
            creds.mkdir(mode=0o700)
            config = creds / "stock-config"
            config.write_text(json.dumps({"version": 1, "paper_account_id": "paper-id"}))
            os.chmod(config, 0o440)
            with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": str(creds)}):
                self.assertEqual(load_config(str(config), systemd_credential=True).paper_account_id,
                                 "paper-id")
                with self.assertRaisesRegex(WorkerConfigError, "private_file_permissions"):
                    load_config(str(config))
                with self.assertRaisesRegex(WorkerConfigError, "systemd_config_path_invalid"):
                    load_config(str(root / "other"), systemd_credential=True)
            state = root / "private-state"
            state.mkdir(mode=0o700)
            link = root / "state"
            link.symlink_to(state, target_is_directory=True)
            with patch.dict(os.environ, {"STATE_DIRECTORY": str(link)}):
                self.assertEqual(_outbox_path(str(link / "outbox.sqlite")),
                                 str(link / "outbox.sqlite"))
            with self.assertRaisesRegex(WorkerConfigError, "outbox_directory_not_private"):
                _outbox_path(str(link / "outbox.sqlite"))

    def test_empty_paper_config_is_read_only_and_no_email(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self._file(folder, {"version": 1, "paper_account_id": "paper-id",
                                       "email_enabled": False, "position_card": None})
            config = load_config(path)
            self.assertIsNone(config.card)
            self.assertFalse(config.email_enabled)

    def test_config_refuses_unapproved_card_and_bad_route(self):
        with tempfile.TemporaryDirectory() as folder:
            card = {"asset_id": "asset", "position_id": "entry-1", "quantity": "1",
                    "target_price": "810", "opened_at": "2026-09-23T14:00:00Z",
                    "news_since": "2026-09-23T14:00:00Z", "drawdown_levels": [5, 10],
                    "review_every_sessions": 5, "explicitly_approved": False}
            path = self._file(folder, {"version": 1, "paper_account_id": "paper-id",
                                       "position_card": card})
            with self.assertRaisesRegex(WorkerConfigError, "approved_position_card_required"):
                load_config(path)
            card["explicitly_approved"] = True
            path = self._file(folder, {"version": 1, "paper_account_id": "paper-id",
                                       "position_card": card, "email_enabled": True,
                                       "sender": "a@example.com", "recipient": "bad\ncc@example.com"})
            with self.assertRaisesRegex(WorkerConfigError, "verified_email_route_required"):
                load_config(path)
            path = self._file(folder, {"version": 1, "paper_account_id": "paper-id",
                                       "position_card": card})
            loaded = load_config(path)
            self.assertEqual(loaded.card.drawdown_levels, (5, 10))
            card["drawdown_levels"] = []
            self._file(folder, {"version": 1, "paper_account_id": "paper-id",
                                "position_card": card})
            with self.assertRaisesRegex(WorkerConfigError, "review_thresholds_required"):
                load_config(path)

    def test_private_file_permission_and_symlink_required(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self._file(folder, {"version": 1, "paper_account_id": "paper-id"}, 0o644)
            with self.assertRaisesRegex(WorkerConfigError, "private_file_permissions"):
                load_config(path)
            os.chmod(path, 0o600)
            link = Path(folder) / "link.json"
            link.symlink_to(path)
            with self.assertRaisesRegex(WorkerConfigError, "private_file_unavailable"):
                load_config(str(link))

    def test_send_flag_cannot_override_disabled_config(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self._file(folder, {"version": 1, "paper_account_id": "paper-id",
                                       "email_enabled": False})
            with redirect_stderr(io.StringIO()):
                code = main(["--config", path, "--secrets", str(Path(folder) / "nonexistent"),
                             "--outbox", str(Path(folder) / "outbox.sqlite"), "--send"])
            self.assertEqual(code, 2)

    def test_default_check_only_does_not_create_or_queue_an_outbox(self):
        with tempfile.TemporaryDirectory() as folder:
            config = self._file(folder, {"version": 1, "paper_account_id": "paper-id",
                                         "email_enabled": False})
            secrets = Path(folder) / "secrets.json"
            secrets.write_text(json.dumps({"alpaca_key_id": "fake-paper-key",
                                           "alpaca_secret_key": "fake-paper-secret"}),
                               encoding="utf-8")
            os.chmod(secrets, 0o600)

            def fake_broker(**_):
                def fetch(url):
                    if url == URLS["account"]:
                        return {"id": "paper-id", "status": "ACTIVE", "cash": "7500"}
                    if url in (URLS["positions"], URLS["open_orders"]):
                        return []
                    if url == URLS["clock"]:
                        return {"is_open": True, "timestamp": datetime.now(timezone.utc).isoformat()}
                    self.fail("unexpected read")
                return fetch

            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("research.alpaca_stock_paper_v1.worker.HttpsGet", side_effect=fake_broker), \
                 redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["--config", config, "--secrets", str(secrets)])
            self.assertEqual(code, 0, stderr.getvalue())
            self.assertEqual(json.loads(stdout.getvalue())["mode"], "check_only")
            self.assertFalse((Path(folder) / "outbox.sqlite").exists())

    def test_named_delivery_test_sends_only_once_without_broker_access(self):
        with tempfile.TemporaryDirectory() as folder:
            config = self._file(folder, {"version": 1,
                                         "email_enabled": True, "sender": "paper@example.com",
                                         "recipient": "owner@example.com"})
            secrets = Path(folder) / "secrets.json"
            secrets.write_text(json.dumps({"resend_api_key": "re_fake"}), encoding="utf-8")
            os.chmod(secrets, 0o600)
            outbox = str(Path(folder) / "outbox.sqlite")
            sent = []

            def fake_mail(**_):
                def deliver(subject, body, key):
                    sent.append((subject, body, key))
                    return "fake-provider-receipt"
                return deliver

            def forbidden_broker(**_):
                self.fail("delivery test must not access Alpaca")

            statuses = []
            with patch("research.alpaca_stock_paper_v1.worker.HttpsGet", side_effect=forbidden_broker), \
                 patch("research.alpaca_stock_paper_v1.worker.ResendTransport", side_effect=fake_mail):
                for _ in range(2):
                    stdout, stderr = io.StringIO(), io.StringIO()
                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        code = main(["--config", config, "--secrets", str(secrets),
                                     "--outbox", outbox, "--test-email", "--test-id", "setup-1"])
                    self.assertEqual(code, 0, stderr.getvalue())
                    statuses.append(json.loads(stdout.getvalue())["status"])
            self.assertEqual(statuses, ["accepted_by_provider", "already_accepted"])
            self.assertEqual(len(sent), 1)
            self.assertIn("no market signal", sent[0][0])
            with sqlite3.connect(outbox) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM stock_alert_outbox").fetchone()[0], 1)

    def test_one_shot_worker_uses_fake_broker_and_fake_mail_only(self):
        with tempfile.TemporaryDirectory() as folder:
            config = self._file(folder, {"version": 1, "paper_account_id": "paper-id",
                                         "email_enabled": True, "sender": "paper@example.com",
                                         "recipient": "owner@example.com"})
            secrets = Path(folder) / "secrets.json"
            secrets.write_text(json.dumps({"alpaca_key_id": "fake-paper-key",
                                           "alpaca_secret_key": "fake-paper-secret",
                                           "resend_api_key": "re_fake"}), encoding="utf-8")
            os.chmod(secrets, 0o600)
            sent = []

            def fake_broker(*, key_id, secret_key):
                self.assertEqual((key_id, secret_key), ("fake-paper-key", "fake-paper-secret"))
                def fetch(url):
                    raise RuntimeError("fake disconnected broker")
                return fetch

            def fake_mail(**kwargs):
                self.assertEqual(kwargs["recipient"], "owner@example.com")
                def deliver(subject, body, key):
                    sent.append((subject, body, key))
                    return "fake-provider-receipt"
                return deliver

            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("research.alpaca_stock_paper_v1.worker.HttpsGet", side_effect=fake_broker), \
                 patch("research.alpaca_stock_paper_v1.worker.ResendTransport", side_effect=fake_mail), \
                 redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["--config", config, "--secrets", str(secrets),
                             "--outbox", str(Path(folder) / "outbox.sqlite"), "--send"])
            self.assertEqual(code, 2)  # broker read blocked; warning was accepted by fake mail
            self.assertEqual(len(sent), 1)
            self.assertEqual(json.loads(stdout.getvalue())["accepted_by_provider"], 1)
            self.assertEqual(stderr.getvalue(), "")

            def broken_mail(**_):
                def deliver(*_args):
                    raise TimeoutError("fake provider down")
                return deliver

            stdout = io.StringIO()
            with patch("research.alpaca_stock_paper_v1.worker.HttpsGet", side_effect=fake_broker), \
                 patch("research.alpaca_stock_paper_v1.worker.ResendTransport", side_effect=broken_mail), \
                 redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                failed_code = main(["--config", config, "--secrets", str(secrets),
                                    "--outbox", str(Path(folder) / "failed.sqlite"), "--send"])
            self.assertEqual(failed_code, 3)
            self.assertEqual(json.loads(stdout.getvalue())["pending_delivery"], 1)

    def test_full_fake_position_alert_path_from_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            now = datetime.now(timezone.utc)
            opened_at = now - timedelta(hours=1)
            news_at = now - timedelta(seconds=1)
            card = {"asset_id": "asset-lite", "position_id": "paper-entry-1",
                    "quantity": "1", "target_price": "810",
                    "opened_at": opened_at.isoformat(), "news_since": opened_at.isoformat(),
                    "drawdown_levels": [5, 10], "review_every_sessions": 5,
                    "explicitly_approved": True}
            config = self._file(folder, {"version": 1, "paper_account_id": "paper-id",
                                         "email_enabled": True, "sender": "paper@example.com",
                                         "recipient": "owner@example.com", "position_card": card})
            secrets = Path(folder) / "secrets.json"
            secrets.write_text(json.dumps({"alpaca_key_id": "fake-paper-key",
                                           "alpaca_secret_key": "fake-paper-secret",
                                           "resend_api_key": "re_fake"}), encoding="utf-8")
            os.chmod(secrets, 0o600)
            local = ZoneInfo("America/New_York")
            first, last = opened_at.astimezone(local).date(), now.astimezone(local).date()
            calendar = []
            day = first
            while day <= last:
                calendar.append({"date": day.isoformat(), "open": "09:30", "close": "16:00"})
                day += timedelta(days=1)
            values = {
                URLS["account"]: {"id": "paper-id", "status": "ACTIVE", "cash": "7500"},
                URLS["positions"]: [{"asset_id": "asset-lite", "symbol": "LITE", "qty": "1",
                                     "avg_entry_price": "800", "side": "long"}],
                URLS["open_orders"]: [],
                URLS["clock"]: {"is_open": True, "timestamp": now.isoformat()},
                URLS["lite_quote"]: {"quote": {"bp": "815", "ap": "815.20", "t": now.isoformat()}},
                URLS["lite_news"]: {"news": [{"id": 51, "symbols": ["LITE"],
                                               "created_at": news_at.isoformat(),
                                               "updated_at": news_at.isoformat(),
                                               "headline": "Paper-only example news", "source": "fixture",
                                               "url": "https://example.com/news"}]},
                calendar_url(first, last): calendar,
            }
            requested = []
            sent = []

            def fake_broker(**_):
                def fetch(url):
                    requested.append(url)
                    return values[url]
                return fetch

            def fake_mail(**_):
                def deliver(subject, body, key):
                    sent.append((subject, body, key))
                    return "fake-provider-receipt"
                return deliver

            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("research.alpaca_stock_paper_v1.worker.HttpsGet", side_effect=fake_broker), \
                 patch("research.alpaca_stock_paper_v1.worker.ResendTransport", side_effect=fake_mail), \
                 redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["--config", config, "--secrets", str(secrets),
                             "--outbox", str(Path(folder) / "outbox.sqlite"), "--send"])
            self.assertEqual(code, 0, stderr.getvalue())
            self.assertEqual(json.loads(stdout.getvalue())["pending_delivery"], 0)
            self.assertTrue(any("target observed" in subject.lower() for subject, _, _ in sent))
            self.assertTrue(any("unclassified" in subject.lower() for subject, _, _ in sent))
            self.assertTrue(all("Paper position ID: paper-entry-1" in body for _, body, _ in sent))
            self.assertIn(calendar_url(first, last), requested)


if __name__ == "__main__":
    unittest.main()
