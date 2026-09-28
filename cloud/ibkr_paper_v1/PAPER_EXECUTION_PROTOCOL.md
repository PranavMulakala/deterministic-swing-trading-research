# IBKR native bracket paper protocol — candidate v1

Status: **experimental paper supervisor armed; entries require all data/risk gates**. The data collector
retains its order-message denylist. No live account or live socket is permitted.

The frozen feasibility engine remains unchanged. Its exits are delayed market
orders triggered by liquidation-side quotes. A broker-native profit limit and
last-price stop have different behavior. This version must be compared with a
matching native-bracket simulation, not passed through the old comparator under
an incorrect execution-model label.

## Entry and protection

- One December 2026 MNQ contract in the exact configured paper account.
- Original strategy signals and the 09:45–11:30 New York window remain the research
  starting point. Full prior-session coverage and a validated IBKR trade adapter
  are mandatory before strategy entries.
- Signal confirmation plus one second is the earliest entry decision. The quote
  must arrive after that time, be real-time and at most 250 ms old at reservation.
- Entry is a marketable limit with at most two ticks of price concession. Its GTD
  expiry is signal confirmation plus two seconds. Timing/rejection support must
  be observed in the paper broker; expiry is not assumed exact before that test.
- The linked target is a GTC limit and the linked protective stop is GTC STP with
  the SDK's Last trigger method (`2`). Parent and target use `transmit=false`; the
  last stop child uses `transmit=true`, following IBKR's bracket example.
- GTC protection avoids intentionally removing the stop at the session boundary.
  A time exit at noon still needs broker-tested cancellation/race handling. Do
  not transmit a separate flatten order while an exit child might also fill.
- A stop-market order can fill beyond its trigger. Planned risk limits are not
  guaranteed maximum losses. Paper testing must include gaps and child rejection.

## Persistent state implemented

`execution.py` recomputes plan arithmetic before reserving an intent. Reservation
and the daily attempt count commit in one SQLite transaction before any future
socket call. Each child is marked `SUBMISSION_UNKNOWN` before sending. Duplicate
signals, out-of-order dispatch, process restart or transport failure prevent an
automatic resend. Order IDs are unique across parent and children.

Executions must match owned order IDs, account, contract, side and exactly one
contract. Duplicate execution IDs are idempotent; conflicting corrections require
review. Missing commission is missing, not zero. Flat reconciliation requires
broker query-end evidence in the adapter, no remaining owned orders, and exactly
one entry and one exit. Cancelled-unfilled attempts require terminal evidence for
all three orders and remain counted toward the daily attempt limit.

The virtual research allocation starts at $5,000 regardless of the broker's paper
balance. Planned risk is at most min($12.50, 0.25% of day-start allocation). There
are at most two attempts per day. Realized and marked-equity daily loss and
high-water pause calculations persist across restarts. Marked equity uses the
liquidation-side quote and reserves the full planned round-trip fee ceiling.
Missing or stale quotes latch an audited pause; a price recovery cannot clear it.
The broker supervisor now acts on these pauses using owned cancellations, terminal
callbacks and a position check before a separate close. These primitives alone
cannot authorize dispatch. The separate live $50 allowance
proposal is neither approved nor imported into paper authorization.

## Candidate comparison model

`native_simulator.py` models the bracket from strictly ordered receipt-time quote
and eligible-trade events. Entries cannot exceed their limit price. Targets need
a trade through the limit by at least one tick; touching the price is insufficient.
Stops use a last-trade trigger, then a delayed liquidation-side quote with adverse
slippage. Gap losses can exceed planned risk. Missing fees leave net profit unknown.
Stale quotes or quote gaps suppress the economic result. Every result retains the
input tape hash and labels broker execution and fill probability as unverified.

This is a comparison convention, not an exchange queue model. It does not model
the actual acknowledgement delay of protective children, all exchange conditions,
or all cancellation races at the noon time exit. The limited experimental paper
pilot collects those observations; it does not claim model parity or live readiness.

## Remaining connection and evidence gates

1. Read-only account, position, open-order, execution and account-summary snapshots.
   The API execution window is limited, and these queries are not atomic. Persist
   request-end markers and timestamps; never infer full account history.
2. Verify broker fees and margin for this account and contract. A provenance hash
   in a plan does not itself verify a fee ceiling.
3. Validate the streaming signal adapter and the separately versioned simulator.
4. The dispatch supervisor, intratrade risk pauses, stop acknowledgement checks,
   owned cleanup and time exit are implemented. Uncertain recovery freezes entries
   and may require operator review rather than automatically resending orders.
5. Actual paper acknowledgements, filled entry/close, child cancellation, fees and
   flat-state process recovery passed. Natural stop/target fills, exact two-second
   strategy GTD behavior, overnight authentication and active-position failure
   recovery remain prospective pilot observations. The forced test used a ten-second
   parent expiry and a short holding period; it was not a qualifying strategy trade.

The current synthetic tests are software evidence only. Neither a generated SDK
Order object nor an empty broker snapshot establishes execution readiness.

The read-only reconciliation validator now verifies capture age (at most five
seconds), capture duration, callbacks and query-end order, owned execution IDs,
client/contract identity and fees. Unsupported fee precision or non-USD fees
remain unresolved. It returns a non-atomic flat observation, not permission to
retry or a claim of complete execution history. The dispatch supervisor must
apply those observations to the durable ledger and resolve all outstanding
intents before any subsequent entry.

Sources checked September 21, 2026:
- https://www.interactivebrokers.com/docs/general/order-types/complex-orders/bracket-orders
- https://www.interactivebrokers.com/docs/tws-api/ref/order
- Official SDK 10.50.2 `OrderSamples.BracketOrder` and `ibapi.order.Order`.

## Supervised staging probe — September 21

`staging_probe.py` is a separate manual probe with every leg forced to
`transmit=False`. It cannot test fills or protective behavior. IBKR documents
that untransmitted orders can be cancelled but cannot be viewed by the API:
https://interactivebrokers.github.io/tws-api/order_submission.html

The first real probe returned zero-filled Cancelled callbacks for all three
owned legs, followed by code 161 for each redundant cancellation. The original
journal and failure result are retained. Cleanup must require a terminal callback
for each attempted leg: an empty open-order query is insufficient evidence.
The updated code tolerates 161 only after an owned leg's Cancelled callback.
This correction has software tests; no second staging probe was needed or run.
Actual bracket acknowledgements, links, fills and protective behavior remain
unverified, and unattended order routing remains disabled.
