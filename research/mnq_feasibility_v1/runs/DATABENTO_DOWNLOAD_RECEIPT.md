# MNQU6 pilot download — completed and checked

Status: **DOWNLOAD_AND_STRUCTURAL_VALIDATION_COMPLETE**. This is a data-acquisition
result, not evidence of a profitable strategy or permission for live trading.

The user approved the six requests if the refreshed combined estimate stayed
below $12. It remained $11.066133189946. Six batch jobs were submitted once.
Completed jobs report **$11.06613318994642 of data usage (about $11.07)**.
This is the provider-reported usage cost; credit application and card settlement
have not been independently checked.

## What is saved

- Dataset: CME Globex `GLBX.MDP3`; exact symbol `MNQU6`, raw-symbol selection.
- Five MBP-1 files, August 31 through September 4, 2026, each 13:30–20:00 UTC
  (09:30–16:00 New York). August 31 is the previous-session warmup.
- Five daily definition files covering the same dates.
- Six sets of provider manifests, query metadata, and data-condition reports.
- **28 downloaded files; 1,561,641,549 bytes**, approximately 1.56 GB compressed.
- Original files and acquisition state: `../data/databento-pilot-20260908/`.
  That data directory is ignored by Git. Credentials are not included in reports.

## Measured verification

All 28 sizes and SHA256 hashes match Databento's file listings, independently
rechecked after the downloads. All six jobs are done, their saved query metadata
matches the requested scope, and no partial download files remain.

The validator streamed through every MBP-1 record, checking its length, record
type, instrument, publisher, capture-time bounds, prices, and selected quality
diagnostics. It checked the vectorized binary layout against Databento's official
decoder at the beginning and end of each processing block. Counts exactly match
the completed batch jobs. This is not a record-by-record comparison with another
exchange feed.

| Session | Market-data records | Minutes containing trades |
|---|---:|---:|
| 2026-08-31 | 17,619,987 | 390 / 390 |
| 2026-09-01 | 18,559,230 | 390 / 390 |
| 2026-09-02 | 15,650,010 | 390 / 390 |
| 2026-09-03 | 16,246,518 | 390 / 390 |
| 2026-09-04 | 14,439,294 | 390 / 390 |
| Total | **82,515,039** | **1,950 / 1,950** |

Records include book changes as well as trades; they are not 82.5 million trades.
All five definitions decode successfully and confirm instrument ID `42004800`,
outright futures class, MNQ asset, USD currency, 0.25-point minimum price increment,
$2 per index point, $0.50 per tick, and expiration September 18, 2026 at 13:30 UTC.

In the scanned records, the tested diagnostics found zero backward capture/event
timestamps, bad-receive-timestamp flags, maybe-bad-book flags, snapshot flags,
undefined best bid/ask prices, locked/crossed books, and off-tick prices.
The provider's daily condition reports say `available` for all requested dates.

## Limits and next work

There are **26 records whose event timestamps fall outside the requested capture-
time window**. They have been retained in the original files. Capture time means
when the data provider received an event; event time means when the exchange says
it happened. The importer must handle those boundaries explicitly. Minute coverage
and provider availability labels do not prove that every exchange event is present.

The replay importer, trade/book event interpretation, exchange-calendar check,
execution assumptions, and verified broker fees still need work. No replay,
strategy performance result, paper order, or live order was produced by this step.
The frozen strategy and risk configuration were not changed.

Detailed evidence: [validation JSON](databento-validation-20260908.json),
[initial estimate](databento-quote-20260908.json), and the private acquisition
folder's `approval-and-quote.json`, `download-summary.json`, and per-job files.
The validation JSON records decoder versions and the validator's source hash.

Format references: [Databento MBP-1](https://databento.com/docs/schemas-and-data-formats/mbp-1),
[instrument tick values](https://databento.com/docs/examples/instrument-definitions/contract-notional).
