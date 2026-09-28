# LITE opening-reversal v1: frozen exploratory experiment

Rules written on September 6, 2026 before running this experiment. The existing
2026 descriptive price analysis has already been seen. This is **not** an unseen
holdout, a historical preregistration, or approval to trade. Do not tune these
parameters in response to the results. A change is a separately recorded experiment.

## Scope and isolation

Offline research only: no broker imports, credentials, network, orders, live
scheduler, or changes to the existing ETF/paper strategy. Use the local snapshot
whose SHA-256 is pinned in `config.json`. Report hashes of inputs, configuration,
this specification, and engine source. No download fallback or automatic refresh.

The input is Alpaca IEX, five-minute, all-adjusted historical bars. These are
single-venue prices, not NBBO or official opening-auction prices. Adjusted historical
prices make dollar sizing illustrative until unadjusted execution data are verified.
Final historical bars may contain revisions unavailable at the original bar close.

## Coverage and causal clock

Only standard 09:30–16:00 New York sessions with all 78 regular-session bars and
positive finite OHLC, volume and vendor bar VWAP qualify. Reject duplicate,
out-of-order, naive, non-grid or malformed timestamps and malformed prices rather
than silently repairing them. Reject unknown in-period trading dates.

Full-session coverage is a **retrospective research quality filter**, not something
a live strategy could know at entry. Report every excluded session and why.
Results are conditional on that selected cohort; missing sessions are not proven
zero-return days. Never forward-fill missing bars or call this a live replay.

Bar timestamps represent the start of five-minute intervals. Signal decisions
use completed bars only. VWAP starts at 09:30, resets daily, and is
sum(vendor_bar_vwap * volume) / sum(volume) over completed regular-session bars.
This deliberately differs from Kenny Glick's premarket/multi-day anchors.

## Two price variants, fixed in advance

Common: first six bars (09:30–09:55) contain a low at least 1% below the 09:30
bar's open. Target is that opening reference. One order attempt per session,
no averaging down, no shorting, no overnight positions, no leverage.

1. `dip`: after 09:55 bar completes at 10:00, attempt an entry. Stop is the
   first-half-hour low minus 0.05% of the opening reference.
2. `vwap_retest`: scan completed bars starting with the 10:00 bar. A reclaim
   requires prior close <= prior completed VWAP and current close > current
   completed VWAP. The immediately following bar must touch/cross its own final
   VWAP with its low, close above that VWAP, and have a low no lower than the
   reclaim bar's low. Both signal bars must close below the opening reference.
   A failed retest discards the arm; a new reclaim can arm another. Stop is the
   lower of the reclaim/retest lows minus 0.05% of the opening reference.
   The last retest bar starts at 10:50; the latest entry is 10:55. First completed
   qualifying retest ends the search, including when sizing/fill checks reject it.

Using final retest-bar VWAP to characterize its low is a completed-bar pattern,
not a claim that the low touched the contemporaneous intrabar VWAP.

## Order intent and fills

At signal completion compute a maximum **all-in** entry price before looking at
the next bar. Let c = cost_bps / 10000, S = stop*(1-c), T = target*(1-c), and R=1.5.

entry_cap = min(signal_close*(1+0.002), (T + R*S)/(1+R)).

Quantity is chosen at signal time, not retrospectively at the next open:

q = floor(min(cash/entry_cap, (0.005*cash)/(entry_cap-S))) for whole shares.

The fractional diagnostic floors to 0.000001 share, with the same cap and risk.
It is explicitly hypothetical; broker support/order protection is not established.
Whole shares are the primary account-feasibility result. Each variant/cost/share
mode has its own $500 compounding ledger over the coverage-qualified sessions.
This is a conditional hypothetical ledger, not a prediction of account value.

On the immediately next bar, require stop < raw open < target and
raw open*(1+c) <= entry_cap. Otherwise cancel, with no intrabar retry. This is an
idealized open-only marketable limit model; there is no order queue, latency or
partial-fill model. Charge c on entry and all exits as an aggregate cost allowance,
not measured spread or a specific fee schedule. Baseline 10 bps per side; stress
25 bps per side. These are scenarios, not asserted realistic upper bounds.

Stops are active on the entry bar, which cannot contribute to the entry signal.
A later opening gap below the stop exits at that worse open less sell costs.
Otherwise a stop touch exits at stop less costs. If stop and target could both
execute in one bar, stop takes precedence and ambiguity is counted.
For a target fill require strict penetration beyond target by 5 bps; a mere
touch does not fill. Opening above that threshold fills at the target, with no
positive gap improvement. Limit-fill assumptions remain unverified even with
penetration. At 15:55 exit at that bar's open less costs (gap stop has precedence),
without consulting the 15:55 high/low/close. No partial exits or trailing stops.

Cash and P&L use unrounded floats internally; presentation rounds cents. Entry
debits and exit credits reconcile independently. Stops define planned risk, not
a guaranteed maximum loss. Gaps can exceed the planned 0.5% account risk.
One attempt per day means a separate same-day entry-loss halt is redundant.
This is not a settlement, margin, broker-order or account-eligibility simulator.

## Comparisons and reporting

Run both price variants under both costs and both share modes; publish **all
eight** results with no winner selection. Report signals, rejections by reason,
trade ledger, equity ledger, net/gross P&L, modeled costs, wins, profit factor,
planned-risk multiples, worst trade, realized and bar-low mark drawdown, ambiguous
exits, monthly outcomes, and reconciled invariants.

Also report the unconditional 10:00-open to 15:55-open LITE return on the same
coverage cohort, and on the first-half-hour-dip subset. These are all-in return
diagnostics, not risk-matched portfolios. They help distinguish a bounce effect
from LITE's generally rising year. Cross-stock/market-adjusted controls need
additional matching intraday data and are not implemented here.

Provide a fixed-seed calendar-week block bootstrap of average trade R, resampling
weeks including no-trade weeks. This is descriptive uncertainty under this sample,
not a cure for selection bias or a proof of future profitability. Months are
descriptive, never labelled out-of-sample. No significance-based parameter tuning.

## News: explicitly blocked, not silently replaced

The snapshot has article IDs, links, symbols, and creation/update timestamps, but
no original headlines/content or historical first-received timestamps. Therefore
**do not run a news/sentiment filter or call missing news neutral**. Report this
third experiment as BLOCKED_DATA. Next step requires point-in-time event versions,
availability timestamps, deduplication and a frozen event-classification rule.
Do not scrape retrospective headlines now and assign them earlier availability.

## Decision

Deliver the experiment and measured evidence, not a profitability guarantee.
Deployment status remains RESEARCH_ONLY regardless of favorable results. Before
promotion: matching consolidated/raw trades and quotes, missing-data and realistic
fill checks, point-in-time news if used, actual $500 broker feasibility, and a
genuinely unseen evaluation of unchanged rules. A few live days can test plumbing,
not establish a durable edge.

References:
- https://docs.alpaca.markets/us/docs/market-data-faq
- https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders
- https://www.humbledtrader.com/blog/vwap-strategy-secrets-boosting-your-trading-skills-to-the-next-level/
- Supplied Kenny Glick transcript: https://www.youtube.com/watch?v=pq1ZMd9qSic
