### Backtest 1: real funds
Window: 2011-08 to 2026-09 (182 months) [actual LIVKX; actual fund classes where they exist]

| Option | CAGR | Volatility | Max drawdown | Worst 12 months | Ending balance* |
|---|---|---|---|---|---|
| A  LifePath Index 2055 K | 10.8% | 13.9% | -25.6% | -20.8% (to 2022-09) | $858,059 |
| B  DIY 4-fund index | 11.3% | 14.4% | -25.0% | -19.7% (to 2022-09) | $888,243 |
| C  Old 14-fund mix | 10.8% | 14.3% | -25.9% | -21.6% (to 2022-09) | $860,219 |

*$16,825 start + $1,650/month; total contributed $317,125. Nominal dollars.

### Backtest 2: long window
Window: 2000-01 to 2026-09 (321 months) [A reconstructed; older share classes ER-adjusted]

| Option | CAGR | Volatility | Max drawdown | Worst 12 months | Ending balance* |
|---|---|---|---|---|---|
| A  LifePath Index 2055 K | 7.2% | 15.2% | -53.7% | -46.3% (to 2009-02) | $2,510,965 |
| B  DIY 4-fund index | 7.6% | 15.6% | -54.1% | -46.6% (to 2009-02) | $2,565,313 |
| C  Old 14-fund mix | 7.9% | 15.5% | -53.2% | -46.4% (to 2009-02) | $2,553,184 |

*$16,825 start + $1,650/month; total contributed $546,475. Nominal dollars.

### Monte Carlo (bootstrap): no forced crash

| Option | P10 @55 | Median @55 | P90 @55 | Median @50 | Median worst drop, last 5y | Bad-case (P10) worst drop, last 5y | P(>25% drop in last 5y) |
|---|---|---|---|---|---|---|---|
| A  LifePath Index 2055 K | $0.80M | $1.33M | $2.29M | $1.07M | -8.7% | -22.3% | 4.4% |
| B  DIY 4-fund index | $0.76M | $1.83M | $4.38M | $1.33M | -24.2% | -47.9% | 46.8% |
| C  Old 14-fund mix | $0.78M | $1.90M | $4.60M | $1.37M | -23.8% | -48.0% | 43.8% |
| A' LifePath Index 2060 K | $0.79M | $1.43M | $2.70M | $1.13M | -12.2% | -26.6% | 13.2% |
| H1 B, switch to A (2055) at 40 | $0.81M | $1.42M | $2.62M | $1.14M | -8.8% | -22.3% | 4.5% |
| H2 B, switch to A' (2060) at 40 | $0.80M | $1.50M | $2.95M | $1.19M | -12.2% | -26.6% | 13.4% |
| H3 B, glide to 60/40 from 40 to 55 | $0.81M | $1.66M | $3.54M | $1.27M | -15.8% | -33.1% | 25.0% |

### Monte Carlo (bootstrap): 2008 crash starts at 50, then 2009-12 recovery

| Option | P10 @55 | Median @55 | P90 @55 | Median @50 | Median worst drop, last 5y | Bad-case (P10) worst drop, last 5y | P(>25% drop in last 5y) |
|---|---|---|---|---|---|---|---|
| A  LifePath Index 2055 K | $0.80M | $1.26M | $2.07M | $1.07M | -22.5% | -23.4% | 0.0% |
| B  DIY 4-fund index | $0.63M | $1.24M | $2.56M | $1.33M | -53.4% | -54.1% | 100.0% |
| C  Old 14-fund mix | $0.64M | $1.29M | $2.69M | $1.37M | -52.8% | -53.5% | 100.0% |
| A' LifePath Index 2060 K | $0.73M | $1.23M | $2.17M | $1.13M | -33.3% | -34.2% | 100.0% |
| H1 B, switch to A (2055) at 40 | $0.80M | $1.33M | $2.38M | $1.14M | -22.6% | -23.6% | 0.0% |
| H2 B, switch to A' (2060) at 40 | $0.73M | $1.29M | $2.38M | $1.19M | -33.4% | -34.2% | 100.0% |
| H3 B, glide to 60/40 from 40 to 55 | $0.72M | $1.34M | $2.62M | $1.27M | -40.2% | -41.0% | 100.0% |

### Monte Carlo (bootstrap): 2008 crash bottoms exactly at 55

| Option | P10 @55 | Median @55 | P90 @55 | Median @50 | Median worst drop, last 5y | Bad-case (P10) worst drop, last 5y | P(>25% drop in last 5y) |
|---|---|---|---|---|---|---|---|
| A  LifePath Index 2055 K | $0.60M | $0.97M | $1.64M | $1.07M | -23.5% | -31.7% | 31.6% |
| B  DIY 4-fund index | $0.34M | $0.77M | $1.77M | $1.33M | -55.9% | -67.2% | 100.0% |
| C  Old 14-fund mix | $0.36M | $0.81M | $1.87M | $1.37M | -55.2% | -66.6% | 100.0% |
| A' LifePath Index 2060 K | $0.57M | $1.01M | $1.86M | $1.13M | -27.0% | -37.2% | 91.3% |
| H1 B, switch to A (2055) at 40 | $0.60M | $1.04M | $1.89M | $1.14M | -23.7% | -31.9% | 33.1% |
| H2 B, switch to A' (2060) at 40 | $0.57M | $1.05M | $2.03M | $1.19M | -27.1% | -37.4% | 91.7% |
| H3 B, glide to 60/40 from 40 to 55 | $0.50M | $1.01M | $2.08M | $1.27M | -37.0% | -47.9% | 100.0% |

Head-to-head (bootstrap): P(B beats A @55) = 81.9%, P(B beats C @55) = 24.5%, P(H1 beats A @55) = 80.2%

### Monte Carlo (cma): no forced crash

| Option | P10 @55 | Median @55 | P90 @55 | Median @50 | Median worst drop, last 5y | Bad-case (P10) worst drop, last 5y | P(>25% drop in last 5y) |
|---|---|---|---|---|---|---|---|
| A  LifePath Index 2055 K | $0.84M | $1.41M | $2.43M | $1.11M | -8.4% | -22.0% | 3.9% |
| B  DIY 4-fund index | $0.73M | $1.74M | $4.16M | $1.28M | -24.3% | -48.0% | 47.2% |
| C  Old 14-fund mix | $0.72M | $1.70M | $4.08M | $1.25M | -24.1% | -48.3% | 46.1% |
| A' LifePath Index 2060 K | $0.82M | $1.49M | $2.82M | $1.16M | -12.0% | -26.3% | 12.4% |
| H1 B, switch to A (2055) at 40 | $0.83M | $1.46M | $2.69M | $1.15M | -8.5% | -22.0% | 4.0% |
| H2 B, switch to A' (2060) at 40 | $0.82M | $1.52M | $2.99M | $1.19M | -12.0% | -26.3% | 12.4% |
| H3 B, glide to 60/40 from 40 to 55 | $0.80M | $1.63M | $3.44M | $1.24M | -15.7% | -33.0% | 24.7% |

### Monte Carlo (cma): 2008 crash starts at 50, then 2009-12 recovery

| Option | P10 @55 | Median @55 | P90 @55 | Median @50 | Median worst drop, last 5y | Bad-case (P10) worst drop, last 5y | P(>25% drop in last 5y) |
|---|---|---|---|---|---|---|---|
| A  LifePath Index 2055 K | $0.82M | $1.30M | $2.15M | $1.11M | -22.6% | -23.4% | 0.0% |
| B  DIY 4-fund index | $0.61M | $1.20M | $2.46M | $1.28M | -53.4% | -54.1% | 100.0% |
| C  Old 14-fund mix | $0.61M | $1.19M | $2.44M | $1.25M | -52.7% | -53.4% | 100.0% |
| A' LifePath Index 2060 K | $0.74M | $1.26M | $2.23M | $1.16M | -33.4% | -34.2% | 100.0% |
| H1 B, switch to A (2055) at 40 | $0.80M | $1.35M | $2.39M | $1.15M | -22.7% | -23.6% | 0.0% |
| H2 B, switch to A' (2060) at 40 | $0.74M | $1.29M | $2.37M | $1.19M | -33.4% | -34.2% | 100.0% |
| H3 B, glide to 60/40 from 40 to 55 | $0.70M | $1.31M | $2.54M | $1.24M | -40.2% | -41.0% | 100.0% |

### Monte Carlo (cma): 2008 crash bottoms exactly at 55

| Option | P10 @55 | Median @55 | P90 @55 | Median @50 | Median worst drop, last 5y | Bad-case (P10) worst drop, last 5y | P(>25% drop in last 5y) |
|---|---|---|---|---|---|---|---|
| A  LifePath Index 2055 K | $0.62M | $1.02M | $1.73M | $1.11M | -23.5% | -31.2% | 30.6% |
| B  DIY 4-fund index | $0.33M | $0.74M | $1.68M | $1.28M | -55.9% | -67.3% | 100.0% |
| C  Old 14-fund mix | $0.33M | $0.74M | $1.67M | $1.25M | -55.3% | -66.7% | 100.0% |
| A' LifePath Index 2060 K | $0.58M | $1.04M | $1.93M | $1.16M | -26.9% | -36.9% | 91.9% |
| H1 B, switch to A (2055) at 40 | $0.61M | $1.06M | $1.93M | $1.15M | -23.6% | -31.4% | 31.3% |
| H2 B, switch to A' (2060) at 40 | $0.58M | $1.06M | $2.05M | $1.19M | -27.0% | -37.0% | 91.9% |
| H3 B, glide to 60/40 from 40 to 55 | $0.50M | $0.98M | $2.03M | $1.24M | -37.0% | -47.8% | 100.0% |

Head-to-head (cma): P(B beats A @55) = 73.5%, P(B beats C @55) = 76.8%, P(H1 beats A @55) = 69.2%
