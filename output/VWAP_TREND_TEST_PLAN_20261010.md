# Test #30 plan: the Reddit "VWAP monster" as a strict rule on QQQ (written October 10, 2026, before any result)

- **Owner's request (Oct 10):** "A strict written-down version of the VWAP rule on QQQ data we already have. It could become the rule for your MNQ paper trading."
- **Source:** r/Daytrading post "I've just created a monster" (about 4 months old).
  - The poster trades 1-minute MGC/NQ futures "with the trend of VWAPs": the session VWAP, the previous-day VWAP ("pdVWAP") and the overnight VWAP. 1-minute momentum must line up with the 20/50/100/200 EMAs. Stop and target come from ATR.
  - He gave no exact numbers, says he doesn't take every entry, and posted no backtest.
- **So this tests OUR strict reading of his description, not his discretionary trading.** Every number below is picked now, before any result, and nothing is tuned afterwards.
- **Paper research only;** no orders. Nothing changes in Plan B, the bots, the MNQ setup or the EP watch. Dollars first, no SPY line (owner's standing instruction).
- **Looked at before writing this plan:** only the data file's layout (5-minute bars including extended hours, 4:00–20:00 ET). No signals, trades or returns.

## Data and conventions (the same file as tests #8, #9 and #18)
- **Bars:** QQQ 5-minute bars, Alpaca SIP, `outputs/crt_sweep_data/QQQ_5min_sip_2016-01-01_2026-10-02.json.gz`, including extended hours. Each bar has open/high/low/close, volume and its own VWAP (`vw`).
- **Why 5-minute, not 1-minute:** that's the QQQ data on disk. All indicator lengths below are counted in 5-minute bars (disclosed as a difference from the post).
- **Account:** $100,000, cash only, compounding.
- **Size:** 1% of equity at risk per trade: shares = 1% of equity ÷ (entry − stop), whole shares, at most 100% of equity. No margin.
- **Costs:** 0.01% slippage on every buy and sell, no commissions (the same as test #18). Results before costs are also reported.
- **Sides:** **long trades decide the verdict** (cash accounts can't short). The mirror-image short side is run as a separate account and reported as information, because MNQ futures can go short.

## Indicators (all from bar data available at the signal bar's close)
- **Session VWAP:** cumulative Σ(`vw` × volume) ÷ Σ volume over today's regular-session bars from 9:30.
- **Previous-day VWAP (pdVWAP):** the same cumulative VWAP but anchored at **9:30 of the previous trading day**, running through all regular-session bars since then (a two-day anchored VWAP, the commenter's reading of "previous day VWAP").
- **Overnight VWAP:** Σ(`vw` × volume) ÷ Σ volume over the extended-hours bars from 16:00 of the previous trading day to the 9:25 bar today. A fixed level for the day; if those bars have no volume, there are no trades that day.
- **EMAs 20, 50, 100 and 200:** of regular-session 5-minute closes, continuing across days.
- **ATR(14):** Wilder's average true range of regular-session 5-minute bars, continuing across days.
- **Warm-up:** no trades until 200 regular-session bars have passed.

## The rule (long side; the short side is the exact mirror)
1. **Trend conditions, at a bar's close:**
   - close > session VWAP, close > pdVWAP and close > overnight VWAP;
   - close > EMA20 > EMA50 > EMA100 > EMA200.
2. **Trigger:** all conditions are true at this bar's close and were **not all true at the previous bar's close** (a fresh alignment).
3. **Time window:** only signal bars that start between **9:45 and 15:00** ET.
4. **Entry:** the next bar's open (plus slippage).
5. **Stop:** entry − **1.5 × ATR(14)** (ATR at the signal bar).
6. **Target:** entry + **3 × ATR(14)** (2× the risk).
7. **Exit:** at the stop or target, whichever a later bar reaches first. If a bar opens beyond either level, fill at that open. If one bar reaches both, **assume the stop** (the flip is reported). If neither is reached, exit at the **15:55 bar's close** (flat every night).
8. **One position at a time.** After an exit, a new trigger may enter from the next bar.

## Windows (the owner's post-COVID default)
- **Main (decides the verdict):** Jan 2, 2020 – Oct 2, 2026. Halves **2020–2022** and **2023–2026**.
- **Stress check:** Jan 4, 2016 – Oct 2, 2026, with halves 2016–2020 and 2021–2026.

## Pass bar (main window, long side)
- **C1:** profit factor ≥ **1.3** after costs.
- **C2:** profitable in **both halves**.
- **C3:** worst drop no worse than **−25%**.
- **C4 (the commenters' "test it in a bad market"):** profitable in **2022**, QQQ's down-and-choppy year.
- **Labels:**
  - **PASS (robust):** C1–C4 also hold in the stress window (C4 there uses 2018 as well as 2022).
  - **PASS (post-COVID only):** the main window only.
  - **FAIL:** any main-window check fails.
- **Nothing will be tuned afterwards:** no other EMA lengths, ATR multiples, time windows or filters.

## Baselines (information, decided now)
- **Break-even check (lesson from test #18):** a 2R target needs a hit rate above 1/(1+2) ≈ 33% before costs. The target-hit rate is reported next to it.
- **Random-entry placebo (lesson from test #11):** the same number of trades per year, entered at random bar opens in the same 9:50–15:05 window with the same stop/target/exit rules (random seed 30, 20 repeats). This shows whether the VWAP/EMA conditions add anything over random timing.

## Also reported (information only, decided now)
- **Variants:**
  - **VWAP bounce:** instead of a fresh alignment, the trigger is a bar whose low touches the session VWAP and whose close is back above it while all the conditions hold (his "it can be a bounce on these levels");
  - **stop at 1 × ATR, target 2 × ATR;**
  - **before costs;**
  - **the short side.**
- **Detail:** trades per year, % winners, average win and loss, average R, the exit split (stop / target / close), P&L by year, $ per week, $1,000 weeks, worst week and month.
- **MNQ translation:** each trade's P&L in QQQ points, and roughly what one MNQ contract would have made (1 MNQ ≈ $2 × the Nasdaq-100 index ≈ $2 × 41 × QQQ's price move; an approximation, labelled as such).
- **Same-bar ambiguity:** the rate and the flip rate.
- **Pilot check before results (no returns):** the stop distance as a multiple of the typical 5-minute bar range (lesson from test #21: a stop smaller than one bar's range makes 5-minute data unable to decide).
- Provenance manifest.

## Checks
- **Unit tests on hand-built bars:**
  - session VWAP, pdVWAP and overnight VWAP arithmetic;
  - a fresh alignment that triggers, and one that was already aligned (no trigger);
  - a signal outside 9:45–15:00 (skipped);
  - stop, target, same-bar touch (stop assumed), gap through a level, exit at 15:55;
  - one position at a time;
  - a mirrored short.
- **An independent recount** of 15 random QQQ days (trade or no trade, entry, exit), with separately written code.
