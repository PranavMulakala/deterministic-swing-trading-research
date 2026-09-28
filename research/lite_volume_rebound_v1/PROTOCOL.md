# LITE opening dip, rebound and volume diagnostic v1 — September 27, 2026

This is a **development replay of already examined prices**, not a selected
strategy, paper order, or live order. It reads pinned local, raw SIP five-minute
regular-session bars through September 4, 2026. The loader verifies source
hashes and 170 complete sessions. It never reads credentials, connects to a
service, or submits an order.

## Predeclared test assumptions

At 10:00 New York time, inspect only the first six **completed** five-minute
bars. A candidate needs (1) a low at least 1% below the 09:30 opening price,
(2) the last three completed closes strictly rising, with the latest still
below the open, and (3) cumulative first-30-minute volume at least 1.5 times
the mean volume over the same interval on the preceding **20 completed full
sessions**. A missing 20-session history disqualifies the day. There is no
historical point-in-time news filter.

The last completed close becomes a buy limit for **only the 10:00–10:05 bar**.
It is below the session open by the signal rule. If that bar's low stays above
the limit, record an unfilled attempt. Otherwise use the lower of its open and
the limit as an optimistic price proxy, plus the tested cost per side. A
bar-low crossing cannot prove a real limit fill, its timing, or queue priority.
Never use the 10:00 bar's high to trigger the sale because the order of high,
low and fill within that bar is unknown.

Use a hypothetical $10,000 fully funded ledger, exactly five whole shares,
one position at a time, no borrowing, no averaging down, and no same-day
reentry. Skip a buy unless the opening-price target, after modeled sale cost,
exceeds the modeled entry debit per share. On the first **later** bar whose
high reaches the opening-price target, model a sale at that target less cost;
ignore favorable gap price improvement. Test 0, 10, 25 and 50 basis points
per side. These are cost sensitivities, **not executable bid/ask quotes**.
There is no automatic stop, loss cap, holding deadline, or forced liquidation.
An unsold position remains open and is marked to the final close less sale
cost. Its marked loss is included in total equity, not counted as a closed
trade or a profitable result.

Replay the complete 170-session saved sample and the trailing 90-calendar-day
window as independent **flat-start ledgers**. The latter uses the full saved
history for its first day's trailing-volume warmup, always strictly before
that day. It is an overlapping development slice, **not an untouched holdout**.
The result includes decisions, cash/equity by session, skipped attempts,
closed trades, unresolved position, worst daily equity drawdown, and the
worst later-bar observed low relative to cost-adjusted entry.

## Limits and next gate

SIP historical bars do not establish current IEX decision-time coverage,
actual spread, executable quotes, intrabar order of events, queue fills,
halts, corporate-action-adjusted holding P&L, or future edge. The opening
target must be reconciled against an actual fill before any prospective paper
experiment. Even a future good-til-canceled paper target would require order
state reconciliation and replacement: Alpaca says GTC orders cancel after 90
days and corporate actions can cancel them. No broker adapter is enabled here.

## Optional bounded data refresh

`refresh.py` is a separate GET-only diagnostic for LITE raw five-minute SIP
and IEX bars from January 1 through September 25, 2026. Run it with
`PYTHONPATH=src .venv/bin/python -m research.lite_volume_rebound_v1.refresh
--output NEW_DIR` only when a fresh output directory is chosen. It uses the
existing allowlisted `ReadOnlyClient`, loads only the two paper market-data
credentials locally, requests a bounded exchange calendar and paginated bars,
and saves each decoded API page plus hashes. It does not call account or order
endpoints. The old pinned snapshot and this version's replay result are never
rewritten.

The report checks every regular five-minute SIP slot on standard sessions,
reports missing IEX slots rather than filling them, and compares signals only
where each feed has the current and preceding 20 first-half-hour windows.
It also verifies the old pinned file hash and checks that September 4 regular
SIP bars are data-equivalent to that pinned day. Incomplete SIP coverage or
an overlap mismatch makes the CLI exit with failure after saving a diagnostic
report. Missing IEX bars are reported and disqualify affected signal windows.
A new historical endpoint
response is still development data; it is not prospective paper execution,
an executable quote, or a fresh holdout.

## Monday September 28 one-shot IEX observer

The observer is a **manual, one-shot read** between 10:00 and 10:05 Eastern
time on September 28. Exact command from the project root:

```sh
PYTHONPATH=src .venv/bin/python -m research.lite_volume_rebound_v1.observe_monday --refresh output/lite-volume-rebound-refresh-20260927 --output output/lite-monday-observation-20260928.json
```

It verifies all saved refresh manifest hashes, the passed refresh status, and
the last 20 completed IEX opening mornings through Friday September 25 before
any network call. During the five-minute window it GETs only Monday's calendar,
market clock, and bounded LITE IEX five-minute morning bars. It requires an
open standard session, a fresh clock, and exactly six distinct completed bars
from 09:30 through 09:55. Missing, duplicate, malformed or late data produces
`BLOCKED`. A valid observation returns `NO_SIGNAL` or `SIGNAL_PROPOSAL` using
the same dip, rising closes and 1.5-times-volume rule. A signal contains a
research buy limit below the open, **never an order**. The output file must
not exist already. If a manual retry is needed within the window, choose a
new output filename; there is no scheduler or automatic retry.

This is an IEX decision-time observation. Historical SIP results must not be
substituted for it. A proposal does not verify current cash, quote or actual
order fill, and it does not authorize paper or live execution.
