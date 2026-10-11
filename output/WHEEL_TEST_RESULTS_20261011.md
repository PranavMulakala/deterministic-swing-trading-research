# Test #29 results: the Reddit wheel on AVGO, CRM, AMZN, META, CBOE (October 11, 2026)

**Verdict: FAIL** on all three checks. Plan: [WHEEL_TEST_PLAN_20261010.md](WHEEL_TEST_PLAN_20261010.md), committed before any option data.
- **Code:** `research/wheel_test_v1/` (36 unit tests, committed before the run).
- **Data:** Databento OPRA, **$28.76** of the owner's credit (hard stop $40).
- **Raw results:** `output/wheel-test-results.json` and its provenance manifest.
- Research only. Dollars first; the comparison is holding the same five stocks, no SPY.

## The headline the poster would see vs the real result ($200,000, Jan 2, 2020 – Oct 9, 2026)
| | Wheel (the poster's rules) | Just holding the same 5 stocks |
|---|---|---|
| **"Premiums collected"** (what his tracker shows) | **$1,129,357** | — |
| Premiums kept after buybacks and fees | $942,971 | — |
| **Losses on the shares** (assigned high, called away low) | **−$868,444** | — |
| **Ending value** | **$310,791 (+$110,791)** | **$880,291 (+$680,291)** |
| Average $ per week | **$313** | $1,922 |
| Median week | $1,337 | $1,048 |
| Weeks ≥ $1,000 | 52.8% | 50.0% |
| Losing weeks | 40.1% | 47.2% |
| Worst week | −$28,182 (Jun 5, 2026) | −$112,368 |
| Worst month | −$41,369 (Jun 2026) | −$150,253 |
| Worst drop from a high | −30.2% (−$77,743) | −42.1% (−$197,177) |
| 2020–2022 | **−$12,275** | +$9,370 |
| 2023 – Oct 2026 | +$123,066 | +$670,921 |

**By year (wheel):**

| Year | P&L |
|---|---|
| 2020 | +$18,991 |
| 2021 | +$34,755 |
| 2022 | −$66,021 |
| 2023 | +$83,788 |
| 2024 | +$41,031 |
| 2025 | +$31,123 |
| 2026 | −$32,875 |

**Checks:**

| Check | Result |
|---|---|
| C1: beat holding | ✗ ($310.8k vs $880.3k) |
| C2: both halves profitable | ✗ (2020–2022 lost $12.3k) |
| C3: worst drop ≤ 25% | ✗ (−30.2%) |

## Why it lost to holding
- **It had a lot of winning trades:** 1,997 contracts, 74% closed early at 75% profit, and only 1.6% expired worthless.
- **But the share trades lost:**
  - 243 assignments and 242 call-aways.
  - The calls had no price floor, so shares were bought on dips and sold right back near the bottom.
  - Selling at the call strike gave up **$537,867** against the expiration-day prices.
- **The premiums are real income, but they came with share losses almost as big.** Once those losses are counted, the "$1.1M premiums" becomes +$110,791.
- **By stock:**

  | Stock | Ending value | Holding the stock |
  |---|---|---|
  | AVGO | $100,260 | $467,038 |
  | CRM | $31,810 | $56,138 |
  | AMZN | $65,050 | $110,946 |
  | META | $63,779 | $138,617 |
  | CBOE | $49,893 | $107,552 |

## Information versions (one change each; not part of the verdict)
| Version | Ending value | Avg $/week | Weeks ≥ $1k | Worst drop | 2020–22 |
|---|---|---|---|---|---|
| Main (delta 0.35, 75% close) | $310,791 | $313 | 52.8% | −30.2% | −$12,275 |
| delta 0.25 | $334,729 | $381 | 50.6% | −30.6% | −$18,197 |
| delta 0.45 | $314,774 | $324 | 53.4% | −29.5% | −$7,775 |
| Hold to expiry (no early close) | $392,825 | $545 | 52.0% | −29.0% | −$16,632 |
| **Calls never below the price paid** (`basis_floor`) | **$654,818** | **$1,285** | 52.0% | **−41.5%** | +$1,375 |
| Whole contracts only | $308,144 | $305 | 47.7% | −20.2% | +$3,537 |

**The biggest lesson:** one rule change, never selling a call below what you paid (ScottishTrader's rule), turned $310k into **$655k, about $1,285 a week**.
- It still trailed holding ($880k), and its worst drop was deeper (−41.5%), because it sits on shares through downturns.
- This is an information view picked after the fact. Test #32 (LITE/MU) uses this floor in its pre-declared main rules.

## Independent check
`research/wheel_test_v1/verify.py` was written separately from the engine and recomputes everything from the raw quote files.
- **12 random contracts:** all match field by field (pick, sale price, buyback or expiration, P&L). Holding the five stocks also matches ($880,291.28 vs $880,291.08).
- **The full replay:**
  - It reproduces every main contract except one last-day sale in CRM and one in AMZN. The engine sells on Oct 9, 2026, under its documented judgment call 13; the verifier doesn't.
  - Sleeve final values agree within **$4–$98** each (≈ $95 on $310,791). The remaining gap comes from small convention differences (that last-day sale, fee accounting and AVGO's split-eve handling) and wasn't itemized further.
  - **No difference comes near changing any check.**
- **One false alarm:** the verifier's "cache vs replay" alarm is expected. The data cache also holds the info versions' contracts.
