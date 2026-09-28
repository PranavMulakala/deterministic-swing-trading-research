# What the next history purchase can establish

The four-session observed-data pilot found no qualifying patterns. Current
win rate, risk-fit percentage, and after-cost expectancy are unknown. Passing
software tests or having 82.5 million market records does not substitute for
observed strategy trades.

The user agreed to a research extension up to a refreshed estimate below $56 and
asked whether that could establish a probability of profitability allowing live
money ASAP. **It cannot establish that on its own.** No additional data was
purchased while answering that question; the following comparison is quote-only.
The research budget does not authorize broker orders or a change in trading risk.

## A staged acquisition proposal

Fixed extension: MNQU6, August 3–28, 2026, 20 full weekday research sessions.
The first new session is warmup. The dates are chosen before opening their price
outcomes; the already inspected September pilot is retained separately.

| Route | Estimated usage | What it buys |
|---|---:|---|
| All MBP-1 plus definitions | $54.96 | Trades and completed-event BBO data on every requested day |
| Trades first, plus definitions | $20.63 | Signal discovery under the frozen trade-based rules; no executable-quote test yet |

Quotes are saved in `runs/expansion-quote-20260909.json` and
`runs/trade-screen-quote-20260909.json`. Prices can change. Credit balance,
application of credits, and the current monthly limit have not been rechecked.

My revised recommendation is to consider the $20.63 trade-first stage because
the immediate uncertainty is whether this strict setup occurs often enough to
study. It uses actual trade prices and sizes, preserving VWAP and variance;
minute OHLC bars alone cannot reproduce that calculation exactly.

If it produces signals, quote every signal day under the unchanged rules,
including signals that later lose, fail risk sizing, or have invalid execution
prices. Do not select only winners. Detailed quotes are a second-stage cost;
**the staged total is not guaranteed to be cheaper** because MBP-1 includes a
trade component already bought in the first stage. Keep any combined purchase
within the approved estimate ceiling, and stop if it would exceed that ceiling.
If there are no or very few signals, report insufficient evidence and reassess
the research design rather than endlessly purchasing the same narrow window.

## Percentages and uncertainty

- Win rate describes the fraction of observed trades that won.
- Risk fit describes how many signals can be sized within the specified budget.
- Average net profit per trade depends on win frequency, win/loss size, and costs.
- A future profit probability also needs a horizon, a model, uncertainty estimates,
  and assumptions about whether market behavior remains similar. It is not a
  percentage the data vendor can supply or a backtest can prove.

An invented example: 60% wins with an $8 average winner and $15 average loser
loses $1.20 per trade before costs: `0.60 * 8 - 0.40 * 15 = -1.20`.
If wins/losses already include all trading costs, do not subtract those costs twice.

Another invented example: seven wins in ten trades is a 70% observed win rate.
A 95% Wilson interval is approximately 39.7%–89.2% under independent trials with
a stable win probability. Trading results can be dependent and market behavior
can change, so this example is not a confidence interval for our strategy and
does not measure the chance of being profitable.

## Evidence needed before a live-money decision

1. Enough independent information across different periods and conditions to
   estimate after-cost expectancy with useful uncertainty. No fixed trade count
   or win-rate threshold automatically establishes an edge.
2. Positive net performance on separately reserved, previously unexamined data
   under frozen rules, robust to plausible worse spreads, slippage, fees and gaps.
   Predeclare the uncertainty method and decision criteria before looking at the
   held-out outcomes; account for serial dependence and multiple strategy trials.
3. Verified broker fees, market-data costs, account margin requirements, and
   execution mechanics. One MNQ must fit the stop and the intended risk budget;
   skip setups that do not fit. Do not shrink stops or raise risk to force entries.
4. Forward paper operation with current data: compare modeled and broker fills,
   reconcile orders/positions, and verify stale-data pauses, duplicate-order
   prevention, protective exits, and stop controls. Successful simulation alone
   does not establish actual execution behavior.

Even meeting those conditions supports a risk decision, not certainty of profit
or a promised live date. If the setup is too infrequent or cannot fit one MNQ
within the account's budget, that is a useful reason not to deploy this version.

Sources: [CME mathematical expectation](https://www.cmegroup.com/education/courses/trading-psychology/the-mathematics-of-trading-success),
[NIST proportion intervals](https://itl.nist.gov/div898/handbook/prc/section2/prc241.htm),
[CFTC simulation limitations](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/fraudadv_tradingsystem.html).
