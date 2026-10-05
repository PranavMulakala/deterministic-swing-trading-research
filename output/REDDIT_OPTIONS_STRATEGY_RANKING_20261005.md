# r/options: "Done ranking of variety of strategies" (u/FlashAlphaLab), notes (October 5, 2026)

- **Read through our RSS reader:** `outputs/reddit/1whv3m8.md` (post + 30 comments).
- **Data, not advice.** The poster's name matches FlashAlpha, an options-analytics company, and the post links to their site. Treat it as vendor research, not independent research. (We cited a FlashAlpha volatility-filter study in the Sept 28 put-spread work.)

## What they tested
- **42 option strategies** on SPY, QQQ and IWM, Jan 2020 – Dec 2025.
- **Each month:** enter ~35-day options chosen by delta, and exit 10 trading days later.
- **No stops, rolls or hedges.** End-of-day quotes, costs included.

## Headline results (their table, summarized)
| Rank | Strategy | Win rate | Average per trade | Worst drawdown |
|---|---|---|---|---|
| 1 | Covered call | 70% | +0.76% | −24% |
| 2 | Protective put (stock + bought put) | 62% | +0.70% | −25% |
| 5 | Long call | 54% | +0.36% | −19% |
| 9 | **Cash-secured put** | **74%** | **+0.09%** | −15% |
| 11 | **Bull put credit spread** | **70%** | **−0.01%** | −6% |
| 20 | Iron condor | 54% | −0.11% | −12% |
| 32 | Short straddle | 50% | −0.29% | −33% |
| 33 | Long put | 29% | −0.31% | −35% |

**Their own takeaways:**
- The volatility-selling strategies "won often, then a few large losses took back much of what they made."
- Trading costs mattered a lot.
- The top results were mostly bullish positions. "Whether the options added anything beyond owning the ETF is the next question."

## How it matches our own tests
- **Cash-secured puts: a high win rate but almost nothing per trade.** Same as our test #10 (82% winners, trailed SPY badly).
- **Bull put credit spread: a 70% win rate, still slightly negative.** Same as our Sept 28 SPY put-spread holdout (85% winners, −$1,809).
- **The top strategies are mostly "own the ETF plus an option overlay"**, so their returns come mainly from the market rising. That's the same point as our 65/35 check: owning the market did the work, not the options.
- **A commenter notes that much of a put-seller's return is interest on the cash collateral.** In our test #10, $28k of the $54.6k profit was T-bill interest.
- **Their volatility-filtered put spread** (+0.17%/trade on 73 trades) is the one result they call worth further work. Our Sept 28 holdout tested a similar IV ≥ 1.2× realized filter on SPY put spreads, and the filter **hurt** there. Small samples go both ways; no reason to chase it.
- **Best comment, from several people:** "The win rate is probably the biggest trap in this table." Expectancy and drawdown matter, not hit rate.
