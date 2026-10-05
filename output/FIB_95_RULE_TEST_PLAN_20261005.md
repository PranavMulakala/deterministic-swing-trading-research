# Does Kevin's "95% Fibonacci rule" hold? Pre-declared test #11 (October 5, 2026)

Written and committed **before** any result was computed. Research only. Nothing changes in the bots, Plan B or MNQ. The owner asked: "yes test the 95% fib rule".

**Source:** a Kevin Trades Discord post pasted by the owner on Oct 5 (Whop trial, cancelled the same day). It makes two claims:
1. **The "95% rule":** "A close of 2–3 candles beyond the 88.7% level is the true structural invalidation signal, carrying a ~95% probability that the move has transitioned into an outright trend reversal."
2. **The "Faker level":** a close beyond 76.4% "alone is never a reason to flip bias". Price "routinely breaks this level … before snapping back."

**No timeframe, market or swing definition was given,** so the reading below is fixed in advance and covers two timeframes. **Prior evidence:** studies find Fibonacci levels no better than arbitrary levels, and our two "liquidity trap" tests (CRT #8, #9) failed.

## The key fairness point
Once price is 88.7% of the way back, it is already close to the start of the move. Even random prices would usually reach the start before a brand-new extreme, roughly 89% of the time for a random walk. **So a high hit rate alone proves nothing about 88.7% being special.** The test therefore also runs the same rule at made-up "placebo" levels (80%, 85%, 90%, 95%) and checks whether 88.7% does better than its neighbours.

## Data (already on disk, no download)
- QQQ and SPY Alpaca SIP 5-minute bars, regular session, Jan 2016 – Oct 2, 2026 (`outputs/crt_sweep_data/`).
- They are built into two timeframes:
  - **1-hour candles:** 9:30-aligned, full hours only, six a day, treated as one continuous series across days.
  - **Daily candles:** the regular session's open, high, low and close.

## Swings and Fibonacci levels
- **Pivot high:** a candle whose high is above the highs of the **5 candles before and the 5 after**. A pivot low is the mirror.
- **Up move ("impulse"):** from a pivot low L to the next pivot high H. It must be at least **1.0%** of L on 1-hour candles, or **5.0%** on daily candles; smaller swings are skipped. The down move is the mirror: pivot high H to the next pivot low L.
- **Retracement level x%** of an up move = H − x × (H − L). "Beyond" a level means below it for an up move, above it for a down move.
- **No peeking:**
  - A pivot is only known after its 5 right-hand candles have closed.
  - Watching starts with the candle after that confirmation.
  - The setup ends if price makes a new extreme beyond H (for an up move) before a signal; the move just extended.

## Claim 1: the 95% rule
- **Signal:** the first time **2 consecutive candle closes** are beyond 88.7% (both after confirmation).
- **"Reversal":** after the signal, price trades **beyond the start of the move** (below L for an up move) **before** it trades back past the end (above H).
- **Counting:**
  - If both happen in the same candle, it's "ambiguous": reported, not counted.
  - If neither happens within 120 candles, it's "unresolved": reported, not counted.
- **Reversal rate** = reversals ÷ (reversals + continuations).
- **Placebo levels:** exactly the same rule at **80%, 85%, 90% and 95%**.
- **Information only:** the same results with 3 consecutive closes.

## Claim 2: the Faker level
- **Event:** the first candle close beyond **76.4%** after confirmation, provided no 88.7% signal has fired yet.
- **"Snap back":** price closes back inside the **61.8%** level before 2 consecutive closes beyond 88.7%. If neither happens within 120 candles, it's unresolved and not counted.
- **Placebo levels:** the same event at **70% and 80%**.

## Verdicts, fixed now
There are 4 combinations: QQQ/SPY × 1-hour/daily. Combinations with fewer than 30 resolved signals are reported but don't count.

**A. "The 95% figure holds":** the reversal rate at 88.7% is **at least 90%** in every counted combination.

**B. "88.7% is a special level":** in each counted combination, the 88.7% reversal rate is compared with a straight line drawn between the 85% and 90% placebo rates, at the 88.7% point. Averaged over the counted combinations, it must beat that line by **at least 2 percentage points**.

**C. "76.4% is a special Faker level":** the 76.4% snap-back rate must beat the straight line between the 70% and 80% placebo rates by **at least 2 points** on average.

Kevin's framework counts as **supported only if A, B and C all hold.** If only A holds, the conclusion is: "the number is roughly right, but any deep level does the same; nothing special about Fibonacci." **Nothing will be tuned afterwards:** no other pivot sizes, move sizes, timeframes or levels.

## Also reported
- Signal counts, and how many were ambiguous or unresolved.
- Median candles until resolution.
- **Information only:** a simple counter-trend trade on the 88.7% signal. Enter at the signal close, target the move's start, stop at the move's end, judged against holding SPY. This is not part of the verdict; it shows whether a "95%" signal pays.

## Checks
- Unit tests on hand-built candles: pivot finding, the 2-close signal, reversal vs continuation, the Faker snap-back and the no-peeking rule.
- A second, independent counter recomputes the 88.7% results for one combination from the raw candles.
- Provenance manifest.
