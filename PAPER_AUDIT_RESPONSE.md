# Builder response to the owner-supplied paper audits

The earlier Claude report audited commit `4fff0c1f7c2dd53b82778615a81b13e128285937`. The later Astra High report audited commit `959b050280316d67eca3cec379e3001bc50ca142` and found five major defects plus two minor gaps. This document records builder dispositions and test evidence, not independent validation of the resulting commit.

## Owner-authorized fixes after the independent `35b570c` re-audit

The independent re-audit of `35b570c3958b061ed4ce34fe37cc4172b4ce19a3` still found five major and two minor issues. The owner then authorized fixes on top of that commit. Implementation tests are not a separate independent certification. The earlier dispositions below are historical claims and are superseded where this table identifies an incomplete fix.

| Re-audit defect | Implemented correction and counterexample |
|---|---|
| R1 major: serialization/connection delay and clock skew outlived authorization | JSON serialization now precedes permit claiming. Journal checks include elapsed lock/integrity time. The production HTTPS connection checks a monotonic, conservative broker-time bound after TLS setup and before each HTTP write, with a two-second reserve and equality rejected. Delayed serialization, expired claim, delayed TLS, and delay between headers/body all block the affected write. Clock regressions cannot extend the bound. No client can guarantee remote arrival time or rule out arbitrary OS suspension after its final check. |
| R2 major: stop earlier than an already-imported entry was accepted | The shared stop/ordinary-exit close path compares the fill against the durable entry timestamp before recording a close. A stop at `15:00:03` after an entry recorded at `15:00:04` latches and creates no close. Repeated reconciliation stays idempotent; ordinary approved exits use the same check. |
| R3 major: clock sampled before slow broker snapshots falsely rejected valid fills | Status, scan/preflight snapshots, reconciliation, owner clearing, and post-cancel state checks now sample the broker clock after the relevant account/position/order reads. A complete zero-P&L round trip during order retrieval reconciles exactly once without a false latch. |
| R4 major: broker parsing errors did not latch | All workflow broker reads use a common failure boundary that latches durably when the journal is writable before propagating the original error. Invalid timestamp, nonnumeric quantity, and missing-symbol wire responses block a subsequent otherwise-valid order, even after the broker returns clean data. |
| R5 major: working child with partial/future fill evidence was accepted | Working child orders require a nonempty ID, finite zero filled quantity, and absent fill price/time. Working parent entries and ordinary exits also reject a reported average fill price. Partial, future, NaN, price-only, and missing-ID variants fail closed. |
| R6 minor: ancestor replacement raced path checks | Journal, lock, and dashboard operations now use pinned directory descriptors, no-follow opens, descriptor chmod, and descriptor-relative atomic replacement. SQLite runs in memory under a separate storage lock and publishes the ordinary SQLite file atomically. Tests swap an ancestor immediately before chmod and a leaf immediately before open; redirected targets remain unchanged. Three concurrent writers retain all 24 unique events. Failed publications preserve the old file or recover the already-published event once. Legacy nonempty sidecars require an owner-controlled checkpoint. |
| R7 minor: stale PDT documentation | Removed the claim that current paper accounts simulate legacy PDT checks. The current paper guide and July 6, 2026 account-schema changelog are cited in `PAPER_READINESS.md`; owner-account restrictions remain unverified. |
| R8 follow-up major: later reconciliation accepted contradictory partial-fill evidence on a working child stop | The shared order-fill validator now permits a partial quantity only when the broker status is `partially_filled` and both average price and fill timestamp are present. A working stop reported as `new` with a partial filled quantity now latches during a later reconciliation, not only during the immediate acknowledgement check. |

Verification: **150 tests passed**, including 18 new regression tests in `tests/test_paper_reaudit.py`. A separate follow-up review reproduced the initial 149-test result and both frozen reproductions, identified R8, and then reran the complete 150-test suite after the correction. The original independent audit probes were also rerun in a disposable copy, covering F1–F5, N1–N2, approval/risk boundaries, malformed wire data, asynchronous exits, recovery, tampering, network fences, and concurrent public operations. The complete frozen reproduction remains byte-identical across all 21 artifacts; all 41 protected files match `ba1232e`. Detailed commands, results, hashes, and limits are recorded in `PAPER_FIX_VERIFICATION.md`.

**Operational NO-GO remains.** No credentials, account endpoints, orders, or active journal migration were used for these fixes. The preregistration's abandonment clause was not changed or waived. Fixing software does not authorize an operational trial or resolve that policy requirement.

## Astra findings reproduced and implemented after `959b050`

| Astra finding | Builder disposition |
|---|---|
| F1, approval/quote/session checks could age before POST | Execution now completes slow asset/state requests before a final account/position/order/quote refresh with the broker clock sampled last. The approved capability carries a journal-bound deadline equal to the earliest proposal expiry, quote-age limit, or session boundary; the adapter checks it both before and after the durable permit claim, immediately before transport. Exit permits use the earlier cancel cutoff. Tests cross proposal expiry and market close during preflight and expire a permit between claim and transport; no POST occurs. |
| F2, normal post-preflight fill appeared future-dated | Fill evidence is now bounded by a broker clock sampled after the acknowledgement is received. A regression submits at `15:00:00`, fills at `15:00:01`, acknowledges at `15:00:02`, and remains unlatched. |
| F3, NaN daily bar could create a signal and order | Historical rows now require a valid object, requested symbol, timezone-aware in-range date, finite positive OHLC, nonnegative finite volume, and a consistent high/low envelope. Signal evaluation independently rejects invalid bars and nonfinite indicators. Tests cover NaN, inconsistent OHLC, and a direct signal-path injection. |
| F4, complete entry/stop round trip between polls failed | Reconciliation now accepts a broker-confirmed filled child stop as historical protection when the parent also fully filled, validates both fills and their chronological order, records the entry and close with broker fill timestamps, and remains idempotent on later polls. The regression reconciles exact cash and realized P&L with one entry and one close event. |
| F5, broker cost-basis mismatch passed | Managed quantity and average entry price are both compared to the journaled fill. A difference over the declared one-cent accounting tolerance is an issue and latches the kill switch. |
| N1, repeated bar page token could loop forever | Historical-bar pagination rejects repeated tokens, repeated symbol/date rows, malformed page shapes, unexpected symbols, and invalid token types. The repeated-token regression terminates on the second page request. |
| N2, symlinked journal ancestor was followed and chmodded | Journal, lock, and dashboard paths validate every existing component before directory creation/open and again after creation. User-controlled ancestor symlinks are rejected before chmod; root-owned macOS compatibility aliases such as `/var` remain usable. |

At `35b570c`, the builder suite executed 132 tests. The frozen historical strategy, data, configuration, preregistration, and v1 artifacts are intentionally unchanged.

## Established findings

| Claude finding | Builder disposition |
|---|---|
| C1, repeated reconciliation fabricated duplicate fills/P&L | Fixed before this hardening pass. State now remembers handled entry client IDs and closed broker order IDs; repeated-poll regression coverage remains in the suite. |
| M8, broker transport inherited environment proxies | Fixed in this pass. The production opener installs an empty `ProxyHandler`, retains the no-redirect handler, and has a direct regression test. |

## Leads reproduced against the current builder tree and addressed

| Lead | Builder change |
|---|---|
| C2/M10, partial-fill cancellation race and synchronous fake | Exit proposals now bind the exact stop ID and price. The adapter polls terminal cancellation, never unlocks a sell when any fill evidence exists, and the workflow re-checks account, clock, and position after cancellation. Tests cover pending cancellation, partial-then-canceled, filled, changed position, lost verification, and near-close rejection. |
| M2, daily halt based on previous-close `last_equity` | The risk gate now uses the first durable account-equity observation in the current run and trading day. Status separately labels observed-day and Alpaca previous-close P&L. |
| M3, quote sampled just after broker clock rejected | A fixed two-second future tolerance is consistently enforced by quote policy, risk authorization, proposal validation, review validation, and execution validation. Larger future skew remains rejected. |
| M4, aggregate-risk ratio could deadlock exits after equity moved | A market-driven ratio overrun is a reconciliation warning, not an unexplained-state latch. The existing risk manager still rejects any additional entry that would exceed 3%. |
| M5, cash-only cap lacked execute-time defense | Execution re-checks current cash and non-marginable buying power against the approved maximum entry reference immediately before submission. |
| Missing config sidecar/digest anchor | `strategy_v1.json` now requires its sidecar and must match the code-anchored frozen digest. |
| Stop cancel permit not bound to stop | The exit proposal, content hash, review, adapter, and durable cancel-verification event bind the stop ID and price. |
| Order history truncated at 500 | The Alpaca adapter paginates with `before_order_id` and rejects duplicate/non-progressing pages. |
| Lock/dashboard local path hardening | Journal, lock, and dashboard files are owner-only; journal/dashboard/lock symbolic-link paths are rejected. |
| Noncanonical HTTP method strings | Methods are stripped, canonicalized, allowlisted, and all mutations still require the private adapter capability plus journal permit. |

## Leads already addressed before this pass or not reproduced as current defects

- Persisted runtime gates are rejected by the `.env` loader; it accepts only the two paper credential names.
- Public workflows hold one cross-process lock across snapshot, approval, cancellation, and submission.
- Approval consumption cross-checks the exact stored proposal and latest review.
- Whole-share quantity is validated from the numeric quantity, not only a boolean flag.
- Clean-$500 rebaseline exists for manual recovery and invalidates prior-run proposals/permits without deleting history.
- The hash chain is deliberately not a signed external audit anchor, and Python is not treated as a sandbox against a hostile process running as the same macOS user. These boundaries remain disclosed rather than overstated.
- A broker `replaced` order remains fail-closed and requires operator reconciliation; the builder did not silently follow a corporate-action replacement chain without real paper-account evidence.

## Still requires independent validation and owner-account evidence

Any eventual commit containing the current fixes must be audited read-only from its exact hash. No local test establishes that the owner's real Alpaca paper account accepts the exact OTO payload, produces the assumed child-stop lifecycle, exposes cancellation within the bounded polling window, or supplies IEX bars sufficiently equivalent to the frozen Yahoo dataset. No credential was read and no order was placed during this build.
