# Frozen plumbing protocol: agentic-options-shadow-indicative-7500-v1

This is a separate, no-cost operational experiment using Alpaca's free
**indicative** options feed and free IEX stock feed. It does not amend or
replace `agentic_shadow_v1`, whose OPRA hypothesis and artifacts remain
unchanged. Indicative quotes are modified derivatives of OPRA quotes and
indicative trades can be delayed. Therefore every output is
**PLUMBING ONLY — NOT VALID FOR PROFIT, EXECUTION, OR AGENT-EFFICACY ANALYSIS**.

The purpose of this version is limited to verifying authenticated read-only
collection, pagination, normalization, provenance, atomic handoff, scheduling,
ledger recovery, report generation, and isolation from broker-order authority.
It may simulate decisions and fills to exercise those paths, but its P&L and
fill results must never be treated as market evidence or compared with the
frozen OPRA experiment. No broker order endpoint, subscription change, model
API, or real-money operation is present.

Frozen before any return evaluation. Capital is exactly $7,500 independently in
EACH comparison arm; these are counterfactual alternatives, not a $22,500 fund.
Hypothesis: modest intraday momentum in SPY/QQQ continues far enough for a short
holding period long option to overcome bid/ask spreads and fees. This hypothesis
is unvalidated and the $75 budget may result in no eligible contracts.

At a supplied observation between 10:00 and 14:00 Eastern on a verified regular
session, examine three consecutive completed five-minute underlying bars. Require
strictly increasing closes and at least +30 bps first-to-last for a call, or
strictly decreasing closes and at most -30 bps for a put. Require the latest
underlying price to remain on the same side of the final bar close. Universe is
SPY and QQQ; no signal inference from news or missing observations. Entry bars
must end within five minutes of observation. No warmup substitutions.

Select standard unadjusted US ETF options, 100 shares, USD, American style,
7–14 calendar days to expiry, strike from at-the-money through 1% out-of-the-money.
Require positive bid, ask >= bid, quoted spread <= $0.05 AND <= 15% of ask,
positive displayed size, open interest >= 500 and session volume >= 100.
Sort eligible contracts by expiry, distance from underlying, then exact OCC symbol.
One position or pending entry per arm. Select the same eligible contract before
agent filtering. No averaging down or additional lots. Buy exactly one contract
only when (ask + $0.01) * 100 + $0.65 entry + $0.65 reserved exit fee <= $75.
No borrowing, short options, spreads, adjusted contracts, expiry-day entries or
underlying earnings during the holding window. ETFs must have explicit sourced
not-applicable earnings status; missing event/corporate-action/calendar coverage
blocks entry. Corporate-action uncertainty blocks entry. Entry must occur before
that day's close minus 15 minutes; no overnight entries are planned.

All three arms see one byte-identical normalized packet and candidate. Baseline
accepts the rule signal. The mock analyst returns a schema-bound accept/abstain
scorecard; the mock critic accepts or vetoes that same proposal. Mock defaults
accept unless supplied mock responses abstain/veto; these test plumbing, not AI
skill. There are no model calls or paid usage. All proposals cite packet evidence,
include thesis, competing explanation and confidence (not win probability), and
are saved durably BEFORE a later observation can fill an intent. No model field
can control symbol, quantity, cash, price, risk thresholds, exits or accounting.
Malformed or extra authority-like fields reject that arm. Learning writes only a
separate suggestion; changes require a new version, held-out review and approval.

Execution is conservative touch simulation, not a claim of executable fills.
An entry IOC can fill only at the first subsequent fresh observation with a quote
strictly later than decision, after >=1 second and within 60 seconds; ask plus
$0.01 must be no greater than the saved limit. Pay ask plus slippage, never midpoint.
No quote, insufficient displayed contracts, price movement or timeout => unfilled.
One listed contract is indivisible: a reported fractional fill is invalid and
must not become exposure. Exit at bid minus $0.01 (floor zero), less $0.65, with
positive displayed bid size; use the next fresh quote after the exit decision.
No fill is manufactured when liquidity vanishes. Missing quotes keep exposure
unresolved and entries paused. Exit intents persist across restart and retry only
on later fresh observations. Displayed size does not guarantee actual execution.

Mark open longs at bid less $0.01 and reserved exit fee, floored to zero; unknown
marks are shown as unknown, with a separate zero-value conservative risk mark.
Exit on >=30% option-premium loss, >=50% premium gain, 120 elapsed minutes, or
15 minutes before the session close, whichever is first observed. Gaps/late polls
can miss thresholds; pauses are interventions, not loss guarantees. At entry,
record simulated do-not-exercise (DNE). If an unfilled exit carries to expiry,
record an operational breach and model expiry lapse at zero under this DNE policy,
including possible forfeited intrinsic value (unknown without official settlement).
Long holders are not assigned short-option obligations; exercise could otherwise
create 100-share exposure. No real DNE instruction or exercise is submitted.

Daily loss compares marked equity to previous day's final durable mark (starting
capital on the first day). Pause new entries for the remainder of a session at
-$150; latch experiment pause permanently at $375 peak-to-trough drawdown.
Conservative unknown marks also pause entry. Always continue existing exit and
expiry management. Resetting a day cannot erase experiment drawdown. Cash includes
actual simulated entry/exit fees; spread/slippage attribution is informational,
not deducted twice. Infrastructure/data/model costs are separately disclosed;
mock incremental model cost is zero, real operating cost is unverified.

Packets must retain contract metadata, bid/ask/size, market and receipt timestamps,
underlying bars/quote, source/feed, original payload hash, timestamped news with
source URLs, and complete event/calendar coverage. Every used item must have
been both published and received by the decision time. Future revisions are not
silently backdated. Nonmatching, stale, missing, conflicting or future data fail
closed. Provider responses are retained separately in compressed archives and
bound into normalized objects by SHA-256. Pagination must terminate without a
repeated token. Derived fields, including the conservative expiry cutoff and
standard-contract classification, must record their basis. Alpaca's published
corporate-action timeliness warning remains a coverage limitation even when a
fully paginated response is empty.

Separate fixture and indicative ledgers; indicative packets must arrive within
60 seconds of wall clock and every provenance feed must be one of the explicit
Alpaca indicative/IEX/calendar/news/corporate-action sources. Offline replay
cannot claim forward operational readiness.

Operational checkpoint: five complete scheduled market sessions with successful
producer and consumer runs, complete pagination, bounded response sizes, current
packets during the collection window, and no credential or order-capability
leakage. Report reliability, latency, missing data, rejection and recovery paths.
Do not interpret P&L, fills, win rate, drawdown, or arm differences. Any OPRA
evaluation remains a separate future experiment. Real-money options remain NOT
AUTHORIZED.
