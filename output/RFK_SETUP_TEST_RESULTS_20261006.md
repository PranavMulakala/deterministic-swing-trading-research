# Test #23: GAnderson's "range, fakeout, killshot" (RFK): results (October 6, 2026)

- **Plan:** [RFK_SETUP_TEST_PLAN_20261006.md](RFK_SETUP_TEST_PLAN_20261006.md) (8deb41c). The code (729c04a, 5 unit tests plus an independent verifier) was committed before the run.
- **Data:** daily bars for the 5,259 stocks on disk, Nov 2015 – Oct 2, 2026.
- **Results:** `output/rfk-test-results.json` + provenance.
- **The verifier matched every signal and exit** for 10 random stocks. The account adds up to within $12 (one open position).
- **A post-run fix to an information-only variant:**
  - "Buy at the next open" never closed trades that hit their stop or target on the entry day. Fixed (commit after 729c04a).
  - The main result moved by $12, because the last-day entry is now closed at its entry price.

## Verdict: FAILED (2 of 5 checks)
| Jan 2020 – Oct 2026 | RFK, 1% risk per trade | Holding SPY |
|---|---|---|
| $100,000 became | **$123,877** (+3.2%/yr) | **$260,559** (+15.3%/yr) |
| Worst drop | −13.8% | −33.8% |
| Profit factor (needs ≥ 1.3) | 1.12 | |
| Halves 2020–22 / 2023–26 | +2.7% / +20.7% | |
| Trades | 1,003 (55% winners) | |

- **Failed:** profit factor 1.12 (needs ≥ 1.3), and growth per unit of worst drop is 0.23 against SPY's 0.45.
- **Passed:** both halves profitable, a worst drop within 25%, and a drop 5+ points smaller than SPY's.
- **Since 2016:** $139,824 vs SPY $450,926.

## Does the setup itself work? A little, but it's small
Every signal on its own, with no account limits:

| Signals since 2020 | Reached 1:1 before the stop | Average result after costs |
|---|---|---|
| **RFK (1,089 signals)** | **54.0%** | **+0.064 R** |
| RFK, 2016–2019 (463) | 53.8% | +0.052 R |
| Plain baseline: red day, then a close above its high (no range or fakeout; 50,980) | 51.3% | −0.001 R |
| RFK with a 2:1 target | 32.5% | +0.09 R |
| RFK, buying at the next open instead of the close | 50.2% | −0.019 R |

- **The range-and-fakeout part does add an edge over the plain pattern:** about +2.7 points of win rate, steady across periods.
- **But it's tiny:** +0.06 of the risk per trade.
  - With 1% risk, that's about **+0.06% of the account per trade**.
  - About 150 trades a year makes roughly 3% a year, far below SPY.
- **Timing matters:** waiting for the next morning's open erased it.
- **His examples:** under these exact rules, neither Broadcom (Oct 2) nor AppLovin (Oct 5) qualified (the clear-lows and range conditions). Note too that the stock list ends Oct 2.
- **Most-traded stocks:** steady large caps (UL, SHW, MKC, AMGN, MDLZ, GIS), not the volatile names in his video.

## What this means
- RFK is one of the better setups we've tested: it beats chance slightly and drops much less than SPY.
- But at a sensible risk per trade it makes **about 3% a year**, roughly the T-bill rate. Risking more per trade would scale the drops up just as fast.
- His 3 hand-picked winners don't show the ~45% of trades that hit the stop.
- **Nothing changes in Plan B or the bots.**

**Score:** 24 pre-declared tests. Only #14 passed.
