from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

from . import (
    BROKER_ENABLED,
    DEPLOY_ENABLED,
    MODEL_CALLS_ENABLED,
    NETWORK_ENABLED,
    ORDERS_ENABLED,
)
from .freeze import REQUIRED_FILES, verify as verify_profile_freeze
from .profile import (
    CORE_FREEZE_SHA256,
    CORE_ROOT,
    ProfileValidationError,
    SCHEDULED_SESSION_DATES,
    build_trial,
    derived_dollar_limits,
    load_config,
    maximum_elapsed_scheduled_sessions,
    offline_summary,
    review_assessment,
    verify_core_binding,
)


class Paper10000ProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="paper-10000-profile-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_config(self, value: object) -> Path:
        target = self.root / "config.json"
        target.write_text(json.dumps(value), encoding="utf-8")
        return target

    def test_exact_amounts_and_hard_false_capabilities(self) -> None:
        config = load_config()
        accounts = config["virtual_accounts"]
        self.assertEqual(accounts["stock_swing"]["initial_cash"], "10000.00")
        self.assertEqual(accounts["long_options"]["initial_cash"], "10000.00")
        self.assertEqual(accounts["total_simulated_bookkeeping"], "20000.00")
        self.assertIs(accounts["shared_pool"], False)
        self.assertEqual(set(config["capabilities"].values()), {False})
        self.assertTrue(all(value is False for value in (
            ORDERS_ENABLED, MODEL_CALLS_ENABLED, NETWORK_ENABLED, BROKER_ENABLED, DEPLOY_ENABLED,
        )))

    def test_dollar_limits_are_derived_from_shared_core_policy(self) -> None:
        self.assertEqual(derived_dollar_limits(), {
            "max_stock_position": "2000.00",
            "max_total_deployed": "5000.00",
            "minimum_cash_reserve": "5000.00",
            "max_option_contractual_loss": "500.00",
            "daily_realized_loss_halt": "200.00",
            "high_water_drawdown_halt": "500.00",
        })

    def test_runtime_uses_verified_core_engines_and_separate_ledgers(self) -> None:
        runtime = build_trial(self.root / "state")
        self.assertEqual(type(runtime.stock_ledger).__module__, "research.agentic_portfolio_v1.risk")
        self.assertEqual(type(runtime.options_ledger).__module__, "research.agentic_portfolio_v1.risk")
        self.assertEqual(type(runtime.stock_engine).__module__, "research.agentic_portfolio_v1.stock")
        self.assertEqual(type(runtime.options_engine).__module__, "research.agentic_portfolio_v1.options")
        self.assertNotEqual(runtime.stock_ledger.account_id, runtime.options_ledger.account_id)
        self.assertNotEqual(runtime.stock_ledger_path, runtime.options_ledger_path)
        self.assertNotEqual(
            (runtime.stock_ledger_path.stat().st_dev, runtime.stock_ledger_path.stat().st_ino),
            (runtime.options_ledger_path.stat().st_dev, runtime.options_ledger_path.stat().st_ino),
        )

    def test_accounts_are_financially_isolated(self) -> None:
        runtime = build_trial(self.root / "state")
        now = datetime(2026, 9, 15, 20, 30, tzinfo=timezone.utc)
        before_stock = runtime.stock_ledger.snapshot(now)
        before_options = runtime.options_ledger.snapshot(now)
        self.assertEqual(before_stock["cash_cents"], 1_000_000)
        self.assertEqual(before_options["cash_cents"], 1_000_000)
        runtime.stock_ledger.reserve(
            idempotency_key="isolation-test", strategy="stock_swing_net10_v1",
            strategy_version="1.0.0", symbol="LITE", asset_type="EQUITY",
            notional=100, contractual_loss=100, quantity=1, now=now,
        )
        runtime.stock_ledger.set_kill_switch(True)
        after_stock = runtime.stock_ledger.snapshot(now)
        after_options = runtime.options_ledger.snapshot(now)
        self.assertEqual(after_stock["pending_cents"], 10_000)
        self.assertEqual(after_options["pending_cents"], 0)
        self.assertTrue(after_stock["kill_switch"])
        self.assertFalse(after_options["kill_switch"])
        self.assertEqual(after_options["cash_cents"], 1_000_000)

    def test_hardlink_alias_is_rejected_before_either_file_is_mutated(self) -> None:
        state = self.root / "hardlink-state"
        state.mkdir()
        stock = state / "stock_swing.sqlite"
        options = state / "long_options.sqlite"
        original_bytes = b"preexisting-ledger-bytes"
        stock.write_bytes(original_bytes)
        os.link(stock, options)
        before_stock = stock.lstat()
        before_options = options.lstat()
        with self.assertRaisesRegex(ProfileValidationError, "inode or hardlink"):
            build_trial(state)
        after_stock = stock.lstat()
        after_options = options.lstat()
        self.assertEqual(stock.read_bytes(), original_bytes)
        self.assertEqual(options.read_bytes(), original_bytes)
        self.assertEqual((after_stock.st_dev, after_stock.st_ino), (before_stock.st_dev, before_stock.st_ino))
        self.assertEqual((after_options.st_dev, after_options.st_ino), (before_options.st_dev, before_options.st_ino))

    def test_invalid_single_existing_ledger_does_not_create_absent_counterpart(self) -> None:
        from research.agentic_portfolio_v1.risk import RiskLedger

        cases = (
            ("stock_swing.sqlite", "paper-10000-stock-swing-v1", "long_options.sqlite"),
            ("long_options.sqlite", "paper-10000-long-options-v1", "stock_swing.sqlite"),
        )
        for existing_name, account_id, absent_name in cases:
            with self.subTest(existing_name=existing_name):
                state = self.root / existing_name
                state.mkdir()
                RiskLedger(str(state / existing_name), account_id, 1000)
                with self.assertRaises(ValueError):
                    build_trial(state)
                self.assertFalse((state / absent_name).exists())

    def test_symlink_and_nonregular_ledger_paths_reject_without_target_mutation(self) -> None:
        symlink_state = self.root / "symlink-state"
        symlink_state.mkdir()
        target = self.root / "symlink-target"
        target.write_bytes(b"unchanged")
        (symlink_state / "stock_swing.sqlite").symlink_to(target)
        with self.assertRaisesRegex(ProfileValidationError, "regular non-symlink"):
            build_trial(symlink_state)
        self.assertEqual(target.read_bytes(), b"unchanged")

        directory_state = self.root / "directory-state"
        directory_state.mkdir()
        (directory_state / "long_options.sqlite").mkdir()
        with self.assertRaisesRegex(ProfileValidationError, "regular non-symlink"):
            build_trial(directory_state)
        self.assertFalse((directory_state / "stock_swing.sqlite").exists())

    def test_incompatible_existing_database_preflight_is_nonmutating_in_either_role(self) -> None:
        cases = (
            ("stock_swing.sqlite", "long_options.sqlite"),
            ("long_options.sqlite", "stock_swing.sqlite"),
        )
        for bad_name, absent_name in cases:
            with self.subTest(bad_name=bad_name):
                state = self.root / f"incompatible-{bad_name}"
                state.mkdir()
                bad = state / bad_name
                with sqlite3.connect(bad) as connection:
                    connection.execute(
                        "CREATE TABLE accounts(account_id TEXT PRIMARY KEY, initial_cash_cents INTEGER)"
                    )
                before = bad.read_bytes()
                metadata = bad.stat()
                with self.assertRaises(ProfileValidationError):
                    build_trial(state)
                after = bad.stat()
                self.assertEqual(bad.read_bytes(), before)
                self.assertEqual((after.st_dev, after.st_ino), (metadata.st_dev, metadata.st_ino))
                self.assertEqual(after.st_mtime_ns, metadata.st_mtime_ns)
                self.assertFalse((state / absent_name).exists())
                self.assertFalse(any((state / f"{bad_name}{suffix}").exists() for suffix in ("-journal", "-shm", "-wal")))

    def test_empty_peer_stays_zero_when_other_preflight_fails_in_either_role(self) -> None:
        from research.agentic_portfolio_v1.risk import RiskLedger

        cases = (
            ("stock_swing.sqlite", "long_options.sqlite", "paper-10000-long-options-v1"),
            ("long_options.sqlite", "stock_swing.sqlite", "paper-10000-stock-swing-v1"),
        )
        for empty_name, bad_name, bad_account in cases:
            with self.subTest(empty_name=empty_name):
                state = self.root / f"empty-peer-{empty_name}"
                state.mkdir()
                empty = state / empty_name
                bad = state / bad_name
                empty.touch()
                RiskLedger(str(bad), bad_account, 1000)
                empty_before = empty.stat()
                bad_before_bytes = bad.read_bytes()
                bad_before = bad.stat()
                with self.assertRaises(ProfileValidationError):
                    build_trial(state)
                empty_after = empty.stat()
                bad_after = bad.stat()
                self.assertEqual(empty.read_bytes(), b"")
                self.assertEqual(empty_after.st_size, 0)
                self.assertEqual(
                    (empty_after.st_dev, empty_after.st_ino, empty_after.st_mtime_ns),
                    (empty_before.st_dev, empty_before.st_ino, empty_before.st_mtime_ns),
                )
                self.assertEqual(bad.read_bytes(), bad_before_bytes)
                self.assertEqual(
                    (bad_after.st_dev, bad_after.st_ino, bad_after.st_mtime_ns),
                    (bad_before.st_dev, bad_before.st_ino, bad_before.st_mtime_ns),
                )

    def test_corrupt_non_sqlite_existing_file_rejects_without_mutation(self) -> None:
        state = self.root / "corrupt"
        state.mkdir()
        corrupt = state / "stock_swing.sqlite"
        corrupt.write_bytes(b"not-a-sqlite-database")
        before_bytes = corrupt.read_bytes()
        before = corrupt.stat()
        with self.assertRaisesRegex(ProfileValidationError, "compatible core v1 database"):
            build_trial(state)
        after = corrupt.stat()
        self.assertEqual(corrupt.read_bytes(), before_bytes)
        self.assertEqual((after.st_dev, after.st_ino, after.st_mtime_ns), (before.st_dev, before.st_ino, before.st_mtime_ns))
        self.assertFalse((state / "long_options.sqlite").exists())

    def test_compatible_pair_reopens_after_read_only_preflight(self) -> None:
        state = self.root / "compatible-reopen"
        first = build_trial(state)
        self.assertEqual(first.stock_ledger.account_id, "paper-10000-stock-swing-v1")
        second = build_trial(state)
        now = datetime(2026, 9, 15, 20, 30, tzinfo=timezone.utc)
        self.assertEqual(second.stock_ledger.snapshot(now)["cash_cents"], 1_000_000)
        self.assertEqual(second.options_ledger.snapshot(now)["cash_cents"], 1_000_000)

    def test_two_empty_placeholders_initialize_only_after_both_preflights(self) -> None:
        state = self.root / "empty-pair"
        state.mkdir()
        (state / "stock_swing.sqlite").touch()
        (state / "long_options.sqlite").touch()
        runtime = build_trial(state)
        now = datetime(2026, 9, 15, 20, 30, tzinfo=timezone.utc)
        self.assertEqual(runtime.stock_ledger.snapshot(now)["cash_cents"], 1_000_000)
        self.assertEqual(runtime.options_ledger.snapshot(now)["cash_cents"], 1_000_000)

    def test_one_empty_and_one_compatible_ledger_initialize_in_either_role(self) -> None:
        source = self.root / "compatible-source"
        build_trial(source)
        cases = (
            ("stock_swing.sqlite", "long_options.sqlite"),
            ("long_options.sqlite", "stock_swing.sqlite"),
        )
        for compatible_name, empty_name in cases:
            with self.subTest(compatible_name=compatible_name):
                state = self.root / f"mixed-{compatible_name}"
                state.mkdir()
                shutil.copy2(source / compatible_name, state / compatible_name)
                (state / empty_name).touch()
                runtime = build_trial(state)
                now = datetime(2026, 9, 15, 20, 30, tzinfo=timezone.utc)
                self.assertEqual(runtime.stock_ledger.snapshot(now)["cash_cents"], 1_000_000)
                self.assertEqual(runtime.options_ledger.snapshot(now)["cash_cents"], 1_000_000)

    def test_core_freeze_is_bound_to_exact_sha256(self) -> None:
        self.assertEqual(verify_core_binding(), CORE_FREEZE_SHA256)
        self.assertEqual(
            hashlib.sha256((CORE_ROOT / "FREEZE.json").read_bytes()).hexdigest(),
            "e6d3961f98830ef46850f194ae77f7486714faac685bd6acd77a8a496ecf488d",
        )

    def test_core_freeze_file_drift_fails_closed(self) -> None:
        copied = self.root / "core-freeze-drift"
        shutil.copytree(CORE_ROOT, copied)
        with (copied / "FREEZE.json").open("ab") as stream:
            stream.write(b"\n")
        with self.assertRaisesRegex(ProfileValidationError, "FREEZE.json SHA-256 differs"):
            verify_core_binding(copied)

    def test_core_manifest_file_drift_fails_closed(self) -> None:
        copied = self.root / "core-runtime-drift"
        shutil.copytree(CORE_ROOT, copied)
        with (copied / "stock.py").open("ab") as stream:
            stream.write(b"\n")
        with self.assertRaisesRegex(ProfileValidationError, "manifest hash differs for stock.py"):
            verify_core_binding(copied)

    def test_core_extra_runtime_file_fails_closed(self) -> None:
        copied = self.root / "core-extra-runtime"
        shutil.copytree(CORE_ROOT, copied)
        (copied / "surprise.py").write_text("raise SystemExit\n", encoding="utf-8")
        with self.assertRaisesRegex(ProfileValidationError, "runtime file set differs"):
            verify_core_binding(copied)

    def test_strict_schema_rejects_extra_field(self) -> None:
        config = deepcopy(load_config())
        config["unexpected"] = False
        with self.assertRaisesRegex(ProfileValidationError, "fields do not match"):
            load_config(self.write_config(config))

    def test_strict_schema_rejects_false_integer_substitution(self) -> None:
        config = deepcopy(load_config())
        config["capabilities"]["orders_enabled"] = 0
        with self.assertRaisesRegex(ProfileValidationError, "must remain False"):
            load_config(self.write_config(config))

    def test_dates_session_count_and_checkpoint_are_exact(self) -> None:
        trial = load_config()["trial"]
        self.assertEqual(tuple(trial["scheduled_session_dates"]), SCHEDULED_SESSION_DATES)
        self.assertEqual(len(SCHEDULED_SESSION_DATES), 34)
        self.assertEqual(SCHEDULED_SESSION_DATES[0], "2026-09-15")
        self.assertEqual(SCHEDULED_SESSION_DATES[29], "2026-10-26")
        self.assertEqual(SCHEDULED_SESSION_DATES[-1], "2026-10-30")
        self.assertEqual(trial["minimum_completed_eligible_market_sessions"], 30)
        self.assertEqual(trial["minimum_closed_trades_per_strategy"], 20)
        self.assertIs(trial["actual_session_completeness_must_be_verified"], True)

    def test_review_cannot_open_before_first_checkpoint(self) -> None:
        result = review_assessment(
            completed_eligible_market_sessions=30, stock_closed_trades=40,
            options_closed_trades=40, actual_session_completeness_verified=True,
            as_of=datetime(2026, 10, 26, 20, 29, 59, tzinfo=timezone.utc),
        )
        self.assertEqual(result["status"], "CONTINUE_PAPER_TRIAL_BEFORE_FIRST_CHECKPOINT")
        self.assertTrue(result["all_initial_review_evidence_gates_met"])
        self.assertFalse(result["proof_of_profitability"])
        self.assertFalse(result["promotion_or_live_readiness"])

    def test_elapsed_session_boundaries_and_timezone_are_strict(self) -> None:
        before_start = datetime(2026, 9, 14, 20, 0, tzinfo=timezone.utc)
        first_close = datetime(2026, 9, 15, 20, 0, tzinfo=timezone.utc)
        thirtieth_close = datetime(2026, 10, 26, 20, 0, tzinfo=timezone.utc)
        final_close = datetime(2026, 10, 30, 20, 0, tzinfo=timezone.utc)
        self.assertEqual(maximum_elapsed_scheduled_sessions(before_start), 0)
        self.assertEqual(maximum_elapsed_scheduled_sessions(first_close), 0)
        self.assertEqual(maximum_elapsed_scheduled_sessions(first_close + timedelta(microseconds=1)), 1)
        self.assertEqual(maximum_elapsed_scheduled_sessions(thirtieth_close), 29)
        self.assertEqual(maximum_elapsed_scheduled_sessions(thirtieth_close + timedelta(microseconds=1)), 30)
        self.assertEqual(maximum_elapsed_scheduled_sessions(final_close), 33)
        self.assertEqual(maximum_elapsed_scheduled_sessions(final_close + timedelta(microseconds=1)), 34)
        same_instant = (thirtieth_close + timedelta(microseconds=1)).astimezone(
            timezone(timedelta(hours=9))
        )
        self.assertEqual(maximum_elapsed_scheduled_sessions(same_instant), 30)

        before = review_assessment(
            completed_eligible_market_sessions=0, stock_closed_trades=0,
            options_closed_trades=0, actual_session_completeness_verified=False,
            as_of=before_start,
        )
        self.assertEqual(before["maximum_elapsed_scheduled_sessions"], 0)
        self.assertEqual(before["status"], "CONTINUE_PAPER_TRIAL_BEFORE_FIRST_CHECKPOINT")
        with self.assertRaisesRegex(ProfileValidationError, "maximum scheduled sessions elapsed"):
            review_assessment(
                completed_eligible_market_sessions=1, stock_closed_trades=0,
                options_closed_trades=0, actual_session_completeness_verified=False,
                as_of=first_close,
            )

    def test_impossible_completed_session_counts_fail_closed(self) -> None:
        with self.assertRaisesRegex(ProfileValidationError, "34-session trial calendar"):
            review_assessment(
                completed_eligible_market_sessions=1_000_000, stock_closed_trades=20,
                options_closed_trades=20, actual_session_completeness_verified=True,
                as_of=datetime(2026, 10, 30, 21, 0, tzinfo=timezone.utc),
            )
        with self.assertRaisesRegex(ProfileValidationError, "maximum scheduled sessions elapsed"):
            review_assessment(
                completed_eligible_market_sessions=30, stock_closed_trades=20,
                options_closed_trades=20, actual_session_completeness_verified=True,
                as_of=datetime(2026, 10, 26, 20, 0, tzinfo=timezone.utc),
            )

    def test_review_requires_verified_sessions_and_trades_per_strategy(self) -> None:
        after_checkpoint = datetime(2026, 10, 26, 21, 0, tzinfo=timezone.utc)
        cases = (
            (29, 20, 20, True),
            (30, 19, 20, True),
            (30, 20, 19, True),
            (30, 20, 20, False),
        )
        for completed, stock, options, verified in cases:
            with self.subTest(completed=completed, stock=stock, options=options, verified=verified):
                result = review_assessment(
                    completed_eligible_market_sessions=completed,
                    stock_closed_trades=stock, options_closed_trades=options,
                    actual_session_completeness_verified=verified, as_of=after_checkpoint,
                )
                self.assertEqual(result["status"], "CONTINUE_PAPER_TRIAL_INCOMPLETE_EVIDENCE")

    def test_initial_and_final_reviews_are_eligible_but_never_proof(self) -> None:
        checkpoint = review_assessment(
            completed_eligible_market_sessions=30, stock_closed_trades=20,
            options_closed_trades=20, actual_session_completeness_verified=True,
            as_of=datetime(2026, 10, 26, 21, 0, tzinfo=timezone.utc),
        )
        final = review_assessment(
            completed_eligible_market_sessions=34, stock_closed_trades=25,
            options_closed_trades=22, actual_session_completeness_verified=True,
            as_of=datetime(2026, 10, 30, 21, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(checkpoint["status"], "ELIGIBLE_FOR_INITIAL_REVIEW_NOT_PROOF")
        self.assertEqual(final["status"], "ELIGIBLE_FOR_SCHEDULED_FINAL_REVIEW_NOT_PROOF")
        for result in (checkpoint, final):
            self.assertFalse(result["proof_of_profitability"])
            self.assertFalse(result["promotion_or_live_readiness"])

    def test_news_and_external_factor_status_is_explicit(self) -> None:
        news = load_config()["news_external_factors"]
        self.assertTrue(news["collector_records_direct_news_metadata"])
        self.assertTrue(news["collector_records_sector_news_metadata"])
        self.assertTrue(news["stock_engine_consumes_supplied_hard_adverse_news_boolean"])
        for field in (
            "collector_performs_sentiment_scoring", "engines_consume_collector_news_metadata",
            "options_engine_consumes_news_or_sentiment", "comprehensive_news_integration",
            "fundamentals_integration", "analyst_ratings_integration",
            "macro_interpretation", "sentiment_integration",
        ):
            self.assertIs(news[field], False)

    def test_executable_import_surface_has_no_broker_network_or_deploy_path(self) -> None:
        banned_roots = {"alpaca", "ibkr", "requests", "socket", "subprocess", "urllib"}
        for name in ("__init__.py", "profile.py", "demo.py", "freeze.py"):
            tree = ast.parse((Path(__file__).parent / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse({alias.name.split(".")[0] for alias in node.names} & banned_roots)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".")[0], banned_roots)
        tree = ast.parse((Path(__file__).parent / "profile.py").read_text(encoding="utf-8"))
        loader = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_load_core_types")
        verify_index = next(
            index for index, node in enumerate(loader.body)
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name) and node.value.func.id == "verify_core_binding"
        )
        import_indices = [index for index, node in enumerate(loader.body) if isinstance(node, ast.ImportFrom)]
        self.assertTrue(import_indices)
        self.assertTrue(all(index > verify_index for index in import_indices))
        imported_modules = {node.module for node in loader.body if isinstance(node, ast.ImportFrom)}
        self.assertEqual(imported_modules, {
            "research.agentic_portfolio_v1.options",
            "research.agentic_portfolio_v1.risk",
            "research.agentic_portfolio_v1.stock",
        })

    def test_profile_freeze_covers_every_runtime_file(self) -> None:
        self.assertEqual(verify_profile_freeze(), [])
        manifest = json.loads((Path(__file__).parent / "FREEZE.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["files"]), set(REQUIRED_FILES))

    def test_profile_freeze_rejects_symlinked_manifest_before_read(self) -> None:
        copied = self.root / "profile-copy"
        shutil.copytree(Path(__file__).parent, copied)
        manifest = copied / "FREEZE.json"
        real_manifest = self.root / "real-profile-manifest.json"
        manifest.rename(real_manifest)
        manifest.symlink_to(real_manifest)
        self.assertEqual(
            verify_profile_freeze(copied),
            ["invalid-manifest:FREEZE.json must not be a symlink"],
        )

    def test_bound_core_hashes_are_current_and_unchanged(self) -> None:
        manifest = json.loads((CORE_ROOT / "FREEZE.json").read_text(encoding="utf-8"))
        actual = {
            name: hashlib.sha256((CORE_ROOT / name).read_bytes()).hexdigest()
            for name in manifest["files"]
        }
        self.assertEqual(actual, manifest["files"])

    def test_offline_summary_exposes_only_temporary_paper_state(self) -> None:
        summary = offline_summary(
            self.root / "demo-state",
            as_of=datetime(2026, 9, 15, 20, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(summary["simulated_bookkeeping"]["total"], "20000.00")
        self.assertFalse(summary["simulated_bookkeeping"]["shared_pool"])
        self.assertEqual(summary["initial_snapshots"]["stock_swing"]["cash_cents"], 1_000_000)
        self.assertEqual(summary["initial_snapshots"]["long_options"]["cash_cents"], 1_000_000)
        self.assertEqual(set(summary["capabilities"].values()), {False})
        self.assertEqual(set(summary["claims"].values()), {False})


if __name__ == "__main__":
    unittest.main()
