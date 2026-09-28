# Quote/trade ORB v2 — completed research, NO-GO

September 7, 2026. **The separately frozen execution version is built, tested and
run. It does not establish a profitable strategy.** All 28 variants finish with
reconciled cash and no unresolved positions. The v1 study remains unchanged.

## The answer in dollars

Starting balance: one $5,000 research portfolio per arm. Same frozen five-stock
universe, eligibility, breakout/retest pattern, stops, targets and risk limits.

| Signal delay | Additional slippage per side | A: no RVOL filter | A trades | B: RVOL >= 2 | B trades |
|---|---:|---:|---:|---:|---:|
| 1 second, primary | 10 bps | **$4,909.17 (-1.82%)** | 9 | $5,000.00 | 0 |
| 1 second, primary | 25 bps | $4,986.20 (-0.28%) | 3 | $5,000.00 | 0 |
| 2 seconds, sensitivity | 10 bps | $4,861.58 (-2.77%) | 8 | $5,000.00 | 0 |
| 2 seconds, sensitivity | 25 bps | $4,974.84 (-0.50%) | 3 | $5,000.00 | 0 |

These costs are additional to observed bid/ask spreads, plus 1 bp fees per side.
Higher-cost runs admit fewer setups because the unchanged cost-to-stop gate
rejects more entries. Smaller losses at higher costs do not imply worse fills
improve the same trades. No scenario or threshold was selected for its return.

**B did not discover winning trades; it stayed in cash.** It outperformed the
losing A baseline by not trading. The primary 10 bps paired bootstrap interval
favors that cash-versus-loss contrast, but that is not a positive-return trading
edge. At 25 bps the interval crosses zero, and omitting AAOI removes even the
return contrast. The frozen acceptance conditions are not met.

## What happened to the opportunities

All 850 stock-days are accounted for. There are 145 fixed price-pattern signals
across the five stocks. Only seven also pass RVOL >= 2.

At the primary one-second / 10 bps setting, before account sizing:

- 76 fail the 0.15% spread limit.
- 45 have a stale quote and 10 have no qualifying prior quote in the window.
- One has conflicting quotes at the same timestamp; it is unknown, not resolved
  by choosing a convenient quote.
- Three fail modeled cost relative to stop distance.
- Ten pass these market checks; one cannot fit the whole-share risk budget,
  leaving nine actual modeled entries.

Of B's seven signals, six fail the spread cap and one lacks a qualifying prior
quote. That is why it makes zero trades. These are the declared diagnostic
instants, not a claim that the spread stayed wide throughout every minute.

Primary A / 10 bps P&L by stock: AAOI -$61.02 (five trades), LITE -$18.50 (two),
CIEN +$10.47 (one), COHR -$21.78 (one), FN no trades. One winning CIEN trade is
not enough to identify it as the best ORB stock.

## What was implemented and verified

- A separate [frozen protocol](PROTOCOL.md), [execution configuration](execution.json)
  and [freeze record](FREEZE.json), created before new tick acquisition/P&L.
- GET-only collection for all 145 entry windows, then all 15 stock-days admitted
  by any declared scenario. No choice based on eventual profit.
- 3,329 entry-window quotes plus 993,359 continuation quotes and 1,799,142 trades;
  entry/continuation windows overlap intentionally. About 293 MB of provider files,
  retained locally and Git-ignored. Every planned request reached its final page.
- SHA-256 checks, exact planned file sets, symbol/feed/date checks, nanosecond
  order validation, and exact agreement between entry and continuation overlap.
- Quote-based entry prices, odd-lot-aware trade stop triggers, bid-based exits,
  explicit signal/exit delays, conservative displayed capacity, partial entry
  cancellation and partial-exit accounting. No invented missing OHLC bars.
- Same $5,000 capital, cash settlement, risk caps, one-attempt rule, stop/target
  levels, position limit and daily loss halt. No live order path.
- **302 tests pass:** 158 application and 144 research tests. The latter include
  29 new v2 tests, including partial fills and unresolved-exit fixtures.
- All 28 ledger variants independently reconcile 208 event instances. A separate
  source-data verifier checks **all 142 actual fill-event instances and 71 first
  exit-trigger instances** against underlying quotes/trades, covering 13 distinct
  traded stock-days. Counts include repeated cost/omission scenarios, not 71
  independent trades. No actual run needed a partial fill; those paths are tested
  synthetically, not claimed to be validated by real partial-fill examples.
- All original v1 spec/protocol/engine/runner checksums remain unchanged. No tracked
  application file changed. This is a local implementation/source verification,
  not an external model audit or a claim of bug-free software.

## Limits that still matter

This is a historical top-of-book model, not broker fills. Displayed size units
are deliberately treated as one-share lower bounds; queue competition and exact
lot normalization are not certified. Quotes can become stale: the replay records
stale-mark intervals, rejects new entries lacking fresh equity marks, and measures
drawdown only where marks are fresh. It never describes stale marks as live.

The signal bars are finalized historical bars, not original delivery-time data.
Halt messages, order routing, broker-native stop behavior and queue priority are
not proven by these endpoints. No live SIP entitlement or operational readiness
follows from historical access. The five related stocks are a hand-picked pilot,
and 2026 was already explored: this is not untouched out-of-sample evidence.
News remains excluded rather than labeled neutral or backfilled with revised text.

The execution mismatch that stopped v1 is addressed for this dataset, but the
broader goal of a profitable unattended trading bot is **not** established.
Do not loosen the spread/risk rules or deploy this configuration to manufacture
a successful outcome. More indicators or another LLM do not change these results.

## Files and reproduction

- [Results summary](runs/replay-01/report.json)
- [All ledgers and stock-day outcomes](runs/replay-01/results.json)
- [Independent raw-source verification](runs/replay-01/source_verification.json)
- [Code and result checksums](RESULT_PINS.json)

Offline commands from the personal repository root:

```sh
PYTHONPATH=src .venv/bin/python -m unittest research.orb_quote_v2.test_quote_replay -v
.venv/bin/python -m research.orb_quote_v2.run --output research/orb_quote_v2/runs/NEW-REPLAY
```

The first command does not access credentials. The second verifies the pinned
local snapshots and creates a new immutable output directory. It may take several
minutes to check/replay the tick history. `verify_execution.py` supplies the
separate raw-price/first-trigger check. Acquisition is a distinct command and
uses existing local credentials only for allowlisted data GETs.

No account access, balance changes, orders, paid subscriptions, cloud deployment,
git commit or push were performed. Everything remains in the personal checkout.
