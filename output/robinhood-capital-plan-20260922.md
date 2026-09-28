# Robinhood capital and swing-trade plan

Prepared September 22, 2026. Status: WRITTEN PLAN ONLY — Robinhood read-only account discovery succeeded later September 22; this plan is not broker-enforced, and no orders, alerts or trading schedule were activated by this task. See [current handoff](PROJECT_HANDOFF_20260922.md).

## Starting facts

- User reports $82,000 cash after selling all LITE shares. Balance, settlement, account type, existing orders, and tax obligations have not been independently verified.
- User's stated acceptable loss is $4,000, and automatic stop-loss orders are not wanted.
- This is separate from the IBKR MNQ paper experiment and all existing frozen research strategies. None of their rules are changed.

## Capital limits

1. Designate at least $78,000 as cash reserve, outside the stock experiment. This is a bookkeeping designation until actual account balances and permissions are verified; no transfer has been made.
2. Allocate at most $4,000 once to the entire stock experiment, including trading costs. No replenishing losses from the reserve. This is a total experimental allocation, not a fresh $4,000 allowance per trade or per month.
3. Recommended starting position limit: $1,000 including entry costs; at most four positions. Outstanding buy orders count toward the allocation and position limits. There is no requirement to invest the full allowance.
4. Fully paid, unleveraged common shares only. No margin borrowing, short selling, options, futures, leveraged products, automatic averaging down, or autonomous orders under this plan.
5. Track the experimental cash and positions separately. Trading costs come from this allocation. Profits do not increase the $4,000 allocation ceiling. If it is exhausted, trading stops; do not fund a replacement experiment without a new decision.
6. The stock allocation can lose its entire value. This bounds the original capital committed to the experiment only if the separation and no-borrowing/no-replenishment rules are followed. It is not a guarantee of total account value: cash custody risks, taxes, withdrawals, and unrelated charges are separate.

## Entry and exit rules — recommended starting defaults

These are proposed discipline rules, not a backtested profitable strategy or a confirmed user agreement to manual loss exits. The ten-session deadline below is a proposal, not the frozen research swing engine's 21/42/126-session policy. Do not retrofit it onto past prices and call that validation.

Before each purchase, fill in the trade card below. No completed card means no entry.

- Entry must be supported by a specific, dated thesis and an observable entry condition, not merely a price decline or social-media enthusiasm.
- Specify a concrete condition that would disprove the thesis. If it occurs, the plan calls for a manual exit at the next practical liquid opportunity, even at a loss. No automatic stop order is placed.
- Set the default maximum holding period to ten regular trading sessions, counting the entry session as session one. The tenth session is the planned manual exit date, whether the position has gained or lost. A holiday is not a trading session.
- Review at each regular-session close and promptly after material company news. These reviews are a manual responsibility; no notification or monitoring service is active.
- Record the price and date for the intended profit exit before entry. There is no universal profit target across stocks. Exit when the documented target or thesis condition is met; do not keep moving the target to avoid a decision.
- Do not extend a losing swing trade indefinitely just to avoid realizing its loss. A longer-term investment requires a separate documented evaluation and must still fit the same capital allocation.
- A manual exit can be delayed by gaps, halts, unavailable liquidity, or inability to access the account. No trigger guarantees its intended exit price.

## Trade card — complete before any order

| Field | Required value |
|---|---|
| Symbol | Not selected |
| Fresh bid/ask, timestamp, and source | Not verified |
| Dated business/catalyst thesis | Not specified |
| Entry condition and maximum purchase price | Not specified |
| Quantity and maximum debit including costs | Must be at most $1,000 and fit remaining experimental cash |
| Thesis invalidation condition | Not specified |
| Profit target and supporting reason | Not specified |
| Earnings date / material scheduled events | Not verified |
| Entry session and tenth-session exit date | Not set; no trade has been entered |
| Existing positions and pending orders checked | Not verified |
| Actual execution and costs | None recorded; not an assertion about the broker account |

Watchlist for evaluation: LITE, COHR, CIEN, FN, AAOI. These names share industry exposure; the list is not broad diversification and does not authorize buying them.

## Robinhood setup still required

- Verify actual settled cash, pending orders, existing positions, and any margin debit using the authenticated account. The Robinhood MCP became callable later September 22. Read-only discovery verified an active Agentic account ending 8616, type limited_margin, agentic_allowed=true; the default account was not agentic-enabled. This does not establish current balances, borrowing permission or authorization to trade.
- Verify cash-program enrollment and actual account APY. Robinhood's official High-Yield Cash page currently lists 3.6% variable APY for eligible cash with Gold and enrollment. Enrollment and subscription have not been changed.
- In Robinhood: Account → Menu → Investing → High-Yield Cash Program. Review eligibility, fees, and account-specific terms before enrolling. Cash held at the brokerage and cash swept to banks have different protections; do not treat all cash as an FDIC-insured bank deposit.
- Account segregation, position caps, and manual review rules in this document are not enforced by Robinhood. No automated sells, buys, stop orders, subscriptions, or transfers were set up.
- Assess any liability from the completed LITE sale before treating all reported cash as deployable.

Source checked September 22, 2026: https://robinhood.com/us/en/support/articles/high-yield-cash-program/

Immediate state: keep funds uncommitted while the account checks and first trade card are incomplete. This document establishes allocation and exit discipline; it does not establish a profitable entry or authorize an agent to execute trades.
