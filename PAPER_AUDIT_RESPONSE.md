# Builder response to the owner-supplied Claude paper audit

The supplied Claude report audited commit `4fff0c1f7c2dd53b82778615a81b13e128285937`, not this branch's eventual frozen Astra target. Claude explicitly reported that its audit did not certify the later tree. This document records builder dispositions, not independent validation.

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

The new frozen commit must be audited read-only by Astra-medium. No local test establishes that the owner's real Alpaca paper account accepts the exact OTO payload, produces the assumed child-stop lifecycle, exposes cancellation within the bounded polling window, or supplies IEX bars sufficiently equivalent to the frozen Yahoo dataset. No credential was read and no order was placed during this build.
