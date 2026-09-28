# LITE funded price-only comparison v1 — proposed research, September 23, 2026

This is a new, separate offline comparison. It does not alter or approve any frozen
strategy, send orders, use credentials, or select a live trading rule. The 2026 LITE
history has already been examined. Results are development diagnostics, not a
holdout or proof of future profit.

Input: the pinned, raw SIP five-minute regular-session LITE and SPY bars through
September 4, 2026. Source hashes and complete-session coverage are checked. No
historical point-in-time news text or receipt record is available. News effects,
earnings reactions, corporate-action-adjusted multi-day returns, broker quotes,
real fills and spreads therefore remain untested.

Each candidate starts with its **own** $4,000 cash ledger. At most one LITE position
is open; each new position debits at most $1,000, including entry cost. No margin,
reinvestment beyond that ticket, averaging down or automatic loss stop. The five
entry cases are deliberately simple comparators, not a claim to encode the owner's
discretionary judgment:

* `dip_10`, `dip_15`, `dip_30`: by the end of the first 10, 15 or 30 minutes,
  respectively, at least one completed bar has traded 1% below that day's 09:30
  opening price and the last completed bar closes below the opening price.
* `rebound_30`: the first half-hour has the same 1% dip, the last two completed
  closes have risen consecutively, and the final close is still below the open.
* `late_1500`: at 15:00, the 14:55 bar close is at least 2% below the open.

Information at each decision is limited to bars fully completed at that time.
Entry is modeled at the **next five-minute bar open**, plus 10 basis points per
side (also rerun at 25). That print is a proxy, not a guaranteed executable ask.
Historical volume is retained as a future sensitivity but is not used to tune a
post-hoc cutoff. The owner examples $800/$810–820 are not used as hindsight zones.

For a common comparison, a completed bar close at least 3% above cost-adjusted
entry schedules a sale at the following bar open. If still open at the end of
the tenth regular trading session including entry, sale is scheduled for the next
session open. There is **no automatic stop-loss**. These target/deadline values are
research assumptions, not owner-approved live or paper rules. A live manual-loss
invalidation, review responsibility and final deadline remain to be chosen.
Positions still open at the data cutoff are marked to the final close with an
estimated exit cost, and labeled unresolved rather than closed trades.

Cash-only, one-ticket LITE buy-and-hold and SPY buy-and-hold from the first
available 10:00 bar, plus all-cash, provide context. They use the same $4,000
ledger and $1,000 ticket, but have different turnover/risk and are not matched
causal counterfactuals. Do not add the separate arms' trades or P&L. Report
candidate days, occupied-day skips, closed trades, unresolved holdings, net
marked equity, worst daily drawdown and worst position excursion. Preserve adverse
outcomes and missed entries.

Before any paper execution, validate current IEX decision-time coverage against
the historical SIP logic and make a separate versioned broker adapter with
cash-only preflight, paper endpoint lock, idempotent order identifiers,
order/position reconciliation, and fail-closed behavior. Alpaca Basic real-time
equity data is IEX only, while historical SIP is available with a delay. A paper
fill is simulated and does not establish live execution quality.
