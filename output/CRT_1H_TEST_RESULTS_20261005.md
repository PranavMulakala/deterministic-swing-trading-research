# Test #9: 1-hour CRT (candle range theory): results (October 5, 2026, morning)

- **Plan:** [CRT_1H_TEST_PLAN_20261005.md](CRT_1H_TEST_PLAN_20261005.md), committed (8699646) before any 1-hour result.
- **Code:** `research/crt_1h_test_v1/` (`backtest.py`, `verify.py`, 4 unit tests).
- **Results:** `output/crt-1h-test-results.json` + `.provenance.json`.
- **Data:** the same QQQ/SPY 5-minute SIP bars as test #8, 2016 – Oct 2, 2026.
- **Independent check:** reproduced all 2,960 trades with 0 mismatches and the same final equity on all four accounts.

## Verdict: FAILED. No edge shown.

| Account ($100k each) | Trades | Target hit | Winners | Avg win / avg loss | Profit factor | $100k became | Worst drop |
|---|---|---|---|---|---|---|---|
| **QQQ long** (counts) | 774 (72/yr) | 56.6% | 59.0% | $133 / $274 | **0.70** | **$73,934** | −27.0% |
| **SPY long** (counts) | 799 (75/yr) | 61.7% | 60.6% | $120 / $223 | **0.83** | **$87,847** | −13.5% |
| QQQ short (info) | 695 | 54.7% | 56.0% | $147 / $264 | 0.71 | $76,274 | −23.8% |
| SPY short (info) | 692 | 62.6% | 58.5% | $120 / $207 | 0.82 | $89,187 | −13.5% |
| **Holding SPY** | — | — | — | — | — | **$451,000** | −33.8% |

**Checks for QQQ long and SPY long:**
- **Profit factor ≥ 1.3:** no (0.70, 0.83).
- **Profitable in both halves:** no (QQQ −8.5% / −19.2%; SPY −2.8% / −9.6%).
- **Drawdown ≤ 25%:** QQQ no (−27.0%), SPY yes (−13.5%).
- **Bar B vs SPY:** no; both lost money.

## Why it loses, in plain words
- **It wins more often than the 15-minute version** (about 60% of trades), but **the average loss is about twice the average win.**
- **The setup puts the target close and the stop far away:**
  - You buy when price breaks above the middle candle's high, which is usually just under the target (the first candle's high).
  - The stop sits all the way down at the sweep low.
  - Median target: **0.12–0.18%** away. Median stop: **0.33–0.44%** away. So you risk about $2.50 to make $1.
- **Before trading costs:**
  - SPY is roughly break-even: profit factor 1.04, +2.9% over 10¾ years.
  - QQQ still loses: profit factor 0.84, −14%.
  - Even the best case is cash-like at best, against +351% for holding SPY.
- **Same-bar ambiguity is about 0%.** The stop and target are too far apart to both be hit in one 5-minute bar, so the result doesn't depend on that assumption.

## Together with test #8
**Both CRT timeframes failed on 10¾ years of QQQ and SPY:**
- **15-minute:** profit factor 0.48–0.56, roughly −65%.
- **1-hour:** profit factor 0.70–0.83, −12% to −26%.

The "sweep and reclaim" pattern does hit its target more than half the time, which is probably why it looks great in TikTok recaps. But where the target and the stop sit makes the losses bigger than the wins.

**Test record: 9 pre-declared tests; none beat holding SPY.**
