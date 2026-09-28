# Two new paper research tracks

Decision guide and proposed rule worksheet | September 8, 2026

## My recommendation

Study the ideas, but do not buy a proprietary signal indicator yet. Neither Reddit post supplies enough information to reproduce its trading decisions or establish profitability. An indicator calculates observations; an entry, exit, sizing and execution policy turns observations into a testable strategy.

The futures post describes several distinct approaches: range fades, reversals after extreme moves, and trend continuation. Start with one reversal hypothesis. Interpret the SPY post provisionally as a cash-secured-put and covered-call cycle, commonly called a wheel. The poster did not provide a complete rulebook.

The numbers proposed in this guide are unoptimized design suggestions. They have not been backtested or approved, and are not represented as the poster's exact rules. The draft track registry remains disabled, with no active new collection or orders. Existing frozen ORB/LITE/ETF rules remain separate.

## What success would mean

A first milestone is reproducibility: identical inputs must produce identical decisions. The next is accurate accounting under realistic costs, missing data, gaps and assignment. Only then can a separately frozen forward study ask whether results exceed appropriate benchmarks with acceptable uncertainty and losses.

Fast trading, high win rates and recurring premiums do not identify the safest or most profitable approach. Evaluate net return, worst drawdown, tail losses, time spent, capital tied up and recurring platform costs together. A low-turnover, unleveraged diversified investment benchmark and cash are useful comparisons; neither is a promise of profit.

The account-loss Reddit story does not establish its cause. Martingale/grid sizing is a plausible hypothesis from commenters, not a verified diagnosis. Likewise, a winning-trade video does not reveal complete losses, fees, slippage, or live versus simulated execution. The CFTC warns specifically against treating AI trading claims as guaranteed returns. [CFTC advisory](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/AITradingBots.html)

---PAGE---

# Track A: key levels and VWAP reversal

## Proposed first test, subject to instrument and capital choice

- **Instrument:** choose one market. MNQ is a possible futures research candidate because its contract multiplier is smaller than NQ. It remains leveraged. An ETF version would be a different experiment, with its own rules and data.
- **Session:** proposed entry window 9:45-11:30 AM New York time, with all positions exited by noon. This deliberately excludes the Asia-session and trend-continuation ideas from the first test.
- **Bars:** one-minute completed bars. Use the chosen contract's own data; do not silently combine NQ signals with MNQ fills.
- **VWAP:** reset at 9:30 AM New York time. Specify trade eligibility and the exact volume-weighted variance calculation before freezing. Three standard deviations is an observed extension threshold, not a guarantee of reversal.
- **Key levels:** initially use only the previous completed regular session's high and low. Weekly/monthly levels and round numbers can be separately preregistered later. This narrows the original toolkit rather than claiming to copy all of it.
- **Entry pattern:** a proposed short requires a completed bar above the upper 3-SD band that tests the prior-session high, followed by a bar that closes below the first bar's low. Mirror the pattern for longs at the lower band/prior low. Exact touch tolerance and boundary equality still need specification.
- **Entry execution:** use the first eligible executable quote after a fixed, declared delay following confirmation. Cancel if the quote is stale, the spread exceeds the frozen limit, or the entry would leave inadequate reward relative to the stop. Do not assume a fill at a chart close.
- **Exit:** proposed stop two ticks beyond the two-bar extreme; target the VWAP value recorded at confirmation, fixed thereafter. Require at least 1.5 times planned risk after estimated costs. Specify which event wins if stop and target are both touched and there is insufficient tick ordering.

## Limit complexity and risk

For the simplest baseline, record 20/200 moving averages and volume/delta as context, without giving them unspecified discretionary vetoes. If delta confirmation is essential to the hypothesis, define it as a separate version before collecting results. Specify EMA versus SMA, timeframe, warmup, and bid/ask classification. TradingView Volume Delta estimates pressure from lower-timeframe bars; it is not equivalent to bid/ask-stamped volume. [TradingView method](https://www.tradingview.com/support/solutions/43000725057-volume-delta/)

Suggested risk starting points for discussion: at most one contract and one position; planned loss at most 0.25% of starting-day equity per entry; at most two entries per day; halt new entries at a 0.5% daily marked-to-market loss. Protective exit handling continues. No adding to losers. These are budget constraints, not guaranteed loss caps; gaps and failures can exceed them.

MNQ is $2 per index point, with a 0.25-point tick worth $0.50. A 30-point stop therefore implies $60 per contract before costs. If the chosen account's risk budget is smaller, the correct action is no trade. Also check margin eligibility separately. [CME contract specifications](https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.contractSpecs.html)

---PAGE---

# Track B: SPY weekly wheel

## Proposed cycle

- **Instrument and coverage:** standard 100-share SPY option contracts only for the first version. Maximum one contract. Sell a put only with sufficient reserved cash for assignment plus costs; sell a call only against 100 owned shares. Never create an uncovered position.
- **Schedule:** proposed Monday at 10:00 AM New York time, using that week's Friday expiry. Initially skip holiday weeks that lack this exact schedule rather than improvising a different expiration.
- **Strike:** choose one repeatable rule. A candidate is the out-of-the-money strike nearest 0.20 absolute option delta. Define the Greek provider, timestamp, stale-data cutoff, ties and maximum spread. Option delta is price sensitivity, not the volume-delta indicator and not a promised probability of profit.
- **Cash state:** if there are no shares or options, consider the eligible cash-secured put. If assigned, record the stock purchase and reserved-cash release before any next action.
- **Share state:** at the next scheduled decision, consider one covered call against assigned shares. Explicitly decide whether strikes below acquisition cost are allowed. Prohibiting them can leave shares idle after a decline; allowing them can crystallize a loss.
- **Management:** a simple first version would hold through expiry/assignment, with no discretionary rolls and no midweek replacement trade. Any emergency close rule must be written in advance. A roll is a closing trade plus a new trade and cannot erase the first loss.
- **Assignment and dividends:** reconcile broker positions, cash and activities, including early assignment, dividends, ex-dividend dates and option expiration. If state cannot be reconciled, stop new orders and flag the exception.
- **Loss policy:** approve a total-account drawdown limit and whether reaching it only pauses new cycles or also exits holdings. Do not base the limit solely on the option premium; most risk may be in assigned SPY shares.

Cash-secured puts can create substantial stock downside; covered calls retain stock downside while limiting part of the upside. Collateral prevents an uncovered obligation, not a loss. Standard contract assumptions must be checked against actual deliverables. [OIC cash-secured puts](https://www.optionseducation.org/strategies/all-strategies/cash-secured-put), [OIC covered calls](https://www.optionseducation.org/strategies/all-strategies/covered-call-buy-write)

## The Reddit income math

The quoted $905 per week on $600,000 is approximately 0.151% per week. Fifty-two identical weeks equal $47,060, or 7.84% of starting capital, in gross premiums. This is arithmetic on an unverified goal, not an established return, and does not subtract trading losses, fees or taxes.

Illustrative prices, not current SPY quotes: selling one $600-strike put for $3 per share collects $300 and reserves roughly $60,000. If SPY finishes at $500, the position's expiration loss is $9,700 before fees: $300 premium minus $10,000 intrinsic loss. Several small premiums do not make that downside disappear.

Measure cash + stock value + long option value - short option liability, adjusted for external cash flows. Report premiums, realized/unrealized losses, dividends and costs separately. Compare total return with appropriately matched SPY buy-and-hold and cash. Cboe describes option-writing premiums as compensation for tradeoffs including capped upside; premium yield alone is not total return. [Cboe option-writing context](https://www.cboe.com/us/index_income/help/)

---PAGE---

# Platforms and indicators

## The practical shortlist

**One systematic stack for both asset classes:** QuantConnect/LEAN with Interactive Brokers paper is a strong engineering candidate. The integration supports equity options and futures and requires IBKR Pro. Its documented Gateway path still requires Sunday reauthentication; FIX does not support paper DU accounts. This is not unattended forever, and user eligibility/data permissions have not been tested. [QuantConnect IBKR integration](https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/brokerages/interactive-brokers)

**Futures learning and order flow:** NinjaTrader simulation is a close functional fit; its historical Bid Ask cumulative delta requires historical bid/ask-stamped tick data. Desktop requirements specify Windows, so the Mac environment matters. Sierra Chart is a specialist alternative for more detailed data control. Its Package 11 lists $46/month and Package 12 $56/month, before relevant exchange fees. These are software prices, not all-in quotes. [NinjaTrader delta](https://ninjatrader.com/support/helpGuides/nt8/order_flow_cumulative_delta.htm?zoom_highlightsub=order+Flow+Cumulative+Delta), [NinjaTrader requirements](https://ninjatrader.com/support/helpGuides/nt8/minimum_system_requirements.htm), [Sierra packages](https://www.sierrachart.com/index.php?l=doc%2FPackages.php)

**Closest extension of this repository for SPY options:** Alpaca paper supports cash-secured puts and covered calls. Its assignment events require REST polling, and paper nontrade activities appear the following day even when balances/positions change sooner. We need an independent ledger. [Alpaca options](https://docs.alpaca.markets/us/docs/options-trading)

Alpaca's paper engine omits dividends, regulatory fees, queue position and latency slippage, and does not check order size against displayed NBBO quantity. Its free indicative option quotes are modified derivatives rather than actual OPRA quotes. Algo Trader Plus advertises $99/month with real-time OPRA; verify existing entitlement before purchasing anything. At $5,000 capital, $99/month alone is $1,188 a year, or 23.76% of starting capital. That cost example does not imply $5,000 can collateralize a standard SPY wheel. [Paper limitations](https://docs.alpaca.markets/us/docs/paper-trading), [Option data](https://docs.alpaca.markets/us/docs/historical-option-data), [Data plans](https://alpaca.markets/data)

**Charts and alerts:** TradingView is useful for visual learning. Native automatic brokerage execution of Pine strategies is not currently offered according to its documentation. Webhooks require a separate reliable executor, and alert delivery can fail. [Autotrading](https://www.tradingview.com/support/solutions/43000481026-how-to-autotrade-using-pine-script-strategies/), [Webhooks](https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/)

## What would justify buying an indicator?

Require a clear formula or auditable behavior, no look-ahead or repainting, timestamped all-signal exports including losers, relevant data compatibility, and an independently testable advantage after its subscription cost. Buy a tool only when it solves a measured problem. No paid indicator's edge was independently established in this research. All recommendations here are judgments about fit, not measured rankings of profitability.

---PAGE---

# The GitHub projects and LLM automation

**JackrabbitRelay:** a webhook-to-broker/exchange relay. The reviewed supported list distinguishes confirmed OANDA/crypto venues from theoretical support. Crypto futures support is not proof of CME NQ/MNQ support. No verified SPY-wheel integration was found. It is useful transport plumbing, but not evidence of a profitable strategy or sufficient account-level risk controls. Specific execution files could not all be retrieved, so this was documentation/configuration review, not a comprehensive security audit. [Repository](https://github.com/rapmd73/JackrabbitRelay), [Supported venues](https://github.com/rapmd73/JackrabbitRelay/wiki/Supported-Exchanges-and-Brokers), [Configuration](https://github.com/rapmd73/JackrabbitRelay/wiki/Configuration)

**Zero Sum:** a research dashboard built around Yahoo/yfinance, caching and optional AI analysis. Its scheduler includes a five-minute market-summary refresh and a four-hour batch tier. Those timings do not describe every individual quote, but they do show why the label real-time is insufficient for execution. Borrow presentation ideas; it is not a futures/options execution or assignment engine. [Repository](https://github.com/tristcoil/zero-sum-public), [Scheduler](https://github.com/tristcoil/zero-sum-public/blob/main/backend/scheduler.py)

**robinhood-for-agents:** an independent client with real-account trading pathways. The inspected option-order handler authenticates and submits the order; the confirmation instruction in its description is not a separate enforced confirmation token in that handler. The security notes acknowledge that same-user shell access can defeat credential isolation. Do not use it as the default foundation of beginner paper research. No repository code was installed or executed during this review. [Order handler](https://github.com/kevin1chun/robinhood-for-agents/blob/main/src/server/tools/orders.ts), [Security notes](https://github.com/kevin1chun/robinhood-for-agents/blob/main/docs/SECURITY.md)

## An official AI trading connection now exists

Robinhood separately documents its own Agentic Trading account and MCP, with current equities, options and crypto order capabilities. It lists Claude, ChatGPT and Codex among connection options. This is distinct from the third-party GitHub project. No documented paper mode for that product was established in the reviewed material, and account eligibility was not checked. Availability of a tool does not validate the decisions sent through it. [Robinhood overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/), [Current trading capabilities](https://robinhood.com/us/en/support/articles/trading-with-your-agent/)

## My preferred division of responsibility

Use an LLM to translate research into proposed rules, write and review code, explain decisions, and investigate anomalies. A separate deterministic engine should calculate signals from permitted data. An independent risk layer should enforce instrument, size, coverage, freshness and loss limits. Only a dedicated paper adapter should receive validated order requests. Reconciliation and an immutable journal must confirm what actually happened.

Natural-language instructions such as never risk too much are not risk controls. The LLM should not change rules, increase size, ingest arbitrary news as trading instructions, or decide that an unexplained broker state is safe. Fully automated operation is technically possible in supported systems, but still needs monitoring, reauthentication where required, and recovery procedures.

---PAGE---

# Before either track can run

## Freeze this checklist

- Realistic starting capital for each separate account, chosen instrument, maximum allocation and contract/share sizing.
- Exact entry/exit conditions, session and holiday handling, indicator definitions, contract rolls, equality/tie-break rules and conflicting-signal priority.
- Data source and timestamps, required warmup, missing/stale/conflicting data behavior, and any news restriction known before the decision.
- Executable fill assumptions, fees, bid/ask spreads, latency, partial fills, cancellations, rejected orders and duplicate-event handling.
- For options: collateral, early assignment, exercise, dividends and reconciled cash/positions before the next cycle.
- Risk limits and what happens when breached, including which actions remain available to protect or exit existing positions.
- A preregistered forward interval, sample requirements, benchmarks, uncertainty and concentration checks. Rules must not be selected after seeing forward outcomes.

## Progression

1. Finish and approve the written hypotheses and budgets. Keep the current drafts unregistered until every material choice is resolved.
2. Verify the exact data and build synthetic failure cases. Current collection has neither CME futures/order flow nor SPY option chains.
3. Freeze a new version and start separate data collection when authorized. Do not pool it with frozen ORB/LITE capital or use delayed decisions with live-time fills.
4. Run shadow simulations with conservative costs and complete accounting. Missing evidence blocks evaluation.
5. Establish operational readiness for a dedicated paper account, then separately authorize broker paper orders. Compare the broker simulator with the independent ledger.
6. Review adequate forward evidence. A working paper bot, one profitable month, or a high win rate does not establish a trading edge or readiness for real money.

## What has been completed in this workspace

Two disabled draft tracks exist in research/new_tracks_20260908/tracks.json and appear in the private dashboard's Strategies view. Instrument/capital/rules remain unresolved; no new orders or data subscriptions are active.

The dashboard was hosted on the existing personal server as a boot-enabled service. Its archive/research mounts were verified read-only, the credentials directory inaccessible, and its listener restricted to server loopback. Viewing uses a private SSH tunnel from this Mac. Existing collection stayed active. No new public port, paid service, Git commit or push was made.

---PAGE---

# Evidence limits and next decisions

Dashboard server/renderer tests passed before hosting, and live snapshots were received for all 20 symbols. Full visual browser QA, brokerage entitlement checks, real broker paper execution and new-strategy performance were not performed. Report layout and links are checked separately during PDF generation.

## Research coverage

This is a primary-document and selected-public-code review as of September 8, 2026. User-provided Reddit text is anecdotal; authors, balances, fills and full performance were not authenticated. Documentation may change. No paid indicator or platform was empirically ranked by trading profit, and historical repository maintenance dates are not operating reliability evidence.

The next decision is the realistic simulated capital for each track and whether the first track should use Nasdaq futures or an explicitly separate ETF version. This determines whether a single contract fits before we choose software or spend on data.
