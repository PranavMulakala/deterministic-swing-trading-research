# Frozen first ORB comparison

September 7, 2026. This freezes a **research comparison**, not broker execution.
`spec.json` contains the numerical constants; this document supplies their exact
semantics. Both are pinned in `FREEZE.json`. A change requires a new version and
an explanation; never replace this freeze after observing strategy results.

## One question, two arms

Does first-five-minute relative volume improve a fixed long breakout/retest rule
in the five-name LITE / COHR / CIEN / FN / AAOI pilot? A uses every lagged-eligible
name. B requires the same eligibility plus opening RVOL >= 2. Nothing else changes.
Each arm has ONE $5,000 portfolio, not $5,000 per ticker. The original $500 ETF
strategy, broker balance, authorizations and LITE dip experiment are untouched.

This chooses the **retest** entry described in the earlier brief/video, not the
published paper's direct stop-entry breakout. Direct breakout versus retest is
a later experiment. SPY/QQQ are descriptive market controls, never extra candidate
stocks. With only five names, top-five ranking cannot prune B further; this is
principally a test of the RVOL threshold, not proof of market-wide top-N selection.

## Data and observation time

Use raw consolidated SIP bars for November 2025 through September 4, 2026.
November/December are warmup, not scored. Use calendar-specific regular sessions
in America/New_York, respecting DST and early closes. Bar timestamps mark interval
START: 09:30 five-minute data are not available for a decision until 09:35 or later.
Historical bars can be revised and do not supply original receipt timestamps.
Therefore the initial replay is explicitly a **finalized-bar proxy**, not an
as-received live simulation. A quote replay must also account for signal latency.

All 2026 results are development evidence: LITE and peer movement have already
been examined. This freeze does not retroactively make that history out of sample.
No prospective start is asserted until a running collector proves data delivery.

Before economic simulation, reconcile instrument identity and corporate actions
over warmup plus evaluation. Exclude a symbol-session if a split/reorganization
falls in its 20-session lookback or today; do not silently mix pre/post-split price
or volume. If action coverage is unknown, that eligibility is unresolved, not a
verified pass. Raw data and symbol-asof pinning alone do not prove action coverage.

## Eligibility and selection

Use the immediately preceding 20 exchange sessions, with no skipping missing
sessions to reach a desired count. Previous close is the last regular five-minute
bar close. Daily dollar volume is sum(bar volume * bar VWAP) over that session.
ATR is the arithmetic mean of the immediately preceding 14 daily true ranges:
max(high-low, abs(high-prior_close), abs(low-prior_close)). It needs one additional
prior close. Include real early-close sessions in lagged indicators, not in entry
evaluation. Require complete five-minute regular-session bars for each lagged
daily input; do not forward-fill. Current-day full-session completeness must
**never** be used to decide pre-entry eligibility.

Require prior close >= $10, median prior-20 dollar volume >= $50m, ATR / prior
close >= 0.02. Require valid positive opening volumes on all immediately prior
14 sessions for RVOL in **both** arms (common information-coverage population).
RVOL = today's 09:30 five-minute volume / mean(prior 14 matching volumes).
Freeze candidates once the opening range is complete; no later re-ranking.
B ranks by RVOL, then lagged median dollar volume, then ticker. Never fill empty
slots with an ineligible name. Opening candle need not be bullish.

## Exact common entry/exit rule

Let H/L be the first five-minute high/low, and S=(H+L)/2-$0.01. H must exceed L.
Beginning with the 09:35 five-minute bar, take the **first** completed close > H
as breakout. A retest must be one of the next three five-minute bars, with
open > H, low <= H (exact touch counts), close > H, and low > S. Use the first
qualifying retest. If price touches/breaches S in any intervening five-minute bar,
invalidate the attempt (including a bar otherwise qualifying as a retest).
Confirmation must finish by 11:00 inclusive. No second breakout cycle that day.

The bar-proxy entry is the immediately next one-minute bar's open plus adverse
slippage. Never enter at the already-observed confirmation close. Do not search
later minutes for a better fill. Skip if the entry minute is absent, its opening
price is <= S, or the slippage-inclusive price exceeds confirmation close*1.005.
This is a one-minute attempt at a capped entry, not a guaranteed limit-order fill.
An unsuccessful attempt consumes that symbol's one attempt for the session.

Stop stays S, target is actual simulated entry + 2*(entry-S). No trailing,
averaging down, overnight holds or "wait until recovery". Stop exits receive
adverse slippage on min(S, minute open); a target exit is credited at target minus
slippage, with no favorable price improvement. At a minute open, first process
opening-gap protective exits for previously held positions, then any scheduled
time exits, then new entries. Only afterward process intraminute protective
touches on positions still held (including new entries). If both levels occur
within that minute and neither already exited at its open, stop wins. A target
already crossed at the open exits before a later intraminute stop; do not use
future minute highs/lows to override a completed opening exit. The time exit is
at the 15:55 minute open minus slippage. For any
held position on a short session, use five minutes before the official close.
Do not originate entries on early-close days. Missing minutes during a position
make its outcome unresolved; never silently value or delete such a position.

## Cash, costs, competition

Run both arms at 10 bps adverse slippage per side plus 1 bp per-side fee allowance;
repeat BOTH at 25 bps + 1 bp. These are explicit approximations, not measured fees
or observed spreads. Report both regardless of profitability. Apply costs to all
entries/exits, including stops and time exits. No commission-free assumption that
trading is costless. Planned round-trip cost per share = entry price *
2*(slippage_bps+fee_bps)/10000; skip if this exceeds 20% of entry-S.

Equity at each decision uses cash (including unsettled receivables) plus open
positions at the last **already completed** one-minute close; before a first
minute completes use entry value. Risk budget is 0.5% of that equity. Size down to
whole shares using the minimum of settled cash affordability (including entry
fees), remaining 1% aggregate planned risk, and the per-entry risk budget.
Per-share planned risk is entry minus slippage-adjusted stop fill plus both fee
allowances. Stop slippage can exceed this plan in gaps: it is NOT a loss guarantee.
Existing-position planned risk stays its entry-time value until closed.

At most two positions. Only exits knowable at the minute open can free position
capacity before that minute's entries; a later intraminute exit cannot. Sale
proceeds become spendable only at the next exchange session. Simultaneous entry
priority is lagged median dollar volume descending then ticker in **both** arms,
not eventual outcome. No fractional shares, margin or shorting. No unsettled-cash
reuse. At net realized session loss >= 2% of start-of-session equity, reject new
entries for the remainder of that day; continue protective exits. Report actual
halt firings, zero-quantity and insufficient-cash rejections. This conservative
settlement model is a research assumption, not certification of broker rules.

## Required reporting and acceptance

Account for every symbol-session: eligible, each rejection, no setup, attempted,
filled, unresolved. Full-day coverage is a retrospective data-quality flag only.
Do not hide missing post-entry data by reporting only complete winning trades.
Run a strict matched-complete-days diagnostic separately, label selection bias,
and report excluded days; it is not the primary portfolio ledger.

Primary contrast: B minus A net portfolio return. Also report trade count, net
expectancy, win/loss size, drawdown, worst loss, cash occupancy, exposure, fill and
rejection counts, and concentration by ticker/month. Show paired differences
by session and a 95% paired moving-block-bootstrap interval: resample consecutive
five-session blocks with replacement from the observed daily return-difference
series, concatenate/truncate to original length, 10,000 samples, seed 20260907;
use percentile bounds for mean daily difference. This is uncertainty on the
daily contrast, not a confidence interval for compounded terminal wealth.
Show leave-one-symbol-out sensitivity without selecting a new winning universe.

Do not call RVOL beneficial unless the direction survives both cost scenarios,
the interval excludes zero in the favorable direction, removal of any one ticker
does not reverse the portfolio contrast, and all candidate sessions/positions
are reconciled. Failure means negative or inconclusive evidence, not permission
to optimize thresholds. Passing is still only development evidence, not proof of
future profit or readiness to trade.

Bar data cannot implement the <=1 second quote-age and <=15 bps spread gates.
Those remain mandatory for an execution-quality validation, with quote sizes,
halts, partial fills, event ordering and latency. Do not treat unknown quotes as
passing. News is not a selection input in either arm; missing news is unknown,
not neutral. News classification and any extra indicator are separate versions.

## Provenance references

- [Alpaca historical bars](https://docs.alpaca.markets/us/reference/stockbarsingle-1): raw adjustment, SIP, pagination and symbol-asof semantics.
- [Original ORB study](https://concretumgroup.com/wp-content/uploads/2026/02/A-Profitable-Day-Trading-Strategy-For-The-U.S.-Equity-Market.pdf): hypothesis source, not a replication target.
- [Earlier local research brief](../ORB_STOCK_SELECTION_RESEARCH.md): choices and limits preceding this freeze.

No backtest profitability result is represented by this document. The next step
after data acquisition is action reconciliation and implementation of this exact
comparison, followed by quote execution checks, not another parameter search.
