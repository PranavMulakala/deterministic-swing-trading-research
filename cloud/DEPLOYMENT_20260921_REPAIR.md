# September 21 operational repair

## Outcome and limits

Deployed at 2026-09-21 16:19:49 UTC (09:19:49 PDT). This repairs paper-research operations, not strategy profitability or permission to trade real money. No broker orders, account funding, credential changes, frozen strategy changes, commits, or pushes were performed.

| Component | Verified status |
|---|---|
| Collector | Active; all 14 streams caught up to their deliberate delayed watermark; no reported collection errors |
| ORB/retest and separately frozen direct-breakout challenger | Crash repaired; nine completed sessions replayed through September 18 |
| LITE $5,000/$10,000 capital arms | Included in replay; eight evaluation sessions from September 9 |
| Free $10,000 stock swing | Scheduled cycles at 16:24 and 16:29 UTC passed; the 16:34 cycle correctly BLOCKED_DATA because CIEN's IEX quote was stale; no trades in observed cycles |
| Legacy $7,500 options shadow | Timeout repaired; service completes in roughly four seconds, but still reports missing data and uses mock agents; not functioning options trading |
| Combined $10,000 options/stock runtime | Still BLOCKED_DATA: no validated provider cycle; do not confuse this with the separate working stock-only trial |
| Original ETF swing forward replay | Still BLOCKED_DAILY_DATA_PARITY: adjusted daily warm-up/forward equivalence is unverified |

## Changes

- `cloud/research_runner.py`: normalize direct-breakout prepared timestamps/numbers at the same serialization boundary as the original engine, after verifying only the intended entry-pattern differences. Publish a blocked status on TypeError instead of leaving an old successful report.
- New `cloud/free_stock_provider_v3.py`: preserve the original provider; reject closed-session decisions, crossed quotes, incomplete daily-history pagination, and prior-day session VWAP.
- New `cloud/stock_runtime_supervisor.py`: verify wall-clock freshness and matching provider/cycle identities; do not reuse a stale successful cycle. Duplicates are explicitly `NO_NEW_CYCLE`. Reject pending incomplete cycles.
- Count closed-session coverage from durable COMPLETE cycles, independently of fresh after-hours quotes. Preserve original journals and historical counters.
- Dashboard: use the new verified release pin, hide stale/failed research results, and show the separate stock trial and coverage status.
- Legacy shadow service: CPU quota 10% to 50%, timeout 20 to 120 seconds. Frozen options engine unchanged.

## Session accounting

New reporting policy `session-coverage-v1`: at least 60 valid regular-session cycles, opening and closing coverage within 15 minutes, and no intraday gap greater than 15 minutes. Assessment begins five minutes after close. It does not alter entries, exits, sizing, risk limits, past trades, or frozen experiment files.

Of the three completed stock-trial dates assessed:

- September 16: 25 regular-session cycles; partial deployment day, not qualified.
- September 17: 70 cycles; maximum gap 918.95 seconds, not qualified.
- September 18: 71 cycles; maximum gap 629.05 seconds, qualified.

Thus **one qualified session**, not zero and not three. Current review thresholds remain 30 qualified sessions and 20 closed trades; reaching them permits review only, never automatic live promotion. Monday's session is still in progress at deployment.

## Verification

- 158 authoritative application tests passed.
- 47 focused cloud/provider/supervisor/research tests passed, including the timestamp-crash reproduction and stale/replayed input, duplicate fill, pending journal, session gaps, weekend, crossed quote, truncated history, and malformed calendar cases.
- 11 dashboard Python tests and three renderer freshness checks passed.
- Frozen stock-v2 integrity verification passed locally and on the server.
- Real archived-data staged replay and deployed replay passed; all eight direct-breakout scenario ledger audits passed.
- Dashboard HTTP snapshot verified: no connection error, all 25 research pins match, indexed artifact hash matches, displayed results match the stored artifact.
- Automatic provider/runtime cycle at 16:24 UTC completed successfully after deployment; collector continued without a restart.
- Current stock evidence contains 70 daily history sessions per symbol, a 24-hour direct-news window, and a calendar receipt covering through October 1. These are bounded provider receipts, not a guarantee of complete news or earnings coverage.
- Post-deployment observation completed at 16:35:18 UTC, more than 15 minutes after cutover. The automatically scheduled research replay started at 16:34:01 and finished successfully at 16:35:07. The 16:29 stock cycle passed; the 16:34 provider rejected a stale CIEN quote and the supervisor published BLOCKED_DATA instead of replaying the old cycle. Do not interpret systemd Result=success as usable market data: this provider intentionally treats its blocked exit code as an expected service outcome.
- The collector advanced to 10,077,022 recorded rows with no reported errors/pending streams; all 14 streams reached 16:10 UTC, consistent with intentional delayed collection. Only cloud/research_runner.py differs among the old/new 25 pinned research files. Frozen stock verification still passed.

Suite counts describe their respective scopes, not a claim of exhaustive coverage or guaranteed correctness. Synthetic fill/exit tests are not evidence of actual broker execution.

## Interpretation of data

Original quote/trade ORB scenarios remain at zero trades. Three direct-breakout scenarios each show a single COHR trade with roughly $23-$24 modeled loss on their own $5,000 scenario; these are alternate simulations, not three independent live trades. Several other scenarios reject the same opportunity on cost/spread/data criteria.

Free stock swing currently remains at $10,000 simulated cash with zero closed trades. News is bounded direct-news metadata with deterministic adverse-headline checks; sector-news annotations are collected separately and are not used to select trades. This does not incorporate every external factor or constitute a trained/self-improving AI.

The free-data archive intentionally trails the market by approximately 20 minutes plus collection cadence. The separate stock provider uses fresh IEX quotes and delayed SIP daily history, not consolidated real-time executable prices. The old ETF feed-equivalence and options-provider prerequisites remain explicit blockers.

## Deployment and recovery

New cloud releases:

- `/opt/trading-research-repair-20260921`
- `/opt/agentic-stock-free-ops-v3-20260921`
- `/opt/trading-dashboard-repair-20260921`

Original releases remain intact. Database snapshots, prior research status, and original effective units are under `/var/backups/trading-repair-20260921`. The deployment uses named `90-repair-20260921.conf` drop-ins for the five changed services; see `cloud/verification/20260921/deploy_cloud.py` for exact settings. The collector and its data were not replaced.

If new repeated crashes, stale status, unexplained ledger changes, or failed pins occur: stop the affected paper timers, preserve current journals/status and logs, and investigate. An operator can move only the five named deployment drop-ins into the backup directory, daemon-reload, and restart the old services/timers. Never blindly restore a database snapshot over a journal containing newer decisions. The prior releases also retain the defects described above; rollback is containment, not a successful repair.

Read-only recheck: `python3 /var/tmp/trading-repair-20260921/verify_cloud.py` on the authenticated cloud host. The dashboard listens only on loopback port 8766.

Next external requirement: a validated fresh complete options-chain feed and verified account entitlement. Do not purchase data or enable trading merely to make a status green. The original ETF experiment needs an explicit data-equivalence decision. Neither is solved by waiting longer.

Final verdict: **operational repairs deployed and verified; continuous stock execution readiness remains conditional on quote freshness; options and original ETF forward readiness remain BLOCKED**. The stock timer will retry automatically. Do not loosen the five-minute freshness limit or remove CIEN from the frozen universe merely to force a successful cycle.
