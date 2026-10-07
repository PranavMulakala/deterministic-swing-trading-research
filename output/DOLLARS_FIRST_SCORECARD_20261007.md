# Every strategy we've tested, in dollars (October 7, 2026)

- **The owner's ask:** judge strategies by the money they make week to week, not only against SPY.
- **How to read it:** every account starts 2020 with **$100,000**, except Plan B, which uses its real $60,000 per buy. "What doing nothing would have made" (the same money in SPY) is the last column.
- **Data:** `output/dollars-first-scorecards-20261007.json`.
- **Code:** `research/scorecard_v1/` (scorecard module + rebuild of each test's account).
- **Nothing here changes any test's verdict.**

## Ranked by profit, Jan 2020 to late 2026 ($100,000 start)
| Strategy (test #) | Profit | Average per week | Weeks up | $1,000+ weeks | Weeks losing $1,000+ | Worst week | Worst month | Worst drop from a high | SPY, same money |
|---|---|---|---|---|---|---|---|---|---|
| Top 5 LITE-like momentum stocks (#17) | **+$298,862** | +$847 | 53% | 177 of 353 | 154 | **−$126,519** | **−$170,960** | **−$439,184** (May → Jul 2026) | +$159,195 |
| 2× the market above its 200-day, else T-bills (#14, the one pass) | +$205,049 | +$588 | 56% | 146 of 349 | 105 | −$22,366 | −$33,351 | −$66,665 | +$159,039 |
| **SPY, just holding it** | **+$161,631** | **+$458** | 57% | 165 of 353 | 108 | −$16,936 | −$12,753 | −$38,523 | n/a |
| Revenue acceleration "LITE fingerprint" (#20) | +$113,809 | +$322 | 54% | 162 of 353 | 144 | −$19,596 | −$24,882 | −$72,092 | +$159,195 |
| SPY only above its 50-day average (#5) | +$73,383 | +$208 | 47% | 119 of 353 | 84 | −$5,843 | −$8,526 | −$27,694 | +$159,195 |
| Buy a ~7-day SPY call every week (#24, to Dec 2025) | +$44,900 | +$143 | 45% | 113 of 314 | 133 | −$5,869 | −$9,295 | −$48,963 | +$129,061 |
| Sell a SPY put every month (#10, to Dec 2025) | +$32,670 | +$104 | **76%** | 25 of 314 | 19 | −$12,306 | −$10,746 | −$22,427 | +$129,061 |
| RFK range-fakeout-killshot (#23) | +$23,877 | +$68 | 50% | 52 of 353 | 45 | −$5,369 | −$6,627 | −$15,433 | +$160,559 |
| Buy big drops in strong stocks (#19) | +$2,544 | +$7 | 49% | 114 of 353 | 116 | −$21,047 | −$31,450 | −$77,444 | +$159,195 |
| Qullamaggie earnings gap-up (#16) | +$2,192 | +$6 | 3% (rarely trades) | 3 of 353 | 4 | −$1,268 | −$1,268 | −$3,480 | +$159,195 |
| Breakouts, TikTok/Qullamaggie style (#3) | −$9,560 | −$27 | 24% | 45 of 353 | 53 | −$6,333 | −$8,279 | −$30,223 | +$159,195 |
| Stocks in Play opening-range breakout (#21) | −$66,271 | −$188 | 22% | 9 of 353 | 7 | −$2,182 | −$3,339 | −$70,944 | +$160,559 |

## Plan B (your LITE dip rule), on $60,000
| | Profit | Average per week | Weeks up | $1,000+ weeks | Weeks losing $1,000+ | Worst week | Worst month | Worst drop | SPY, same $60,000 |
|---|---|---|---|---|---|---|---|---|---|
| **2025 – Sep 2026 (LITE's boom)** | **+$125,568** | **+$1,365** | 66% | **52 of 92** | 20 | −$9,275 | −$9,245 | −$24,597 | +$20,120 |
| 2022 – 2024 (LITE fell about 70%) | +$61,756 | +$393 | 45% | 61 of 157 | 32 | −$8,644 | −$9,214 | −$22,736 | +$16,917 |

**The big caveat:**
- These numbers are **LITE only, chosen after its run.**
- Test #15 ran the same rule on 100 other volatile stocks picked without hindsight, and it **lost money** ($100k → $93k), because a few stuck buys trapped the money.
- So Plan B's dollars come from **LITE itself**, which is the "conviction about the business" part.

## What the dollars say
1. **Only three things made more than holding SPY, and each needs a strong stomach:**
   - **#17 (the hot volatile stocks)** made the most, but fell **$439,000 from its high in 11 weeks** this summer.
   - **#14 (2× leverage in uptrends)** made $45k more than SPY with a drop of $67k (SPY's worst was $39k).
   - **Plan B on LITE** made $1,365 a week, but only because LITE was the stock.
2. **The "safe-feeling" strategies make steady small money:**
   - **Selling puts** wins 76% of weeks, but averages $104 a week.
   - **RFK** averages $68 a week.
3. **$1,000 weeks:**
   - **SPY alone** gave **165** of 353 weeks with $1,000 or more on $100k. Its average is $458 a week.
   - **Only Plan B on LITE** (52 of 92) did it more often, with a smaller account.
4. **Every strategy also has $1,000+ losing weeks.** Even SPY had 108. Making a lot every week isn't something any tested rule did.
