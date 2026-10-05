# Tracking Collective2 strategies alongside our tests: "ares" and "US Stock Momentum" (started October 5, 2026)

**Baseline snapshot:** `research/ares_tracking/snapshot_20261005.json`, taken from its public page on Oct 5.
- **Stats:** +32.6%/yr since Sep 2020, worst drop −14.1%, 763 closed trades, 72 live AutoTraders, $9.9M following.
- **2026 so far:** +12.1%. The last three full months were small: Jul +0.6%, Aug −2.6%, Sep +2.3%.
- **Recent trades** (Jul 13 – Oct 2, 2026): 30 trades, 8 winners. One big winner (+$4,920 on Sep 21) covers several ~$700–1,000 stop-outs. That's the trend-following pattern: lose small often, win big sometimes.
- **The prices look real:** e.g. the Oct 2 entry at 31,229 on MNQ Dec fits Nasdaq futures trading around 31,000–31,100 that morning (the Options Insider stream from that day said the same).

## How tracking works (no waiting needed to read the history)
- **Its history is already recorded going forward** (not a backtest) since 2020. What waiting adds is confirmation that it keeps working, and that its fills match real prices.
- **Weekly:** in each session, re-read its page and record new trades and the month's result vs the claims.
- **Independent price check:** our own IBKR paper collector records live MNQ prices from Oct 6. Each week, ares' entry and exit prices can be compared with our recorded MNQ quotes at the same minutes. This is a check Collective2's marketing can't fake.
- **Decision point:** after about 4–8 weeks of matching fills and results in line with its history, decide whether paying ($100/mo, a supported futures broker needed) makes sense. Robinhood isn't on Collective2's broker list.

## Added Oct 5: US Stock Momentum (`research/ares_tracking/us_stock_momentum_snapshot_20261005.json`)
- **What it does** (its page): the top 10 S&P 500 stocks by momentum, with an uptrend filter, rebalanced monthly. It is mostly shares, but it also bought an XSP option that expired worthless (−$4,162).
- **Results:**
  - **2025 (from Jun):** +27.6%.
  - **2026 so far:** +107.3%.
  - **Worst drop:** −39.2%.
  - **July 2026:** −30.5% in one month.
  - **Following:** 31 live AutoTraders, $2.9M. Price $99/mo.
- **Overlap warning:** its recent holdings are the owner's same bet: LITE, SNDK, WDC, STX, MRVL, INTC, AMAT. Following it would add more exposure to AI hardware and memory on top of MU and LITE, not spread it out.
- **Tracking:** record the monthly result vs the claims each session. Watch how it behaves in the next tech pullback.
