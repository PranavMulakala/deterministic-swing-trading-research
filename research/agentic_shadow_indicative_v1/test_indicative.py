from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from .checkpoint import CheckpointError, audit_archive
from .engine import Ledger, digest
from .producer import (
    AlpacaReadOnlyClient,
    ProducerError,
    _atomic_bytes,
    append_jsonl,
    build_packet,
    build_with_fallback,
    choose_symbol,
    credentials,
    in_collection_window,
    publish_json,
    utc,
)
from .report import build, html_report


NOW = datetime(2026, 9, 14, 14, 0, 0, tzinfo=timezone.utc)


def record(url: str, payload: object, at: datetime = NOW) -> dict:
    raw = json.dumps(payload, sort_keys=True).encode()
    return {
        "url": url,
        "received_at": at.isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "raw_base64": base64.b64encode(raw).decode("ascii"),
        "payload": payload,
    }


class FixtureClient:
    def __init__(self):
        self.records = []

    def _save(self, url, payload):
        item = record(url, payload)
        self.records.append(item)
        return item

    def get(self, base, params):
        if "/stocks/SPY/bars" in base:
            return self._save(base, {"bars": [
                {"t": "2026-09-14T13:45:00+00:00", "c": 500},
                {"t": "2026-09-14T13:50:00+00:00", "c": 501},
                {"t": "2026-09-14T13:55:00+00:00", "c": 502},
            ], "next_page_token": None})
        if "/stocks/QQQ/bars" in base:
            return self._save(base, {"bars": [
                {"t": "2026-09-14T13:45:00+00:00", "c": 400},
                {"t": "2026-09-14T13:50:00+00:00", "c": 401},
                {"t": "2026-09-14T13:55:00+00:00", "c": 402},
            ], "next_page_token": None})
        symbol = "SPY" if "/SPY/" in base else "QQQ"
        price = 502 if symbol == "SPY" else 402
        return self._save(base, {"trade": {"p": price, "t": "2026-09-14T13:59:59+00:00", "c": []}})

    def pages(self, base, params):
        if base.endswith("/v2/calendar"):
            return [self._save(base, [
                {"date": "2026-09-14", "open": "2026-09-14T09:30:00-04:00", "close": "2026-09-14T16:00:00-04:00"},
                {"date": "2026-09-21", "open": "2026-09-21T09:30:00-04:00", "close": "2026-09-21T16:00:00-04:00"},
            ])]
        if "/stocks/SPY/bars" in base:
            return [self._save(base, {"bars": [
                {"t": "2026-09-14T13:45:00+00:00", "c": 500},
                {"t": "2026-09-14T13:50:00+00:00", "c": 501},
                {"t": "2026-09-14T13:55:00+00:00", "c": 502},
            ], "next_page_token": None})]
        if base.endswith("/v2/options/contracts"):
            symbol = params["underlying_symbols"]
            strike = 502 if symbol == "SPY" else 402
            occ = f"{symbol}260921C00{strike}000"
            return [self._save(base, {"option_contracts": [{
                "id": symbol.lower(), "symbol": occ, "underlying_symbol": symbol,
                "root_symbol": symbol, "expiration_date": "2026-09-21",
                "strike_price": str(strike), "type": "call", "style": "american",
                "multiplier": "100", "size": "100", "open_interest": "1000",
                "open_interest_date": "2026-09-11", "deliverables": [],
            }], "next_page_token": None})]
        if "/options/snapshots/" in base:
            symbol = "SPY" if base.endswith("/SPY") else "QQQ"
            strike = 502 if symbol == "SPY" else 402
            occ = f"{symbol}260921C00{strike}000"
            return [self._save(base, {"snapshots": {occ: {
                "latestQuote": {"bp": 0.62, "ap": 0.65, "bs": 10, "as": 10,
                                "t": "2026-09-14T13:59:59+00:00", "c": []},
                "dailyBar": {"v": 200},
            }}, "next_page_token": None})]
        if base.endswith("/v1beta1/news"):
            return [self._save(base, {"news": [{
                "id": 1, "headline": "Fixture market headline",
                "url": "https://example.com/news/1", "symbols": ["SPY"],
                "created_at": "2026-09-14T13:58:00+00:00",
                "updated_at": "2026-09-14T13:58:00+00:00",
            }], "next_page_token": None})]
        if base.endswith("/v1/corporate-actions"):
            return [self._save(base, {"corporate_actions": {}, "next_page_token": None})]
        raise AssertionError(base)


class QQQGapClient(FixtureClient):
    def pages(self, base, params):
        if "/stocks/QQQ/bars" in base:
            return [self._save(base, {"bars": [
                {"t": "2026-09-14T13:35:00+00:00", "c": 400},
                {"t": "2026-09-14T13:45:00+00:00", "c": 401},
                {"t": "2026-09-14T13:55:00+00:00", "c": 402},
            ], "next_page_token": None})]
        return super().pages(base, params)

    def get(self, base, params):
        if "/stocks/QQQ/bars" in base:
            return self._save(base, {"bars": [
                {"t": "2026-09-14T13:35:00+00:00", "c": 400},
                {"t": "2026-09-14T13:45:00+00:00", "c": 401},
                {"t": "2026-09-14T13:55:00+00:00", "c": 402},
            ], "next_page_token": None})
        if "/stocks/SPY/bars" in base:
            return self._save(base, {"bars": [
                {"t": "2026-09-14T13:45:00+00:00", "c": 500},
                {"t": "2026-09-14T13:50:00+00:00", "c": 501},
                {"t": "2026-09-14T13:55:00+00:00", "c": 502},
            ], "next_page_token": None})
        return super().get(base, params)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.raw = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.raw[:limit]


class FakeOpener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeResponse(self.payloads.pop(0))


class IndicativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def packet(self):
        return build_packet(FixtureClient(), "SPY", now=NOW)

    def test_complete_packet_accepts_only_as_indicative(self):
        packet = self.packet()
        self.assertEqual(packet["purpose"], "plumbing_only")
        self.assertFalse(packet["orders_enabled"])
        self.assertEqual(len(packet["bars"]), 3)
        self.assertEqual(len(packet["chain"]["contracts"]), 2)
        ledger = Ledger(self.root / "indicative.sqlite", "indicative")
        try:
            result = ledger.step(packet, now=NOW)
            self.assertEqual(result["decisions"]["deterministic"]["verdict"], "accepted")
        finally:
            ledger.close()
        fixture = Ledger(self.root / "fixture.sqlite", "fixture")
        try:
            with self.assertRaisesRegex(ValueError, "invalid_envelope"):
                fixture.step(packet, now=NOW)
        finally:
            fixture.close()

    def test_packet_carries_both_symbols_but_selects_only_requested_symbol(self):
        packet = self.packet()
        underlyings = {row["contract"]["underlying"] for row in packet["chain"]["contracts"]}
        self.assertEqual(underlyings, {"SPY", "QQQ"})
        ledger = Ledger(self.root / "ledger.sqlite", "indicative")
        try:
            result = ledger.step(packet, now=NOW)
            self.assertEqual(result["candidate"]["contract"]["underlying"], "SPY")
            self.assertNotIn("contract_identity", result["contract_rejections"])
            self.assertEqual(result["packet_hash"], digest(packet))
            self.assertEqual(result["packet"]["full_packet_sha256"], digest(packet))
            self.assertEqual(result["packet"]["chain"]["evaluated_contract_count"], 2)
            self.assertEqual(len(result["packet"]["chain"]["contracts"]), 1)
        finally:
            ledger.close()

    def test_auto_collection_falls_back_when_preferred_bars_have_gaps(self):
        packet = build_with_fallback(QQQGapClient(), "QQQ", now=NOW)
        self.assertEqual(packet["symbol"], "SPY")
        self.assertEqual(packet["producer_symbol_attempts"], [
            {"symbol": "QQQ", "status": "blocked", "reason": "nonconsecutive_bars_QQQ"},
            {"symbol": "SPY", "status": "selected"},
        ])

    def test_scope_and_provider_binding_fail_closed(self):
        mutations = []
        packet = self.packet(); packet["purpose"] = "research"; mutations.append(packet)
        packet = self.packet(); packet["orders_enabled"] = True; mutations.append(packet)
        packet = self.packet(); packet["chain"]["provenance"]["feed"] = "opra"; mutations.append(packet)
        packet = self.packet(); del packet["chain"]["provenance"]["raw"]["provider_response_sha256s"]; mutations.append(packet)
        packet = self.packet(); packet["chain"]["provenance"]["source"] = "https://attacker.invalid/data"; mutations.append(packet)
        for index, malformed in enumerate(mutations):
            with self.subTest(index=index):
                ledger = Ledger(self.root / f"bad-{index}.sqlite", "indicative")
                try:
                    with self.assertRaises(ValueError):
                        ledger.step(malformed, now=NOW)
                finally:
                    ledger.close()

    def test_current_packet_required(self):
        packet = self.packet()
        ledger = Ledger(self.root / "stale.sqlite", "indicative")
        try:
            with self.assertRaisesRegex(ValueError, "not_current"):
                ledger.step(packet, now=datetime(2026, 9, 14, 14, 1, 1, tzinfo=timezone.utc))
        finally:
            ledger.close()

    def test_report_has_unmistakable_plumbing_labels(self):
        ledger = Ledger(self.root / "report.sqlite", "indicative")
        try:
            ledger.step(self.packet(), now=NOW)
            report = build(ledger)
        finally:
            ledger.close()
        rendered = html_report(report)
        self.assertEqual(report["purpose"], "PLUMBING ONLY")
        self.assertIn("NOT VALID FOR PROFIT", report["execution_validity"])
        self.assertIn("PLUMBING ONLY", rendered)
        self.assertIn("Real-money options: DISABLED", rendered)

    def test_client_is_get_only_allowlisted_and_does_not_archive_headers(self):
        opener = FakeOpener([json.dumps({"ok": True}).encode()])
        client = AlpacaReadOnlyClient("private-key", "private-secret", opener=opener)
        result = client.get("https://data.alpaca.markets/example", {"feed": "indicative"})
        request, timeout = opener.requests[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(timeout, 10)
        self.assertEqual(result["payload"], {"ok": True})
        archived = json.dumps(client.records)
        self.assertNotIn("private-key", archived)
        self.assertNotIn("private-secret", archived)
        with self.assertRaisesRegex(ProducerError, "allowlisted"):
            client.get("https://example.com/steal", {})

    def test_repeated_pagination_token_is_rejected(self):
        raw = json.dumps({"items": [], "next_page_token": "repeat"}).encode()
        client = AlpacaReadOnlyClient("key", "secret", opener=FakeOpener([raw, raw]))
        with self.assertRaisesRegex(ProducerError, "pagination_invalid"):
            client.pages("https://data.alpaca.markets/example", {})

    def test_oversize_response_is_rejected(self):
        from .producer import MAX_RESPONSE_BYTES
        client = AlpacaReadOnlyClient(
            "key", "secret", opener=FakeOpener([b"{" + b"x" * MAX_RESPONSE_BYTES])
        )
        with self.assertRaisesRegex(ProducerError, "too_large"):
            client.get("https://data.alpaca.markets/example", {})

    def test_credentials_require_exact_private_file_or_complete_environment(self):
        path = self.root / "alpaca.env"
        path.write_text("ALPACA_PAPER_API_KEY=key\nALPACA_PAPER_API_SECRET=secret\n")
        path.chmod(0o600)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(credentials(path), ("key", "secret"))
        path.write_text(path.read_text() + "EXTRA=value\n")
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ProducerError, "invalid"):
            credentials(path)
        path.write_text("ALPACA_PAPER_API_KEY=key\nALPACA_PAPER_API_SECRET=secret\n")
        path.chmod(0o644)
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ProducerError, "insecure"):
            credentials(path)
        with patch.dict(os.environ, {"ALPACA_PAPER_API_KEY": "key"}, clear=True), self.assertRaisesRegex(ProducerError, "partial"):
            credentials()

    def test_systemd_root_owned_0440_credential_form_is_exactly_scoped(self):
        path = self.root / "alpaca.env"
        path.write_text("ALPACA_PAPER_API_KEY=key\nALPACA_PAPER_API_SECRET=secret\n")
        path.chmod(0o440)
        real_stat = Path.stat
        def root_owned(candidate):
            result = real_stat(candidate)
            values = list(result)
            values[4] = 0
            values[5] = 0
            return os.stat_result(values)
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": str(self.root)}, clear=True), \
                patch.object(Path, "stat", root_owned):
            self.assertEqual(credentials(), ("key", "secret"))
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": str(self.root / "other")}, clear=True), \
                patch.object(Path, "stat", root_owned), self.assertRaisesRegex(ProducerError, "insecure"):
            credentials(path)

    def test_atomic_publication_permissions_and_symlink_refusal(self):
        output = self.root / "packet.json"
        publish_json(output, [{"safe": True}])
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o640)
        self.assertEqual(stat.S_IMODE(output.parent.stat().st_mode), 0o750)
        self.assertEqual(json.loads(output.read_text()), [{"safe": True}])
        linked = self.root / "linked"
        linked.symlink_to(self.root)
        with self.assertRaises(PermissionError):
            _atomic_bytes(linked / "packet.json", b"bad")

    def test_append_only_run_log_is_private_and_machine_readable(self):
        path = self.root / "run-log.jsonl"
        append_jsonl(path, {"status": "PUBLISHED", "orders": False})
        append_jsonl(path, {"status": "IDLE_OUTSIDE_COLLECTION_WINDOW", "network_requests": 0})
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        self.assertEqual([json.loads(line)["status"] for line in path.read_text().splitlines()],
                         ["PUBLISHED", "IDLE_OUTSIDE_COLLECTION_WINDOW"])

    def test_symbol_alternation_and_collection_window(self):
        output = self.root / "packet.json"
        self.assertEqual(choose_symbol(output), "SPY")
        publish_json(output, [{"symbol": "SPY"}])
        self.assertEqual(choose_symbol(output), "QQQ")
        self.assertTrue(in_collection_window(NOW))
        self.assertFalse(in_collection_window(datetime(2026, 9, 14, 22, 0, tzinfo=timezone.utc)))
        self.assertFalse(in_collection_window(datetime(2026, 9, 13, 14, 0, tzinfo=timezone.utc)))

    def test_alpaca_rfc3339_nanoseconds_are_normalized_without_losing_the_instant(self):
        parsed = utc("2026-09-14T19:59:59.968807373+00:00")
        self.assertEqual(parsed.isoformat(), "2026-09-14T19:59:59.968807+00:00")
        self.assertEqual(utc("2026-09-14T19:59:59Z").isoformat(),
                         "2026-09-14T19:59:59+00:00")
        with self.assertRaisesRegex(ProducerError, "invalid_provider_timestamp"):
            utc("2026-09-14 19:59:59")

    def test_normalized_packet_and_archive_are_credential_free(self):
        client = FixtureClient()
        packet = build_packet(client, "SPY", now=NOW)
        artifacts = json.dumps({"packet": packet, "records": client.records})
        for secret in ("private-key", "private-secret", "APCA-API-SECRET-KEY"):
            self.assertNotIn(secret, artifacts)
        self.assertEqual(digest(packet), digest(deepcopy(packet)))

    def test_checkpoint_recomputes_raw_response_archive_and_packet_bindings(self):
        client = FixtureClient()
        packet = build_packet(client, "SPY", now=NOW)
        payload = {
            "event_id": packet["event_id"], "created_at": NOW.isoformat(),
            "purpose": "plumbing_only", "credentials_included": False,
            "normalized_packet_without_archive_hash": packet, "responses": client.records,
        }
        compressed = gzip.compress((json.dumps(payload, sort_keys=True) + "\n").encode(), mtime=0)
        sha = hashlib.sha256(compressed).hexdigest()
        path = self.root / (packet["event_id"] + ".json.gz")
        path.write_bytes(compressed)
        result = audit_archive(path, packet["event_id"], sha)
        full = deepcopy(packet); full["provider_archive_sha256"] = sha
        self.assertEqual(result["packet_sha256"], digest(full))
        payload["responses"][0]["raw_base64"] = base64.b64encode(b"{}").decode("ascii")
        damaged = gzip.compress((json.dumps(payload, sort_keys=True) + "\n").encode(), mtime=0)
        path.write_bytes(damaged)
        with self.assertRaisesRegex(CheckpointError, "binding"):
            audit_archive(path, packet["event_id"], hashlib.sha256(damaged).hexdigest())

    def test_producer_source_has_no_order_or_mutating_http_path(self):
        source = (Path(__file__).with_name("producer.py")).read_text()
        for forbidden in ('method="POST"', 'method="PUT"', 'method="DELETE"',
                          'method="PATCH"', '/v2/orders', '/v2/positions'):
            self.assertNotIn(forbidden, source)

    def test_release_is_exact_credential_free_and_verifiable(self):
        repo = Path(__file__).resolve().parents[2]
        release = self.root / "release"
        built = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("deployment") / "build.py"), str(release)],
            cwd=repo, text=True, capture_output=True, check=True,
        )
        manifest = json.loads((release / "RELEASE.json").read_text())
        self.assertEqual(built.stdout.strip(), manifest["revision"])
        self.assertFalse(manifest["orders"])
        self.assertFalse(manifest["credentials_included"])
        self.assertIn("research/agentic_shadow_indicative_v1/checkpoint.py", manifest["files"])
        self.assertIn("rollback.sh", manifest["files"])
        self.assertNotIn("test_indicative.py", "\n".join(manifest["files"]))
        verified = subprocess.run(
            [sys.executable, str(release / "verify_release.py")],
            text=True, capture_output=True, check=True,
        )
        self.assertIn(manifest["revision"], verified.stdout)
        (release / "unlisted.txt").write_text("unexpected")
        rejected = subprocess.run(
            [sys.executable, str(release / "verify_release.py")],
            text=True, capture_output=True,
        )
        self.assertNotEqual(rejected.returncode, 0)

    def test_deployment_units_keep_credentials_out_of_consumer(self):
        deployment = Path(__file__).with_name("deployment")
        producer = (deployment / "trading-shadow-indicative-producer.service").read_text()
        consumer = (deployment / "trading-shadow-indicative-consumer.service").read_text()
        path_unit = (deployment / "trading-shadow-indicative.path").read_text()
        self.assertIn("LoadCredential=alpaca.env", producer)
        self.assertNotIn("LoadCredential", consumer)
        self.assertIn("PrivateNetwork=yes", consumer)
        self.assertIn("IPAddressDeny=any", consumer)
        self.assertIn("InaccessiblePaths=-/etc/trading-shadow-indicative", consumer)
        self.assertIn("StateDirectory=trading-shadow-indicative-@STATE@", consumer)
        self.assertIn("SHADOW_RELEASE_REVISION=@REVISION@", producer)
        self.assertIn("--run-log", producer)
        self.assertIn("PathChanged=/var/lib/trading-shadow-indicative-inbox/packet.json", path_unit)

    def test_prepare_credentials_selects_only_alpaca_keys_without_printing_values(self):
        source = self.root / "shared.env"
        output = self.root / "dedicated.env"
        source.write_text("OTHER=value\nALPACA_PAPER_API_KEY=private-key\nALPACA_PAPER_API_SECRET=private-secret\n")
        source.chmod(0o600)
        repo = Path(__file__).resolve().parents[2]
        prepared = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("deployment") / "prepare_credentials.py"),
             str(source), str(output)],
            cwd=repo, env={**os.environ, "PYTHONPATH": str(repo / "src")},
            text=True, capture_output=True, check=True,
        )
        self.assertNotIn("private-key", prepared.stdout)
        self.assertNotIn("private-secret", prepared.stdout)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertEqual(output.read_text(),
                         "ALPACA_PAPER_API_KEY=private-key\nALPACA_PAPER_API_SECRET=private-secret\n")


if __name__ == "__main__":
    unittest.main()
