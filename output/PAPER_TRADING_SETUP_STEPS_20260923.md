# Step-by-step stock paper setup — September 23, 2026

This checklist is a project status, not an order authorization or a trading
schedule. It keeps the existing Robinhood real-money account, Alpaca paper
account, DigitalOcean server and IBKR MNQ paper project separate.

The exact [stock-paper alert activation gate](STOCK_PAPER_ACTIVATION_GATE_20260923.md)
lists what the offline build has verified and what an active service would still
need.

| Step | Status | Evidence and next condition |
|---|---|---|
| 1. Use existing accounts and host | DONE for access check | [Alpaca Paper Trading and DigitalOcean status](PAPER_SETUP_STATUS_20260923.md): $7,500 simulated cash, $30,000 paper buying power ignored for sizing, no positions or recent orders; existing active $12/month server. Application health was not verified from the host UI. No new server or paid feed needed. |
| 2. Compare plausible stock entries with funded capital | DONE as exploratory offline work | [September 23 funded comparison](LITE_FUNDED_COMPARISON_20260923.md): five price-only LITE cases, cash and buy-hold controls, 30 cost/deadline cases, tests and independent accounting checks. Strong positive LITE sample but no demonstrated timing edge over LITE buy-and-hold. No historical news edge test. |
| 3. Choose the exact paper-only behavior | DEFAULT EXIT PREFERENCE CLARIFIED; ENTRY/EXIT DETAILS STILL OPEN | The owner's latest September 23 correction is **email first, manual sell by default**. No fixed-time sale or automatic stop order. A future one-off automatic profit sale needs explicit position-specific advance authorization; silence alone is insufficient. [Alert plan](STOCK_PAPER_ALERT_PLAN_20260923.md). Entry/target/news and manual broken-thesis rules still need a versioned decision. The 10-session/3% comparison values remain research assumptions. |
| 4. Build stock-specific Alpaca paper order and alert lifecycle | OFFLINE READ-ONLY ALERT WORKER PREPARED; ORDER CLIENT NOT BUILT | [Paper preflight and alert components](../research/alpaca_stock_paper_v1/README.md) now include a separate GET-only Alpaca paper reader, exact account/position/order matching, IEX quote and bounded paginated news retrieval, official-session holding reviews, read-failure warning drafts, one-shot private-config worker, durable outbox and a fake-tested Resend HTTPS request. Its default read-only check does not queue alerts; `--send` explicitly enables delivery and outbox use. A separate idempotent test-email command cannot flush market alerts or access Alpaca. The worker reports undelivered/expired alerts and exits nonzero after a failed requested send. Target alerts require an approved position card; pending orders and mismatches generate reconciliation notices. The September 23 focused offline suite has 53 passing tests, including a complete fake card-to-email worker run. No account ID, sender/recipient/key or inbound reply monitor is configured; no live broker read, email, order, or cloud deployment occurred. Partial-fill/order lifecycle, durable experimental cash ledger, restart reconciliation, delivery verification and audit log still need implementation. The original ETF broker adapter is not this implementation. |
| 5. Run a bounded paper operational check | NOT STARTED | Requires explicit paper-order authorization; earlier instructions prohibited orders and previews. Measure actual paper submit/ack/fill/reconcile behavior and feed divergence. Paper does not prove live fills or profit. |
| 6. Consider unattended cloud schedule | NOT STARTED | Requires separate authorization after step 5, current server health check, deployment review, monitoring/alert routing and failure drill. An active Droplet is not an active stock order runner. |
| 7. Real-money Robinhood decision | NOT STARTED | Separate explicit authorization and current account/settlement/positions/orders/capital-control verification. The $4,000 loss tolerance and written allocation plan are not broker-enforced. |

Do not buy the optional $99/month real-time consolidated feed just to speed the
current work. The free IEX feed differs from historical SIP signals; resolve
the exact strategy/data need first. Paper account buying power is larger than
simulated cash and must never be treated as the spending limit.
