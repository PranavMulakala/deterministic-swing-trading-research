# Levels, liquidity sweeps and volume spikes on momentum stocks: pre-declared test #22 plan (a correlation study), October 6, 2026

- **Written and committed before the intraday data was downloaded and before any result.** Research only; no orders.
- **Owner's request (Oct 6):** "people mark the highs and lows from previous days or an hour before the market opens … to see where we can go and take profit … four hour candles or an hour candles … liquidity sweeps … the volume things … can we test all this liquidity volume stuff for momentum to see if there's maybe a correlation with anything."
- **What kind of test this is:** a **correlation study, not a strategy test.** It asks whether any of these popular ideas tells us something about what momentum stocks do next, beyond chance.
  - Anything that passes earns a separate, pre-declared strategy test against SPY later.
  - Nothing here changes Plan B. **LITE is reported as information only:** the LITE formula freeze runs until the 8-week paper test ends, and LITE ideas go on the parked list.
- **Prior evidence:**
  - Sweeps were tested as CRT on QQQ/SPY (#8, #9) and failed.
  - Price levels were tested in #11 and #12: they were reached no more often than nearby placebo levels.
  - This test extends both to individual momentum stocks and adds premarket levels, hourly candle levels and volume spikes.
  - Academic work finds a modest "high-volume return premium": unusually high volume tends to precede slightly higher returns (Gervais, Kaniel & Mingelgrin 2001).

## Data
- **Daily, the big sample:** raw and split-adjusted daily bars for the 5,259 stocks on disk (test #21's download), Nov 2015 – Oct 2, 2026.
  - **Each day's universe:** raw close > $10 and 60-day average dollar volume ≥ $50M.
  - **"Momentum" stocks:** the top 20% of that universe by 6-month (126-day) return, all measured at the **prior** close.
- **Intraday (new download, free Alpaca SIP, under the owner's download approval for these tests):** 5-minute bars **including premarket**, Jan 3, 2022 – Oct 2, 2026.
  - **Main group:** the 100 most volatile big stocks chosen with data up to Dec 31, 2021, raw price ≥ $20 (test #15's corrected list, hindsight-free).
  - **Information group:** the 12 AI-hardware names picked with hindsight (LITE, MU, SNDK, WDC, STX, DELL, INTC, TER, MRVL, COHR, CIEN, HPE).
  - The premarket is 4:00–9:29 ET. Yesterday's 1-hour candles start at 9:30 (the last is 15:30–16:00). Its 4-hour candles are 9:30–13:30 and 13:30–16:00.

## The 5 hypotheses (one primary measure each)
**Placebo levels** (H1–H4): the same stock and day, at the real level × (1 − 1%), (1 − 0.5%), (1 + 0.5%), (1 + 1%). For sweeps they are ±1% and ±2%. Each placebo is used only on days where it qualifies the same way. The effect is **the real level minus the average of its placebos**, so a level only "matters" if it behaves differently from nearby prices that aren't special.

| # | Idea | Event | Primary measure | Data |
|---|---|---|---|---|
| H1 | **Previous-day high as a take-profit spot** | The stock opens below yesterday's high and trades up to it | Share of those days that **close back below it** ("it stalled there") | Daily, momentum stocks |
| H2 | **Premarket high as a take-profit spot** | Opens below the premarket high and trades up to it | Share that close back below it | Intraday, main group |
| H3 | **Yesterday's 1-hour candle highs** | The lowest of yesterday's hourly-candle highs that is above today's open, excluding yesterday's high itself (that's H1); price trades up to it | Share that close back below it | Intraday, main group |
| H4 | **Liquidity sweep of yesterday's low, then reclaim** | The low goes under yesterday's low, and the day closes back above it | **Next day's return** (close to close, minus SPY's), vs placebo sweeps of levels ±1% and ±2% away | Daily, momentum stocks |
| H5 | **Volume spike on an up day** | Volume ≥ 2× its 50-day average and a gain ≥ +4% | **Next 5 days' return** (minus SPY's), vs **non-spike days with a similar gain** (volume < 1.5×), compared within gain buckets of 4–6%, 6–10% and 10%+ | Daily, momentum stocks |

## When does something count as a real correlation? (all three needed)
1. **Statistically:** a confidence interval from a **day-block bootstrap** (1,000 resamples of trading days, seeded), so same-day moves across stocks don't fake precision. The 5 primary tests are **Holm-corrected** (overall 5% false-alarm rate).
2. **Not one lucky stretch:** the same sign and p < 0.05 in **both halves**:
   - daily: 2020–2022 and 2023–2026;
   - intraday: 2022–2023 and 2024–2026.
3. **Big enough to matter:** at least **5 percentage points** of stall rate (H1–H3), or **0.25% per trade** (H4, H5; about a round trip's cost plus a margin).

**Windows (the owner's post-COVID default):**
- **Daily:** main Jan 2, 2020 – Oct 2, 2026; 2016–2019 reported as a stress check.
- **Intraday:** Jan 3, 2022 – Oct 2, 2026 (all the intraday data).

## Also reported (information only, decided now)
- **Reach rates** (the "magnet" idea): how often the real level is reached vs the ±0.5% placebos.
- How far price runs **past** each level by the close once it's reached, i.e. the cost of selling there too early.
- **Other groups:**
  - H1, H4 and H5 on all liquid stocks (not just momentum);
  - H1 on the intraday groups;
  - the bearish mirror of H4 (a sweep of yesterday's high that closes back below);
  - the down-day mirror of H5;
  - 1-day and 20-day horizons for H5;
  - the 4-hour candle version of H3;
  - the premarket low and yesterday's low as support levels.
- **The AI-hardware group, and LITE alone** (small samples, not decisive), plus whether LITE's Oct 5 volume met H5's spike definition.

## Checks
- **Unit tests on hand-built bars:**
  - each event definition;
  - placebos;
  - the gain buckets;
  - premarket and hourly-candle levels;
  - the bootstrap and the Holm correction.
- **An independent recount:** event counts and rates for H1, H4 and H5 on 10 random stocks, and H2/H3 on 5 random stocks, with separate code.
- Provenance manifest. **Nothing will be tuned afterwards:** no other thresholds, levels, horizons or groups.
