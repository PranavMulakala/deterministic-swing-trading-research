# Stock paper holding and email-alert plan — September 23, 2026

Owner clarification: a stock position should **not be sold automatically just
because a fixed number of sessions passed**. A profit target may take months.
The owner expects to be active during market hours and wants timely notification
about price, news and sentiment so they can review and act. This does **not**
approve holding a broken thesis forever, automatic loss exits, a particular
profit target, or any paper/real order. No alert service or stock broker runner
was activated by this document.

Later September 23 clarification supersedes the owner's brief "sell
automatically" response: **email first, owner decides by default**. A one-off
automatic profit sale could be considered only if the owner explicitly opts in
for that exact paper position in advance, with a recorded target, maximum
quantity, response deadline, order-price rule and expiration. A casual reminder
to the assistant, a missed email, or silence alone does not create permission.
There is currently no verified inbound-response monitor or authorized fallback.
For a future paper-only exception, record the exact position, maximum shares,
minimum acceptable sale price, active window, time to wait after the email,
expiration, and how a reply is detected. The owner should review and confirm
that record before the window starts. If delivery or response status is unknown,
the exception fails closed to email/manual review. A limit sale can remain
unfilled even after its price condition is observed; broker order/fill state
must be reconciled separately.

The earlier ten-session hard exit was only a research assumption in the
[funded comparison](LITE_FUNDED_COMPARISON_20260923.md) and a separate proposed
capital-plan default. Its historical numbers stay intact; **it is not adopted
for the proposed paper workflow**. The existing frozen 21/42/126-session stock
swing rules also remain a different strategy.

## Proposed notification behavior, not yet active

| Trigger | Proposed message | Trading action |
|---|---|---|
| Position reaches its predeclared profit target on a fresh observed bid | Prompt review/exit with price, source and timestamp | **Email first; manual sale by default.** A separate, explicit per-position fallback would be needed for any automatic profit sale; an email is not a fill. |
| First fall through each configured drawdown level, e.g. 5%, 10% or 20% | Show marked loss, position cost, thesis and review prompt; deduplicate each threshold per position | **No stop order and no automatic sale** |
| New LITE-tagged company news, earnings/guidance or material event | Include source, publication and receipt time, headline and link; mark sentiment **unclassified** until reviewed | Manual thesis review; unknown news is not positive or neutral |
| Still held at each 5-session review interval, including 20/40/60 sessions | Ask whether the original thesis, target and capital use still make sense | Reminder only; **no maximum time exit** |
| Paper order/fill/reject, stale quote/feed, disconnected broker, or missed research heartbeat | Immediate operational notice with state and required inspection | Block new entries on uncertainty; reconcile any open position manually |

Use short event emails plus one end-of-day status when there is an open paper
position, rather than a message on every price tick. Deduplicate events in a
durable outbox. Price and news notifications should say **PAPER ONLY** and
include symbol, position ID, observed time, feed, trigger, and a direct review
link; never include an API key or full account number. The program should
record receipt and sending outcomes separately. Email may be delayed, filtered,
or missed; lack of an email must never be treated as a safe position state.

The existing [IBKR paper operations](../cloud/ibkr_paper_v1/READINESS.md) used
Resend's HTTPS API and verified a scheduled email in Gmail on September 21.
That is a separate MNQ service, not a stock-alert service, and its current
credentials/delivery status have not been refreshed. Reuse the delivery pattern
with a separate stock outbox and scope only after verifying the sender,
recipient and provider status; do not copy secrets between packages. DigitalOcean
[blocks outbound SMTP ports 25, 465 and 587](https://docs.digitalocean.com/support/why-is-smtp-blocked/),
so direct SMTP from the Droplet is not the intended path. DigitalOcean's
[free resource alerts](https://docs.digitalocean.com/products/monitoring/how-to/manage-alerts/)
can separately watch host metrics; they do not understand a LITE thesis or
guarantee the stock application is healthy.

What remains: select exact per-position target and alert thresholds, connect
the alert evaluator to current paper positions and point-in-time news, connect
and verify the stock-specific outbox to an actual email transport, perform one authorized test
email, then consider a schedule. The earlier authorization explicitly excluded
deployments and new trading schedules; no email or alert has been sent or enabled.

Later September 23 update: the owner explicitly requested deployment and chose
the same inbox as the existing IBKR paper reports for stock-paper alerts. This
resolves the destination choice, not delivery validation or position-specific
trading rules. The pinned server connection timed out, and the in-app DigitalOcean
Web Console did not open a terminal. The Alpaca paper dashboard still showed no
positions or recent orders at 3:06 p.m. New York time. No stock alert service,
test email, order, or schedule has been activated as of this update.
