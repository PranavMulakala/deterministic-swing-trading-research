# Databento pilot adapter, declared before opening strategy outcomes

The existing `config.json`, `PROTOCOL.md`, and reference `engine.py` remain
unchanged. This adapter specifies data interpretation and scalable storage.
Acquisition diagnostics have already been inspected; these dates are a pipeline
pilot, never untouched validation data. No further purchases or broker orders.

## Input and clocks

Use only the six approved jobs and verify every source hash against the acquisition
list. Check the previously decoded outright MNQU6 definitions. Use the fixed full
cash-session windows August 31–September 4, 2026, 09:30–16:00 New York, with August
31 as warmup and each following date linked to the preceding session. CME's 2026
Globex holiday schedule lists Labor Day changes September 6–8, outside this pilot.
These are cash-session research windows, not the full overnight futures session.

Keep original DBN row ordinal, publisher sequence, event time, capture time, and
flags. Never sort or deduplicate same-timestamp records. A derived event identity
is `2 * source_row` for a trade and `2 * source_row + 1` for a quote, preserving
source order if both arise from one record. Zero-based source rows reset per file.

The reference replay explicitly uses exchange event time plus hypothetical entry
and exit delays. Capture time is retained for diagnostics; this is not a simulation
of our own computer's receipt time. Filter to the event-time session window and
count every excluded boundary record. Source files are left unchanged.

## Trades and quotes

- A trade is an `action=T` MBP-1 record with positive size and valid tick price.
  Count it once; book cancels after the trade are not additional trades.
- Evaluate quotes only at records carrying `F_LAST`, the last record for that
  instrument in an exchange event. Earlier records may describe an intermediate
  book. Retain every such quote, including unchanged prices and repeated times:
  these matter to the first-available-quote and latency rules.
- Snapshot, bad-book, bad-capture-time flags, unsupported actions, non-MNQU6
  instruments, off-tick prices, or unordered timestamps fail this pilot import.
  This is deliberately a narrow importer; it does not silently clean a different
  feed. Invalid or empty quote prices/sizes otherwise remain explicit.
- Fixed-point prices divide exactly by 250,000,000 to produce 0.25-point ticks.
  Original sequence and row ordinals remain separate; the exchange's sequence
  number alone is not a unique trade identity.

## Scalability and checks

Store compact trade and quote arrays on disk, with a manifest and checksums.
Use the original weighted-Welford bar calculation and signal function, and check
all minute bars against a separate aggregate calculation before viewing outcomes.
Use the original `screen` function for risk and reward calculations.

The prepared replay may skip flat periods between scheduled decisions because
cash, equity, and pause state cannot change while no position is held. It must
remember the latest valid quote before the next entry and evaluate every quote
while exposed. Record marks while exposed and at decisions/session boundaries;
omitted flat marks all have the same cash equity. Compare economic results and
every decision/trade/pause against the unchanged reference engine on independent
fixtures, including long/short exits, gaps, and consecutive sessions.

## Limits retained

Capture-time requests can omit exchange events arriving just after a boundary;
minute coverage does not prove full exchange completeness. Report results as
observed-data diagnostics pending that audit and verified broker costs. Fixed
history expense is separate from the simulated trading ledger. Do not optimize
the setup or loosen the $12.50 initial planned-risk budget after seeing this pilot.

Sources checked for this adapter:
[Databento event completion](https://databento.com/docs/examples/order-book/order-tracking),
[trade/BBO semantics](https://databento.com/docs/schemas-and-data-formats/tbbo),
[CME holiday windows](https://www.cmegroup.com/trading-hours.html).
