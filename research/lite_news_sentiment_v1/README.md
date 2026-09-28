# LITE news-sentiment filter test v1 (September 28, 2026)

A one-time, pre-declared test of skipping the LITE dip bot's buys when the 10:00 morning news reading is Somewhat-Bearish or worse. Research only; it places no orders.

- **Plan:** `output/LITE_NEWS_SENTIMENT_TEST_PLAN_20260928.md`, committed before any news was pulled.
- **Results:** `output/LITE_NEWS_SENTIMENT_TEST_RESULTS_20260928.md`. The filter did not help, and the archive is too thin before December 2025.
- **Inputs:**
  - Alpha Vantage LITE articles in `outputs/lite_news_history/` (gitignored), pulled through the owner's Alpha Vantage connector;
  - the SIP bar cache from `research/lite_dip_history_v1/`.
- **Reused code:** the bot's own reading (`research/lite_paper_bot_v1/news.py`) and the history replay.

```
PYTHONPATH=src:. .venv/bin/python -m research.lite_news_sentiment_v1.run
```
