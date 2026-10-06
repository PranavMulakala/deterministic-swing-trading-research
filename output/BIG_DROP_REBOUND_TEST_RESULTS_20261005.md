# Test #19: buy a strong stock after a big one-day drop, hold up to 2 weeks: results (October 5, 2026)

- **Plan:** [BIG_DROP_REBOUND_TEST_PLAN_20261005.md](BIG_DROP_REBOUND_TEST_PLAN_20261005.md), committed (3d59252) before any result.
- **Code:** `research/big_drop_rebound_v1/`, with unit tests and an independent verifier (b66a81b), committed before the run. One fix after the first run (89aca16, below). 5 unit tests.
- **Data:** daily bars for 5,259 US stocks on disk (SIP, split- and dividend-adjusted), Jan 2016 – Sep 28, 2026.
- **Main window:** Jan 2, 2020 – Sep 28, 2026.
- **Results:** `output/big-drop-rebound-test-results.json` + `.provenance.json`.
- **Checks:**
  - 5 unit tests pass.
  - **The independent recount matched all 2,054 events,** every outcome for 6 random stocks, and the whole account value ($102,544), using its own portfolio code.

## A fix found by the verifier after the first run
- **What went wrong:** same-day signals were ranked by the drop **rounded to 0.01%**. 26 events tied after rounding and were then picked alphabetically, which isn't the plan's "biggest drops first".
- **Fixed (89aca16)** with a unit test. The rule itself is unchanged.
- **The first run ended at $99,658; the corrected one at $102,544.** Swapping which of a few tied stocks got bought moved the result by 3%. That alone shows how much luck drives this account.

## Verdict: FAILED all 5 checks

| Jan 2020 – Sep 2026 | Buy-the-big-drop | Holding SPY |
|---|---|---|
| $100,000 became | **$102,544** (+0.4%/yr) | **$261,631** (+15.3%/yr) |
| Worst drop | **−52.9%** (Feb 2021 $145k → Jan 2022 $68k) | −33.8% |
| Profit factor (needs ≥ 1.3) | 1.00 | |
| Halves 2020–22 / 2023–26 | −20.9% / +29.7% | |

**Stress check since 2016:** $135,190 (+3.1%/yr, worst drop −52%) vs SPY $412,550.

## Your question: is it a strategy or luck?
**All 2,054 qualifying drops since 2020, each trade on its own:**

| | Share |
|---|---|
| Reached **+20%** within 2 weeks (the dream) | **27.7%** |
| **Fell another 10%** at some point in those 2 weeks | **52.3%** |
| Made money at all | 53.5% |
| Average trade | +1.2% (median +1.3%) |

**The portfolio (10 slots):**
- 955 trades, 51% winners;
- an average trade of **+0.4%** after costs;
- about 1 in 4 hit +20%;
- 48% fell another 10% along the way.

**By year:**

| Year | Profit / loss |
|---|---|
| 2020 | +$6.0k |
| 2021 | **−$21.5k** |
| 2022 | +$7.7k |
| 2023 | +$11.5k |
| 2024 | +$10.7k |
| 2025 | **+$35.5k** |
| 2026 | **−$47.3k** |

- After a great 2025 the account stood at $148,856. **The summer 2026 selloff took it back to $102,544.**
- **Most-traded stocks:** MARA, RIOT, GME, SPCE, CVNA, DJT, MRNA, NVAX, TSLA, ENPH. "Strong stocks that suddenly fall 10%" are mostly the wildest stocks.
- **Worst trade:** GME after its −31% day on Feb 1, 2021, then **−78%** in 2 weeks.

## Information only (decided in the plan)
| Version | $100k became | Worst drop |
|---|---|---|
| Buy at the next day's open | $89,605 | −52% |
| No +20% target (just hold 10 days) | $121,848 | **−71%** |
| No uptrend filter | $67,873 | −72% |
| Costs 0.25% per side | $79,683 | −55% |

## Bias reminder
**Stocks that fell 10% and later delisted aren't in the data.** That flatters this rule, so the real result is likely worse.

## What this means
- **It's luck, not a strategy.** Buying a strong stock's big drop is a coin flip with a tiny average edge (about +1% per trade before position limits, +0.4% after costs) and huge swings.
- **The Western Digital bounce happens, but it can't be told apart in advance from the times the stock keeps falling.** About half kept falling.
- **It matches the research:** the short-term bounce effect is real but small and mostly eaten by costs.
- **Nothing changes in Plan B, the bots, MNQ or the EP watch.**

**Score:** 19 pre-declared tests. Only #14 passed (and it ties the market since 2000).
