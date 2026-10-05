# Test #16: Qullamaggie's "Episodic Pivot" (earnings gap-up): results (October 5, 2026)

- **Plan:** [EP_EARNINGS_GAP_TEST_PLAN_20261005.md](EP_EARNINGS_GAP_TEST_PLAN_20261005.md), committed (6c45b08) before any EP data. Pre-data corrections (413ba68) are noted in it.
- **Code:** `research/ep_test_v1/`, with an independent verifier, committed (22b5709) before the run. One bookkeeping fix after the first run (d7e3ddf, see below). 14 unit tests.
- **Data:**
  - daily SIP bars for 5,259 stocks (on disk);
  - Alpaca 5-minute bars for all 7,647 candidate gap days (1,932 dates; 5 days had no bars);
  - SEC EDGAR 8-K Item 2.02 acceptance times for all 2,073 candidate stocks (78,016 filings).
  - Both downloads were free and approved by the owner. The SEC User-Agent used the owner's approved Gmail.
- **Results:** `output/ep-test-results.json` + `.provenance.json`.
- **Checks:**
  - 14 unit tests pass.
  - **The independent recount matched all 10 random trades and all 10 random rejected days**, before and after the fix.
  - **Spot checks on famous earnings (NVDA May 2023, META Feb 2023, LITE Nov 2025):** the SEC filing times match the known after-close releases.

## A bug found after the first run (fixed; all numbers below are after the fix)
- **What went wrong:** trades that **gapped below their stop at the next day's open** were left out of the trade list. Their money was counted, so account values were always right, but profit factor, win rate and R left out those losers.
- **Fixed in d7e3ddf,** with a unit test for that case and a built-in check that every position entered is recorded.
- **The effect:**
  - main profit factor 1.68 → **1.29**, so the rule now also fails A1;
  - the "all catalysts" view goes from 73 to **84 trades**, profit factor 2.18 → **1.74**.

## Verdict: FAILED checks A1 and B2, mainly because the rule almost never traded

| Check (Feb 2016 – Sep 2026) | Needed | EP rule | SPY |
|---|---|---|---|
| A1. Profit factor | ≥ 1.3 | **1.29 ✗** | |
| A2. Profitable in both halves | 2016–20 and 2021–26 | +1.1% / +0.4% ✓ | |
| A3. Worst drop | no worse than −25% | −3.4% ✓ | −33.8% |
| B1. Worst drop 5+ points smaller than SPY's | | ✓ | |
| B2. Growth ÷ worst drop beats SPY | > 0.46 | **0.04 ✗** | 0.46 |

**$100,000 → $101,541 (+0.14%/yr), against $465,473 (+15.6%/yr) for holding SPY.** The checks it passed are trivial: the account sat in cash almost the whole time.

## Why so few trades: the funnel
| Of 7,647 gap-ups of 10%+ with heavy volume | Days |
|---|---|
| No earnings 8-K between the previous close and 10:30 (biotech news, meme spikes, foreign companies…) | 5,098 |
| First 30 minutes' volume under a full day's average | 1,490 |
| Never broke above the first hour's high | 622 |
| Day's low too far below the entry (stop wider than the 20-day average range) | 418 |
| Other (warm-up, scale mismatch) | 4 |
| **Traded** | **15** |

- **The volume rule was the tightest filter, and it was my wording.** Qullamaggie says EPs "often" trade a full day's average volume in the first 15–30 minutes; the plan made that a hard 1.0× cutoff.
  - **Famous EPs missed by a hair:** NVDA May 25, 2023 (+26% gap, 0.91×), META Feb 2, 2023 (+20%, 0.91×), NFLX Oct 19, 2022 (0.90×), LITE Nov 5, 2025 (+16%, 0.86×).
  - Loosening it now would be tuning after seeing the results, so the verdict stands as declared.
- **65 gap days** had their earnings 8-K filed after 10:30 that day and weren't counted, as declared.

## The 15 trades
| Stock | Bought | Gap | P&L | R |
|---|---|---|---|---|
| ULTA | 2016-03-11 | +14% | +$61 | +0.10 |
| CLF | 2016-04-28 | +12% | −$1,010 | −1.01 |
| BBY | 2016-08-23 | +17% | +$313 | +0.62 |
| SNAP | 2020-04-22 | +22% | +$1,505 | +1.51 |
| BYND | 2020-05-06 | +10% | +$1,310 | +1.30 |
| CDNA | 2020-10-08 | +14% | −$1,040 | −1.02 |
| RSI | 2021-03-11 | +16% | −$1,260 | −1.25 (gapped below the stop next morning) |
| CHWY | 2022-06-02 | +15% | +$149 | +0.15 |
| PLTR | 2023-02-14 | +13% | +$269 | +0.27 |
| META | 2023-04-27 | +15% | −$535 | −1.05 |
| LITE | 2024-08-15 | +13% | +$754 | +0.76 |
| MDB | 2025-08-27 | +32% | +$2,461 | +2.45 |
| PACS | 2025-11-20 | +53% | −$1,042 | −1.01 |
| PEN | 2026-01-15 | +11% | −$469 | −1.06 |
| CBZ | 2026-07-29 | +17% | +$73 | +0.54 |

- **Profile:** 60% winners, an average win of +0.86R and an average loss of −1.06R; the median hold was 4 days. (R = the dollars at risk on the trade, about 1% of the account.)
- **15 trades over 10 years is far too few to say whether earnings EPs have an edge.**

## Information only (decided in the plan)
| Version | $100k became | Per year | Worst drop | Trades | Profit factor | Checks failed |
|---|---|---|---|---|---|---|
| Main (earnings) | $101,541 | +0.1% | −3.4% | 15 | 1.29 | A1, B2 |
| **All catalysts** (any 10% gap with volume) | **$140,840** | **+3.3%** | **−17.1%** | **84** | **1.74** | **B2 only** |
| 20-day trail | $100,750 | +0.1% | −4.2% | 15 | 1.14 | A1, B2 |
| Costs 0.25% per side | $103,411 | +0.3% | −2.1% | 12 | 2.19 | B2 |
| Same-bar flip | identical (no ambiguous entries) | | | | | |
| **SPY** | **$465,473** | **+15.6%** | **−33.8%** | | | |

- **The "all catalysts" version shows his pattern clearly:**
  - only **39% winners** (the median trade loses a full 1R);
  - but an average win of **+2.57R** vs an average loss of −0.93R, about **+0.45R per trade**;
  - **the top 10% of trades made 76% of the gross profit.**
  - It was lumpy: 2020 (+$14.9k) and 2024 (+$21.4k) made almost all of it, and 2021 lost $5.4k.
  - **At 1% risk and about 8 trades a year, the money mostly sat idle,** so it grew 3.3% a year against SPY's 15.6%.
- **Splits on the 15 main trades** (too few to mean anything):
  - not-run-up stocks +$3,041 vs run-up stocks −$1,561;
  - large +$4,753 vs small −$3,212.
- **Bias reminder:** stocks delisted since 2016 are missing, which flatters gap-up buying.

## What this means
- **Test #16 can't confirm the EP for us.** As written it almost never traded, so the result says little either way.
- **The all-catalysts view hints at a real per-trade edge** carried by a few big winners. But it's too rare, at sensible risk, to compete with simply holding SPY. Qullamaggie's returns came from doing many setups, with large concentrated positions, for years.
- **Any looser version would be designed after seeing this data**, so it would only be exploratory evidence.
- **The clean next step, if wanted:** watch EPs **forward** on paper (a morning list of earnings gap-ups, logged against these exact rules), without tuning.
- **Nothing changes in Plan B, the bots or MNQ.**

**Score:** 16 pre-declared tests. Only #14 passed (and it ties the market since 2000). #16 failed, mostly for lack of trades.
