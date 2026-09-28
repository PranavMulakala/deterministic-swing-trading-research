# SPY bull put spread backtest — development results and pre-declared holdout (Sept 28, 2026, about 17:30 ET)

> **Holdout result (18:15 ET): FAILED.** The candidate lost $1,809 under natural fills (−1.33% average return on risk). See [SPY_SPREAD_BACKTEST_HOLDOUT_RESULTS_20260928.md](SPY_SPREAD_BACKTEST_HOLDOUT_RESULTS_20260928.md).

Historical replay only; this is not live evidence. Code: `research/spy_put_spread_backtest_v1/backtest.py`.

- **Data:** Databento OPRA `cbbo-1m` for the SPY chain at 10:30 ET and the close each trading day, bought with the owner-approved free credit. Development period: **2013-04-01 to 2021-03-31**, 2,016 trading days, none missing.
- **Account:** $100,000 paper; 2% risk per trade, at most 5 contracts.
- **Exits:** profit-take at 50%, break-even exit, time exit at 5 or fewer sessions. Mondays only.
- **Fills:** "mid" = all fills at mid; "natural" = pay the full bid/ask spread on every fill. Real fills lie in between.

## Development results (2013-04 to 2021-03)

| Variant | Fills | Vol filter | Trades | Per year | Win % | Avg win | Avg loss | Worst | Total P&L | Avg return on risk | Max DD |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Approved: $5 wide, min $0.75 | mid | yes | 1 | 0.1 | 100 | $152 | – | $152 | +$152 | 8.9% | −0.4% |
| Approved: $5 wide, min $0.75 | natural | yes | 1 | 0.1 | 100 | $144 | – | $144 | +$144 | 8.4% | −0.4% |
| Approved: $5 wide, min $0.75 | mid | no | 3 | 0.4 | 100 | $153 | – | $152 | +$459 | 9.0% | −0.4% |
| Approved: $5 wide, min $0.75 | natural | no | 3 | 0.4 | 100 | $142 | – | $140 | +$427 | 8.3% | −0.4% |
| $5 wide, min $0.50 | mid | yes | 47 | 5.9 | 89 | $113 | −$641 | −$856 | +$1,533 | 1.9% | −1.5% |
| $5 wide, min $0.50 | natural | yes | 46 | 5.8 | 89 | $108 | −$889 | −$1,744 | −$22 | 0.0% | −2.5% |
| $5 wide, min $0.50 | mid | no | 86 | 10.8 | 91 | $112 | −$532 | −$842 | **+$4,517** | 3.0% | −1.4% |
| $5 wide, min $0.50 | natural | no | 79 | 9.9 | 89 | $106 | −$766 | −$1,744 | **+$502** | 0.4% | −2.2% |
| 0.25/0.10 delta, no min | mid | yes | 75 | 9.4 | 84 | $95 | −$586 | −$973 | −$1,032 | −0.6% | −2.7% |
| 0.25/0.10 delta, no min | natural | yes | 71 | 8.9 | 83 | $92 | −$633 | −$1,163 | −$2,185 | −1.5% | −3.4% |
| 0.25/0.10 delta, no min | mid | no | 136 | 17.0 | 86 | $99 | −$515 | −$973 | +$1,799 | 0.9% | −2.2% |
| 0.25/0.10 delta, no min | natural | no | 130 | 16.3 | 85 | $96 | −$513 | −$1,163 | +$920 | 0.5% | −2.2% |

## Findings
1. **The approved rule almost never trades.** A $5-wide spread with a ~0.20-delta short collected a median of only $0.40–$0.67 (8–13% of width) per year from 2013 to 2021. The $0.75 minimum was met on about 18 of 380 Mondays, mostly in 2020. This matches the live check on Sept 28: mid credit $0.59.
2. **The volatility filter hurt in this period** for both structures: fewer trades and lower totals. This is the opposite of FlashAlpha's 2020–2025 finding, which used different exits.
3. **Fill quality decides the result.** The best variant makes +$4,517 over 8 years at mid and only +$502 when paying the full spread. The "edge" is about the size of the bid/ask cost.
4. **The tail dominates.** About 90% of trades win about $110, but single crash weeks cost $800–$1,744: Aug 2015, Mar 2018, Feb 24 2020. The losing years were 2018 and 2020, plus 2015 under natural fills.
5. **Magnitude:** even the best case is about +0.06% to +0.56% a year on the whole $100k account at 2% risk sizing. The cash collateral can separately earn T-bill interest.

## Pre-declared holdout test (decided before any April 2021–2025 data was viewed)
- **Holdout period:** trades entered **2021-04-01 to 2025-12-31**, run once when the download completes.
- **The one candidate tested:** **$5 wide, 0.20-delta short, minimum credit $0.50, no volatility filter.** It had the best development results under both fill assumptions. The other variants will be shown for completeness only.
- **Success criteria:** under **natural** fills, holdout total P&L > $0 **and** average return on risk ≥ +1.0% per trade. Mid results will be reported too.
- **If it fails:** conclude that no edge has been demonstrated. No further tuning on the holdout.
- **Caveats:**
  - The volatility-filter idea came from a 2020–2025 study, so the holdout is not untouched for that idea (it is not the candidate).
  - There are only two snapshots a day, so some intraday profit-take fills may be missed.
  - Deltas and IV come from Black–Scholes.
- **The live paper bot is unchanged.** It still runs the approved rules (min $0.75, with the filter) until the owner decides otherwise.
