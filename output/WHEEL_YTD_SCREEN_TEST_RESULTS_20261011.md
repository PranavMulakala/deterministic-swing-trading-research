# Test #33 results: a $50k wheel on Dec 31, 2025's screened movers, Jan 2 – Oct 9, 2026 (October 11, 2026)

**Verdict: FAIL** on all three checks. Plan: [WHEEL_YTD_SCREEN_TEST_PLAN_20261011.md](WHEEL_YTD_SCREEN_TEST_PLAN_20261011.md), including its pre-result correction for RNA.
- **Code:** `research/wheel_ytd_v1/` (29 unit tests, committed before the run).
- **Data:** Databento **$3.40** (stop $15).
- **Raw results:** `output/wheel-ytd-test-results.json` and its provenance manifest.
- **Independent verifier** (`research/wheel_ytd_v1/verify.py`):
  - all 169 main contracts match field by field;
  - all ten final values and all ten holding values match to the cent;
  - 12 of 12 random contracts match.
  - **One engine convention was confirmed and adopted:** no sale on the trading day before a split (CVNA, May 7).
- Research only. Dollars first, no SPY line.

## Rules
- One **$50,000** account per stock.
- ~1-week 0.30-delta puts; buy back at 50% profit.
- Calls only at or above the price paid.
- **No contract held over an earnings session.**
- The stocks were chosen using only data up to Dec 31, 2025.

## Results
| Stock | Wheel ending value | Avg $/week | Worst drop | Holding the stock ($50k) |
|---|---|---|---|---|
| LITE | $85,533 | +$867 | −30.7% | $143,640 |
| STX | $72,967 | +$560 | −17.3% | $136,460 |
| COHR | $66,791 | +$410 | −40.1% | $80,439 |
| RKLB | $62,755 | +$311 | −47.4% | $45,166 |
| PRAX | $53,719 | +$91 | −26.1% | $45,295 |
| RNA (Avidity, acquired Feb 27) | $51,431 | +$35 | 0% | $52,125 |
| AG | $41,724 | −$202 | −47.7% | $54,160 |
| HL | $38,841 | −$272 | −39.2% | $45,660 |
| RIVN | $38,271 | −$286 | −30.9% | $36,119 |
| CVNA | $37,035 | −$316 | −37.2% | $39,769 |
| **Average account** | **$54,907** | **+$120** | −31.7% | **$67,883** |
| **Median account** | $52,575 | +$63 | −34.0% | |

**Checks:**

| Check | Result |
|---|---|
| C1: average account ≥ $1,000/week | ✗ ($120) |
| C2: ≥ 7 of 10 accounts profitable | ✗ (6) |
| C3: median account's worst drop ≤ 25% | ✗ (−34.0%) |

## Information versions
| Version | Average account | Avg $/week | Median worst drop | Profitable |
|---|---|---|---|---|
| Main (skip earnings) | $54,907 | $120 | −34.0% | 6/10 |
| Earnings allowed | $54,979 | $121 | −33.9% | 5/10 |
| Hold to expiry (no 50% buyback) | $59,253 | $226 | −33.5% | 6/10 |
| **$25k, whole contracts** | **$25,464** | **$11** | −20.8% | 7/10 |

## What it shows
- **A fair "bullish movers" screen did pick LITE.** Wheeling it made about $867 a week, about 60% of what holding LITE made.
- **The typical account made $120 a week,** and four of ten lost $8–13k.
- **The wheel beat holding on stocks that fell or went sideways** (RKLB, PRAX, RIVN), because the premiums cushioned them. It trailed badly on the big winners (LITE, STX), where the calls were capped.
- **At $25k with whole contracts,** the higher-priced names can't be traded and the result is about flat ($11 a week).
- **Same direction as tests #29 and #32:** on $25–50k, the wheel hasn't produced $1,000 weeks.
