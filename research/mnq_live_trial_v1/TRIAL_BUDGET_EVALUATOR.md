# Offline trial-budget evaluator

Status: **NOT APPROVED. Review only. No broker calls or order capability.**

`trial_budget.py` checks a supplied snapshot against the separate proposal in
`trial_budget_proposal.json`. It does not modify the frozen research. Even when
`entry_fits_proposed_limits` is true, the output always has `orders_enabled: false`
and `live_authorized: false`. Changing the policy to approved or widening a limit
is rejected; this utility is not a live-trading switch.

## Accounting contract

All observations must refer to the same reconciled time and a dedicated trial
ledger with no unrelated trading or unaccounted cash transfers. Missing equity
or nonpositive equity blocks the assessment. Numeric booleans, nonnumeric values,
NaN, infinity, negative fee reserves, and invalid counts are rejected.

- `day_start_equity_usd`: marked net equity at this session's start, after all
  fees already incurred at that time. Each session uses a fixed saved start.
- `marked_equity_usd`: current marked net equity, including all realized P&L,
  current gross unrealized P&L, and **all fees already incurred**. Mark an open
  long to an executable bid and an open short to an executable ask. It excludes
  only the unpaid future exit-fee reserve below. Do not pass cash as equity.
- `high_water_equity_usd`: trial high-water marked net equity on that same basis;
  it must include the initial trial equity and cannot be below either current
  equity or this session's day-start equity.
- `closed_trade_net_pnls_usd`: the complete trial-to-date list of each completed
  round trip's net result **after all its entry and exit fees**. Include wins,
  losses, and breakevens. A completed trip also counts toward the five-trip review.
  Never duplicate partial fills or reset/truncate this list between days.
- `open_position_gross_pnl_usd`: signed unrealized P&L from entry price to current
  executable liquidation price, **before fees**.
- `open_position_paid_entry_fees_usd`: nonnegative entry fees already incurred by
  that open position; these are already in `marked_equity_usd`.
- `open_position_unpaid_exit_fee_reserve_usd`: nonnegative fee allowance for
  closing that position, not yet deducted in `marked_equity_usd`.
- A flat position requires explicit zero for all three open-position fields.
  A nonzero position with unknown open accounting causes a pause.

Calculations use decimal arithmetic without rounding a limit upward:

```text
trade cap = min(12.50, 0.0025 * day-start equity)
daily cap = min(25.00, 0.005 * day-start equity)
daily loss = max(0, day-start equity - marked equity + unpaid exit fee reserve)
closed loss tally = sum(max(0, -net result) for every completed trial trade)
open loss = max(0, -(open gross P&L - paid entry fees - unpaid exit fee reserve))
total allowance used = closed loss tally + open loss
remaining total allowance = max(0, 50.00 - total allowance used)
```

Paid entry fees are subtracted when deriving the open trade's net loss, but are
**not subtracted again from current equity** for the daily calculation. Closed
trade fees are already in net results. Winning closed or open trades cannot
offset the nonreplenishing closed loss tally. Daily gains cannot enlarge the
daily allowance above its cap. Loss-limit equality and overshoots both pause.

`candidate_planned_loss_usd` is the complete conservative planned loss for a new
entry, including entry-to-stop exposure, expected entry/exit fees, and modeled
adverse slippage. The evaluator does not calculate a stop or verify those cost
assumptions. The supplied cost-verification flag must be true. The candidate
must fit the trade cap and remaining daily and total allowances. Existing or
pending positions block another entry. MNQ root and exactly one candidate
contract are required; actual contract/expiry qualification is a separate check.

## State and health contract

`entry_attempts_today` includes each sent entry attempt, including rejected or
uncertain submissions; retries must not evade the two-attempt ceiling. Track
order identities and submission outcomes elsewhere. At exactly two attempts,
`DAILY_ENTRY_ATTEMPT_LIMIT` blocks only further entries: the legitimate second
position continues its normal protection and exits. It does not trigger a
global pause or an early flatten. More than two attempts is a policy violation
reported as `DAILY_ENTRY_ATTEMPT_LIMIT_EXCEEDED` in `pause_reasons`.

`completed_sessions` counts
finished monitored sessions, including those with no trades, so the fifth
session may finish but a sixth cannot start without review. Review also occurs
when the fifth round trip finishes. These are operational review boundaries,
not evidence of a profitable strategy.

Unknown/stale data, unknown position, unhealthy connection, unreconciled equity,
an unavailable operator, excess exposure, or missing protection while exposed
requires a pause. Once a pause occurs, an external durable ledger must set
`prior_pause_latched` until a valid review/reset; this pure evaluator saves no
state and cannot enforce that requirement itself. The original 5% high-water
drawdown test uses marked equity without adding a new reserve to its definition.

`entry_block_reasons` describes admission restrictions only. They must never be
used as an instruction to close an existing valid position. `pause_reasons`
identifies loss, health, violation, or review conditions that require the
separately tested recovery/review procedure. Neither output sends an exit order;
unknown-position recovery in particular must reconcile state before acting.

The evaluator trusts supplied observations/health flags. It does not authenticate
the account, verify freshness, infer true fees, enforce broker limits, flatten a
position, or determine strategy/live readiness. Broker enforcement and the
paper-vs-simulation evidence remain required. Limits are pause triggers and can
be exceeded by real execution, gaps, or failures.

## Run offline

From the repository root:

```sh
.venv/bin/python -m unittest discover -s research/mnq_live_trial_v1 -p 'test_trial_budget.py' -v
.venv/bin/python research/mnq_live_trial_v1/trial_budget.py /absolute/path/to/local-snapshot.json
```

The test helper `snapshot()` in `test_trial_budget.py` lists every required input
using **invented examples**. No real broker observation is included or claimed.
Dollar metrics are JSON decimal strings to preserve exact budget comparisons.

See [the broker and trial proposal](BROKER_AND_TRIAL_PROPOSAL.md) for the
remaining account, execution, evidence, supervision, and approval requirements.
