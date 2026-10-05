# Test #13: monthly SPY covered calls vs holding SPY: results (October 5, 2026)

- **Plan:** [COVERED_CALL_SPY_TEST_PLAN_20261005.md](COVERED_CALL_SPY_TEST_PLAN_20261005.md), committed (ae57f73) before any result.
- **Code:** `research/cc_spy_test_v1/` (5 unit tests), committed (5fe55ba) before the run.
- **Results:** `output/cc-spy-test-results.json` + `.provenance.json`.
- **Data:** OPRA SPY chain every trading day, Jan 4, 2016 – Dec 31, 2025, plus 38 dividends ($56.28/share in total, matching SPY's actual payouts).
- **Independent check:**
  - All 111 settled calls sold at exactly the 10:30 bid in the raw files.
  - The cash + shares path rebuilt from the trade list comes to $254,054 vs $254,834 reported. The $780 gap is the one call still open on Dec 31: its premium is in cash, minus its buy-back cost.

## Verdict: did NOT beat holding SPY

It passed 2 of 5 checks.

| Check | Needed | Result |
|---|---|---|
| A1 Profit factor of monthly cycles | ≥ 1.3 | **1.92 ✓** |
| A2 Profitable in both halves | both > 0 | **+47.7% / +72.5% ✓** |
| A3 Worst drop | ≤ 25% | **−32.0% ✗** |
| B1 Drop ≥5 points smaller than SPY's | ≥ −28.8% | **−32.0% vs −33.8% ✗** |
| B2 Growth ÷ drop beats SPY | > 0.438 | **0.307 ✗** |

## $100,000 from Jan 2016 to Dec 2025, full history
| | Ended with | Per year | Worst drop |
|---|---|---|---|
| **Holding SPY (dividends reinvested)** | **$396,414** | 14.8% | −33.8% |
| **Covered calls, ~0.30 delta (main)** | **$254,834** | 9.8% | −32.0% |
| Covered calls at midpoint fills (info) | $257,167 | 9.9% | −32.0% |
| Covered calls, 0.20 delta, further out (info) | $287,440 | 11.2% | −31.2% |
| Covered calls at the money, BXM-style (info) | $183,954 | 6.3% | −23.4% |
| *(for reference) 65% SPY / 35% T-bills* | *$272,990* | *10.6%* | *−22.6%* |
| *(for reference) Cash-secured puts, test #10* | *$154,556* | *4.5%* | *−22.2%* |

## Why it trails
- **Premium collected: $109,783. Upside given up when SPY ran past the strike: $173,829.** The calls cost more in missed gains than they paid.
- **It fell almost as much as SPY in crashes (−32% vs −34%).** A ~1% monthly premium barely cushions a 30% drop. The worst cycle was Feb 18 – Mar 18, 2020 (−$37,281).
- **51% of calls were exercised** (shares called away), mostly in rising markets, which is exactly when you want to own them.
- **Down years:** 2018 (−5.8%) and 2022 (−9.4%). Up years trailed SPY's.

## The owner's question: what if shock periods are left out?
The same windows are removed from both the covered call and SPY.

| View | Covered call: per year / worst drop / growth ÷ drop | SPY: per year / worst drop / growth ÷ drop |
|---|---|---|
| Full history | 9.8% / −32.0% / 0.31 | 14.8% / −33.8% / 0.44 |
| COVID removed (Feb 20 – Apr 30, 2020) | 11.7% / −17.1% / **0.69** | 16.5% / −24.5% / **0.67** |
| All big shocks removed (+ Feb 2018, Aug 2024, Apr 2025) | 11.9% / −17.1% / **0.70** | 16.8% / −24.5% / **0.69** |

- **With the shocks removed, the covered call's growth-per-unit-of-drop becomes about equal to SPY's** (0.69 vs 0.67). It's smoother in normal markets.
- **But it still grows much less:** about 5 points a year slower. On $100k, that's roughly $301k vs $459k in the COVID-removed view.
- **So even in "normal" times it's a calmer, lower-return way to own SPY, not a better one.** And in real life, the shocks can't be skipped.

## Takeaway
- **Covered calls top the Reddit ranking because they're mostly just owning SPY,** with a capped upside.
- **They beat cash-secured puts and T-bills, but not simply holding SPY.** For the same smoothness, the 65/35 mix did better ($273k at −23% vs $255k at −32%).
- **Test record: 13 pre-declared tests; none beat holding SPY.**
