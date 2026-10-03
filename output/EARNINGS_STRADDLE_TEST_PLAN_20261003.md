# Pre-declared test #7: buy a straddle 3 trading days before earnings, sell before the report

Written Oct 3, 2026, **before any option prices for this test were looked at.** The rules below are fixed and will not be tuned after results are seen. Evidence only, not advice. Paper or backtest only; no real money.

## Why this idea (independent evidence)
Gao, Xing & Zhang (2018, *Journal of Financial and Quantitative Analysis*): stock straddles normally lose money, but at-the-money straddles bought 3 days before an earnings announcement earned **+3.34%** on average up to the announcement. The effect was strongest in small, costly-to-trade stocks. This test asks whether it survives **real bid/ask prices on large, liquid stocks**, where the owner could actually trade. It's the one idea from Joey's material with outside support (his AMZN pre-earnings trade). Follows goal part 3: test only ideas with independent evidence.

## Rules
| Item | Rule |
|---|---|
| Stocks (fixed list of 20) | AAPL, MSFT, AMZN, GOOGL, META, NVDA, TSLA, NFLX, AMD, INTC, MU, ORCL, CRM, ADBE, AVGO, QCOM, CSCO, JPM, BAC, XOM. **No LITE** (Lumentum policy: no LITE options for the owner) |
| Events | Every quarterly report from 2012-01-01 to 2026-09-30 whose timing is labeled "pre-market" or "post-market" (Alpha Vantage EARNINGS). Other or unknown timing: skipped |
| Last close before the report (L) | Post-market report: the report date. Pre-market report: the trading day before it |
| Entry day (E) | 3 trading days before L |
| Which options | At 10:00 on E: the expiration is the nearest one **after L**, so the report falls before expiry. Strike: the listed strike nearest the stock price (tie: the lower). Buy 1 call + 1 put |
| Entry price | **Ask** prices of both legs at the close of E (the last hourly quote of the day) |
| Exit | **Bid** prices of both legs at the close of L. Always out **before** the report |
| Skip | Either leg missing a two-sided quote at entry or exit, or either leg's bid/ask gap wider than 20% of its mid at entry |
| Event return | (call bid + put bid at exit) ÷ (call ask + put ask at entry) − 1 |
| Data | QuantConnect cloud (AlgoSeek US equity options, hourly bars), run by the owner in their own free account |

## Pass bar: all five must hold, on bid/ask returns
1. At least **300** valid events.
2. Average event return **> 0** with a t-statistic **≥ 2.0**.
3. Average event return **> 0 in both halves:** 2012–2018 and 2019–2026.
4. Still **> 0 after dropping the best 5% of events,** so it isn't a few lucky reports.
5. **Bar B on a sleeve:** $100,000, spending 2% of current equity on each event's straddle, idle cash at 0%. It must beat holding SPY over the same dates on max drawdown by **≥ 5 points** AND on CAGR ÷ max drawdown.

Reported for information only (not part of pass/fail): mid-to-mid returns; results by stock and by year; pre-market vs post-market.

## If it fails
It goes on the failed list. No re-running with 2, 4 or 5 days, other strikes, other stocks, or other exits.

## If it passes
A forward paper test in the Options paper account through one earnings season, with the same rules. Real money would be a separate decision by the owner.
