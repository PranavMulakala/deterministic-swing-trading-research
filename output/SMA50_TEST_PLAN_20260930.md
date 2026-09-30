# Does the video's 50-day moving-average rule hold up on SPY? Pre-declared test (September 30, 2026)

Written and committed **before** any result was computed. Research only: no orders of any kind.

**Source:** Mind Math Money, "AI Trading Full Course" [0:50–1:01]. The rule was backtested on Bitcoin from May 2015, where it beat buy and hold 1.8× with a 54% worst drop. The owner said: "Yes, let's run it... let's make sure this test works at least. But don't be biased."

**Why SPY:** Bitcoin was hand-picked with hindsight, as the best-performing asset of the decade. SPY is the market the owner actually holds and compares everything against. Its data is already on disk, so there's no new download.

## Data
- SPY daily bars already on disk: `outputs/breakout_data/SPY.csv.gz`. Alpaca SIP, adjusted for splits and dividends, Jan 4, 2016 to Sept 28, 2026 (2,699 days).
- Because the prices are dividend-adjusted, both the rule and buy and hold get dividends while invested.

## The rule, exactly as in the video (checked after each day's close)
1. **Indicator:** the 50-day simple moving average of the adjusted close, including today. The first usable day is the 50th bar.
2. **Buy:** if not holding and today's close is **above** the 50-day SMA, buy at the **next day's open**.
3. **Sell:** if holding and today's close is **below** the 50-day SMA, sell at the **next day's open**.
4. **A close exactly equal to the SMA** changes nothing.
5. **Other rules:**
   - Long only, one position.
   - The whole account goes in each trade, with fractional shares allowed.
   - Cash earns nothing while out.
6. **Why the next day's open:** you only know the close after the market shuts. This is also TradingView's default fill in the video's strategy tester.

## Costs and account
- **0.1% on every buy and every sell,** the video's own cost setting. That's conservative for SPY; the real spread is about 0.01%.
- **$100,000 start,** marked at each day's close.
- **A trade still open on Sept 28, 2026** is closed at that day's close, after costs, for the trade statistics.

## Benchmark: buy and hold SPY
Buy at the open of the same first day the rule could first trade (the day after the 50th bar), hold to Sept 28, 2026. Pay the same 0.1% on the way in and out.

## Verdict A: the same pass bar as every earlier test (all three must hold)
1. **Profit factor** (total $ of winning trades ÷ total $ of losing trades) is at least **1.3**.
2. **Profitable in both halves:**
   - 2016–2020: account at the last close of 2020 minus the start.
   - 2021–Sept 2026: the final account minus the account at the end of 2020.
3. **Worst peak-to-trough drop** in daily account value is at most **25%**.

## Verdict B: the video's actual claim, that moving averages are "better used to avoid downside" (both must hold)
1. The rule's worst drop is at least **5 percentage points smaller** than buy and hold's.
2. The rule's **yearly growth ÷ worst drop** (CAGR ÷ |max drawdown|) is **higher** than buy and hold's. This checks that it bought safety cheaply: it isn't enough to just hold less stock.

**How the two verdicts fit together:**
- **A** asks "is it a strategy that works on its own?"
- **B** asks "is it a better way to hold the market?"
- Both are fixed now, before the results. If only B passes, the honest description is "a risk-reduction tool", not "a money-making edge".

## Checks that the test itself works (all must pass, or the results don't count)
1. **Unit tests on made-up prices:**
   - a hand-built series with known crossings must produce the exact trades, fills, costs and ending value worked out by hand;
   - a price that never closes above its SMA must produce zero trades;
   - a price that stays above must produce one trade that matches buy and hold, less the 50-day delay.
2. **Two independent calculations must agree:**
   - **the trade loop:** trade by trade;
   - **a daily-returns calculation:** position each day × SPY's daily return, minus costs on switch days.

   Their ending values must match to within **$1**.
3. **Data consistency:** SPY's close-to-close change over the pullback test's own date range (from its first equity-curve day to Sept 28, 2026) must reproduce that test's +348.6% figure. It's the same data file, so this confirms we're reading it the same way.
   - *Correction made before any result was computed:* the first version of this plan said "from Jan 4, 2016". That was wrong, because the pullback test's figure started after its 200-day warm-up.

## Nothing will be tuned afterwards
- No other lengths (20, 100, 200 days), no other markets, no stops, no filters, no other windows.
- The result stands as one run.
- **Deliberately not adding "info-only" variants.** Showing several versions after the fact is how bias creeps in.

## Also reported (information only)
- **Trading activity:** number of trades, trades per year, win rate, and average win and loss.
- **Time in the market:** percent of days holding SPY.
- **Returns:** yearly return of the rule vs SPY.
- **Rough patches:** the drops in late 2018, early 2020 and 2022 for both.
- **Growth and risk:** CAGR and final value for both.

## Known limits, stated in advance
- **Cash earning nothing is harsh on this rule.** In practice, cash in a brokerage sweep or T-bills earned roughly 0–5% a year over this period. The report will give time out of the market so this effect can be estimated. It is not modelled, to stay consistent with the earlier tests.
- **Taxes are ignored.** In a taxable account, every sale is taxable. That's a real cost for this rule that buy and hold mostly avoids.
- **One market, one decade (2016–2026).** A pass would still be one sample, not proof.
- **Check not yet run (needs the owner's OK for a free Alpaca crypto download):** re-running the rule on Bitcoin from May 2015 to see whether our code reproduces the video's numbers (100 trades, about 29% win rate, profit factor about 2.1). This would be a check that our code matches TradingView's, not part of the verdict.
