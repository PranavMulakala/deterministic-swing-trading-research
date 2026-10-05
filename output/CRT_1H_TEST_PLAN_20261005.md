# Does the 1-hour CRT (candle range theory) strategy work on history? Pre-declared test #9 (October 5, 2026)

Written and committed **before** any 1-hour result was computed. Research only: no orders of any kind. Nothing changes in the running bots, Plan B or the MNQ paper test. The owner asked: "yes run the 1 hour CRT test".

**Source:**
- **TikTok batch 2 video 3 (@nitrotrades):** "I took this MYM one hour CRT. Price sweeps that low so we know it wants to make a move to this high. I put on the break of that middle candle…"
- The video only shows results, so the missing pieces follow the **standard CRT definition** also used in batch 2 video 9 (@parthtrades): stop beyond the sweep, target the far side of the range.

**Honest note:** test #8 (the 15-minute version) already failed on this same data. This is a separate question: bigger candles mean bigger targets, and test #8's main problem was targets too small for its stops and costs. Two tests on related ideas also raise the chance of a lucky pass, so the pass bars stay strict and unchanged.

## Data (already on disk from test #8; no new download)
- **Source:** Alpaca SIP 5-minute bars, QQQ and SPY, Jan 2016 – Oct 2, 2026, regular session only (`outputs/crt_sweep_data/`).
- **1-hour candles** are built from them, aligned to the 9:30 open as stock charts do: 9:30, 10:30, 11:30, 12:30, 13:30 and 14:30. Each is a full hour.
- The 15:30–16:00 half-hour is never used as candle 1 or candle 2.

## The rules: long side (the video's example)
1. **Setup.** Two consecutive full 1-hour candles in the same day, C1 then C2:
   - **C2 sweeps C1's low:** C2's low is below C1's low.
   - **C2 closes back inside C1's range.**
   - **C2 doesn't also break C1's high.** A two-sided candle is skipped.
2. **Entry ("break of the middle candle").** Watch the 5-minute bars in the **60 minutes after C2 closes** (the third candle's hour).
   - The first bar that **closes above C2's high** is the signal. Buy at that bar's close.
   - No signal bar may start after 15:25. If nothing triggers within the 60 minutes, the setup expires.
3. **Stop:** C2's low, the sweep low (the standard CRT stop).
4. **Target:** C1's high (the "range high").
   - Skip the setup if the target is not above the entry.
5. **Exits, on each later 5-minute bar:**
   - If the low reaches the stop, exit at the stop.
   - Otherwise, if the high reaches the target, exit at the target.
   - **If both are touched in the same bar, count it as a stop.**
   - **Otherwise, exit at the 15:55 bar's close.** Always flat overnight.
6. **One trade at a time per symbol.** After an exit, only setups whose C2 closes at or after the exit time count.

## The short side (information only; the owner's stock accounts can't short)
The mirror image:
- C2 sweeps C1's high and closes back inside.
- Signal: a 5-minute close below C2's low.
- Stop: C2's high. Target: C1's low.

## Size, costs, account (same as test #8)
- **$100,000 per symbol per side**, cash only.
- **Risk 1% of equity per trade:** shares = 1% of equity ÷ (entry − stop), with the position capped at 100% of equity.
- **Costs:** 0.01% slippage per buy and per sell. Results before costs are also shown.

## It counts as working only if, for BOTH QQQ and SPY long, all of these hold
**Bar A:**
1. Profit factor of at least 1.3.
2. Profitable in both 2016–2020 and 2021–2026.
3. Worst peak-to-trough drop of at most 25%.

**Bar B (vs holding SPY over the same dates):**
4. Max drawdown at least 5 points smaller than SPY's.
5. CAGR ÷ |max drawdown| higher than SPY's.

**Nothing will be tuned afterwards:** no other candle sizes, alignments, windows, stops or targets.

## Also reported
- Target-hit rate and win rate.
- Typical distances to the target and the stop, and reward-to-risk.
- Trades per year, P&L by year and exit split.
- Same-bar ambiguity, plus the result if those bars count as targets instead.
- Results before costs.
- Provenance manifest.

## Checks before running
- Offline unit tests on hand-built bars.
- An independent re-computation (explicit short side, no mirroring) that must reproduce every trade.

## Known limits
- **ETF regular session only.** The video trades MYM futures nearly around the clock, with clock-hour candles; overnight candles aren't available here.
- **"Lower timeframe entry" is read as a 5-minute close.** The video's exact entry timeframe isn't stated.
