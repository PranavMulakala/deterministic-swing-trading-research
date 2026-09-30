# Would a "more dynamic" LITE dip rule beat the 10:00 rule? Pre-declared test plan (September 30, 2026)

Written and committed **before** any of these versions was computed. History replay only: no orders, no change to the running paper bot.

**Why:** the owner asked (Sept 30): "Why does it have to be a specific time?... can we not analyze the market for the first hour... maybe even sell higher than the target?" and then "Yes, write the test plan. With all three ideas."

## The agreement that comes with this test (proposed; needs the owner's yes)
The owner also said: "I keep changing ideas or adding everything... we have to agree on [a point to] stop making different formulas."

**Proposed rule:** this is the **last LITE formula test** until the running 8-week paper test finishes.
- After this test, new LITE ideas go on a written "parked ideas" list instead of becoming new tests.
- The list gets reviewed once, when the paper test ends.
- **Why it matters:** every extra formula we try on the same history raises the odds that one looks good by luck. Five versions are tested here, which is already enough for that to happen. That's why the pass rule below is strict.

## Data
- **Already on disk, no download:** LITE 5-minute bars from Alpaca, Jan 2022 to Sept 28, 2026, in `outputs/lite_history/`. The complete market feed (SIP) is used for signals, fills and daily values.
- **Windows, the same ones as the [earlier replay](LITE_DIP_BOT_HISTORY_20260928.md):**
  - **Main:** 2025 and 2026 (Jan 2 to Sept 28), each judged on its own. The owner prefers these years because LITE changed after its boom.
  - **Stress test:** 2022–2024, LITE's last big fall.
- **What's already been seen:** the current 10:00 rule was chosen after looking at 2026. The three new ideas below were written down from reasoning alone, without looking at how they'd have done.

## What stays the same in every version
- **One position at a time.** No averaging down, no re-buy on the same day.
- **No stop-loss** while a position is below its target. This is the owner's standing choice.
- **$60,000 per buy,** except in the version that changes size.
- **Buy price:** the next 5-minute bar's opening price plus 0.1%.
- **Each window starts with no position.** A position still open at the end is valued at the last close.
- **No taxes or commissions** are counted (Alpaca charges no commission).

## The five versions

### 0. Baseline: the rule the paper bot runs today
- **Signal:** in the first 30 minutes, LITE's low is at least 1% below the 9:30 open, and the 9:55 bar closes below the open.
- **Buy:** at 10:00.
- **Sell:** a resting order at +2% over the buy price. A touch of that price counts as a sale. A gap above it at the open sells at the open.

### 1. "Watch the first hour" (changes when it buys)
- **Watch** each completed 5-minute bar from the one starting at 9:35 to the one starting at 10:25.
- **Buy trigger:** the first bar where all three are true:
  - the day's low so far is at least 1% below the 9:30 open;
  - this bar **closes above the previous bar's high** (the dip has turned);
  - this bar closes below the 9:30 open (it's still a dip).
- **Buy:** at the next bar's open plus 0.1%. No trigger by the 10:25 bar means no buy that day.
- **Sell:** the same +2% as the baseline.

### 2. "Let winners run" (changes when it sells)
- **Buy:** exactly as the baseline, at 10:00.
- **Sell:**
  - When the price first reaches **+2%**, don't sell. "Arm" a trailing exit instead.
  - From the next bar on, track the highest price reached since arming.
  - Sell when a bar's low falls to **1% below that highest price**, at that level minus 0.1% for slippage.
  - If a bar opens below that level (a gap down), sell at that open minus 0.1%.
  - A bar can only trigger the level set by earlier bars. The order of the high and low inside one 5-minute bar is unknown.
- **What this means:** once armed, the sale is normally at about +1% or better; a gap down past the trail can make it lower. Before arming, it holds with no stop, like the baseline.

### 3. "Bigger dip, bigger buy" (changes how much it buys)
- **Buy and sell:** exactly as the baseline.
- **Size by how deep the morning low was, measured from the open:**

  | Dip | Buy |
  |---|---|
  | 1% to under 2% | $40,000 |
  | 2% to under 3% | $60,000 |
  | 3% or more | $80,000 |

### 4. All three together
- Version 1's entry, version 2's exit and version 3's sizing.

## How a version is judged (fixed now)
**A version "beats the baseline" only if all four hold:**
1. **More profit in 2025** than the baseline. Profit means realized profit plus the value of any open position at the end.
2. **More profit in 2026** (Jan 2 to Sept 28) than the baseline.
3. **Not much riskier:** its worst drop from a peak over 2025–2026 is no more than 10% deeper than the baseline's, in dollars.
4. **Holds up in the stress test:** its 2022–2024 end result is no more than $5,000 worse than the baseline's.

**Why both years separately:** with five versions on the same history, one can easily win a single period by luck. Winning two separate years is harder to do by accident. It still isn't proof.

**What a pass means:**
- The version becomes a candidate for a second paper bot, running next to the current one.
- It doesn't mean real money, and it doesn't replace the running bot mid-test.

**If nothing passes:** the 10:00 rule stays as it is, and we stop adjusting formulas, per the agreement above.

## Also reported for every version, for information
- **Activity:** buys and sales.
- **Income pattern:** weeks with at least $1,000 realized, the average per week, and the longest stretch with no sale.
- **Downside:** the worst paper loss on one holding, and the worst drop from peak.
- **Capital use:** profit per $1,000 of money tied up per day, so the bigger-buy version is compared fairly.
- **Stricter sale check:** results when a sale at the +2% price requires the market to trade 0.1% beyond it.
- **Benchmarks:** what simply holding $60,000 of LITE, and $60,000 of SPY, did over the same windows.

## Checks that the test itself works (all must pass, or results don't count)
1. **Baseline reproduction:** version 0 must reproduce the published baseline numbers from the earlier replay: 2026 realized +$79,946 with 59 sales, and 2025 realized +$38,403 with 28 sales.
2. **Unit tests on made-up 5-minute bars** for each new rule:
   - the turn trigger fires on the right bar, and doesn't fire when the turn bar closes above the open;
   - the trailing exit arms at +2% and sells at the right level, including a gap-down open;
   - the size tiers pick $40k, $60k and $80k at the right dip depths.

## Known limits, stated in advance
- **5-minute bars, not real fills.** Real orders can fill worse, especially the trailing exit in a fast drop.
- **One stock, in a boom.** LITE rose about 10× over 2025–2026. Any "buy the dip" rule looks good on a stock that kept recovering. The stress window is there to show the other case.
- **No stop-loss** in any version, so the unbounded downside of the baseline remains (paper losses of $21,000–$40,000 on one holding in every period tested).
- **Nothing will be tuned afterwards.** No other percentages, time windows, trail widths or size tiers.
