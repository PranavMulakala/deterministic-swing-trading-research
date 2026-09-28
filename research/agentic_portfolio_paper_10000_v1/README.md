# Agentic Portfolio $10,000 Paper Profile v1

This is a separately versioned, **paper-only and offline** profile around the frozen
`agentic_portfolio_v1` engines. It does not alter or replace that validated package.
It creates two financially isolated simulated accounts:

- stock swing: $10,000 initial cash in `stock_swing.sqlite`;
- long options: $10,000 initial cash in `long_options.sqlite`.

That is **$20,000 of total simulated bookkeeping**, not one shared $10,000 or
$20,000 pool. A result in one ledger cannot change the other ledger.

The shared frozen risk policy produces these limits for each $10,000 account:

- $2,000 maximum stock position (20%);
- $5,000 maximum deployed capital and $5,000 minimum cash reserve (50% each);
- $500 maximum option contractual loss (5%);
- $200 daily realized-loss halt (2%);
- $500 high-water drawdown halt (5%).

## Trial window and review gates

The planned start is September 15, 2026. The first checkpoint is after the close
on October 26, when the published 2026 NYSE calendar implies the 30th scheduled
session. The scheduled final review is after the close on October 30, 2026.
September 15 through October 30 contains **34 scheduled NYSE weekday sessions**
under the [published 2026 NYSE calendar](https://www.nyse.com/markets/hours-calendars).
Actual completed-session status and data completeness must still be verified; the
hardcoded dates are a planning declaration, not an exchange-calendar feed.
For count plausibility, a listed date becomes elapsed only when the supplied time
is **strictly after 16:00 America/New_York**. At or before the normal scheduled
close, that date does not count. Before September 15 the elapsed maximum is zero,
and after October 30 it is capped at 34. Claimed completed sessions above the
elapsed maximum are rejected.

An initial review requires all of the following:

- at least 30 completed eligible market sessions whose completeness was verified;
- at least 20 closed stock-strategy trades;
- at least 20 closed option-strategy trades;
- the October 26 after-close checkpoint has been reached.

The October 30 date is a scheduled review, not an instruction to stop despite
missing evidence. Meeting these gates permits analysis only. It is not proof of
profitability, promotion approval, broker readiness, or permission for live use.

## News and external-factor boundary

The existing cloud collector records direct-news and sector-news metadata, but it
does **not** score sentiment. These reused engines do not consume that collector
metadata. The stock engine consumes only a supplied `hard_adverse_news` boolean;
the option baseline consumes no news or sentiment input. This profile therefore
does not claim comprehensive news, fundamentals, analyst ratings, macroeconomic
interpretation, external-factor analysis, or sentiment integration.

## Safety and operation

Orders, model calls, network access, broker access, and deployment are hard false.
The package contains no runner, scheduler, credential loader, broker client, or
network client. Adding this profile does not deploy it or automatically start the
trial. A later paper-data workflow would have to be separately authorized and
validated while keeping these capability flags false.

The profile verifies the exact SHA-256 of the core `FREEZE.json` and every hash in
that manifest before importing `RiskLedger`, `StockSwingEngine`, or
`OptionShadowEngine`. Any core or profile drift fails closed.
Before either ledger is opened, both target paths must be regular, non-symlink
files with distinct device/inode identities. A pre-existing hardlink alias is
rejected without modifying either file.
Every nonempty existing ledger is then opened with SQLite's read-only immutable
URI mode and `query_only`: its exact core-v1 tables/columns, account identity,
$10,000 balance identity, policy hash, SQLite integrity, account clock/latch state,
and chronological core reconciliation must pass. A zero-byte placeholder is
accepted as uninitialized, but neither placeholder is initialized until both
preflights pass. Unresolved WAL/journal/SHM sidecars reject rather than being
checkpointed or changed.

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest research.agentic_portfolio_paper_10000_v1.test_profile
PYTHONDONTWRITEBYTECODE=1 python -m research.agentic_portfolio_paper_10000_v1.freeze
PYTHONDONTWRITEBYTECODE=1 python -m research.agentic_portfolio_v1.freeze
PYTHONDONTWRITEBYTECODE=1 python -m research.agentic_portfolio_paper_10000_v1.demo
```

The demo creates both databases only inside a temporary directory, prints their
initial snapshots and limits, and deletes the temporary state on exit.
