# LITE news-sentiment test: results (September 28, 2026, about 18:10 ET)

- **Plan:** [LITE_NEWS_SENTIMENT_TEST_PLAN_20260928.md](LITE_NEWS_SENTIMENT_TEST_PLAN_20260928.md), committed before any news was pulled (f6e67f1).
- **Code:** `research/lite_news_sentiment_v1/run.py`.
- **Results:** `output/lite-news-sentiment-test.json`.

## Verdict under the pre-declared rules: the news filter did not help

Check 1 failed: the worst drop from peak was unchanged in both periods. Checks 2 and 3 passed only because the filter barely changed anything. News stays **learning-only** in the daily email.

## Data

899 Alpha Vantage LITE articles:
- 20 from March 2022 to December 2024;
- 98 in 2025, 65 of them in December;
- 781 from January to September 2026.

## Results

| Period | Dip-signal days | With any morning news | Buys the filter skipped | Realized profit, without → with | Worst drop from peak, without → with |
|---|---:|---:|---|---:|---:|
| **Main:** Jan 2025 – Sep 2026 | 192 | 89 | 3 (Jun 5, Jul 15, Jul 28, 2026) | +$115,956 → +$114,760 | −$29,719 → −$29,719 |
| **Stress:** Mar 2022 – Dec 2024 | 215 | 3 | 1 (Jul 12, 2023; the bot was already holding) | +$8,419 → +$8,419 | −$36,359 → −$36,359 |

The stress window starts in March 2022, when Alpha Vantage's archive begins, so it differs from the January 2022 replay. Here the bot bought on Aug 24, 2022 at $90.79 and was stuck, down as much as 61% (−$36,590).

## The mornings before the worst buys

| Buy | Later worst | Morning LITE news |
|---|---|---|
| Jan 24, 2025 at $98.24 | −53% (−$32,080) | none |
| Jun 16, 2026 at $933.24 | −36% (−$21,658) | one article, **Bullish** (+0.63): a "top stock picks" list |
| Aug 24, 2022 at $90.79 | −61% (−$36,590) | none |

The big losses came with market-wide selloffs: the April 2025 tariff crash and the June–July 2026 slide. LITE-specific news did not flag them.

## Descriptive: a hypothetical buy on every signal day, Jan 2025 – Sep 2026

| Morning LITE news | Signal days | +2% sale within 5 trading days | Median worst drop before it |
|---|---:|---:|---:|
| Bearish (≤ −0.15) | 3 | 3 of 3 | −3.2% |
| Neutral | 20 | 20 of 20 | −1.7% |
| Bullish (≥ +0.15) | 66 | 61 of 66 | −1.5% |
| No news | 103 | 90 of 103 | −2.2% |

There are too few bearish mornings to conclude anything.

## Limits
- **Coverage:** Alpha Vantage had almost no LITE news before December 2025, so 2022–2025 cannot test the idea.
- **Not point-in-time:**
  - 68 of 899 articles share repeated clock times. For example, three unrelated August 2025 articles are all stamped 19:35:36.
  - 4 articles are stamped exactly midnight.
  - Both suggest filler timestamps.
- **Scores can be wrong:** an SEC insider-trading charge involving a former Lumentum employee is scored +0.88 "Bullish" for LITE.
- **Some "bearish" mornings only restated the previous day's drop.** For example: "Stock Down 6.7% but Still Overvalued".
- **Macro news was not tested:** China, Iran, and bonds are outside this test.

## Next
- **Forward record:** the bot's email reading will build a true point-in-time record from September 29. At about 90 LITE articles a month, six months should give enough bearish mornings to look again.
- **Macro:** the owner's macro idea needs a different measure, such as how the Nasdaq (QQQ) or the 10-year yield moved before 10:00. That could be tested on the same 2022–2026 price history without any news archive. It would need its own pre-declared plan and the owner's go-ahead.
