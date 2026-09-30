# Does the course's "pullback, then first turn candle" strategy work on history? Pre-declared test (September 29, 2026)

Written and committed **before** any result was computed. Research only: no orders of any kind.

**Source:** "Trading for Beginners Part 1", the made-up strategy shown at 1:21–1:35 and on the backtest sheet at 1:44. The instructor says at 1:50 it is "not an actual strategy that I have any idea that will produce a profit". The owner asked: "set up the test end to end 100%".

## Data
- **Prices:** the daily bars already downloaded for the breakout test (`outputs/breakout_data/`). These are Alpaca SIP bars adjusted for splits and dividends, January 2016 to Sept 28, 2026, for 5,259 US stocks plus SPY. **No new download.**
- **Why stocks, not currencies:** the video trades forex, but US forex is the less practical market for the owner, and this data is already on disk. The trigger and exit rules are the same on any daily chart.
- **Known bias:** companies delisted before 2026 are missing, which flatters long trades.

## What counts
- **The long side is the main test.** The owner's accounts are cash-only and can't short, so only the long side counts toward the verdict.
- **The short side is reported for information only.** It mirrors the long rules exactly and does not count.

## Rules for the long side (checked after each day's close)
1. **Liquid stock:** close of at least $10, and average daily dollar volume over the last 20 days of at least $20 million.
2. **Uptrend (stands in for "higher highs and higher lows"):**
   - The 50-day average is above the 200-day average.
   - The 50-day average is higher than it was 10 trading days earlier.
3. **A run, then a pullback:**
   - The **peak day** is the day with the highest high in the previous 20 trading days (the latest such day on ties).
   - The peak day is 3 to 20 trading days before today.
   - **No day between the peak and today closed above the prior day's high.** This makes today the *first* turn candle of the pullback.
4. **Signal (the video's "higher-high, higher-close" candle):** today's close is above yesterday's high.
5. **Order levels:**
   - **Entry:** buy stop at today's high + 0.1% (the video uses 2 pips).
   - **Stop:** the lowest low from the day after the peak through today, − 0.1%.
   - **Target:** the highest close in the previous 20 trading days, − 0.1% (the video's "highest close of the run, less 2 pips").
6. **Only take it if** the target is above the entry and the reward is at least the risk: (target − entry) ≥ (entry − stop).
7. **Fill, next trading day only:**
   - If the open is at or above the entry, fill at the open.
   - Otherwise, if the high reaches the entry, fill at the entry.
   - Otherwise cancel the order.
8. **Exits, from the fill day on:**
   - **Open at or below the stop:** exit at the open.
   - **Open at or above the target:** exit at the open.
   - **Otherwise, low at or below the stop:** exit at the stop.
   - **Otherwise, high at or above the target:** exit at the target.
   - **If the stop and the target are both touched on the same day,** count it as a stop (the cautious assumption).
   - **After 60 trading days in the trade,** exit at the close. This backstop is not in the video.
9. **One trade per stock at a time.** A new trade in the same stock needs a peak day later than the previous trade's exit (the video's "wait for a new high").
10. **Size:**
    - Risk 1% of the account: shares = (1% of account value at the signal close) ÷ (entry − stop).
    - Cap each position at 25% of the account, and at the cash available.
    - At most 10 positions (counting pending orders).
    - **When there are more signals than open slots,** the most liquid stocks go first (highest 20-day average dollar volume).
11. **Costs:** 0.1% slippage on every buy and sell. No commissions.
12. **Account:** $100,000 to start, cash only. Unused cash earns nothing. Positions are marked at each day's close.

## The short side (information only)
The exact mirror of the long rules:
- **Downtrend:** 50-day average below the 200-day average and falling.
- **Setup:** the lowest low in 20 days, then no close below the prior day's low.
- **Signal:** a close below yesterday's low.
- **Orders:** sell stop at the low − 0.1%. Stop at the highest high of the rally + 0.1%. Target at the lowest close in 20 days + 0.1%.

It is sized the same way, and its capital counts against the 25% cap and the 10 slots. It is run as a separate $100,000 account.

## The long side counts as working only if all three hold
1. The **profit factor** (total gains ÷ total losses) is at least **1.3**.
2. **Profitable in both halves:** 2016–2020 and 2021–Sept 2026.
3. The worst **peak-to-trough drop** in account value is at most **25%**.

Otherwise the conclusion is that it did not show an edge. **Nothing will be tuned afterwards:** no other windows, buffers, trend filters, reward rules or exits. Results will be shown next to simply holding SPY, for context only.

## Also reported
- Trades per year, win rate, average win and loss, and average hold time.
- **Expectancy from the video's formula:** (1 + W ÷ L) × P − 1.
- Yearly P&L, best and worst trade, and how exits split between stop, target and time.

## Known limits, stated in advance
- **Discretion left out:** the video's judgement calls ("pullback into old support", "deceleration", Fibonacci, round numbers) can't be applied objectively, so the test uses only the exact trigger, stop and target rules.
- **Daily bars only.** Which of the stop or target came first on a day is unknown; the rules assume the stop, which is cautious.
- **Survivorship bias** favors the long side.
