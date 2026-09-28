# Data and $500 feasibility follow-up — September 6, 2026

This is a data/execution replication of lite_reversal_v1, not parameter tuning or
unseen validation. Its original config, specification, source and results remain
unchanged. New GET-only requests use the configured personal Alpaca paper keys,
paper account host and official data host. No submissions, resets, settings
changes, purchases, subscription changes or live-money requests are permitted.

## Declared analysis

1. Read account cash/equity/buying power, restrictions, fractional configuration,
   LITE asset eligibility, open-order count and position count. Persist an allowlist
   excluding account IDs, names, keys and secrets. Missing fields remain unknown.
2. Fetch raw SIP LITE 1Min/5Min and SPY 5Min bars for the already-examined
   January 1–September 4, 2026 period. Every response is paginated with explicit
   bounds and completeness status, and each persisted file is hashed. Do not
   overwrite the original IEX snapshot or pretend SIP is IEX.
3. Validate positive finite OHLC/volume/VWAP, symbol/timeframe/feed/adjustment,
   ordering, duplicates, calendar dates and expected time grid. Report coverage.
   Re-run the original eight price/risk/cost/share combinations on complete SIP
   five-minute sessions using the unchanged v1 signal/sizing/exit functions.
4. On the stricter intersection of complete one-minute and five-minute sessions,
   compare five-minute versus one-minute exit replay. Signals remain five-minute;
   only execution-bar resolution changes. Entry remains idealized at the next open;
   this does not simulate latency, queue position or guarantee limit fills.
   Both intersection results are reported, not compared across different dates.
   Intraminute stop/target ambiguity remains stop-first. Time exit remains 15:55.
5. Quantify whole-share rejection: for each valid signal at fixed $500 cash,
   minimum capital for one share = max(entry_cap,
   (entry_cap - stop_after_cost)/0.005). Report cash vs risk failures separately.
   This is a sizing diagnostic, not a recommendation to deposit more money.
6. Request historical SIP quotes around **every** qualifying VWAP strategy signal
   in this SIP dataset, regardless of sizing, fill or outcome. Each window spans
   signal time - 2 seconds through signal time + 8 seconds. Do not cherry-pick wins.
   At a declared 1-second decision/transport delay use the most recent regular
   positive two-sided noncrossed quote no more than 1 second old. Report unknown
   when unavailable. Measure spread and whether ask fits the original 10-bps
   cap converted to a raw limit. This is an entry feasibility diagnostic, not
   a quote-driven P&L backtest or an assertion of an actual fill. Inspect earlier
   0.1-second and later 2-second points as fixed latency sensitivities; do not
   select whichever delay produces a fill. Keep nanosecond timestamp ordering.
7. Report same-period, same-time LITE-minus-SPY endpoint returns as descriptive
   controls. They are not risk-matched portfolios or executable strategy profits.

Historical data can be revised. Consolidated quotes are not queue position or
historical broker delivery times. Short quote windows do not validate protective
stop/target executions through a full day. Session completeness remains a
retrospective data filter, including the one-minute intersection. Corporate actions
and historical asset fractionability must be considered before generalizing
today's asset flag to all past dates.

Fractional simple DAY orders may address intraday sizing; the existing ETF adapter
deliberately rejects fractional orders and uses GTC OTO protection. Do not alter
that adapter or infer fractional bracket/OTO/OCO support from fractionable=true.
Conflicting or incomplete current vendor documentation must be labeled. Any actual
paper-order compatibility test or support message requires separate owner authority.
