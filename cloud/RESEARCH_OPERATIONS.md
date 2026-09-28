# Automated research loop — operating guide

September 9 release: versioned source root `/opt/trading-research-v2-20260909`;
pin manifest `d2cf583908999e85a66868212fb832a67007e469d5d2922c6522afe66a4a512b`.
See `SEPTEMBER9_FREEZE.md` for the prospective scope and
`READINESS_20260909.md` for the final deployment verdict and measured checks.
The earlier deployment observations at the end of this guide are historical.
The read-only dashboard is loopback-only at port 8766, with its own service;
no public web firewall rule is required.

## What is installed

Personal server `198.211.113.234` now has:

| Component | Schedule | Purpose |
|---|---|---|
| trading-collector.service | continuous | Delayed SIP 1/5-minute bars for 20 symbols, five-stock quotes/trades, direct and prospective context-news metadata |
| trading-references.timer | every 6 hours | Provider calendar and corporate-action snapshots, read-only API requests |
| trading-research.timer | every 15 minutes | Offline simulated-trade replays and evidence review |

This is a **simulation and research system, not broker paper execution**. It makes
no orders. No unattended paid LLM runs or model training are configured.
The deterministic reviewer stores outcomes and evidence, compares existing arms,
and proposes further prospective research; it does not rewrite its own code.

The research unit starts at boot through its enabled timer. The collector restarts
on failure. A research job failure does not stop collection; the next timer retries.
No external failure alert channel or off-server backup is configured.

## When results appear

The observation interval is September 8–December 31, 2026. A session is evaluated
only after its official close plus at least 20 minutes and complete archive
coverage. At a normal 16:00 Eastern close, expect a check around 16:20–16:40 Eastern
(13:20–13:40 Pacific), potentially later if data is backlogged. Before then the
service reports waiting; this version does not display live intraday simulated
positions. The timers run even while the owner's Mac is off.

Reports re-evaluate the cumulative forward interval from the same original
capital. They are not separate daily deposits or new independent samples.
Repeated identical runs have the same run ID and do not add evidence. Reference
snapshot changes produce separately retained revisions, not extra market sessions.
Unresolved positions remain unresolved and the frozen engines stop later portfolio
replays. Inspect each ledger's `complete` field; a completed report is not a claim
that every diagnostic execution model resolved.

## Strategy coverage

* ORB: original selection/entry/risk logic, $5,000 per separate simulated portfolio,
  arms A/B, 1/2-second delay, 10/25-bps scenarios, frozen tick execution and ledger
  audit. The old one-minute execution model is retained as a separate diagnostic.
* LITE: original dip and VWAP-retest rules, original $500 capital and whole-share
  mode, 10/25-bps scenarios. **SIP/raw input is a separately labeled data version**,
  not the original IEX/dividend-adjusted experiment. Incomplete session coverage
  blocks the LITE comparison rather than treating excluded days as cash returns.
  Separate $5,000 and $10,000 whole-share capital arms begin September 9 and reuse
  the exact entry, exit, sizing formula, risk percentage, and cost rules. They are
  hypothetical and not broker-ready.
* ETF swing: explicitly `BLOCKED_DAILY_DATA_PARITY`. It does not have a verified
  adjusted daily forward/warmup adapter; no ETF P&L is fabricated.
* News: metadata/availability annotations only. Articles collected after a signal
  cannot inform that signal. Missing coverage is unknown, never neutral sentiment.
  The original direct stream remains unchanged. A separately versioned context
  stream begins September 9 for 13 frozen peer/customer/supplier/networking symbols;
  it does not alter selection and is not comprehensive news or sentiment analysis.

Prices remain provider-finalized delayed data. This does not test actual live
receipt latency, broker fills, queue position, or profitability. The prior frozen
results remain NOT_ESTABLISHED; the new future interval is not used to tune rules.

## What the reviewer can do

It records cumulative outcomes, zero-trade and unresolved-execution findings,
and A/B net-return contrasts. With fewer than 20 sessions or 20 closed trades per
arm it reports insufficient evidence. Meeting those thresholds only permits an
evaluation proposal—not approval. Paired uncertainty and both costs are retained;
a separate future freeze and concentration review would be needed for a new rule.

Automatic promotion and risk edits are disabled. The proposal memory is not
retraining an LLM, and writing a lesson is not evidence of improved performance.
Our durable goal is measurable evidence, not "always gets better".

## Check status (server terminal)

```sh
systemctl is-active trading-collector
systemctl list-timers trading-research.timer trading-references.timer --no-pager
cat /var/lib/trading-collector/health.json
cat /var/lib/trading-research/latest.json
journalctl -u trading-research -n 10 --no-pager
python3 /opt/trading-collector/check_archive.py /var/lib/trading-collector
df -h /
```

Always inspect `checked_at`, the timer's last result, stream checkpoints, and
errors; a stale successful report is not evidence a newer job succeeded.
`latest.json.session_readiness.status` must be
`READY_FOR_DELAYED_RESEARCH_SESSION`; it checks all 14 streams, a maximum
30-minute checkpoint lag, no recorded collector errors, and at least 5 GiB free.

Artifacts: `/var/lib/trading-research/runs/<run-id>.json` contains complete source
provenance, simulations, ledger audits, decisions/rejections, and the review.
`memory.sqlite` indexes unique runs/proposals. Source code and warmup are pinned
by the active versioned source root above. The preserved initial root is
`/opt/trading-research-v1/PINS.json` (initial pin-manifest SHA-256:
`251ff7786da9fb96d4e64a61c7afc9886cd640f24b69921bbacef7221798b7f2`).

## Stop / rollback

To stop only research and metadata refresh, preserving the collector and all data:

```sh
systemctl disable --now trading-research.timer trading-references.timer
systemctl stop trading-research.service trading-references.service
```

To stop collection too: `systemctl disable --now trading-collector`.
None of these stop cloud billing or delete data. Do not copy an active WAL SQLite
database alone; use SQLite backup. The synthetic smoke archive under
`/var/lib/trading-research/fixture` is intentionally separate from real observations.

## Verification at deployment

* 158 existing application tests and 144 existing research tests passed.
* 11 collector/archive tests and 9 new research-loop tests passed locally.
* Full Linux synthetic pipeline passed: 8 tick ORB + 4 LITE scenarios, plus the
  4 bar-proxy diagnostics; ledger audits and repeated-run idempotency tested locally.
* Linux sandbox probe: credentials inaccessible, no outbound network, source
  archive read-only. The actual live WAL archive was independently readable and
  its recent 200 page hashes and contiguous checkpoints passed verification.
* Actual provider calendar: 128 sessions; latest 20 warmup sessions matched exactly.
  Corporate-action schema parsed successfully for all five ORB stocks.
* Updated 13-stream collector passed 11 tests on the server. At 07:27 UTC all
  streams were caught up through 07:05 UTC, with no errors. A separately labeled
  historical smoke sample returned 31,145 records across all 13 streams, including
  the added provider five-minute feed; it is not forward strategy evidence.
* All 17 previously pinned ORB result/source hashes were unchanged.
* No Git commit/push, broker order, paid data upgrade, or LLM subscription purchase.
* The unattended timer fired at 07:31:21 UTC (00:31 Pacific), updated `latest.json`,
  and exited successfully. This was an actual timer trigger, not a manual start.
  The collector remained active and the isolation write probe left no archive file.
  The initial research deployment was observed through its first 15-minute repeat.

Not established: sustained market-hours performance, strategy profitability,
full-machine reboot recovery, external notifications/backups, daily ETF parity,
or live brokerage execution. Tick memory is capped at 500,000 selected rows per
session and the research process at 1,000 MiB; oversized jobs fail instead of
silently sampling quotes/trades. Resource limits may need revisiting after real load.
