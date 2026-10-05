# 65% SPY / 35% T-bills: comparison check results (October 5, 2026)

- **Plan:** [MIX_65_35_CHECK_PLAN_20261005.md](MIX_65_35_CHECK_PLAN_20261005.md), committed (a99b796) before the run.
- **Code:** `research/mix_65_35_v1/run.py`.
- **Results:** `output/mix-65-35-check.json` + `.provenance.json`.
- **Window:** the same 2,514 trading days, dividend-adjusted SPY and T-bill rates as test #10 (Jan 4, 2016 – Dec 31, 2025).

## Answer: yes. The mix matched the puts' calm, with more than twice the growth.

| $100,000 → end of 2025 | Ended with | Per year | Worst drop | Growth ÷ worst drop |
|---|---|---|---|---|
| SPY only | $396,414 | 14.8% | −33.8% | 0.44 |
| **65/35, rebalanced monthly (main)** | **$272,990** | **10.6%** | **−22.6%** | **0.47** |
| 65/35, rebalanced yearly (info) | $275,414 | 10.7% | −22.2% | 0.48 |
| 65/35, never rebalanced (info) | $301,511 | 11.7% | −25.7% | 0.46 |
| Cash-secured puts (test #10) | $154,556 | 4.5% | −22.2% | 0.20 |
| T-bills only | $125,261 | 2.3% | ~0% | — |

- **Same worst drop as the puts** (−22.6% vs −22.2%), but **$118,000 more** at the end: $273k vs $155k.
- **Its growth ÷ worst drop (0.47) was slightly better than SPY alone (0.44).** Less pain per dollar of growth than going all-in, though less total growth.
- **Both halves strong:** +64.7% (2016–2020) and +65.8% (2021–2025). The puts made only +5.9% in the first half.
- **Down years:** 2018 −2.3% and 2022 −11.1%. In 2020 it still ended **+13.1%** (the puts lost $10.7k that year).
- No options, one rebalance a month or a year, and simpler taxes (no short-term option income).

**Takeaway:** if the goal is a smoother ride than all-SPY, owning less SPY (plus T-bills) did the job far better than selling puts over 2016–2025. This is a comparison check, not advice. Past results, one decade.
