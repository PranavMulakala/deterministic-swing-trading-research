# Stock-specific Alpaca paper guard v1 — offline preparation

Prepared September 23, 2026. This package contains **offline preparation only**.
It has no broker submit/cancel/replace method or schedule. The one-shot worker
can load explicitly supplied private runtime files but has not been invoked with
real credentials. The email request class requires an explicitly injected HTTPS opener
and was exercised only with a fake. The existing ETF adapter and frozen stock simulation rules
are unchanged. There is no approved stock strategy version, so production use
of the guard fails closed until a separate, explicit policy decision.

`guard.py` checks a proposed entry against the exact Alpaca paper endpoint,
current account and quote snapshots, an open-market observation, a non-empty approved strategy list, a
$1,000 per-entry debit cap, an independently tracked $4,000 experimental cash
allocation and no existing positions or pending orders. It ignores reported
broker buying power for sizing. It rejects stale or crossed quotes, market
hours outside regular trading, non-LITE symbols, bad quantities and duplicate
decision identifiers. This is a preliminary check, not broker enforcement:
another process, manual action, stale snapshot or concurrent order can change
account state after validation.

`alerts.py` produces **email drafts only** for observed profit target, proposed
drawdown review levels, scheduled holding reviews, LITE-tagged news and stale
price data. Its news messages retain publication and first-receipt time and
call sentiment unclassified. There is no automatic time sale, stop order,
email delivery, recipient address or timer in this module. See the separate
[owner preference and alert plan](../../output/STOCK_PAPER_ALERT_PLAN_20260923.md).

`outbox.py` holds drafts in a separate SQLite queue, deduplicates event keys,
expires stale alerts, and requires an **injected** delivery transport. It has no
default network path, recipient or credential reader. A failed/ambiguous send
can only retry with the same idempotency key before its 24-hour expiry. Unit
tests use a fake transport; no email was sent.

`resend_transport.py` prepares a stock-only Resend HTTPS request and requires
an explicit injected opener, sender, recipient and API key. The current tests
inject a fake opener. Deployment must supply a no-redirect HTTPS opener,
verify the exact recipient/sender and provider entitlement, and perform a
separately authorized delivery check. Nothing loads or copies the existing
IBKR mail credential.

`fallback.py` is a **pure, disabled-by-default** gate for a possible one-off
automatic *profit* sale if the owner later gives a precise, explicitly confirmed
instruction for a specific paper position. It requires a fresh target bid,
matching paper position and endpoint, accepted email, expired response wait,
healthy inbound-response monitor, verified lack of reply, and an unexpired
instruction. It cannot send an order. There is no configured authorization or
inbound-response monitor, so no automatic fallback is currently possible.

`read_only.py` is a separate Alpaca GET-only reader for the **paper** account,
positions, open orders and market clock, plus an explicitly requested LITE IEX
quote, bounded paginated LITE news back to a reviewed cutoff, and a bounded
trading-calendar request. It accepts
credentials only as constructor arguments; no
live request was made during preparation. The exact paper account ID must be
locked before reading other endpoints. It rejects unexpected/large responses,
redirects, stale clocks, crossed quotes and truncated order/news pages. API
errors are reduced to fixed codes, never raw responses or keys.

`monitor.py` matches a manually approved, position-specific card to the broker
asset, side and quantity before generating price/news/review drafts. It refuses
to infer a target from the backtest. An open order or partial-fill mismatch
instead yields a reconciliation warning. News needs an explicit first-seen
cutoff and remains unclassified. `pipeline.py` converts a failed broker/data
read into an operational warning draft; it has no sender or timer. An empty
paper account produces no position alerts.

`calendar.py` and `pipeline.py` derive completed holding sessions from the
read-only Alpaca calendar and reviewed entry time. A missing calendar causes a
warning, not an invented session count. Quote and news failures are isolated so
one feed can still produce alerts while the other is unavailable. Alert decision
time follows the completed read, so news received during a request is not
mistaken for future information.

`service.py` joins one read, draft evaluation and durable outbox enqueue. It
drains pending alerts even when the current read produces no new event, and
delivers only when a transport is explicitly injected. Provider acceptance is
recorded separately from actual inbox delivery and does not cause a trade. The
worker reports pending and expired-unsent alerts and exits nonzero when a
requested send fails; an external host monitor would still be required to
notify the owner if the mail channel or whole Droplet is down.

`worker.py` is an explicitly invoked, one-shot CLI. It requires paths to private
configuration and credentials. By default it performs a read-only check and
prints draft counts without creating or queueing an outbox. `--send` additionally
requires a private outbox directory and enables delivery for that invocation.
`--test-email --test-id <unique-label>` sends only one idempotent delivery-test
message through the outbox; it neither reads Alpaca nor flushes position alerts.
That command has **not** been run with a real mail route or key. A provider
receipt would still require separate inbox confirmation.
Both input files must
be owned by the invoking user and mode 0600 or stricter; the outbox directory must be
private. Email requires both `email_enabled: true` in that file and `--send`
on the invocation. No sample file contains a key, address, account ID, target or
approved card. It has no daemon loop or installed timer; the cloud is unchanged.
The exact config fields are `version: 1`, `paper_account_id`,
`email_enabled`, `sender`, `recipient`, and optional `position_card`. An approved
card must include `asset_id`, a unique `position_id` for that holding,
`quantity`, `target_price`, `opened_at`, `news_since`, and
explicitly chosen `drawdown_levels`, `review_every_sessions`, and
`explicitly_approved: true`. There are no default risk/review thresholds; the
5%/10%/20% and five-session values in earlier plans remain proposals. A
separately supplied private credentials JSON
would contain `alpaca_key_id`, `alpaca_secret_key`, and `resend_api_key` only if
mail is enabled. Do not put secret values in the repository or chat.

The September 23 focused offline suite has **53 passing tests** with fake
broker/news/email transports. It did not access Alpaca credentials, send an
email, create an order, run on the Droplet or validate inbox delivery. An
offline end-to-end fake run exercised a reviewed card, broker state, IEX quote, news,
calendar, outbox and email receipt through the one-shot worker. A live
service additionally needs a known paper account ID, reviewed recipient and
sender, delivery check, approved per-position target/card, durable deployment
state, run schedule and health monitoring. The latest owner instruction keeps
manual sale as the default; no fallback instruction exists.

Future implementation would need a paper-only order client, fill/reject/partial
fill handling, durable experimental-cash accounting, restart reconciliation,
actual email routing and delivery verification, current news and exit policy,
and explicit authorization for any paper order or schedule.
No real-money broker path belongs in this package.

September 24 update: 55 focused tests pass. The paper-only worker is installed
on the existing Droplet behind static one-shot systemd units, with credentials
provided through isolated systemd copies. A labeled email test reached the
chosen inbox, and a duplicate invocation was suppressed. GET-only paper account
and IEX/news checks succeeded at the check instant; the account held no
positions or open orders. A no-send worker run returned `no_paper_position`.
There is no position card, recurring timer, automatic sale, or broker write
path. See [the activation gate](../../output/STOCK_PAPER_ACTIVATION_GATE_20260923.md)
for the current prerequisites before any position-specific alert activation.
