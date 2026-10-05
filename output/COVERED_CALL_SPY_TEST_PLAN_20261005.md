# Does selling covered calls on SPY beat simply holding SPY? Pre-declared test #13 (October 5, 2026)

Written and committed **before** any result was computed. Research only; no orders. Nothing changes in the bots, Plan B or MNQ.

**Owner's request:** "test the covered call strategy on SPY but remember dont take into account days like covid and stuff becuase thats external".
- Covered calls topped the r/options 42-strategy ranking (`REDDIT_OPTIONS_STRATEGY_RANKING_20261005.md`).
- **Shock periods:** the verdict uses the full history, because crashes recur and any strategy held for years will live through them. Versions with the shocks removed are reported alongside **as information**, with the same windows removed from SPY so the comparison stays fair.

## Data (on disk; no download)
- **SPY options:** Databento OPRA chain at 10:30 ET and the close, every trading day (`outputs/spy_options_data/`), with SPY's price from put-call parity, as in test #10.
- **Dividends:** credited as cash on each ex-dividend day. Computed as shares × previous raw close × (adjusted daily return − raw daily return), using the dividend-adjusted SPY closes (`outputs/breakout_data/SPY.csv.gz`) and Alpaca raw SPY daily closes.
- **Cash:** earns the monthly 3-month T-bill rate (same file as test #10).
- **Window:** Jan 4, 2016 – Dec 31, 2025 (same as tests #10 and the 65/35 check). Halves: 2016–2020 and 2021–2025.

## The rules (main candidate)
1. **Start:** $100,000. At the first 10:30 snapshot, buy as many 100-share lots of SPY as the cash allows. The rest stays in cash.
2. **Each cycle:** on the first trading day of the window, and on the first trading day after each call expires, at 10:30:
   - Sell **one call per 100 shares**.
   - **Expiration:** the one with 21–45 days left closest to 30.
   - **Strike:** above SPY's price, with delta closest to **0.30** (about 2–3% above the price).
   - **Sold at the bid.** $0.03 fee per contract.
3. **Hold to expiration.** No rolling and no early closing.
4. **At expiration** (SPY's close that day):
   - **At or below the strike:** the call expires worthless and the premium is kept.
   - **Above the strike:** the shares are called away at the strike (cash received = strike × shares). At the next trading day's 10:30 snapshot, buy back as many 100-share lots as cash allows, at that price + 0.01% slippage. Then sell the next call the same morning.
5. **Daily value:** shares × SPY close + cash − open calls × closing midpoint.

## Information-only variants (don't count)
- Same rules **filled at the midpoint**.
- **Delta 0.20** calls (further out).
- **At-the-money** (delta 0.50, like the Cboe BXM buy-write index).
- **Shock-removed views:** daily returns of **both** the strategy and SPY set to zero during these windows, as if the money sat out:
  - **"COVID removed":** Feb 20 – Apr 30, 2020.
  - **"All big shocks removed":** COVID, plus:
    - Feb 1–28, 2018 (volatility blow-up);
    - Jul 31 – Aug 15, 2024 (yen carry unwind);
    - Apr 2–30, 2025 (tariff crash).

## It counts as working only if all hold (full history, main candidate)
**Bar A:**
1. Profit factor across monthly cycles (total cycle P&L: stock + option + dividends + interest) of at least **1.3**.
2. Profitable in **both halves**.
3. Worst peak-to-trough drop of at most **25%**.

**Bar B (vs holding SPY with dividends):**
4. Max drawdown at least **5 points smaller** than SPY's.
5. CAGR ÷ |max drawdown| **higher** than SPY's.

**Nothing will be tuned afterwards.**

## Also reported
- Share of calls that expired worthless vs got called away.
- Premium collected vs the upside given up.
- Returns by year; best/worst cycle.
- **The same metrics in the shock-removed views, for both the strategy and SPY.**
- Provenance manifest.

## Checks
- Unit tests on a hand-built chain: strike choice, lot sizing, call-away and buy-back, dividend credit.
- An independent re-computation of the cash path from the trade list.
