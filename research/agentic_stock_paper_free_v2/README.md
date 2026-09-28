# Free stock-only paper runtime v2

This separately versioned runtime allows the frozen `$10,000` stock-swing
strategy to operate without waiting for an options provider. It does not alter
or replace `agentic_paper_runtime_v1`; the combined stock/options experiment
remains frozen and blocked until Tradier supplies validated option chains.

The input adapter uses only no-subscription sources:

- Alpaca Basic real-time IEX executable bids and asks. The bid is the
  conservative current paper mark and the ask is the simulated entry price;
- Alpaca Basic delayed SIP daily history for SMA50, ATR14, and prior-session
  dollar volume;
- a fresh, paginated 24-hour Alpaca news query for the fixed adverse-headline
  veto;
- Nasdaq's public earnings calendar, with at least seven calendar days of
  coverage. A missing or malformed calendar blocks the entire cycle.

This v2 adapter does not treat an inactive last trade as a fresh price merely
because the current IEX quote is fresh. It binds both its mark and freshness to
the executable quote. IEX is one venue, not the consolidated SIP. This is a separately labeled
forward paper experiment and is not evidence of broker fill quality. It may
simulate stock fills, marks, management, and exits, but it has no broker/order
client, no model calls, no options, and no promotion path.

Every cycle requires all five symbols, at least 50 completed daily sessions,
fresh quotes, complete news coverage, and current earnings coverage. Missing
data is `BLOCKED_DATA`, creates no trade, and does not count a session.
