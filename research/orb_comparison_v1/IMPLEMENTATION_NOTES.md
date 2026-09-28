# Implementation decisions, recorded before the first P&L run

September 7, 2026. Supplements but does not replace the frozen protocol.

- The supplementary corporate-action query returned a terminal empty action set
  for all five stocks over October 1, 2025–September 7, 2026. Current provider asset
  names/classes/exchanges match the requested companies. This is single-provider
  retrospective reconciliation, not independent point-in-time membership or proof
  that the provider could never omit an event. No action adjustment is inferred
  from a large price move. Future non-cash events with ambiguous effective-date
  or symbol fields fail closed for manual reconciliation.
- Cash calculations use Python Decimal from decimal representations of provider
  numbers, without rounding each internal entry to cents. Display values round
  only for readability. Integer shares are floored after costs/risk constraints.
- Entry fees are included in entry basis; realized daily P&L is net P&L of closed
  trades including both fees. Entry fees on an open position affect equity but
  are not double-counted as realized closed-trade losses.
- At a missing minute **while a position is held**, the primary portfolio stops.
  Its remaining cash is recorded, but terminal equity/return are null, the open
  position remains present, and later symbol-days are explicitly unevaluated.
  Restarting with a fictional cash balance or skipping the trade would violate
  the frozen rule. Missing entry minutes are rejected before any position exists.
- An unknown five-minute pattern interval is an unknown pattern, never a known
  failure to break out. It prevents favorable acceptance even if the cash ledger
  otherwise finishes. Future full-day completeness is not an eligibility input.
- The strict matched-complete-day diagnostic requires both one- and five-minute
  regular-session data on the same date for all five names. Excluded dates earn
  zero in that separate diagnostic; original prior-session indicators still use
  the full calendar. This diagnostic deliberately conditions on future coverage
  and is selection-biased, not a repaired primary result or replacement strategy.
- Leave-one-stock-out tests rerun BOTH arms with that name absent, keeping rules,
  cash and all thresholds identical. Report every omission, not the best subset.
- Drawdown is sampled at completed-minute marks after modeled trades. Cash
  occupancy is the time average of deployed marked dollars / starting capital;
  position-minutes are also reported. These are not tick-level worst drawdowns.
- The bootstrap uses paired mean daily return differences, overlapping eligible
  five-session blocks, percentile interpolation, and the frozen seed/count. If
  either primary ledger is unresolved, the full-period contrast and interval are
  unavailable. Do not bootstrap only convenient completed trades as substitutes.
- Quote execution checks remain a separate gate. Bar-proxy results cannot pass
  that gate by assuming an unknown spread is zero. News is not a v1 filter.

The frozen protocol and thresholds remain byte-identical. Software correctness,
statistical evidence, and broker execution readiness are separate conclusions.
