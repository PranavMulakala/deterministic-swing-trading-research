# $7,500 agentic options shadow experiment

Isolated alternative portfolios: deterministic, mock analyst, mock analyst plus
critic. Every arm starts at **$7,500**. No broker orders or model API calls exist
in the runtime bundle. This is research software, not a demonstrated trading edge.
See [REVERIFICATION_20260914.md](REVERIFICATION_20260914.md) for current verified readiness, deployed revision and unresolved data dependencies.

From the repository root:

```sh
PYTHONPATH=src:. .venv/bin/python -m unittest research.agentic_shadow_v1.test_shadow -v
PYTHONPATH=src:. .venv/bin/python -m research.agentic_shadow_v1.run --demo --state research/agentic_shadow_v1/results/reviewed-fixture-demo
PYTHONPATH=src:. .venv/bin/python -m research.agentic_shadow_v1.run --kind observed --state research/agentic_shadow_v1/results/observed --input /path/to/packet.json
```

The demo is SYNTHETIC, reproducible, and idempotent. Each state directory owns its
SQLite ledger and JSON/HTML reports. The ledger binds the exact engine checksum,
frozen protocol/config, and evidence kind. Never reuse an old state directory for
changed code: preserve it and start a distinctly labeled software version.
Missing/stale/malformed observed input records a blocked observation and still
manages existing positions' deadlines. The service has no data fetcher; its inbox
is a read-only dependency. A successful scheduled process can report BLOCKED.

## Inputs and proposal boundary

`fixtures.packet()` is the executable schema example; **do not relabel it as real
data**. Export JSON with `json.dumps([packet])`. The observed runner accepts one
current packet per invocation (<=60 seconds old); the ledger refuses synthetic or
indicative sources. Multiple symbols use distinct increasing observation times;
quotes for an open position must continue arriving even while screening another
symbol. All three arms share one packet hash, ordered candidate selection,
execution costs, and independent capital. Their displayed liquidity is
counterfactual, not three allocations against a shared market order book.

Required normalized fields are `event_id`, `kind`, `observed_at`, `symbol`,
`calendar`, `events`, `news`, `underlying`, three completed `bars`, and `chain`.
Each sourced object contains `provenance` with nonempty `source`/`feed`, timezone
aware `published_at`/`received_at`, retained normalized `raw`, and its canonical
SHA-256. A producer must retain original provider responses separately and map
provider publication/revision/receipt times honestly. These self-reported hashes
prove internal consistency, not provider authenticity. No provider adapter or
complete observed packet was verified in this implementation.

The chain includes explicit completeness, exact OCC identity, right, strike in
mills, multiplier, adjustment/style/currency, date and sourced `expiry_at`, open
interest and current volume, plus timestamped option bid/ask in cents and sizes in
contracts. No prices are inferred from underlying bars. Calendar and event
coverage cannot be replaced with defaults. News may be explicitly complete and
empty; missing coverage is not neutral news. The strict supplied-data contract
intentionally produces no trades when these facts are unavailable.

`Ledger.step(packet, proposals={...})` accepts mock analyst/critic scorecards.
`mock_proposal()` documents the exact schema. Rejected fields include quantity,
price and risk overrides. Defaults are mock acceptance for plumbing comparisons;
custom mock abstention/veto illustrates divergence. Mock agents demonstrate no
financial intelligence. Any real model integration needs a verified existing
budget or approval for new paid usage. It is not enabled here.

`learning.propose(ledger, directory, text, event_ids)` appends a separate proposal
with references to existing decisions. The engine never reads this archive and
has no promotion pathway. Preserve v1 when evaluating changes.

## Accounting and operational limits

Integer cents avoid floating-point money errors. The entry risk check reserves
both entry and exit fees. Clarification to the frozen prose's valuation floor:
the *option recovery price* floors at zero; the reserved exit fee remains a
separate liability in the conservative risk mark. Thus an unknown/zero recovery
can have risk value -$0.65. It is never presented as a negative option quote.
This is conservative accounting, not a change to entry signals or the $75 limit.

Entry intent is committed in one transaction; only a later event can fill it.
Each new event atomically records outcomes for earlier intents and new decisions.
Crash rollback exposes either the whole event or none. Replays are idempotent;
conflicting duplicates and backward time are rejected. SQLite serializes writers,
and the append-only journal has a verified hash chain. This does not defeat a
privileged operator rewriting an entire database and its metadata; preserve
external evidence copies for independent auditing.

Only one whole contract is allowed, so valid partial entry quantities are zero or
one. Fractional reported size is rejected; an unfilled exit remains pending.
Quotes and displayed size are assumptions about potential fills, not actual
execution. Option expiry time is sourced, not inferred from stock bars. A missed
exit expires via explicitly simulated DNE at zero, with an operational breach and
unknown forfeited intrinsic. No actual DNE instruction or exercise exists.

Unknown marks use worst-case recovery for risk, with `mark_cents: null` in reports.
Risk thresholds may be exceeded before the next observation. They do not protect
real money or stop management of open exposure. No fresh observations means no
claimed up-to-date P&L. Reports show last observation, source presence, decisions,
positions, fees, realized/unrealized P&L, risk equity, drawdown and rejections.

## Deployment

```sh
python3 research/agentic_shadow_v1/deployment/build.py /private/tmp/shadow7500-release
python3 /private/tmp/shadow7500-release/verify_release.py
```

The allowlisted bundle contains only this engine/runner/fixtures/report, frozen
rules, and the existing `swingbot.safe_paths` utility and package initializer.
It excludes the data probe, credentials, model clients, broker adapters and old
research engines. A credential-free network-isolated systemd oneshot runs every
30 seconds in a dedicated dynamic identity and state directory, with 128 MiB RAM
and 10% CPU limits. It cannot access the existing collector's data or credentials.
No public listener or firewall change is needed. A separate approved producer
must atomically publish authentic packets into its read-only inbox.

After verifying personal host identity, tests, resources, release checksums and
existing collector state, copy the bundle to a new staging directory and run
`sh install.sh`. The installer refuses existing shadow units/releases. It never
stops or changes existing services. Verify `LastTriggerUSec`, the shadow service's
`Result`, the report observation time, and actual data status after a timer firing;
then recheck the collector's PID/checkpoints and source hashes. Merely invoking
`run.py` is not a scheduled-run verification.

Rollback only this service: `systemctl disable --now trading-shadow-7500.timer`,
then `systemctl stop trading-shadow-7500.service`. Preserve its state and release
for audit. Linux systemd isolation and repeated timer runs were verified; see the re-verification record. There is no independently verified external alert channel.

OPRA access is required for this options-quote experiment. Alpaca's indicative
feed contains modified quotes and is not an acceptable replacement:
https://docs.alpaca.markets/us/docs/historical-option-data
