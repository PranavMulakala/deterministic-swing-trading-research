# Hosted MNQ paper research — September 21, 2026

## September 22 incident update — recovery not verified

The actual cloud emails at 13:15:38 and 13:30:49 UTC reported
`GATEWAY_LOGIN_OR_API_REQUIRED`, zero captured events and no eligible new entries.
Opening quotes were missing. September 22 cannot count as the first complete
warmup session. The earlier Wednesday earliest-eligible date below was conditional
and no longer follows from the observed data.

Pinned SSH connections timed out repeatedly from the user's current mobile
network. The provider browser also requires sign-in. Gateway process state, its
login screen and the cause of the failed API handshake remain unverified. No
Gateway restart or credential change was made during this incident.

A **local, not deployed** reporting fix now persists connectivity incidents outside
research hours: alert after three minutes of sustained failure (immediately during
the session), confirm recovery after two healthy minutes, and expire an unsent
outage notice after recovery. A persistent incident can send one notice per New
York calendar day. All 91 focused tests pass locally. Existing scheduled pre/post
reports remain unchanged on the cloud until deployment is possible.

Recovery requires working server access, inspection of the Gateway and its restart
logs, paper authentication if requested, verified fresh MNQ quotes, deployment of
the tested reporting update and an observed overnight restart. Whole-host outage
monitoring still needs an independent observer. IBKR weekly authentication and
possible unexpected token revocation cannot be eliminated by these alerts.

Official reference: https://www.ibkrguides.com/traderworkstation/auto-restart-considerations.htm

## September 21 activation record

**The experimental paper supervisor is deployed, enabled at boot and armed.
Current entry gate: PREVIOUS_SESSION_INCOMPLETE. Live trading is not authorized.**

“Armed” means the program can send a qualifying paper order after all gates pass.
It does not mean a trade must occur. The data collector is intentionally read-only;
the separate strategy supervisor owns the guarded order interface. Its heartbeat
is `execution-health.json`, separate from the collector's `orders_enabled=false`.

## What is verified

- Cloud Gateway is authenticated to the exact simulated account, with real-time
  CME MNQZ6 data. The API socket is blocked from non-loopback traffic by a
  boot-enabled firewall. Only localhost port 4002 and the exact paper account
  are accepted by the order client. No live account or live endpoint is supported.
- Existing personal server `198.211.113.234` runs Gateway, capture, analysis,
  paper supervisor and report scheduling. The Mac provides only an optional
  private login console, not the runtime or price transport.
- A transmitted, unfilled one-contract bracket was acknowledged, including its
  protective stop, then all three orders were cancelled and the account was flat.
- A second supervised test filled one contract and its closing order. Native
  protective exits were acknowledged, cancelled and confirmed terminal before
  the independent closing order was sent. Two fee reports were USD 0.61 each.
  The account ended with zero quantity and no working orders.
- Both forced tests are labeled PLUMBING_ONLY and excluded from strategy P&L,
  win rates, qualifying signals and performance sample counts.
- Current validation replayed both actual callback journals. It checks account,
  client, contract, parent linkage, side, quantity, stop trigger/price, limit
  price, owned execution identity, fees and no duplicate entry or close.
- 87 focused tests passed locally and on the server. Tests cover durable intent,
  loss pauses, data quality, duplicate dispatch, cancellation/fill races, missing
  fees, persistent uncertainty, collector isolation and report scheduling.
- Resend delivery was verified in Gmail, including a message sent by the actual
  scheduled systemd service. Only the report key was transferred to a restricted
  server file; the Gmail app password remained local.
- The collector and unrelated research services kept their original PIDs through
  this deployment. Collector restart recovery was demonstrated earlier.

## What the supervisor does

`strategy_runtime.py` reads the recorded tape in insertion order. It requires the
immediately preceding calendar session of the same contract to pass completeness
checks, then builds causal minute bars. Today's prefix must have opening quotes,
no disallowed interruptions, valid timestamps and fresh real-time prices. Late
signals are skipped; it never chases an expired entry after connecting.

The existing strategy remains the starting hypothesis: prior-session levels,
VWAP with three-standard-deviation bands, and the defined two-bar reversal.
Native bracket execution is a separately versioned candidate, not claimed
identical to the historical delayed-market-exit model.

The virtual allocation is USD 5,000, irrespective of the broker's simulated
balance. One contract maximum; at most two attempts per day; planned risk at most
min(USD 12.50, 0.25% of day-start equity); daily loss pause at
min(USD 25, 0.5% of day-start equity); 5% high-water drawdown pause.
A USD 4 round-trip fee reserve is conservative planning, not a guaranteed fee
ceiling. Recorded costs above it pause further entries. Margin preview plus
planned trade risk and a USD 25 buffer must fit the research allocation.
Stop slippage can exceed the planned loss allowance.

Order intent and unknown-submission markers are durable before socket writes.
An uncertain journal or unreconciled intent blocks later entries after restart.
Only owned orders can be cancelled. A time/risk exit first cancels native orders,
waits for terminal callbacks, and checks positions against owned executions;
it cannot send an independent close while an old order might still fill.

Each reconciled strategy trade stores actual fills/fees and a comparison against
its recorded-tape candidate model. Missing or invalid comparison data remains
unknown. A modeled outcome is not a claim of executable prices or future profit.

## Schedule and current data gate

The research session is 09:30–16:00 New York on the stored exchange calendar.
Entry window: 09:45–11:30; planned time exit: noon. Short sessions are excluded
from this full-session strategy. Overnight futures hours are outside this version.

Reports: 15 minutes before open and 15 minutes after close, normally 06:15 and
13:15 Pacific. Holidays, DST and early closes follow the verified calendar.
Reports distinguish capture health, paper supervisor gates, candidate signals,
reconciled strategy performance and unresolved attempts. Forced tests are excluded.

Monday September 21 began mid-session and is incomplete. Tuesday September 22
can provide the first complete warmup day if all quality checks pass. Wednesday
September 23 is therefore the earliest normal session eligible to use it.
A valid warmup still does not guarantee a qualifying signal or affordable stop.

## Remaining observation requirements

This is operational experimental paper trading, **not 100% validated execution or
real-money readiness**. The following evidence cannot be manufactured by tests:

- A complete current/prior-session pair, followed by prospective strategy signals
  and actual matching fills. The prior historical study found no qualifying
  setups across 24 sessions; time to collect enough trades is unknown.
- Natural stop fills and target fills in this broker setup. Stop acknowledgement
  and cancel-then-market-close are verified; these other exit outcomes are not.
- The first overnight authenticated Gateway recovery and normal scheduled pre/post
  emails. IBKR can require periodic human reauthentication. Unattended recovery
  is not a promise of uninterrupted broker access.
- Active-position crash/disconnect recovery. Current behavior preserves native
  protection where accepted and blocks new entries on uncertainty, with an email
  attention report; operator review may be needed. It does not silently retry.
- Full-host reboot, off-host backup/restore and independent outage monitoring.
  Process uptime is not a full disaster-recovery demonstration.

Review the code-bound paper qualification by October 21 or before changing its
critical modules. Contract rollover requires a separate review before December
expiry. The supervisor fails closed if its qualified code hashes change.

## Paper duration and any live decision

Use 20 complete sessions as the first research review, roughly four trading weeks,
not a promised live date. Five consecutive clean operational sessions and a
proposed diagnostic sample of 50 qualifying closed out-of-sample trades across
at least 20 sessions are review checkpoints, not proof of profit. Sparse signals
may require much longer; a strategy can also fail the review and never go live.

Any real-money trial requires a separate evidence review and explicit approval
naming account, contract, version, dates and loss allowance. No live order has
been authorized or requested by this deployment.

## Operations

- Inspect: `venv/bin/python cloud/ibkr_paper_v1/inspect_server.py` on the server.
- Execution heartbeat: `/var/lib/ibkr-paper/execution-health.json`.
- Durable strategy ledger: `/var/lib/ibkr-paper/strategy-ledger.sqlite`.
- Immutable execution journals: `/var/lib/ibkr-paper/execution-journals/`.
- Stopping `ibkr-paper-strategy.service` requests owned cleanup if an order is
  active. Do not kill Gateway or the collector to pause new entries.
- Never delete an unresolved journal to make the gate green. Reconcile the exact
  owned orders and preserve a reviewed recovery record.
- Existing data, reports and analysis can continue while strategy entry is paused.
