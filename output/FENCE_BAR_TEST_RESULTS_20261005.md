# Test #18: the "fence bar" opening setup (Trade Your Edge): results (October 5, 2026)

- **Plan:** [FENCE_BAR_TEST_PLAN_20261005.md](FENCE_BAR_TEST_PLAN_20261005.md), committed (0e01a28) before any result.
- **Code:** `research/fence_bar_test_v1/`, with 8 unit tests and an independent verifier, committed (f6d4164) before the run.
- **Data:** QQQ and SPY 5-minute SIP bars (dividend-adjusted) already on disk, Jan 2016 – Oct 2, 2026.
- **Main window:** Jan 2, 2020 – Oct 2, 2026 (post-COVID).
- **Results:** `output/fence-bar-test-results.json` + `.provenance.json`.
- **Checks:**
  - 8 unit tests pass.
  - **The independent recount matched all 15 random QQQ days** (8 with trades, 7 without) and rebuilt the QQQ account value exactly ($92,873).

## Verdict: FAILED (both QQQ and SPY fail checks A1, A2 and B2)

| Long side, $100,000, Jan 2020 – Oct 2026 | QQQ | SPY |
|---|---|---|
| Ended with | **$92,873** | **$96,136** |
| Per year | −1.1% | −0.6% |
| Profit factor (needs ≥ 1.3) | 0.91 ✗ | 0.93 ✗ |
| Halves 2020–22 / 2023–26 (both must be positive) | −6.3% / −0.9% ✗ | +2.3% / −6.0% ✗ |
| Worst drop | −8.9% ✓ | −11.4% ✓ |
| Growth ÷ worst drop (must beat SPY's 0.45) | −0.12 ✗ | −0.05 ✗ |
| Trades | 428 (64 a year; a trade on 25% of days) | 438 |
| Reached the 2× target | 32% | 33% |
| **Holding SPY instead** | **$260,600 (+15.3%/yr, worst −34%)** | |

**Stress check since 2016:** QQQ $81,882 (profit factor 0.82), SPY $94,378 (0.92). It fails there too.

## Why it loses, in plain words
- **It hits its 2× target about 1 time in 3** (32–33%). With wins twice the size of losses, 1 in 3 is exactly break-even.
- **Before costs it roughly breaks even** (profit factor 1.02 on QQQ, 1.10 on SPY). The tiny trading cost (0.01% per side) is enough to tip it negative.
- **The video's proof was 4 winners out of 4 triggers in 5 days.** Over 6¾ years it won about 1 in 3, and it triggers on about 1 day in 4, not 4 in 5.

## Information only (decided in the plan)
| Version (main window) | QQQ: profit factor / ended with | SPY: profit factor / ended with |
|---|---|---|
| No anchor-line filter | 0.94 / $93,641 | 0.89 / $91,977 |
| Stop at the retest bar's low | 0.76 / $89,062 | 0.70 / $90,360 |
| Entries until 3 PM | 0.85 / $82,580 | 0.91 / $92,418 |
| Before costs | 1.02 / $101,139 | 1.10 / $104,907 |
| Same-bar touches counted as targets | 0.91 / $93,184 | 0.93 / $96,136 |
| Short side | 0.94 / $96,119 | 0.68 / $84,424 |

- **Same-bar ambiguity:** 1 of 428 QQQ trades, none on SPY, so that assumption doesn't matter.
- **Profit and loss by year (QQQ long):** 2020 −$4,088, 2021 +$332, 2022 −$2,515, 2023 +$1,866, 2024 +$3,262, 2025 −$5,680, 2026 −$303.

## What this means
- **The fence bar has no edge on QQQ or SPY.** It's a coin flip with a 2:1 payoff that loses a little after costs. No version, filter, stop choice or side rescues it.
- **It matches our September opening-range work** and the published evidence: opening-range breakouts mostly don't survive costs.
- **Nothing changes in Plan B, the bots, MNQ or the EP watch.**

**Score:** 18 pre-declared tests. Only #14 passed (and it ties the market since 2000).
