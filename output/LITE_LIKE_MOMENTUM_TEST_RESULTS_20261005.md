# Test #17: hold the 5 strongest LITE-like stocks, re-picked monthly, vs holding SMH: results (October 5, 2026)

- **Plan:** [LITE_LIKE_MOMENTUM_TEST_PLAN_20261005.md](LITE_LIKE_MOMENTUM_TEST_PLAN_20261005.md), committed (d025462) before any result.
- **Code:** `research/momentum_lite_like_v1/`, with 4 unit tests and an independent verifier, committed (35977f4) before the run.
- **Data:** daily bars for 5,259 stocks on disk, plus fresh Alpaca SMH, SPY and QQQ (adjusted, dividends included).
- **Main window:** the open of Jan 2, 2020 to the Sep 28, 2026 close (post-COVID).
- **Results:** `output/lite-like-momentum-test-results.json` + `.provenance.json`.
- **Checks:**
  - 4 unit tests pass.
  - **The independent recount matched:**
    - the picks for 6 random months;
    - the whole value path (final $398,863 vs $398,862);
    - SMH buy-and-hold exactly.

## Verdict: FAILED all 3 checks

| Check (Jan 2020 – Sep 2026) | Strategy | Holding SMH |
|---|---|---|
| 1. Growth per year | 22.8% ✗ | **37.8%** |
| 2. Growth ÷ worst drop | 0.27 ✗ | **0.83** |
| 3. Beat SMH in both halves | 2020–22 +24% vs +44% ✗; 2023–26 +222% vs +499% ✗ | |

| $100,000 became | Value | Worst drop |
|---|---|---|
| Strategy (5 strongest LITE-like, monthly) | $398,862 | **−84%** |
| **Holding SMH** | **$865,324** | −45% |
| Holding QQQ | $358,033 | −35% |
| Holding SPY | $260,001 | −34% |

## What happened
- **It caught the 2020–21 mania:** NIO, WKHS, PLUG, BLNK, GME, MARA, RIOT, OCGN. $100k became **$474k by Feb 17, 2021** in 13½ months.
- **Then it rode them down.** −84% to **$75.7k by March 10, 2025**. It only got back to the Feb 2021 peak on **April 9, 2026**, more than 5 years later, and then fell again in the summer 2026 chip selloff.
- **Most-held stocks:** MARA, GME, UPST, SNDK, DJT, MSTR, QBTS, MRNA, NVAX, RIOT, AFRM, NIO, OCGN, AMC, AI.
  - The "strongest volatile" stocks are mostly manias (memes, crypto, EVs, COVID biotech), not the steady AI winners.
  - It rotated out of real winners as soon as something wilder spiked.
- **Year by year (strategy vs SMH):**

  | | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 YTD |
  |---|---|---|---|---|---|---|---|
  | Strategy | +73.5% | +24.1% | −42.4% | +76.5% | **−26.0%** | +57.4% | +56.4% |
  | SMH | +52.8% | +42.1% | −33.5% | +73.4% | +39.1% | +49.2% | +66.6% |

- **More detail:**
  - beat SMH in 48% of months;
  - worst single month −34%;
  - 30 of 81 months had empty slots held in SMH;
  - it replaced about 87% of the portfolio each month.

## Information only (decided in the plan): every variant also fails
| Version | $100k became | Worst drop |
|---|---|---|
| Top 3 instead of 5 | $328,100 | −91% |
| 12-1 month momentum (academic standard) | $679,324 | −80% |
| No "must be rising" filter | $415,557 | −83% |
| Costs 0.25% per side | $358,711 | −85% |
| **Stress check since Oct 2016** | $743,702 (SMH $1,897,468) | −84% (SMH −45%) |

## Bias reminder
- **Stocks delisted before 2026 are missing.** That flatters this rule: busted meme stocks and SPACs it would have bought aren't in the data.
- **So the real result is likely worse.** No survivorship re-check is needed for a fail.

## What this means
- **Chasing the strongest LITE-like stocks did far worse than just holding SMH,** with an 84% crash on the way. The test can't find "the next LITE" in advance.
- **The trap is how the first 13 months looked: +374%.** Anyone who saw that would have believed it, then lost 84%.
- **This matches the evidence:** momentum works on average, but in volatile stocks it crashes hard (Daniel & Moskowitz 2016).
- **Nothing changes in Plan B, the bots, MNQ or the EP watch.**

**Score:** 17 pre-declared tests. Only #14 passed (and it ties the market since 2000).

## 2026 alone (added after the owner asked "shouldn't we compare since January?"; information only)
**Dec 31, 2025 close → Sep 28, 2026 close:**

| | Return |
|---|---|
| Strategy | **+56.4%** |
| **SMH** | **+66.6%** |
| QQQ | +20.3% |
| SPY | +13.2% |

**Hindsight, single stocks:** SNDK +622%, MRNA +569%, AXTI +351%, MU +270%, LITE +150%.

- **The strategy did hold this year's momentum names:**
  - Jan: OPEN, ONDS, SNDK, LITE, BE;
  - Apr: AXTI, SNDK, LITE, AAOI, CIEN;
  - Jul: SNDK, MXL, AXTI, MU, AAOI.
- **It peaked at $700,103 on May 5** (about +175% for the year), then fell **63% to $260,918 by July 29** in the summer chip selloff.
- **Even in the year most favourable to momentum, it finished behind simply holding SMH.**
