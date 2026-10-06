# When does LITE move during the day? A descriptive study (October 6, 2026)

- **What this is:** a **descriptive look**, not a pre-declared test. **Plan B is unchanged** (the formula freeze runs until the paper test ends), and anything useful goes on the parked-ideas list.
- **Data:** every 5-minute bar from 9:30 to 16:00 ET on **743 full trading days, Oct 2, 2023 – Sep 28, 2026**. Alpaca SIP data, raw prices, with SPY on the same days for comparison.
- **Halves:** Oct 2023 – Mar 2025 (371 days) and Apr 2025 – Sep 2026 (372 days).
- **Code:** `research/lite_intraday_timing_v1/study.py`. Full numbers: `output/lite-intraday-timing-20261006.json`.

## 1. When LITE moves most: the first 30 minutes, by far
| 30-minute block | Average size of one 5-minute move | Share of the day's volume | SPY's average 5-minute move |
|---|---|---|---|
| **9:30–10:00** | **0.68%** (the 9:30 bar alone: 1.11%) | **13.8%** | 0.076% |
| 10:00–10:30 | 0.42% | 9.2% | 0.071% |
| 10:30–11:00 | 0.34% | 7.6% | 0.061% |
| 11:00–12:00 | 0.25% | 12.1% | 0.052% |
| 12:00–15:00 | **0.19–0.21%** (the quietest) | 30.1% | 0.045% |
| 15:00–15:30 | 0.19% | 6.8% | 0.044% |
| **15:30–16:00** | 0.23% | **20.4%** (the last bar alone: 8.8%) | 0.059% |

- **The shape:** a 5-minute bar right after the open moves **3–6× as much** as a midday bar. Volume is heaviest at the open and the close.
- **That's normal for stocks:** SPY has the same shape. LITE's moves are 4–9× bigger than SPY's: the biggest gap is at the open.

## 2. When LITE goes up or down: no time of day is reliably either
- **No single 5-minute slot** had an average move that held up as real once you account for checking 78 slots (Holm-corrected; none below p = 0.05).
- **The strongest-looking slots flip between the halves:**
  - 15:00–15:05 was down in the first half (t = −3.4) and **up** in the second (t = +3.2).
  - **9:55–10:00** leaned down in both halves (−0.03%, then −0.12% on average; 52% of days down). It's interesting, but not significant after the correction.
- **Above the open?** At every time of day, LITE is above its 9:30 open on **50–52% of days**, a coin flip.
- **The average day drifts up slowly:** +0.04% by 10:00, +0.14% by 1:30, +0.11% at the close. That's tiny next to the noise.

## 3. When the day's high and low happen
| | High happens in the first 30 min | Low in the first 30 min | High in the last 30 min | Low in the last 30 min |
|---|---|---|---|---|
| **All days** | **44.7%** | **42.3%** | 13.7% | 12.2% |
| **Up days** (close > open, 52%) | 13.0% | **69.9%** (80% by 10:30) | **25.6%** | 0.8% |
| **Down days** | **79.0%** | 12.3% | 0.8% | **24.6%** |
| SPY, all days | 24.0% | 29.5% | 20.7% | 13.6% |

- **In words:** the day's extreme usually comes **right after the open**. Up days usually make their low by 10:30 and grind higher into the close. Down days usually make their high at the open and slide into the close.
- **Midday rarely sets the high or low:** about 2–3% of days for each 30-minute block between 11:00 and 15:00.
- **The catch:** at 10:00 you don't yet know whether it's an up day or a down day. Unconditionally, the low is in the first 30 minutes only 42% of the time.
- Both halves look the same (low in the first 30 minutes: 39% and 45% of days).

## 4. Days the Plan B 10:00 rule would have fired (291 days)
| When the day's low came | Share |
|---|---|
| Before 10:00 (so the 10:00 buy was already above the low) | 24% |
| **10:00–12:00** | **36%** |
| 12:00–14:00 | 13% |
| After 14:00 | 27% |

- **Closed above the 10:00 price:** 52% of these days.
- **Reached +2% above the 10:00 price the same day:** 50%. That was 38% in the first half and **60% in the second**, the boom.
- **The median best gain after 10:00** was +2.0%.

So on dip days, **three out of four times LITE went lower after 10:00**, but when that low comes is spread across the whole day. There's no clock time where "the bottom is in".

## What this means
- **Timing tells you *how much* LITE will move, not *which way*.** The first 30 minutes and the last 30 minutes are when the big moves and the day's high and low happen. The middle of the day is quiet.
- **No time of day is a reliable "buy" or "sell" moment.** The patterns that look strongest either flip sign between periods or are too small to beat the noise.
- **For buying lower than 10:00:** on Plan B's dip days the low usually came after 10:00, but at an unpredictable time. The parked idea "wait for the close" covers this. Its fair test has to include the days that rallied away after 10:00.
- **Nothing changes in Plan B.** This goes on the parked-ideas list.
