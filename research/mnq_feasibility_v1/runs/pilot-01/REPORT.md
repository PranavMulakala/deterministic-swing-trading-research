# First real-data MNQ pilot

**Observed-data diagnostic; costs and broker execution remain unverified.**

Five sessions were imported; August 31 is warmup and September 1–4 are evaluated. 
The frozen setup, $5,000 simulated account, and $12.50 initial planned-risk budget were unchanged.

| Cost scenario | Patterns | Risk assessable | Risk fits | Fits / patterns | Entries | Closed net P&L | Observed drawdown |
|---|---:|---:|---:|---:|---:|---:|---:|
| fee2_slip0 | 0 | 0 | 0 | N/A | 0 | $0.00 | $0.00 |
| fee2_slip1 | 0 | 0 | 0 | N/A | 0 | $0.00 | $0.00 |
| fee2_slip2 | 0 | 0 | 0 | N/A | 0 | $0.00 | $0.00 |
| fee4_slip2 | 0 | 0 | 0 | N/A | 0 | $0.00 | $0.00 |

The fee2/fee4 labels mean $2/$4 total entry-and-exit fees; slip0/1/2 are extra adverse ticks per side.
Risk-fit percentages describe the observed patterns, not a probability of future success.
No patterns means the fit percentage is unknown; no entries means losses and pauses were not meaningfully exercised.
Zero observed drawdown does not mean a risk-free strategy. Data expense of about $11.07 is separate from trading P&L.

## Evidence and limits

See `report.json` for every signal, decision, trade, pause, and retained equity mark; `signals.csv` is the compact decision table.
Minute bars passed an independent calculation check. Prepared-array hashes and source hashes are included in the manifests.
The replay was checked against the original engine on long/short and randomized multi-session fixtures before these outcomes were opened.
Boundary completeness, calendar assumptions beyond these dates, account costs, margin, and actual broker execution remain limitations.
This small pilot cannot approve live money. Do not loosen the setup or risk budget merely because the sample is sparse.
