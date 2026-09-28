# LITE: better data and $500 account feasibility

September 6, 2026. **Historical data improved; basic fractional eligibility verified;
unattended strategy execution not established. Do not deploy the current rules.**

This follow-up is in the personal repository. It preserves the original
`lite_reversal_v1` config, source, specification and results. No strategy tuning,
account changes, order submissions, purchases, subscriptions, commits or pushes.
Current credentials were used locally only for authenticated GET requests; they
were not printed or saved in the research output. Account identifiers are omitted.

## 1. Account facts measured directly

Read-only observation at 2026-09-06 20:16:39 UTC (13:16:39 Pacific):

| Check | Observed value | What it establishes |
|---|---|---|
| Account | ACTIVE, USD | Accessible paper account |
| Cash / equity / buying power | $500 / $500 / $500 | No account increase needed to keep the intended allocation |
| Effective multiplier | 1 | No current leveraged buying power |
| Positions / open orders | 0 / 0 | Empty at the observation time |
| Trading/account/user-suspension flags | All false | No reported block at that instant |
| Account fractional_trading | true | Account configured for fractions |
| LITE tradable / fractionable | true / true | Current asset eligibility |

The configuration's `max_margin_multiplier` was 4, but actual account multiplier
was 1 and buying power was $500. The configuration maximum is **not** current
permission to spend $2,000. No settings were altered. A 1x multiplier does not
by itself prove that the legal account type is a cash account.

These flags are eligibility evidence, not evidence an exact limit/stop/bracket
order was accepted. Paper and live execution can differ. Today's asset flags also
do not establish historical fractionability on every date in the backtest.

## 2. Better historical data obtained with existing access

Historical SIP requests succeeded without buying a new subscription. SIP covers
consolidated exchange activity; IEX is one venue. Alpaca documents historical SIP
access with an end time at least 15 minutes old separately from real-time SIP
entitlement. The latter was **not** verified by this historical download.
[Alpaca data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)

| Data | Downloaded records, including extended hours | Complete regular sessions |
|---|---:|---:|
| LITE raw SIP 5-minute | 28,459 | **170 / 170** |
| LITE raw SIP 1-minute | 107,051 | **140 / 170** |
| SPY raw SIP 5-minute | 32,628 | **170 / 170** |

All pages completed. Files have SHA-256 hashes. The original IEX experiment had
only 118 complete five-minute sessions. The 30 incomplete one-minute dates and
their exact missing timestamps remain listed; they are not forward-filled.
No eligibility for additional feeds or future real-time access is inferred.

## 3. Unchanged rules on the improved data

These are historical, hypothetical $500 ledgers, not real account changes.
Five-minute SIP results over all 170 sessions:

| Strategy | Shares | Cost per side | Trades | Ending cash | Net P&L |
|---|---|---:|---:|---:|---:|
| Dip entry | Whole | 0.10% | 2 | $497.39 | -$2.61 |
| Dip entry | Fractional diagnostic | 0.10% | 50 | $455.11 | -$44.89 |
| Dip entry | Whole | 0.25% | 1 | $498.04 | -$1.96 |
| Dip entry | Fractional diagnostic | 0.25% | 16 | $491.01 | -$8.99 |
| VWAP reclaim/retest | Whole | 0.10% | 0 | $500.00 | $0.00 |
| VWAP reclaim/retest | Fractional diagnostic | 0.10% | 5 | $494.60 | -$5.40 |
| VWAP reclaim/retest | Whole | 0.25% | 0 | $500.00 | $0.00 |
| VWAP reclaim/retest | Fractional diagnostic | 0.25% | 0 | $500.00 | $0.00 |

All 14 VWAP signals fail whole-share risk sizing at $500; 13 also fail the cash
constraint. The implied capital to size one share under the unchanged 0.5% rule
ranges from $665.65 to $3,259.18, median $2,049.74. This is a diagnostic—not a
recommendation to deposit more money. Increasing capital would not establish an edge.

On the **same 140-session intersection**, five-minute and one-minute execution
replays produced identical ending cash for each scenario. At baseline cost the
fractional dip version ended at $438.95 and VWAP at $494.60. Do not compare the
$438.95 intersection result with $455.11 on 170 dates as if only execution resolution
changed. No intrabar stop/target ordering improvement rescued the strategy here.
One-minute bars still cannot resolve everything happening within a minute.

The LITE-minus-SPY 10:00–15:55 endpoint return averaged +0.298 percentage points
across all 170 sessions, and +0.697 points across 131 opening-dip sessions, before
costs. That is descriptive support for investigating rebounds, not evidence for
the tested stops, limits and sizing. These are not risk-matched portfolios.

Compared with the earlier +$1.18 IEX fractional dip result, this data replication
is materially worse. Feed, raw/adjusted semantics and coverage changed together;
do not attribute the full difference to a single factor. No parameters were changed
to make the new results positive. Higher modeled costs change which limits fill;
the cost scenarios are not a fixed-trade cost comparison.

## 4. Quote-level entry check

Downloaded **364 SIP quote records** across ten-second windows around **all 14
qualifying VWAP signals**, regardless of outcome. Every window finished pagination.
No news headlines, profitable-trade selection or future prices picked the windows.

The fixed one-second decision/transport-delay diagnostic requires a regular,
positive, noncrossed two-sided quote no more than one second old, strictly using
timestamps at or before the decision. Nanosecond ordering is preserved.

| Assumed delay | Usable quotes | Asks within original raw entry cap | Unknown |
|---|---:|---:|---:|
| 0.1 seconds | 3 / 14 | 1 | 11 |
| 1 second — primary diagnostic | 4 / 14 | 0 | 10 |
| 2 seconds | 8 / 14 | 2 | 6 |

For the four primary observations, median full bid-ask spread was 18.44 bps
(0.1844%), maximum 36.65 bps. This is a tiny signal-conditioned sample, not the
typical full-day spread or a bound on total costs. Unknowns reflect this declared
freshness/window criterion, not proof that no executable quote existed. An unchanged
older quote may remain valid; this diagnostic deliberately does not assume it does.
Passing an ask/limit comparison would still not prove a fill, broker receipt timing,
or stop/target protection. Full-day quote-driven P&L was not implemented.

## 5. What $500 can and cannot do

**Basic fractional eligibility: verified.** You do not need $25,000 merely because
older tutorials mention PDT. Alpaca states it implemented the replacement intraday
margin framework on June 4, 2026. Its current non-leverage FAQ removes the old
trade-count restriction while retaining buying-power/risk requirements. The account
response also omits the deprecated day-trade fields; omitted is not zero.
[Alpaca rollout](https://alpaca.markets/blog/finra-retires-the-pdt-rule-introducing-alpacas-new-intraday-margin-framework/),
[non-leverage FAQ](https://docs.alpaca.markets/us/docs/intraday-margin-rule-for-non-leverage-margin-accounts)

**Fractional protective-order compatibility: not established.** The current
fractional guide and order/TIF table list DAY market, limit, stop and stop-limit
orders. However, the fractional guide still contains an inconsistent market-only
sentence, and the create-order reference still describes fractional qty as
market/DAY-only. None of those statements proves fractional bracket, OTO or OCO
support. An older Alpaca staff response describes complex fractional orders as
unsupported; its age prevents treating it as definitive current account evidence.
[Fractional guide](https://docs.alpaca.markets/us/docs/fractional-trading),
[order table](https://docs.alpaca.markets/us/docs/orders-at-alpaca),
[create-order reference](https://docs.alpaca.markets/us/reference/postorder),
[older staff explanation](https://forum.alpaca.markets/t/why-are-stop-loss-and-take-profit-not-allowed-with-market-orders/14600)

**Current software compatibility: no.** `src/swingbot/alpaca_paper.py` deliberately
accepts whole-share market/GTC OTO entries and rejects fractional entries. Those
constraints belong to the original overnight ETF strategy; they were not weakened
for this separate intraday experiment. Simple fractional DAY orders would require
a separate execution design, including partial fills, stop placement, cancellation
races and close-of-session failure handling. Manually stitching entry and stop
orders together introduces a period without protection; it is not equivalent to
a broker-native atomic bracket.

There was no order submission—not even an intentionally invalid test order.
GET-only checks cannot conclusively verify an exact order's acceptance. The
[support question](BROKER_QUESTION.md) is prepared but **not sent**. A narrowly
authorized paper-order test could follow broker clarification if still useful,
but current economic results do not justify enabling unattended trading.

## Verification and scope

- 21 new targeted tests pass; existing 158 application, 36 strategy and 4 profile
  tests pass: **219 total**. No broad additional model audit was run.
- Ledger checks cover **24 scenarios, 196 trade records and 3,600 daily rows**.
  A separate Decimal calculation replayed every debit/credit and terminal cash.
  Repeated scenario records are not independent market observations.
- Repeated offline SIP studies produced identical result JSON. Original v1 input,
  rules, source and result hashes remain unchanged and its verifier still passes.
- No tracked application file changed. Existing untracked audit/research output was
  preserved. Nothing committed/pushed; no account mutation or order sent.

This does not prove bug-free code, execution fidelity or future profitability.
News remains untested because point-in-time original text/delivery evidence is
missing. This year's data were already studied, so none of these runs is labeled
an independent holdout.

## Reproduce

The detailed market/account data remain local and ignored. Offline analyses need
the matching local data; they never load credentials. Use fresh output paths:

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s research/lite_execution_data -p 'test_*.py' -v
.venv/bin/python -m research.lite_execution_data.study --data research/lite_execution_data/runs/sip-bars-01 --output research/lite_execution_data/runs/my-study
.venv/bin/python -m research.lite_execution_data.quotes --study research/lite_execution_data/runs/my-study/results.json --quotes research/lite_execution_data/runs/quotes-01 --output research/lite_execution_data/runs/my-quotes.json
```

Authenticated collection is an explicit separate command in `collect.py`; output
directories/files must not already exist. No automatic refresh or order fallback.

Evidence:
- [Sanitized account observation](runs/probe-03/probe.json)
- [Historical data manifest](runs/sip-bars-01/manifest.json)
- [SIP study: all scenarios, trades and sizing diagnostics](runs/study-01/results.json)
- [Quote observations and unknowns](runs/quote-analysis-01.json)
- [Declared method](METHOD.md)

SIP results SHA-256: `cd3b26ca557f4e4044dc3b0253b319d07d01c037cb397ca0630e1db15df7b68d`.
Quote results SHA-256: `f5ef8ad25f533cfd90d77db0b040e8ca8970b472bc147aeadd9f4493207f1de4`.
