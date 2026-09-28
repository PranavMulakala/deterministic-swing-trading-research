# Frozen prospective ORB direct-breakout challenger v1

Frozen before the September 16, 2026 regular session. This is a separately
versioned, paper-only research challenger. It does not amend, replace, or tune the
retest experiment after seeing its zero-trade forward result.

## One deliberate change

Reuse the exact five symbols, lagged eligibility, opening range, A/B candidate
selection, RVOL threshold, stop, 2R target, portfolio limits, quote validation,
signal delays, slippage, fees, settlement, and exit model from
`orb_comparison_v1` plus `orb_quote_v2`.

Change only entry confirmation: beginning with the 09:35 five-minute bar, the
first completed five-minute close strictly above the 09:30 opening-range high is
the signal. The decision time is that bar's end. There is no retest requirement
and no second breakout attempt. Confirmation must be known by 11:00 ET.

The quote/trade engine makes its single IOC-style paper attempt one or two
seconds after that decision, under the unchanged quote-age, spread, geometry,
cost, capacity, sizing, stop, target, time-exit, and unresolved-position rules.

## Prospective boundary and reporting

September 8-15 data were already observed and are excluded from this challenger's
scored results. The first eligible date is September 16. Report A and B at both
declared delays and both declared cost assumptions. Report every symbol-session,
including no breakout, RVOL rejection, quote rejection, zero quantity, fill, and
unresolved exit. Never pool capital or trades with the retest experiment.

No threshold is optimized here. In particular, RVOL remains 2 in Arm B. A lower
RVOL threshold would be a different, later preregistered sensitivity—not a repair
to this challenger.

Review requires at least 20 complete prospective sessions and at least 20 closed
trades in the arm being assessed. Meeting those counts permits analysis only; it
does not prove profitability, authorize broker orders, or enable promotion.

