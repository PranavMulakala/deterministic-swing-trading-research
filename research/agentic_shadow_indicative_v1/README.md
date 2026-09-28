# $7,500 Alpaca indicative shadow experiment

This is a separate, no-cost operational experiment. It reads Alpaca's free
indicative options feed and IEX stock feed, simulates the frozen comparison
logic, and writes an auditable local ledger. It has no broker-order client or
mutating HTTP method.

Every result is **PLUMBING ONLY — NOT VALID FOR PROFIT, EXECUTION, OR
AGENT-EFFICACY ANALYSIS**. Modified indicative quotes and delayed indicative
trades cannot test the original OPRA hypothesis. The frozen OPRA experiment in
`../agentic_shadow_v1/` remains separate and unchanged.

## What runs

- A credentialed producer performs hardcoded HTTPS `GET` requests only to
  `data.alpaca.markets` and `paper-api.alpaca.markets`.
- The producer collects SPY/QQQ data from 09:50 through 16:00 Eastern on
  weekdays, alternates the screened symbol, and tries the other symbol when the
  preferred symbol lacks three consecutive completed bars.
- It atomically publishes one normalized packet, stores an exact compressed
  raw-response archive, and appends a credential-free operational status line.
- A separate consumer receives no credential and has no IP network access. A
  systemd path unit runs it after each packet replacement.
- Each immutable release receives its own consumer state directory because the
  ledger is bound to the exact engine hash. Older releases and ledgers remain
  available for rollback.

The paper account does not need funding for this read-only plumbing run. The
free Alpaca Basic plan is sufficient. OPRA remains a paid future experiment and
is not silently substituted here.

## Local verification

From the repository root:

```bash
PYTHONPATH=src:. .venv/bin/python -m unittest \
  research.agentic_shadow_indicative_v1.test_engine \
  research.agentic_shadow_indicative_v1.test_engine_adversarial \
  research.agentic_shadow_indicative_v1.test_indicative
```

Build into a new empty directory and verify the exact manifest:

```bash
PYTHONPATH=src:. .venv/bin/python \
  research/agentic_shadow_indicative_v1/deployment/build.py /private/tmp/indicative-release
python3 /private/tmp/indicative-release/verify_release.py
```

See [deployment/README.md](deployment/README.md) for install, smoke, evidence,
checkpoint, and rollback commands. The frozen rules and limitations are in
[PROTOCOL.md](PROTOCOL.md).

