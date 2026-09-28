# Architecture

## Requirements and invariants

The package is an offline, deterministic, paper-only A/B entry gate. Literal
capability constants and config fields disable orders, brokers, networks, model
calls, and deployment. There is no endpoint input and no execution method.
Frozen dependency files are verified byte-for-byte before engine import.

The experiment has two dimensions: frozen stock versus frozen long-option entry
logic, and price-only control versus context treatment. Each cell owns a
physically distinct SQLite risk ledger initialized with $10,000. A fifth SQLite
journal contains only decision-request identities and receipts; it is not a cash
pool. Cross-arm balances must never be aggregated.

## Components

- `binding.py`: pins both upstream `FREEZE.json` hashes, their complete manifest
  file sets, and every listed file digest.
- `receipts.py`: strict hash-bound archived-provider receipt envelope with
  canonical UTC chronology and receipt-cutoff validation.
- `context.py`: complete market/news validation plus deterministic veto logic.
- `sector_mapping.json`: bounded target-to-upstream/customer/supplier/peer map,
  copied prospectively from the exact pinned cloud mapping.
- `macro.py` and `macro_calendar.json`: ET scheduled-event abstention windows.
- `runner.py`: validates required strategy inputs, imports the bound frozen core,
  opens isolated ledgers, evaluates paired entry gates, and journals idempotent
  paper receipts.
- `observer.py`: read-only, always-blocked current data-gap report.
- `deployment/`: an explicit nondeployment decision; no service or strategy runner.

## Data flow

```text
external collector/archive
  -> immutable archive receipt available by cutoff
  -> exact schema, hash, chronology, completeness and freshness validation
  -> frozen technical screen
       -> price control -> frozen core entry engine -> isolated paper ledger
       -> context gate
            -> macro veto
            -> complete SPY/QQQ/XLK/IWM/DIA regime
            -> complete raw direct/bounded-sector news archive
            -> frozen core entry engine -> isolated paper ledger
  -> hash-bound JSON decision receipt + durable idempotency journal
```

Nothing in this flow fetches data. Receipts are produced outside the decision
boundary from data that was already archived. A receipt archived after the
decision cutoff is rejected even when its underlying market timestamp is older.

## Context logic

The market gate vetoes if QQQ or XLK is at or below -150 bps, or if at least
three of the five context symbols are at or below -100 bps. It is clear only if
at least three symbols are nonnegative and both QQQ and XLK are above -50 bps.
Everything between those sets is ambiguous and blocks. These are precommitted
research assumptions, not proven optimal thresholds.

News can only veto via a short fixed adverse-phrase list. A sector item is
eligible only when its symbols intersect the exact mapping for the candidate.
Unmapped headlines are ignored. Direct items must name the candidate. Raw page
bytes are recomputed to their SHA-256, parsed only as data, and matched to the
normalized item. Both streams need every contiguous five-minute window and every
pagination page for the 24-hour interval.

The macro gate blocks the whole named ET date/span from midnight through 16:00
ET (end exclusive). This deliberately over-blocks rather than guessing release
times. Agency schedules can change; this v1 snapshot does not refresh itself.

## Tradeoffs and scaling

The strict raw-news proof can require hundreds of page records per decision and
is intentionally expensive. A future version could replace embedded bytes with
a Merkle proof over a separately immutable archive, but only after equivalent
coverage, pagination, and cutoff guarantees are tested. A future full trial also
needs point-in-time earnings, at least 50 daily sessions, fresh execution data,
complete option chains, and idempotent fill/mark/close accounting. Those are
version-bound additions, not patches to v1.

SQLite is appropriate for one local observer process. Multiple writers or a
distributed deployment would need a new transactional design. The current
journal fail-closes on a crash-left `PENDING` row because cross-database atomicity
between four frozen ledgers and the decision journal is not claimed.
