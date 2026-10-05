# Is the LITE "morning dip, sell +2%" rule a general pattern? Pre-declared test #15 (October 5, 2026)

Written and committed **before** any test-period intraday data was downloaded or any result computed. Research only; no orders. It changes nothing in Plan B, the bots or MNQ. It is not a change to the LITE formula (the freeze), because it applies the **unchanged** Plan B rule to other stocks.

**Owner's request:** "start step 1 … this is for all stocks you can find … help me find one 100%". Steps 2 (calls instead of shares) and 3 (paper trading) only follow **if step 1 passes**.

## The hindsight trap, and how this test avoids it
- **Picking stocks that already soared** (our Oct 2 LITE-like list: MU, SNDK, WDC, COHR…) makes any buy-the-dip rule look great.
- **So the main universe is chosen using only data up to Dec 31, 2021,** then tested Jan 3, 2022 – Sep 30, 2026. The LITE-like list is reported separately and labelled hindsight.

## Universe (main): the 100 most volatile big stocks as of Dec 31, 2021
- **Source:** the daily bars on disk for 5,259 US stocks (`outputs/breakout_data/`, Alpaca SIP, adjusted).
- **Eligible on Dec 31, 2021:**
  - closing price at least $20;
  - average daily dollar volume over the prior 60 trading days of at least **$200 million**.
- **Rank** by average daily range, (high − low) ÷ previous close, over those 60 days, and **take the top 100.**
- **Known bias:** the disk data only includes companies still listed in 2026. 2021's volatile names that later delisted (busted SPACs, meme stocks, some Chinese ADRs) are missing, which **flatters** the rule. Stated, not fixable with this data.

## Universe (information only, hindsight): the Oct 2 LITE-like list
MU, SNDK, WDC, STX, DELL, INTC, TER, MRVL, COHR, CIEN, HPE, plus LITE itself. Tested over the same window, results labelled "hindsight".

## Data for the test
- **Source:** Alpaca SIP **30-minute bars**, regular session, Jan 3, 2022 – Sep 30, 2026. The 9:30–10:00 bar gives exactly the open, the morning low and the 10:00 price that Plan B uses. The later 30-minute bars give the rest of the entry day.
- **Later days:** daily bars from the same disk files (and Alpaca for any gap).
- **Splits:** prices are split-adjusted, as in all our tests.

## The rule (Plan B / the LITE bot's v1, unchanged)
1. **Signal at 10:00:**
   - the 9:30–10:00 low is at least **1% below the 9:30 open**, **and**
   - the 10:00 price (that bar's close) is **below the open**.
2. **Buy** at the 10:00 price + 0.1% (Plan B's limit buffer).
3. **Sell** with a standing limit order at **entry × 1.02**, filled the first time a later price reaches it:
   - later 30-minute bars that day;
   - after that, each day's high (a gap open above it fills at the open).
4. **No stop. One position per stock at a time.** No new buy in a stock while it's held.
5. **Costs:** the 0.1% entry buffer, plus 0.05% on the sale.

## Portfolio simulation (the verdict uses this)
- **$100,000 cash.** Each buy uses **$10,000**, so at most 10 positions at once.
- **When more than one stock signals the same morning,** fill the free slots in order of the biggest morning dip.
- **Skip the signal** if no slot is free or there isn't enough cash.
- **Idle cash earns nothing.**
- **Daily value:** cash plus open positions at that day's close.
- **Benchmark:** SPY with dividends, same dates.

## It counts as a real pattern only if all hold (main, hindsight-free universe)
**Bar A:**
1. Profit factor of at least **1.3**, with all trades **including still-open positions marked at the final close**.
2. Profitable in **both halves:** 2022–2023 and 2024–Sep 2026.
3. Worst peak-to-trough drop of at most **25%**.

**Bar B (vs SPY):**
4. Max drawdown at least **5 points smaller** than SPY's.
5. CAGR ÷ |max drawdown| **higher** than SPY's.

If any fail, the pattern isn't shown, and **steps 2–3 don't proceed** on this rule. **Nothing will be tuned afterwards:** no other dip sizes, targets, stops, slot sizes or universe sizes.

## Also reported
- Trades, win rate, and how long winners and losers were held.
- **Positions still stuck at the end and their losses.**
- The worst single trade.
- Per-stock results; how many stocks were profitable.
- The same portfolio on the hindsight LITE-like list.
- Provenance manifest.

## Checks
- Unit tests on hand-built bars: the signal, a same-day exit, a later-day exit, a gap-up fill, stuck to the end, slot limits.
- An independent recount of every signal and exit for 5 random stocks with separately written code.
