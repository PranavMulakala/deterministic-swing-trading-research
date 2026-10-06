# The LITE business fingerprint: buy companies whose sales growth suddenly speeds up. Pre-declared test #20 plan (October 5, 2026)

- **Written and committed before any revenue data was downloaded and before any result.** Research only; no orders.
- **Owner's request:** "Yes, do test 20, please" (Oct 5). It comes from the question "can we pattern-match what happened with Lumentum?"
- **Why this, not a chart pattern:** right before its run, LITE's chart looked dead. It was $84 at the end of 2024, 23% below its 2021 high and level with 2019. What changed was the **business**: AI data centers suddenly needed its lasers, and sales growth sped up quarter after quarter.
- **Independent evidence:** earnings and revenue momentum (Chan, Jegadeesh & Lakonishok 1996; Jegadeesh & Livnat 2006) — stocks with accelerating or surprising sales tend to keep doing slightly better for months. The effect is modest, and weaker in recent decades.

## Data
- **Quarterly revenue for every SEC filer:** from SEC EDGAR's free XBRL "frames" API (`data.sec.gov/api/xbrl/frames/us-gaap/<concept>/USD/CY<year>Q<n>.json`), calendar quarters 2015 Q1 – 2026 Q2. Annual frames are used for Q4 (Q4 = year − Q1 − Q2 − Q3 when all four exist and the result is positive).
  - **Revenue tags, in priority order:** `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet`, `RevenueFromContractWithCustomerIncludingAssessedTax`.
  - **The download needs the owner's OK first.** The size will be measured on a pilot. The User-Agent is the same approved name and Gmail as test #16.
- **When each figure counts as known:** **90 days after the quarter ends.** That's conservative: 10-Q/10-K deadlines are 40–90 days and earnings releases come earlier, so it never uses numbers before they were public.
- **Prices:** the daily bars on disk for 5,259 US stocks (adjusted). SEC company IDs are matched to tickers with SEC's own ticker list. SPY, SMH and QQQ come from the fresh benchmark files.

## The fingerprint (checked at each month-end, using only revenue known by then)
For the latest known quarter (Q0) and the two before it (Q−1, Q−2), with growth measured against the same quarter a year earlier:
1. **Real size:** Q0 revenue ≥ **$50M** (no tiny base effects).
2. **Fast:** Q0 growth ≥ **+25%**.
3. **Speeding up:** Q0 growth is at least **10 points faster** than Q−1's, **and** Q−1's growth was at least as fast as Q−2's (two quarters in a row of faster growth).
4. **Tradeable:** average dollar volume over the prior 60 trading days ≥ **$20M**.

## The portfolio
- Each month, rank flagged companies by **how much growth sped up** (Q0 minus Q−1). Hold the **top 20, equal weight (5% each)**. **Empty slots are held in SPY.**
- **Timing:** signals at the month-end close; trades at the **next trading day's open**; costs 0.1% per side.

## Windows (the owner's post-COVID default)
- **Main (decides the verdict):** Jan 2, 2020 – Sep 28, 2026. Halves: **2020–2022** and **2023–2026**.
- **Stress check:** Jan 2017 (the first month with enough history) – Sep 2026.

## Pass checks (main window, vs holding SPY from the same open)
1. **More growth:** a yearly growth rate above SPY's.
2. **More growth per unit of pain:** growth ÷ |worst drop| above SPY's.
3. **Not one lucky stretch:** beats SPY in **both halves**.

**Labels:**
- **PASS (robust):** it also beats SPY on growth ÷ worst drop in the stress window.
- **PASS (post-COVID only):** it passes the main window only.
- **FAIL:** any check fails.

**Required before trusting a PASS:** the price data only has stocks still listed in 2026, which flatters this rule. A PASS must be re-checked with delisted stocks (another download, the owner's OK first).

**Nothing will be tuned afterwards:** no other growth cut-offs, sizes, lags, holding counts or tags.

## Also reported (information only, decided now)
- **Comparisons:** vs SMH and QQQ.
- **Variants:**
  - top **10** instead of 20;
  - **no "speeding up" requirement** (just ≥25% growth);
  - a **"hasn't run yet" filter** (12-month price gain under 100%);
  - a **60-day** lag instead of 90.
- **Detail:**
  - how many companies are flagged each month;
  - months with SPY slots;
  - the most-held stocks;
  - yearly returns.
- **A case check:** was LITE (or MU, SNDK) flagged, and when?
- Provenance manifest.

## Checks
- **Unit tests:**
  - growth and acceleration maths;
  - the Q4 calculation;
  - the 90-day availability rule;
  - ranking and SPY filling;
  - next-open trades with costs.
- **An independent recount:** the flagged list for 4 random month-ends from the raw SEC files, plus the whole value path re-chained with separate code.

## Correction before any result (Oct 5, after the download, before any backtest)
- **What went wrong:** the first version derived the missing quarter as "calendar year − calendar Q1–Q3". That only works for January–December fiscal years.
- **Who it hurt:** companies like LITE (June year-end) and MU (September year-end) never tag their **fiscal** Q4, so they lost one quarter a year and would rarely have been flagged.
- **Fixed** (`research/revenue_accel_v1/revenue.py`): the missing quarter is now the **fiscal-year total minus the three tagged quarters inside that fiscal year** (matched by their own start and end dates), labelled by the calendar quarter holding its midpoint (SEC's own labelling).
- **Checked on raw quarters only:** LITE now has its April–June quarters and MU its June–August quarters. No fingerprint or return was computed before the fix.

## Second correction before any result (Oct 6, before any backtest run)
Found while writing the code, by inspecting the revenue data only (no prices, no returns):
- **Mixed revenue tags.** The first version merged the four tags into one series per company, so a quarter could be compared with its year-ago quarter under a **different** tag.
  - That happened in **9% of year-over-year comparisons** (13,469 of 152,421).
  - Where a company reports 2+ tags for the same quarter, they **disagree by more than 2% in 31%** of cases (e.g. total revenue vs contract revenue only).
  - A rule that ranks by the **biggest** speed-up would preferentially pick these fake jumps.
  - **Fixed:** each growth rate now compares a quarter with its year-ago quarter under the **same tag** (the first tag, in priority order, that has both). The size check uses the same tag's revenue.
- **Stale numbers.** A company that stopped filing (e.g. switched to foreign accounting) would keep its last fingerprint forever.
  - **Fixed:** the latest known quarter must have ended within **200 days** of the month-end. 200 days still allows a normal company whose newest quarter is just short of the 90-day wait.
- **Implementation details fixed now:**
  - In the "no speeding-up requirement" variant, companies are ranked by **growth itself**.
  - The "hasn't run yet" variant needs 12 months of prices (otherwise skipped).
  - A pick with no price bar at the next open gives its slot to SPY (counted in the results).
- **Known limitation (not fixable with this data):** SEC frames hold the **latest filed** number for each quarter. A later restatement can replace what investors saw at the time, which is mild look-ahead of unknown direction.
