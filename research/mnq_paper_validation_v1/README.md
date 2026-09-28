# MNQ paper versus simulation: offline comparison v1

This is a working evidence importer and comparator. It does not connect to a broker, collect real paper fills, place orders, authorize a live trial, or establish a trading edge. The current status is **NOT_READY**, because no actual MNQ broker paper evidence or paired forward simulation has been supplied.

In simple terms: we need two receipts for the same opportunity. One records what the simulator expected. The other records what the broker's paper account actually did. This tool checks that both receipts refer to the same rules, contract and period, then checks the arithmetic and highlights every disagreement. If a receipt is missing, it does not invent one.

## Run it

From the repository root, using the existing virtual environment:

```sh
.venv/bin/python -m unittest discover -s research/mnq_paper_validation_v1 -p 'test_*.py' -v
.venv/bin/python research/mnq_paper_validation_v1/compare.py --out research/mnq_paper_validation_v1/runs/new-status.json
```

The second command intentionally returns exit code 2 and writes a report with missing-evidence blockers. Report destinations must be new files; an existing artifact is never overwritten.

When real exports and their source files exist:

```sh
.venv/bin/python research/mnq_paper_validation_v1/compare.py \
  --paper research/mnq_paper_validation_v1/private/paper.json \
  --simulation research/mnq_paper_validation_v1/private/shadow.json \
  --out research/mnq_paper_validation_v1/runs/comparison-001.json
```

Keep broker exports and identifying account details in the Git-ignored `private/` directory. Use an account alias in normalized evidence. Never place passwords, tokens or API keys in exports.

## Canonical import contract

Two JSON objects are required. `fixture.py` builds a full structural example, with `SYNTHETIC_FIXTURE` labels on both sides. Those labels must remain on invented data. The fixture contains no real broker account or fills.

Both objects contain:

| Field | Required meaning |
|---|---|
| `schema_version` | Integer `1`. |
| `evidence_kind` | Paper: `BROKER_PAPER_EXPORT`; simulation: `FORWARD_SHADOW_SIMULATION`. Invented data: `SYNTHETIC_FIXTURE`. Historical simulation is not forward paper evidence. |
| `strategy_fingerprint` | `compare.frozen_fingerprint()` hashes the pinned, unchanged `engine.py`, `config.json`, and `PROTOCOL.md`. A matching hash alone does not prove the adapter executed those rules. |
| `execution_model` | Exact `compare.EXECUTION_MODEL` dictionary. It includes the model version, entry timing, liquidation-side BBO exit trigger and delayed market exits. |
| `execution_model_source` | Exact nonempty relative path of retained adapter/version and trigger-semantic evidence in `source_files`, with a matching verified hash. A boolean or arbitrary description is rejected. |
| `symbol` | One explicit outright MNQ expiry, e.g. `MNQU6`; no continuous alias, parent family, spread, or contract substitution. |
| `window.start`, `window.end` | Identical complete flat-to-flat intervals in both bundles. Include the opening flat snapshot before any fills and a fresh final flat snapshot after all fills. |
| `exported_at` | Export produced after the complete window, with a timezone. Historical evidence does not become unusable merely because the present date advances. |
| `complete` | Literal `true` only when pagination, cancellations, rejections, executions and the entire requested interval have been verified complete. |
| `source_files` | Nonempty list of `{path, sha256}`. Relative paths are confined to the bundle's directory; symlinks escaping it and `..` traversal are rejected. Preserve immutable original exports, raw logs and fee/clock provenance. |

**Timestamp and numeric rules:** use RFC3339 timestamps with an explicit offset, up to nine fractional digits. Offsets normalize to UTC without floating-point conversion. Prices and fees are nonnegative decimal **strings**; prices must be on the 0.25-point MNQ tick. Quantities are integer contracts. A one-contract order cannot fill in fractional contracts. Missing fees are `null`, never an assumed zero. Duplicate JSON keys, nonfinite values and duplicate IDs are rejected.

Paper-specific fields:

- `account_mode: "PAPER"`, `broker`, `account_alias`, and `fees_complete`.
- `clock_alignment_verified` and `clock_alignment_source`: require documented relationships among exchange event, local receipt and broker fill clocks. The source must be an exact nonempty relative path in retained, hash-verified `source_files`; a boolean or arbitrary description is rejected. This declaration is not independent verification. Retain actual quote-receipt times; do not relabel broker timestamps as exchange events.
- `decisions`: every detected signal, including skips, as `{signal_id, at, direction, decision, reason}`. IDs are assigned deterministically at signal generation and must be carried into broker order logs. `direction` is `1` or `-1`; `decision` is `ENTER` or `SKIP`.
- `orders`: one final canonical record per broker `order_id`, with `signal_id`, `leg` (`ENTRY`/`EXIT`), `symbol`, `side` (`BUY`/`SELL`), `quantity`, `filled_quantity`, `order_type`, `submitted_at`, `acknowledgement_received_at`, `broker_acknowledged_at`, `reference_quote_at`, `reference_quote_received_at`, `trigger_at`, `trigger_basis`, and `status`. Submission and acknowledgement **receipt** are local logged events. `broker_acknowledged_at` is the separate broker event timestamp, if supplied; otherwise it is `null`. Reference quotes retain exchange and receipt timestamps; fills retain broker execution timestamps. A verified clock mapping is required before comparing domains. A fill may happen before the acknowledgement message reaches the client; this is not rejected as a chronology error. `acknowledgement_received_at: null` blocks comparison. Active/partial/pending orders block comparison.
- `fills`: one record per immutable broker execution ID, as `{fill_id, order_id, at, quantity, price, fee_usd, fee_source, fee_source_reference}`. Fee source is `BROKER_EXPORT` or `VERIFIED_FEE_SCHEDULE`; `fee_source_reference` is the exact nonempty relative path of retained, hash-verified evidence in `source_files`. Broker paper fees must not silently inherit the simulator's illustrative assumptions.
- `positions`: `{snapshot_id, symbol, at, quantity}` for the start, end and any intermediate snapshots; signed quantities must reconcile with all fills up to the snapshot timestamp. Export one canonical snapshot per timestamp.
- `cash_snapshots`: exactly two `{snapshot_id, at, currency: "USD", cash_usd}` records at the window's exact start and end. `cash_ledger_complete` must be `true`. Opening cash plus net realised P&L from **all** actual fills and documented non-trade cash flows must equal closing cash exactly. Missing, unsettled or mismatched cash blocks comparison.
- `cash_flows`: every non-trade flow as `{flow_id, at, currency: "USD", kind, amount_usd, source_reference}`. `amount_usd` is a signed decimal string; positive deposits/interest add cash, negative withdrawals/non-trade account fees remove cash. Kinds are `DEPOSIT`, `WITHDRAWAL`, `INTEREST`, and `NON_TRADE_ACCOUNT_FEE`. The timestamp is after the opening snapshot and at or before the closing snapshot. Trade commissions belong on fills and must not be counted again as a cash flow. `source_reference` must be the exact nonempty relative path of a retained, hash-verified source file, not a made-up balancing label. Preserve the raw statement behind every flow; arbitrary balancing adjustments are not supported.

Cash fields must have the same broker ledger definition in both snapshots. If futures variation-margin or settlement timing prevents reconciliation to settled cash, retain the raw statement and mark the cash ledger incomplete. This v1 tool does not invent settlement adjustments; a broker-specific settlement-aware extension is required first.

Simulation-specific fields:

- `clock_basis: "EXCHANGE_EVENT_UTC"` preserves the frozen historical engine's clock. `market_data_complete: true` requires a complete paired stream, not a claim based only on a running process.
- `signals`: every detected signal with the same fields as paper decisions, plus `entry` and `exit`. Skips have both fields `null`; entries require complete simulated entry and exit records of `{at, price, quantity, fee_usd}`.
- The forward simulator adapter must retain input hashes, exact cost scenario, engine/config hashes and market-source lineage in `source_files`. Map frozen `portfolio_reason == "ENTERED"` to `ENTER`; preserve all other portfolio reasons as `SKIP`. Convert integer engine ticks to decimal index points and integer nanoseconds to offset-qualified timestamps without rounding. Do not export only successful trades.

## What it checks and measures

The tool compares complete signal sets and decisions, then pairs entry/exit orders and fills by stable signal ID. It rejects missing, extra, duplicate, partial, nonterminal and orphan records; wrong contracts/sides; stale or future reference quotes; absent or stale position/cash snapshots; incomplete source files; mismatched strategy/model; and missing or unverified fees. It reconciles total fills against order quantities, the signed position path, and the flat-to-flat cash ledger. More than one contract of exposure or an unclosed position blocks the comparison. Two fills with the same timestamp are ambiguous without a broker sequence and are blocked; v1 does not invent their order by sorting IDs.

Exit triggers must occur after the corresponding entry fill. Optional broker acceptance-event timestamps must fall between local submission and acknowledgement receipt under the documented clock mapping. Signal confirmation and entry-reference quotes must fall in the frozen 09:45–11:30 America/New_York window, and more than two entries in one New York trading date block comparison. A conservative observed-cash check also rejects an entry after the 0.5% daily loss pause or 5% account drawdown pause has already been breached by realized trading equity. This excludes non-trade cash flows and requires opening cash by 09:30; it is only a lower bound on full intratrade loss/drawdown behavior.

For each fully matched round trip it measures adverse entry and exit price differences in ticks, signed fill-time differences in milliseconds, fees, net P&L, and the paper-minus-simulation P&L difference. Positive adverse-price differences mean worse paper execution; positive time differences mean later paper fills. The contract multiplier is $2 per index point, pinned to the unchanged research configuration.

No performance tolerance has been approved. Every nonzero difference is sent for review. Small nonzero latency is not automatically an economic failure. Values on a blocked report are diagnostic only.

`RECONCILED_FOR_REVIEW` means the submitted records reconciled under this contract. It never means live-ready. `DIFFERENCES_REQUIRE_REVIEW` requires assessment. `EVIDENCE_BLOCKED` means missing or inconsistent evidence. Synthetic input always produces `SYNTHETIC_FIXTURE_ONLY`, even if its arithmetic matches perfectly. Every report sets `live_readiness: "NOT_READY"` and `live_trial_authorized: false`.

## Execution semantics and remaining integration

The frozen simulator triggers exits using the liquidation-side best bid/offer, waits at least 100ms, and then models a market execution; this includes the profit target. A native target limit order, last-trade-triggered stop or broker OCO bracket has different behavior. Do not change a label to make it pass. A broker-specific implementation must either demonstrate the same semantics, or use a separately versioned research model and repeat validation. The comparator does not recommend omitting protective broker orders to make a historical model appear equivalent.

No futures broker has been connected here. The repository's existing Alpaca paper workflow is equity-specific and is not evidence of MNQ support or readiness. Remaining work needs the selected futures broker's paper access, market-data entitlement, adapter, verified fees/margin, market and local receipt logs, immutable order/position exports, and clock-alignment evidence. Adapter tests must exercise protective orders, rejects, delayed acknowledgements, disconnects, restarts, duplicate submissions and the frozen pause rules against the real paper environment.

Version 1 intentionally accepts one entry and one exit order per signal. Replacements, multi-leg brackets, corrections, busts and position carryover are reported for review instead of silently merged. If the selected broker requires these, retain its full lifecycle export and extend the canonical importer with focused tests before treating it as reconciled.

Positive after-cost evidence on separately reserved periods, uncertainty assessment and an explicit user-approved live loss budget remain separate requirements. File hashes and passing software tests do not prove broker-export authenticity, future profitability or live execution safety.

This canonical contract does not contain the full quote path, stop/target values, planned-risk calculation or proof that the supplied simulation decisions were actually produced by running the frozen engine. Therefore those checks, full intratrade marked-equity pause fidelity and complete market-replay provenance remain explicitly pending in every report. A matching fingerprint establishes file identity only. Even `RECONCILED_FOR_REVIEW` must not be interpreted as completion of those missing gates.
