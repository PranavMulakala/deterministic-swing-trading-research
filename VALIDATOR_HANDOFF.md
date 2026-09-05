# Independent validator handoff

Audit commit `ec65984` plus the later documentation-only handoff commit. The preregistered protocol was frozen in commit `877fc12` before historical market data was downloaded or the empirical strategy run was performed.

## Start here

```bash
make reproduce
git status --short
```

The first command must pass all tests and regenerate the contents of `outputs/v1/`. A second identical run must leave `outputs/v1/artifact_hashes.json` unchanged. The second command should be empty after reproduction; if it is not, investigate nondeterminism or modified inputs.

## Audit targets

1. Trace completed-close signals to next-available-open entries in `src/swingbot/backtest.py` and sample them against `events_*.jsonl` and `trades_*.csv`.
2. Confirm the risk manager is the only entry authorization path, position size is derived from modeled entry-to-stop loss, and the 0.5% and 3% limits cannot be bypassed.
3. Confirm stops use signal-day ATR but entry-day open, allow same-entry-day protective-stop fills, and model gap-through at the open.
4. Review the deterministic timestamp convention, adjusted-OHLC method, static-universe bias, daily-bar ambiguity, and benchmark turnover disclosed in `methodology.md`.
5. Search the decision path for network and LLM dependencies. The only remote data code should be the explicit downloader; broker submission must raise `ExecutionDisabled`.
6. Independently recompute a sample of fees, modeled spread/slippage, planned risk, P&L, equity, drawdown, and exposure.
7. Treat the 13 local tests and `validation_report.json` as builder evidence, not independent proof.

## Explicit milestone boundary

No Alpaca connection or paper-account mutation exists. The configured research equity is exactly $500, but the owner's Alpaca paper account has not been reset or verified at $500 because the brief places broker integration after milestone 1. `execution_contract.py` only records the future requirements for a broker-native protective stop and broker-confirmed close before local position removal.

## Builder verdict to challenge

V1 passed its software/accounting invariants, but failed to establish superior OOS returns: $500 became $680.48 versus $1,099.85 for SPY and $793.05 for the simple momentum baseline. Its defensible feature is lower drawdown (7.43%) and lower average exposure (31.08%), not benchmark-beating return. The builder recommends retaining it as a reproducible baseline and not advancing it unchanged to paper execution.
