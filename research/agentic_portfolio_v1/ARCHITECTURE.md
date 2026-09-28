# Architecture

## Requirements

The design must keep the stock and option experiments financially isolated while enforcing identical account-wide risk semantics. All inputs are hash-bound point-in-time packets. All outputs say `PAPER_ONLY/NO_ORDER`. State survives process restarts. Malformed, stale, missing, conflicting, or ungrounded inputs fail closed.

## Components and data flow

```text
validated evidence packet
        |
        +--> stock engine ----------+
        |                           |
        +--> option baseline/council+--> shared RiskLedger code --> isolated SQLite account
                                    |
                                    +--> paper decision --> card + JSON receipt

read-only broker receipts --> broker_handoff validator --> comparison/reconciliation only
```

- `evidence.py` enforces exact schemas, hashes, ordering and freshness of timestamps.
- `stock.py` applies the frozen +10% net-return swing assumptions and review/exit schedule. Plans and holding time are re-derived from the durable position, origin reservation, fills and UTC timestamps. Management evidence cannot predate the latest fill contributing to its position economics.
- `options.py` applies the frozen long-option assumptions. Entry economics and the management clock are re-derived from the durable fill; caller fields cannot reset them, and management evidence cannot predate the fill. `council.py` defines optional analyst/critic envelopes, but makes no model calls. Baseline mode is deterministic.
- `risk.py` owns atomic reservations, idempotent reservation-create/fill/close/release/expiry event journals, a monotonic UTC account clock, limits, durable controls, fills, conservative credit rounding, and chronological event-derived reconciliation before every mutation or replay. Account, reservation and position records carry the exact frozen policy/strategy-version identity. Each engine requires its literal version at entry replay, plan construction and management. A persistent integrity latch has an explicit repair path.
- `controller.py` revalidates packet integrity, freshness, decision identity and account binding before creating hash-sealed human-readable cards and receipts.
- `broker_handoff.py` validates three read-only receipt shapes. An order review requires the actual validated quote receipt it names. The module contains no brokerage client or URL.

## Decisions and trade-offs

SQLite with `BEGIN IMMEDIATE` was selected for a single-process/small-account research system because transactions, uniqueness constraints and durable recovery are more important than distributed throughput. Separate database files prevent accidental capital commingling. Decimal inputs are stored as integer cents or canonical decimal strings to avoid binary-float accounting.

The stock strategy uses a review threshold rather than an automatic -10% stop, matching the stated research hypothesis. The fail-closed 42-session exit and 126-session absolute maximum prevent “hold forever” from becoming an unbounded hidden rule. Full notional is treated as modeled stock downside because no hard stop exists.

Stock and option holding time use conservative UTC weekdays derived from durable opening and decision timestamps. This avoids a caller-resettable clock and may exit early on exchange holidays. Adding an exchange-calendar adapter requires a new version.

The options budget is intentionally restrictive. On $1,000, the 5% maximum contractual loss is $50; a one-contract premium above that budget produces no trade. The system never fractions an option contract to make a signal fit. Worthless long options can be marked and closed at zero without inventing proceeds.

The package does not migrate older journals in place. Exact schema checks reject them so a changed policy, reservation lifetime, or identity cannot be silently reinterpreted under this version.

## Scaling boundary

If this progresses beyond one local research process, preserve the schemas and pure engines while moving transactional risk state to a serializable database and adding an authenticated, separately deployed execution gateway. That gateway is deliberately absent here. Data adapters, model providers, monitoring and broker reconciliation must each be versioned and independently tested before any broker-capable version is considered.
