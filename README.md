# Deterministic ETF Swing Research v1

This repository contains two deliberately separated layers:

- Frozen milestone 1 produces auditable historical research. Its config, pinned data, results, and independent validation record remain unchanged.
- The `paper-trading-readiness-v1` branch adds a human-approved Alpaca paper adapter. It contains a real paper submission path, but the default runtime kill switch blocks it and the code has no live-money endpoint.

The current operational verdict is **NO-GO for a faithful v1 paper trial**. Read `PAPER_READINESS.md` before configuring a broker account.

## Quick start

Use Python 3.11 or newer. Runtime dependencies are standard-library only.

```bash
make test
make fetch-data
make reproduce
make paper-constraint
```

Within frozen milestone 1, `fetch-data` is the only networked step. It creates a checksummed snapshot under `data/pinned/`. `reproduce` verifies those checksums, runs the frozen in-sample and out-of-sample simulations plus both benchmarks, and writes `outputs/v1/dashboard.html`, full ledgers, trades, equity, exposure, metrics, and artifact hashes.

The measured conclusion is in `outputs/v1/milestone1_report.md`. V1 remains research-only even if every software validation passes; software correctness does not imply trading profitability.

## Plain-language operating model

- Market: 15 liquid US equity/sector ETFs.
- Direction: long or cash only; no options, leverage, shorts, crypto, or penny stocks.
- Starting account: $500 with fractional shares.
- Entry: ETF is above SMA(200) and RSI(2) is below 10 at a completed daily close; buy next open.
- Exit: fixed 2 x ATR(14) protective stop, close above SMA(20), 20-session time stop, or end of evaluation window.
- Risk: at most 0.5% planned loss per trade, 3% aggregate planned open risk, and a 2% daily realized-loss halt.
- Friction: spread, slippage, and fees are modeled on both sides.

Read `preregistration/v1.md` for the original frozen protocol, `preregistration/v1_post_validation_addendum.md` for non-strategy clarifications, `EXTERNAL_VALIDATION.md` for the independent audit record, and `methodology.md` for assumptions and limitations. The old `src/swingbot/execution_contract.py` milestone-1 boundary still rejects every submission; the separately gated paper adapter is not called through that historical function.

## Human-approved Alpaca paper layer

The added operational path is intentionally narrow:

- exact endpoint allowlist: `https://paper-api.alpaca.markets`; the live trading hostname is rejected by both config validation and the adapter constructor;
- empty account binding only when Alpaca reports approximately $500 equity, no positions, and no working orders;
- completed prior-session bars only, the frozen ETF universe and indicators, and no LLM in data, signal, risk, sizing, or execution;
- whole-share market/GTC OTO entries with a broker-native stop, because Alpaca documents fractional equity orders as DAY-only;
- a fresh quote, full order review, a 120-second confirmation bound to the exact latest review, a final broker-state refresh with the clock sampled last, and an adapter-enforced deadline at the earliest proposal/quote/session boundary; process-only enable/kill-switch values are required for every single order and persisted runtime gates are rejected;
- an exit review that binds the exact protective-stop order ID and price, waits for terminal cancellation, rejects any partial fill, revalidates broker position/account state, and then permits one sell;
- durable SQLite event journal with a hash chain and cross-checked authorization capabilities, client-order idempotency, exact restart recovery (including a completed entry/stop round trip between polls), broker-timestamped fills, fill-ledger cash/accounting and cost-basis reconciliation, point-in-time account marks, a latched kill switch on unknown state, and an explicit clean-$500 new-run rebaseline that preserves history and invalidates old authority;
- scheduled exits require a separate fresh approval; the already-approved protective stop remains broker-native and may execute without another prompt.

Setup and operating steps are in `PAPER_TRADING_RUNBOOK.md`. The exact independent-review scope is in `PAPER_VALIDATOR_HANDOFF.md`.

### Paper-only unattended trial

The `paper-autopilot-v1` branch adds a separately labeled, preauthorized paper-only runner. It reconciles the bound account, scans the frozen 15-ETF strategy once per open session, prioritizes one deterministic exit and defers entries until that exit has reconciled, restates and requotes every exact order, and submits qualifying paper orders without a conversation-time confirmation. Automated approvals are journaled as `automation_approved`, never as `owner_approved`. Each symbol/action is attempted at most once per session and failures are not retried automatically.

The runner cannot change the universe, strategy, risk limits, broker hostname, or execution payload. It exits on a closed holiday, after an observed session closes, on a kill switch, or on reconciliation failure. This mode changes the manual approval model and therefore is not covered by the earlier independent validation record. It remains a paper experiment; the frozen v1 economics still underperformed both benchmarks.

## Audit trail

The event ledger logs every entry decision (including rejection), signal, simulated fill, position change, and daily P&L mark with deterministic IDs. The data manifest and artifact hash list make accidental changes detectable. Re-running against identical code, config, and pinned data must reproduce identical artifacts.
