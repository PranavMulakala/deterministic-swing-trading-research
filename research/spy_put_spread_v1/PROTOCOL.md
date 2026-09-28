# SPY bull put spread paper bot v1 — frozen September 28, 2026

**Paper trading only**, in the dedicated "Options bot" Alpaca paper account (keys in `.env.options`). It never touches live trading, Robinhood, the LITE bot's or ETF bot's accounts, or Joey's material.

The owner approved these rules, the volatility filter, and a weekday 10:30 ET schedule on September 28, 2026. Sources: [proposal](../../output/OPTIONS_STRATEGY_PROPOSAL_20260928.md), [research](../../output/OPTIONS_RESEARCH_20260928.md).

## Each weekday run (10:30 ET)
1. **Safety checks.** Confirm:
   - the bound account ID, and that the account is ACTIVE
   - the broker clock is open and agrees with the Mac's clock within 60 s
   - no `KILL` file exists

   Reconcile broker positions and open orders against the bot's record. Anything the bot didn't create halts it.
2. **Manage an open spread:**
   - **Profit-take filled** (the resting GTC order): record the realized result.
   - **Break-even exit:** if SPY's last close is below (short strike − credit), close now.
   - **Time exit:** if 5 or fewer trading sessions remain through expiration, close now.
   - Otherwise, re-place the profit-take order if it is missing.
3. **Open a new spread** only on **Mondays between 10:25 and 11:30 ET**, and only when flat. The window, added Sept 28, enforces "about 10:30": a run macOS launches late, for example after the Mac wakes from sleep, cannot enter. Exits and management still run whenever the market is open. All of these must hold:
   - SPY's last close is above its 50-day average (adjusted daily closes, through the prior session).
   - At-the-money put implied volatility of the chosen expiration is **≥ 1.2 × SPY's 20-day realized volatility** (annualized, from 21 closes).
   - The expiration is 21–35 calendar days away; the one closest to 30 days is used.

## The spread
- **Legs:** sell the put whose delta is closest to −0.20, and buy the put exactly **$5 lower**, same expiration.
- **Minimum credit:** the mid-price credit must be at least **$0.75**. Otherwise skip the week.
- **Size:** contracts = floor(equity × 2% ÷ ((5 − credit) × 100)), capped at 5; skip if 0. Size never increases because of a loss.
- **Entry:** a DAY limit multi-leg order for a **credit** (Alpaca's convention: a negative `limit_price` is a credit).
  - First try at the mid credit, then $0.05 less. It never asks below $0.75.
  - If unfilled after the second try, cancel.
- **After a fill:** confirm the sold leg is short and the bought leg is long by the same count. Otherwise the bot halts.
- **Profit-take:** a resting GTC limit order to buy the spread back for 50% of the actual credit (a positive `limit_price` is a debit).
- **Exits** (break-even or time):
  1. Cancel the profit-take.
  2. Buy the spread back with a marketable limit of the full $5 width. At that price, fills happen at the market.
  3. Confirm the account is flat.
- **Never:** roll, average down, add size after a loss, sell calls, sell unprotected puts, or hold into expiration week's final 5 sessions.

## Plumbing test (`--plumbing-test`)
- Opens **one** contract of a spread chosen by the same selection rules, at a marketable credit. It checks the leg signs and that the credit actually arrived.
- It rests and then cancels a GTC profit-take, buys the spread back, and checks the account is flat.
- The test is excluded from strategy results.

## Records
- `outputs/spy_put_spread_bot/` holds `state.json`, `events.jsonl` and `KILL`.
- One summary email per run goes to pranavm1104@gmail.com via the existing Resend route.

## Limits
- Decisions use Alpaca's free **indicative** option quotes and greeks, which are approximate.
- Paper fills are optimistic: NBBO, random partial fills, no slippage.
- Early assignment is detected, not simulated. Daily closes, not intraday prices, drive the break-even exit, so a fast crash can reach the full $5 width before the next daily check.
- A paper result is not live evidence.
