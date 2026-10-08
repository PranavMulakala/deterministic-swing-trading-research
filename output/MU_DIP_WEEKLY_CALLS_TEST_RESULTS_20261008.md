# Test #27 results: ~1-week MU calls on mornings MU opens down 2%+ (2020–2026)

**Verdict: PASS** on all three pre-declared checks (`MU_DIP_WEEKLY_CALLS_TEST_PLAN_20261008.md`, committed before any option data).
- **The edge is thin and not statistically strong** (about a 1-in-9 chance it is luck; see below).
- **Checks:** 4 unit tests pass. The independent verifier re-checked 12 random trades from the raw quote files, and all matched (contract, entry, exit, P&L). The trade list adds up to the reported total.
- **Data:** Databento OPRA quotes (about $1.6 of the owner's credit, approved, under the $5 hard stop) and Alpaca SIP.
- **Report:** dollars only, $1,000 per trade. Research, not advice.

## Main rule: buy the ~7-day at-the-money call at 10:00 on a 2%+ gap-down; sell at 2× or at expiration
| | Signal mornings | Ordinary mornings (200 random) |
|---|---|---|
| Trades | 181 | 200 |
| **Total** | **+$16,638** | −$9,727 |
| **Per trade** (avg / median) | **+$92 / +$88** | −$49 / −$630 |
| Win % | 50% | 45% |
| Hit +100% | 44% | 42% |
| Expired worthless | 37% | 44% |
| Best / worst trade | +$2,527 / −$1,000 | +$1,782 / −$1,000 |
| Longest losing streak | 9 trades (−$9,000) | 9 |
| Worst cumulative drop | −$11,572 | |
| Average 1-contract cost | $1,163 | $515 |

**By year (signal mornings):**
- 2020 +$2,342
- 2021 +$2,502
- 2022 +$4,290
- 2023 +$2,661
- **2024 −$6,513**
- 2025 +$8,539
- 2026 +$2,816

**Halves:** 2020–22 +$9,134; 2023–26 +$7,504.

## Pre-declared checks
| Check | Result |
|---|---|
| C1: total > 0 | ✅ +$16,638 |
| C2: both halves profitable | ✅ +$9,134 and +$7,504 |
| C3: beats ordinary mornings per trade | ✅ +$92 vs −$49 |

## How strong is it? (information only, computed after the result)
- **Spread of results:** the average is +$92 per trade, but individual trades vary by about ±$990.
  - That gives a t-statistic of **1.25** (2 or more is the usual bar).
  - The bootstrap range for the average runs from **−$30 to +$213**, with about an **11%** chance the true average is ≤ 0.
- **Vs ordinary mornings:** +$141 per trade, t = 1.38. **Suggestive, not proven.**
- **Information-only versions:**
  - sell at +50%: +$60/trade (65% wins), both halves positive;
  - no target (hold to expiration): +$173/trade, **but 2020–22 −$4,930**;
  - **only gaps of 3% or more: about flat (+$5/trade)**. A bigger dip did *not* help, which argues against a strong "the dip is the edge" story;
  - 2-week expiration: +$141/trade, but 2020–22 −$4,383.

## What it means
1. **It's the first options idea to pass a pre-declared test.** Buying a weekly MU call on a gap-down morning, then selling at a double or at expiration, beat buying the same call on ordinary mornings.
2. **But it's thin and noisy.**
   - About half the trades lose, and 37% go to zero.
   - Streaks of 9 losses happen.
   - 2024 lost $6.5k.
   - The statistics can't rule out luck.
3. **MU options are expensive now.** One at-the-money weekly costs about $1,160 at MU near $1,000, so "$1,000 per trade" means roughly one contract.
4. **The sensible next step is a forward paper test.** Add the rule to the forward watch so every future 2% gap-down morning is traded on paper. The live record decides whether it's worth real money. Keep the rule exactly as declared.
