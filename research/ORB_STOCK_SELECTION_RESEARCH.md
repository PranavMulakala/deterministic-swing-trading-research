# ORB stock selection: evidence and proposed research plan

September 7, 2026. Personal research; no orders, deployment, subscriptions,
credentials, commits or pushes. This is a research brief, not a frozen strategy,
an implemented scanner, or a verified list of tomorrow's trading opportunities.
Proposed simulation allocation: $5,000. Original ETF rules remain unchanged.

## The actual question

Which **stock-days**, selected using information available before entry, have
better net results under a fixed opening-range rule? A permanently fashionable
ticker is not necessarily in play each morning. A stock being volatile is not
proof that its breakouts continue or that its dips recover.

Keep three experiments separate:

1. ORB continuation: trade a break beyond the opening high/low.
2. ORB breakout/retest: wait for the break, then a specified retest and rejection.
3. Opening-dip recovery / longer holding: buy weakness and wait for another level.

The owner's video describes (2); the LITE bounce work is (3). Holding a failed ORB
indefinitely changes its exit rule and creates a different strategy.

## What other people actually do, and how strong the evidence is

### Published stock-market research

Zarattini, Barbon and Aziz studied approximately 7,000 US equities during 2016–2023,
using CRSP membership and IQFeed intraday data. Their stock selection combines
minimum price, historical volume and ATR with first-five-minute relative volume,
ranking the strongest 20. The comparison reports a large improvement with this
selection. It uses both long and short positions, $25,000 initial capital and up
to 4x leverage; it is not evidence for our $5,000 long-only retest strategy. The
study does not establish that an LLM news-sentiment filter improves the approach.

[Original paper](https://concretumgroup.com/wp-content/uploads/2026/02/A-Profitable-Day-Trading-Strategy-For-The-U.S.-Equity-Market.pdf)

### Reproducible engineering example

QuantConnect provides a stocks-in-play implementation based on that research.
It chooses a liquid universe, computes opening-window relative volume and ranks
candidates at 09:35. Its displayed backtest covers **2016**, not all years in the
paper; it also explores parameter combinations. Useful implementation reference,
not an independently verified all-period replication or a reason to migrate repos.

[QuantConnect implementation](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)

### Practitioner workflow

SMB describes looking for fresh catalysts, unusual participation, liquidity and
specific price setups. That provides a sensible way to generate candidates.
It is practitioner/education material, not a complete independently audited trade
record, and it should not be treated as proof a proposed threshold is profitable.

[SMB stock-selection discussion](https://www.smbtraining.com/blog/stock-trading)

### What forums add

A reviewed Reddit ORB discussion describes a futures backtest with out-of-sample
results, then debates stop placement, bar-close timing, targets and regime effects.
Those are useful questions. The claimed results are self-reported, concern MNQ
futures, and were not reproduced here; they do not validate LITE equities.
In particular, changing a rule after viewing an out-of-sample result turns that
period into development data. Popularity, win screenshots and agreement among
commenters are not evidence of profitability.

[Community discussion](https://www.reddit.com/r/Daytrading/comments/1rrn609/i_tested_the_opening_range_breakout_on_mnq/)

## Initial comparison names: candidates, not ranked winners

Recomputed from the existing hash-pinned IEX all-adjusted daily-bar snapshot:
`research/lite_2026/snapshot.json`, SHA-256
`42342bcebbc42da4c51b028b15c90ce8942809566c14c69a841f6cb55e1202a5`.
All seven symbols have 170 daily observations January 2–September 4, 2026.

| Symbol | Median daily high-low range / open | Research role |
|---|---:|---|
| LITE | 7.5% | Original hypothesis anchor |
| COHR | 7.1% | Additional stock with substantial observed movement |
| CIEN | 5.9% | Additional stock, somewhat lower observed range |
| FN | 5.6% | Comparison that was not selected for a positive year-to-date return |
| AAOI | 10.2% | Higher-volatility stress case, not automatically the best candidate |
| QQQ | 1.3% | ETF comparison/control, not a single company |
| SPY | 0.9% | Broad-market comparison/control |

These are one-venue daily bars, not consolidated regular-session ranges. Do not
mix them with the earlier LITE-only SIP figures as if the feeds were identical.
They establish movement sufficient to investigate, not liquidity, spread, tomorrow's
relative volume, brokerage eligibility, ORB win rate or an edge. The comparison
names are concentrated in a related industry; they do not provide broad portfolio
diversification. Add a cross-sector, point-in-time liquid universe for a general
test rather than declaring this hand-picked group representative of the market.

## Proposed screen: transparent starting rules, NOT tuned or validated

This is an initial **research proposal**, subject to an explicit spec freeze before
testing. Do not search dozens of threshold combinations and retain only winners.

### Previous close / premarket: eligibility

- US exchange-listed common stocks; exclude OTC, warrants, leveraged products and
  instruments whose identity/corporate-action history is unresolved. ETFs stay in
  a separate control group. Initial direction: long only, no leverage.
- Previous regular-session close at least $10.
- Median daily dollar volume over the previous 20 sessions at least $50 million.
  Calculate from consolidated regular-session data, consistently; do not use IEX
  volume as a stand-in for consolidated liquidity.
- Prior 14-session ATR / previous close at least 2%. Use only completed historical
  sessions with a declared ATR smoothing method. This is a minimum movement screen,
  not a direction forecast or automatic instruction to trade the most volatile name.
- Record the premarket gap, volume and catalyst **as features**, not extra hard
  filters initially. This avoids bundling several untested hypotheses into selection.
- Proposed broad-universe path: rank eligible names by prior dollar volume and
  retain up to 500 for daily analysis. A budget-limited five-stock pilot is a
  different universe and must be labeled accordingly; it cannot find market-wide
  top candidates. No current full-market scan has been performed.

### At 09:35 New York: opening participation

After the 09:30–09:34:59 bar is completed **and received**, calculate:

```
opening_RVOL = today's first-five-minute volume
               / mean(first-five-minute volume on the previous 14 sessions)
```

Require all baseline windows on the same feed and a positive denominator. Missing
data gives `unknown`, not zero. Split effects on share volumes must be normalized
consistently; otherwise invalidate the baseline. Never divide five-minute volume
by a full day's average volume or by future volume from the rest of today.

- Proposed minimum: RVOL >= 2.0; rank descending and retain up to five candidates.
  Two times normal activity is a research starting threshold, not a published
  guarantee. Rank ties by prior dollar volume, then ticker, deterministically.
- Do not fill empty places just to force five opportunities.
- Freeze the ranking snapshot and all information timestamps. Re-rank only under a
  separately declared schedule, never with knowledge of later winning breakouts.

### At a candidate entry: tradability

- Fresh valid two-sided quote; proposed maximum age one second.
- Proposed spread cap: 15 basis points of midprice. Also require the modeled
  round-trip execution cost to be <=20% of the proposed stop distance. A small
  percentage spread can still overwhelm a very tight-stop strategy.
- One whole share must fit both available simulation cash and the planned risk
  budget after costs. At 0.5% of a $5,000 allocation the proposed initial budget is
  $25; that is a sizing assumption, not a guaranteed maximum actual loss.
- Unknown spread, data gap, halt, invalid stop/target geometry or zero quantity:
  no trade. Never narrow a stop or invent a quote to pass the screen.
- Ranking is eligibility for watching, not an order. The frozen price-entry pattern
  must trigger afterward. Avoid pretending a confirmed candle's closing price was
  automatically obtainable after the confirmation arrived.

## Breakout rules still requiring a single explicit specification

Keep first-five-minute range for the initial retest candidate, rather than testing
5/10/15/30/60 minutes simultaneously. Define exactly:

- Whether the initial opening candle must be bullish for a long.
- What constitutes a breakout: trade through, quote through, or completed-bar close.
- Retest sequence: later bar starts above range high, touches/crosses it, then closes
  above it; whether an exact touch qualifies; maximum bars/time allowed to retest.
- Entry after receipt of the confirmation; limit, expiry and no-chase rule.
- Fixed stop definition, target and time exit. The video's discretionary support
  selection is not executable until support and buffers are mathematical rules.
- Maximum entries, concurrent positions and aggregate cash/risk allocation.

When comparing direct breakout with retest, keep stock selection, costs, sizing,
stop/target construction and time limits fixed where mathematically possible.
Declare unavoidable differences. These tests must not inherit the dip strategy's
"return to opening price" target, which may sit below a breakout entry.

## News: record now, test its incremental value separately

An earnings/guidance release or analyst change can explain attention, but positive
tone does not guarantee upward price action. For each event preserve the source,
symbol relevance, original/version text where licensed, publication/update/receipt
timestamps, duplicates/event ID and the text supporting any label.

Initial categories: earnings/guidance, financing, analyst change, material company
announcement, sector/macro, and unknown. Report the same ORB rules split by event
type. Only later test a predeclared filter against the price-only baseline.
Unknown/newsless-looking sessions must not be silently labeled neutral. P/E and
current analyst consensus are not mandatory first-version intraday filters.
Historical values must be public as of the decision, not backfilled revisions.

The 228 cached LITE article records are metadata only, not sufficient for this
analysis. Other candidate stocks also need news acquisition and coverage checks.
News/current market-data entitlement has not been refreshed in this turn. A live
SIP stock-ranking experiment needs consolidated live data; delayed replay can be
useful research but must not be called contemporaneous live selection.

## How to determine whether selection helps

1. Collect equivalent SIP intraday histories for each pilot name and price/quote
   windows for execution checks. Add the previous 14 opening windows and 20 daily
   sessions as warmup; do not use future sessions to fill warmup gaps.
2. Establish a full, date-appropriate universe including delisted names before
   drawing market-wide historical conclusions. Today's constituent list alone
   creates survivorship and selection problems.
3. Freeze one entry/exit rule. Compare it on all eligible stock-days versus the
   RVOL-ranked subset. Keep everything else fixed. This isolates stock selection.
4. Report signals, fill/rejection counts, net mean P&L, average winner/loser, drawdown,
   worst trade, cash occupancy and profit concentration by stock/month/event type.
   Include spreads, slippage, partial fills, gaps and ambiguous same-bar exits.
5. Include a realistic **single $5,000** portfolio ledger. Independent $5,000
   per-stock diagnostic ledgers are not a combined $5,000 portfolio. Correlated
   names can fail together; test allocation/ranking when signals compete for cash.
6. Check uncertainty clustered by session/week, leave-one-symbol-out concentration,
   cost sensitivity and genuinely untouched dates. This year's explored data is
   development data, not a restored holdout. Predeclare decisions before results.
7. Evaluate news and the retest modification in later controlled comparisons, not
   an all-at-once indicator/threshold search. Preserve every tried version.

The research can fail: fewer stops does not guarantee higher net expectancy;
high-RVOL ranking might merely select high spreads; retests may miss trend days;
results might be driven by one ticker or a rising market. Those are findings, not
reasons to keep changing rules until something turns green.

## Deliverable and operational boundaries

The eventual daily report should contain ticker, selection timestamp, lagged
liquidity/ATR, opening RVOL, gap, catalyst and provenance, range high/low, quote
freshness/spread, proposed pattern status and every rejection reason. Missing
fields stay unknown, with no automatic order path in the research collector.

September 7 is a market holiday. September 8's opening volume, spreads and fresh
price patterns are not knowable in advance; today's output is only a candidate
roster. The next market opening is 09:30 New York / 06:30 Pacific, and a five-minute
range first becomes complete at 09:35 / 06:35, plus actual delivery latency.
[NYSE calendar](https://www.nyse.com/trade/hours-calendars)

No new owner videos, course purchases or LLM subscriptions are required to proceed.
Remaining operational dependencies are the personal cloud account, verified data
access, a read-only collector and an exact research spec. This document does not
create any of them or authorize live-money activity.
