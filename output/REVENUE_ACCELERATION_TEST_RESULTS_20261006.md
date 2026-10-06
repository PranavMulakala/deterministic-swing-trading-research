# Test #20: the LITE business fingerprint (buy companies whose sales growth suddenly speeds up): results (October 6, 2026)

- **Plan:** [REVENUE_ACCELERATION_TEST_PLAN_20261005.md](REVENUE_ACCELERATION_TEST_PLAN_20261005.md), committed (43e94ce) before any data or result.
  - Two corrections were made before any result, both written into the plan: a fiscal-year quarter fix (9f3ceea), and same-tag growth plus a 200-day staleness guard (6810c1e).
- **Code:** `research/revenue_accel_v1/`, with 7 unit tests and an independent verifier, committed (6810c1e) before the run.
- **Data:**
  - SEC EDGAR XBRL revenue "frames", 2015 – mid-2026, for 5,205 companies matched to the 5,262 stocks on disk;
  - daily prices, split- and dividend-adjusted;
  - SPY, SMH and QQQ to Sep 28, 2026.
- **Results:** `output/revenue-acceleration-test-results.json` + `.provenance.json`.
- **Checks:**
  - 7 unit tests pass.
  - **The independent recount matched everything:**
    - flagged counts and top-20 lists at 4 random month-ends (32, 126, 19 and 27 companies flagged), rebuilt from the raw SEC files with separate code;
    - the whole account path (largest gap 0.0001%);
    - SPY's final value.

## Verdict: FAILED all 3 checks

| Jan 2020 – Sep 2026 | Fingerprint, top 20 | Holding SPY |
|---|---|---|
| $100,000 became | **$213,809** (+11.9%/yr) | **$260,001** (+15.2%/yr) |
| Worst drop | **−46.2%** (Feb 20 → Mar 18, 2020) | −33.8% |
| Growth ÷ worst drop | 0.26 | 0.45 |
| 2020–2022 | **+41.0%** | +23.9% |
| 2023–2026 | +51.7% | **+109.9%** |

- **Other benchmarks:**
  - SMH: $865k (+37.8%/yr, −45%);
  - QQQ: $358k (+20.8%/yr, −35%).
- **Stress check since 2017:** $283,667 (+11.3%/yr) vs SPY $393,905 (+15.1%/yr).

| Year | Fingerprint | SPY |
|---|---|---|
| 2020 | +38.5% | +17.7% |
| 2021 | +10.6% | +28.6% |
| 2022 | −8.0% | −18.2% |
| 2023 | +16.2% | +26.2% |
| 2024 | −2.9% | +24.9% |
| 2025 | −0.5% | +17.7% |
| 2026 (to Sep 28) | +35.1% | +13.2% |

### What it actually bought
- **The basket:** 412 different stocks over 81 months; on average 52 companies were flagged a month (from 15 to 321). Turnover was 71% a month, and fees totalled $8.5k.
- **Most-held stocks:**
  - COVID-era sales spikes that later reversed: MRNA (15 months), VIR, CRSP;
  - reopening rebounds: WYNN, NCLH, LVS;
  - gold and silver miners: SSRM, CDE, HL;
  - plus NVDA, APO, CALM, EQT, TTWO, CLF.
- **The flaw:** most "sped-up" sales came from **temporary jumps or rebounds from a depressed base**, not lasting demand like LITE's AI lasers. The numbers alone can't tell the two apart.
- **The 2024–2025 AI boom years were flat** (−2.9%, −0.5%). The few AI winners it held (NVDA, MU) sat next to names like MMM, GPN, BB, CARG and HON.

## Your question: would it have found LITE (and MU, SNDK)?
| Stock | Flagged | Bought? | Price when first flagged → Sep 28, 2026 |
|---|---|---|---|
| **MU** | First on May 31, 2024 (growth +58%, sped up 42 points), **rank 21**, just outside the 20; flagged 16 months in all | Held **9 months** | $127 → $1,054 |
| **SNDK** | Jul 31, 2026 (growth +251%), rank 8 | Held 2 months | $1,160 → $1,713 |
| **LITE** | Only on Jun 30, 2026 (rank 43, not bought), at $818 | **No** | $818 → $921 |

### Why LITE was missed: a hole in SEC's data
- **What was missing:** SEC's frames API never placed LITE's **fiscal-2024 annual revenue** ($1,359.2M, in the 10-K filed Aug 21, 2024) in any calendar-year frame. So LITE's **Apr–Jun 2024 quarter was missing** ($308.3M).
- **The effect:** without that quarter, the rule couldn't score LITE from **Sep 2025 to Apr 2026**, which is exactly its big run.
- **With that one quarter restored** from LITE's own SEC filings (worked out *after* the result, information only, `research/revenue_accel_v1/lite_gap_check.py`):
  - LITE is flagged on **Sep 30, 2025 at rank 12**: growth +56%, up from +16%, a 40-point speed-up;
  - it's **bought at $159 on Oct 1, 2025** and held through December ($369 by Dec 31);
  - the account ends at **$225,974** instead of $213,809. **Still $34k below SPY and still failing all 3 checks.**
- **Coverage:** the fingerprint could score only **77% of liquid stocks** (on average 1,189 of 1,549). The rest are:
  - banks and insurers, which use other revenue tags;
  - foreign filers using international accounting;
  - frame holes like LITE's.

## Information only (decided in the plan)
| Version | $100k became | Worst drop | Checks passed |
|---|---|---|---|
| Top 10 instead of 20 | $165,291 | −54.7% | 0 of 3 |
| No "speeding up" requirement (just ≥25% growth, fastest first) | $193,177 | −53.5% | 0 of 3 |
| "Hasn't run yet" (12-month gain under 100%) | $168,877 | −42.2% | 0 of 3 |
| **60-day wait instead of 90** | **$309,702** | −46.2% | 1 of 3 |

- **The 60-day version is the one interesting number.** Acting a month sooner on the same sales figures was worth about **$96k**, and it ended above SPY's $260k.
  - It still failed: a much deeper worst drop (−46% vs −34%), and only +77.8% in 2023–2026 vs SPY's +109.9%.
  - It's the best of 4 variants picked after the fact, which proves nothing by itself.
  - It does match the research: most of the drift after good news happens in the first couple of months, so speed matters more than the screen.

## Known limitations
- **Survivorship:** stocks that delisted before 2026 are missing, which flatters the rule. No PASS, so no re-check with delisted stocks is needed.
- **Restated figures:** SEC frames keep the **latest filed** number for each quarter, so later restatements can replace what investors saw at the time.
- **Fixed before any result** (in the plan):
  - fiscal-year Q4 quarters;
  - mixed revenue tags: 9% of comparisons had compared different revenue lines;
  - stale numbers from companies that stopped filing.

## What this means
- **The business fingerprint is real information, but as a rule it lost to SPY by $46k, with a deeper crash.**
  - It can spot a LITE or an MU, though late: LITE had already nearly doubled from $84.
  - It also buys about 40 other "fast-growing" companies every month, and most of those jumps are temporary.
- **Telling a lasting change (AI data centers needing lasers) from a one-off (vaccine sales, reopening) is a judgment about the business.** That's the part you did yourself with LITE when you "just knew they had a future". The numbers can point you to candidates to research; they can't do the picking.
- **Nothing changes in Plan B, the bots, MNQ or the EP watch.**

**Score:** 20 pre-declared tests. Only #14 passed, and it ties the market since 2000.
