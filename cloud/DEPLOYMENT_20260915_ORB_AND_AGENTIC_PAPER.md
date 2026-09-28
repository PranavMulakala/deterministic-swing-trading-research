# September 15 deployment: ORB challenger and $10,000 paper lifecycle

## Deployed state

- Research release: `/opt/trading-research-v3-20260915-orb-direct-v1`
- Dashboard release: `/opt/trading-dashboard-20260915-paper-runtime-v1`
- Paper lifecycle release: `/opt/agentic-paper-runtime-v1-20260915b`
- ORB direct-breakout prospective start: 2026-09-16
- Paper lifecycle accounts: isolated $10,000 stock and $10,000 options simulations
- Orders, broker access, promotion, and model calls: disabled

The original ORB result sections were reproduced unchanged during staging and
cutover.  The challenger changes only breakout confirmation: the first completed
five-minute close strictly above the opening-range high is eligible without a
retest.  Eligibility, universe, risk, costs, delays, accounting, and Arm A/B
relative-volume rules are unchanged.  September 8 through 15 are excluded from
challenger scoring.

## Verification

- 158 combined Python tests passed.
- 22 dashboard renderer contracts passed.
- Both new source freezes verified.
- Staging and production artifact hashes matched.
- The deployed dashboard trusts the deployed research pin manifest and its
  stored result artifact/index agree.
- The collector remained active and was not restarted; its final health check
  reported no errors or pending streams.
- Rollback unit copies are retained under
  `/var/backups/trading-orb-direct-v1-20260915` and
  `/var/backups/trading-dashboard-paper-runtime-v1`.

## Current verdicts

- ORB direct-breakout challenger: **RUNNING / WAITING FOR FIRST PROSPECTIVE
  SESSION**.  Its first eligible result can only exist after the September 16
  regular session is complete and the delayed archive has caught up.
- $10,000 stock/options lifecycle software: **DEPLOYED**.  The scheduled offline
  runner includes simulated fills, marks, management, exits, ledger accounting,
  idempotency, session counting, and review gates.
- $10,000 stock/options data trial: **BLOCKED_DATA**.  No validated provider
  cycle exists, so the service has created only `status.json`; it has created no
  account ledgers, counted no sessions, and simulated no trades.

The remaining external inputs are a production-quality fresh stock/option data
producer, at least 50 point-in-time history sessions, current earnings-calendar
receipts, complete SPY/QQQ option-chain receipts within 30 seconds, and the
bounded market/news/macro receipts required by the frozen input contract.
Waiting alone does not satisfy these gates.

Nothing in this deployment establishes profitability or authorizes paper-broker
or real-money orders.
