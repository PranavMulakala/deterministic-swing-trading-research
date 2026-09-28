# Agentic Portfolio Research v1

This package is a **paper-only research harness**. It creates two independent simulated $1,000 accounts: one for a deterministic stock swing experiment and one for a long-option experiment. It cannot connect to a broker, submit an order, cancel an order, replace an order, transfer cash, or call an AI model.

## What is frozen

- Stock universe: LITE, COHR, CIEN, FN, AAOI.
- Stock target: a conservatively rounded exit price intended to leave at least 10% net return after modeled entry and exit costs and the ledger's floor-to-cent cash credit; every management decision rebinds the plan and hold clock to durable fills.
- Options: one long SPY/QQQ call or put, 14-30 DTE, exactly one whole contract and at most one open position; management requires fresh hash-bound evidence and re-derives its economics and clock from the durable fill.
- Both strategies use the same risk code and policy schema, but different databases and virtual accounts.
- `orders_enabled` is permanently false in this version. A future behavior change requires a new package version.

The entry and management rules are research assumptions. They are understandable and testable; they are **not proven optimal and do not establish profitability**.

## Run locally

From the repository root with Python 3.12:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s research/agentic_portfolio_v1 -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python -m research.agentic_portfolio_v1.demo
PYTHONDONTWRITEBYTECODE=1 python -m research.agentic_portfolio_v1.freeze
```

The demo uses synthetic data and a temporary SQLite database. It does not write into the repository.

## Evidence boundary

Validated here: deterministic calculations, strict packet schemas and hashes, replay-safe chronological SQLite accounting/risk invariants, pre-mutation and pre-replay reconciliation, reservation TTL/policy/strategy binding, position-carried exact engine versions, rejection of management evidence from before a durable fill, UTC time-reversal rejection, non-resettable conservative hold clocks, durable integrity latching, decision-card generation, validation against an actual quote-bound read-only broker receipt, and complete frozen-file coverage.

Not validated here: live or historical strategy edge, broker execution, fills, data entitlements, news interpretation, options assignment/exercise, tax treatment, model quality, cloud deployment, or unattended operation. A passing test suite means the code follows its stated protocol; it does not mean the strategy makes money.
