# Test #24: buying a short-dated SPY call every week: results (October 6, 2026)

- **Plan:** [SHORT_DATED_SPY_CALLS_TEST_PLAN_20261006.md](SHORT_DATED_SPY_CALLS_TEST_PLAN_20261006.md) (8deb41c). The code (c0414e9, 3 unit tests plus an independent verifier) was committed before the run.
- **Data:** SPY option quote snapshots from Databento OPRA, 2016–2025. There's no 2026 data.
- **Results:** `output/short-dated-calls-test-results.json` + provenance.
- **The verifier matched all 12 sampled trades** (expiration, strike, the ask paid, value at expiration), and the trade list adds up to the reported total.

## Verdict: FAILED all 5 checks
**The rule:** every Monday at the close, buy the at-the-money SPY call expiring about a week out, pay the ask, spend 2% of the account, and hold to expiration.

| Jan 2020 – Dec 2025 | Weekly calls (2% a week) | Holding SPY |
|---|---|---|
| $100,000 became | **$144,900** (+6.4%/yr; **$18k of that was T-bill interest** on idle cash) | **$229,061** (+14.9%/yr) |
| Worst drop | **−34.4%** | −33.8% |
| Profit made by the calls themselves | **+$26,716** on 313 calls | |
| Halves 2020–22 / 2023–25 | −0.6% / +45.8% | |

**What a typical call did:**
- **40%** expired worthless.
- **42%** made money.
- **The median call lost 37.5%.**
- The average was +6.4%, carried by a few big winners; the best was +390%.

**Year by year (call profit):**

| Year | Call profit |
|---|---|
| 2020 | +$19.7k |
| 2021 | +$17.8k |
| **2022** | **−$42.1k** |
| 2023 | +$10.4k |
| 2024 | +$18.2k |
| 2025 | +$2.7k |

**2016–2019, a calm rising market:** $210k vs SPY $171k. ATM weekly calls do pay in quiet uptrends, and give it back when the market turns, as in 2022.

## Information only
| Version | $100k became (2020–25) | Worst drop | Expired worthless |
|---|---|---|---|
| **1.5% out of the money** (like the 790 call) | **$64,187** | −50% | **74%** |
| Mid-price fills | $145,557 | −34% | 40% |
| 5% of the account a week | $163,005 | **−70%** | 40% |
| 10% a week | **$64,737** | **−94%** | 40% |
| Sell at +100% | $133,092 | −20% | 39% |
| A flat $1,000 a week | $136,205 | −11% | 40% |

## What this means
- **Out-of-the-money short-dated calls,** the kind in the $7M flow post, lost almost half the account: about 3 in 4 expired worthless.
- **At-the-money calls** made some money from 2020 to 2025, but less than half of SPY, with the same kind of crash in 2022.
- **Betting bigger made it far worse:** 10% a week wiped out 94% at the worst point.
- **Buying short-dated calls is a bet on direction *and* timing within days.** The median call loses about a third of its cost.
- **Nothing changes in Plan B or the bots.**
