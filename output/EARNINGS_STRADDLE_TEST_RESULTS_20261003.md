# Test #7 results: pre-earnings straddle — **FAILED** (Oct 3, 2026)

Plan (committed before any option data): [EARNINGS_STRADDLE_TEST_PLAN_20261003.md](EARNINGS_STRADDLE_TEST_PLAN_20261003.md). Run in the owner's free QuantConnect account (project "Dancing Red Bear", backtest "Well Dressed Sky Blue Hippopotamus", free B-MICRO node, no charges). The algorithm placed no orders; it read hourly option quotes and bought at the ask, sold at the bid.

**Data window:** 2012-01-03 to 2026-07-06. QuantConnect's free tier holds back the latest ~3 months as "out of sample", so reports after early July 2026 weren't tested. **1,116 valid events** out of 1,179 scheduled.

## Headline
| | Result |
|---|---|
| Average return per event, **real bid/ask prices** | **−4.68%** (t = −9.0) |
| Median | −6.65% |
| Share of events that made money | 30.7% |
| Average return at **mid prices** (no trading cost) | **+1.81%** |
| 2012–2018 / 2019–2026 (bid/ask) | −4.50% (539) / −4.84% (577) |
| After dropping the best 5% of events | −7.24% |
| Sleeve: $100k spending 2% per event | CAGR **−7.1%**, max drawdown **−65.9%** |
| SPY, same dates | CAGR +15.0%, max drawdown −33.7% |
| Pre-market reports / after-close reports | −6.17% (208) / −4.33% (908) |
| By stock (bid/ask) | 18 of 20 negative. Only MSFT +0.37% and ORCL +1.36%; MU −10.1% (worst) |

## Pass bar
| Check | Result |
|---|---|
| 1. At least 300 events | PASS (1,116) |
| 2. Average > 0, t ≥ 2 | **FAIL** (−4.68%, t −9.0) |
| 3. Positive in both halves | **FAIL** |
| 4. Positive without the best 5% | **FAIL** |
| 5. Bar B vs SPY | **FAIL** |

## What it means
- **At mid prices the paper's effect shows up, smaller:** +1.8% per event, against +3.3% in the paper's broader, older sample. So investors may well underestimate earnings uncertainty.
- **But buying at the ask and selling at the bid costs about 6.5 points per round trip** on these short-dated straddles. That turns +1.8% into −4.7%. **The edge exists only for someone who doesn't pay the spread** (market makers), not for a retail buyer.
- It failed in both halves, on 18 of 20 stocks, and as a sleeve (−66% drawdown).
- Per the plan: it goes on the failed list. **No re-runs** with other days, strikes, stocks or exits.

## Notes
- QuantConnect's Object Store isn't writable on the free tier, so the per-event CSV wasn't saved. About 220 per-event lines printed before the terminal rate-limited them.
- The first run's "Logs" tab showed nothing for `self.log` output. Switching to `self.debug` printed the results to the terminal. The local template now matches what ran.
