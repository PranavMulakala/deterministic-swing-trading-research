# Verification of the owner-authorized paper fixes

These changes were prepared on top of `35b570c3958b061ed4ce34fe37cc4172b4ce19a3`, after its independent audit found five major and two minor defects. The owner explicitly authorized implementing those fixes. Initial checkout status contained only the pre-existing untracked `outputs/independent-audit-959b050/`; that directory was left alone.

**Implementation result: all seven reproduced defects and one follow-up reconciliation defect addressed; 150 tests pass. Operational result: NO-GO remains.** The original seven fixes were verified by their implementing agent. A separate Codex review reproduced that suite and the frozen outputs, found the follow-up defect R8, and verified its regression after correction. This is still not a fresh read-only certification of the eventual exact commit or a promise of bug-free code. No credential access, actual `.env` access, Alpaca account endpoint, or real order operation occurred.

## Reproduced defects and fixes

| Defect from the `35b570c` re-audit | Verification of the changed code | Current evidence |
|---|---|---|
| R1, major: late transport after serialization/claim and clock skew | Expiry during JSON encoding blocks transport. Expiry during TLS setup produces zero HTTP writes. Expiry after headers blocks the body. Local/broker clock regression cannot extend the deadline; exact equality expires. A delayed journal check cannot claim expired authority. Valid HTTPS preparation still succeeds with exactly one claim. | `src/swingbot/alpaca_paper.py:52`, `:158`, `:239`, `:605`; `src/swingbot/paper_journal.py:639`; `tests/test_paper_reaudit.py:41`, `:64`, `:111`, `:344` |
| R2, major: stop could predate an entry imported earlier | Entry at +4s and stop at +3s latches on every poll and never records a close. Ordinary approved exits use the same causal check. Valid +4/+6s and equal +4/+4s entry/stop times still import exactly one entry and one close. | `src/swingbot/paper_reconcile.py:671`; `tests/test_paper_reaudit.py:260`, `:316` |
| R3, major: valid fills during snapshot reads falsely latched | A coherent zero-P&L round trip at +4/+4.5s during order retrieval uses the subsequent +5s broker clock. Status, scan, reconciliation, and owner clearing stay clean and idempotent. Genuinely future fills still fail. | `src/swingbot/paper_workflow.py:883`; `tests/test_paper_reaudit.py:284` |
| R4, major: malformed broker reads did not durably latch | Real adapter parsing of an invalid timestamp, nonnumeric quantity, or missing symbol now latches before the error propagates. Restoring a clean broker response does not permit the outstanding reviewed entry to execute. | `src/swingbot/paper_workflow.py:1253`; `tests/test_paper_reaudit.py:224` |
| R5, major: working stop accepted partial/future fill evidence | Working child orders reject partial quantity, future time, price-only evidence, NaN, and empty ID. Working parent/exit acknowledgements also reject a non-null average fill price. Acknowledgement failure latches. | `src/swingbot/paper_workflow.py:1068`, `:1142`; `tests/test_paper_reaudit.py:150`, `:248` |
| R6, minor: directory substitution raced symlink checks | Ancestor swaps just before descriptor chmod cannot redirect journal, lock, or dashboard writes. A leaf swapped between checking and opening cannot be read or chmodded through the link. Target contents and modes stay unchanged. Root-owned macOS compatibility aliases remain accepted. | `src/swingbot/safe_paths.py:61`, `:84`, `:107`; `src/swingbot/paper_journal.py:50`; `tests/test_paper_reaudit.py:385`, `:417` |
| R7, minor: stale PDT documentation | Removed the current-PDT-simulation assertion and distinguished the older versioned guide from the current paper guide and July 6, 2026 account-schema changelog. No owner-account behavior is inferred from the schema change. | `PAPER_READINESS.md:17`; [current paper guide](https://docs.alpaca.markets/us/docs/paper-trading), [official changelog](https://docs.alpaca.markets/us/changelog/2026-07-06-pdt-db49dba) |
| R8, follow-up major: later reconciliation accepted a working child stop with contradictory partial-fill evidence | The common reconciliation validator now requires partial quantity to agree with a `partially_filled` status and complete price/time evidence. A child reported as `new` with a partial quantity latches and cannot be treated as valid protection. | `src/swingbot/paper_reconcile.py:836`; `tests/test_paper_reaudit.py:172` |

The original F1–F5/N1–N2 probes were rerun separately from the new regression tests. F1 slow preflight, serialization, claim, local-lag, and exit-cutoff counterexamples now produce no late mutation call. F2 accepts fills at +1s and exactly +2s against an acknowledgement clock of +2s, while +3s fails and latches. F3 malformed data and N1 malformed/non-progressing pagination remain rejected. F4's complete round trip produces cash `498.71`, realized P&L `-1.29`, one entry, one close, a flat position, and no latch after four reconciliations. F5 accepts the signed one-cent boundary and rejects `+0.010001` and `-0.010001` differences. N2 static links and dynamic replacement probes leave target files and permissions unchanged.

## Tests, storage compatibility, and frozen reproduction

The complete suite reports exactly:

```text
Ran 150 tests in 4.719s

OK
```

There were no skips, failures, or errors. All 26 source modules and 20 test/support files in the tested copy were subsequently compared byte-for-byte with the source checkout. The 18 new regression tests include a real urllib handler with a fake socket, later-poll contradictory child-fill evidence, and preservation of the original operation error through filesystem/lock cleanup; no real broker socket is opened.

SQLite's Python API cannot safely address a database relative to a pinned directory descriptor on macOS. The new journal therefore loads an ordinary SQLite file under a separate storage lock, executes transactions in memory, and publishes complete snapshots by descriptor-relative atomic rename. Three competing processes retained all 24 unique committed events and a valid hash chain. Injected failure before publication preserved the old database; injected failure after publication recovered the committed event exactly once. A synthetic legacy WAL database with pending sidecar data was refused without changing database/WAL bytes. After owner-style checkpoint and connection closure, it reopened with exactly the original events and accepted a new event. The runbook describes the upgrade boundary; no active owner journal was opened or migrated. Snapshot memory and I/O scale with journal size; this is not a production load benchmark.

Two complete historical reproductions generated the same 21 v1 artifacts, byte-identical to `ba1232e`. All 41 protected data/configuration/preregistration/artifact files matched both the source checkout and the reproduced copy. No frozen strategy rule, protected data, configuration, preregistration, or v1 artifact changed.

| Ending equity from $500 | In sample | Out of sample |
|---|---:|---:|
| Frozen strategy | 762.48760914 | 680.48031652 |
| SPY benchmark | 2017.98330179 | 1099.84843136 |
| Momentum benchmark | 1234.56921595 | 793.04974055 |

An independent calculation matched every published benchmark curve value at eight decimal places: 3,776 in-sample rows and 1,421 out-of-sample rows per benchmark, maximum difference `0.0`. All 45 indicator-prefix checks passed. The post-hoc whole-share diagnostic remains OOS equity `587.29064967`, 395 trades, 713 zero-quantity rejections out of 1,108 attempts, and maximum drawdown `3.82387953%`. It is still not a preregistered result.

SHA-256 anchors:

- `config/strategy_v1.json`: `215d907b4d87f009d461a59fe3ff060a424cf00020fc77f2d6dfcdf138c7bd27`
- `data/pinned/manifest.json`: `46bae3cff594fdb2b5cd0e03007f77b0b30919f4347833d58b05b74457e91b68`
- `outputs/v1/artifact_hashes.json`: `c1230221198a0b80deb4bdf84dd208f053cee5518c678fe305182cb66e1a0ead`

## Bright-line checks and limits

| Handoff condition | Observed result |
|---|---|
| No route to live-money submission | Passed constructor/config/path/redirect/proxy and architecture checks. Network-capable imports remain confined to the two approved adapters. The new HTTP connection uses the same fixed paper host and verified TLS defaults. |
| Fresh, exact, one-use approval and both runtime gates | Passed the tested preparation/write boundaries, expiry equality, clock regression, reuse, mutation, superseded review, missing session, and concurrent claim cases. No finite client-side test proves remote arrival timing or excludes arbitrary suspension after the last check. |
| No fractional swing entry | Passed adapter/workflow rejection and cash/risk sizing checks. |
| Matching persistent native stop | Passed valid GTC/OTO cases; missing, mismatched, held-after-fill, stop-limit, and inconsistent fill evidence reject. |
| Broker fill required for local open/close | Passed pending, partial, complete, causal ordering, restart, and repeated-poll cases. |
| No unexplained cash/market-value mismatch beyond tolerance | Passed cash-ledger, account/position identity, cost-basis boundary, and round-trip probes. |
| Unexplained account/order/position state latches | Passed malformed parsing, typed invalid state, duplicates, regressions, partial fills, and cancellation uncertainty. The durable latch is best-effort if storage itself is unwritable; submission still fails closed. |
| Frozen results and conclusions unchanged | Passed all 41 protected-file comparisons and both reproductions. |

No remaining reproduced R1–R8 software defect is known within these tested boundaries. This does not certify arbitrary broker behavior, OS scheduling, transactional consistency across separate REST endpoints, same-user hostile code, wholesale journal replacement, or future market behavior. The journal hash chain is not an externally signed audit anchor. Local pre-write checks cannot guarantee remote arrival time; an uncertain transmission remains one-use and cannot be retried automatically.

Operational **NO-GO** persists: fractional/GTC incompatibility, session approval versus next-open execution, and IEX versus pinned Yahoo signal equivalence remain unresolved. Owner account identity, balance, permissions, exact order acceptance, native-stop lifecycle, cancellation latency, restart/reconciliation, and the longitudinal paper gates remain unobserved. The frozen preregistration's abandonment rule for repeated unresolved audit defects was not changed or waived; these fixes do not retroactively erase the earlier findings or authorize continuation of v1.

## Commands and raw evidence

Initial isolation used `git archive HEAD` into a disposable directory, followed by copying only the changed source/tests from the working tree. No branch operation or fetch was used. The effective command environment for every test/probe was:

```sh
env -i PATH=/usr/bin:/bin \
  TMPDIR=/private/tmp/swing-fixes.I7xNXp/tmp \
  PYTHONDONTWRITEBYTECODE=1 \
  make -C /private/tmp/swing-fixes.I7xNXp/current test \
  PYTHON=/Users/pranavmulakala/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
```

Using that Python 3.12.14 runtime and the same clean environment, the following ran in the disposable copy with `PYTHONPATH=src`:

```text
python -m swingbot.cli reproduce --root .                 # twice
python -m swingbot.cli analyze-paper-constraint --root .
python ../economics.py /private/tmp/swing-fixes.I7xNXp/current
python ../probes.py /private/tmp/swing-fixes.I7xNXp/current
python ../breadth.py /private/tmp/swing-fixes.I7xNXp/current
python ../exits.py /private/tmp/swing-fixes.I7xNXp/current
python ../refinements.py /private/tmp/swing-fixes.I7xNXp/current
python ../final-probes.py /private/tmp/swing-fixes.I7xNXp/current
```

Those five probe scripts produced 213 top-level result groups, with additional matrices inside groups. Results were inspected individually; that number is not an assertion or coverage count. Raw scripts and results remain under `/private/tmp/swing-fixes.I7xNXp/`, with logs in `evidence/`. `evidence/final-verification.json` contains all protected-file hashes, source/test hashes, exact HEAD, and empty mismatch lists. `git diff --check` passed. The original audit's comparison evidence against `959b050` and `35b570c` remains separate under `/private/tmp/swing-reaudit-35b570c.SoObWu/`; it was not rewritten to describe the fixed tree.
