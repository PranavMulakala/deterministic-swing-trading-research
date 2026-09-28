# SPY bull put spread: pre-declared holdout result (September 28, 2026, about 18:15 ET)

Historical replay only; not live evidence.
- **Pre-declared:** [SPY_SPREAD_BACKTEST_DEV_RESULTS_20260928.md](SPY_SPREAD_BACKTEST_DEV_RESULTS_20260928.md) (commit dcc6f77), before any April 2021–2025 data was viewed.
- **Data:** Databento OPRA `cbbo-1m`, 3,210 trading days from 2013-04-01 to 2025-12-31, with none missing. It used about $6.44 of the free credit, against $64 approved.
- **Results:** `output/spy-put-spread-backtest-2013-2025.json`. Code: `research/spy_put_spread_backtest_v1/backtest.py`.

## Verdict: failed. No edge has been demonstrated.

The one candidate tested: $5 wide, 0.20-delta short put, minimum credit $0.50, no volatility filter. It covers trades entered from 2021-04-01 to 2025-12-31.

| Fills | Trades | Win % | Total P&L | Average return on risk | Worst trade |
|---|---:|---:|---:|---:|---:|
| **Natural (the pre-declared test)** | 78 | 85% | **−$1,809** | **−1.33%** | −$2,220 |
| Mid (optimistic bound) | 81 | 85% | +$1,260 | +1.00% | −$930 |

Success required a natural-fill total above $0 and an average return on risk of at least +1.0%. Both failed. Per the plan, there will be no further tuning on this data.

**Correction check.** One natural-fill exit, on Aug 5, 2024, paid more than the spread's $5 width because quotes were extremely wide. A real limit order would never pay above the width. Capping that exit gives −$1,361 and −1.00%, which still fails.

## Every other variant in the same holdout (natural fills)

| Variant | Volatility filter | Trades | Total | Average return on risk |
|---|---|---:|---:|---:|
| **Approved rule (what the paper bot runs):** $5 wide, minimum $0.75 | yes | 3 | −$289 | −5.67% |
| Approved rule | no | 8 | −$1,008 | −7.49% |
| $5 wide, minimum $0.50 | yes | 33 | −$3,616 | −6.18% |
| 0.25/0.10 delta, no minimum | yes | 20 | −$1,687 | −4.40% |
| 0.25/0.10 delta, no minimum | no | 56 | −$755 | −0.72% |

Every variant lost money in the holdout. This was during a period when SPY rose strongly: +337% in price from April 2013 to December 2025.

## What it means
- **The same shape as the development period.** About 85% of trades won about $114. About 1 in 7 lost about $780, which wiped out the gains. The worst losses came in the April 2022, August 2022, August 5 2024 and March 2025 selloffs.
- **The approved rule barely trades.** It traded 4 times in 12¾ years, so the paper options bot will almost never place a trade.
- **It is no route to the owner's $1,000-a-week goal.** The best case here, mid fills, is about +$265 a year on a $100,000 account at 2% risk per trade. A larger size doesn't fix a strategy that loses after costs; it only makes the losses bigger.

## Choices for the owner (nothing has been changed)
1. Leave the paper options bot running as a harmless plumbing check. It will rarely trade and sends one email per weekday.
2. Switch it off by unloading its launchd job, to cut email noise.
3. Treat SPY put-spread selling as closed research. Any new options idea gets its own pre-declared plan.

In every case: no live options trading on these rules.
