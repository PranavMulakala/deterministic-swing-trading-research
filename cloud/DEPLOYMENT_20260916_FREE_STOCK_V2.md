# September 16 free stock-only paper deployment

## Outcome

The separately versioned free stock-only paper profile is deployed at
`/opt/agentic-stock-free-v2-20260916` and its provider/runtime timers are enabled.
It preserves the frozen combined stock/options profile, which remains blocked
until approved Tradier production market data is available.

The free profile has one isolated simulated `$10,000` stock account. It uses:

- fresh Alpaca Basic IEX bids and asks (bid for the conservative mark, ask for
  the simulated entry price);
- delayed consolidated SIP completed-session history;
- a bounded, paginated 24-hour Alpaca direct-news metadata query;
- Nasdaq's public estimated earnings calendar, cached for up to six hours.

The feed is explicitly labeled
`ALPACA_BASIC_FREE_IEX_QUOTES_SIP_HISTORY_V2`. IEX is a single venue and is not
equivalent to consolidated SIP execution. The runtime has no broker/order
client, no options, no model calls, and no promotion path.

## Measured activation state

- Real provider cycle: `PROVIDER_CYCLE_READY` for AAOI, CIEN, COHR, FN, and LITE.
- Real runtime cycle: `PAPER_STOCK_CYCLE_COMPLETE`.
- Initial simulated account: `$10,000.00` cash, `$0.00` deployed, zero closed
  trades, zero completed end-of-day sessions at the intraday activation point.
- All five stocks correctly abstained because one or more frozen technical or
  executable-ask conditions failed. No fill was fabricated.
- Both five-minute timers were enabled and showed a next trigger.
- Existing collector and combined paper timer were not restarted or modified.

## Verification

- 158 existing application tests passed.
- 11 focused v2 runtime/provider tests passed locally.
- 7 frozen v2 lifecycle tests passed on the server.
- `AGENTIC_STOCK_PAPER_FREE_V2_FREEZE_OK` passed locally and on the server.
- The uploaded archive SHA-256 was
  `64c8c96f04a70cce00c0863bcebd89988dae6f2916614046e5fbd6bbade1d6f5`.
- Server identity was reverified against the previously recorded ED25519
  fingerprint before transfer.

The broad research-only discovery run still has known pre-existing failures in
unrelated frozen observer/source-snapshot and indicative-shadow tests. The
authoritative 158-test application suite and all new focused tests passed.

Nothing here establishes profitability or enables a real or broker-paper order.

