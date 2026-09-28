# MNQ feasibility report

**Status: BLOCKED_MISSING_MNQ_DATA_AND_VERIFIED_COSTS**

Starting simulated cash: $5,000. Initial per-entry planned-loss budget: $12.50.

## What we can calculate without market data

These fee/slippage scenarios are assumptions, not a verified broker quote.

| Scenario | Fee for entry + exit | Extra slippage each side | Maximum quote-to-stop distance |
|---|---:|---:|---:|
| fee2_slip0 | $2.00 | 0 ticks | 21 ticks / 5.25 points |
| fee2_slip1 | $2.00 | 1 ticks | 19 ticks / 4.75 points |
| fee2_slip2 | $2.00 | 2 ticks | 17 ticks / 4.25 points |
| fee4_slip2 | $4.00 | 2 ticks | 13 ticks / 3.25 points |

The observed spread is already included by buying at the ask and selling at the bid.
This is a maximum allowable distance, not a recommended stop placement.

## Answers to the three questions

1. Percentage of signals fitting the budget: **unknown; no MNQ tape supplied**.
2. Performance after realistic costs: **unknown; verified broker fees and MNQ quotes missing**.
3. Losses and drawdowns under pause rules: **unknown; no real replay performed**.

## Boundaries

No broker connection or orders. No strategy profitability or live-trading approval.
Data/platform subscriptions, taxes, and broker margin constraints are not included in the trading ledger.
Subtract actual fixed expenses separately before assessing the economics of the project.
A historical input label and coverage declaration do not prove the vendor export is complete.
The protocol and source hashes are recorded in report.json. Do not replace a prior output directory.
