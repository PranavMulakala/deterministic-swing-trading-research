# TikTok breakout strategy: results of the pre-declared test (September 29, 2026)

- **Plan:** [BREAKOUT_TEST_PLAN_20260929.md](BREAKOUT_TEST_PLAN_20260929.md), committed before any data was downloaded (e222f26).
- **Code:** `research/breakout_test_v1/` (6 tests).
- **Results:** `output/breakout-test-results.json`.
- **Data:** Alpaca SIP daily bars for 5,259 US stocks plus SPY, April 2016 to Sept 28, 2026.

## Verdict: failed all three checks. No edge shown.

| Check | Needed | Result |
|---|---|---|
| Profit factor (gains ÷ losses) | at least 1.3 | **0.94** |
| Profitable in 2016–2020 and in 2021–2026 | both above 0 | **−13.8%** and **−5.1%** |
| Worst drop in account value | at most 25% | **−40.7%** |

## What happened
- **$100,000 became $81,800 (−18.2%)** over 10½ years, about −1.9% a year. Holding SPY returned **+335.8%** over the same period.
- **1,167 trades, about 111 a year.** 39.1% won, with an average win of +4.4% and an average loss of −2.9%.
- **Almost every trade ended at the stop:** 929 of 1,167. Of those, 333 opened below the stop the next morning, so the loss was bigger than the planned 1% of the account. 444 trades were stopped out before day 3.
- **The market filter allowed new trades on only 40% of days.**
- **By exit year:**
  - Losing: 2017 −$17,763, 2021 −$11,204, 2020 −$5,440.
  - Profitable: 2016, 2018, and 2023–2026, but those gains were small.
- **Sanity check:** most positions were full size (median $15,700). Counting only positions of $5,000 or more gives the same profit factor, 0.94.

## What this does and doesn't mean
- **It's one fixed reading of the video.** The video's own chart judgement, trims and intraday entries could do better. These rules were fixed in advance precisely so the result couldn't be tuned after looking.
- **Survivorship bias favored the strategy, and it still lost:** stocks delisted before 2026 are missing.
- **Nothing will be tuned** on this data. Per the plan, the conclusion is that the rules as written showed no edge.
