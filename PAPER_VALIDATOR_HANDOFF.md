# Independent Validator Handoff — Paper Readiness Branch

> **September 22, 2026 orientation:** See the [current project handoff](output/PROJECT_HANDOFF_20260922.md) for all experiments, updated broker/cloud status, LITE opening-dip evidence, and the Claude review prompt. The dated material below retains its original scope; it is not a current status report for every project track. Frozen strategies and historical evidence are unchanged.


Audit the exact supplied commit read-only. Do not use credentials, mutate the paper account, place or cancel an order, change files, or accept the builder's test summary without reproducing it.

## Expected verdict to challenge

The builder's verdict is **software path implemented; operational NO-GO for a faithful v1 paper trial** because Alpaca fractional orders are DAY-only, the required persistent GTC stop forces whole-share sizing, human-approved regular-session fills are not guaranteed to match the backtest's next-open fills, and Alpaca IEX bars are not proven signal-equivalent to the frozen Yahoo adjusted dataset.

Try to falsify both halves: find any code path that could reach live money or bypass approval or risk, and independently verify whether the declared broker/spec mismatches are real.

## Required audit

1. Record `git rev-parse HEAD`, `git status --short`, and the diff from validated commit `ba1232e`.
2. Re-run the full test suite and frozen reproduction. Confirm the core v1 result artifacts remain byte-identical to `ba1232e`.
3. Trace every network-capable import. Confirm only frozen data acquisition and the narrow Alpaca adapter can perform network I/O; confirm no LLM can influence selection, indicators, signal, sizing, risk, proposal, approval, or execution.
4. Prove that no constructor, config, environment variable, URL, redirect, or request path can send an order to `https://api.alpaca.markets` or another trading host.
5. Exhaustively challenge account binding, cash-only sizing, per-trade risk, aggregate risk including pending orders, daily halt, duplicates, stale/future/wide/drifting quotes, market-hours gating, and whole-share/GTC enforcement. Force slow preflight calls across proposal expiry, quote expiry, market close, and the exit-cancel cutoff; prove both the journal permit claim and the adapter's immediate pre-transport check enforce the earliest bound.
   Confirm the daily halt uses the first durable same-day equity observation, not Alpaca `last_equity`; confirm a market-driven aggregate-risk warning blocks new entry risk without blocking a valid approved exit.
6. Attempt approval reuse, proposal mutation, expiration bypass, session omission, batch submission, conditional order persistence, persisted runtime-gate bypass, superseded-review approval, fabricated reserved authorization or authoritative state events, authorization-table tampering, and concurrent status/scan/review/execute processes.
7. Replay journal state from genesis; tamper with every stored field class; confirm every failed public paper operation is recorded without granting authority; test restart before submission, after authority is consumed but before/after an uncertain POST, during partial entry or exit fill, after parent fill/before child activation, during stop cancellation or lost cancellation verification, after exit fill, and with duplicate, malformed, regressing, unknown, or manual broker state. Include a complete parent-fill/child-stop-fill round trip between polls and prove chronological, exact, idempotent entry/close/P&L recovery. Change only broker average entry price while preserving quantity, cash, and market value; prove a difference over one cent latches. Prove the owner-confirmed rebaseline is impossible unless the same account is clean, flat, reset to $500, and latched; prove it preserves earlier events while resetting only the new operational run and permanently invalidating every older proposal/permit. Reconcile cash from the latest run baseline through every fill, validate account/position market-value identities, and prove repeated polls cannot duplicate a fill or realized P&L.
8. Verify the adapter submits exactly one market/GTC/OTO buy with the approved quantity and stop; confirm the direct nested child is a sell stop—not a stop-limit—at the approved price. Confirm ordinary exits bind and restate the exact old stop ID and price, poll asynchronous cancellation to a terminal state, reject all partial-fill evidence, re-check the account/clock/position after cancellation, and cannot submit until both the adapter capability and durable journal record prove the exact zero-fill stop canceled or expired.
9. Prove broker egress ignores environment proxy variables, redirects remain prohibited, order history paginates beyond 500 parent orders without duplication, and historical bars reject repeated tokens, duplicate dates, malformed/nonfinite OHLCV, unexpected symbols, and invalid page shapes. Prove journal/dashboard paths have owner-only permissions and reject leaf and ancestor symbolic links before chmod/open.
10. Check Alpaca's current official documentation for fractional TIF, advanced-order TIF and leg behavior, empty/simple `order_class`, order states, asynchronous cancellation, `filled_at`/`filled_qty`, nested retrieval, pagination, paper endpoint, account, asset, quote, and historical-bar semantics. Confirm that parent/child association is validated through the documented direct nested `legs` relationship without assuming an undocumented child `parent_order_id`. Cite exact primary pages and identify any documentation ambiguity.
11. Inspect all 26 source modules and every test, not a sample. Report critical, major, and minor findings with file and line evidence.

## Additional counterexamples after the `35b570c` re-audit

The current owner-authorized fixes are described in `PAPER_FIX_VERIFICATION.md`. Independently repeat those probes; do not infer certification from the fixing agent's results.

- Cross the deadline during JSON serialization, journal lock/integrity checking, TLS setup, and between HTTP header/body writes. Exercise the production urllib handler with a fake socket, not only an injected transport. Test equality and local/broker clock regressions. Distinguish local write authorization from unprovable remote arrival timing or arbitrary process suspension.
- Import an entry on one poll, then report a protective stop or ordinary exit with an earlier timestamp on the next. Neither may create a close or realized P&L. Equal entry/stop timestamps remain valid.
- Complete a coherent zero-P&L entry/stop round trip during a slow order poll. Status, scan, reconciliation, and owner-confirmed clearing must use a subsequent broker clock, without accepting genuinely future fills.
- Make real adapter parsing raise on malformed timestamps, numeric strings, or missing fields. Restore a clean response and prove new execution stays blocked by a durable latch. Test working child orders with partial, future, nonfinite, price-only, and missing-ID fill evidence.
- Repeat contradictory child-order fill probes during later reconciliation, not only the immediate acknowledgement. A working status such as `new` with a partial filled quantity must latch; coherent `partially_filled` evidence must remain fail-closed through the existing partial-fill path.
- Swap ancestors after directory opening and before chmod/open/replace; swap leaves after checking and before opening. Verify the redirected target's contents and mode remain untouched for journal, lock, and dashboard. Preserve legitimate root-owned macOS aliases.
- Test competing journal writers and failures both before and after atomic snapshot publication. Reopen and verify event/hash-chain integrity and exact-once authorization. Legacy uncheckpointed WAL/rollback data must be rejected without discarding it; a closed, fully checkpointed legacy SQLite file must preserve all existing events.
- Confirm current PDT claims use current official documentation. Do not treat the older versioned paper guide as proof of owner-account restrictions.

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
