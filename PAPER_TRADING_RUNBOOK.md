# Alpaca Paper Runbook

This runbook is intentionally gated. Completing setup does not change the `PAPER_READINESS.md` no-go verdict or authorize an order.

## Journal compatibility before using this revision

The journal remains an ordinary SQLite file with the existing schema and hash chain. This revision loads it into memory under a separate owner-only `.storage.lock` and publishes committed snapshots atomically through a pinned directory descriptor. It rejects linked paths without following them. The workflow `.lock` still serializes complete commands.

Before an owner-controlled upgrade, ensure old processes and external SQLite writers are stopped, and preserve a backup of the database and any sidecars together. Do not run old and new journal writers concurrently. A nonempty `-wal`, `-journal`, or `-shm` is rejected with an owner-controlled-checkpoint error; do not delete those files to bypass the check. Recover and checkpoint the legacy database with SQLite under owner control, close its connections, then verify the existing event chain before continuing. A fully checkpointed legacy database without pending sidecar data is compatible. No real journal migration was performed during development.

## 1. Keep credentials local

Copy `.env.example` to `.env`, restrict the file to your macOS user, and fill only the two paper-key fields. Do not paste keys into chat, commit them, reuse live keys, or add another API hostname.

```bash
cp .env.example .env
chmod 600 .env
```

The loader accepts only the two documented Alpaca paper-key variables, does not execute shell syntax from `.env`, and rejects persisted execution or kill-switch flags. The two runtime gates shown in the execution command below must be supplied inline for that one process only.

## 2. Prepare and bind the dedicated account

In Alpaca's paper dashboard, cancel all orders, close all positions, and reset the paper balance to $500. Then run:

```bash
PYTHONPATH=src python3 -m swingbot.cli paper --root . bind
```

Binding fails unless the account is ACTIVE, USD, unblocked, flat, free of working orders, and both equity and cash are within one cent of $500. The journal stores only the account ID, last four account-number characters, and measured account state—not credentials.

## 3. Open every session with reconciliation

```bash
PYTHONPATH=src python3 -m swingbot.cli paper --root . status
```

This verifies the journal hash chain and authorization tables, queries current account/position/order state, imports broker-confirmed fills using broker fill timestamps, reconciles cash against every confirmed fill, checks account/position market-value identities, checks every managed position has the exact active native stop, and latches the durable kill switch on any unexplained mismatch. It appends a point-in-time account/cash/mark/P&L snapshot and prints current marks and P&L. The 2% realized-loss halt is scaled from the first durable equity observation of that trading day; Alpaca's `last_equity` remains labeled as previous-close P&L only. A market-driven aggregate-risk percentage overrun appears as a warning and blocks additional entries without blocking an approved exit. Nothing watches after the process exits.

For continuous local polling while a terminal stays open:

```bash
PYTHONPATH=src python3 -m swingbot.cli paper --root . monitor --interval 15
```

## 4. Scan, propose, review, and separately approve one order

```bash
PYTHONPATH=src python3 -m swingbot.cli paper --root . scan
PYTHONPATH=src python3 -m swingbot.cli paper --root . propose-entry XLF
PYTHONPATH=src python3 -m swingbot.cli paper --root . review PROPOSAL_ID
```

An entry proposal is created only during regular hours from the most recent completed prior-session bar. It is rejected if the frozen signal fails, the quote is stale or wide, a position or order conflicts, the account is unreconciled, or whole-share sizing would break cash/risk limits. The review prints the ticker, side, whole-share quantity, market/GTC/OTO terms, quote and timestamp, maximum entry reference, native stop, estimated cost, planned loss, account ID suffix, thesis, invalidation, client order ID, expiration, and exact confirmation code.

Every failed public paper command appends a timestamped `paper_operation_failed` event with the operation, error type, and reason when the journal remains writable. This record is diagnostic only and cannot create authorization or authoritative broker state. Broker read or parsing failures also latch the durable kill switch when the journal is writable, even if the next response is clean. Recovery requires owner-confirmed clearing after clean reconciliation; ordinary status polling does not clear the latch.

Only after the owner explicitly approves that exact order in the current conversation, run one process-scoped submission:

```bash
SWINGBOT_PAPER_EXECUTION=I_UNDERSTAND_PAPER_ONLY \
SWINGBOT_KILL_SWITCH=0 \
PYTHONPATH=src python3 -m swingbot.cli paper --root . execute PROPOSAL_ID \
  --confirmation-code CONFIRM-XXXXXXXXXXXX \
  --session-id CURRENT_SESSION_ID
```

The enable values disappear when that process exits. The confirmation expires after 120 seconds and can be consumed once. It is bound to the exact latest review event and that review's side-appropriate quote, so a stale, superseded, or changed proposal requires a new review and approval. Submission completes asset and state requests, re-queries account, positions, orders and quote, then samples the broker clock last. The resulting permit expires at the earliest proposal-expiry, quote-age, or regular-session boundary and is checked after JSON preparation and permit claiming, after HTTPS connection setup, and before each HTTP header/body write. A monotonic clock preserves a conservative broker-time bound across local or broker clock regressions; the last two seconds of the deadline are reserved for clock uncertainty. Local checks cannot guarantee remote arrival time or eliminate arbitrary process suspension. A consumed permit is never retried after an uncertain transmission.

`maximum_entry_reference` is a local pre-submit guard, not a broker limit price. A market order can fill worse after submission. Reconciliation measures risk again from the actual fill and latches the kill switch if the observed fill exceeds the approved risk ceiling. A stop can also fill below its stop price during a gap or fast market.

Immediately run `paper status` or keep `paper monitor` running until the parent fill and active child stop reconcile.

## 5. Ordinary exits

The native protective stop is already authorized with the entry and can trigger at the broker. Recovery and time exits never self-submit.

```bash
PYTHONPATH=src python3 -m swingbot.cli paper --root . propose-exit XLF --reason auto
```

Review and execute the resulting proposal using the same one-order process. The review restates the exact protective-stop order ID and price that will be canceled. Immediately before the sell, the workflow requests cancellation, polls that exact order up to five times at 250 ms intervals, and proceeds only after a canceled/expired terminal state with zero fill evidence. It then re-queries account and position quantity and samples the broker clock last before allowing the sell. A partially filled, filled, changed, or unconfirmed stop blocks the sell and latches the kill switch. Exits are rejected during the final 60 seconds of the regular session before any stop is canceled. Both the broker adapter's process-local capability and the journal's durable verified-cancellation stage block the sell until every check succeeds. If cancellation, journaling, or the sell outcome is uncertain, the kill switch latches and automatic retry is forbidden.

For an owner-directed exit, use `--reason manual_owner_exit`; it still needs a fresh proposal and confirmation.

## 6. Recovery and kill-switch procedure

Never rerun an order command after a timeout or connection loss. Query the broker by running `paper status`; client order IDs are used to recover an exact already-accepted request after a restart. If the journal shows that submission authority was consumed but no single exact broker order can be found, the state remains unresolved, the kill switch latches, and retry is forbidden.

The runtime kill switch blocks new submissions but does not cancel broker-native stops. Resolve the broker discrepancy first. Only after `paper status` is clean may the owner clear the durable latch:

```bash
PYTHONPATH=src python3 -m swingbot.cli paper --root . clear-kill \
  --confirmation CLEAR-PAPER-KILL-SWITCH
```

If a position is unprotected, use Alpaca's paper UI to restore protection or close it. Because that manual activity is intentionally unknown to the journal, ordinary reconciliation must remain failed. Cancel every remaining order, close every position, reset both paper cash and equity to $500, and explicitly terminate the broken run with:

```bash
PYTHONPATH=src python3 -m swingbot.cli paper --root . reset-run \
  --confirmation REBASELINE-PAPER-RUN-AT-CLEAN-500
```

This command is accepted only while the durable kill switch is latched, against the same bound paper account, and after the broker is flat, has no working orders, and reports both cash and equity within one cent of $500. It appends a rebaseline event instead of deleting history, invalidates every prior proposal and permit, clears prior operational positions/orders from the new run, and restarts the paper-observation gate from zero. Do not delete or edit the SQLite journal to force a pass.

The application cannot protect credentials from another process running as the same macOS user. Keep the computer account and `.env` private; the in-application approval gate is not an operating-system security boundary.

Broker HTTP requests explicitly ignore `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY`. The journal, lock, and generated status dashboard use owner-only permissions; sensitive paths refuse symbolic links. Order reconciliation paginates the Alpaca history rather than silently truncating at 500 parent orders.
