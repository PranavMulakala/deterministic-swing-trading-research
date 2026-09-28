# September 9 research-session readiness

Final verdict: **READY — September 9 delayed-data research session.**
Verified September 9 at 06:48:28 UTC (September 8, 23:48 Pacific).
Real-money/broker execution remains **NO-GO**.

Scope: delayed-data LITE/ORB research and expanded sector-news collection, not
broker execution, profitability, ETF swing readiness, or the separate MNQ work.

## Reviewed release

All 190 uncommitted files present at the pre-deployment snapshot were inventoried
and hashed in `verification/20260909/uncommitted-inventory.json`. Git reports the
entire cloud/research/dashboard trees as untracked, so a normal Git diff is not
a sufficient release review. Actual deployable changes were compared against
copies of the running cloud release and reviewed before cutover. Historical data,
audit exports, MNQ work, new-track drafts and scratch files were preserved and
excluded from executable deployment. This is not a new independent audit of every
historical research artifact or excluded project.

Reviewed fixes include missing-forward-day handling, defining the parent LITE
config even when a parent session is incomplete, nonempty sector-news parsing,
premarket coverage, receipt-time cutoffs, unknown-not-neutral news states, invalid
checkpoint/health handling, and dashboard support for the new arms/source pins.

Release pins: `d2cf583908999e85a66868212fb832a67007e469d5d2922c6522afe66a4a512b`.
Archive SHA-256: `d5207a289ce82fe4853deb33e0d061c82e4dfd6b344ba6ee8668d38adc116b9b`.
See `SEPTEMBER9_FREEZE.md` and `verification/20260909/RELEASE.json`.

## Tests and preservation

- 390 unique Python tests passed: 158 application, 144 existing LITE/ORB research,
  34 cloud, 11 dashboard, and 43 separate MNQ tests. MNQ passing does not deploy it.
- 20 JavaScript renderer contracts passed. HTTP tests exercised loopback access,
  forbidden paths, cross-origin rejection and read-only routes. These are not a
  full visual/browser compatibility audit; WebMCP used a registry stub.
- The exact staged Linux cloud suite passed all 34 tests. A full synthetic
  September 9 archive exercised the eight capital arms, missing inputs, timestamps,
  ledger validation and identical repeat results. Synthetic data is never forward
  market evidence.
- An additional roughly $900/share synthetic fixture produced a valid fill and
  passing ledger in every capital/style/cost combination, with whole shares,
  entry debit within cash and planned risk within 0.5% of capital. The existing
  tests also retain cost-based rejections and gap losses beyond planned risk.
- All 17 protected historical ORB hashes matched. All tracked files were unchanged.
  Of 16 initial cloud pins, 13 are byte-identical (all parent engines/configs,
  the learning reviewer and warmup); only three orchestration/configuration files
  changed. Four new pinned files make 20 current pins.
- Staged replay reproduced every September 8 ORB, LITE, ledger, preparation and
  bar-diagnostic result section exactly. Both original immutable artifacts remain
  byte-identical. The larger LITE arms correctly contain no September 8 results.

## Deployment evidence

Cutover completed September 9 at 06:32:27 UTC (September 8, 23:32 Pacific).
Research root: `/opt/trading-research-v2-20260909`.
Dashboard root: `/opt/trading-dashboard-20260909`.
Previous roots remain intact. Collector code was replaced atomically after a
brief controlled stop; existing archive checkpoints were retained.

SQLite online backups and old service/code files are under
`/var/backups/trading-readiness-20260909`, accessible only to root. The backup passed
SQLite integrity checks. A full archive probe verified all 4,780 pages then
present (1,359,755 raw records), not just a sample, and proved all 4,706
pre-deployment pages remained byte-identical. Later collection adds more pages.

The Linux isolation probe confirmed no researcher network access, inaccessible
credential storage and a read-only collector archive. The loaded production unit
retains these controls. The dashboard listens only on `127.0.0.1:8766`; no public
web listener/firewall rule was added. Both its artifact and source checks passed.
Calendar/corporate-action refresh succeeded after cutover and confirms September
9 regular hours of 09:30–16:00 America/New_York.

Final acceptance passed: all 14 streams were complete through 06:25 UTC, a
23-minute-27-second lag at the final read (within the 30-minute gate). No pending
streams or collector errors; 45.2 GiB free. The unattended timer fired at
06:47:27 UTC and exited successfully at 06:47:28, after a full 15-minute deployment
observation. Both direct and scheduled readiness checks returned READY with no
reasons. Collector and dashboard had zero restarts. The dashboard's 06:47:32
snapshot contained that exact 06:47:27 research report and its verified artifact.

The new scheduled run ID is
`4992845fcba2f0e8c08e12374dd5c7407269dd615c7ffb39f0d63d8c4fdfa9ed`,
identical to the independent staging replay with the refreshed references. Every
parent result section still matches September 8; the journal retains one distinct
completed-session date, not extra evidence from repeated checks. The sector stream
had 77 committed pages and three raw news records, from September 9 00:00 UTC,
with honest first receipt at 06:32:25 UTC. At final health read, all streams held
4,822 pages and 1,359,756 raw records (these counts continue changing).
Evidence snapshots are retained under `verification/20260909/`.

## Exactly what will run

- LITE: $5,000 and $10,000 separate cumulative whole-share portfolios from
  September 9, each with dip/VWAP-retest and 10/25-bps cost scenarios. The original
  $500 comparison remains separate. These are five-minute-bar simulations, not
  quote-level evidence of executable fills.
- ORB: unchanged $5,000 A/B portfolios at both frozen cost/delay settings, with
  quote/trade execution replay and a separately labeled bar diagnostic.
- Collection: original 13 streams plus `sector_news`, covering 13 additional
  frozen peer/customer/supplier/networking symbols. Real news metadata has been
  received. First receipt is recorded honestly even for overnight backfill.
  News is context only; no sentiment-based rule or stock-selection change.
- Automatic collection continues when the owner's Mac is asleep. Evaluations
  occur after official close plus at least 20 minutes and complete inputs,
  ordinarily around 13:20–13:40 Pacific, later if backlogged. No intraday simulated
  positions or brokerage orders are produced by this release.

## Limits and rollback

No profitability claim, broker orders, risk-rule edits, paid feed upgrade, Git
commit/push, automatic strategy promotion or unattended LLM training occurred.
ETF swing remains blocked on adjusted daily-data parity. Off-server backups,
external alerts, full-machine reboot recovery and sustained future market-hours
load are not established by this release. Boot/restart configuration is verified,
not a guarantee that the cloud or data provider cannot fail.

If persistent collection errors, source-integrity failures or unexpected execution
appear, stop the research timer and investigate. Restore the saved collector code
and two service units from the backup, reload systemd, then restart the old
collector/research/dashboard configuration. Never restore an old database over the
newer live archive or delete newer pages. The versioned release archive and the
exact deployment/staging/probe scripts are retained with the verification record.
