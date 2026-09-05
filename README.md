# Deterministic ETF Swing Research v1

This repository is milestone 1 of a paper-only swing-trading project. It produces auditable historical research; it does not connect to a broker or place orders.

## Quick start

Use Python 3.11 or newer. Runtime dependencies are standard-library only.

```bash
make test
make fetch-data
make reproduce
```

`fetch-data` is the only networked step. It creates a checksummed snapshot under `data/pinned/`. `reproduce` verifies those checksums, runs the frozen in-sample and out-of-sample simulations plus both benchmarks, and writes `outputs/v1/dashboard.html`, full ledgers, trades, equity, exposure, metrics, and artifact hashes.

The measured conclusion is in `outputs/v1/milestone1_report.md`. V1 remains research-only even if every software validation passes; software correctness does not imply trading profitability.

## Plain-language operating model

- Market: 15 liquid US equity/sector ETFs.
- Direction: long or cash only; no options, leverage, shorts, crypto, or penny stocks.
- Starting account: $500 with fractional shares.
- Entry: ETF is above SMA(200) and RSI(2) is below 10 at a completed daily close; buy next open.
- Exit: fixed 2 x ATR(14) protective stop, close above SMA(20), 20-session time stop, or end of evaluation window.
- Risk: at most 0.5% planned loss per trade, 3% aggregate planned open risk, and a 2% daily realized-loss halt.
- Friction: spread, slippage, and fees are modeled on both sides.

Read `preregistration/v1.md` for the original frozen protocol, `preregistration/v1_post_validation_addendum.md` for non-strategy clarifications, `EXTERNAL_VALIDATION.md` for the independent audit record, and `methodology.md` for assumptions and limitations. The `src/swingbot/execution_contract.py` file documents a future broker boundary, but rejects every submission until separate validation is completed.

## Audit trail

The event ledger logs every entry decision (including rejection), signal, simulated fill, position change, and daily P&L mark with deterministic IDs. The data manifest and artifact hash list make accidental changes detectable. Re-running against identical code, config, and pinned data must reproduce identical artifacts.
