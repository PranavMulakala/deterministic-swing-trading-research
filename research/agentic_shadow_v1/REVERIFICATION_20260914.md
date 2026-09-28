# Independent re-verification and isolated deployment

Checked September 14, 2026, through 20:19:35 UTC (13:19 Pacific).
This supersedes the initial HANDOFF.md readiness/revision claims. The original
release, demo ledger, frozen configuration and hypothesis remain preserved.

## Verdict

- **Local software: READY** for the tested fixture and fail-closed research workflow.
- **Cloud scheduler: READY and deployed.** Five timer-triggered observations were verified; latest completed at 20:19:34 UTC.
- **Cloud shadow session with real market data: BLOCKED.** Existing personal credentials received HTTP 403 for the real OPRA options-data request. No complete, authenticated input-packet producer exists yet.
- **Real-money options: NOT AUTHORIZED.** No orders, funding, subscriptions, account-permission changes, model API usage or Git pushes occurred.

The service runs, but it currently records missing-input/BLOCKED observations.
There are no cloud trades or agent-performance results. The models remain mocks,
as requested until an API budget is verified. A consumer subscription was not
assumed to authorize programmatic model spending.

No finite test run proves everything correct. This review found defects missed by
the original 38 tests; the original claim of readiness applied too narrowly to its
fixtures to establish unattended operation. The corrected release has the measured
scope below, not a blanket 100% certification or evidence of trading profitability.

## Fresh findings and fixes

| Finding | Correction / evidence |
|---|---|
| A revised early session close was ignored at fill and for open exposure | Use the earlier verified close at fill; only tighten existing position deadlines. Fresh regressions reproduce both paths. |
| Exit simulation accepted an after-hours quote without checking the session | Every simulated fill now needs a verified open session; pending exits remain unresolved otherwise. |
| Malformed provenance could escape the observed runner's safe rejection path | Validate provenance container/field types and reject cleanly; report/management continue on a missing-input observation. |
| False/empty malformed proposal containers silently selected default acceptance | Only a dictionary or explicit None is accepted. |
| A failed existing credential load could leave partial keys for a later retry | Restore every allowed process key in a finally block; a mocked double-failure test proves zero requests on retry. No existing loader or .env edit. |
| Reports and steps retained the whole decoded history | Stream integrity verification and aggregate reports while retaining only 20 decision summaries. A 15,600-record small-fixture report used 54,668 peak traced Python bytes and 1.448 seconds with tracing enabled. This is not a full-options-chain load test. |
| Dynamic systemd state paths and restrictive staging permissions were incompatible with safe file access | Use the real private StateDirectory path and readable immutable code permissions, retaining the existing no-symlink checks. Actual timer runs pass on Linux. |
| Release checker did not recompute the manifest's revision | Recompute manifest identity and reject absolute/parent-traversing member paths. |

The new adversarial file has eight tests, including bearish long-put selection and
agent abstention independence. Before fixes it produced seven failed assertions
(including subtests) and two errors. Logs retain the exact before/after evidence.

## Verification performed

- **378 unique local tests passed:** 46 shadow, 158 existing application,
  140 relevant LITE/ORB and 34 existing cloud tests.
- **46 shadow tests also passed on the personal Linux server.** These repeat
  the shadow suite; do not add them again to the unique-test count.
- The exact hashed bundle passed an independent Linux offline demo and repeated
  release-integrity checks before installation.
- **All 2,006 previously inventoried files outside this new experiment are
  byte-identical.** Existing dirty/untracked work and frozen artifacts remain.
- The reviewed source uses a new ledger directory; old ledgers stay tied to their
  original engine revision. No historical ledger was migrated or rewritten.
- Actual loaded service settings include a dynamic non-root identity, no network,
  AF_UNIX only, read-only system/home restrictions, inaccessible collector paths,
  128 MiB memory ceiling and 10% CPU ceiling.
- An independent transient probe with the same relevant restrictions confirmed
  non-root execution, blocked Internet sockets, denied collector-credential access
  and denied collector-archive access. No secret content was read or printed.
- First timer run: trigger 20:17:14 UTC, exit 20:17:17 UTC, status 0. Subsequent
  verified trigger: 20:19:30 UTC, exit 20:19:34 UTC, status 0; five observations.
- Collector PID stayed **74726**, restart count **0**, code checksum stayed
  `a07051763a0f696ef3f510c8f39dfa1b734f8ce4e4407021a9b83df576162f4a`.
  No pending streams or collector errors. Its checkpoints advanced from 19:50 to
  19:55 UTC while verification ran. No existing service was stopped or restarted.

Not established: real options coverage/normalization, full-chain sustained load,
real model efficacy, whole-machine reboot behavior, external failure alerts, or a
profitable edge. Data/model costs beyond this credentialed GET are unverified.

## Deployed revision and paths

Content-manifest revision:
`0337a4f4917a7a71734b0d77652a9e402d8f8a9e1435d91d88faf744e05b91a3`

- Local bundle: `release-reviewed-20260914/`.
- Personal cloud code: `/opt/trading-shadow-7500-v1-0337a4f4917a7a71734b0d77652a9e402d8f8a9e1435d91d88faf744e05b91a3`.
- Units: `trading-shadow-7500.service` and `trading-shadow-7500.timer`.
- Durable state/report: `/var/lib/private/trading-shadow-7500/`.
- Read-only input dependency: `/var/lib/trading-shadow-7500-inbox/packet.json`.
- Cloud data/collection credentials are not included in the release or accessible
  to the simulation service. No network fetcher or public listener is installed.

SSH access was recovered from the exact previously owner-verified public host key,
then checked against the current server using StrictHostKeyChecking=yes. No new
unknown key was accepted. The public key is now preserved in
`deployment/personal-cloud-known-hosts` so a deleted temporary file does not repeat
the blocker. It contains no private credential. The historical record had matched
this fingerprint to the owner's console before the earlier deployment.

## What still prevents a real shadow session

1. An authorized genuine options-quote feed. The existing cloud loader works, but
   the OPRA request returns **403**. The provider request/error code are recorded
   in `evidence/reverification-20260914/remote-data-probe.json`; no subscription or
   permission change was made. A provider/body-specific cause beyond 403 was not
   inferred. Indicative/modified quotes are not a substitute.
2. A verified read-only producer supplying complete sourced contract, quote,
   underlying, calendar/event and news packets with honest receipt timestamps and
   raw-response retention. The old collector contains no options stream and was
   intentionally not modified. Test this pipeline and realistic packet load before
   changing the real-data verdict.
3. For an actual AI-effectiveness comparison, an explicitly budgeted model API.
   Mock responses remain valid for software tests but cannot measure analyst skill.

## Reproduce / inspect / stop

From the personal repository root:

```sh
PYTHONPATH=src:. .venv/bin/python -m unittest research.agentic_shadow_v1.test_shadow research.agentic_shadow_v1.test_adversarial -v
PYTHONPATH=src:. .venv/bin/python -m research.agentic_shadow_v1.run --demo --state research/agentic_shadow_v1/results/reviewed-fixture-demo
python3 research/agentic_shadow_v1/release-reviewed-20260914/verify_release.py
```

Via the verified personal SSH connection, inspection is read-only:

```sh
systemctl show trading-shadow-7500.timer -p LastTriggerUSec -p ActiveState
systemctl show trading-shadow-7500.service -p Result -p ExecMainStatus
cat /var/lib/private/trading-shadow-7500/report.json
```

To stop only this new schedule, preserve all state and existing collector services:

```sh
systemctl disable --now trading-shadow-7500.timer
systemctl stop trading-shadow-7500.service
```

Evidence, including captured cloud reports, is in
`evidence/reverification-20260914/`. The HTML cloud report is a captured snapshot,
not a live dashboard. The old HANDOFF and initial release remain historical.
