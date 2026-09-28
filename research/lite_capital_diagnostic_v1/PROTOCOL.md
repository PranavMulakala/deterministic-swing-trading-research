# Historical LITE capital diagnosis — September 9, before market open

Question: does removing the $500 whole-share sizing obstacle justify a live pilot?
This diagnostic was specified after seeing the existing 2026 studies, but before
running these larger-capital historical comparisons. It is NOT unseen validation,
not a new selection rule, and not part of the frozen September 9 forward sample.

Use only the pinned January 2–September 4 raw SIP snapshots already on disk.
Keep original LITE entry/exit, stop, reward/risk, sizing fraction, cost rules and
random seed unchanged. Evaluate ALL $500 control, $5,000 and $10,000 portfolios
with dip/VWAP-retest entries and 10/25-bps costs, whole shares only. No optimization,
longer holding periods, new indicators, news filter, or winner selection.

Publish 12 full-coverage five-minute cases. On the exact intersection of complete
one-/five-minute sessions, publish 12 five-minute and 12 one-minute execution cases.
Five-minute signals stay unchanged. Do not compare different date sets as if only
execution resolution changed. No missing bars are fabricated; excluded days are
reported. Whole-day coverage is a retrospective condition, not entry-time knowledge.

Tests: immutable inputs/outputs, complete fixed matrix, unchanged non-capital
config, exact matched dates, no cross-account/cross-scenario cash sharing, repeat
determinism, and an independent Decimal reconstruction of every daily ledger and
trade debit/credit/cost. Fixtures cover tampered/missing trades, risk/cash breaches,
and the distinction between planned risk and larger gap losses. Existing signal,
stop/target and partial-fill tests remain applicable to their own engines only.

Report cash, P&L, trades, rejection counts, win rate, mean R and uncertainty where
the parent provides them. All scenarios remain visible; repeated scenarios are
not independent samples. One-minute bars are not quote-level fills or broker
latency, and assumed costs are not certified real-execution bounds. Capital
feasibility does not establish positive expected return. No live authorization,
account access, API request, cloud change or automatic promotion occurs here.
