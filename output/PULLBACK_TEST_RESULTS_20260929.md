# Course pullback strategy: results of the pre-declared test (September 29, 2026)

- **Plan:** [PULLBACK_TEST_PLAN_20260929.md](PULLBACK_TEST_PLAN_20260929.md), committed before any result was computed (07630a1).
- **Code:** `research/pullback_test_v1/` (13 offline tests).
- **Results:** `output/pullback-test-results.json`.
- **Data:** the same Alpaca daily bars as the breakout test: 5,259 US stocks, 2016 to Sept 28, 2026. No new download.
- **Source:** "Trading for Beginners Part 1", 1:21–1:50. The strategy is: after a pullback, trade the first candle that closes back past the prior day's range. The stop goes at the pullback extreme and the target at the run's best close.

## Verdict: the long side (the one that counts) failed all three checks. No edge shown.

| Check | Needed | Long side (counts) | Short side (info only) |
|---|---|---|---|
| Profit factor (gains ÷ losses) | at least 1.3 | **0.97** | 0.77 |
| Profitable in 2016–2020 and in 2021–2026 | both above 0 | **−1.9%** and **−15.2%** | −56.1% and −48.0% |
| Worst drop in account value | at most 25% | **−42.0%** | −80.7% |

## What happened on the long side
- **$100,000 became $83,200 (−16.8%)** from Oct 2016 to Sept 2026. Holding SPY returned **+348.6%** over the same data.
- **1,817 trades, about 170 a year,** held about 9 days on average.
- **42.5% won.** The average win was +7.9% ($703) and the average loss −5.8% ($536).
- **The video's own formula:** (1 + 703 ÷ 536) × 0.425 − 1 = **−0.02**, just below zero. Each trade lost on average 0.02 of what it risked.
- **How trades ended:**
  - Stop: 888. Gap through the stop: 146.
  - Target: 653. Gap through the target: 102.
  - 60-day time limit: 28.
- **Up and down years:**
  - Good: 2017 (+$10.8k) and 2021 (+$18.9k).
  - Bad: 2018 (−$13.8k), 2022 (−$19.7k) and 2023 (−$12.6k).
  - This is the "sporadic" pattern the video describes, except it doesn't add up to a profit.
- **Sanity checks:**
  - The per-trade result doesn't depend on sizing (average −0.02R).
  - Counting only positions of $5,000 or more gives a profit factor of 0.95.
  - The per-trade average was slightly positive in 2016–2020 (+0.02R) and negative after (−0.04R).

## The short side (information only; cash accounts can't short)
It lost badly: $100,000 → $22,800, with a profit factor of 0.77. Betting against stocks in a decade when the market more than quadrupled was a losing game, and survivorship bias also works against shorts here.

## What this does and doesn't mean
- **One fixed reading of a teaching example.** The instructor said himself that he had no idea whether it's profitable. The judgement calls he adds (old support, slowing candles, Fibonacci, round numbers) weren't tested because they can't be applied objectively.
- **It was tested on stocks, not the currencies he trades.**
- **Nothing will be tuned** on this data. The rules as written showed no edge.
- **Pattern across three tests:** this is the third pre-declared chart strategy to fail, after the SPY put spread holdout and the TikTok breakout. Simple chart rules like these don't beat holding the index after costs.
