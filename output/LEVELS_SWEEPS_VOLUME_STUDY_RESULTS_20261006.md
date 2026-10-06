# Test #22: levels, liquidity sweeps and volume spikes on momentum stocks (a correlation study): results (October 6, 2026)

- **Plan:** [LEVELS_SWEEPS_VOLUME_STUDY_PLAN_20261006.md](LEVELS_SWEEPS_VOLUME_STUDY_PLAN_20261006.md), committed (a99670d) before the intraday data and before any result.
- **Code:** `research/levels_volume_v1/`:
  - `fetch.py`, the download (ca81a0e);
  - `study.py`, `test_study.py` (7 unit tests) and `verify.py`, all committed (d8d7456) before the run.
- **Data:**
  - **Daily:** bars for 5,259 stocks, Nov 2015 – Oct 2, 2026. "Momentum" means the top 20% of liquid stocks (raw close > $10, 60-day dollar volume ≥ $50M) by 6-month return, measured at the prior close.
  - **Intraday:** 5-minute bars **including premarket**, Jan 2022 – Oct 2, 2026, for 112 stocks (6,425 requests):
    - the 100 most volatile big stocks chosen with data up to Dec 31, 2021 (hindsight-free);
    - the 12 AI-hardware names (information only).
- **Results:** `output/levels-volume-study-results.json` + `.provenance.json`.
- **Checks:**
  - 7 unit tests pass.
  - **The independent recount matched everything:**
    - the momentum cut-off on 5 random days;
    - every count for 10 random stocks in both groups;
    - the premarket-high and hourly-candle counts for 5 intraday stocks.

## Verdict: none of the 5 ideas shows a real correlation
Each real level is compared with "placebo" prices 0.5% and 1% above and below it, on the same stock and day. A level only counts if it behaves differently from nearby prices that aren't special.

| # | Idea, on momentum stocks | Real level | Nearby prices | Difference | Passes? |
|---|---|---|---|---|---|
| H1 | Price reaches **yesterday's high**: share that close back below it | 50.5% | 51.0% | −0.5 points | **No** |
| H2 | Price reaches the **premarket high**: close back below | 51.0% | 50.8% | +0.2 points | **No** |
| H3 | Price reaches **yesterday's nearest 1-hour candle high**: close back below | 50.7% | 51.1% | −0.3 points | **No** |
| H4 | **Sweep of yesterday's low** (dips under, closes back above): next day vs SPY | −0.01% | the same after placebo sweeps | 0.00% | **No** |
| H5 | **Up day of +4% or more on 2× normal volume:** next 5 days vs SPY | | vs similar up days on normal volume | **+0.9%** | **No** (closest) |

- **H1:** 116,675 times the price reached yesterday's high (2020–2026). The −0.5 points is "detectable" (p = 0.001) only because the sample is huge.
  - It's 10 times smaller than the 5-point bar.
  - It isn't significant in 2023–2026, and it flips sign in 2016–2019.
- **H2 / H3:** 69,123 and 68,395 touches. Nothing: p = 0.39 and 0.29.
- **H4:** 71,472 sweeps; nothing (p = 0.86). The mirror case, a sweep of yesterday's high that closes back below, was also nothing (−0.03% the next day).
- **H5:** 4,411 volume spikes vs 19,523 normal-volume up days.
  - **The extra gain:** +0.9% over the next 5 days (95% range +0.1% to +1.7%), and +1.3% over 20 days.
  - **Positive in all three periods:**
    - 2020–2022: +0.8% (p = 0.24);
    - 2023–2026: +1.0% (p = 0.04);
    - 2016–2019: +0.7% (p = 0.21).
  - **Why it still fails:** after correcting for testing five ideas, p = 0.11. It also isn't significant in both halves.
  - Across all liquid stocks (not just momentum) the extra gain is only +0.4%.
  - **Treat it as a hint, not a finding.** It matches the academic "high-volume return premium" (Gervais, Kaniel & Mingelgrin 2001).

## What this means for taking profit
- **Reaching a level is a coin flip.** When a momentum stock reaches yesterday's high, it closes back below about half the time, and so it does at any price 0.5–1% away. On average it closes right at the level (−0.01%). The same holds at premarket highs and hourly-candle highs.
- **So a "level" is not a better place to sell than a nearby price.** It's still a useful, concrete price for planning an exit.
- **"Price is drawn to levels" (information only):**
  - The premarket high and hourly-candle highs look "magnetic": they're reached 67–75% of the time, against 64–66% for nearby prices.
  - But that comes from how they're picked: they're the nearest level above the open, so they're closer by construction. It's not evidence of a magnet.
  - Yesterday's high: 41.5% vs 40.5%.

## LITE (information only; small samples, not decisive)
| Since 2022 | Closed back below (or, for support, held) | Nearby prices | Touches |
|---|---|---|---|
| Yesterday's high | 47.7% | 48.4% | 390 |
| Premarket high | 48.9% | 47.6% | 470 |
| Yesterday's nearest 1-hour high | 49.3% | 48.7% | 664 |
| Premarket low as support (held) | 55.6% | 52.7% | 435 |

**Oct 5:** LITE traded 0.63× its 50-day average volume and rose 0.6%. It was **not** a volume spike.

## Conclusion
- **Levels and sweeps help you plan exits and cap risk:** they give you concrete prices. **They don't tell you which way the stock goes from there.**
- **The volume-spike hint (+0.9% over 5 days) is the only thing worth remembering.** It's too small and too uncertain to trade on its own; it could be a candidate for a future strategy test.
- **Nothing changes in Plan B, the bots, MNQ or the EP watch.** The LITE formula freeze holds.

**Score:** 22 pre-declared tests. Only #14 passed, and it ties the market since 2000.
