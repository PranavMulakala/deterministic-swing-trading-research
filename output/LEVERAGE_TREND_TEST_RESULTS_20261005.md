# Test #14: "2× leverage only above the 200-day average": results (October 5, 2026)

- **Plan:** [LEVERAGE_TREND_TEST_PLAN_20261005.md](LEVERAGE_TREND_TEST_PLAN_20261005.md), committed (95b9691) before any result.
- **Code:** `research/lev_trend_test_v1/` (3 unit tests), committed (ebedc90) before the run.
- **Results:** `output/lev-trend-test-results.json` + `.provenance.json`.
- **Data:** Ken French daily US market total returns and T-bill rates, Mar 1927 – Aug 2026 (99.5 years), downloaded with the owner's OK.
- **Checks:**
  - An independent recomputation matched growth and worst drop exactly, for both the strategy and the market.
  - **The cost model is realistic:** simulated 2× SPY matched the actual SSO fund over 2016–2025 within 0.01 points a year (23.11% vs 23.10%; worst drop −58.7% vs −59.2%).

## Verdict: PASSED all 4 pre-declared checks, the first of 14 tests to do so

| Check (full 1927–2026 history) | Needed | 2× above 200-day | Holding the market |
|---|---|---|---|
| 1. Growth at least 2 points/yr higher | ≥ 12.21% | **17.06% ✓** | 10.21% |
| 2. Worst drop no worse | ≥ −84.1% | **−60.1% ✓** | −84.1% |
| 3. Growth ÷ worst drop higher | > 0.121 | **0.284 ✓** | 0.121 |
| 4. Higher growth in both halves | 1927–75 and 1976–2026 | **19.4% vs 8.1%; 14.9% vs 12.3% ✓** | |

## All strategies, full history
| Strategy | Per year | Worst drop | Time in stocks | Switches/yr |
|---|---|---|---|---|
| Holding the market (1×) | 10.2% | −84% (1932) | 100% | 0 |
| **2× above the 200-day, else T-bills (main)** | **17.1%** | **−60%** (1935) | 73% | 5.7 |
| Holding 2× permanently | 12.5% | **−98%** | 100% | 0 |
| 1× above the 200-day (info) | 10.9% | −34% | 73% | 5.7 |
| 3× above the 200-day (info) | 22.7% | −78% | 73% | 5.7 |
| Holding 3× permanently (info) | 12.2% | **−99.9%** | 100% | 0 |

- **The filter is what makes leverage survivable.** Held permanently, 2× and 3× were nearly wiped out in 1929–32 (−98%, −99.9%).

## The important catch: the edge has faded in the modern era
| Window | 2× above 200-day: per year / worst drop | Market: per year / worst drop |
|---|---|---|
| 1927–1975 | 19.4% / −60% | 8.1% / −84% |
| 1976–2026 | 14.9% / −58% | 12.3% / −55% |
| **Since 1990** | **12.6% / −58%** | **11.0% / −55%** |
| **Since 2000** | **8.55% / −58%** | **8.57% / −55%** (a tie) |

- **Since 2000 it has only tied the market,** with a slightly deeper worst drop. $1 became $8.91 vs $8.96.
- **By decade:**
  - 2000s: −1.0% vs −0.4%;
  - 2010s: 12.5% vs 13.6% (worse);
  - 2020s so far: 18.2% vs 15.5% (better).
- **Whipsaw years hurt:**
  - **2000: −36.8%** (vs market −11.7%);
  - **2022: −25.0%** (vs −20.0%).
- **Crash protection was strong:**
  - **2008: −5.8%** (vs −36.5%);
  - 1931: −2.3% (vs −44.3%);
  - 1974: +8.1% (vs −27.8%);
  - 1987: +24.7%.

## Real-fund check, QQQ version (Oct 2016 – Dec 2025, actual QLD prices; information only)
| | Per year | Worst drop |
|---|---|---|
| QLD (2× Nasdaq) above QQQ's 200-day, else T-bills | 30.1% | −41.8% |
| Holding QQQ | 20.7% | −35.0% |
| Holding QLD | 32.8% | −63.7% |
| Holding SPY | 15.3% | −33.8% |

It made 38 switches in about 9 years.

## What this means
- **This is the first idea with both independent published evidence and a passing pre-declared test.** Over a century it beat holding the market by about 7 points a year, with a smaller worst drop.
- **But most of that advantage came before 2000.** In the last 26 years it roughly tied the market, with deeper drops in whipsaw years like 2000 and 2022. Past results don't promise the future, and the recent record is the closest guide to today's markets.
- **Real-world frictions not in the numbers:**
  - **Taxes:** about 5–6 switches a year means frequent taxable sales, often short-term, in a regular account. It's far more practical inside a tax-advantaged account (IRA/401k), if those allow the funds.
  - **Behaviour:** it still had −58% to −60% drops. On $180k that's about −$105k–$108k on paper, well past the owner's ~$38k limit.
  - **Execution:** the signal must be checked every trading day and followed without exception.
- **Test record: 14 pre-declared tests; this is the first that beat holding the market on its pre-declared bars** (over the full 1927–2026 history).
