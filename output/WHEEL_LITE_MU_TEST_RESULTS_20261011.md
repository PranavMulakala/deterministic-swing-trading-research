# Test #32 results: the weekly wheel on LITE and MU (October 11, 2026)

**Verdict: FAIL.** It cleared the $1,000-a-week bar (C1) but failed C2 (lost money in 2020–2022) and C3 (worst drops −62% LITE, −50% MU). Plan: [WHEEL_LITE_MU_TEST_PLAN_20261010.md](WHEEL_LITE_MU_TEST_PLAN_20261010.md), committed before any LITE/MU option data.
- **Code:** `research/wheel_lite_mu_v1/` (29 unit tests, committed before the run).
- **Data:** Databento **$7.57** (hard stop $12).
- **Raw results:** `output/wheel-lite-mu-test-results.json` and its provenance manifest.
- Research only. Dollars first. No SPY; the comparison is holding the same stock.

## Rules in one line
Sell a ~1-week put at 0.30 delta; buy it back at 50% profit. If assigned, sell 0.30-delta calls, **never below the price paid**. $100,000 per stock, Jan 2, 2020 – Oct 9, 2026.

## Main result
| | LITE wheel | MU wheel | **Both ($200k)** | Just holding both |
|---|---|---|---|---|
| Ending value | $397,420 | $524,411 | **$921,832** | **$3,208,339** |
| Average $ per week | $840 | $1,199 | **$2,039** | $8,498 |
| Median week | $640 | $836 | $1,154 | $1,473 |
| Weeks ≥ $1,000 | 48.3% | 48.3% | 50.3% | 52.0% |
| Losing weeks | 46.3% | 45.5% | 46.6% | 46.9% |
| Worst week | −$48,651 | −$61,689 | **−$83,369** (Jul 17, 2026) | −$391,519 |
| Worst month | −$45,102 | −$134,990 | **−$180,091** (Jul 2026) | −$774,476 |
| Worst drop from a high | **−62.1%** | −49.8% | −43.7% (−$254,882) | −51.0% |
| 2020–2022 | −$32,610 | −$5,605 | **−$38,215** | −$44,939 |
| 2023 – Oct 2026 | +$330,030 | +$430,016 | +$760,046 | +$3,053,277 |

**By year (both accounts):**

| Year | P&L |
|---|---|
| 2020 | +$34,071 |
| 2021 | +$35,079 |
| 2022 | −$107,364 |
| 2023 | +$52,485 |
| 2024 | +$13,342 |
| 2025 | +$266,732 |
| 2026 | +$427,488 |

**Checks:**

| Check | Result |
|---|---|
| C1: averages ≥ $1,000/week | ✓ ($2,039) |
| C2: each account profitable in both halves | ✗ |
| C3: each account's worst drop ≤ 25% | ✗ |

## What really happened
- **It sold only 261 contracts in 6.75 years:** 18 assignments, 17 call-aways, 86% closed at 50% profit.
- **Most of the time it was holding shares and allowed to sell nothing:**
  - Both accounts together sat **554 weeks** that way (2,323 days), holding shares with no call at or above cost available.
  - The calls "never below cost" rule turned the wheel into **"buy LITE/MU on a dip, then hold."**
- **The money came from that holding,** when LITE and MU went up ~10–19× in 2025–2026. Premiums collected: $1,141,130. Buybacks: −$462,778. Share gains: +$22,640, mostly realized below later prices.
- **Before the boom it lost money:** −$38,215 over 2020–2022. The worst year was 2022 (−$107,364).
- **Recent window (information):**

  | Since Jan 2, 2025 | Ending value | Avg $/week | Weeks ≥ $1,000 | Worst drop |
  |---|---|---|---|---|
  | Fresh $200k start, wheel | $681,880 | $5,182 | 63% | −37% |
  | Fresh $200k start, holding | $2,471,769 | — | — | −45% |

## Information versions (one change each)
| Version | Ending value | Avg $/week | Weeks ≥ $1k | Worst drop | 2020–22 |
|---|---|---|---|---|---|
| **Main** | **$921,832** | **$2,039** | 50.3% | −43.7% | −$38,215 |
| Calls allowed below cost | $453,983 | $717 | 54.0% | −40.0% | −$12,474 |
| delta 0.20 | $1,033,819 | $2,355 | 50.3% | −44.8% | −$27,855 |
| Hold to expiry (no 50% buyback) | $1,392,870 | $3,370 | 52.0% | −45.2% | −$5,130 |
| Skip earnings | $915,023 | $2,020 | 50.8% | −45.1% | −$28,293 |
| Whole contracts only | $829,157 | $1,777 | 50.3% | −41.4% | −$34,470 |

- **Same lesson as test #29:** selling calls below cost roughly halves the result ($454k vs $922k).
- The versions that hold more stock did better here, because LITE and MU soared. That's hindsight about these two stocks, not a rule.

## Independent check
`research/wheel_lite_mu_v1/verify.py`, written separately from the engine:
- **All 261 main contracts match exactly,** and both final values match to the cent (LITE $397,420.48, MU $524,411.42). Holding matches too, and all 12 random contracts pass.
- **One reading difference, resolved:**
  - The verifier first scanned buyback quotes only through 15:59. That missed one LITE buyback at a 16:00 quote (Sep 4, 2025, ask $1.95 = 50% of $3.90).
  - The plan's window runs through 16:00, so the engine is right. That reading makes LITE about $3,000 *lower* (conservative).
- **Interest:** the engine credits each day's interest at the previous day's monthly rate. The verifier matches it with `--rate-prev`; with the other reading, final values move by under $20.
