# Alpaca stock-paper alert activation gate — September 23, 2026

Goal: reliable **paper-only** email alerts on a reviewed LITE position, with
manual sale by default. This is an activation checklist, not an active service,
order instruction, or request to subscribe to a data plan.

## Completed offline

- A separate GET-only Alpaca paper reader uses exact paper/data URLs and an
  explicit IEX quote request. News follows bounded pages back to a reviewed
  cutoff; uncovered gaps produce a warning rather than a completeness claim.
  It verifies the expected account before reading
  positions, orders, clock, quote or news. It has no broker write method.
- A reviewed position card must match the paper account, LITE asset, long side,
  and quantity. It must specify target, drawdown alert levels and holding-review
  interval; the example thresholds in earlier plans are not defaults. No card or
  mismatch yields a warning, not a guessed target.
- Target, drawdown, holding-review, news and health events produce drafts only.
  News is unclassified; unavailable or truncated news produces an operational
  warning without suppressing an independently verified price alert. Every
  draft links to the Alpaca paper dashboard for manual review.
- SQLite outbox deduplicates events and the one-shot service can use an explicitly
  injected HTTPS mail transport. Pending, unexpired alerts are drained even if
  the next broker read has no new event. The one-shot worker's default read-only
  check does not create or queue an outbox; an explicit `--send` flag and private
  runtime files are required for delivery. There is no default
  email route, timer, broker order client or automatic-sale instruction.
- A separate `--test-email` path sends only one named, idempotent delivery test.
  It does not read Alpaca or flush market alerts. It is prepared but unrun;
  provider acceptance and owner-inbox delivery both remain unverified.
- The worker exits nonzero on a requested send with pending/expired alerts;
  external host monitoring is still needed to detect a broken mail channel or
  an unavailable Droplet.
- Holding-review counts come from a bounded read-only Alpaca market calendar;
  failed calendar reads produce a warning instead of a guessed age.
- September 23 offline check: 53 focused tests passed with fake broker, news and
  mail responses, including a full fake worker run from position card through
  outbox receipt. This verifies code behavior against fixtures, not Alpaca access,
  inbox delivery, a paper fill or real-world signal quality.

## Inputs and validation still needed

1. **Email route.** The owner confirmed on September 23 that stock-paper alerts
   should use the existing IBKR paper-report inbox. A stock-specific sender and
   actual delivery to that inbox still need verification. No address or key
   should be pasted into a chat or written in this document.
2. **Paper account lock.** The signed-in Alpaca dashboard identified the paper
   account on September 23; place that identity in a restricted runtime
   configuration, then make a read-only account/positions/orders/clock check.
   A 3:06 p.m. New York dashboard refresh showed no positions or recent orders.
   This is still not a current API check, and the account identifier is not
   recorded in this document.
3. **Position-specific card.** After a paper LITE position exists, review its
   unique local position ID, broker asset, quantity, reviewed entry time,
   target, and first-seen news cutoff. Choose drawdown/review prompts and a
   manual broken-thesis review rule.
   No target, entry zone, or automatic sale is approved now. The historical
   10-session exit is a research assumption, not an adopted instruction.
4. **Live read and delivery drill.** Verify IEX quote freshness during the
   intended market window, news access and timestamps, provider acceptance,
   mailbox delivery, duplicate suppression, a simulated broker-read outage, and
   a stale-quote warning. IEX is one exchange, so absence of a fresh quote can
   delay an alert. Email is not a guaranteed real-time channel.
5. **Cloud operation.** The owner subsequently requested deployment and confirmed
   the existing report inbox. Activation remains pending a current pinned server
   connection, live configuration and a delivery drill. Isolate any new stock
   service from existing IBKR and frozen stock simulation services, keep
   persistent outbox data private, and check a heartbeat and restart behavior.
   An active DigitalOcean Droplet alone does not meet this gate.

September 23 access check: the pinned SSH connection timed out. The signed-in
DigitalOcean console still showed the Droplet Active and its SSH inbound firewall
limited to one source address. Clicking Web Console from the in-app browser did
not open a terminal. No firewall rule, service, credential, mail route or order
was changed. The owner was asked to open Web Console directly; activation and
inbox delivery are not verified.

Later September 23 owner evidence: while connected to Sage Wi-Fi, DigitalOcean's
console displayed **"Error: Timed out while waiting for handshake"**. The owner
clarified that the server was originally set up in California and they are now
in Atlanta; an Atlanta home connection is not the original source network and
also failed. The single existing SSH source rule is therefore insufficient for
current direct access. The console timeout may additionally involve the
Droplet agent or SSH service, so the cause is not isolated. A narrow, current
source-IP SSH rule requires the owner's explicit security-change confirmation
at the action point; no broad rule should be used. The cloud firewall remains
unchanged, and no root-password reset, reboot or recovery action was performed.

The owner chose to try a temporary Sage Wi-Fi SSH rule rather than wait for
Atlanta home access. The current Sage public IPv4 address has not been verified,
so no rule was prepared or added. The DigitalOcean firewall form defaults to
All IPv4 and All IPv6; both must be removed before any narrow single-address
rule can be saved. A read-only attempt to inspect the private DigitalOcean
account profile for a session IP was rejected by automatic approval review as
outside the firewall troubleshooting scope. No alternate account-profile route
was attempted.

The owner's Mac Wi-Fi settings showed only private Sage-network addresses, not
a usable public source for a cloud firewall rule. After the owner disconnected
VPN, a fresh pinned SSH reachability check still timed out on port 22. No
firewall change or mail activation followed.

A fresh Web Console attempt after VPN disconnection again timed out waiting for
handshake. DigitalOcean's separate Recovery Console was launched from Settings
as a read-only access attempt; no authenticated terminal was observed through
the in-app browser, and no password was entered or reset. The owner was asked
whether its separate window reached a login prompt.

The owner reached the Recovery Console's Linux login prompt, but does not know
an existing root password; two usual passwords did not work. Stop password
guesses. No root-password reset was requested or performed. Recovery Console
login remains unavailable, so the next access route is a narrowly scoped SSH
firewall rule for a verified current public source address, followed by a pinned
key-based SSH check.

A read-only [DigitalOcean overview check](PAPER_SETUP_STATUS_20260923.md)
around 12:29 p.m. New York time still showed the existing Droplet Active at an
estimated $12/month. It did not verify application processes or delivery.

There is no reason to buy the optional Alpaca consolidated-data subscription
for the current offline stage. A paid feed would be considered only after a
specific free-IEX data limitation is measured against the chosen alert need.

An automatic paper **profit** sale remains off. If the owner later chooses one
for a particular position, record and confirm the exact quantity, minimum
price, active window, email wait and verified reply channel before building an
order path. Silence after an email is insufficient by itself. Real-money
Robinhood remains entirely outside this activation gate.

## September 24 access and preparation update

The owner identified Atlanta home's Xfinity WAN IPv4 in the router app. After
reviewing the exact change, the owner approved adding a DigitalOcean inbound
**SSH TCP 22** rule scoped to that address as a `/32`. The new rule appeared in
the firewall alongside the older single-address rule. Pinned, key-based SSH
then returned a successful read-only response using the repository's recorded
host identity. No broad SSH source, password reset, reboot, broker order or
trading schedule was added.

Read-only server inventory showed no stock-alert service. Python 3.12 and
systemd 255 are available; the pre-existing Alpaca paper and IBKR report-mail
credential files exist with restricted ownership and modes. Their contents were
not read. The stock worker now has an offline-tested systemd-credential mapping
and a separate, inactive [service unit](../cloud/stock_paper_v1/README.md).
All 54 focused tests passed locally and the inactive unit passed server-side
`systemd-analyze verify`. Neither the code nor unit has been installed or run on
the server. Adding the service would give a new process use of both existing
keys; that is a pending owner security decision. No test email has been sent.

## September 24 deployment and live checks

The owner approved isolated systemd use of the existing Alpaca **paper** and
Resend keys and one labeled test email to the existing IBKR-report inbox. The
stock code and two one-shot service units are now installed on the existing
Droplet. They are static and inactive between manual invocations; **no stock
timer or recurring schedule exists**. The live alert unit has not been invoked
with `--send`. Existing IBKR and collector services and frozen strategies were
not changed.

The test unit submitted one `[PAPER STOCK] Delivery test — no market signal`
message. The provider accepted it, and it appeared in the configured inbox at
10:26 a.m. Eastern. A second run with the same test ID returned
`already_accepted` without sending a duplicate. The test path does not load
the Alpaca key or read a broker position.

A one-time GET-only Alpaca paper check found an ACTIVE account, **zero
positions** and **zero open orders**; it stored the paper account ID privately
in the root-only stock config. A separate GET-only feed check found an IEX LITE
quote aged zero seconds at the check instant and fetched 50 news items on the
first page with more pages indicated. A no-send run of the deployed worker as
its dynamic service user returned `no_paper_position`. The deployed worker hash
matched the locally tested worker; 55 focused tests passed locally with bytecode
writing disabled. These are point-in-time connectivity checks. Quote freshness
over a full market window, headline coverage, position-specific alert behavior,
host outage detection, and recurring delivery are still unverified.

The remaining activation gate is a real **paper** LITE position and a reviewed
position card with its actual broker asset/quantity, target, drawdown prompts,
holding review interval, and news cutoff. Only then can position-specific alerts
be drilled and a suitable alert schedule and health monitor selected. No order
method, automatic sale, Robinhood integration, or profit claim was added.
