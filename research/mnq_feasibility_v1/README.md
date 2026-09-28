# One-contract MNQ feasibility study

This separate, offline study builds the measurement requested on September 8,
2026: signal risk fit, execution after costs, and account losses under pause rules.
It also powers the beginner notes in `../../learnings.md`.

**Current result: no qualifying patterns; risk fit and profitability remain
unknown.** The [August extension](runs/trade-extension-01/REPORT.md) added 20
sessions (one warmup, 19 evaluated) for $20.63 of additional provider usage and
found zero patterns. The earlier [pilot](runs/pilot-01/REPORT.md) found zero in
four sessions. An extra [August 28–31 bridge check](runs/bridge-01/REPORT.md)
also found zero; it is explicitly exploratory. These are 24 distinct evaluated
sessions under unchanged rules, not 24 trades. No further data is being bought
for this version. Total Databento usage across the two purchases is about $31.70.

The extension verified 106 downloaded files, 16,482,391 raw trade records,
23 definition records and 7,800 minute bars. Fourteen event-time boundary
records were excluded and retained in the raw source. Full exchange completeness
is not independently certified. See [current readiness](../mnq_live_trial_v1/READINESS.md)
for the paper-comparison tools, proposed budget, and remaining dependencies.

## Run it

From the personal repository root, using its existing standard-library Python:

```sh
.venv/bin/python -m unittest research.mnq_feasibility_v1.test_engine -v
.venv/bin/python -m research.mnq_feasibility_v1.run --output research/mnq_feasibility_v1/runs/new-status
.venv/bin/python -m research.mnq_feasibility_v1.run --demo --output research/mnq_feasibility_v1/runs/new-demo
```

Each output directory must be new. A plain run reports missing real data and the
budget arithmetic. `--demo` explicitly labels invented results as synthetic.
For small normalized JSON fixtures, the reference CLI accepts:

```sh
.venv/bin/python -m research.mnq_feasibility_v1.run --data /absolute/path/normalized-mnq.json --output research/mnq_feasibility_v1/runs/new-pilot
```

The CLI writes `REPORT.md`, `report.json` and `budget.csv`, including source/config
hashes. JSON includes each signal, reason for rejection, execution, equity mark,
pause and data-quality problem. There is no connection or trading command.

The large Databento pilot instead uses `import_databento.py` and
`run_imported.py`, with compact arrays in the ignored `data/import-v1` directory.
Both refuse to overwrite existing outputs. `replay_prepared.py` evaluates every
quote while exposed and skips redundant flat periods; economic results were
compared with the unchanged reference engine before opening market outcomes.
See `IMPORT_PROTOCOL.md` for exact event-completion, timestamp, and boundary rules.
`test_import_and_prepared.py` adds adapter and reference-equivalence checks.

## Read next

- `PROTOCOL.md`: precise hypothesis, rules, risk, timing, and limitations.
- `DATA_CONTRACT.md`: recommended small Databento request and remaining importer work.
- `config.json`: $5,000 account and predeclared illustrative cost scenarios.
- `runs/trade-extension-01/REPORT.md`: latest fixed August signal screen.
- `runs/pilot-01/REPORT.md`: earlier observed-data replay with illustrative costs.
- `runs/status-02/REPORT.md`: historical missing-data snapshot.
- `runs/demo-02/REPORT.md`: synthetic illustration only, never performance evidence.

Numbered output folders belong to different experiments; their suffix alone
does not establish which is current. Prior files remain unchanged for provenance.

The initial purchase was explicitly approved and handled separately by
`acquire_databento.py`; its `collect` mode retrieves existing jobs without buying
again. The replay configuration's `data_purchase_enabled=false` remains unchanged
and does not authorize additional purchases. `validate_download.py` runs offline
using isolated decoding libraries in the ignored data directory.

The separately approved extension uses `acquire_trade_extension.py`. Its
first attempt stopped at HTTP402 after 13 accepted requests. A read-only job
reconciliation and the user's monthly-limit update preceded the one-use
`resume_trade_extension_after_402.py` recovery of only eight missing requests.
Do not rerun either submission command: all 21 jobs are now acquired.
`screen_trade_extension.py` validates and screens those records offline, and
`run_bridge.py` checks the adjacent-date bridge using existing data. They refuse
to overwrite their existing outputs. See `STAGED_EXTENSION_PROTOCOL.md`.

No indicator, broker funding, new cloud collector, dashboard deployment, or
real/paper broker orders were added. Existing frozen research stays separate.
Fixed subscriptions and broker margin rules remain unverified and must be
included in a later economic/readiness assessment.
