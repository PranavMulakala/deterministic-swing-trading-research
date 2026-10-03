# What Joey's material taught us, and whether anything is worth testing (Oct 3, 2026)

Covers: the Sept 26 emails, course and code (`reference/joey_2026-09-26/`, private); the Oct 1 DELL rolls/collar, ORCL "bearish" diagonal and AMZN pre-earnings double diagonal; the Oct 3 hedge monitor, MU covered call and MU put diagonal. Evidence only, not advice.

## The biggest lesson
**A high "chance of profit" is not an edge.** Every Joey structure is built to win small and often, with a rare large loss:
| Trade | Best case | A bad but normal case | Analyzer's chance of profit |
|---|---|---|---|
| MU covered call (200 sh) | +$3,528 | −$28,500 at $860 | about 64–70% |
| MU put diagonal (to Mon) | about +$500 | about −$6,000 on a −10% day | about 42% in the profit zone |
| MSTR hedge (mock) | protects the downside | costs $7,300; gains only above $170 | n/a |

The analyzer's probabilities come from option prices, and option prices roughly balance win chance against payoff size. So before costs and before skill, expected value is about zero. What decides results is the rare big loss and the costs, not the 70%. These trades **reshape risk** (cap the upside, buy a floor, collect a cushion). They don't create return. Rolling a losing position postpones a loss; it doesn't remove it. None of his results are verified realized P&L (screenshots, projections, selected-day backtests).

## Already tested or settled
| Idea | Status |
|---|---|
| Selling put spreads (the course's main strategy) | **Tested: SPY put-spread holdout failed.** The Cboe PUT index returned 7.1%/yr vs 11.0% for the S&P 500 |
| Buying protection (hedge monitor, collars) | Settled by research. The *variance risk premium*: option prices on average imply more movement than happens, so **buyers of options lose on average** (Bakshi–Kapadia 2003; Carr–Wu 2009; Goyal–Saretto 2009). Insurance only makes sense against a loss you truly can't bear; position size is the free alternative |
| Covered calls | Risk reshaping: cap the upside for a cushion. Costliest in strong rallies (MU +6× in a year). Needs 100 shares (owner has 50.96) |
| His Schwab dip bot (ATR trigger, trailing stop) | Selected-day backtests only. Our own LITE dip rule is already in paper testing |
| Diagonals/condors with "adjust if it moves" | No rules precise enough to test; adjustments aren't verified |

## The one thing with independent evidence: options before earnings
Joey's AMZN trade bets that options get pricier *as earnings approaches* and exits *before* the report. A peer-reviewed study supports the idea:
- **Gao, Xing & Zhang (2018), *Journal of Financial and Quantitative Analysis*:** stock straddles normally earn significantly *negative* returns. But at-the-money straddles bought **3 days before** an earnings announcement and held to the announcement date earned a **highly significant +3.34%** on average. Interpretation: investors underestimate earnings uncertainty.

**Caveats that could kill it:**
1. The effect was **strongest in smaller, harder-to-trade stocks**, exactly where option bid/ask spreads can eat 3% (we measured LITE's at 14%).
2. Published anomalies typically shrink after publication. The paper's data predates 2018.
3. It's a short-dated option *purchase*, the category where retail losses concentrate.
4. It must exit *before* the report (or the paper's exact timing); holding through the report is a different, usually losing bet.
5. LITE options are banned for the owner (Lumentum policy). Any test uses other liquid large caps.

**How it could be tested, if the owner wants (each step needs an explicit yes):**
- **Forward paper test, no data cost:** in the existing Options paper account, buy an at-the-money straddle 3 trading days before each report on a fixed list of liquid large caps. Sell at the last close before the report. Log fills against bid/ask. Late-Oct earnings season (big tech Oct 27–29) gives 30+ events in a few weeks.
- **Pass bar (pre-declared):** average return after real bid/ask fills > 0, with at least 30 events, and losers that don't dominate (judged against the pre-earnings drift of the stock itself).
- **Or a historical test:** needs historical option *quotes*, which means paid data (ThetaData about $40/mo, or Databento credit). Ask first.

## Bottom line
Joey's main value is the habits: look at the whole payoff chart before entering, write the adjustment plan first, know the max loss in dollars. As a source of edge, only the pre-earnings idea has independent support, and it's worth a small pre-declared paper test at most.
