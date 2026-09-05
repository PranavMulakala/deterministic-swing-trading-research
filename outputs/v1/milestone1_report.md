# Milestone 1 research report

## Verdict

V1 is a lower-exposure, lower-drawdown research result, but it does not establish a superior return edge. It should not advance to broker paper execution unchanged.

## Measured results

| System | Period | Final equity | Total return | CAGR | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Pullback v1 IS | 2006-01-03 to 2020-12-31 | $762.49 | 52.50% | 2.85% | 15.39% |
| Pullback v1 OOS | 2021-01-04 to 2026-08-31 | $680.48 | 36.10% | 5.60% | 7.43% |
| SPY buy/hold OOS | 2021-01-04 to 2026-08-31 | $1099.85 | 119.97% | 14.96% | 24.50% |
| Momentum OOS | 2021-01-04 to 2026-08-31 | $793.05 | 58.61% | 8.50% | 20.79% |

OOS v1 completed 684 trades, won 64.18%, averaged $0.2639 per trade, had profit factor 1.381, and incurred $38.01 of modeled spread, slippage, and fees. Average market exposure was 31.08%. Its total return trailed SPY by 83.87 percentage points and momentum by 22.51 points, while its drawdown was lower.

## Why it might work

Broad ETFs often retain medium/long-term trend persistence while short, sharp selloffs mean-revert. The 200-day filter attempts to isolate that setting; RSI(2) locates unusually weak closes; the recovery exit avoids demanding a large forecast. This is a plausible mechanism, not proof.

## What must be true

The signal must contain enough short-horizon rebound information to overcome frequent turnover costs. Daily adjusted bars must approximate executable opens/stops adequately. Cross-ETF signals must add diversification rather than duplicate the same market bet. Most importantly, the lower exposure and risk cap must provide enough drawdown benefit to justify giving up passive-market return.

## What would invalidate it

The implementation is invalid if next-bar timing, checksum reproducibility, fill reconciliation, or risk tests fail. The economic case is invalidated if the frozen OOS run remains materially weaker than both benchmarks after costs without a separately valued low-drawdown objective. On this run, that economic warning has fired: v1 underperformed both benchmarks. A future v2 must be newly preregistered and tested on a new untouched period; tuning v1 against this OOS set would contaminate it.

## Decision

Keep v1 as a reproducible baseline and evidence artifact. Do not connect it to a broker. Before any separate paper-execution milestone, independently validate event ordering and accounting, then design a genuinely new v2 hypothesis—without optimizing against the disclosed OOS results. See `methodology.md` for data and simulation limitations and `validation_report.json` for invariant checks.
