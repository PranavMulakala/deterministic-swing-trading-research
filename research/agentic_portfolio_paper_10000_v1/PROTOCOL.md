# Frozen $10,000 paper-trial protocol

## Immutable scope

Profile `agentic_portfolio_paper_10000_v1` is a paper-only configuration wrapper.
It reuses the frozen `research.agentic_portfolio_v1` risk ledger and stock/options
engines without copying or changing strategy logic. It binds to core
`FREEZE.json` SHA-256
`e6d3961f98830ef46850f194ae77f7486714faac685bd6acd77a8a496ecf488d`
and independently verifies every core manifest entry before importing core code.
Manifest drift, file drift, a symlink, a missing file, or an extra runtime file
rejects the profile.

`orders_enabled`, `model_calls_enabled`, `network_enabled`, `broker_enabled`, and
`deploy_enabled` are literal booleans fixed to false in both code and the strict
configuration. This package cannot submit, cancel, replace, or route orders. It
cannot connect to a broker, load credentials, call a model, collect data, access a
network, deploy itself, schedule itself, or automatically run the trial.

## Account isolation and limits

The stock and long-option strategies each start with exactly $10,000 in distinct
SQLite files and distinct account IDs. The combined $20,000 is a bookkeeping sum,
not shared buying power. No transfer, shared balance, cross-margin, or cross-ledger
offset exists.

Before opening either ledger, the profile inspects both paths without following
symlinks. Existing paths must be regular files, must retain their device/inode
identity throughout initialization, and must not be hardlinks to the same inode.
A pre-existing alias is rejected before SQLite can mutate either file. Existing
ledgers receive a non-mutating preflight before either `RiskLedger` constructor is
invoked. A zero-byte regular file is an acceptable uninitialized placeholder. A
nonempty file is opened through SQLite URI `mode=ro&immutable=1` with `query_only`
and must have no journal/WAL/SHM sidecar, `user_version` zero, the exact core-v1
table/column sets, exactly the expected account ID and $1,000,000 initial cents,
the exact imported core policy hash, a clear integrity latch, coherent account
clock fields, a successful SQLite integrity check, and a clean run of the core
chronological reconciliation logic. Any corrupt, foreign, stale-schema, wrong-cash,
wrong-policy, or unreconciled database rejects without initializing an empty peer
or creating an absent peer. Missing names are exclusively claimed only after both
preflights pass.

The preflight performs no SQLite write transaction, WAL setup, checkpoint, chmod,
or repair, and it compares inode, size, modification time, and content hash across
the read. The later constructor phase rechecks path identities around each open.
These checks reduce offline path races but cannot make a concurrently hostile or
compromised filesystem safe; the state directory and its ancestors must remain
trusted and exclusively controlled while initialization runs.

Dollar limits are derived at runtime from the imported core `RiskPolicy`, not from
a second risk engine: 20%/$2,000 maximum equity position, 50%/$5,000 maximum
deployed, 50%/$5,000 minimum cash reserve, 5%/$500 maximum option contractual
loss, 2%/$200 daily realized-loss pause, and 5%/$500 high-water drawdown pause.
All original core engine, accounting, chronology, evidence, and risk invariants
remain applicable.

## Dates and evidence sufficiency

The trial planning timezone is `America/New_York`.

- planned start: 2026-09-15;
- first after-close checkpoint: 2026-10-26 16:30 EDT;
- scheduled after-close final review: 2026-10-30 16:30 EDT.

The explicit planning calendar contains 34 scheduled NYSE sessions from September
15 through October 30 under the published 2026 NYSE holiday calendar; its 30th
entry is October 26. Actual market opening, early/unscheduled closure, source
availability, evidence completeness, and successful processing must be verified
before a day is counted as a completed eligible session.

For the plausibility ceiling used by `review_assessment`, each listed session is
elapsed only when `as_of`, converted to `America/New_York`, is strictly later than
that date at 16:00. At exactly 16:00 or earlier, the current scheduled date is not
counted. Before September 15 the maximum is zero; after the final scheduled close
it remains 34. A claimed completed-session count above 34 or above the elapsed
maximum fails closed. This ceiling cannot prove that an elapsed session was open,
complete, successfully collected, or eligible; the separate completeness flag and
evidence review remain required.

The initial-review gate is at least 30 verified completed eligible sessions and at
least 20 closed trades **for each strategy**. Zero-trade days can count only toward
the verified session gate, not either trade gate. Before October 26, no initial
review is eligible even if caller-supplied counts are higher. On and after October
30, missing session or per-strategy trade evidence means the paper trial remains
incomplete; the calendar date alone does not promote or prove the system.

No review outcome produced here is proof of profitability, statistical
significance, robustness, production safety, broker execution quality, or live
readiness. Any continuation, design change, broker integration, or live-money
proposal requires a separately versioned and separately validated decision.

## News, sentiment, and external factors

The existing cloud collector records direct and sector news metadata. It does not
perform sentiment scoring. Neither reused strategy engine consumes that collector
metadata. The stock-entry schema accepts a caller-supplied `hard_adverse_news`
boolean and rejects an entry when it is true; this is not a sentiment model or a
complete news interpretation. The deterministic options baseline has no news or
sentiment feature.

Therefore this trial does not represent comprehensive news coverage, sentiment
analysis, fundamentals, analyst ratings, macro interpretation, geopolitical
reasoning, or exhaustive external-factor integration. Those omissions must remain
visible in every review.

## Verification boundary

The profile tests exact balances and dollar limits, physical and financial ledger
isolation, strict schema/type rejection, core freeze binding and manifest drift,
session close/timezone boundaries and review thresholds, news declarations, safe
import paths, and profile/core freeze integrity, including rejection of a symlinked
profile manifest. The offline demo uses only temporary local state.
Passing tests establish conformance to this protocol; they do not establish market
edge, real fills, data-feed completeness, automatic operation, deployment, or live
readiness.
