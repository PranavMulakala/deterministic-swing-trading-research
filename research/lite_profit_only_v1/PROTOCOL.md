# LITE profit-only holding diagnostic v1 — September 27, 2026

This is an **offline development diagnostic**, not a selected strategy or a
paper/live order instruction. It uses previously examined 2026 prices. No
credentials, network requests, broker clients, or account changes are involved.

## Fixed assumptions for this diagnostic

- Input: pinned, raw, regular-session SIP five-minute LITE bars with hash and
  complete-session checks from `lite_funded_comparison_v1.inputs()`.
- Two pre-existing entry definitions are replayed separately: `dip_30` and
  `rebound_30`. Their signals use only the first six completed bars and attempt
  entry at the 10:00 bar open. Neither definition includes a volume or news
  filter. These are **stand-ins** for the owner's still-unspecified entry rule.
- One five-share position at a time. Initial research ledger: $10,000 cash,
  fully paid shares, no borrowing, no averaging down and no same-day re-entry
  after an exit. This ledger is hypothetical; it is not an account balance.
- Entry price proxy: 10:00 bar open plus 10 basis points. No entry is taken if
  the planned target cannot exceed modeled entry and exit costs.
- Profit target proxy: that entry day's 09:30 opening price. A simulated sell
  occurs at that target, less 10 basis points, on the first **later** bar whose
  high strictly exceeds the target. A touch alone and the entry bar never count.
  A high strictly through a level is evidence of a price crossing, **not proof**
  a live limit order would fill there.
- **No automatic loss cap, stop order, deadline, or forced sale.** An unsold
  position remains open through the dataset. Its ending value is marked using
  the last regular-session close less 10 basis points of modeled exit cost.
- Report candidate signals, occupied skips, entries, closed trades, unresolved
  holdings, marked P&L, worst daily ledger drawdown and worst intrabar position
  excursion. Do not count an unresolved position as a profitable trade.
- Run once across the complete saved 2026 sample and once across the last 90
  calendar days ending on the saved data cutoff. The shorter replay begins
  flat; it is not a continuation of the full replay and is not an untouched
  holdout. Both samples are already-known development data.

## Limits

The fixed 10-bp cost is a sensitivity proxy, not recorded executable bid/ask.
Historical news receipt times, volume qualification, corporate actions, queue
position, halts, partial fills, tax, and live order behavior are not tested.
The target is the session open for this diagnostic; the owner's final target
must be explicitly defined relative to an actual fill before a prospective
paper experiment. These results cannot establish a bounded maximum loss or a
repeatable trading edge.
