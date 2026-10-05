# Test #8: 15-minute sweep-and-reclaim (CRT): results (October 5, 2026, overnight)

- **Plan:** [CRT_SWEEP_TEST_PLAN_20261005.md](CRT_SWEEP_TEST_PLAN_20261005.md), committed (bda086a) before any data was downloaded.
- **Code:** `research/crt_sweep_test_v1/`: `fetch.py`, `backtest.py`, `verify.py`, plus 7 offline unit tests.
- **Results:** `output/crt-sweep-test-results.json`, with the provenance manifest `output/crt-sweep-test-results.json.provenance.json` (code + data SHA-256).
- **Data:** Alpaca SIP 5-minute bars, regular session, Jan 2016 – Oct 2, 2026. 481k QQQ bars and a similar SPY file.
- **Independent check:** `verify.py` (explicit short logic, no mirroring) reproduced **all 14,539 trades with 0 field mismatches** and the same final equity on all four accounts.

## Verdict: FAILED every check, on both symbols and both sides. No edge shown.

| Account ($100k each) | Trades | Target hit | Winners after costs | Profit factor | $100k became | Worst drop | 2016–20 / 2021–26 |
|---|---|---|---|---|---|---|---|
| **QQQ long** (counts) | 3,765 | 53.8% | 42.6% | **0.55** | **$31,950** | −68.1% | −38.4% / −48.2% |
| **SPY long** (counts) | 3,667 | 54.1% | 38.1% | **0.48** | **$35,919** | −64.2% | −38.8% / −41.3% |
| QQQ short (info) | 3,553 | 53.5% | 42.0% | 0.56 | $37,334 | −62.7% | −36.7% / −41.0% |
| SPY short (info) | 3,554 | 54.4% | 39.3% | 0.48 | $38,482 | −61.6% | −34.3% / −41.4% |
| **Holding SPY** | — | — | — | — | **$451,000** (+351%) | −33.8% | — |

**Every year from 2016 to 2026 lost money in all four accounts.**

## Why it loses, in plain words
- **The video's "85–90%" is really about 54%.** The target is hit only a little more than half the time.
- **The target is tiny, and closer than the stop.**
  - Median distance to the target: **0.07% on QQQ** (about 35 cents on a $500 share) and 0.05% on SPY.
  - Median distance to the stop: 0.10% / 0.08%.
  - So a typical win is about **0.7× the size of a typical loss**. Winning 54% of the time at 0.7-to-1 loses money.
- **Even with zero trading costs it loses:** profit factor 0.82 (QQQ long), 0.82 (SPY long), 0.85 / 0.83 (shorts).
  - With costs of 0.01% per side, many "target hits" become small losses. 38–49% of targets are under 0.05% away, so 0.02% of round-trip cost eats a big share of them.
- **The same-bar assumption doesn't change the answer.** Both the stop and the target were touched in the same 5-minute bar on 3.9–4.2% of trades. Counting all of those as wins instead of losses still gives a profit factor of 0.53–0.62.

## What this does and doesn't mean
- **It's one fixed, mechanical reading:** consecutive 15-minute candles, a 30-minute entry window, the stop at the signal bar, the target at the first candle's far side. The videos add judgment ("bias", "untested highs", key levels) that can't be tested objectively. Fixed rules were the point: they can't be tuned after seeing results.
- **Nothing will be tuned.** No other candle sizes, windows or filters.
- **It also covers batch 3 video u5** (sweep an untested high or low, fail to close beyond it, trade the bounce) in its simplest intraday form, and the core of batch 2 #9 (full CRT).
- **Test record is now 8 pre-declared tests; none beat holding SPY.**
