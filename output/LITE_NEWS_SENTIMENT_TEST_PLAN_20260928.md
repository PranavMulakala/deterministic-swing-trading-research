# Does morning news sentiment improve the LITE dip bot? Pre-declared test (September 28, 2026, 18:05 ET)

Written and committed **before** any historical LITE news was pulled or matched to trades. The owner asked to "factor in sentiment from news". This tests that idea on history, so we don't have to wait months of paper runs.

## Data and reading
- **News:** Alpha Vantage NEWS_SENTIMENT for `tickers=LITE`, from March 2022 (the start of its archive) to September 28, 2026, pulled through the owner's Alpha Vantage connector.
- **Morning reading:** computed exactly as the paper bot now does (`research/lite_paper_bot_v1/news.py`). It uses articles published from the previous weekday's 16:00 ET to 10:00 ET, with relevance-weighted LITE sentiment and Alpha Vantage's own labels. A morning with no articles counts as "no news".
- **Trades:** the history replay in `research/lite_dip_history_v1/run.py`. SIP signals, $60,000 per buy, +2% target, no stop, one position at a time.

## The one filter tested
**Skip the buy when the morning reading is Somewhat-Bearish or worse (score ≤ −0.15).** Mornings with no news or a higher score buy as usual. Nothing else will be tuned: no other cut-offs, windows, or weights.

## Periods
- **Main:** 2025-01-01 to 2026-09-28, the owner's preferred window.
- **Stress:** 2022-03-01 to 2024-12-31.

## It counts as helping only if all three hold
1. The worst drop from peak (marked) is smaller with the filter in **both** periods.
2. In the main period, realized profit falls by no more than 10%.
3. In the stress period, marked profit at the end is no worse.

Otherwise the conclusion is that news sentiment did not help in this test, and it stays learning-only in the email.

## Also reported (descriptive only; no decision)
For every dip-signal day, grouped by the morning label (Bearish or Somewhat-Bearish / Neutral / Somewhat-Bullish or Bullish / no news), whether a hypothetical buy at 10:00 was followed by:
- the +2% sale within 5 trading days;
- the worst drop before that sale.

These are shown with counts.

## Known limits, stated in advance
- Alpha Vantage's archive may not be exactly point-in-time. Scores may come from a later model version, and some articles may have entered the archive after their publish time.
- Coverage in 2022–2023 may be thinner than today.
- Timestamps are treated as New York time. That was checked on one known event: bank prime-rate cuts after the Fed's 14:00 ET decision on 2025-09-17 are stamped 15:09 and 15:20.
- Only LITE-specific news is scored. Macro news (China, Iran, bonds) is not tested, because Alpha Vantage's economy feed is mostly unrelated company stories.
