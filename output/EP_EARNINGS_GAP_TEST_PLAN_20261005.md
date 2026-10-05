# Qullamaggie's "Episodic Pivot" (earnings gap-up): pre-declared test #16 plan (October 5, 2026)

- **Written and committed before** any earnings dates or intraday bars were downloaded and before any EP result was computed.
- **Done beforehand:** only a count of candidate gap-up days from the daily data already on disk, to size the downloads. No returns were looked at.
- Research only; no orders. It changes nothing in Plan B, the bots or MNQ.
- **Owner's request (Oct 5):** "yes plan the EP test after test 15 finishes."
- **Source of the rules:** Qullamaggie's post "3 TIMELESS setups that have made me TENS OF MILLIONS!" (Jan 8, 2021) and his comment replies, as summarized in [QULLAMAGGIE_REVIEW_20261005.md](QULLAMAGGIE_REVIEW_20261005.md).
  - Where he gives a range (opening-range length, when to take partial profits, 10- or 20-day average), this plan picks **one** main value now and reports at most one alternative as information.

## Expectations, stated up front
- **The academic support is old.** Post-earnings drift was strong historically, but Martineau (2021) finds it **gone for large stocks since about 2006**, and more recently for microcaps too. His EP adds filters those studies don't use, but expect modest results.
- **Our closest past test failed.** Test #3, swing breakouts, lost money. That test entered at the close, though, and this one uses his intraday entry.
- **A known bias flatters the rule:** the on-disk data only has stocks still listed in 2026, and many 2016–2019 gappers that later failed are missing. It also explains why there are far fewer events before 2020.

## Data
1. **Daily bars** on disk: `outputs/breakout_data/` (5,259 US stocks, SIP, split- and dividend-adjusted, Jan 2016 – Sep 28, 2026).
2. **Earnings dates: SEC EDGAR** (free, official). Each company's filing list (`data.sec.gov/submissions`) shows every **8-K with Item 2.02** ("Results of Operations"), the form US companies file with an earnings release, and its exact acceptance time.
   - **Only needed for the 2,044 stocks** that had at least one candidate gap day.
   - **Foreign companies** (ADRs filing 6-Ks) have no Item 2.02, so they can't count as earnings EPs; they're reported in the "all catalysts" view.
3. **Intraday bars:** Alpaca SIP **5-minute bars** (split-adjusted, matching the daily data) for each of the **7,330 candidate days**.
   - A candidate day is a gap ≥ 10% with **full-day** volume at least 1× the 20-day average. That's a superset used only to choose what to download; the rule itself uses only the first 30 minutes' volume.
4. **Benchmark:** SPY with dividends, same dates.

## The rule (main)
| Step | Rule |
|---|---|
| Liquidity | 20-day average dollar volume before the day ≥ **$20 million** (this doesn't change with splits; no price filter, see test #15's lesson) |
| Catalyst | An **8-K with Item 2.02 accepted between the previous session's 4:00 PM close and 9:30 AM** on the gap day |
| Gap | Open ≥ **1.10 ×** the previous close |
| Big volume | Volume from 9:30 to 10:00 ≥ **1.0 ×** the 20-day average **daily** volume |
| Opening range | The first **60 minutes** (9:30–10:30): its high (ORH) |
| Entry | The first 5-minute bar from 10:30 to 15:55 that trades above the ORH: buy at the ORH (or that bar's open if higher) **+ 0.1%** |
| Stop | **The day's low at the moment of entry** |
| Skip | If entry − stop is wider than the stock's 20-day average daily range |
| Size | **1% of equity at risk:** shares = 1% of equity ÷ (entry − stop), capped at **25% of equity** and by cash. No margin |
| Day 3 | At the close of the **3rd trading day** after entry, **sell half** and move the stop on the rest to **break-even** |
| Trail | Sell what's left at the close of the **first day that closes below the 10-day average** |
| Stop fills | During the entry day, at the stop. Later days: if the day opens below the stop, at the open; otherwise at the stop |
| Order within a day | Stop first, then the day-3 sale, then the trail |
| Costs | 0.1% per side (our standard) |
| Portfolio | **$100,000 cash.** Entries the same day are taken in breakout-time order, ties by the bigger gap. One position per stock. Positions open at the end are marked at the last close |

**Not tested:** his "strong growth and a big beat" (we have no free fundamentals; the 10% gap is the market's verdict on the surprise).

## Pass bars (the same as every daily test)
**Bar A:**
1. Profit factor ≥ **1.3**, with positions open at the end marked.
2. Profitable in both **2016–2020** and **2021–Sep 2026**.
3. Worst drop no worse than **−25%**.

**Bar B (vs SPY):**
4. A worst drop at least **5 points smaller** than SPY's.
5. Growth ÷ |worst drop| **higher** than SPY's.

If any fail, the setup isn't shown to work for us. **Nothing will be tuned afterwards:** no other gap sizes, volume levels, opening ranges, stops, partials, averages or sizes.

## Also reported (information only, decided now)
- **All catalysts:** the same rule without the earnings requirement (any 10% gap with volume).
- **His "ideally hadn't already run up":** main trades split by the prior 3-month return, below vs above the median.
- **20-day trail** instead of 10-day.
- **Cost stress:** 0.25% per side.
- **Large vs small:** split by dollar volume (median), since Martineau finds the drift vanished first in large stocks.
- **Trade profile:**
  - win rate;
  - average win and loss in multiples of the risk (R);
  - **the share of profit from the top 10% of trades** (his "few big winners" claim);
  - hold times;
  - year by year.
- **Same-bar ambiguity:** how often the entry bar also trades below the stop. The main run assumes the stop hit; the flip rate is reported.
- Provenance manifest.

## Checks
- **Unit tests on hand-built bars:**
  - the signal (gap, volume, earnings timing);
  - ORH entry and the day's-low stop;
  - the range skip;
  - the day-3 half sale and break-even stop;
  - the 10-day trail;
  - a gap-down below the stop;
  - the same-bar case;
  - sizing and the cap.
- **An independent recount** of signals, entries and exits for 10 random events, with separately written code.

## Downloads (need the owner's OK first)
| What | From | Size and time | Cost |
|---|---|---|---|
| Earnings 8-K list for about 2,044 companies | SEC EDGAR (`data.sec.gov`) | About 2,000–5,000 requests at ≤5 per second (15–20 min). Measured on a 20-company pilot first, before the full run. Only the extracted earnings times (a few MB) are kept | Free |
| 5-minute bars for 7,330 gap days | Alpaca (same as test #15) | 7,330 requests, about 1 hour, about 15 MB compressed | Free |

**SEC's fair-access rules require a name and contact email in each request's header.** That needs the owner's OK (and which email).
