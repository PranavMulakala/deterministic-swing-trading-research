# Options track: proposed first paper strategy — "SPY bull put spread v1"

**Status: RULES APPROVED by the owner on Sept 28, 2026, including the volatility filter.** Still pending: the owner creates the third "Options bot" paper account, and gives explicit approval of the weekday schedule. No bot has been built or scheduled yet. Paper trading only, in a separate, new Alpaca paper account. This track is independent of the LITE bot and of the owner's real positions. Joey's material is used as study input only; none of his code or keys are used.

## Sources this combines
- **OptionsAnimal course** (47 decks in Joey's Drive), via private notes at `reference/joey_2026-09-26/drive_options_notes_20260928.md`:
  - bull put rules (3.3, 7.5)
  - chain liquidity test (6.5)
  - 2% risk sizing (3.3, 6.1)
  - close spreads before expiration (3.4, 3.5)
  - about 50% of max profit as the benchmark exit (8.4)
  - no earnings or scheduled news inside the trade (3.3)
  - index ETFs preferred over single stocks (8.4)
- **Research brief:** [OPTIONS_RESEARCH_20260928.md](OPTIONS_RESEARCH_20260928.md).
  - Common rules: 0.20–0.30 delta, 30–45 DTE, 50% profit, early time exit.
  - A published SPX put-spread backtest won 92.5% of trades yet had a −39.5% drawdown.
  - The Cboe PUT index returned 7.1%/yr against 11.0% for the S&P 500.
  - Retail losses concentrate in *buying* short-dated options.
- **Joey's code:**
  - a liquidity screen
  - an IV ranking
  - review at 3 or fewer DTE
  - in-the-money alerts
  - an earnings check
- **Measured today:** SPY's near-the-money bid/ask gap was 0.6% of the option price. LITE's was 14.2%, which fails the course's 10% cutoff.

## Proposed rules

| Item | Rule | Why |
|---|---|---|
| Underlying | **SPY only** (QQQ/IWM later) | The deepest, cheapest options market, with no earnings. Passes the course's liquidity test easily. |
| Outlook filter | Open only when SPY closes **above its 50-day average** | A bull put needs a bullish-to-flat outlook (course). This is simpler than the course's three-indicator signal, which can be an option. |
| When to open | At most once a week, Monday about 10:30 ET, **only if no spread is open** | One position at a time while learning. |
| Volatility filter (owner approved Sept 28) | Open only if SPY's at-the-money implied volatility (about 30–35 DTE) is **at least 1.2 × its 20-day realized volatility**. Log the ratio every Monday, including skipped weeks. | See the note below the table. |
| Expiration | **21–35 days** out | The course sells short options under ~30 DTE; common practice is 30–45. |
| Short put | About **0.20 delta** (roughly an 80% chance to expire worthless by pricing math) | Course condor recipe and common practice. |
| Long put (protection) | **$5 below** the short put | Caps the loss. SPY strikes are $1 apart. |
| Minimum credit | At least **$0.75 per $5 of width** (15%); otherwise skip the week | The course warns against a small credit for a big risk. |
| Size | Contracts = floor(account × **2%** ÷ max loss per contract), **capped at 5** | The course's sizing formula. |
| Take profit | A resting GTC order to buy the spread back at **50% of the credit** | The course benchmark; the most common rule. |
| Loss exit | Close if SPY closes **below the short strike minus the credit** (the course's "theoretical breakeven") | Written down before entry, per the course. The loss is also capped by the spread's width regardless. |
| Time exit | Close any open spread at **5 trading days or fewer** before expiry | The course says close before expiration day; Joey reviews at 3 or fewer DTE. Avoids assignment and pin risk. |
| Never | Add size after a loss, roll a losing spread for more risk, or hold into expiration day | The blow-ups in the research came from exactly this. |
| Data | Alpaca's free options feed (approximate) for decisions. Every paper fill is logged against the quoted mid. | Enough for paper mechanics. Real OPRA ($99/mo) or ThetaData ($40+/mo) only if the paper test shows it matters. |
| Reporting | Emails for the entry, profit-take, exits and a daily open-position summary (the existing Resend route) | Same as the LITE bot. |

**Why the volatility filter** (owner-supplied source, read Sept 28): FlashAlpha's "options strategies ranked" light backtest, https://flashalpha.com/articles/options-strategies-ranked-light-backtest-spy-qqq-iwm.
- **Setup:** SPY/QQQ/IWM, 2020–2025, monthly entries with a fixed 10-session exit, a 25/10-delta put spread, and costs modeled as bid/ask plus $0.65 per contract.
- **Results:**
  - Plain spread: 206 trades, **−0.01% per trade**, worst trade −7.05%.
  - Filtered spread: 73 trades, **+0.17% per trade**, Sharpe 1.18, worst trade −2.24%.
  - Returns are measured as a % of 100 shares' value.
- **Caveats:** a vendor study promoting its data; designed in 2026 with **no untouched holdout**; a small filtered sample; a strong bull-market period; and no early assignment, margin, collateral yield or taxes modeled.
- **Our rules differ** (narrower $5 spread, 50% profit-take, breakeven and 5-DTE exits), so the study motivates the filter but does not predict our results.
- **Snapshot:** on Sept 28, SPY 20-day realized volatility (through Sept 25) was 10.8%, and near-the-money implied volatility on the free feed was about 14%. The ratio of about 1.3 would pass.

## Example at today's prices (illustrative, not a quote)
SPY is about $765 and IV about 14%.
- A 30-day, 0.20-delta short put sits near **$739**, with the long put at **$734**.
- A typical credit is roughly **$0.80–$1.20**, so max loss is about **$380–$420 per contract**.
- On a $100,000 paper account, 2% risk ($2,000) allows **4 contracts**, for about $1,600 of max loss.
- A 50% profit-take on that position would be about **+$200**.

## What this test can and cannot show
- **It can check:** order handling for two-leg spreads, fills against quoted prices, profit-take behavior, exits, and assignment handling.
- **It cannot prove an edge.** Published backtests of similar rules show high win rates, occasional maximum losses, and long-run returns below simply holding the index.
- **It cannot show real-money fills.** Paper fills are optimistic.

## What the owner needs to decide or do
1. Approve these rules, or change any of them.
2. Create a **third** Alpaca paper account ("Options bot"), save its keys in `.env.options`, then run a one-time bind, the same as the LITE bot.
3. Approve a weekday schedule: open Mondays about 10:30 ET; check open spreads daily about 10:30 ET. Mac for now, the cloud once it is reachable.
