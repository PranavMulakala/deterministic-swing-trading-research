# Test and verification inventory — September 22, 2026

Fresh static discovery; no full-suite execution claimed. 70 Python test modules contain 1,079 test function definitions. Runtime parametrization/discovery may differ. Release copies, runs and deployment verification directories excluded from primary count. Exact function names and SHA-256 hashes are in [JSON](project-test-inventory-20260922.json). Historical pass reports remain dated evidence; do not sum them.

| Module | Static test definitions |
|---|---:|
| [cloud/test_collector.py](../cloud/test_collector.py) | 12 |
| [cloud/test_free_stock_provider.py](../cloud/test_free_stock_provider.py) | 4 |
| [cloud/test_readiness_v2.py](../cloud/test_readiness_v2.py) | 11 |
| [cloud/test_repair_20260921.py](../cloud/test_repair_20260921.py) | 1 |
| [cloud/test_research_loop.py](../cloud/test_research_loop.py) | 11 |
| [cloud/test_stock_runtime_supervisor.py](../cloud/test_stock_runtime_supervisor.py) | 13 |
| [dashboard/test_dashboard.py](../dashboard/test_dashboard.py) | 11 |
| [research/agentic_forward_trial_context_v1/test_forward_trial.py](../research/agentic_forward_trial_context_v1/test_forward_trial.py) | 64 |
| [research/agentic_forward_trial_context_v2/test_forward_trial.py](../research/agentic_forward_trial_context_v2/test_forward_trial.py) | 73 |
| [research/agentic_forward_trial_context_v3/test_forward_trial.py](../research/agentic_forward_trial_context_v3/test_forward_trial.py) | 81 |
| [research/agentic_paper_runtime_v1/test_runtime.py](../research/agentic_paper_runtime_v1/test_runtime.py) | 6 |
| [research/agentic_portfolio_paper_10000_v1/test_profile.py](../research/agentic_portfolio_paper_10000_v1/test_profile.py) | 31 |
| [research/agentic_portfolio_v1/test_boundaries.py](../research/agentic_portfolio_v1/test_boundaries.py) | 12 |
| [research/agentic_portfolio_v1/test_options.py](../research/agentic_portfolio_v1/test_options.py) | 25 |
| [research/agentic_portfolio_v1/test_risk.py](../research/agentic_portfolio_v1/test_risk.py) | 34 |
| [research/agentic_portfolio_v1/test_stock.py](../research/agentic_portfolio_v1/test_stock.py) | 24 |
| [research/agentic_shadow_indicative_v1/test_engine.py](../research/agentic_shadow_indicative_v1/test_engine.py) | 38 |
| [research/agentic_shadow_indicative_v1/test_engine_adversarial.py](../research/agentic_shadow_indicative_v1/test_engine_adversarial.py) | 7 |
| [research/agentic_shadow_indicative_v1/test_indicative.py](../research/agentic_shadow_indicative_v1/test_indicative.py) | 21 |
| [research/agentic_shadow_v1/test_adversarial.py](../research/agentic_shadow_v1/test_adversarial.py) | 8 |
| [research/agentic_shadow_v1/test_shadow.py](../research/agentic_shadow_v1/test_shadow.py) | 38 |
| [research/agentic_stock_paper_free_v1/test_runtime.py](../research/agentic_stock_paper_free_v1/test_runtime.py) | 7 |
| [research/agentic_stock_paper_free_v2/test_runtime.py](../research/agentic_stock_paper_free_v2/test_runtime.py) | 7 |
| [research/lite_2026/test_profile.py](../research/lite_2026/test_profile.py) | 4 |
| [research/lite_capital_diagnostic_v1/test_run.py](../research/lite_capital_diagnostic_v1/test_run.py) | 8 |
| [research/lite_execution_data/test_followup.py](../research/lite_execution_data/test_followup.py) | 21 |
| [research/lite_reversal_v1/test_experiment.py](../research/lite_reversal_v1/test_experiment.py) | 36 |
| [research/lite_ytd_movement/test_analyze.py](../research/lite_ytd_movement/test_analyze.py) | 12 |
| [research/mnq_feasibility_v1/test_engine.py](../research/mnq_feasibility_v1/test_engine.py) | 29 |
| [research/mnq_feasibility_v1/test_import_and_prepared.py](../research/mnq_feasibility_v1/test_import_and_prepared.py) | 6 |
| [research/mnq_feasibility_v1/test_quote_only.py](../research/mnq_feasibility_v1/test_quote_only.py) | 8 |
| [research/mnq_feasibility_v1/test_trade_extension.py](../research/mnq_feasibility_v1/test_trade_extension.py) | 11 |
| [research/mnq_live_trial_v1/test_trial_budget.py](../research/mnq_live_trial_v1/test_trial_budget.py) | 21 |
| [research/mnq_paper_validation_v1/test_compare.py](../research/mnq_paper_validation_v1/test_compare.py) | 39 |
| [research/orb_comparison_v1/test_data.py](../research/orb_comparison_v1/test_data.py) | 15 |
| [research/orb_comparison_v1/test_engine.py](../research/orb_comparison_v1/test_engine.py) | 27 |
| [research/orb_direct_breakout_v1/test_direct.py](../research/orb_direct_breakout_v1/test_direct.py) | 5 |
| [research/orb_quote_v2/test_quote_replay.py](../research/orb_quote_v2/test_quote_replay.py) | 29 |
| [research/webull_sandbox_v1/test_probe.py](../research/webull_sandbox_v1/test_probe.py) | 11 |
| [scripts/test_check_ibkr_paper.py](../scripts/test_check_ibkr_paper.py) | 9 |
| [tests/ibkr_paper_v1/test_broker_execution.py](../tests/ibkr_paper_v1/test_broker_execution.py) | 15 |
| [tests/ibkr_paper_v1/test_execution.py](../tests/ibkr_paper_v1/test_execution.py) | 16 |
| [tests/ibkr_paper_v1/test_native_simulator.py](../tests/ibkr_paper_v1/test_native_simulator.py) | 8 |
| [tests/ibkr_paper_v1/test_operations.py](../tests/ibkr_paper_v1/test_operations.py) | 19 |
| [tests/ibkr_paper_v1/test_reconciliation.py](../tests/ibkr_paper_v1/test_reconciliation.py) | 7 |
| [tests/ibkr_paper_v1/test_session_analysis.py](../tests/ibkr_paper_v1/test_session_analysis.py) | 7 |
| [tests/ibkr_paper_v1/test_signal_adapter.py](../tests/ibkr_paper_v1/test_signal_adapter.py) | 3 |
| [tests/ibkr_paper_v1/test_staging_probe.py](../tests/ibkr_paper_v1/test_staging_probe.py) | 5 |
| [tests/ibkr_paper_v1/test_strategy_runtime.py](../tests/ibkr_paper_v1/test_strategy_runtime.py) | 6 |
| [tests/ibkr_paper_v1/test_tape_adapter.py](../tests/ibkr_paper_v1/test_tape_adapter.py) | 5 |
| [tests/test_alpaca_paper.py](../tests/test_alpaca_paper.py) | 21 |
| [tests/test_alpaca_read_contract.py](../tests/test_alpaca_read_contract.py) | 5 |
| [tests/test_architecture.py](../tests/test_architecture.py) | 4 |
| [tests/test_backtest.py](../tests/test_backtest.py) | 3 |
| [tests/test_config.py](../tests/test_config.py) | 2 |
| [tests/test_data.py](../tests/test_data.py) | 1 |
| [tests/test_execution_contract.py](../tests/test_execution_contract.py) | 1 |
| [tests/test_indicators.py](../tests/test_indicators.py) | 2 |
| [tests/test_paper_autopilot.py](../tests/test_paper_autopilot.py) | 7 |
| [tests/test_paper_cli.py](../tests/test_paper_cli.py) | 10 |
| [tests/test_paper_config.py](../tests/test_paper_config.py) | 2 |
| [tests/test_paper_constraint.py](../tests/test_paper_constraint.py) | 1 |
| [tests/test_paper_dashboard.py](../tests/test_paper_dashboard.py) | 3 |
| [tests/test_paper_journal.py](../tests/test_paper_journal.py) | 11 |
| [tests/test_paper_policy.py](../tests/test_paper_policy.py) | 4 |
| [tests/test_paper_reaudit.py](../tests/test_paper_reaudit.py) | 18 |
| [tests/test_paper_reconcile.py](../tests/test_paper_reconcile.py) | 24 |
| [tests/test_paper_signals.py](../tests/test_paper_signals.py) | 2 |
| [tests/test_paper_workflow.py](../tests/test_paper_workflow.py) | 32 |
| [tests/test_risk.py](../tests/test_risk.py) | 5 |

## Additional test and independent verification entrypoints

These paths are an inventory, not instructions to run every script. Inspect effects first; deployment verifiers may contact servers and require access.
- [cloud/verification/20260909/verify_stage.py](../cloud/verification/20260909/verify_stage.py)
- [cloud/verification/20260921/test_renderer.cjs](../cloud/verification/20260921/test_renderer.cjs)
- [cloud/verification/20260921/verify_cloud.py](../cloud/verification/20260921/verify_cloud.py)
- [dashboard/test_ui.cjs](../dashboard/test_ui.cjs)
- [research/agentic_shadow_indicative_v1/deployment/verify_release.py](../research/agentic_shadow_indicative_v1/deployment/verify_release.py)
- [research/agentic_shadow_v1/deployment/verify_release.py](../research/agentic_shadow_v1/deployment/verify_release.py)
- [research/lite_reversal_v1/verify_run.py](../research/lite_reversal_v1/verify_run.py)
- [research/mnq_feasibility_v1/data/validation-tools/numpy/ma/testutils.pyi](../research/mnq_feasibility_v1/data/validation-tools/numpy/ma/testutils.pyi)
- [research/mnq_feasibility_v1/data/validation-tools/numpy/typing/tests/data/fail/testing.pyi](../research/mnq_feasibility_v1/data/validation-tools/numpy/typing/tests/data/fail/testing.pyi)
- [research/mnq_feasibility_v1/data/validation-tools/numpy/typing/tests/data/reveal/testing.pyi](../research/mnq_feasibility_v1/data/validation-tools/numpy/typing/tests/data/reveal/testing.pyi)
- [research/orb_comparison_v1/verify.py](../research/orb_comparison_v1/verify.py)
- [research/orb_quote_v2/verify_execution.py](../research/orb_quote_v2/verify_execution.py)

## Documentation and manifests

All discovered source documentation paths and freeze/manifest paths are enumerated in the JSON. Read the [master handoff](PROJECT_HANDOFF_20260922.md) for dated statuses and strategy-level interpretation. No credentials or raw broker responses are included.
