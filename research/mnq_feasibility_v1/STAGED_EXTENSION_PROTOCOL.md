# Fixed August extension and paper preparation

Authorized scope: the user approved up to $56 of additional historical research
and asked us to shorten the route toward a limited live trial requiring their
later approval. This does not authorize live orders or changed strategy rules.

Stage 1 requests trades for MNQU6 only, GLBX.MDP3 raw symbol, August 3–28,
2026, each of the 20 weekdays from 13:30 through 20:00 UTC (end exclusive),
plus definitions for August 3–29 exclusive. The refreshed stage estimate must
be positive and strictly below $22; all extension stages together must stay
below the approved $56 estimate ceiling. Provider billing is usage based;
an estimate guard is not a guaranteed billing cap. No portal limits are changed.
Submissions are journaled before the paid POST and are never blindly retried.

Dates, rules, and all four existing illustrative cost scenarios are fixed before
opening these new outcomes. August 3 supplies warmup and August 4–28 provides
19 new evaluation sessions. The already examined September pilot stays separate.
This is a feasibility screen, not an untouched final validation set.

Trade schema records are validated against the official DBN decoder, provider
counts, file hashes, exact contract definitions, instrument, publisher, tick
size, timestamps, order, flags, and full 390-minute trade coverage. Event-time
boundary exclusions are recorded separately. Individual trade price/size records
feed the unchanged weighted VWAP/population-SD engine. Minute OHLC/variance and
signal enumeration receive a separate calculation check. Source completeness
beyond the supplied records is not independently certified.

Stage 1 can report signal frequency and signal definitions. It cannot report
executable risk fit, fills, trading P&L or drawdowns without quotes. If signals
exist, request quotes for EVERY signal day, including subsequently losing or
ineligible signals. Refresh those costs, add actual prior stage usage when
available (otherwise fail closed), and stop if combined spending estimates
reach $56. MBP-1 is the executable-quote source; no trade-only prices are
substituted for quotes. Buying both schemas can duplicate trade data costs.

If there are no or very few signals, publish insufficient evidence and stop
automatic acquisition. Do not loosen the three-SD or prior-level conditions,
shrink stops, or increase risk after seeing this sample. Any alternative is a
separately declared version with separately reserved evaluation data.

Paper preparation proceeds independently. Only actual broker-paper evidence
can establish that a paper comparison was performed. Synthetic fixtures test
software, and no quantity of passing fixture tests authorizes live trading.

Sources: [Databento trades schema](https://databento.com/docs/schemas-and-data-formats/trades),
[batch requests](https://databento.com/docs/api-reference-historical/batch/batch-submit-job).
