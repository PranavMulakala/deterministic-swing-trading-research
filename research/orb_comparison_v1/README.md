# ORB data acquisition and first comparison freeze

**Follow-up:** the simulator and execution-data checks are now implemented and
run. The edge is **not established**; see [RESULTS.md](RESULTS.md) for the actual
findings, 273-test verification, data limitations and next required model change.
The original acquisition-stage record below is retained for provenance.

Completed September 7, 2026: **matching SIP data collected and the first research
comparison frozen**. No ORB profit backtest or daily scanner has been implemented
in this step. No orders, account/balance changes, deployment, paid subscription,
commit or push. This work stays inside the personal repository.

## What is now available

- COHR, CIEN, FN and AAOI: one-minute AND five-minute raw consolidated SIP bars.
- LITE refreshed with identical query dates, feed, adjustment and symbol-asof.
- SPY and QQQ five-minute bars as separate market controls.
- 41 prior sessions in November/December 2025; 170 evaluation sessions from
  January 2 through September 4, 2026. Calendar includes early closes and DST.
- 785,481 provider bars including extended hours; 12 bar files plus the calendar,
  about 82 MB. Every paginated query reached its terminal page. Hashes and fetch
  timestamps are pinned; raw provider data stays locally Git-ignored in `runs/`.

Regular-session verification (a complete day requires every expected bar):

| Stock | Complete 5-minute days / 170 | Complete 1-minute days / 170 | Absent 1-minute bars in 2026 |
|---|---:|---:|---:|
| LITE | 170 | 140 | 66 |
| COHR | 170 | 152 | 48 |
| CIEN | 170 | 71 | 470 |
| FN | 169 | 5 | 3,593 |
| AAOI | 170 | 144 | 95 |

Both controls have 170 complete five-minute evaluation sessions. All five stocks
have their first five-minute bar on all 170 evaluation days. Across warmup and
evaluation, **76,891 complete five-minute windows** match the aggregation of their
five one-minute bars for open/high/low/close/volume: zero disagreements at the
declared tolerance. VWAP aggregation was not tested. This is internal consistency
within one provider, not independent-vendor proof of every underlying trade.

FN's absent five-minute windows: December 10 at 12:05, December 26 at 11:15,
December 30 at 11:10, and January 9 at 13:20 (New York time). The frozen strict
lagged-input rule therefore has sufficient prior-20-session coverage on 144/170
FN evaluation dates, first February 10. The other four have 170/170. These are
**input availability counts**, not eligible stocks, entry signals or win rates.

An absent minute can reflect no qualifying bar-generating trades, provider
coverage or another issue; this acquisition does not establish which. Do not
manufacture flat bars or treat silence as a proven halt. Do not exclude a whole
day before entry because its later data are missing. Preserve unresolved outcomes
if an execution-relevant minute is absent. FN particularly needs that distinction.

## What was frozen

See [PROTOCOL.md](PROTOCOL.md), [spec.json](spec.json), and [FREEZE.json](FREEZE.json).

**A: the fixed opening breakout/retest rule on all lagged-eligible names.**
**B: the identical rule, restricted to first-five-minute RVOL >= 2.**

Both use one $5,000 long-only, whole-share, unleveraged research portfolio, with
defined entry/stop/2R-target/time-exit rules, cash constraints, competing signals,
and identical primary/stress costs. This is NOT the LITE dip-and-hold strategy and
does not modify the original $500 ETF strategy or paper account. No threshold
grid search, discretionary news filter, or "hold losers until recovery" is added.

Freeze scope is transparent: recorded locally after data-quality inspection,
before running any ORB P&L. It is not independently registered or tamper-proof.
The already-examined 2026 sample remains development data. A changed rule requires
a new version; this freeze must not silently be replaced after seeing outcomes.

## What remains before claims about results

1. Reconcile corporate actions/instrument history for raw-price and volume
   baselines; unknown action coverage cannot silently pass eligibility.
2. Implement the two-arm ledger exactly as frozen, retaining all rejected and
   unresolved cases. The current deliverable is data + specification, not results.
3. For execution-quality claims, obtain relevant historical quote/halts evidence
   and account for actual signal arrival, spreads, gaps, partial fills and latency.
   Bar-proxy output must stay labeled as such. Free historical SIP access observed
   here does not establish a live SIP entitlement.
4. Test news separately once point-in-time article text and receipt/version
   evidence exist; the prior metadata-only news cache is insufficient.

No claim of profitability, low-loss trading or Tuesday readiness follows from
successful data collection or passing tests. Data does not certify account rules.

## Reproduce locally

From the personal repository root; this verification is offline and does not
load `.env` or contact Alpaca:

```sh
.venv/bin/python -m research.orb_comparison_v1.verify research/orb_comparison_v1/runs/sip-20260907-02
PYTHONPATH=src .venv/bin/python -m unittest research.orb_comparison_v1.test_data -v
```

The frozen dataset manifest is `runs/sip-20260907-02/manifest.json`; its SHA-256 is
`5de081d38e028cb4de1c68a971d1ebc84fcdb8bae7caf8697c7d9ee9047334d4`.
Detailed per-session missing-minute inventories are in that directory's
`coverage.json`; its checksum is in `FREEZE.json`. The frozen files' hashes are
verified by the test suite. Lost raw data must be restored against those hashes;
a new API download may contain revisions and is a new snapshot, not an identical
reproduction. An initial restricted-network attempt remains separately recorded
as incomplete in `runs/sip-20260907-01`; it is not used by the freeze.

New downloads require explicit owner scope and a new, nonexistent output folder:

```sh
PYTHONPATH=src .venv/bin/python -m research.orb_comparison_v1.collect --output research/orb_comparison_v1/runs/NEW-SNAPSHOT-NAME
```

Only the seven allowlisted symbols' historical bars and the calendar GET endpoint
are accessible through this collector. There is no account, positions or orders
GET path, and mutation requests are rejected before transport. Existing local
credentials are loaded only for acquisition, never printed; provider error bodies
are suppressed. No plaintext credentials are stored in research outputs.

## Verification performed

- 158 existing application tests pass.
- 88 research tests pass, including 15 new acquisition/coverage/freeze tests.
- Real-data schema, timestamp ordering, pagination completion, raw/SIP provenance,
  OHLC/volume, calendar alignment, missing intervals and manifest hashes verified.
- Previous `lite_2026/snapshot.json` and the original SIP `LITE_5Min.json` still
  match their previously recorded hashes; no tracked application file changed.
- Network boundary tests use synthetic credentials and a recording fake transport.

Source for API semantics: [Alpaca historical bars documentation](https://docs.alpaca.markets/us/reference/stockbarsingle-1).
