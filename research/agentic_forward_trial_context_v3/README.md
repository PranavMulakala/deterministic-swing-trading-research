# Agentic forward trial with deterministic context, v3

## Outcome

This is a new, isolated **paper-only entry-gate observer**. It does not place,
preview, route, cancel, or replace an order. It does not call a model, a broker,
or the network. Its overall status is **BLOCKED** because the current archives do
not supply all inputs required by the two already-frozen strategies and this
version intentionally has no fill/mark/exit lifecycle.

It compares four independent hypothetical accounts. Never add their balances:

- `price_stock`: $10,000 frozen technical-control ledger;
- `context_stock`: $10,000 technical candidate plus context-veto ledger;
- `price_options`: $10,000 frozen deterministic option-control ledger;
- `context_options`: $10,000 option candidate plus context-veto ledger.

All four bind the exact manifest hashes of `agentic_portfolio_v1` and
`agentic_portfolio_paper_10000_v1` before importing their core engines. Neither
upstream package was modified.

## What the comparison means

The price-only control applies the frozen numeric entry filters. Its
`hard_adverse_news=false` value is an experimental feature-disable constant, not
a factual claim that news was neutral. The context arm can only evaluate a
candidate that already passed the corresponding deterministic technical screen.
It can preserve, veto, or block that candidate; it can never create one.

Context requires all of the following at the exact decision cutoff:

1. complete, fresh archived SPY/QQQ/XLK/IWM/DIA market context;
2. 24 continuous hours of five-minute direct and bounded-sector raw news pages,
   including exact archived raw bytes and page hashes;
3. the frozen scheduled-macro calendar to cover the cutoff.

Missing, stale, incomplete, mixed, or ambiguous context is `BLOCKED_DATA`, never
neutral. Headline text is inert data. A fixed phrase list may veto a candidate;
positive language is never a reason to enter.

Version 2 closes four archive-integrity gaps found in external review. Every
eligible raw provider row must have an exact normalized counterpart, including
its provider source, row index, page identity, and page hash; omission or
substitution blocks. Market coverage ends at `coverage_end`, while a page may
arrive slightly later only when its receipt is still available by the decision
cutoff. Upstream runtime/specification files must exactly match their manifests;
test files and interpreter caches remain explicitly outside that runtime set.

Version 3 closes two serialization-boundary gaps from the next review. The
16 MiB archive ceiling is now measured from actual UTF-8 encoded bytes with an
incremental bounded hash, not Python character count. Normalized news primitives
use exact JSON types, so booleans cannot stand in for integer page/row indices
and integers cannot stand in for the literal `raw_archive=true` assertion.

## Current evidence boundary

The code-visible current collector waits 1,200 seconds. The frozen stock engine
allows five-minute evidence and the option engine allows 30-second evidence.
The collector has no earnings-calendar or option-chain stream. The bundled
warmup has 20 sessions, which cannot independently produce SMA50. Therefore the
runner must report `BLOCKED_DATA` unless a separate, point-in-time archived
source proves every required field. It never invents `sma50`,
`earnings_sessions_away`, an option chain, or a neutral news state.

`PAPER_ENTRY_INTENT` is only a reserved hypothetical entry. This version has no
modeled fill, mark, management, close, or performance calculation. It cannot
satisfy a closed-trade review gate and must not be described as a working or
profitable trial.

## Safe commands

From the repository root with Python 3.12:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest research.agentic_forward_trial_context_v3.test_forward_trial -v
PYTHONDONTWRITEBYTECODE=1 python3 -m research.agentic_forward_trial_context_v3.demo
PYTHONDONTWRITEBYTECODE=1 python3 -m research.agentic_forward_trial_context_v3.observer
PYTHONDONTWRITEBYTECODE=1 python3 -m research.agentic_forward_trial_context_v3.freeze
```

The demo uses a temporary directory and deliberately shows missing inputs as
`BLOCKED_DATA`. The observer is read-only, prints a blocked JSON diagnostic, and
returns status 2. `deployment/README.md` explicitly records why no installable
unit was produced. Nothing was installed or enabled.

Before a deliberate reopen of a runtime created by this package, call
`runtime.checkpoint_and_close()`. Unresolved SQLite sidecars fail closed. A crash
may leave a `PENDING` request; replay then returns `BLOCKED_DATA` for manual paper
state inspection rather than issuing a second intent.

Future changes require a new versioned directory, not mutation of this one.
