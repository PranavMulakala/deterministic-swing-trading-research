# V1 post-validation addendum

Recorded: 2026-09-05  
Applies to audited commit: `0cf291235e5e75d185ddac3285be6f4ca2bc7a3f`

This is a transparency addendum, not a retroactive modification of the frozen strategy. It changes no universe, indicator, threshold, sizing rule, cost assumption, date split, trade, equity value, or benchmark definition. The original preregistration remains preserved in Git commit `877fc12`.

## Evaluation-boundary exit

The backtest forcibly liquidates any position still open on the final date of each evaluation split at that date's adjusted close, with modeled sell-side costs. This produces comparable terminal cash equity. It is not a live strategy signal or an instruction for future paper execution. Five reported trades used this exit across the two evaluation splits.

## Daily-loss-halt observability

The 2% daily realized-loss halt produced zero rejections in the frozen history. The rule can reject pending entries after losses from scheduled open exits; a post-audit integration test exercises that path. Daily bars cannot establish whether an intraday protective stop happened before another decision at the same timestamp. Future paper execution must calculate the halt from actual broker fill ordering.

## Small-account signal capacity

A qualifying signal can still produce zero quantity when existing holdings consume the $500 cash balance. Such decisions are logged as `zero_quantity` rejections and do not become trades. Generated metrics now state their counts and percentages explicitly.

## Benchmark interpretation

The preregistered momentum baseline intentionally performs full monthly liquidation and repurchase, including names that remain selected. Generated benchmark metrics now show modeled execution costs and the difference from a zero-cost shadow calculation. This quantifies, but does not revise, the frozen conservative cost treatment.
