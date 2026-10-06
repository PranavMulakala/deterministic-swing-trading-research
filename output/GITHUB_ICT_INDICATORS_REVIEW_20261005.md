# The 4 GitHub indicator repos from @JustExecution's tweet (Oct 5, 2026): what they are, and are they useful?

- **Source:** the tweet (8K views, Oct 5) lists 4 repos.
- **Reading only:** each repo's README and Pine Script source, as text. Nothing was installed or run.

| Repo | What it is | Age / stars |
|---|---|---|
| `JustExecution/HTF_indicator` | "HTF Suite": higher-timeframe candles, Fractal Model, CISD, SMT divergence, sessions; plus a liquidity suite | Jul 2026, 117 ⭐ |
| `ict2023trader/Indicators` | Fractal Model variants (FM + CISD), higher-timeframe FVG taps | Sep 30, 2026, 51 ⭐, no license |
| `cantolab/open-source-fractal` | Open-source Fractal Model (C2 sweep + CISD) | Aug 2026, 168 ⭐, MIT |
| `fxraptor-alpha/pinescript-indicators` | Fractal Model and Unicorn Model (sweep + breaker + FVG) | Jul 2026, 104 ⭐ |

## Findings
- **All are TradingView chart indicators, not strategies.** Every file is an `indicator()`, with no `strategy()` or backtest code, so there are no performance claims to check.
- **They're all ICT / "smart money" ideas:** a sweep of a higher-timeframe high or low, a reversal candle ("C2"), then a confirmation ("CISD"). That's the same family as CRT ("sweep and reclaim"), which we tested twice (#8 and #9; both lost money), and the "Power of 3" video.
- **One author says it himself.** The `cantolab` README says he does **not** recommend trading the model as is. In his words, C2 setups backtested "across enough sample size" are "not profitable", and payouts are explained by variance and survivorship. That's the same as our results.
- **A technical warning: three scripts look ahead.** The `ict2023trader` (×2) and `cantolab` code detect C2 by calling `request.security(..., [open[0], high[0], low[0], close[0], high[1], low[1]], lookahead = barmerge.lookahead_on)`.
  - On past bars, that gives the **current** higher-timeframe candle's final low and close **before that candle has finished**.
  - So historical signals on the chart can look better than they could have been in real time ("repainting").
  - `fxraptor`'s Fractal Model only looks ahead within the same timeframe (no effect), and its Unicorn Model doesn't look ahead at all.
- **The code is shared.** `ict2023trader`'s Fractal Model lines match `cantolab`'s (MIT-licensed), so they're the same model.
- **Safe and free.** Pine scripts run inside TradingView and can't touch a computer or broker account. The donation pages (crypto) are voluntary.

## Verdict
- **Fine as free charting aids for learning the vocabulary.** There's no reason to pay for look-alike indicators.
- **Not an edge.** The model family already failed our tests, and one of the authors says the same.
- **Not worth a new test.**
