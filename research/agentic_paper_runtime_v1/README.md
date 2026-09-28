# Agentic paper runtime v1

This is a scheduled, offline, paper-only lifecycle for the separately frozen
$10,000 stock-swing and $10,000 long-option accounts.  It adds deterministic
simulated fills, marks, position management, closes, accounting, session counts,
and idempotency without adding an order, broker, model, or network client.

The input contract requires one fresh stock packet for every frozen stock, one
fresh selected-contract packet for both SPY and QQQ, at least 50 point-in-time
history sessions, complete current earnings coverage, a complete current option
chain, and 24 hours of bounded raw context receipts.  Missing data is
`BLOCKED_DATA` and does not count a session.

The cloud runner may be deployed before a provider producer.  Until approved
production Tradier option data and an earnings-calendar source are connected, it
will deliberately remain blocked.  A running timer is not evidence that the
trial is active, has traded, or is profitable.

