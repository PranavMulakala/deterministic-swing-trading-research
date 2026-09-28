# Does more capital fix LITE? No evidence that it does.

September 9, 2026, before market open. Historical diagnosis only; the September 9
forward arms, cloud release and all original strategy rules remain unchanged.

## Measured answer

Same 170 complete raw SIP five-minute sessions, January 2–September 4, 2026.
Only initial cash changes; all portfolios use whole shares and original limits.

| Capital | Entry | Cost per side | Trades | Ending cash | Net P&L |
|---:|---|---:|---:|---:|---:|
| $5,000 | Dip | 10 bps | 50 | $4,625.84 | -$374.16 |
| $5,000 | Dip | 25 bps | 16 | $4,914.71 | -$85.29 |
| $5,000 | VWAP retest | 10 bps | 5 | $4,954.60 | -$45.40 |
| $5,000 | VWAP retest | 25 bps | 0 | $5,000.00 | $0.00 |
| $10,000 | Dip | 10 bps | 50 | $9,177.95 | -$822.05 |
| $10,000 | Dip | 25 bps | 16 | $9,838.59 | -$161.41 |
| $10,000 | VWAP retest | 10 bps | 5 | $9,902.84 | -$97.16 |
| $10,000 | VWAP retest | 25 bps | 0 | $10,000.00 | $0.00 |

All six larger-capital cases that traded lost money; the other two did not trade.
The baseline-cost dip cases had 43 stop exits, five target exits and two time exits,
with seven profitable trades out of 50. Their mean net R was approximately -0.385.
The exploratory weekly bootstrap interval was approximately [-0.700, -0.004] R;
it does not correct for choosing this strategy/year/cohort and is not a future
profit probability. VWAP had only five baseline-cost trades, too few for confidence.

Capital removes most sizing failures but does not repair the measured entry/exit
economics. Higher-cost cases trade less because their limits change, not because
paying more cost improves identical fills. Do not promote the least-losing case.

On the same 140-session one-/five-minute intersection, every case has identical
ending cash between resolutions. Both larger dip portfolios lose more on this
intersection; that is a different date subset, not an effect of higher resolution.
Neither resolution proves executable quotes, latency, native stops or real fills.
This whole year was already studied: **not an untouched holdout**.

## Verification

- Eight new tests passed: matrix completeness, frozen non-capital settings,
  matching dates, immutable outputs, repeat determinism, and accounting tampering.
- All 36 cases passed both the parent ledger check and a separate Decimal replay:
  385 trade records and 5,400 daily rows. These are repeated scenarios, not 385
  independent trades. Planned-risk checks do not cap actual gap losses.
- Two full runs produced byte-identical results:
  `4b72f49c442f39dc9d7b33789b4700c91356319129d0ca1f66c1c8741e0b5a5b`.
- All 12 $500 controls match every field of the original full/intersection study.
- Inputs and original source were hashed before and after; no credentials, API
  requests, broker orders, strategy edits, cloud deployments or purchases.

See [protocol](PROTOCOL.md), [input pins](INPUT_PINS.json),
[full tables](runs/diagnostic-01/REPORT.md) and
[ledgers](runs/diagnostic-01/results.json).

```sh
PYTHONPATH=.:src .venv/bin/python -m unittest research.lite_capital_diagnostic_v1.test_run -q
PYTHONPATH=.:src .venv/bin/python -m research.lite_capital_diagnostic_v1.run --output research/lite_capital_diagnostic_v1/runs/NEW
```

Provider-derived outputs remain local/Git-ignored. A fresh clone needs the pinned
data files; synthetic tests require no credentials or market access.
