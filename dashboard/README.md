# Research Desk

## Private hosted deployment - September 8, 2026

The dashboard is now hosted on the existing personal server as
`trading-dashboard.service`. It starts at boot and reads local research files
without SSH keys or broker credentials. It binds only to server loopback.

On this Mac, double-click `Open Hosted Dashboard.command`, then open
http://127.0.0.1:8766. Keep that SSH tunnel terminal open while viewing.
The server continues running when the Mac sleeps; viewing resumes after reconnecting.
No public website, new public port, paid service or brokerage connection was added.

The deployed bundle is `/opt/trading-dashboard-20260908`. Its `MANIFEST.json`
records all deployed file hashes. The local research catalog is an explicitly
dated snapshot; live market and forward-research artifacts refresh automatically.
The two new Reddit-inspired tracks are drafts with no active collection or orders.

The original local-only alternative is documented below.

A private dashboard for this personal research project. It reads the existing
cloud collector and research artifacts over fingerprint-pinned SSH. It does not
place orders, run strategies, read broker credentials, change the cloud, or alter
frozen source files. No external dependencies or frontend build are needed.

## Open and run

Open http://127.0.0.1:8766 while the dashboard process is running.

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m dashboard.server
```

Or double-click `Run Dashboard.command` on this Mac. Leave its terminal running.
Stop the local dashboard with Ctrl-C. This does not stop cloud collection.
The dashboard is available only on this Mac; it stops updating when the Mac
sleeps, loses connectivity, or the local process exits. This local-only alternative has no launch-at-login job. The separate hosted
service above starts on the personal server at boot.

The default key path is `~/.ssh/personal_trading_cloud`. The private key is used
only by the local SSH client and is never sent to the browser or server script.
The public host record in ignored `state/known_hosts` must match the fingerprint
confirmed by the owner on September 8, 2026:
`SHA256:fy4i90RRjUZAz1pCNrkMDqFlKL1cydddD3ub5rlw7MI`.
If that file is missing, restore verified public host material; do not disable
strict host checking. No automatic trust-on-first-use is performed.

## What the four views mean

- **Overview:** current collection health, slowest stream checkpoint, completed
  replay sessions, strategy scope and stock prices. An absent result is not zero.
- **Stocks & ETFs:** all 20 collected symbols, searchable by name or ticker;
  completed 1-minute and provider 5-minute close charts; missing bar counts;
  latest delayed quote/trade observations for the five stocks; related news.
  Price change is from the regular-session opening bar, not prior-day close.
- **Strategies:** eight ORB A/B cost/delay scenarios, four LITE scenarios,
  closed trades, exits, rejected decisions, unresolved/open positions, daily
  ledgers, recorded ledger audits, uncertainty, news timing and reviewer output.
  The older bar model is explicitly separate. ETF swing remains blocked.
- **Data & evidence:** all 13 streams, errors, backlog, storage, loaded services,
  references, source hashes, artifact/index consistency, original research notes
  for every local research directory, and frozen historical ORB results.

The server refreshes from SSH once per 60 seconds after each completed read.
The browser reads that shared snapshot every 15 seconds; “Refresh view” reloads
that snapshot without launching additional SSH jobs. Market collection is
intentionally 20–25 minutes delayed. Strategy results are cumulative completed-
session replays, not live intraday positions or separate daily deposits.

A failed read retains the last successful snapshot and shows an error. A snapshot
or health report older than 150 seconds is labeled stale. Research result metrics
are hidden when pinned-code or artifact/index verification fails. Unresolved ORB
ending equity/return remains unknown. The LITE engine does not expose a `complete`
field; its ledger validation and session exclusions are shown instead.

The dashboard verifies hashes of displayed session bar/news pages, latest sampled
nonempty tick pages, pinned deployed files and reference/artifact files. It does
not re-audit the entire archive or independently replay fills each minute. Hash
agreement is not proof of complete provider coverage. News is metadata, never a
sentiment score or a confirmed explanation for a move. Historical notes retain
their original dates and may describe outdated deployment state.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest dashboard.test_dashboard -v
node --check dashboard/static/app.js
```

`test_ui.cjs` accepts a synthetic snapshot JSON as its argument. It checks waiting,
complete, unresolved, tampered and stale states plus navigation, escaping and
missing-opening-bar handling. Keep synthetic snapshots separate from live data;
the running dashboard has no fixture mode or synthetic fallback.

The optional WebMCP read/navigation tools are feature-detected. Their contracts
were tested with a stub registry; an actual supported WebMCP browser context and
visual browser QA were not tested. Core navigation does not depend on WebMCP.

HTTP serves only exact allowlisted routes and research notes. It binds only to
127.0.0.1, rejects foreign Host/Origin and cross-site requests, disables caching,
and offers no mutation API. There is no directory listing or filesystem browser.
The current reader uses the already authorized personal SSH account. A future
hosted version would need a separately authorized deployment and private access.
