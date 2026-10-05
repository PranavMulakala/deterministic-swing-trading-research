# Test #11: Kevin's "95% Fibonacci rule" and "Faker level": results (October 5, 2026)

- **Plan:** [FIB_95_RULE_TEST_PLAN_20261005.md](FIB_95_RULE_TEST_PLAN_20261005.md), committed (92214f1) before any result.
- **Code:** `research/fib_95_test_v1/` (`run.py`, 8 unit tests, `verify.py`, plus `breakdown.py`, information only, written after the main run).
- **Results:** `output/fib-95-test-results.json` (+ `.provenance.json`) and `output/fib-95-breakdown.json`.
- **Data:** QQQ and SPY, 2016 – Oct 2, 2026, as 1-hour candles (~16,200 each) and daily candles (~2,700 each). Up and down moves both count.
- **Independent recount:** QQQ 1-hour, 88.7%: identical counts (589 reversals, 14 continuations, 1 ambiguous, 1 unresolved). The first recount differed by one; the cause was the recount itself letting one candle be both the start and end of a move, which the plan's "low → the next high" excludes. Fixed in the recount, then matched.

## Verdict: NOT supported. The "95%" number is roughly right, but nothing about Fibonacci makes it so, and the "Faker level" claim is backwards.

| Pre-declared check | Needed | Result |
|---|---|---|
| **A.** Reversal rate after 2 closes beyond 88.7% | ≥ 90% in all 4 | **✓** QQQ-1h 97.7%, QQQ-daily 95.5%, SPY-1h 97.4%, SPY-daily 100% |
| **B.** 88.7% beats the placebo line (85%↔90%) | ≥ +2 points on average | **✗ +0.16 points.** Any line that deep does the same |
| **C.** 76.4% "Faker" snap-back beats the placebo line (70%↔80%) | ≥ +2 points on average | **✗ −0.41 points** |

### Claim 1, the 95% rule: same result at made-up levels (2 closes, reversal rate)
| | 80% | 85% | **88.7%** | 90% | 95% |
|---|---|---|---|---|---|
| QQQ 1-hour | 95.6 | 96.3 | **97.7** | 98.0 | 99.3 |
| SPY 1-hour | 93.8 | 95.5 | **97.4** | 98.2 | 98.5 |
| QQQ daily | 92.9 | 95.5 | **95.5** | 95.5 | 95.4 |
| SPY daily | 93.3 | 97.7 | **100.0** | 100.0 | 100.0 |

The rate simply rises the deeper the line, because price is closer to the start of the move. **88.7% sits exactly where a plain line between 85% and 90% would put it.**

### Why the "95%" is mostly automatic (information-only breakdown)
- **About 3 in 4 of the 1-hour signals fired after price had already closed beyond the start of the move:** QQQ 458 of 604, SPY 354 of 496. The "reversal" had already happened, and the signal just announced it. Daily: about half.
- **Genuine forecasts only** (signal close still between 88.7% and the start): 92.5% QQQ-1h, 94.4% SPY-1h, 90.0% QQQ-daily (30 signals), 100% SPY-daily (16 signals). That's close to what you'd expect from price simply being near the start, and similar at 85% and 90%.
- **Trading it pays nothing.** Short (or buy, for down moves) at the signal, take profit at the start of the move, stop at the end:
  - wins averaged about **+0.2%** and losses about **−2.5%** (1-hour);
  - net about **0.00% per trade before costs** on QQQ-1h (−0.02% after a 0.02% round-trip cost), +0.016% after costs on SPY-1h;
  - **−0.35% per trade** on QQQ daily. Only SPY daily was positive (+0.59%, 16 trades, too few to mean much).

### Claim 2, the Faker level: backwards
After the first close beyond the level, how often did price snap back inside 61.8% before 2 closes beyond 88.7%?

| | 70% | **76.4%** | 80% |
|---|---|---|---|
| QQQ 1-hour | 29.0% | **22.0%** | 17.6% |
| SPY 1-hour | 33.9% | **26.2%** | 21.8% |
| QQQ daily | 35.4% | **26.0%** | 21.6% |
| SPY daily | 34.6% | **28.0%** | 26.5% |

- **A close beyond 76.4% snapped back only 22–28% of the time.** About 3 in 4 times it kept going to full invalidation.
- So "price routinely breaks this level … before snapping back" is the opposite of what happened on QQQ and SPY.
- And 76.4% behaved exactly like its neighbours. It isn't a special "trap" level.

## Plain takeaway
- The "95%" is real but **automatic:** once price has given back ~89% of a move, it usually reaches the start, very often because it already has.
- **88.7% is no better than any other deep line.**
- **Trading it makes roughly nothing,** because you win tiny amounts and lose big ones (the same pattern as CRT and selling puts).
- **The "Faker level" advice would have kept you in losing trades about 3 times out of 4.**
- **Test record: 11 pre-declared tests; none beat holding SPY.**
