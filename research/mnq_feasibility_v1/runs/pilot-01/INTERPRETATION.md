# What the first observed-data pilot answers

The four evaluated sessions generated **zero complete patterns**, independently
confirmed by a separate enumeration of the audited bars. Within the permitted
setup times, no setup-minute close was strictly beyond its cumulative VWAP plus
or minus three volume-weighted standard deviations. No later entry conditions
could therefore complete the pattern.

1. **What percentage of signals fit $12.50? Unknown.** The denominator is zero.
   This sample does not show that every setup fails the budget or that the budget
   fits the setup. No actual entry-to-stop distances were observed.
2. **What happens after fees, spreads, and slippage? Not observed on real entries.**
   All four frozen cost scenarios produced zero entries. Their zero trading P&L
   is a no-trade outcome, not evidence of profitability. Fees remain illustrative.
3. **What losses and drawdowns occur under the pauses? Not meaningfully exercised
   by this market sample.** The simulator stayed in cash. Pause behavior passed
   synthetic execution tests; this does not validate live broker behavior.

The useful progress is a checked acquisition, importer, minute-bar calculation,
and reproducible application of unchanged rules. The next experiment should
extend history under the same definitions, with dates fixed before opening their
outcomes. It should retain this four-day result rather than quietly replacing it.

Validation included 35 tests (29 existing and six added adapter/equivalence tests),
88 reference-vs-prepared economic comparisons across cost/direction/randomized
fixtures, and rerunning the original execution tests with the prepared backend.
All 1,950 minute bars matched independent OHLC/VWAP/variance calculations; maximum
VWAP and standard-deviation differences were below 0.000000005 ticks. Frozen
source/config/protocol hashes matched the saved pre-import values.

The 26 capture/event-boundary records and limits in `IMPORT_PROTOCOL.md` still
apply. No extra historical data was purchased by the importer or replay, and no
broker orders were placed.
