# Input and data acquisition checklist

Databento authentication succeeded using the local `MNQ_RESEARCH_KEY`.
The user subsequently approved the six-request pilot with a refreshed estimate
below $12. **The data is now downloaded and structurally checked**:
[download receipt](runs/DATABENTO_DOWNLOAD_RECEIPT.md). All 28 downloaded files
match the provider's sizes and hashes; 82,515,039 market records match the job
counts. The adapter and first observed-data replay are now complete; see
[pilot-01](runs/pilot-01/REPORT.md). No complete patterns occurred in the four
evaluation sessions. That leaves risk-fit percentages unknown and after-cost
trading behavior untested on this sample, rather than replacing them with demo results.

The saved [API estimate](runs/databento-quote-20260908.json) is
**$11.066133189946 (about $11.07)** for the five MBP-1 sessions below plus
contract definitions from August 31 through September 4. Credit balance and
licensing readiness were not independently verified by those metadata calls.
The later completed jobs report $11.06613318994642 in usage; payment/credit
settlement remains unverified. Neither number establishes strategy performance.

## Recommended starting purchase route

Use **Databento historical usage-based data**, starting with a small batch.
This recommendation is about the data needed for our own program, not a claim
that Databento makes an algorithm profitable or is a brokerage platform.

1. Create a personal Databento account and complete its eligibility/licensing
   questions accurately. Keep it separate from employer accounts. Do not paste
   API keys, passwords, or payment details into chat.
2. Use the historical API with dataset `GLBX.MDP3`, `stype_in=raw_symbol`,
   `symbols=MNQU6`, and **MBP-1**. The inspected portal request builder selected
   the whole MNQ product family and found no exact MNQU6 product. Confirm the
   contract's instrument ID and specifications from definitions before replay.
   MBP-1 supplies trades and every top-of-book update;
   do not substitute minute bars, sampled BBO, or trade-only data for this test.
3. Request 09:30-16:00 New York for each of August 31, September 1, 2, 3, and 4,
   2026 (13:30-20:00 UTC on these dates). Obtain contract definitions and verify
   the exchange session calendar. August 31 is warmup. No parent-symbol wildcard
   that silently buys all MNQ expiries, options, or spreads.
4. View and save the **API cost estimate before submitting a paid request**.
   Actual billing depends on data delivered. Initial suggestion: cap this pilot's out-of-
   pocket historical-data purchase at $25; this is a proposed spending ceiling,
   not a price estimate or authorization to charge you. If it costs more, inspect
   the request's symbols/hours/schema before considering a different cap.
5. Prefer a batch export so the original files can be retained and checksummed.
   Preserve the job manifest, definitions, symbology mappings, CSV/DBN files,
   available condition/quality flags and any vendor gap notices. Export integer
   nanosecond timestamps and unrounded prices; retain original sequence fields.
6. Stop at the quote/account setup if anything is unclear. No live subscription,
   indicator purchase, broker funding, or automatic trading is required now.

The provider currently advertises $125 of new-user credits, subject to eligibility,
shared team limits and six-month expiry. Check what your account actually receives.
Do not assume a free trial or a headline commission covers every charge.

Sources: [Databento pricing](https://databento.com/pricing),
[credits and definitive quotes](https://databento.com/docs/faqs/usage-pricing-and-data-credits),
[MBP-1 fields](https://databento.com/docs/schemas-and-data-formats/mbp-1),
[CME dataset](https://databento.com/docs/venues-and-datasets/glbx-mdp3).
Checked September 8, 2026. Pricing and eligibility can change.

## What the offline engine accepts

The reference engine accepts a **normalized JSON tape**, not a raw Databento
export directly. The implemented Databento adapter uses compact trade/quote arrays
for this large pilot, applying the data interpretation in `IMPORT_PROTOCOL.md`.
Its prepared replay reuses the original signal and screening functions; execution
results were compared against the reference engine on fixtures. A `.csv` renamed
to `.json` is not an import. Independent exchange completeness and broker costs
remain separate unresolved checks.

```json
{
  "schema_version": 1,
  "evidence": "HISTORICAL",
  "source": "Provider, dataset, job ID, original file hashes, mapping and quality audit",
  "time_basis": "exchange_event_time",
  "sessions": [
    {
      "date": "2026-09-01",
      "previous_date": "2026-08-31",
      "contract": "MNQU6",
      "regular_session_complete": true,
      "events": []
    }
  ]
}
```

The empty events list above shows structure only. It is not a valid market sample.
Include the previous day's full events as another earlier session in the list.

Trade event fields: `type="trade"`, integer `ts_ns`, integer `seq`, positive integer
`price_ticks`, positive integer `size` in contracts.

Quote event fields: `type="quote"`, integer `ts_ns`, integer `seq`, integer
`bid_ticks`, `ask_ticks`, `bid_size`, `ask_size`. Preserve invalid/empty/crossed
books explicitly where representable; do not drop them to beautify results.

One price tick is 0.25 index points; a price of 25,000.00 becomes 100,000 ticks.
Convert with exact decimal/integer arithmetic and reject off-tick prices. Never
confuse the vendor's integer price scaling (e.g. 1e-9) with our tick integer.

Events must be strictly ordered by `(ts_ns, seq)`, with a deterministic sequence
that preserves source ordering of same-time trade and book updates. The importer
must explain this transformation and retain the original sequence separately.
Do not silently reorder records to invent unavailable causal sequencing.

Sessions use New York date and a verified full 390-minute regular session.
`previous_date` must come from the exchange calendar, not the previous calendar
day or simply the preceding file. The same dated contract is required on both.
The current reader is an in-memory pilot reader; large histories need a streaming
adapter and memory profiling before expansion.

## Checks before trusting a vendor import

- All files and exact request boundaries match the retained manifest; hashes
  match; every requested session and page is accounted for.
- Definitions confirm MNQ, the tick/multiplier, outright instrument, and expiry.
- Decode trade/cancel/correction and book-reset/snapshot/quality flags according
  to this dataset; do not count replay snapshots as newly executed trades.
- Preserve missing/invalid book intervals, timestamps, and trade eligibility.
- Reconstruct trade minutes and compare volume/OHLC against independent provider
  aggregates diagnostically. Investigate differences; never silently overwrite.
- Distinguish exchange timestamps, provider capture timestamps and local arrival.
  The present engine models exchange-time history plus explicit delay only.
- Verify trading costs from the intended broker's complete schedule, then version
  the fee configuration before using it on new outcome data.

A user-entered `regular_session_complete=true` is only a declaration. The engine
cannot infer or certify the completeness of a vendor request from that field.
