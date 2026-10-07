# Test #25 results: covered calls on SPY (October 7, 2026)

**Verdict: FAIL.** The rules were pre-declared in `COVERED_CALLS_TEST_PLAN_20261007.md`, committed before the code and before any result.
- **Report:** dollars only, with no SPY comparison line (owner's instruction).
- **Checks:** 3 unit tests pass. The independent verifier re-picked 12 random calls from the raw option files, and all matched (expiration, strike, sale price and amount paid at expiration). The trade list adds up to the reported call P&L.
- **Data and code:** `output/covered-calls-test-results.json` and `research/covered_calls_test_v1/`.

## The main version: $100,000 of SPY shares from Jan 2, 2020, selling a ~30-day call ~2% above the price every month
| | Dollars |
|---|---|
| **Account at the end of 2025** | **$181,282 (+$81,282)** |
| Average per week | **+$259** (median week +$574) |
| Weeks with a gain | 62% |
| $1,000+ weeks | 120 of 314 |
| Worst week / worst month | −$12,543 / −$10,225 |
| Worst drop from a high | −$30,990 (−30.4%) |
| Profit, 2020–22 / 2023–25 | +$6,966 / +$74,316 |
| Dividends received | +$9,970 |

**The calls on their own:**
| | Dollars |
|---|---|
| Calls sold | 74 |
| Premium collected | +$63,344 |
| Paid back when SPY finished above the strike | −$89,202 |
| **The calls' net result** | **−$25,858** |
| Expired worthless (kept the full premium) | 51% |
| Worst single call | −$5,836 |
| Calls' profit factor | 0.55 (the bar was 1.3) |
| By year | 2020 −$9,467 · 2021 −$6,421 · 2022 −$699 · 2023 −$1,118 · 2024 −$8,649 · 2025 +$496 |

## Pre-declared checks
| Check | Result |
|---|---|
| C1: the calls earn their keep (net > 0 and profit factor ≥ 1.3) | ❌ −$25,858; profit factor 0.55 |
| C2: profitable in both halves | ✅ +$6,966 and +$74,316 |
| C3: worst drop ≤ 25% | ❌ −30.4% (COVID, March 2020) |

**Stress years, 2016–2019 (separate $100,000):**
- The account ended at **$152,365**.
- The calls again **lost $13,561** (profit factor 0.47).
- Worst drop: −17.3%.

## Information-only versions (2020–2025, $100,000 each)
| Version | Account profit | Per week | Calls' net result | Expired worthless | Worst drop |
|---|---|---|---|---|---|
| **Main: 2% above, ~30 days** | +$81,282 | +$259 | **−$25,858** | 51% | −30.4% |
| At the money, ~30 days | +$68,932 | +$220 | −$36,157 | 38% | −27.0% |
| 5% above, ~30 days | +$105,183 | +$335 | −$7,788 | 80% | −32.9% |
| Weekly, 1% above | +$80,767 | +$257 | −$27,111 | 62% | −26.7% |
| Sold at mid price | +$82,639 | +$263 | −$25,036 | 51% | −30.3% |

## What it means, plainly
1. **Selling calls "wins" often but loses big.**
   - About half the calls expired worthless, so the account kept the premium.
   - But when SPY rallied past the strike, the payback was bigger than everything collected. That's because 2020–2025 had many fast rallies: 2020's rebound, 2021, 2023–24.
2. **Every version lost money on the calls, in every window.**
   - Selling further from the price (5% above) lost the least ($7,788), because it rarely got hit.
   - It also collected only $17,194 in premium over 6 years: small income.
3. **The money came from owning the shares,** plus $10k of dividends. The calls subtracted from it.
4. **Why Joey's MU trade made money anyway:**
   - MU went **down and sideways** during his trade, which is exactly when covered calls win.
   - He also **actively adjusts**: rolling, restructuring and adding puts. This test is mechanical, with no adjustments.
   - So his result is real, but it came from that period and his active management, not from covered calls being a winner by themselves.
5. **When covered calls help:** flat or slowly falling markets, or when you want income and are fine selling your shares at a set price.
   - In a market that rises in jumps, they cap the gains that pay for everything else.

Joey's active rolling and restructuring can't be tested from these rules. If he shares his exact roll rules, they could be pre-declared as a new test.
