# MNQ feasibility report

**Status: SYNTHETIC_SOFTWARE_CHECK_ONLY**

Starting simulated cash: $5,000.00. Initial per-entry planned-loss budget: $12.50.

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

**If this is SYNTHETIC, every figure below is a software demonstration, not trading evidence.**

| Scenario | Patterns | Risk known | Risk fits | Fits / all patterns | Entries | Closed net P&L | Ending equity | Observed max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fee2_slip0 | 1 | 1 | 1 | 100.0% | 1 | $25.50 | $5025.50 | $2.50 |
| fee2_slip1 | 1 | 1 | 1 | 100.0% | 1 | $24.50 | $5024.50 | $3.50 |
| fee2_slip2 | 1 | 1 | 1 | 100.0% | 1 | $23.50 | $5023.50 | $4.50 |
| fee4_slip2 | 1 | 1 | 0 | 0.0% | 0 | $0.00 | $5000.00 | $0.00 |

Read report.json for every screen, rejection, trade, mark, and data-quality issue.
Unknown quotes remain in the total-pattern denominator. Known-risk fit rate is also reported.
Observed drawdown is only a lower bound when a position crosses a data gap.
Different scenarios may admit different trades. Their totals are not matched-trade cost comparisons.

## Boundaries

No broker connection or orders. No strategy profitability or live-trading approval.
Data/platform subscriptions, taxes, and broker margin constraints are not included in the trading ledger.
Subtract actual fixed expenses separately before assessing the economics of the project.
A historical input label and coverage declaration do not prove the vendor export is complete.
The protocol and source hashes are recorded in report.json. Do not replace a prior output directory.
