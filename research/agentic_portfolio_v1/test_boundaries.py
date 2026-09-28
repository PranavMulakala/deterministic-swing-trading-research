from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from research.agentic_portfolio_v1 import ORDERS_ENABLED
from research.agentic_portfolio_v1.broker_handoff import sign_receipt, validate_receipt
from research.agentic_portfolio_v1.common import ValidationError
from research.agentic_portfolio_v1.controller import make_card, make_receipt
from research.agentic_portfolio_v1.decisions import PaperDecision
from research.agentic_portfolio_v1.evidence import EvidencePacket
from research.agentic_portfolio_v1.freeze import verify


NOW = datetime(2026, 9, 14, 20, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parent


class BrokerHandoffTests(unittest.TestCase):
    def test_account_and_quote_reads_validate(self):
        account = sign_receipt({
            "receipt_type": "ACCOUNT_READ", "account_ref": "virtual-or-redacted",
            "status": "READ_ONLY", "buying_power": "0", "observed_at": (NOW - timedelta(seconds=2)).isoformat(),
            "retrieved_at": (NOW - timedelta(seconds=1)).isoformat(),
        })
        quote = sign_receipt({
            "receipt_type": "QUOTE_READ", "symbol": "LITE", "bid": "99", "ask": "100",
            "source": "SYNTHETIC", "observed_at": (NOW - timedelta(seconds=2)).isoformat(),
            "retrieved_at": (NOW - timedelta(seconds=1)).isoformat(),
        })
        self.assertEqual(validate_receipt(account, now=NOW)["status"], "READ_ONLY")
        self.assertEqual(validate_receipt(quote, now=NOW)["symbol"], "LITE")

    def test_order_review_is_validation_only(self):
        quote = sign_receipt({
            "receipt_type": "QUOTE_READ", "symbol": "LITE", "bid": "99", "ask": "100",
            "source": "SYNTHETIC", "observed_at": (NOW - timedelta(seconds=2)).isoformat(),
            "retrieved_at": (NOW - timedelta(seconds=1)).isoformat(),
        })
        review = sign_receipt({
            "receipt_type": "ORDER_REVIEW", "intent_hash": "a" * 64, "account_ref": "redacted",
            "symbol": "LITE", "side": "BUY", "quantity": "1", "order_type": "LIMIT",
            "limit_price": "100", "time_in_force": "DAY", "estimated_cost": "100",
            "warnings": ["PAPER comparison only"], "reviewed_at": NOW.isoformat(), "status": "REVIEW_ONLY",
            "quote_receipt_hash": quote["receipt_hash"], "quote_symbol": "LITE",
            "quote_observed_at": (NOW - timedelta(seconds=2)).isoformat(),
            "quote_retrieved_at": (NOW - timedelta(seconds=1)).isoformat(),
        })
        self.assertEqual(validate_receipt(review, now=NOW, quote_receipt=quote)["status"], "REVIEW_ONLY")
        with self.assertRaisesRegex(ValidationError, "actual signed"):
            validate_receipt(review, now=NOW)
        wrong_quote = sign_receipt({**{k: v for k, v in quote.items() if k != "receipt_hash"}, "symbol": "COHR"})
        with self.assertRaisesRegex(ValidationError, "not bound"):
            validate_receipt(review, now=NOW, quote_receipt=wrong_quote)
        stale_quote = sign_receipt({
            **{k: v for k, v in quote.items() if k != "receipt_hash"},
            "observed_at": (NOW - timedelta(minutes=3)).isoformat(),
            "retrieved_at": (NOW - timedelta(minutes=3)).isoformat(),
        })
        with self.assertRaisesRegex(ValidationError, "stale"):
            validate_receipt(review, now=NOW, quote_receipt=stale_quote)

    def test_malformed_stale_tampered_and_execution_receipts_reject(self):
        base = {
            "receipt_type": "QUOTE_READ", "symbol": "LITE", "bid": "99", "ask": "100", "source": "TEST",
            "observed_at": (NOW - timedelta(minutes=3)).isoformat(), "retrieved_at": (NOW - timedelta(minutes=3)).isoformat(),
        }
        with self.assertRaisesRegex(ValidationError, "stale"):
            validate_receipt(sign_receipt(base), now=NOW)
        fresh = dict(base, observed_at=NOW.isoformat(), retrieved_at=NOW.isoformat())
        tampered = sign_receipt(fresh)
        tampered["ask"] = "101"
        with self.assertRaisesRegex(ValidationError, "hash"):
            validate_receipt(tampered, now=NOW)
        executable = sign_receipt({**fresh, "endpoint": "https://example.invalid"})
        with self.assertRaisesRegex(ValidationError, "fields"):
            validate_receipt(executable, now=NOW)
        shaped = sign_receipt({
            "receipt_type": "ORDER_REVIEW", "intent_hash": "a" * 64, "account_ref": None,
            "symbol": None, "side": "BUY", "quantity": "1", "order_type": "LIMIT",
            "limit_price": "100", "time_in_force": "DAY", "estimated_cost": "100", "warnings": [],
            "reviewed_at": NOW.isoformat(), "status": "REVIEW_ONLY", "quote_receipt_hash": "b" * 64,
            "quote_symbol": None, "quote_observed_at": NOW.isoformat(), "quote_retrieved_at": NOW.isoformat(),
        })
        with self.assertRaises(ValidationError):
            validate_receipt(shaped, now=NOW)


class ControllerTests(unittest.TestCase):
    def test_card_has_provenance_and_explicit_no_order_banner(self):
        evidence = EvidencePacket.build(
            kind="test", strategy="test", version="1", symbol="LITE", source="SYNTHETIC",
            feature_as_of=NOW - timedelta(seconds=2), observed_at=NOW - timedelta(seconds=1), retrieved_at=NOW,
            data={"x": 1},
        )
        decision = PaperDecision(
            "ABSTAIN", "test", "1", "virtual", "LITE", ("test reason",), evidence.evidence_hash,
            {"target_price": "110", "invalidation": "broken", "review_conditions": "21 sessions",
             "modeled_entry_debit": "200"},
        )
        card = make_card(decision, evidence, NOW, expected_virtual_account="virtual")
        receipt = make_receipt(card)
        self.assertEqual(card.banner, "PAPER_ONLY/NO_ORDER")
        self.assertIs(receipt["paper_only"], True)
        self.assertIs(receipt["no_order"], True)
        self.assertIn("observed", card.human_text())
        self.assertEqual(len(receipt["receipt_hash"]), 64)

    def test_controller_rejects_mismatched_evidence(self):
        evidence = EvidencePacket.build(
            kind="test", strategy="test", version="1", symbol="LITE", source="TEST",
            feature_as_of=NOW, observed_at=NOW, retrieved_at=NOW, data={"x": 1},
        )
        decision = PaperDecision("ABSTAIN", "test", "1", "virtual", "LITE", ("x",), "wrong")
        with self.assertRaisesRegex(ValidationError, "mismatch"):
            make_card(decision, evidence, NOW, expected_virtual_account="virtual")

    def test_controller_revalidates_mutation_time_and_identity(self):
        evidence = EvidencePacket.build(
            kind="test", strategy="test", version="1", symbol="LITE", source="TEST",
            feature_as_of=NOW, observed_at=NOW, retrieved_at=NOW, data={"x": 1},
        )
        valid = PaperDecision("ABSTAIN", "test", "1", "virtual", "LITE", ("x",), evidence.evidence_hash)
        with self.assertRaisesRegex(ValidationError, "future-data"):
            make_card(valid, evidence, NOW - timedelta(seconds=1), expected_virtual_account="virtual")
        wrong = PaperDecision("ABSTAIN", "test", "1", "virtual", "COHR", ("x",), evidence.evidence_hash)
        with self.assertRaisesRegex(ValidationError, "symbol"):
            make_card(wrong, evidence, NOW, expected_virtual_account="virtual")
        evidence.data["x"] = 2
        with self.assertRaisesRegex(ValidationError, "hash mismatch"):
            make_card(valid, evidence, NOW, expected_virtual_account="virtual")

    def test_controller_requires_exact_strategy_version_and_account_binding(self):
        evidence = EvidencePacket.build(
            kind="test", strategy="test", version="1", symbol="LITE", source="TEST",
            feature_as_of=NOW, observed_at=NOW, retrieved_at=NOW, data={"x": 1},
        )
        wrong_strategy = PaperDecision("ABSTAIN", "other", "1", "virtual", "LITE", ("x",), evidence.evidence_hash)
        with self.assertRaisesRegex(ValidationError, "strategy/version"):
            make_card(wrong_strategy, evidence, NOW, expected_virtual_account="virtual")
        valid = PaperDecision("ABSTAIN", "test", "1", "virtual", "LITE", ("x",), evidence.evidence_hash)
        with self.assertRaisesRegex(ValidationError, "account binding"):
            make_card(valid, evidence, NOW)
        with self.assertRaisesRegex(ValidationError, "virtual account"):
            make_card(valid, evidence, NOW, expected_virtual_account="different")


class StaticBoundaryTests(unittest.TestCase):
    def test_runtime_has_no_network_or_brokerage_imports(self):
        forbidden_roots = {"requests", "httpx", "aiohttp", "urllib", "alpaca", "robinhood", "ib_insync", "webull"}
        runtime_files = [
            path for path in ROOT.glob("*.py")
            if not path.name.startswith("test_") and path.name not in {"freeze.py"}
        ]
        for path in runtime_files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(forbidden_roots & imported, f"forbidden import in {path.name}")

    def test_orders_enabled_is_literal_false_everywhere(self):
        self.assertIs(ORDERS_ENABLED, False)
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        self.assertIs(config["orders_enabled"], False)
        runtime_files = [path for path in ROOT.glob("*.py") if not path.name.startswith("test_")]
        self.assertFalse(any("def place" in path.read_text(encoding="utf-8").lower()
                             for path in runtime_files))

    def test_broker_schema_has_no_execution_operation(self):
        schema = json.loads((ROOT / "broker_handoff_schema.json").read_text(encoding="utf-8"))
        rendered = json.dumps(schema).lower()
        for forbidden in ("place_order", "cancel_order", "replace_order", "submit_order"):
            self.assertNotIn(forbidden, rendered)

    def test_freeze_manifest_and_drift_detection(self):
        self.assertEqual(verify(), [])
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            manifest = json.loads((ROOT / "FREEZE.json").read_text(encoding="utf-8"))
            shutil.copy2(ROOT / "FREEZE.json", target / "FREEZE.json")
            for relative in manifest["files"]:
                shutil.copy2(ROOT / relative, target / relative)
            victim = target / next(iter(manifest["files"]))
            victim.write_text(victim.read_text(encoding="utf-8") + "\ndrift", encoding="utf-8")
            self.assertTrue(any(error.startswith("drift:") for error in verify(target)))

    def test_freeze_manifest_omission_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            manifest = json.loads((ROOT / "FREEZE.json").read_text(encoding="utf-8"))
            for relative in manifest["files"]:
                shutil.copy2(ROOT / relative, target / relative)
            manifest["files"].pop("risk.py")
            (target / "FREEZE.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertIn("omitted-from-manifest:risk.py", verify(target))


if __name__ == "__main__":
    unittest.main()
