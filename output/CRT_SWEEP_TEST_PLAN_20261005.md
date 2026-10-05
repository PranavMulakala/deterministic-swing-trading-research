# Does the TikTok "15-minute sweep and reclaim" (CRT) strategy work on history? Pre-declared test #8 (October 5, 2026)

Written and committed **before** any data for this test was downloaded or any result was computed. Research only: no orders of any kind. It changes nothing in the running bots, Plan B or the MNQ paper test.

**Source:** TikTok batch 2, video 2 (`output/TIKTOK_BATCH2_NOTES_20261005.md`), the 15-minute "sweep and reclaim" setup on MES futures. Its claim is that it "prints almost 85–90% of the time". The owner asked for anything useful from the videos to be implemented overnight, as long as it doesn't affect running tests.

**Why this one:** of the videos seen Oct 5 it's the only intraday setup with exact rules (setup, entry, stop and target all stated), and its claim is directly checkable. **No independent evidence supports it;** that is what the test is for. Batch 2 video 7 (swing breakouts) was withdrawn, because it is the same video test #3 already tested and failed.

## Data
- **Prices:** Alpaca SIP 5-minute bars for **QQQ and SPY**, Jan 4, 2016 to Oct 2, 2026, split- and dividend-adjusted. The download uses the LITE paper account's read-only data keys and is cached under `outputs/crt_sweep_data/`.
- **Session:** only regular-session bars, 9:30–16:00 New York time. Half-days use whatever bars exist.
- **Why ETFs, not MES:** the owner's cash accounts can trade QQQ and SPY. QQQ tracks the Nasdaq-100, the same index as MNQ, and SPY tracks the same index as MES. Intraday ETF and futures moves are near-identical in percentage terms.

## The rules: long side (the mirror of the video's short example)
1. **15-minute candles** are built from 5-minute bars on the clock (9:30, 9:45, … 15:45), each with an open, high, low and close.
2. **Setup.** For each pair of consecutive 15-minute candles, C1 then C2, in the same day:
   - **C2 sweeps C1's low:** C2's low is below C1's low.
   - **C2's body closes back inside:** C2's close is at or above C1's low and at or below C1's high.
   - **C2 doesn't also sweep C1's high.** A candle that breaks both sides is skipped as ambiguous.
   - **Trigger line:** C2's high.
3. **Entry.** Use the 5-minute bars that start after C2 ends, within the next 30 minutes (6 bars).
   - The first bar that **closes above the trigger line** is the signal bar. Entry is at the signal bar's close.
   - If no bar closes above the line in those 30 minutes, the setup expires.
   - **No signal bar may start after 15:25.**
4. **Stop:** the signal bar's low.
5. **Target:** C1's high.
   - Skip the setup if the target is not above the entry.
   - Skip it if the stop is not below the entry.
6. **Exits, on each later 5-minute bar:**
   - If the low reaches the stop, exit at the stop.
   - Otherwise, if the high reaches the target, exit at the target.
   - **If both are touched in the same bar, count it as a stop** (the cautious assumption). The `same_bar_ambiguity` rate is reported.
   - **Otherwise, exit at the close of the 15:55 bar.** Always flat overnight.
7. **One trade at a time per symbol.** After an exit, only setups whose C2 ends at or after the exit time count.

## The short side (information only)
The exact mirror of the long rules:
- C2 sweeps C1's high and closes back inside.
- Trigger line: C2's low.
- Signal: a 5-minute close below the line.
- Stop: the signal bar's high. Target: C1's low.

This is the video's own example. It's run as a separate account and **does not count toward the verdict**, because the owner's stock accounts can't short. It is useful context for futures, which can short.

## Size and costs
- **$100,000 per symbol per side**, cash only.
- **Risk 1% of the account per trade:** shares = (1% of current equity) ÷ (entry − stop), capped so the position is at most 100% of equity. No margin.
- **Costs:** 0.01% slippage on every buy and sell (about 5 cents per share on QQQ at $500, several times the usual 1-cent spread). No commissions. Results before costs are also reported.

## It counts as working only if, for BOTH QQQ and SPY long, all of these hold
**Bar A:**
1. Profit factor (gains ÷ losses) is at least **1.3**.
2. Profitable in **both halves:** 2016–2020 and 2021–2026.
3. The worst peak-to-trough drop is at most **25%**.

**Bar B (vs holding SPY over the same dates):**
4. The max drawdown is at least 5 points smaller than SPY buy-and-hold's.
5. CAGR ÷ |max drawdown| is higher than SPY buy-and-hold's.

Otherwise the conclusion is that it did not show an edge. **Nothing will be tuned afterwards:** no other candle sizes, expiry windows, stops, targets, symbols or time filters.

## The video's claim, checked separately
- **Win rate,** the share of trades that hit the target, for each symbol and side, against the claimed **85–90%**.
- **Setup frequency:** setups per day and triggers per day.

## Also reported
Trades per year, average win and loss, average R multiple, exit split (stop / target / close), P&L by year, the same-bar ambiguity rate and flip rate, and the result if same-bar touches are counted as targets instead (to show how much that assumption matters). Plus a provenance manifest (code and data hashes).

## Checks before running
- Offline unit tests on hand-built bars: a valid long, a valid short, a body closing outside (invalid), a two-sided sweep (skipped), a setup expiring, a same-bar stop/target touch, and the 15:55 exit.
- A second, independent re-computation of every trade's P&L from the raw bars and the trade list; it must match the backtest's totals.

## Known limits, stated in advance
- **5-minute bars.** The order of the stop and the target inside one bar is unknown; the cautious stop-first rule and the ambiguity rate cover this.
- **ETF, not futures.** No contract rolls, and MES is shown only by proxy.
- **The video's "any previous 15-minute candle" is read as consecutive candles.** A rule that picks the best candle in hindsight can't be tested fairly.
