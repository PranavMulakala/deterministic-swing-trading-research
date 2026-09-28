# Frozen ORB comparison: implementation complete, edge not established

September 7, 2026. **Research verdict: NOT ESTABLISHED. Operational verdict:
NO-GO for this ORB version.** Do not equate these findings with the original ETF
strategy. No broker balance, trading permission or existing strategy was changed.

## What was completed

Implemented the frozen long opening-breakout/retest simulator, using one $5,000
cash portfolio per arm, integer shares, Decimal accounting, the prescribed
entry/stop/2R-target/time exit, next-session proceeds settlement, loss halt,
position/risk limits and both cost assumptions. A admits all lagged-eligible
names; B adds opening RVOL >= 2. The strategy rules were not optimized or changed.

Ran 28 ledger variants: two arms × two cost assumptions × seven scenarios
(primary, strict matched-complete-day diagnostic, and each of five stock omissions).
Recorded all 850 primary symbol-days per arm, including unevaluated future days
when a missing held-position minute prevents reliable accounting.

Alpaca reported no corporate actions in the supplementary query and confirmed
matching current asset identities. This is single-provider retrospective evidence,
not independent point-in-time security-master certification. The API explicitly
warns that action availability can be delayed. [Alpaca corporate actions](https://docs.alpaca.markets/us/v1.4.2/reference/corporateactions-1)

## Primary results

Costs below are **per-side slippage**, with another 1 bp per-side fee allowance.
An unresolved row has no defensible full-period balance or return.

| Arm | Slippage | Closed trades observed | Full-period result |
|---|---:|---:|---|
| A: all eligible | 10 bps | 1 | Unresolved: COHR, January 7 at 11:53 ET |
| B: RVOL >= 2 | 10 bps | 4 | Unresolved: FN, April 16 at 10:17 ET |
| A: all eligible | 25 bps | 2 | Unresolved: COHR, January 23 at 11:40 ET |
| B: RVOL >= 2 | 25 bps | 3 | $5,010.74; +$10.74 / +0.215%, bar proxy only |

The last row is **not a validated edge**: only three trades, one winner and two
losers, with no completed A comparison at that cost. The higher-cost scenario
also rejects more entries through the frozen cost-to-stop gate; it is a different
surviving opportunity set, not evidence that worse execution improves trading.
None of its three entries passes the measured one-second spread diagnostic below.

The strict matched-complete diagnostic retains only May 7, June 25, August 4 and
August 18. Neither arm trades on those dates. A zero-return four-date subset is
not proof the strategy avoids losses. All leave-one-stock-out paired comparisons
also encounter unresolved primary ledgers. Full-period paired confidence intervals
cannot honestly be calculated; they remain null, not fabricated from closed trades.

SPY and QQQ raw close-price changes over the evaluation interval were +12.96% and
+17.06%. These are descriptive price controls, exclude dividends, and are not
costed $5,000 benchmark portfolios or like-for-like comparisons with truncated
ORB runs. Complete machine-readable statistics retain this label.

## Why the bars stop the test

Re-queried all five distinct missing execution minutes encountered across the
variants, not just a convenient sample. **All five still return no one-minute
bar**, but their trade queries return 22–48 trades per window. Most have condition
`I` (odd lot). Alpaca's aggregation rules exclude odd-lot trades from OHLC updates,
so trading can occur without a qualifying price bar. This is evidence of an
aggregation limitation, not proof of a market halt or a failed bulk download.
[Alpaca aggregation rules](https://docs.alpaca.markets/us/docs/market-data-faq)

Missing windows: AAOI February 24 14:13; CIEN January 27 11:37; COHR January 7
11:53 and January 23 11:40; FN April 16 10:17. All times New York.

The frozen protocol explicitly makes missing held-position minutes unresolved.
Inventing flat bars, skipping those trades, or restarting the cash ledger would
change the experiment. The implementation instead preserves the open position,
cash and evidence, stops that ledger, and leaves terminal wealth unknown.

## Quote execution checks

Fetched SIP quote windows around **all 12 unique primary entry times** (13 modeled
entries across the four primary variants; one time is shared). Examined 100 ms,
1 second and 2 seconds after the modeled signal boundary, without choosing a
favorable delay after seeing results.

| Diagnostic delay | Usable fresh quotes | Within frozen 15 bps spread cap |
|---|---:|---:|
| 100 ms | 9 / 12 | 0 / 9 |
| 1 second | 9 / 12 | 0 / 9 |
| 2 seconds | 6 / 12 | 0 / 6 |

At one second the usable spreads range from 18.32–44.35 bps (0.183%–0.443%), versus
our maximum 15 bps (0.15%). The other three windows are missing a qualifying prior
quote or have a stale quote. Unknowns are not passes. These checks do not show that
every quote throughout the entire entry minute failed, nor that all future setups
would fail; they concern the exact bounded diagnostic instants observed here.

A quote is not a fill: original bar delivery, broker latency, queue position,
partial fills, protective order behavior and halt handling remain unvalidated.
Historical quote availability does not establish live SIP entitlement.

## Verification

- **273 tests pass:** 158 application tests plus 115 research tests. The current
  research total includes 27 new simulator/evidence tests added in this step.
- Independent event-accounting reconstruction passes for all 28 variants: 203
  event instances and 64 closed-trade instances, including repeated scenarios.
  This checks cash, quantity, costs, settlement chronology, risk and position
  limits; it is not 64 unique independent market trades or an external LLM audit.
- Two separate full runs produced **identical results for all 28 ledgers**.
- Frozen spec/protocol/collector/verifier hash tests pass. The prior LITE snapshots
  retain their recorded hashes. No tracked application file changed.
- Network collectors reject account/order paths and mutations before transport.
  No account query, order, purchase, deployment, commit or push was performed.

## Artifacts and reproduction

- [Frozen protocol](PROTOCOL.md) and [implementation decisions](IMPLEMENTATION_NOTES.md).
- [Latest report](runs/comparison-02/report.json), [every ledger](runs/comparison-02/results.json),
  [all prepared features](runs/comparison-02/prepared.json).
- [Quote and missing-minute evidence](runs/execution-evidence-02/report.json).
- `RESULT_PINS.json` pins code and outputs; raw provider data remains Git-ignored.
  Initial failed probes and the first run are retained, not erased or overwritten.

Offline rerun from the personal repository root, choosing a new output directory:

```sh
.venv/bin/python -m research.orb_comparison_v1.run --output research/orb_comparison_v1/runs/NEW-REPLAY
PYTHONPATH=src .venv/bin/python -m unittest research.orb_comparison_v1.test_data research.orb_comparison_v1.test_engine
```

## What would actually move this forward

The current work establishes an engineering result and a failure to establish an
economic edge. It does **not** accomplish a profitable, unattended trading bot.

The next experiment needs a separately versioned **quote/trade-based execution
model**, with explicit signal latency and handling of intervals containing only
price-ineligible trades. Keep the stock-selection and entry/risk hypotheses fixed.
Use the already available historical trade/quote endpoints before purchasing data.
Do not relax the spread limit simply to admit these rejected examples. A new
execution model must preserve this failed/inconclusive v1 evidence, rather than
silently rewriting its missing-minute rule. News or another indicator cannot
repair this accounting/market-data mismatch.
