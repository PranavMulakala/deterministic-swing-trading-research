# Test #10: monthly SPY cash-secured puts vs holding SPY: results (October 5, 2026, 9:09 AM)

- **Plan:** [CSP_SPY_TEST_PLAN_20261005.md](CSP_SPY_TEST_PLAN_20261005.md), committed (6bbbc9f) before any result.
- **Code:** `research/csp_spy_test_v1/` (`backtest.py`, `verify.py`, 5 unit tests), committed ed4177b before the run.
- **Results:** `output/csp-spy-test-results.json` + `.provenance.json`.
- **Data:** Databento OPRA SPY chain at 10:30 ET and the close, all 2,514 trading days from Jan 4, 2016 to Dec 31, 2025. No new download, no cost.

## Verdict: did NOT beat holding SPY

It passed 4 of the 5 checks, including all of bar A. **It failed the risk-adjusted comparison with SPY.**

| Check | Needed | Result |
|---|---|---|
| A1 Profit factor | ≥ 1.3 | **1.39 ✓** |
| A2 Profitable in both halves | both > 0 | **+5.9% (2016–20) ✓, +45.9% (2021–25) ✓** |
| A3 Worst drop | ≤ 25% | **−22.2% ✓** |
| B1 Drop at least 5 points smaller than SPY's | ≥ −28.8% | **−22.2% vs SPY −33.8% ✓** |
| B2 CAGR ÷ drop higher than SPY's | > 0.438 | **0.201 ✗** |

## The money, $100,000 at the start of 2016 → end of 2025
| | Ends with | Per year | Worst drop |
|---|---|---|---|
| **Holding SPY (dividends reinvested)** | **$396,400** | 14.8% | −33.8% |
| **Selling a ~30-delta put every month (main test, sold at the bid)** | **$154,556** | 4.5% | −22.2% |
| Same, sold at the midpoint (best case, info) | $159,169 | 4.8% | −22.0% |
| At-the-money puts (Cboe PutWrite style, info) | $193,561 | 6.8% | −23.6% |
| ~20-delta puts, further from the price (info) | $146,464 | 3.9% | −21.6% |

## What happened, in plain words
- **111 puts sold. 80% expired worthless; 82% made money.** The high win rate is real.
- **A typical win was about $1,000; a typical loss about $3,300.** The worst single month was **March 2020: −$25,986** on one put. It was sold on Feb 18 at the $329 strike, and SPY closed at ~$240 on Mar 18.
- **About half the profit was just T-bill interest on the cash:**
  - **$28,282 from interest**, which you'd get by holding T-bills and doing nothing;
  - **$25,446 from selling puts** (premium kept, minus losses), about $2,500 a year on $100k.
- **Losing years:** 2018 (−$2,817), **2020 (−$10,745)** and 2022 (−$2,606). Best year: 2025 (+$9,002).
- **Trading costs barely mattered:** selling at the midpoint instead of the bid adds only ~$4,600 over 10 years. Unlike the spread test, costs aren't what holds it back. The cap does: you keep only the premium when SPY rises, but take most of the loss when it falls.
- **The strike was typically 2.3% below SPY's price**, with a delta of −0.30 as planned.

## Why it trails SPY even though it "wins" 82% of the time
Over 2016–2025, SPY rose about 4×. A put seller earns the premium in an up month however far SPY rises, so it gives up nearly all of a bull market's upside. In return it gets a smaller worst drop (−22% vs −34%). That's a real trade-off, but the drop shrank much less than the return did:
- **Return:** about one-third of SPY's per year.
- **Worst drop:** about two-thirds of SPY's.

## Checks on the result
- **Independent verifier:**
  - All 111 sale prices match the real 10:30 bids (and midpoints) in the raw files.
  - Using Alpaca's actual SPY close instead of the parity price changes **no outcome** (median difference 6 cents).
  - Trade P&L matches to within 2 cents of rounding on all trades.
- **Cash-path reconciliation:**
  - The verifier's cash from the closed trades is $153,726.
  - The backtest also holds one put still open on Dec 31, 2025: the Jan 16, 2026 $665 put, sold for $1,268 and marked at $440.
  - $153,726 + $1,268 − $440 + ~$2 of interest = **$154,556**, the reported final equity. The verifier doesn't see open positions, which is the only reason its raw number differs.
- **Provenance manifest** written (code + every data file hashed).

## What this means
- **Selling cash-secured puts is the first options idea here with real substance:** it passed every bar-A check, unlike the CRT, breakout and spread tests. The edge is real but small.
- **It's a "calmer, much lower-return" way to be in the market, not a way to beat it.** For someone who would otherwise hold cash or T-bills, it beat T-bills: $154.6k vs **$125.3k** from T-bill interest alone (same rates, computed the same way). For someone who would hold SPY, it cost about $240,000 over 10 years on $100k.
- **The right use is the one the TikTok video described:** sell a put only on something you'd actually like to own at the strike price, as a way to get paid while waiting. It isn't an income machine.
- **Taxes would widen the gap:** option premiums are short-term gains taxed as ordinary income, while SPY held for years is taxed at lower long-term rates.
- **Test record: 10 pre-declared tests; none beat holding SPY.** Two (the SMA50 rule and this one) passed bar A.
