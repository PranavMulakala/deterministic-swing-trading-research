# 50-day moving-average rule on SPY: results of the pre-declared test (September 30, 2026)

- **Plan:** [SMA50_TEST_PLAN_20260930.md](SMA50_TEST_PLAN_20260930.md). It was committed before any result was computed (5d1bd47), plus one correction to a data check, also made before any result (0d8e134).
- **Code:** `research/sma50_test_v1/` (5 offline tests).
- **Results file:** `output/sma50-test-results.json`.
- **Data:** SPY daily bars already on disk, adjusted for dividends. The first possible trade is Mar 16, 2016 (after the 50-day warm-up); the last day is Sept 28, 2026. No download.
- **Source:** Mind Math Money, "AI Trading Full Course". The rule: buy when the daily close is above the 50-day average, sell when it closes below. Long only, whole account, 0.1% cost per buy and per sell.

## Did the test itself work? Yes, all three checks passed
1. **Unit tests on made-up prices (5 of 5 pass):**
   - a hand-worked example with exact fills and costs;
   - never above the average means no trades;
   - always above equals buy and hold;
   - a close exactly on the average changes nothing;
   - the two calculation methods agree.
2. **Two independent calculations agree to the cent:** $190,794.96 from the trade loop and $190,794.96 from daily growth factors.
3. **Data consistency:** SPY's change over the pullback test's date range comes out at +348.6%, the same as that test reported.

## Verdict
- **A, "does it work as a strategy on its own?": PASSED.** It's the first of five pre-declared tests to pass this bar.
- **B, "is it a better way to hold the market?", the video's actual claim: FAILED.** It earned far less than just holding SPY, and it didn't make up for that with enough safety.

| | 50-day rule | Just hold SPY |
|---|---|---|
| $100,000 became | **$190,795** | **$446,387** |
| Total return | +90.8% | +346.4% |
| Yearly growth (CAGR) | 6.3% | 15.3% |
| Worst drop | **−19.7%** | −33.8% |
| Growth per unit of worst drop | 0.32 | **0.45** |
| Days invested | 74% | 100% |

**Verdict A: the old pass bar (all three needed)**

| Check | Needed | Result |
|---|---|---|
| Profit factor | ≥ 1.3 | **1.88** ✓ |
| Profitable 2016–2020 | > $0 | **+$29,718** ✓ |
| Profitable 2021–2026 | > $0 | **+$61,077** ✓ |
| Worst drop | ≤ 25% | **−19.7%** ✓ |

**Verdict B: better than holding SPY (both needed)**

| Check | Needed | Result |
|---|---|---|
| Worst drop at least 5 points smaller than SPY's | ≥ 5 points | 14.1 points smaller ✓ |
| Growth per unit of worst drop higher than SPY's | > 0.45 | **0.32** ✗ |

## What happened
- **87 trades, about 8 a year.**
  - 38% won: the average win was +4.6% and the average loss −1.5%.
  - The best trade was +17.7% (May–Nov 2025). The worst was −7.6% (a gap in Aug 2024).
- **It did its job in crashes.** Drop inside each rough patch:

  | Rough patch | Rule | SPY |
  |---|---|---|
  | Early 2020 | −6.5% | −33.8% |
  | Late 2018 | −9.7% | −19.3% |
  | 2022 | −16.1% | −24.5% |

- **It paid for that in normal years.** Year by year:

  | Year | Rule | SPY |
  |---|---|---|
  | 2016 | −2.5% | +12.6% |
  | 2019 | +9.9% | +31.1% |
  | 2023 | +12.1% | +26.2% |
  | 2024 | +9.7% | +24.9% |

  Every dip below the average sold it out, and every bounce bought it back higher. Of the 87 trades, 39 were losses of 1–2%.
- **Why verdict B failed:** the rule gave up about 60% of SPY's yearly growth to cut the worst drop by about 40%. Growth per unit of worst drop is 0.32 against SPY's 0.45. Just holding a smaller slice of SPY, with the rest in cash, would roughly have beaten that trade-off, with no trading at all. That's an estimate from this ratio, not a separate test.

## What wasn't counted, and which way it cuts
- **Interest on cash:** the rule sat in cash 26% of the time. At a rough 2–3% average cash yield over the decade, that adds about 0.5–0.8% a year: 6.3% becomes roughly 7%, still far below 15.3%.
- **Taxes:** 87 sales in a taxable account would realize gains as short-term income. That cuts against the rule.
- **Real SPY trading costs** are about 0.01%, not 0.1%. Lower costs would help the rule slightly. It's still nowhere near closing a 9-point-a-year gap.

## What this means
- **The testing isn't rigged to fail.** The same machinery, pass bar and data that failed four strategies passed this one on verdict A, and every engine check passed.
- **Verdict A alone was too easy to misread.** A rule can make money, have a good profit factor and small drops, and still leave $255,000 on the table next to doing nothing. From now on, every test should be judged against holding SPY, not just against zero.
- **The video's own lesson held up on SPY:** "moving averages are often better used to avoid downside than to maximize upside." It did avoid downside. It just wasn't a good deal, because in 2016–2026 upside was what mattered.
- **Nothing will be tuned.** No 200-day version, no other markets, no added filters. This result stands as one run.
