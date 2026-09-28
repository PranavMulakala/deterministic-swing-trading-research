# LITE paper dip bot v1 — frozen September 28, 2026

**Paper trading only.** This bot places orders in a dedicated Alpaca **paper** account ("LITE bot"). It never uses live trading, Robinhood, the ETF bot's paper account, or Joey's material. The owner approved its rules and the weekday 10:00 schedule on September 28, 2026: the dip rule, 7 shares, a +2% target over the actual fill, no automatic stop, no time limit, no averaging down. That evening the owner raised the size to 66 shares (see Changes).

## The rule (checked once per weekday)

At **10:00:30 ET**, look at LITE's six completed **IEX** five-minute bars, 09:30 through 09:55:

1. **Dip:** the lowest price in those bars is at least 1% below the 09:30 bar's open.
2. **Still down:** the 09:55 bar closes below that open.

If both hold and the bot holds no LITE, it buys. This is the `dip_30` definition from `research/lite_funded_comparison_v1/run.py`, applied to the free IEX feed. For learning only, each day also records whether the stricter conditions held (the last three closes rising; morning volume ≥1.5× the prior 20 IEX mornings). Those two never change the decision.

## Orders

- **Buy:** 66 whole shares (about $60,000 at late-September 2026 prices); a DAY **limit** order at the reference price +0.1%, rounded to the cent. The reference is the fresh IEX ask (≤30 s old), or else the latest IEX trade (≤60 s old). It must be within 2% of the 09:55 close, or the day is skipped. The buy must be submitted by 10:04:00 ET. Anything unfilled is cancelled at 10:05:00 ET.
- **Sell:** as soon as shares fill, a GTC **limit** sell for exactly the filled shares at **the average fill × 1.02, rounded up to the cent**. It never sells below that price, and it never uses market or stop orders.
- **One position at a time.** No new buy while holding. There is no same-day re-entry and no averaging down.
- **Cash only:** the account's cash must cover 66 × limit × 1.01, and each buy is capped at $72,000, so no buy happens above about $1,090 a share. Borrowing power is ignored.

## Every run also

- Checks the bound account ID, that the market is open, and that the broker clock agrees with the Mac's within 60 s.
- Re-places the target sell if it is missing (Alpaca cancels GTC orders after 90 days, and corporate actions can cancel them).
- Records a completed sale with its realized profit.
- **Halts** by writing `outputs/lite_paper_bot/KILL` with the reason, and places no further orders, on anything unexpected: the wrong account, a position or order the bot didn't create, a share count that doesn't match, or a position that vanished without its sell filling. The owner deletes `KILL` after reviewing.
- Emails one summary per run to pranavm1104@gmail.com: signal or no signal, orders, fills, the holding's marked profit/loss and cash tied up, and any halt. A missing weekday email means something is wrong.
- If it starts after 10:04 ET (for example, the Mac was asleep), it skips the buy for that day but still checks and reports.
- After every order step, it records a **learning-only news reading**. The source is Alpha Vantage's relevance-weighted LITE sentiment and top headlines for articles published from the previous weekday's 16:00 ET to 10:00 ET. It is written to `outputs/lite_paper_bot/news.jsonl` and shown in the email. It never changes a decision. It needs the owner's key in the owner-only `.env.news`; without one, the email says so.

## First run

`--bind` locks the bot to the new paper account after read-only checks: the account is ACTIVE and not blocked, has no positions and no open orders, and holds at least the per-buy cap in cash. The account was bound on September 28 under the original $8,000 cap and holds $100,000 in paper cash. Until it is bound, scheduled runs place no orders.

## Changes

- **September 28, 2026, evening, by the owner:** size raised from 7 to 66 shares and the per-buy cap from $8,000 to $72,000, matching the owner's $50,000–$70,000 budget for this paper test. The rule, the +2% target, no stop and the 10:00 schedule are unchanged. It applies from the 10:00 ET run on September 29; the bot had placed no orders before the change. At this size, each +2% sale makes about $1,200, a 10% drop while holding is a paper loss of about $6,000, and the 2026 replay's worst hold (entered June 16, down 36% at its low) would have been about −$21,900 before it recovered.

- **September 28, 2026, evening, by the owner:** "add the news sentiment to the daily email". The reading is learning only and does not change the rule. Only LITE-specific news is scored: Alpha Vantage's general economy feed was checked, and it was mostly unrelated company stories.

## What this cannot show

Alpaca paper fills are optimistic: instant fills at the best price, random partial fills, no queue position or slippage. The free IEX feed is about 2% of volume. A paper profit is not live-money evidence, and nothing here bounds the loss on an unsold position. Signals and fills from this bot are prospective records. They count as evidence only alongside their unresolved holdings and marked losses.
