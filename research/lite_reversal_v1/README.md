# LITE opening-reversal experiment — start here

**Built and tested September 6, 2026. Decision: RESEARCH_ONLY; do not deploy v1 unchanged.**

This is an offline experiment in the personal repository, separate from the ETF
strategy and Alpaca paper runner. It does not place orders, read `.env`, download
data, or start background services. No strategy parameters were changed after
seeing these results. The existing trading configuration is unchanged.

## What we built

- A precise [strategy specification](SPEC.md) and [fixed configuration](config.json).
- A standard-library-only [simulator](experiment.py) with $500 cash/risk sizing,
  signal-before-entry ordering, daily-reset VWAP, entry limits, entry-bar stops,
  stop gaps, conservative target fills, costs and session exits.
- A dip-buying comparator and the main VWAP reclaim/retest candidate, both run at
  10 and 25 basis points per side (0.10% and 0.25%), with whole shares and a
  separately labeled hypothetical fractional mode. All eight scenarios published.
- Complete trade and daily cash ledgers, rejected-order reasons, monthly results,
  descriptive block-bootstrap intervals and pinned input/source hashes.
- [36 regression tests](test_experiment.py) and a separate
  [Decimal accounting/fill verifier](verify_run.py) that does not import the engine.

## Results, including the inconvenient parts

The snapshot covers January 2–September 4, 2026. Only 118 of 170 calendar sessions
have every regular-hours five-minute bar. All 52 excluded dates are listed in the
local result JSON. We cannot know full-day coverage at entry: this is a retrospective
data-quality selection, not an unbiased, complete-year execution replay.

| Strategy | Shares | Cost each side | Trades | Hypothetical final cash | Net P&L |
|---|---|---:|---:|---:|---:|
| Simple opening-dip entry | Whole | 0.10% | 0 | $500.00 | $0.00 |
| Simple opening-dip entry | Fractional diagnostic | 0.10% | 29 | $501.18 | +$1.18 |
| Simple opening-dip entry | Whole | 0.25% | 0 | $500.00 | $0.00 |
| Simple opening-dip entry | Fractional diagnostic | 0.25% | 12 | $508.91 | +$8.91 |
| VWAP reclaim + retest | Whole | 0.10% | 0 | $500.00 | $0.00 |
| VWAP reclaim + retest | Fractional diagnostic | 0.10% | 2 | $496.13 | -$3.87 |
| VWAP reclaim + retest | Whole | 0.25% | 0 | $500.00 | $0.00 |
| VWAP reclaim + retest | Fractional diagnostic | 0.25% | 2 | $495.32 | -$4.68 |

**Whole-share feasibility fails for these rules and this allocation.** At baseline
cost the dip strategy generated 85 signals: 54 sized to zero, 29 already failed
the required price-level relationship, one failed the entry cap, and one opened
outside the permitted levels. The main VWAP strategy generated just three signals;
all three sized to zero. Zero quantity reflects cash and/or the permitted stop
risk, not necessarily share price alone. Stops were not tightened to force a fill.

The fractional dip baseline won 6 of 29 trades (20.7%); its profit factor was 1.027.
One February trade contributed +$18.37, larger than the entire +$1.18 net result.
Average net R was slightly negative (-0.010); dollar P&L and mean R can differ in
sign because actual risk dollars vary by trade. Neither statistic establishes an edge.

The cost-stress dip result improved because the higher allowance changed entry
caps and **which trades filled**, reducing 29 fills to 12. It is not evidence that
paying higher costs improves the same trades. Do not select that scenario as a
historical winner. A fixed-fill cost attribution would be a different diagnostic.

The VWAP candidate's two fractional trades both lost. Two observations are far
too few for useful performance inference. Its narrow bootstrap interval should
not be mistaken for certainty: resampling two observed losing trades cannot
invent the unseen range of outcomes.

The descriptive baseline-cost 10:00–15:55 return averaged +0.096% across all 118
covered days, and +0.726% across the 85 opening-dip days. This suggests your bounce
observation is worth studying, but those endpoints have no protective stop and
are not risk-matched portfolios. It does **not** establish a profitable, low-loss
entry/exit strategy.

## What is missing, explicitly

1. **News experiment: BLOCKED_DATA.** The 228 news records have metadata, not
   original headlines/content or historical receipt timestamps. No sentiment was
   invented and no later article was backdated. Point-in-time news versions are
   required to test whether event type improves the identical price strategy.
2. **Execution-grade data.** The snapshot is all-adjusted IEX data, not raw
   consolidated quotes/trades. Dollar sizing is illustrative. Missing sessions,
   bar revisions, spread, latency, queue priority and partial fills remain issues.
   The assumed cost levels are not verified bounds on real execution costs.
3. **Unseen validation.** We already looked at 2026 descriptive data. Calling a
   slice of it a holdout would not make it independent. No unseen evaluation was run.
4. **Broker feasibility.** Fractional results do not establish support for the
   required entry and protective orders, cash settlement or account permissions.
   No broker connection or order was attempted by this experiment.

The useful next step is to resolve data/account feasibility, then declare a new
experiment if warranted. Do not keep loosening rules on this same year until a
profitable curve appears. No further LLM audit is required to recognize the present
economic/data limitations; software correctness and profitability are different claims.

## Verification performed

- New experiment: **36/36 tests passed**.
- Existing application suite: **158/158 tests passed**.
- Existing LITE descriptive profile: **4/4 tests passed**.
- **198 tests total**, plus the separate Decimal verifier replayed **all 45
  simulated trade records and 944 daily rows across eight scenarios**. These
  include repeated trades across scenarios, not 45 independent market events.
- Repeated offline runs produced byte-identical JSON and Markdown reports.
- `git diff --exit-code` confirmed tracked application files unchanged; prior
  untracked research and audit output were preserved. No credentials accessed,
  commits/pushes made, or orders sent.

This is targeted verification, not a promise of 100% test coverage or bug-free code.

## Reproduce locally

Run from the repository root using its existing Python 3.12 virtual environment:

```sh
.venv/bin/python -m unittest discover -s research/lite_reversal_v1 -p 'test_*.py' -v
.venv/bin/python -m research.lite_reversal_v1.experiment --output research/lite_reversal_v1/runs/my-run
.venv/bin/python -m research.lite_reversal_v1.verify_run research/lite_reversal_v1/runs/my-run
```

Use a new output directory for each run; existing results are never overwritten.
The pinned `research/lite_2026/snapshot.json` must already exist. Missing or changed
data cause an error, not a credential lookup or download. The snapshot and detailed
run files stay ignored/local pending provider redistribution terms; a fresh clone
can run synthetic tests but needs the matching snapshot to reproduce market results.

Local artifacts:

- [Initial report](runs/initial/REPORT.md)
- [Full initial results and ledgers](runs/initial/results.json)
- [Identical reproduction](runs/reproduction/results.json)

Initial results SHA-256:
`59bc1e36ae2f1129d1029a8e8e569fa9910199f5bf871ea92458087b2096253c`.

The result JSON records the exact snapshot, config, engine and specification
hashes. Source links and every trading/modeling assumption are in SPEC.md.
