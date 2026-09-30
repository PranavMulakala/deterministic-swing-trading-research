> **Parked by the owner on Sept 29 before any download** ("let's not do options for Lumentum... we'll look at it later"). Free cost estimate: about $3.95 for 1,188 days. The rules above stay locked for when it resumes.

# Would buying LITE calls on dip days beat buying the stock? Pre-declared test (September 29, 2026)

Written and committed **before** any historical LITE options data was downloaded or viewed. The owner asked whether LITE options could make more from the same dips ("set up the test please 100%"). Research only: no orders of any kind.

## Signals
- **Rule:** the LITE paper bot's own dip rule on SIP five-minute bars. LITE must dip at least 1% below the 09:30 open during the first 30 minutes, and the 09:55 close must still be below the open.
- **Source:** the same days as `research/lite_dip_history_v1/run.py` with `--signal-feed sip`.
- **One call at a time:** signals are skipped while a call is held.

## The trade
- **Entry at 10:05 ET** on the signal day, from the 10:05 one-minute quotes. Buy **one** call contract:
  - **Expiration:** the one closest to 30 calendar days, among those 21–45 days out.
  - **Strike:** the one closest to LITE's price at 10:05.
  - **Skip** if there is no two-sided quote.
- **Exit, checked at each day's 15:59 quotes, including the entry day:**
  1. **Target:** sell once LITE's close is at least 2% above its 10:05 price. This is the same +2% the stock bot uses, measured at the close.
  2. **Time exit:** otherwise, sell at the close on the last trading day with 5 or fewer trading days left before expiration.
- **Fills:**
  - **Natural:** buy at the ask, sell at the bid.
  - **Mid:** both at the midpoint.
  - Fees are $0.65 per contract per side. A call that can't be sold (no bid) counts as worth $0.

## Periods
- **Main:** trades entered from 2025-01-01 to 2026-09-28.
- **Stress:** trades entered from 2022-01-01 to 2024-12-31.

## It counts as working only if both hold, under natural fills, in both periods
1. Total profit is above $0.
2. The average return on the premium paid is at least +10% per trade.

Otherwise the conclusion is that buying calls on dips did not show an edge. Nothing will be tuned afterwards: no other strikes, expirations, targets or exits.

## Also reported (no decision)
- Win rate, average win and loss, and the worst trade.
- How many trades lost 90% or more of the premium.
- Premium paid per trade and the bid/ask cost.
- The stock bot's result on the same signal days, for context.

## Known limits, stated in advance
- **Two quote snapshots a day** (10:05 and 15:59), so intraday highs are missed, and the target is checked only at the close.
- **Quotes are not fills.** Real fills can be worse, especially on wide LITE option spreads.
- **The period is short:** the options data covers 2022–2026 only.
- **Hindsight:** LITE was picked because it rose, which flatters any bullish strategy.
