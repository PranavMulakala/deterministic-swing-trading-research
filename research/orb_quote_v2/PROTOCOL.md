# Quote/trade execution v2 — separately frozen research

September 7, 2026. Owner approved a separately versioned execution model. Preserve
all v1 files and results. This is NOT an amendment that makes v1 appear complete.

## Unchanged hypothesis and risk policy

Inherit the hash-pinned v1 spec, corporate-action supplement and prepared features:
same five stocks, 2026 development dates, previous-20-session liquidity, ATR14,
first-five-minute range, first breakout/three-bar retest, stop at range midpoint
minus $0.01, 2R target, one attempt per symbol/day, cutoff 11:00, time exit 15:55,
long-only $5,000 shared portfolio, whole shares, 0.5% entry-risk cap, 1% aggregate
risk cap, two positions, 2% daily realized-loss halt, no same-day proceeds reuse.
A uses all eligible names; B requires opening RVOL >= 2. No news filter, new
indicator, threshold search, stock removal or leverage. Existing frozen eligibility
exclusions remain; execution ticks do not retroactively repair the bar indicators.

## Exact authorized execution differences

Five-minute pattern confirmation remains identical. For primary execution make
ONE IOC-style attempt exactly one second after confirmation; rerun at two seconds
as a named sensitivity. Cancel any unfilled entry remainder, do not wait until a
more favorable point in the minute. This replaces v1's next-one-minute-open fill.
Query all 145 frozen pattern signals, not merely v1's realized or winning trades.

Use the latest quote at or before the attempt, never a future quote. Require age
<=1 second, conditions exactly [R], positive finite prices/sizes, noncrossed market
and spread <=15 bps of mid. Conflicting quotes sharing a timestamp are unknown,
not arbitrarily ordered. Invalid latest quotes invalidate previous good quotes.
Unknown entry data rejects entry with a reason; a failed/truncated request is
unknown coverage, not an empty market or a verified rejection.

Buy at ask plus the original 10 or 25 bps adverse allowance; charge the original
1 bp fee. These allowances are NOW additional to observed spread, so costs are
deliberately conservative, not empirically calibrated. Keep the 0.5% confirmation
price entry ceiling. Replace the old estimated round-trip cost numerator with
observed ask-bid + mid*2*(slippage+fee), retaining the 20%-of-stop-distance ceiling.
Size from cash/risk/aggregate limits exactly as v1, then cap the fill by displayed
ask size. Treat one provider size unit as ONE share: a conservative capacity lower
bound, not a claim that Alpaca quote units are universally shares. This can reduce
position size and must be disclosed. Do not multiply an unverified round-lot size.
Filled shares alone create a position; cancel the remaining requested shares.

## Exits and event ordering

The stop and target prices do not move. A fresh valid bid <= stop OR a contemporaneous
trade <= stop with all conditions in [space, @, F, I] latches a stop. Odd-lot I
trades participate here even when they generated no OHLC bar; exclude average-price,
out-of-sequence and other nonallowlisted trade conditions. A fresh bid >= target
latches a target exit (a trade printing above target alone cannot prove a sale).
At 15:55 latch a time exit. This is a marketable-exit model, not a resting limit
queue simulation or a claim about Alpaca's broker stop-trigger policy.

After any exit trigger wait 100 ms. Sell on the first fresh valid executable bid
then available. Stop/time sales use bid minus adverse slippage; target-triggered
sales use min(bid,target) minus adverse slippage, so a reversal during latency can
lose target profit. No favorable gap improvement is credited to a target. Stop
exits can lose more than planned. Protective exits have no entry spread cap.

Respect displayed bid capacity and partial exits. Consume an observed bid price/
size state only once per position; an ask-only update with unchanged bid/size
does not replenish that state. A changed bid/size state supplies a new modeled
capacity observation. This is a conservative top-of-book model, not queue proof.
Allocate entry basis/fees proportionally as shares exit; realized partial P&L
affects the daily loss halt immediately. Unfilled exit shares remain a position.
If not fully exited within 60 seconds of trigger, stop the portfolio as unresolved,
preserving shares/cash. Never fabricate a close or silently hold overnight.

At equal timestamps: ingest all quotes as a group, ingest qualifying trade stop
triggers, evaluate stop before target before time, execute due exits, then process
entries by the original lagged-dollar-volume/ticker order. New positions cannot
react to trades that preceded their entry at the same timestamp. Initial exit
trigger on a new position is evaluated against its entry quote; no backdating.
All data use nanosecond timestamps. Partial exits and entries use Decimal cash.

Missing price bars do not stop this replay: the full tick stream is the execution
input. Missing/truncated tick coverage does. Lack of a quote update is not a halt;
do not forward-fill it as fresh. Existing-position equity must have a fresh valid
bid at any new entry decision, otherwise reject that entry as unknown equity.
Record stale-mark intervals; drawdown is only measured where marks are fresh.
Broker/exchange halt messages and original receipt timestamps are not supplied by
these quote/trade endpoints: this limitation remains explicit, not guessed away.

## Collection and evaluation

Stage 1: completed SIP quote windows spanning confirmation-1s through confirmation+2s
for EVERY frozen signal, with pagination, timestamps, hashes, immutable local files.
Stage 2: collect quotes AND trades from confirmation-1s through 15:56:00 for every
symbol-day passing any scenario's market/geometry/cost screen, independent of cash
competition or eventual outcome. No full-day download for an entry that cannot
pass any declared scenario. This is an acquisition optimization, not trade selection.
If stage 2 is needed it is mandatory before running that position. Preserve the
stage-1 entry quote; validate overlapping tick events rather than silently replacing
the entry snapshot with revisions. A per-request/page/storage ceiling yields an
explicit incomplete result, never a claim of complete coverage.

Run A/B at both adverse allowances and both signal delays; report all variants.
For primary one-second runs also repeat each leave-one-symbol-out comparison.
Use v1's paired five-session block bootstrap, seed and 10,000 repetitions. Require
positive paired net return and favorable uncertainty at both costs, no reversal
in any symbol omission, reconciled ledgers and known entry-data coverage before
claiming developmental selection benefit. A failed or inconclusive test is a
valid research conclusion; do not optimize it away. Zero trades is not validation.

This is more realistic historical execution research, NOT a fully as-received
simulation, broker-paper certification, real-time data entitlement, or a profitable
autonomous bot. No subscriptions, orders, broker changes or cloud deployment.

References: [Alpaca quote API](https://docs.alpaca.markets/us/v1.4.2/reference/stockquotesingle-1),
[trade/bar condition semantics](https://docs.alpaca.markets/us/docs/market-data-faq).
