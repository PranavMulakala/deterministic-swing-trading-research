# Test #30 results: the Reddit "VWAP monster" as a strict rule on QQQ (October 10, 2026)

**Verdict: FAIL.** It failed C1 (profit factor 0.98, needed 1.3) and C2 (lost money in 2023–2026). Plan: [VWAP_TREND_TEST_PLAN_20261010.md](VWAP_TREND_TEST_PLAN_20261010.md), committed before any result.
- **Code:** `research/vwap_trend_test_v1/` (24 unit tests).
- **Independent check:** `verify.py` matched all 1,555 trades field by field, plus 20 sampled days, and re-derived the final equity of $94,326.
- **Raw results:** `output/vwap-trend-test-results.json` and its provenance manifest.
- Research only; no orders. Dollars first, no SPY line.

## Main result (long side, Jan 2, 2020 – Oct 2, 2026, $100k cash account, 1% risk per trade)
| Measure | Value |
|---|---|
| Trades | 1,555 (about 231 a year) |
| Winners | 39.3% |
| Hit the 2× target | **27.2%** (break-even needs 33.3%) |
| Exits | 901 stopped out / 423 hit the target / 231 closed at 3:55 |
| Average win / loss | +$397 / −$263 |
| Profit factor | **0.98** |
| **Total** | **−$5,674** ($100,000 → $94,326) |
| $ per week | average −$16, median $0 |
| $1,000+ weeks | 5.9% of weeks |
| Worst week / worst month | −$3,003 (Jun 2020) / −$4,078 (May 2024) |
| Worst drop | −15.2% |

**By year:**

| Year | P&L |
|---|---|
| 2020 | +$1,407 |
| 2021 | −$1,778 |
| 2022 | **+$5,180** |
| 2023 | +$1,974 |
| 2024 | −$7,022 |
| 2025 | −$3,346 |
| 2026 | −$2,088 |

**Halves:** 2020–2022 +$4,809; 2023–2026 **−$10,483**.

**Checks:**

| Check | Result |
|---|---|
| C1: profit factor ≥ 1.3 | ✗ |
| C2: profitable in both halves | ✗ |
| C3: worst drop no worse than −25% | ✓ |
| C4: profitable in 2022 | ✓ |

**Stress window 2016–2026:** −$14,001, profit factor 0.96, and it also lost in 2018.

## What the rule does well, and why it still fails
- **Better than random:** the same number of trades at random times with the same stops lost **−$31,743 on average** (20 runs, profit factor 0.86). So the VWAP/EMA conditions do pick better moments than chance. It even made money in 2022, the year the Reddit commenters worried about.
- **Before costs it makes money:** +$28,638 (profit factor 1.11).
- **But the edge is tiny:** about **0.05 QQQ points per trade** on average (the median trade loses 0.50). Just 0.01% slippage per buy and sell turns +$28.6k into −$5.7k, because a 1%-risk trade with a tight stop holds close to the whole account each time.
- **It has faded:** 2024–2026 lost money even in the info views.

## As an MNQ futures rule
- **Before costs:** one MNQ contract would have made about **$4.15 per trade, ≈ $18 a week** (approximate: 1 MNQ ≈ $2 × 41 × QQQ points).
- **Costs:** a round trip costs about $2.24 (≈ $1.24 commission + 1 tick of slippage each way). That leaves ≈ $1.90 a trade, about **$440 a year per contract**.
- **What $1,000 weeks would take:** roughly 100+ contracts. **Not a good MNQ paper rule.**

## Information versions
| Version | Trades | Profit factor | Total |
|---|---|---|---|
| VWAP-bounce trigger | 944 | 0.95 | −$7,719 |
| Stop 1×ATR, target 2×ATR | 2,101 | 0.88 | −$25,932 |
| Short side (main window) | 1,067 | 0.96 | −$9,443 |
| Short side, 2016–2026 | 1,634 | 0.93 | −$20,154 |

- **Same-bar ambiguity:** 0 trades. A bar never reached both the stop and the target, so 5-minute data decides every trade.
- **Pilot:** the 1.5×ATR stop is 1.76× the median 5-minute bar range.

## Lesson
- Like tests #18 and #23, the conditions find a real but **very small** edge: better than random timing, but smaller than trading costs.
- The Reddit poster's chart shows a trending stretch. Across 6.75 years, the strict version loses a little money after costs.
