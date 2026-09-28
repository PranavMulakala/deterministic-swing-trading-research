# Local validation — September 8, 2026

- 29 MNQ feasibility tests passed, including long/short signal generation,
  volume-weighted variance, causal confirmation, missing-data rejection,
  realistic entry sides, delayed exits, gap-through-stop losses, daily resets,
  two-entry and one-position limits, unrealized high-water drawdown, persistent
  review pauses, unresolved inventory and denominator accounting.
- 158 existing application tests passed (5.703 seconds in this run).
- 125 pre-existing source/config/document files matched pre-change SHA-256
  checksums. Existing untracked work was preserved; no commit or push.
- The demo reproduced byte-for-byte into a fresh temporary directory. An attempt
  to reuse that output directory failed and left its result unchanged.
- Recorded source hashes matched current files. A separate arithmetic check
  reconstructed every demo trade's net P&L from entry/exit ticks, direction,
  multiplier and fees, then reconciled final cash for all four scenarios.

`demo-02` uses invented data. These tests validate selected software behavior,
not profitability, vendor completeness, broker fills, live risk controls or
account eligibility. No MNQ market dataset was acquired or replayed. No real or
paper broker orders, purchases, installations, cloud mutations or deployments.

Current real-evidence status: **BLOCKED_MISSING_MNQ_DATA_AND_VERIFIED_COSTS**.
The raw-vendor importer, calendar/contract checks and source-quality audit remain
to be implemented/validated against the selected export once available.
