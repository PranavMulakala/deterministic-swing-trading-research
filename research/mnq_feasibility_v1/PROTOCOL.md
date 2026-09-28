# MNQ feasibility pilot v1

Written September 8, 2026, before acquiring or inspecting MNQ market data for this
experiment. This is an implementation specification, not a claim of an edge or
formal independent preregistration. Prior Reddit examples are not validation data.
No old ORB/LITE/ETF strategy or its frozen results are changed.

## Question and scope

Can this particular reversal setup be simulated with one dated MNQ contract,
$5,000 starting cash, 0.25% planned risk per entry, and the stated cost and pause
rules? A negative answer can mean insufficient budget, insufficient evidence, or
an unprofitable setup. These are different findings.

The initial implementation has no broker adapter, network requests, secret reads,
or order methods. The SPY wheel and additional Reddit strategies are outside it.

## Signal, defined before market results

1. Use a single actual dated MNQ contract per session, with that same contract's
   preceding full regular session for the high and low. No adjusted continuous
   price series or NQ-to-MNQ substitution. The pilot avoids rollover; a longer
   study needs a separately specified calendar roll and same-contract warmup.
2. Use a verified regular-session calendar, New York time, 09:30 inclusive to
   16:00 exclusive. This engine handles full 390-minute sessions only. Exclude
   partial holidays explicitly in the input manifest, not after viewing results.
3. Aggregate eligible individual trades into completed one-minute bars. VWAP and
   population variance are volume-weighted across individual trade prices from
   09:30, updated causally. The implementation uses weighted Welford updates to
   avoid cancellation error. No typical-price approximation or overnight volume.
4. Let A be the completed setup minute and B the next completed minute. For a
   short, A.close must be strictly greater than A's VWAP + 3 standard deviations,
   A.low <= previous-session high <= A.high, and B.close < A.low. A positive
   standard deviation is required. Mirror these inequalities for a long, using
   the previous-session low and the lower band. Touch tolerance is exactly zero:
   the known level must lie inside A's traded high/low range, endpoints included.
5. B must finish at or after 09:45 and strictly before 11:30. Each qualifying
   two-bar pattern is a separate signal, regardless of portfolio eligibility.
6. Stop is two ticks beyond the more extreme price across A and B. The target is
   B's cumulative VWAP, fixed forever at confirmation. Round the target toward
   the entry (down for a long; up for a short). Never adjust a stop to fit capital.
7. An empty minute is ambiguous in an unverified export. Keep any earlier signals,
   then halt signal generation for the remainder of that session at the first
   missing minute. Missing previous-session minutes exclude the next session.
   Count and report all affected sessions; do not silently delete them.

Moving averages, volume delta, discretionary news judgments, and additional
levels are not entry filters. They are not currently computed by this minimal
engine. A future contextual study must declare its own definitions first.

## Executable-price model

Signal confirmation is B's end boundary, not its last trade timestamp. Attempt
entry using the first quote at or after confirmation + 1 second, and no later
than a further 1 second. Do not carry a quote forward or shop for a better quote.
Reject a crossed/zero/empty book, spread above four ticks, insufficient displayed
size for one contract, or prices that have already crossed the stop/target.

Buy at ask plus adverse entry slippage; sell at bid minus adverse entry slippage.
This incorporates the displayed spread once. Do not add it again as a cash fee.

Planned loss = entry-to-stop ticks * $0.50 + exit slippage ticks * $0.50 + total
entry/exit fees. Entry slippage is already inside the entry-to-stop distance.
Planned net reward uses the fixed target, adverse exit slippage, and the same
fees. Require net reward / planned loss >= 1.5, as well as the risk budget.

Stop/target triggers use the executable liquidation side (bid for a long, ask
for a short), not chart highs or lows. Model a market exit at the first valid
quote at least 100 milliseconds after its trigger, with adverse exit slippage.
A target touch can therefore produce a worse fill, including a loss after a
fast reversal. This is an explicit simulated exit policy, not a resting-limit
fill assumption. Broker-native stop semantics remain unverified.

At noon, the first valid quote triggers a time exit, followed by the same delay.
It is not a promise of an exact noon fill. Wide spreads do not block exits;
invalid books or absent size do. An unclosed position at the end of available
quotes stops the replay, keeps the inventory in the report, and nulls final
equity. No overnight inventory reset or fabricated closing price.

## Portfolio overlay

- One contract total, no adding, at most two actual entries per session.
- Per-entry risk budget: 0.25% of starting-day equity, initially $12.50.
- Daily loss pause: mark-to-market net liquidation equity falls to or below
  99.5% of starting-day equity, initially a $25 loss. Latch until the next day.
- Account review pause: equity falls to or below 95% of its running high-water
  mark, initially a $250 drawdown. Latch for the rest of the experiment; there is
  no automatic reset or restart after a recovery.
- **Implementation decision:** either loss pause also requests an exit from an
  open position using the exit latency model. This makes the previously general
  pause proposal explicit. It does not guarantee a loss cap.
- Marks include estimated liquidation slippage and the remaining exit fee. Charge
  half the round-trip fee on entry and half on exit; reconcile all cash to trades.
- A quote interval exceeding one second, or an invalid book while exposed,
  latches a data-quality pause and requests exit on valid data. Record all such
  intervals. Closed trade P&L remains a diagnostic, final equity is suppressed,
  and observed drawdown is only a lower bound. This strict gap rule may reject
  genuine quiet periods; measure that limitation rather than weaken it afterward.

Fees of $2 and $4 round trip and slippage of 0/1/2 ticks per side are **illustrative
stress scenarios**, not verified account charges. Run all specified scenarios;
do not select the one with the best P&L. Replace assumptions only in a new version
once a real fee schedule is known, before evaluating its market outcomes.
Fixed subscriptions, purchased history, taxes and margin eligibility are not
modeled in portfolio returns. State their actual costs separately; operational
readiness remains unestablished until broker margin and execution are checked.

## Denominators and outputs

For each scenario, report all patterns, risk-assessable patterns, unknown risk,
risk fits / all patterns, and risk fits / assessable patterns. Unknown is never
converted to zero risk. Risk-fit screening uses the fixed initial $12.50 budget;
the separate portfolio overlay uses each day's actual starting equity.

Also report reward/cost rejections, entry-window and position/entry-limit
rejections, pause reasons, actual simulated entries, every closed trade, every
quote mark, cash reconciliation, worst observed drawdown and unresolved inventory.
Different cost scenarios may admit different trades. Their aggregate difference
combines selection and execution effects, not pure matched-trade slippage.

## Data and evaluation plan

First pilot request: full regular sessions August 31 through September 4, 2026,
with August 31 used as previous-session warmup, on the actual September 2026 MNQ
contract. Verify contract mapping and the session calendar before the request.
The dates are selected for being the last completed full week, not their returns.
This is a small pipeline/capital feasibility pilot, not proof of profitability.

After the pilot, document data quality, sample size, signal distances, rejection
rates, estimated costs, and accounting failures. Any repair changes the code hash.
Do not call the same inspected dates untouched validation after a repair/tune.
Plan longer historical periods and a separate unexamined forward period before
opening their outcomes. No arbitrary number of days guarantees a reliable edge.

To proceed toward live money requires, at minimum, verified costs and margins,
valid data, reproducible after-cost results with uncertainty and drawdown
analysis, and a separate forward paper execution/reconciliation check. This
pilot alone cannot provide that approval or a promised live launch date.

## Sources checked September 8, 2026

- [CME MNQ contract size](https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.contractSpecs.html): $2/point, 0.25-point tick.
- [NinjaTrader pricing](https://ninjatrader.com/pricing/): advertised commissions are per side; exchange, clearing and NFA fees also apply. Account-specific all-in costs are not verified.
- [Databento MBP-1](https://databento.com/docs/schemas-and-data-formats/mbp-1): top-of-book changes, trades, size, and timestamps. Provider capture time is not our computer's receipt time.
