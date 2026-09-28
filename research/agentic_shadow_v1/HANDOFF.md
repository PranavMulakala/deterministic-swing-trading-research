# $7,500 shadow experiment handoff — September 14, 2026

- **Local software: READY** for offline fixture research and fail-closed normalized-input processing. Real-data integration is not certified.
- **Cloud shadow session: BLOCKED.** No deployment or scheduled cloud run was verified.
- **Real-money options: NOT AUTHORIZED.** No orders, funding, permission changes, subscriptions, paid model calls, commits or pushes.

## Delivered

Everything added is under `research/agentic_shadow_v1/`:

| Files | Purpose |
|---|---|
| `config.json`, `PROTOCOL.md`, `FREEZE.json` | Frozen $7,500 hypothesis, $75 trade risk, $150 daily pause, $375 drawdown pause |
| `engine.py` | Three alternative ledgers, deterministic validation/sizing/exits, mock proposal validation, durable intents, fills, marks, pauses and DNE expiry |
| `fixtures.py`, `test_shadow.py` | Synthetic scenarios and 38 regression tests |
| `run.py`, `report.py` | JSON inbox runner, missing-input management, readable JSON/HTML reports |
| `learning.py` | Evidence-linked suggestions only; no active-rule rewrite or promotion |
| `probe_data.py` | Bounded GET-only OPRA capability probe using existing credential loader; not in runtime bundle |
| `deployment/`, `release/` | Isolated systemd service/timer, refusing-overwrite installer, minimal hashed bundle |
| `results/fixture-demo/` | Four synthetic observations and one simulated round trip per arm |
| `evidence/` | Tests, preservation comparison, data/access blockers, bundle replay evidence |
| `README.md`, this file | Schema, operation, assumptions, commands and next steps |

Reused the existing `swingbot.safe_paths` utility, standard-library integer-money /
SQLite approach, and personal credential loader. Did not install OpenBB,
TradingAgents, Fincept, QuantDinger or any new dependency.

The three demo arms deliberately agree because their model responses are mocked.
The tests separately exercise analyst abstention/critic veto and reject agent
quantity, price, symbol and risk overrides. The synthetic demo's P&L is purely an
arithmetic example. No market returns were evaluated or used to retune the frozen
hypothesis. Expiry/loss handling and all observed-price claims remain simulated.

## Verification

**370 tests passed:** 38 new shadow tests, 158 existing application tests,
140 relevant LITE/ORB research tests, and 34 existing cloud tests. Existing cloud
tests use fixtures; they do not establish today's server health.

New tests include exact-cent entry/exit accounting and risk boundaries; stale,
missing, malformed and future information; duplicate IDs and conflicting chain
records; restart recovery, transaction rollback and concurrent duplicate writers;
fractional fill rejection for indivisible one-contract sizing; unfilled exits;
expiry DNE lapse; unknown marks; agent authority rejection; immutable suggestions;
and an end-to-end seven-loss sequence proving daily and drawdown pauses while
exit management continues. This is targeted verification, not exhaustive auditing.

The final staged bundle independently replayed the demo with exactly matching
arm states and decision history. Release integrity verification and shell syntax
checks pass. Linux systemd controls are prepared but **not tested on the server**.
No visual/browser certification is claimed for the HTML report.

**All 2,006 pre-existing inventoried files remain byte-identical**, including the
existing source/tests, cloud/research/dashboard files, configurations and frozen
artifacts in the snapshot. `.env` was not edited; its contents are excluded from
the preservation manifest. Existing dirty/untracked work was retained.

## Exact revision

Deployed revision: **NONE**.

Prepared release SHA-256 (content manifest identity):
`33e7f3be86448d7d6ccf0c6f17d4e3afe1b2a930e1cd25f7f33c01605bbeeaa8`

`release/RELEASE.json` lists each bundled file hash. This is an uncommitted local
release identity, not a Git commit or an installed cloud revision.

## Current external dependencies

1. **Trusted personal SSH identity:** the documented server `198.211.113.234`
   answers SSH, but `/private/tmp/trading-cloud-verified-host` no longer exists and
   there is no trusted key for this host in `~/.ssh/known_hosts`. A strict SSH
   attempt failed with “No ED25519 host key is known.” No remote command executed.
   Obtain the fingerprint from the owner's DigitalOcean console or a trusted
   known-hosts file; do not accept an unverified network key. The user has been
   asked for this information. No current collector health claim is possible.
2. **Usable real options evidence:** the existing collector source only archives
   stock bars/quotes/trades and news, not options. The OPRA probe stopped because
   the existing `_load_env` rejects an unrelated key in the expanded local `.env`.
   It made **no HTTP request**; entitlement is unknown, not denied. The existing
   loader and `.env` were left unchanged. Use an existing approved scoped
   credential source or explicitly supplied process credentials to retry the
   read-only probe. Never bypass validation by treating a partial load as success.
3. **Complete packet producer:** no authenticated producer currently supplies the
   required complete, timestamped options chain, genuine bid/ask/size, contract
   metadata/open interest/volume, underlying bars/quotes, calendar/event coverage
   and news receipt history into the isolated inbox. Raw provider responses also
   need retention outside the normalized ledger. Normalization self-hashes are
   not source authentication. Alpaca's indicative feed modifies quotes and is
   explicitly rejected; no paid upgrade was requested or performed.
4. **Real model comparison:** no approved programmatic model budget was verified.
   The three-arm software comparison works with mock responses. An actual analyst
   efficacy study requires separately budgeted, point-in-time model outputs; none
   are claimed here.

## Next steps

After host identity is verified, inspect personal server resources and collector
PID/checkpoints/source hashes. Only deploy the new service if isolation and tests
hold. Provide authentic options packets, verify a timer-triggered run and report
freshness, then recheck collector invariants before calling the cloud session
READY. The prepared service deliberately has no network, credentials or collector
access and will report BLOCKED if input is absent. No public ports are added.

A successful process, mock-filled trade or passing fixture does not satisfy that
data gate. No profitability, live execution or unattended model-readiness claim.

## Commands

Run from the personal repository root:

```sh
PYTHONPATH=src:. .venv/bin/python -m unittest research.agentic_shadow_v1.test_shadow -v
PYTHONPATH=src:. .venv/bin/python -m unittest discover -s tests -q
PYTHONPATH=src:. .venv/bin/python -m unittest discover -s cloud -q
PYTHONPATH=src:. .venv/bin/python -m unittest research.orb_comparison_v1.test_data research.orb_comparison_v1.test_engine research.orb_quote_v2.test_quote_replay research.lite_execution_data.test_followup research.lite_reversal_v1.test_experiment research.lite_capital_diagnostic_v1.test_run research.lite_2026.test_profile -q
PYTHONPATH=src:. .venv/bin/python -m research.agentic_shadow_v1.run --demo --state research/agentic_shadow_v1/results/fixture-demo
python3 research/agentic_shadow_v1/release/verify_release.py
```

Fixture report: `results/fixture-demo/report.html`; full immutable event journal:
`results/fixture-demo/ledger.sqlite`. Repeat demo runs are idempotent. The report
has the last 20 decisions; the ledger retains the entire packet/decision history.
