# The "fence bar" opening setup (Trade Your Edge video): pre-declared test #18 plan (October 5, 2026)

- **Written and committed before any result.** Research only; no orders. Nothing changes in Plan B, the bots, MNQ or the EP watch.
- **Owner's request:** "yes run the fence bar test please 100%" (Oct 5).
- **Source:** Steven (Trade Your Edge), "How to Trade the First 5 Minutes (And Be Done by 10 AM)", as summarized in [YOUTUBE_THREE_VIDEOS_NOTES_20261005.md](YOUTUBE_THREE_VIDEOS_NOTES_20261005.md).
- **Where he gives a range** (stop "about halfway or near support", "reluctant" when the average points the other way, "done by 10:30 ideally"), this plan picks one main value now and reports one alternative as information.

## Data and conventions (the same as tests #8 and #9)
- **Bars:** QQQ and SPY 5-minute bars, regular session, already on disk (`outputs/crt_sweep_data/`). Alpaca SIP, dividend-adjusted, Jan 4, 2016 – Oct 2, 2026; every day starts with a 9:30 bar.
- **Account:** $100,000 per symbol per side, cash only.
- **Size:** 1% of the account at risk per trade: shares = 1% of equity ÷ (entry − stop), at most 100% of equity, whole shares. No margin.
- **Costs:** 0.01% slippage on every buy and sell; no commissions. Results before costs are also reported.
- **Sides:** **long trades decide the verdict** (the owner's stock accounts can't short). Shorts are run as separate accounts and reported as information (relevant for futures).

## The rule (long side; the short side is the exact mirror)
1. **Fence:** the high and low of the first 5-minute bar (9:30–9:35).
2. **Breakout:** a later 5-minute bar **closes above** the fence high. Any later close back at or below the fence high cancels it; a new breakout is then needed.
3. **Retest (entry):** after a breakout, a bar that **opens above** the fence high, **trades back down to or below** it, and **closes above** it.
   - Buy at that bar's close.
   - **Only if the bar starts by 10:55** (closes by 11:00, "a trade for the open").
4. **Anchor-line filter:** the 20-bar simple average of 5-minute closes (continuing across days, regular hours) must be **flat or rising** at the entry bar: average now ≥ average one bar earlier. He says he's "reluctant" otherwise.
5. **Stop:** halfway into the fence (its midpoint).
6. **Target:** 2× the risk above the entry.
7. **Exit:** at the stop or target, whichever later 5-minute bar reaches first. If one bar reaches both, **assume the stop** (the flip is reported). If neither is reached, exit at the day's last close.
8. **One trade per side per day:** the first valid retest.

## Windows (the owner's post-COVID default)
- **Main (decides the verdict):** Jan 2, 2020 – Oct 2, 2026. Bar A2's halves are **2020–2022** and **2023–2026**.
- **Stress check:** Jan 4, 2016 – Oct 2, 2026, with halves 2016–2020 and 2021–2026.

## It counts as working only if, for BOTH QQQ and SPY long, all hold (main window)
**Bar A:**
1. Profit factor ≥ **1.3**.
2. Profitable in **both halves**.
3. Worst drop no worse than **−25%**.

**Bar B (vs holding SPY over the same dates):**
4. Worst drop at least **5 points smaller** than SPY's.
5. Growth ÷ |worst drop| **higher** than SPY's.

**Labels:**
- **PASS (robust):** it also passes all 5 checks for both symbols in the stress window.
- **PASS (post-COVID only):** it passes the main window only.
- **FAIL:** any check fails.

**Nothing will be tuned afterwards:** no other fence lengths, stops, targets, filters, windows or symbols.

## The video's claim, checked separately
His proof was 4 winners from 4 triggers over 5 days. Reported here: the share of trades reaching the 2R target, and how often the setup triggers (days with a trade).

## Also reported (information only, decided now)
- **Variants:**
  - **no anchor-line filter;**
  - **stop at the retest bar's low** (his "just past the entry candle");
  - **entries allowed until 3 PM** (bar start by 14:55);
  - **before costs;**
  - the **short side** (both symbols).
- **Detail:**
  - trades per year;
  - average win and loss;
  - average R;
  - the exit split (stop / target / close);
  - P&L by year.
- **Same-bar ambiguity:** the rate and the flip rate.
- Provenance manifest.

## Checks
- **Unit tests on hand-built bars:**
  - a valid long;
  - a breakout bar that isn't a retest;
  - a close back inside that cancels;
  - a retest after 10:55 (skipped);
  - a falling anchor line (skipped);
  - a same-bar stop/target touch;
  - an exit at the close;
  - a mirrored short.
- **An independent recount** of 15 random QQQ days (trade or no trade, entry, exit), with separately written code.
