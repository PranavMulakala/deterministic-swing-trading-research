# Does "2× leverage only in uptrends" beat holding the market? Pre-declared test #14 (October 5, 2026)

Written and committed **before** any result was computed. Research only; no orders.

The owner asked to beat SPY's 14.8% a year. The idea comes from Gayed & Bilello (2016), "Leverage for the Long Run": hold leveraged stocks only while the market is above its 200-day average, otherwise hold T-bills. The owner: "yes download it and run test 14".

## Data
- **Main:** Ken French Data Library, daily factors (`F-F_Research_Data_Factors_daily.csv`, built from CRSP 202608). Downloaded Oct 5, 2026 with the owner's OK into `outputs/lev_trend_data/` (gitignored).
  - **Market daily total return** = (Mkt-RF + RF) / 100: all US stocks, value-weighted, dividends included. Close to the S&P 500.
  - **Cash daily return** = RF / 100 (1-month T-bill).
  - **Dates:** Jul 1, 1926 – Aug 31, 2026. The first 200 trading days only build the average, so results start once it exists (~1927).
- **Real-fund check (2016–2025, Alpaca, dividend-adjusted):** SPY, SSO (2× S&P), QQQ, QLD (2× Nasdaq-100). The cash return for this check is the French RF series.

## The rules (main candidate: "2× above the 200-day")
1. **Market level:** a total-return index built by compounding the market's daily return.
2. **Signal at each day's close:** "up" if the index is above its 200-day simple moving average, otherwise "down".
3. **Positions:** the signal at day t's close sets the position for day t+1's return (no peeking).
   - **Up:** 2× the market, rebalanced daily, like a 2× ETF. Daily return = 2 × market − 1 × (cash rate + 0.50%/yr borrowing spread) − 0.90%/yr fund expense.
   - **Down:** T-bills (the cash return).
4. **Switching cost:** 0.10% of the account each time the position changes.
5. **Taxes ignored.** Switching creates taxable sales in a regular account; this is stated in the results.

## Compared against (all from the same data)
- **Holding the market (1×):** the benchmark.
- **Holding 2× permanently** (same cost formula, no filter): shows what the filter adds.
- **Information only:** 1× with the same 200-day filter; 3× with the filter; 3× held permanently. 3× costs: 3 × market − 2 × (cash + 0.50%) − 0.95%/yr.

## It counts as working only if all hold (full history, main candidate vs holding the market)
1. **Growth (CAGR) at least 2 points a year higher** than holding the market.
2. **Worst peak-to-trough drop no worse** than holding the market's.
3. **CAGR ÷ |worst drop| higher** than the market's.
4. **Higher CAGR than the market in both halves:** 1927–1975 and 1976–2026.

If any fail, it didn't beat holding the market. **Nothing will be tuned afterwards:** no other averages (no 100- or 150-day), leverage levels or costs.

## Also reported
- Results by decade, and for 1990–2026 and 2000–2026.
- Number of switches per year; share of time invested.
- The worst years (1929–32, 1973–74, 1987, 2000–02, 2008, 2020, 2022) for each strategy.
- **Real-fund check:**
  - The same 2× formula on SPY's daily returns vs the actual SSO, 2016–2025 (growth difference per year), to confirm the cost assumptions are realistic.
  - The QQQ version (2× QLD above QQQ's 200-day, else T-bills) on 2016–2025 actual fund prices. Information only, because it's a short window.
- Provenance manifest.

## Checks
- Unit tests: signal lag (no peeking), leverage cost formula, switching cost.
- An independent re-computation of the main equity curve with separately written code; it must match.
