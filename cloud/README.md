# Personal cloud collection — installation record

> **September 22, 2026 orientation:** See the [current project handoff](../output/PROJECT_HANDOFF_20260922.md) for all experiments, updated broker/cloud status, LITE opening-dip evidence, and the Claude review prompt. The dated material below retains its original scope; it is not a current status report for every project track. Frozen strategies and historical evidence are unchanged.


Update: the separate scheduled research loop is installed. See
[RESEARCH_OPERATIONS.md](RESEARCH_OPERATIONS.md) for current capabilities, times,
validation, and limits. The initial installation history below predates that update.

Installed on personal DigitalOcean server `198.211.113.234`, Ubuntu/Python 3.12.
Status at activation: **running and boot-enabled**, started September 8, 2026
06:11 UTC after the owner confirmed fresh credentials and authorized transferring
exactly the two paper secrets over pinned SSH. Secret values were not displayed.
11 collector/archive tests passed locally; the initial 10 passed on server;
158 existing application tests passed locally in the installation turn with
`PYTHONPATH=src`. No frozen research files were edited. No commit/push.

The separate `smoke-20260904` archive contains 31,105 provider records from
September 4, 13:35–13:40 UTC (inclusive endpoint): 120 bars, 14,511 quotes,
16,473 trades, and one news item. All 12 streams completed without API errors.
All 12 smoke response hashes and SQLite integrity passed. It is NOT forward
strategy evidence and is not mixed into the main archive.

Manual service restart succeeded (PID changed 9187 → 9519). Main-archive
checkpoints advanced afterward, remained contiguous, and the latest 200 page
hashes and SQLite integrity passed. At 06:14 UTC the main archive was still
catching up through closed-market hours, with zero market/news records and no
API errors. Do not confuse successful empty-window polling with market records.

## What this service does

The standalone `/opt/trading-collector/collector.py` requests only HTTPS GETs from
`data.alpaca.markets`. No broker client, orders, strategy logic, or LLM is deployed.
13 independent streams now collect 1-minute and provider 5-minute raw SIP bars for the frozen 15 ETFs plus
LITE/COHR/CIEN/FN/AAOI; individual SIP quotes and trades for those five stocks;
and symbol-filtered Alpaca news metadata (not article bodies or all internet news).

Collection starts at September 8, 2026 00:00 UTC. Five-minute windows end at least
20 minutes before wall-clock time. Each stream resumes its last fully committed
window; failed pagination rolls back the whole window. The process runs all day,
including empty market-closed windows. This is delayed archival collection, not
a real-time arrival feed. Requests are paced; no paid feed upgrade is performed.

The SQLite archive records compressed original response pages, SHA-256 checksums,
request window, stream, page number, receipt timestamp, and record counts. Inclusive
API window boundaries can repeat a record in adjacent windows: readers must
deduplicate appropriately, not count raw records as distinct trades/news events.
News may contain revised articles; receipt time does not establish original
publication-time availability. SIP bars are raw, not dividend-adjusted; historical
warmup, official daily bars, corporate actions and strategy-specific replay adapters
are still needed before forward performance comparisons. Missing bars are not filled.

## Activate (server terminal, root)

Rotate any chat-exposed Alpaca paper credentials first. Never place secrets in a
command argument, chat, repository, or screenshot.

```sh
python3 /opt/trading-collector/set_credentials.py
systemctl start trading-collector
systemctl status trading-collector --no-pager
journalctl -u trading-collector -n 20 --no-pager
```

The credential helper uses hidden prompts and writes only the two values to
`/etc/trading-collector/credentials.json` with root ownership, service-group read,
and mode 0640. Prefix checking is a sanity check, not proof of account permissions.
Do not copy the repository .env wholesale. Credential rotation/transfer requires
owner confirmation. Service reads credentials once; restart after any rotation.

## Health and storage

```sh
cat /var/lib/trading-collector/health.json
systemctl is-enabled trading-collector
systemctl is-active trading-collector
df -h /
du -sh /var/lib/trading-collector
```

An active process is not sufficient: check all 13 stream checkpoints, errors,
and increasing records during active sessions. Large checkpoint lag means a
backlog or failed stream, not successful current capture. `health.json` updates
between cycles and cannot report during a stuck cycle. There is no external
notification channel yet. A 5 GiB free-disk reserve pauses new collection; no
automatic data deletion is performed. Large full-tick collections will eventually
need an off-server archive or more disk. No off-server backup is configured.
Use SQLite's backup API rather than copying a live WAL database alone.

Service settings: automatic boot, restart on failure after 30 seconds, no login
shell for service user, read-only system/home protection, 768 MiB RAM maximum,
50% of one CPU. Credentials gate startup. No extra inbound ports are needed.
Keep SSH restricted to the owner's IP; outbound HTTPS/DNS must remain available.

## Stop / rollback

```sh
systemctl disable --now trading-collector
```

This stops collection and future boot startup without deleting any data. It does
not stop DigitalOcean billing. Stop on unexpected endpoint access or unexplained
archive corruption; investigate repeated errors or growing lag. After credentials
are activated, verify received data, checkpoint recovery through service restart,
and at least 15 minutes of logs. API access, market-hours sample storage, and
manual-restart checkpoint recovery have been verified. Full-machine reboot,
failure-triggered auto-restart, a full 15-minute observation period, and sustained
market-open load have **not** been verified at this handoff. SIP historical and
one news sample succeeded; this does not establish comprehensive news coverage.

## Not installed

This initial deployment does not run the paper autopilot, strategy simulations,
scheduled historical test suites, sentiment scoring, dashboards, or real orders.
Those require separate integration with the archive; existing historical results
remain unchanged and do not establish a profitable strategy.

Sources: https://docs.alpaca.markets/us/reference/stockbars and
https://docs.alpaca.markets/us/reference/news-3 .
