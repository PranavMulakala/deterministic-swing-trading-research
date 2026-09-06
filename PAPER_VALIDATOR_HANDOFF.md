# Independent Validator Handoff — Paper Readiness Branch

Audit the exact supplied commit read-only. Do not use credentials, mutate the paper account, place or cancel an order, change files, or accept the builder's test summary without reproducing it.

## Expected verdict to challenge

The builder's verdict is **software path implemented; operational NO-GO for a faithful v1 paper trial** because Alpaca fractional orders are DAY-only, the required persistent GTC stop forces whole-share sizing, and human-approved regular-session fills are not guaranteed to match the backtest's next-open fills.

Try to falsify both halves: find any code path that could reach live money or bypass approval or risk, and independently verify whether the declared broker/spec mismatches are real.

## Required audit

1. Record `git rev-parse HEAD`, `git status --short`, and the diff from validated commit `ba1232e`.
2. Re-run the full test suite and frozen reproduction. Confirm the core v1 result artifacts remain byte-identical to `ba1232e`.
3. Trace every network-capable import. Confirm only frozen data acquisition and the narrow Alpaca adapter can perform network I/O; confirm no LLM can influence selection, indicators, signal, sizing, risk, proposal, approval, or execution.
4. Prove that no constructor, config, environment variable, URL, redirect, or request path can send an order to `https://api.alpaca.markets` or another trading host.
5. Exhaustively challenge account binding, cash-only sizing, per-trade risk, aggregate risk including pending orders, daily halt, duplicates, stale/future/wide/drifting quotes, market-hours gating, and whole-share/GTC enforcement.
6. Attempt approval reuse, proposal mutation, expiration bypass, session omission, batch submission, conditional order persistence, persisted runtime-gate bypass, superseded-review approval, fabricated reserved authorization or authoritative state events, authorization-table tampering, and concurrent status/scan/review/execute processes.
7. Replay journal state from genesis; tamper with every stored field class; confirm every failed public paper operation is recorded without granting authority; test restart before submission, after authority is consumed but before/after an uncertain POST, during partial entry or exit fill, after parent fill/before child activation, during stop cancellation or lost cancellation verification, after exit fill, and with duplicate, malformed, regressing, unknown, or manual broker state. Reconcile cash from the bound baseline through every fill, validate account/position market-value identities, and prove repeated polls cannot duplicate a fill or realized P&L.
8. Verify the adapter submits exactly one market/GTC/OTO buy with the approved quantity and stop; confirm the direct nested child is a sell stop—not a stop-limit—at the approved price. Confirm ordinary exits cannot submit until both the adapter capability and durable journal record prove the exact old stop canceled or expired.
9. Check Alpaca's current official documentation for fractional TIF, advanced-order TIF and leg behavior, empty/simple `order_class`, order states, `filled_at`, nested retrieval, paper endpoint, account, asset, quote, and historical-bar semantics. Confirm that parent/child association is validated through the documented direct nested `legs` relationship without assuming an undocumented child `parent_order_id`. Cite exact primary pages and identify any documentation ambiguity.
10. Inspect all 25 source modules and every test, not a sample. Report critical, major, and minor findings with file and line evidence.

## Bright-line pass conditions

- Zero path to live-money submission.
- Zero order without a fresh exact one-use owner approval and both runtime gates.
- Zero accepted fractional Alpaca swing entry.
- Zero accepted entry without a matching broker-native persistent stop.
- Zero local position open or close transition without corresponding broker-confirmed fill.
- Zero unexplained cash movement or account/position market-value mismatch beyond the declared one-cent paper tolerance.
- Every unexplained account, order, or position state latches the kill switch and blocks new submission.
- Frozen v1 artifacts and conclusions are unchanged.

Do not change the no-go verdict merely because the software tests pass. A go verdict requires observed owner-account paper evidence and a separately approved, pre-registered resolution of the execution mismatches.
