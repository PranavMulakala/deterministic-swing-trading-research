# Paper test plan and goals, starting Tuesday, September 29, 2026

Research checkpoints for the owner's paper bots. This is not investment advice, and any real-money decision is the owner's.

## The goal
About **$1,000 a week** from the LITE dip bot, tested in the Alpaca **paper** account first. The bot trades **66 shares**, about $60,000 per buy. It buys when LITE dips at least 1% in the first 30 minutes and is still below its open, then waits for a +2% sale. There is no stop.

## What history says to expect at this size
Source: [LITE_DIP_BOT_HISTORY_20260928.md](LITE_DIP_BOT_HISTORY_20260928.md).

- **While LITE keeps rising (like 2026):** about 3 weeks in 4 bring at least $1,000, averaging about $2,000 a week.
- **When LITE slides (early 2025, 2022–2024):** as few as 1 week in 4 bring $1,000, sometimes none for months. Meanwhile, $20,000–$40,000 sits as a paper loss.
- **Morning news does not warn of those slides:** [news test](LITE_NEWS_SENTIMENT_TEST_RESULTS_20260928.md). The email shows it for learning only.

## The test
- **Length:** at least **8 weeks**, to about November 20. That should include Lumentum's next earnings report; the date is not yet confirmed.
- **Weekly scorecard,** filled in from the daily emails:

| Week | Sales | Realized profit | Open paper loss | $1,000 weeks so far | Days since last sale | News on buy days |
|---|---:|---:|---:|---:|---:|---|
| Sep 29 – Oct 2 | | | | | | |

- **Checkpoints, proposed now so they aren't decided in the heat of the moment.** They don't change the bot; they mark when to stop and rethink before any real money. The owner can change them.
  1. The open paper loss reaches **−$15,000**, about −25% on $60,000.
  2. **Six weeks** pass without a sale.
  3. Any **HALTED** or **ERROR** email, or a weekday with **no email**.

## What paper can't show
- Real fills and slippage. Alpaca paper fills instantly at the quoted price.
- How it feels to watch −$20,000 for weeks.

## Options bot
The SPY bull put spread rules **failed** their pre-declared holdout: the candidate lost $1,809 in 2021–2025 under realistic fills ([results](SPY_SPREAD_BACKTEST_HOLDOUT_RESULTS_20260928.md)). The paper options bot runs the approved rules, which traded only 4 times in 12¾ years. It is a plumbing check, not a path to the goal. Keep it or switch it off; that is the owner's choice.

## Before any real-money version (the owner's decision)
- **Broker:** one with an order API. Robinhood has none for stocks.
- **Maximum loss:** a written limit the owner would accept on one position.
- **Size:** chosen deliberately. It doesn't have to match the paper size.

## Tomorrow morning
- **Keep the Mac awake at 10:00 ET.** Plugged in and lid open, with sleep turned off while on power (System Settings → Battery → Options). Otherwise the bot runs late and skips the day. The cloud server avoids this; it can be deployed from home Wi-Fi.
- **Alpha Vantage key:** paste it into `.env.news` (`open -e .env.news`) to turn on the news reading.
- **Expect two emails:** LITE bot at about 10:00–10:05 ET, and the options bot at about 10:30 ET. The options bot enters only on Mondays, so on Tuesday it just checks and reports.
