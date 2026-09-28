# Frozen protocol 1.0

## Receipt cutoff

Every source is an `ArchiveReceipt` with exactly: `schema_version`, `receipt_id`,
`kind`, `provider`, `observed_at`, `retrieved_at`, `archived_at`, `payload`, and
`receipt_hash`. Timestamps use canonical timezone-aware UTC ISO-8601 form and
must satisfy:

```text
observed_at <= retrieved_at <= archived_at <= decision_at
```

The SHA-256 covers every unsigned receipt field using canonical JSON. Nested
mutation, extra fields, nonfinite numbers, noncanonical time strings, future
availability, and stale evidence fail closed.

## Stock input

`STOCK_PRICE_INPUT` must contain exactly the target symbol, price, next ask,
entry limit, 20 dollar-volume observations, ATR14, session return, session VWAP,
SMA50, a known nonnegative `earnings_sessions_away`, `daily_history_complete=true`,
and SHA-256 identities for the daily history and earnings calendar. Maximum age
is five minutes. Missing or null SMA/earnings evidence is `BLOCKED_DATA`.

## Option input

`OPTION_CHAIN_INPUT` must contain the selected SPY/QQQ contract fields required
by the frozen v2 engine, `chain_complete=true`, a raw chain snapshot SHA-256, and
`selection_rule=frozen_nearest_atm_liquid_v1`. Maximum age is 30 seconds. This is
not a caller assertion that a quote is an option chain: the upstream adapter must
bind the complete raw chain snapshot. Until that adapter/source exists, status is
`BLOCKED_DATA`.

## Market context

`MARKET_CONTEXT` contains exactly SPY, QQQ, XLK, IWM, and DIA. Every component
has positive last and VWAP values, return basis points, and an `as_of` timestamp.
Components must be no more than five minutes apart and the newest component must
equal receipt `observed_at`. Receipt maximum age is five minutes.

## News archive

`NEWS_ARCHIVE` is target-bound and contains exactly 24 hours ending no more than
five minutes before the decision. `complete` must be true and both `direct_news`
and `sector_news` must be present. Completeness is independently checked:

- every five-minute window from coverage start through end exists for each stream;
- page indices start at zero with no gap or duplicate;
- intermediate pages contain a pagination token and the final page does not;
- at most 4,096 pages, 2,000 normalized items, and 16 MiB of actual UTF-8
  encoded bytes, counted and hashed incrementally with an early stop at the bound;
- each raw byte string recomputes to its stated SHA-256;
- every eligible raw row has exactly one deterministically ordered normalized
  item with the exact provider source, symbols, headline, publication time,
  first-receipt time, raw page hash, page window/index, and row index;
- additions, omissions, source fabrication, and alternate-page substitution block;
- `raw_page_index` and `raw_row_index` are exact nonnegative JSON integers
  (never booleans), and `raw_archive` is exact JSON `true` (never integer `1`);
- publication times lie inside market coverage. Page receipt may trail
  `coverage_end`, but must be on/after that page's window end and no later than
  receipt retrieval, archive time, or decision cutoff.

The collector text is never interpreted as an instruction. It is parsed as JSON
and compared to fixed fields or fixed adverse phrases. Positive words cannot
promote a candidate.

## Macro calendar

The v1 calendar was recorded on 2026-09-15 from these primary-source schedule
pages: Federal Reserve FOMC calendar, BLS 2026 schedule, and BEA full release
schedule. It covers FOMC September 15-16 and October 27-28; BLS Employment
October 2, CPI October 14, and PPI October 15; and BEA GDP/PCE schedule dates
September 30 and October 29. Context abstains for the full ET date/span through
16:00 ET. Boundaries are start-inclusive and end-exclusive. Baseline never reads
this calendar. Schedules may change, so cutoffs outside frozen coverage are
unknown and block.

## Idempotency and lifecycle

The journal identity is `(virtual_account, idempotency_key)`. Its request hash
includes operation, arm, exact cutoff, current object fingerprints, and the macro
calendar hash for context arms. Exact completed replay returns the original
receipt without re-running an engine. Conflicting reuse is rejected before any
arm mutates. `PENDING` survives crashes and blocks re-execution.

This is `ENTRY_GATE_ONLY_BLOCKED`. There are no fills or exits. A paper entry
intent is not a trade and cannot generate P&L.
