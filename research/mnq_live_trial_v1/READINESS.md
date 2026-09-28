# MNQ research and proposed live trial: current decision

Updated 2026-09-09 UTC (evening of September 8 in Los Angeles).

**NOT READY for a live trial.** The work below is completed, but there are no
qualifying strategy trades on which to estimate profitability, and no futures
broker-paper evidence has been collected. Approval of preparation and data
spending is not approval of a live order.

## What we completed

| Work | Measured result |
|---|---|
| August history purchase | 20 trade sessions plus definitions; $20.63098720833659 additional provider usage. |
| Transport checks | 106 files, 266,419,940 compressed bytes; sizes and SHA256 hashes verified. |
| Trade data checks | 16,482,391 source records; 16,482,377 retained session trades; 14 boundary exclusions preserved in raw data. |
| Independent calculation | 7,800 minute bars checked; OHLC/VWAP/population variance and separate signal enumeration agree. |
| New fixed-rule screen | Zero complete setups in 19 evaluation sessions; August 3 is warmup. |
| Existing pilot | Zero complete setups in four evaluation sessions. |
| Additional free bridge check | August 31, using August 28 as its prior session: zero setups. Exploratory, not untouched validation. |
| Paper-versus-simulation tool | Offline comparison of signals, decisions, orders, fills, fees, positions, cash and clock differences; malformed/missing evidence blocks review. |
| Proposed loss controls | Offline arithmetic evaluator; proposed policy remains NOT_APPROVED and cannot send orders. |

Across the separate reports there are **24 distinct evaluated sessions and zero
complete setups**. These are sessions, not trades. Win rate, executable risk fit,
average net profit per trade and strategy drawdown are unknown. In the new
19-session screen, only one candidate minute crossed the three-standard-deviation
band; it did not touch the prior-session low or satisfy the reversal condition.

The original rules, configuration, protocol and reference fixtures/tests retain
their pinned hashes. Synthetic tests are software evidence only. Full exchange
completeness, broker execution and profitable performance are not established.

**114 software tests passed:** 54 research/import/quote tests, 39 paper-comparison
tests and 21 budget-evaluator tests. Independent review reproduced and closed
seven comparator cases and two budget cases; the trade importer also received
an overflow regression. See [validation record](VALIDATION.json) for artifact
fingerprints and the exact evidence boundary.

## Spending

- Approved additional research budget: **$56**. The user raised the portal's
  monthly limit to **$75**; that does not increase the research spending plan.
- Additional usage this batch: **$20.63**; unused additional budget: **$35.37**.
- Including the earlier $11.07 pilot, total provider usage is **$31.70**.
- No second-stage quote purchase is needed because the screen found no signals.
- No broker deposits, indicators, live subscriptions, or paper/live orders were
  purchased or submitted. Provider usage is reported separately from any
  credit application/card settlement and from trading P&L.

## Proposed limited trial — approval comes later

One MNQ maximum, at most two entry attempts per day, planned risk no greater
than min($12.50, 0.25% of day-start trial equity), daily loss pause at
min($25, 0.5% of day-start equity), and a separate **$50 total nonreplenishing
loss allowance**. Winners do not refill that total allowance. Review after
five completed round trips or five monitored sessions, whichever comes first.
Preserve the research's 5% high-water pause as an additional limit.

These are proposals and loss-trigger thresholds, not guaranteed maximum losses.
They still require durable state, actual broker enforcement, verified costs,
supervision, tested recovery and final approval naming the account, contract,
execution version, dates and budget. The offline evaluator never authorizes a
trade, even when a supplied snapshot fits its arithmetic.

## What still needs to happen

1. **Research decision:** this version does not support a live trial. Preserve
   its result. If pursuing a more frequent setup, specify a separate version
   before testing, reserve new evaluation data, and record every tested version.
   Do not loosen this version's rules or raise risk to force a trade. Further
   purchases are paused until a concrete research question justifies them.
2. **Broker choice and access:** the user's current futures account is
   unverified. The provisional API route is Tradovate/NinjaTrader; confirm actual
   eligibility and recurring costs before funding/subscribing for it. Historical
   Databento access does not provide broker-paper execution or a live feed.
3. **Actual paper integration:** implement the selected broker's adapter and
   capture real paper records plus the identical recorded market stream. The
   offline comparison tool is ready to receive canonical evidence; it is not
   a connected futures runner. Native stop/target semantics must be modeled
   honestly; a native target limit differs from the frozen delayed market exit.
4. **Evidence review:** assess held-out after-cost performance and uncertainty,
   actual fees/margin/sizing, paper fills and differences, protective orders,
   disconnect/restart/duplicate handling, and recorded loss pauses. Calendar
   time and a small trade count alone do not establish an edge.
5. **Final live approval:** only after the preceding evidence supports a trial,
   present the concrete account/contract/version/window and loss limits. This
   step has not been reached, and no live trial is authorized.

## Evidence files

- [August screen](../mnq_feasibility_v1/runs/trade-extension-01/REPORT.md)
- [Extra bridge diagnostic](../mnq_feasibility_v1/runs/bridge-01/REPORT.md)
- [Paper comparison and import contract](../mnq_paper_validation_v1/README.md)
- [Source-backed broker and trial proposal](BROKER_AND_TRIAL_PROPOSAL.md)
- [Budget accounting and limitations](TRIAL_BUDGET_EVALUATOR.md)
- [Beginner explanations](../../learnings.md)
