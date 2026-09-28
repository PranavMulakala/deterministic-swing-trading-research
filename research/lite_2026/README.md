# LITE opening-reversal research brief

Created September 6, 2026. Status: exploratory research and proposed experiment.
This is not a preregistration, an approved trading strategy, or a deployed news collector.

## Question and current evidence

Can an observable rebound after an opening decline produce positive returns after
execution costs, with small planned dollar losses? A rebound from a retrospectively
selected low to a retrospectively selected high is not a return an investor can capture.

The local `profile.py` downloads and replays a fixed 2026 snapshot. It measures price
patterns and news availability; it does not simulate fills, score sentiment, or trade.
`results.json` contains the observations, formulas' outputs, coverage, and snapshot hash.
The ignored `snapshot.json` contains public market data and news metadata, not secrets.
It stays local pending any market-data redistribution requirements.

Source: Alpaca IEX, all-adjusted bars, through September 4, 2026. IEX covers one venue.
Its first trade is not necessarily the official exchange opening price. Daily bar
high/low ranges are not asserted to be regular-hours-only. These are selected
comparison symbols, not a screen of all stocks or an unbiased historical universe.

| Symbol | Adjusted close change in 2026 | Median daily bar range / open |
|---|---:|---:|
| LITE | +139.14% | 7.49% |
| COHR | +52.89% | 7.05% |
| CIEN | +37.33% | 5.87% |
| AAOI | +202.74% | 10.20% |
| FN | -10.47% | 5.65% |
| QQQ | +17.35% | 1.34% |
| SPY | +13.57% | 0.89% |

Volatility alone did not determine the direction of returns. These percentages
describe historical prices, not capturable profit or a prediction.

There were 170 calendar sessions, with 166 qualifying for LITE intraday analysis.
Four failed the 90% five-minute-bar coverage requirement. All six bars from 09:30
through 09:55, plus the 10:00 and 15:55 bars, must exist. All times are New York local.
Filtering by data completeness can introduce selection bias and excludes some risk.

In the qualified sessions, 116 had a first-half-hour low at least 1% below the first
09:30 bar's open. Of these, 63.79% later touched that opening reference. The 10:00
bar's open to the 15:55 bar's close return was positive on 56.03%, averaged +0.704%
before costs, and reached -6.363% at worst. These are descriptive endpoints, not
executable-entry or stop-order backtest results. The positive-close rate was 30.77%
in July (13 observations) and 60% in August (15); small monthly samples are noisy.
The broad upward trend can explain some rebounds, so comparisons must include
unconditional same-time LITE returns and market-adjusted returns.

News access: the historical REST query returned 228 unique LITE-tagged article IDs
from Benzinga. 119 records have different creation and update timestamps. The
latest text version must never be attached to an earlier original timestamp.
This is provider coverage, not all LITE news. Real-time streaming entitlement,
delivery delay, and historical original versions have not been established.

## Correction to the earlier chat analysis

The temporary five-minute limit-order simulation was approximate: it ignored
entry-bar exits, allowed entries throughout the remaining session, assumed exact
stop fills, and filtered sparse IEX sessions. It was not a validated opening-only
backtest. Its precise mean losses are not reliable estimates for a proposed new
strategy. The broad conclusion remains that a frequent rebound is not sufficient
evidence of positive trade expectancy. This new profile intentionally makes no
fill-based performance claims.

## A concrete candidate to test, not tuned parameters

Start with LITE shares, a $500 paper allocation, one position and one attempt per
symbol per session. Candidate rules for discussion:

1. Observe a drop of at least 1% from the 09:30 opening reference before 10:00.
2. Between 10:00 and 11:00, wait for a completed five-minute bar with a low above
   the preceding bar's low and a close above that preceding bar's high. This is
   an observable rebound; never use a pivot requiring future bars.
3. Enter at the next available executable price only if below the opening reference.
   Define the stop below the lower of those two completed bars, with a fixed
   preregistered price buffer. Fix the target at the opening reference.
4. Require prospective reward to the target of at least 1.5 times the planned
   loss, including estimated spread and slippage. Otherwise skip.
5. Exit on stop, target, or at 15:55. Do not average down or hold overnight.

The buffer and cost model must be specified before formal testing. A small fixed
comparison set should include an immediate dip entry, this confirmed rebound,
and the same rebound with a news-event filter. A VWAP reclaim can be a separately
declared alternative. Do not add many filters and keep only the best historical
combination. Record every tested variation, including failures.

Proposed risk research default: $2.50 planned loss per entry (0.5% of $500), block
new entries after $5 realized daily loss, and allow only one open position. Actual
loss may exceed the plan during gaps, halts, or slippage. Existing-position exit
handling continues after an entry halt. These defaults have not been applied to
the existing execution configuration. Whole-share sizing can result in no trade.

Size = floor(min(available cash / executable entry price,
                 dollar risk budget / (entry - stop + cost allowance per share))).
Do not narrow the stop merely to fit a share into the budget.

## Finding comparable candidates

Screen on information available at that time: prior-session ATR as a percentage
of price, lagged dollar volume, live spread, cumulative relative volume versus the
same time on prior sessions, current gap, and fresh event type. A provisional
screen might use 3-10% ATR/price, $50 million median daily dollar volume, relative
volume above 1.5, and spread below 0.1%; these are research starting points, not
validated thresholds. Avoid selecting stocks because their later yearly return
was high. Keep LITE/COHR/CIEN/AAOI/FN as an illustrative cohort, and evaluate a
historically available wider universe before claiming a general strategy.

## News collector and historical event study

Proposed sources: Alpaca/Benzinga news, company investor-relations releases, SEC
8-K and other relevant filings, and scheduled macro releases. Add licensed social
feeds only if they improve measured results. Exhaustive scraping of all websites
is not an achievable coverage promise. Respect source access and storage terms.

For every item/version store provider ID, source URL, symbols, published time,
updated time, first-received time, source/content hash, and duplicate-event group.
Retain original versions where permitted. Reconnect with overlapping backfill and
deduplicate; record gaps, health status and processing delay. Silence in the feed
is not proof of no news. No article text may alter code, tools, credentials, risk
settings, or order authorization; parse it as untrusted content.

Classify event type (earnings/guidance, financing/dilution, analyst action, contract,
regulatory, sector/macro), positive/negative/uncertain tone, company relevance,
novelty, and surprise versus expectations. Preserve the supporting text span and
an unknown value when evidence is absent. A positive-tone probability is not a
probability that a stock price rises. A model can classify tone while failing to
forecast returns; model accuracy must not be sold as trading accuracy.

Match historical events to prices only after the event version could have arrived,
including explicit ingestion and inference delays. Historical retrieval now does
not prove past first-delivery times. Revised articles need their version time;
when original versions are unavailable, flag or exclude them rather than backdate
the latest text. Recaps explaining an earlier move are not forecasts of that move.
Modern language models may know historical outcomes: pin versions, restrict inputs,
and treat their retrospective performance cautiously.

Measure returns at 5, 15, 30 and 60 minutes and the close, relative to the market
and comparable non-news sessions. Include adverse excursions, spread, fill rates,
stop gaps, complete per-trade costs, and uncertainty clustered by day/week. Multiple
articles about one event are one event, not independent confirmation. Evaluate
news as a feature by comparing the identical price strategy with and without it.

For formal testing, use better-covered intraday trades/quotes and report unresolved
bar ordering. A stop gapped through fills at the worse available price. A touched
limit is not a guaranteed fill. Model cash, settlement/account constraints, share
granularity and common losses across correlated stocks. Report dollar outcomes
at the actual $500 scale, plus hosting and data costs separately.

All 2026 results already examined are exploratory. Retrospectively choosing a
2026 holdout does not restore independence. Freeze a final rule/model before an
actually unseen evaluation period. Passing software tests does not establish an
edge. A few live days can reveal operational errors, but not lasting profitability.

A future continuous collector requires an always-on personal host with persistent
storage, restricted secrets, restart recovery and health monitoring. It must keep
working independently of the work laptop. No such host or 24/7 service was created
by this research step. Start with efficient deterministic filtering and a compact
sentiment model; reserve larger-model calls for relevant new events.

## YouTube learning sequence

Search these phrases:

1. `SMB Capital stocks in play news catalyst relative volume`
2. `Humbled Trader stock scanner relative volume ATR`
3. `opening range reversal higher low confirmation day trading`
4. `VWAP reclaim vs VWAP rejection trading`
5. `ATR position sizing risk per trade R multiple expectancy`
6. `news trading earnings surprise guidance priced in`
7. `backtesting look ahead bias walk forward slippage`

Watch for exact stock-selection criteria, timestamps, observable entries, stops,
targets, losing examples, full trade counts, net results and testing on unseen
dates. Courses, affiliates and selected winning examples are not independent
performance evidence. Begin with free examples before buying tools or courses.

Send a video URL and the relevant start/end timestamp, what you want copied,
entry/exit rules you understood, and what is unclear. We can turn those into
testable rules; you do not need to learn Python first.

## References

- [SMB worked VWAP pullback example and transcript](https://www.smbtraining.com/blog/how-to-use-vwap-to-buy-a-pullback-in-a-meme-stock)
- [Humbled Trader watchlist/scanner video](https://www.youtube.com/watch?v=VDN4jp4Uf1k) (description inspected, full video not reviewed)
- [Alpaca historical bars](https://docs.alpaca.markets/us/reference/stockbarsingle-1)
- [Alpaca historical news](https://docs.alpaca.markets/us/docs/historical-news-data)
- [Alpaca news endpoint](https://docs.alpaca.markets/us/reference/news-3)
- [Alpaca news stream](https://docs.alpaca.markets/us/docs/streaming-real-time-news)
- [SEC public data APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [EdgarTools](https://github.com/dgunning/edgartools)
- [FinBERT](https://github.com/ProsusAI/finBERT) (financial tone classification, not a price predictor)

## Reproduce

From the repository root:

```sh
PYTHONPATH=src .venv/bin/python research/lite_2026/profile.py
PYTHONPATH=src .venv/bin/python -m unittest discover -s research/lite_2026 -p 'test_*.py' -v
```

The first command reuses the local snapshot without any network or credentials.
If the snapshot is absent, or `--refresh` is supplied, it reads the existing local
credential configuration and queries Alpaca. A refresh overwrites the local
snapshot and changes the hash if the vendor revises history. Preserve a snapshot
before refresh when comparisons to its exact contents matter.
