# Does selling cash-secured puts on SPY beat simply holding SPY? Pre-declared test #10 (October 5, 2026)

Written and committed **before** any result was computed. Research only: no orders of any kind. Nothing changes in the running bots, Plan B or the MNQ paper test.

The owner asked, after seeing that high win rates didn't make money in earlier tests: "yes run the cash secured put test after 10". The source ideas are TikTok "option selling basics" (Sept 29 video 3 / batch 2 #8) and the owner's question about whether people really make money selling options.

**Why this one has a real chance:** selling options has **independent evidence** of a small edge. Options are usually priced for bigger moves than happen (the "variance risk premium"), and the Cboe PutWrite index is the long-running record. Our earlier SPY **put spread** holdout failed (85% winners, −$1,809). That was a different structure: small credits, a bought put that costs money, and short holds. A fully cash-secured, unhedged monthly put is the plain version of the idea.

## Data (already on disk; no new download, no cost)
- **SPY options:** Databento OPRA best bid/ask for the whole SPY chain at 10:30 ET and at the close, every trading day (`outputs/spy_options_data/`, from the Sept 28 spread test).
- **SPY's price in each snapshot** comes from put-call parity, using the same helper as the spread backtest.
- **Benchmark:** SPY daily closes adjusted for dividends (`outputs/breakout_data/SPY.csv.gz`), so "holding SPY" includes reinvested dividends.
- **Cash interest:** the monthly 3-month T-bill rate already used in the spread test (`research/spy_put_spread_backtest_v1/tbill_3m_monthly.csv`).
- **Test window:** Jan 4, 2016 – Dec 31, 2025, the window where both the option data and the dividend-adjusted SPY series exist. Halves: 2016–2020 and 2021–2025.

## The rules (main candidate)
1. **Start:** a $100,000 cash account.
2. **Entry:** on the first trading day of the window, and again on the first trading day after each put expires, at 10:30 ET:
   - **Expiration:** the one with 21–45 days left that's closest to 30 days.
   - **Strike:** the put below SPY's price whose delta is closest to **−0.30**. Delta is computed from the option's own implied volatility, the same way as the spread backtest. In plain terms, a strike about 3–5% below the price that has roughly a 70% chance of expiring worthless.
   - **Sell at the bid** (the price you'd realistically get).
   - **Contracts:** as many as the cash fully secures, floor(cash ÷ (strike × 100)). **No margin, ever.**
3. **Hold to expiration.** No early closing and no rolling.
4. **At expiration**, using SPY's closing price that day:
   - **If SPY is at or above the strike,** the put expires worthless and the premium is kept.
   - **If SPY is below the strike,** the loss is (strike − SPY close) × 100 per contract. This is the same as being assigned the shares and selling them at that close. The cash then goes back into the next put. (This "cash-settled" version is how the Cboe PutWrite index works.)
5. **Cash earns the T-bill rate** every calendar day, including the cash securing the put.
6. **Fees:** $0.03 per contract when selling. Assignment is treated as free (Robinhood charges no assignment fee).
7. **Daily account value:** cash minus the cost to buy the put back at that day's closing midpoint. The worst drop is measured on this.

## It counts as working only if all of these hold
**Bar A (same as earlier tests):**
1. Profit factor across all puts (premium kept vs losses paid) of at least **1.3**.
2. Profitable in both halves (2016–2020 and 2021–2025).
3. Worst peak-to-trough drop of at most **25%**.

**Bar B (vs holding SPY with dividends over the same dates):**
4. Max drawdown at least **5 points smaller** than SPY's.
5. CAGR ÷ |max drawdown| **higher** than SPY's.

If any fail, the conclusion is that it did not beat simply holding SPY. **Nothing will be tuned afterwards.**

## Information only (does not count toward the verdict)
- The same rules filled at the **midpoint** (an optimistic bound).
- **At-the-money puts** (delta closest to −0.50), the Cboe PutWrite style.
- **Delta −0.20** puts (further out, smaller premium).

## Also reported
- Win rate (puts expiring worthless) and average premium kept vs average loss.
- The worst single month, and returns by year.
- Total return and CAGR vs SPY with dividends.
- How much of the profit came from T-bill interest vs from premiums.
- A provenance manifest (code and data hashes).

## Checks before trusting the result
- Offline unit tests on a hand-built option chain: strike choice, contract count, premium kept, assignment loss, interest.
- An independent re-computation of every trade's P&L from the raw files, which must match.

## Known limits
- **No early assignment.** SPY puts can be assigned early; that's rare and roughly equivalent to the cash-settled loss.
- **Exit at the expiration-day close.** It ignores after-hours moves before the official settlement.
- **Taxes are ignored.** Short-term option gains are taxed as ordinary income, which hurts this vs holding SPY.
- **One account, one symbol, one period** that was mostly a strong bull market (good for put sellers, but even better for SPY holders).
