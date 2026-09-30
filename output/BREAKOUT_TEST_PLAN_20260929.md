# Does the TikTok breakout strategy work on history? Pre-declared test (September 29, 2026)

Written and committed **before** any data for this test was downloaded or any result was computed. The source is TikTok video 1 (stock swing trading breakouts), transcribed on Sept 29. The owner asked: "set up the breakout test end to end 100%". Research only: no orders of any kind.

## Data
- **Prices:** Alpaca consolidated (SIP) daily bars, adjusted for splits and dividends. January 2016 to Sept 28, 2026, the full span available.
- **Universe:** US common stocks currently listed on NYSE, Nasdaq or NYSE American, as returned by Alpaca's asset list. Obvious funds and trusts are dropped: ETF, ETN, fund, trust, SPAC, warrant, unit and right in the name or symbol.
- **Known bias:** companies delisted before 2026 are missing. That flatters results, because failed companies never appear.

## The rules (checked after each day's close; trades happen at the close)
1. **Market filter (from the video):** SPY closes above its 10-day average. The 10-day average is above the 20-day, which is above the 50-day, and all three are higher than 5 trading days earlier. If this fails, no new trades that day.
2. **Liquidity (stands in for "market cap over $2 billion, volume over 750,000"):** close of at least $10. Average daily dollar volume over the last 20 days of at least $20 million. Average daily share volume of at least 750,000.
3. **Leadership (stands in for "the top sector on FinViz"):** the stock's 21-day return is in the top 30% of all stocks that pass step 2 that day.
4. **Pattern:**
   - **Prior run-up:** within the last 60 trading days, the highest close is at least 30% above the lowest close before it.
   - **Base:** the 10 days before today form a tight range. Highest high to lowest low is at most 12% of the highest high.
   - **Pullback:** the base's lowest low is no more than 25% below the run-up peak.
5. **Breakout day:**
   - Today's close is above the base's highest high.
   - Today's volume is at least 1.5 times its 20-day average.
   - The stop distance (close minus today's low) is between 0.5% and 10% of the close.
6. **Entry at today's close. Stop at today's low.**
7. **Size:** risk 1% of current account value, where shares = (1% of the account) ÷ (entry − stop). Each position is capped at 25% of the account. At most 10 positions at a time, one per stock. When there are more signals than open slots, the strongest 21-day return goes first.
8. **Exits:**
   - **Stop:** exits at the stop price, or at the open if the stock gaps below it.
   - **3rd trading day after entry:** sell 30% at the close and move the stop to the entry price (break-even).
   - **5th trading day:** sell another 20% at the close.
   - **The remaining 50%:** sell at the first close below the 10-day average from day 5 on, or at the break-even stop.
9. **Costs:** 0.1% slippage on every buy and sell. No commissions.
10. **Account:** $100,000 to start, cash only. Unused cash earns nothing.

## It counts as working only if all three hold
1. The **profit factor** (total gains ÷ total losses) is at least **1.3** over the whole period.
2. **Profitable in both halves:** 2016–2020 and 2021–Sept 2026.
3. The worst **peak-to-trough drop** in account value is at most **25%**.

Otherwise the conclusion is that it did not show an edge. Nothing will be tuned afterwards: no other thresholds, windows or exits. Results will be shown next to simply holding SPY, for context only.

## Also reported
Trades per year, win rate, average win and loss in percent, average hold time, yearly returns, best and worst trade, and how often the market filter was off.

## Known limits, stated in advance
- **Daily bars only.** The video enters intraday as the breakout happens; here the entry is at the close. The video's volume check can only be confirmed at the close anyway.
- **No sector data.** The leadership rule is an approximation.
- **Survivorship bias** favors the strategy.
- **Discretion:** the video's trims ("10–50%") and pattern judgement are discretionary. These rules are one reasonable reading of them, fixed in advance.
