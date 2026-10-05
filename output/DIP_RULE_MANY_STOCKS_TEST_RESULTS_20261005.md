# Test #15: does the LITE "morning dip, sell +2%" rule work on other stocks? Results (October 5, 2026)

- **Plan:** [DIP_RULE_MANY_STOCKS_TEST_PLAN_20261005.md](DIP_RULE_MANY_STOCKS_TEST_PLAN_20261005.md), committed (82e461b) before any test-period data. A pre-result correction (96192a1) is noted in it.
- **Code:** `research/dip_many_test_v1/`, with 4 unit tests. Universe and backtest 9ffa2f7, fetch fix 7bf7a44, verifier 8d06836, correction 96192a1. All committed before the run.
- **Data:** Alpaca SIP 30-minute bars, Jan 3, 2022 – Sep 30, 2026, for 113 symbols (100 main + 12 hindsight + SPY). All complete; SNDK only exists from its Feb 2025 spin-off.
- **Results:** `output/dip-many-test-results.json` + `.provenance.json` (commit 071bfd0, clean code).
- **Checks:**
  - 4 unit tests pass.
  - **An independent recount matched all 5 random stocks exactly:** DJT, ABNB, PINS, WYNN, AMD (trades, stuck positions, total %).

## Verdict: FAILED all 5 pre-declared checks

| Check (100 most volatile big stocks, chosen as of 2021) | Needed | Dip rule | SPY |
|---|---|---|---|
| A1. Profit factor, open positions included | ≥ 1.3 | **0.89 ✗** | |
| A2. Profitable in both halves | 2022–23 and 2024–Sep 2026 | **−8.4% / +1.6% ✗** | |
| A3. Worst drop | no worse than −25% | **−49.6% ✗** | −24.5% |
| B1. Worst drop at least 5 points smaller than SPY's | no worse than −19.5% | **−49.6% ✗** | −24.5% |
| B2. Growth ÷ worst drop beats SPY | > 0.492 | **−0.03 ✗** | 0.492 |

**$100,000 → $93,060 (−1.5%/yr), against $171,081 (+12.0%/yr) for holding SPY with dividends.**

## What happened, in plain words
- **It won 96% of its trades.** All 260 trades that closed were +2% winners, together +$57,387; 146 of them sold the same day.
- **10 buys never came back.** Open at the end, they're down **−$64,329**, more than all the winners made:

| Stock | Bought | Price then → Sep 30, 2026 | Loss on $10,000 |
|---|---|---|---|
| LGVN | Dec 20, 2023 | $182.17 → $2.66 | −$9,854 (−98.5%) |
| FLNA | Feb 11, 2022 | $54.05 → $0.88 | −$9,837 |
| BKKT | Mar 30, 2022 | $169.89 → $7.79 | −$9,541 |
| DJT | Apr 1, 2024 | $56.31 → $9.06 | −$8,391 |
| PHUN | Oct 28, 2024 | $11.16 → $1.98 | −$8,225 |
| BYND | Apr 21, 2026 | $39.79 → $8.30 | −$7,913 |
| TEAM | Jan 3, 2022 | $358.73 → $179.17 | −$5,005 |
| APP | Jul 13, 2026 | $468.75 → $290.43 | −$3,804 |
| GNRC | Jul 7, 2026 | $240.79 → $206.93 | −$1,406 |
| PATH | Sep 22, 2026 | $13.30 → $12.83 | −$352 |

(Prices are split-adjusted, so reverse-split stocks show inflated old prices.)

- **The money got trapped.** With no stop, a stock that keeps falling keeps its slot. **All 10 slots were full on 1,036 of 1,190 trading days (87%),** so most new signals couldn't be taken.
  - TEAM was bought on the very first day (Jan 3, 2022) and was still −50% on the last.
  - CVNA (Jan 2022) took 2.7 years to get back to +2%.
- **2022 did the damage.** $100k fell to **$53,314** (Dec 28, 2022), was back to about $92k by the end of 2023, then went nowhere.
- **Stock by stock** (each stock trading all its own signals): **37 of 100 made money.**
  - **Best:** NVDA, AMD, GME, CRWD, NET.
  - **Worst:** 2021's hot stocks that collapsed: SPCE, LCID, TDOC, CHPT, NIO, SNAP, PLUG, NVAX, CHGG. Each one's stuck buy lost 80–99%.

## The hindsight list (information only: stocks picked in Oct 2026 because they soared)

| | Dip rule on MU, SNDK, WDC, STX, DELL, INTC, TER, MRVL, COHR, CIEN, HPE, LITE | SPY |
|---|---|---|
| $100,000 became | **$249,906** (+21.4%/yr) | $171,081 (+12.0%/yr) |
| Worst drop | −43.9% | −24.5% |
| 2022–2023 | −18.0% | |
| 2024–Sep 2026 | +204.9% | |

- **All 12 made money, but the list still fails A2, A3, B1 and B2.** Its growth ÷ drop was 0.488, against SPY's 0.492.
- **Lesson:** the rule looks great only on stocks you already know went up. Picked the honest way (with only 2021 information), "volatile stocks like LITE" included many that collapsed.

## A flaw found after the results, and why it doesn't change the verdict (information only)
- **What went wrong:** `universe.py` applied the "$20 or more" filter to **split-adjusted** prices. Stocks that later did reverse splits looked expensive in 2021 and got in.
  - **7 of the 100 actually traded under $20 then:** PHUN $2.63, FCEL $5.20, TLRY $7.03, BKKT $8.51, LGVN $12.07, SPCE $13.38, CHPT $19.05.
  - That's hindsight, and it **hurts** the rule.
- **The correct list:** with the filter on real 2021 prices, those 7 would have been replaced by BEKE, CCL, SPOT, F, CPNG, MTCH and NTES (`output/dip-many-test-info-raw-price.json`).
- **Re-run without the 7** (93 stocks, no replacements; `research/dip_many_test_v1/info_raw_price_check.py`, written after the results):
  - $100k → **$115,311** (+3.1%/yr);
  - worst drop **−47.0%**;
  - profit factor 1.33;
  - 2022–23 −2.4%, 2024–26 +18.1%.
  - **It still fails 4 of 5 checks (A2, A3, B1, B2)** and trails SPY's $171k by $56k. Adding the 7 replacements is very unlikely to halve a −47% drop.
- **The official verdict stays the pre-declared one.**

## Known biases
- **Flatters the rule:** companies delisted since 2021 aren't in the data (stated in the plan).
- **Hurts the rule:** the split-adjusted price filter above. It was measured, and it doesn't change the verdict.

## What this means
- **The Plan B dip rule is not a general pattern.** On volatile stocks chosen without hindsight it lost money, while SPY gained 71%.
- **It made money only where the stock kept rising** (the hindsight list). So Plan B's results depend on LITE continuing to rise, not on the rule itself.
  - If LITE ever falls the way TEAM, AFRM or CVNA did in 2022, the rule has no way out: no stop, one position at a time, and money trapped for months or years.
  - The Plan B note already shows this risk for LITE: −66% in 2022–24.
- **As the plan says, steps 2 (calls on signal days) and 3 (paper-trading many stocks) don't proceed.**
- **Nothing changes in Plan B, the bots or MNQ.** The LITE formula freeze stays until the paper test ends.

**Score:** 15 pre-declared tests. Only #14 passed, and it only ties the market since 2000.
