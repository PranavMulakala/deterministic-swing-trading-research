# Alpaca Paper Runbook

This runbook is intentionally gated. Completing setup does not change the `PAPER_READINESS.md` no-go verdict or authorize an order.

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

Binding fails unless the account is ACTIVE, USD, unblocked, flat, free of working orders, and within one cent of $500. The journal stores only the account ID, last four account-number characters, and measured account state—not credentials.

## 3. Open every session with reconciliation

```bash
PYTHONPATH=src python3 -m swingbot.cli paper --root . status
```

This verifies the journal hash chain and authorization tables, queries current account/position/order state, imports broker-confirmed fills using broker fill timestamps, checks every managed position has the exact active native stop, and latches the durable kill switch on any mismatch. It appends a point-in-time account/cash/mark/P&L snapshot and prints current marks and P&L. Nothing watches after the process exits.

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

Only after the owner explicitly approves that exact order in the current conversation, run one process-scoped submission:

```bash
SWINGBOT_PAPER_EXECUTION=I_UNDERSTAND_PAPER_ONLY \
SWINGBOT_KILL_SWITCH=0 \
PYTHONPATH=src python3 -m swingbot.cli paper --root . execute PROPOSAL_ID \
  --confirmation-code CONFIRM-XXXXXXXXXXXX \
  --session-id CURRENT_SESSION_ID
```

The enable values disappear when that process exits. The confirmation expires after 120 seconds and can be consumed once. It is bound to the exact latest review event and that review's side-appropriate quote, so a stale, superseded, or changed proposal requires a new review and approval. Submission re-queries account, positions, orders, clock, asset, and quote.

`maximum_entry_reference` is a local pre-submit guard, not a broker limit price. A market order can fill worse after submission. Reconciliation measures risk again from the actual fill and latches the kill switch if the observed fill exceeds the approved risk ceiling. A stop can also fill below its stop price during a gap or fast market.

Immediately run `paper status` or keep `paper monitor` running until the parent fill and active child stop reconcile.

## 5. Ordinary exits

The native protective stop is already authorized with the entry and can trigger at the broker. Recovery and time exits never self-submit.

```bash
PYTHONPATH=src python3 -m swingbot.cli paper --root . propose-exit XLF --reason auto
```

Review and execute the resulting proposal using the same one-order process. Immediately before the sell, the workflow cancels the existing native stop and re-fetches that exact order to confirm the approved stop is canceled or expired. Both the broker adapter's process-local capability and the journal's durable verified-cancellation stage block the sell until that succeeds. If cancellation, journaling, or the sell outcome is uncertain, the kill switch latches and automatic retry is forbidden.

For an owner-directed exit, use `--reason manual_owner_exit`; it still needs a fresh proposal and confirmation.

## 6. Recovery and kill-switch procedure

Never rerun an order command after a timeout or connection loss. Query the broker by running `paper status`; client order IDs are used to recover an exact already-accepted request after a restart. If the journal shows that submission authority was consumed but no single exact broker order can be found, the state remains unresolved, the kill switch latches, and retry is forbidden.

The runtime kill switch blocks new submissions but does not cancel broker-native stops. Resolve the broker discrepancy first. Only after `paper status` is clean may the owner clear the durable latch:

```bash
PYTHONPATH=src python3 -m swingbot.cli paper --root . clear-kill \
  --confirmation CLEAR-PAPER-KILL-SWITCH
```

If a position is unprotected, use Alpaca's paper UI to restore protection or close it, then reconcile. Do not delete or edit the SQLite journal to force a pass.

The application cannot protect credentials from another process running as the same macOS user. Keep the computer account and `.env` private; the in-application approval gate is not an operating-system security boundary.
