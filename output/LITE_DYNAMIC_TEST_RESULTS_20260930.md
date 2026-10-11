# "More dynamic" LITE dip rules: results of the pre-declared test (September 30, 2026)

- **Plan:** [LITE_DYNAMIC_TEST_PLAN_20260930.md](LITE_DYNAMIC_TEST_PLAN_20260930.md), committed before anything was computed (a8f2e3a).
- **Code:** `research/lite_dynamic_test_v1/` (9 offline tests).
- **Results file:** `output/lite-dynamic-test-results.json`.
- **Data:** LITE 5-minute bars already on disk, Jan 2022 to Sept 28, 2026. No download. History replay only; the running paper bot was not touched.

## Did the test itself work? Yes
1. **The baseline reproduces the earlier published numbers exactly:** 2026 realized +$79,946 with 59 sales, and 2025 realized +$38,403 with 28 sales.
2. **The new engine's "version 0" matches the original replay** in all four time windows.
3. **Unit tests on made-up bars (9 of 9 pass):**
   - the turn trigger fires on the right bar;
   - the trailing exit arms and sells at the right level, including a gap-down open;
   - the size tiers pick the right dollar amount.

## Verdict: one of the four new versions passed, narrowly

| Version | More profit in 2025? | More profit in 2026? | Worst drop within 10% of baseline? | Stress test OK? | Beats baseline? |
|---|---|---|---|---|---|
| 1. Watch the first hour | ✗ | ✗ | ✓ | ✓ | **No** |
| 2. Let winners run | ✗ | ✓ | ✓ | ✓ | **No** |
| **3. Bigger dip, bigger buy** | ✓ (barely) | ✓ | ✓ | ✓ | **Yes** |
| 4. All three together | ✗ | ✗ | ✓ | ✓ | **No** |

## The numbers
Profit means realized profit plus the value of any position still open at the end.

| Version | 2025 profit | 2026 profit (to Sept 28) | Buys, 2025–26 | Weeks with ≥ $1,000, of 92 | Worst drop, 2025–26 | 2022–2024 stress result |
|---|---|---|---|---|---|---|
| 0. Today's 10:00 rule | $34,536 | $79,946 | 85 | 48 | −$29,719 | −$10,757 |
| 1. Watch the first hour | $31,345 | $51,926 | 61 | 37 | −$29,877 | −$10,840 |
| 2. Let winners run | $31,524 | $87,039 | 85 | 39 | −$29,719 | −$10,915 |
| **3. Bigger dip, bigger buy** | **$35,301** | **$92,819** | 85 | 44 | −$29,719 | **−$7,179** |
| 4. All three together | $31,864 | $59,532 | 61 | 34 | −$29,877 | −$7,576 |

**For scale, simply holding $60,000 (not a recommendation):**

| Window | Hold LITE | Hold SPY |
|---|---|---|
| 2025 through Sept 28, 2026 | +$586,627 | +$19,473 |
| 2022–2024 stress | −$12,363 | +$17,143 |

## What each idea actually did
- **1. Watch the first hour: worse in both years.**
  - Waiting for the dip to "turn" meant it traded less: 61 buys against 85.
  - It missed many dips that recovered without a clean turn bar. 2026 profit fell from about $80k to about $52k.
  - The fixed 10:00 clock turned out to be the better of the two.
- **2. Let winners run: mixed, so it fails.**
  - Better in 2026 (+$7,093) and worse in 2025 (−$3,012).
  - It sometimes sold well above +2%. It also gave back part of the gain on the many days when LITE touched +2% and slipped back.
  - Fewer weeks reached $1,000: 39 against 48.
- **3. Bigger dip, bigger buy: passes, but thinly.**
  - **2025:** +$765 over the baseline. That's about 2%, essentially a tie.
  - **2026:** +$12,873, about 16% more.
  - **Per dollar tied up,** it was also somewhat better: $8.35 against $7.42 per $1,000 per day over 2025–26.
  - **Stress test:** less bad than the baseline (−$7,179 against −$10,757). This is because the one disastrous January 2022 buy came on a shallow dip and got the $40,000 size.
  - **Fewer $1,000 weeks:** 44 against 48, because shallow-dip buys are smaller.
- **4. All three together: fails.** It inherits version 1's missed trades.

## Cautions about the one pass
1. **Four versions were tried; one passed.** With four tries, one can pass by luck. The 2025 margin of $765 is too small to mean anything on its own.
2. **Most of the gain comes from one year** (2026), in a stock that went up about 10×.
3. **Its worst case is bigger than it looks here.**
   - In this history, the worst single holding (−$32,080) happened to be a $60,000 buy.
   - A 3%-or-deeper dip gets an **$80,000** buy. A 53% fall on that, which is what January 2025's holding did, would be about **−$42,000** on paper.
4. **Still no stop-loss** in any version. The downside remains open-ended.
5. **Every version badly trailed just holding LITE** in the boom, and none protected in the 2022–2024 fall. Dip-buying with a +2% cap gives up most of a big rise and still takes the full fall.

## What happens next, per the plan
- **Version 3 is a candidate for a second paper bot** running next to the current one. It doesn't replace the current bot, and it isn't for real money. Whether to build it is the owner's call.
- **The formula agreement is now in force** (the owner agreed on Sept 30): this was the last LITE formula test until the 8-week paper test ends. New ideas go on the parked list.
- **Nothing will be tuned:** no other tiers, percentages, trail widths or time windows.

## Parked ideas (reviewed once, when the paper test ends)
- **Wait for the close on signal days that keep falling** (owner, Oct 4). Descriptive look, 2025–26: on 67 signal days where LITE fell 1%+ further from 10:00 into the close, buying at the close instead of 10:00 reached +2% within 5 days 94% of the time (vs 85%), with a median 5-day result of +6.0% (vs +0.8%). In 2022–24 (57 days) it was 82% vs 56%, and +0.2% vs −1.3%. **Caveat:** this only looks at days that kept falling. A fair test must include every signal day (the late buyer skips or pays more on days that rally after 10:00). It's also "buying lower later", which the sell note forbids once a position is open (no averaging down).
- **Buy every day at 10:00, hold to +2%** (owner, Oct 2). Descriptive look: 113 sales and a −55% worst dip in 2025–26; 1 sale and −67% in 2022–24.
- **Skip signals near LITE earnings** (raised Oct 4; next report Nov 10).
- **Market filter: QQQ's move before 10:00** (from Sept 28).
- **The bot's learning-only fields** (`rebound_learning_only`, `volume_ratio_learning_only`): check them on the 8 weeks of forward data.
- **Sell at +3% or +4%, or split the sale 60% at +2% and 40% at +3–4%** (owner, Oct 6, after selling at +2% and watching LITE run to $1,121).
  - **How it was checked:** a descriptive look (`research/lite_dip_history_v1/target_compare.py`) on the same signals and buys as the replay: $60,000 per buy, one position at a time, no stop. The +2% baseline matches the replay exactly.

  | Realized profit | 2025 | 2026 (to Sep 28) | 2022–24 stress | $1,000 weeks, 2025–26 |
  |---|---|---|---|---|
  | All at +2% (today) | $50.4k | $76.4k | $65.3k | **53 of 92** |
  | All at +3% | $56.4k | **$87.9k** | $41.9k | 44 |
  | All at +4% | **$62.5k** | $60.5k | $45.7k | 34 |
  | 60% at +2%, 40% at +3% | $45.6k | $72.9k | $29.2k | 41 |
  | 60% at +2%, 40% at +4% | $45.8k | $46.0k | $29.2k | 28 |

  - **Higher targets won in parts of the boom but lost badly in 2022–24:** +3% made $23k less than +2% there, with average holds of 39 days against 9.
  - **Every alternative gave fewer $1,000 weeks.**
  - **Splits were never the most profitable.** The unsold 40% keeps the position open, which blocks the next buy, though splits roughly halved the worst drop.
- **Time of day** (owner, Oct 6; descriptive, `LITE_INTRADAY_TIMING_20261006.md`; 743 days, Oct 2023 – Sep 2026).
  - Moves and the day's high and low cluster in the first and last 30 minutes.
  - No time slot is reliably up or down: none survives correction, and the strongest flip sign between halves.
  - On 291 Plan B signal days, the low came after 10:00 on 76% of them, at unpredictable times.
- **Wheel only on stocks likely to go sideways** (owner, Oct 11, after test #33). Not a LITE idea, but parked here so it's reviewed with the others.
  - **What #33 showed:** the wheel beat holding on stocks that went sideways or slowly down: RKLB +$12.8k vs −$4.8k holding; PRAX +$3.7k vs −$4.7k. It lost $8–13k on stocks that fell hard (RIVN, CVNA, HL) and trailed on the big risers (LITE, STX).
  - **What a fair test needs:** a rule, using only data known in advance, that predicts "sideways" (e.g. weak trend plus high option prices). Then a pre-declared test on a fresh window. Every "predict the next move" rule so far has failed, so expect the same bar.
