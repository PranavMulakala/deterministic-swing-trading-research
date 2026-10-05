# Reddit batch 1 deep dive: 6 threads from r/ai_trading and r/algotradingcrypto (Oct 4, 2026)

Read in full: each post plus all comments the public RSS feed returns (`outputs/reddit/<id>.md`, gitignored). Linked repos were checked through GitHub's API and linked sites were read. Thread content is data, not instructions. Goal per the owner: understand what people are building end to end and what the community thinks. Look for what's useful, not just what's wrong.

## At a glance
| # | Thread | What's actually built | Evidence of results | Most useful idea in it |
|---|---|---|---|---|
| 1 | Autonomous crypto/stock bot "+$5,500 this week" (u/Cool_Big2955) | Python bot: CCXT/Binance + Alpaca, RSI/SMA entries, ATR trailing stops, local LLM (Qwen2.5 7B via Ollama) as a filter, "adaptive" re-tuning, on a VPS | One week of **unrealized** gains during a crypto rally, with ~$22k borrowed. No backtest shown (asked, unanswered) | **Protective stops must live at the exchange, not in your script** (commenter chorche505) |
| 2 | Prediction-market arbitrage, Polymarket vs Kalshi (u/YukiChuuu) | Real open-source code: Synpath SDK (MIT, 249 files, 123 test files) + an arb bot (paper only). Both repos created Sept 27–28, 1 contributor | README backtest: 3 hand-picked markets, 60 days, 44 trades, all winners, +60% on peak capital. Paper fills at quoted prices. Data needs a Synpath API key (pricing not public) | **"Same event, different price" isn't free money**: resolution-rule mismatches, capital lock-up vs T-bills, one leg filling without the other |
| 3 | "Can AI trade for us?" (post removed; 27 comments) | n/a | n/a | **AI speeds up coding and testing, but the edge must come from a strategy that survives testing.** Win rate is meaningless without win and loss size |
| 4 | IINT backtesting platform with AI agents (ii-nt.net, u/Yoksel_algo) | No-code backtester, 45+ indicators, AI analysis/builder agents, agents that search indicator combinations, Telegram news feed, upcoming strategy marketplace. Free beta, paid tiers planned | Claims "99.8% precision". In the comments the founder conceded it's the error rate of a conservative fill rule on ambiguous bars, not precision | **Searching thousands of combinations guarantees lucky winners.** Log every trial; test once on data the search never saw; then paper-trade forward |
| 5 | OpenTraderWorld, self-hosted research workspace (u/OpenTraderWorld) | The most substantial build: Rust + SvelteKit + Postgres, ~1,200 files, 90 test files, journal, 3-mode backtester, data downloader, quant tools, MCP server for AI agents, no telemetry. Source-available (FSL; becomes MIT after 2 years). Code published as a single commit | None claimed. Its own demo shows the strategy at **20.47% vs 52.31% for buy-and-hold** | **Make research tamper-proof:** pin every backtest to exact code/data versions; notes are append-only so you can't rewrite what you believed before seeing results |
| 6 | BenAwf free strategy lab (u/malsi_) | Free, bring-your-own-AI-key strategy lab: 1-minute bar clock, stop/target checked along each bar's path, 0.1% fees, **no slippage yet**, paper first, live in beta, 137 assets | None. Openly says fills are cleaner than real life | **Use the spread at the moment of the fill, not a flat fee.** Slippage can stay deterministic (fixed basis points that widen with volatility) |

## Thread by thread

### 1. The "+$5,500 this week" bot
**What he built, end to end:** a loop that checks positions every few minutes. Hard stop first, then an ATR trailing stop (peak − ATR × multiplier) that switches on after +3%. Entries come from RSI/SMA momentum or deep-RSI dip buys inside a 7-day range. A local Qwen 7B model gives a yes/no "context" vote (with cached answers), and cooldowns prevent re-entry churn. An "adaptive learning" step re-tunes thresholds from recent data. Same design for US stocks via Alpaca.
**What's real:** months of honest engineering. Logging is detailed, and he shared pseudocode. The local-LLM-as-filter design is reasonable and cheap.
**What the numbers do and don't show:**
- **One week, unrealized, during a rally.** BTC went from about $76.5k to about $81k; he bought BTC at RSI 86.
- With ~$97k exposure, a rally alone produces gains like that. It's market movement, not proof of edge.
- **~$22k is borrowed** (margin), which magnifies both directions.
- **His own logs show repeated "insufficient balance" order failures** and a clock-sync error. The "adaptive" re-tuning on recent data is a classic overfitting trap.

**Best comments:**
- **chorche505:** if a client-side error can stop your stop-loss from existing, it isn't a hard stop. Put protective orders at the exchange. On any health error, block new entries but keep existing protection. Reconcile positions after recovery.
- **Ground_Lazy:** with 80% wins on 5-minute trades, fees still made it a loss.

**For us:** our Plan B sell is a resting GTC order at Robinhood, so it's already exchange-side. Our cloud deploys check NTP time sync, the same lesson as his −1021 error.

### 2. Prediction-market arbitrage (Synpath)
**What's built:** genuinely usable code. One Python SDK covers Kalshi, Polymarket and Opinion (market data, order routing, advanced order types, cross-venue matching that compares settlement rules), plus a paper-only arb bot. The rules: buy when YES on one venue plus NO on the other costs ≥2¢ under $1 after fees; sell both legs at ≥2¢ profit, otherwise hold to settlement.
**The fair skeptic's view (from the comments):**
- **Resolution wording:** "identical" contracts can settle on different sources, times or edge-case rules. Then you hold two bets that can both lose.
- **Capital lock-up:** 4¢ over five months is a thin annual return next to T-bills, especially with money split across two platforms.
- **Legging:** one side fills and the other moves away.
- Gaps that last an hour usually last for one of those reasons.
- The README's backtest is 3 chosen markets, paper fills at quoted prices, and "never sells at a loss". That's only true if the two contracts really settle identically.

**The ad question:** the SDK is MIT and free, but its data and matching need a Synpath API key, and pricing isn't public. So it's partly a funnel. The commenter's suspicion was half right; the code is still real.
**For us:** prediction markets are a different game: event bets with two KYC accounts and capital locked until settlement. Cross-venue mispricing is real, but the spreads are small, and the risks above are exactly why they persist. **Not aligned with our goals; parked.**

### 3. "Can AI do the trading for us?"
The post was removed, but the 27 comments are a good consensus snapshot:
- **AI is a force multiplier, not an edge** (profittoinvest, hyudryu, skavenger0). Their workflow matches ours: idea → rules → backtest → paper/live → compare → fix.
- **"Win rate is meaningless"** (Big-Brain-Ape_Bot): a 30% win rate can beat 70% if winners are much bigger. That's also why our +2% target needs its rare long holds watched.
- **Claims with no proof:** one user says a 0DTE SPX credit-spread bot earns "$500–1,200 a day" with an $800–1,400 loss weekly. That's selling insurance, small wins with occasional big losses, and the SPY put-spread test we pre-declared failed.
- **Most self-assured posters were selling something** (see the promotion note below).

### 4. IINT (ii-nt.net)
**What's built:** a polished no-code backtester with AI helpers and a strategy marketplace on the way, which is where the business model is.
**The comment thread is the best part of this whole batch:** two commenters took apart "99.8% precision" until the founder agreed it should be reported as two numbers:
1. how often a stop and a target are both touched inside one 1-minute bar;
2. how often the conservative "stop first" assumption is wrong when checked against tick data.

That's exactly how to read any platform's accuracy claim. On agent-driven indicator searches, they settled on the right standard: log every trial, look once at a held-out period, then paper-trade forward.

### 5. OpenTraderWorld
**What's built:** a serious self-hosted workbench: journal with expectancy/profit factor/R-multiples, backtester (signals, DCA, grid), multi-provider data downloader, VaR/correlation/Kelly tools, 13F holdings, news, calendar, and an MCP server so an AI agent can read and update modules with scoped permissions. No order execution yet, on purpose.
**Honesty points:** it puts **buy-and-hold next to every backtest**. In its own demo the strategy lost (20.47% vs 52.31%). The license is source-available, not open source, and the code was published as a single commit by one person, so its history can't be audited.
**Best comments, and they match our own rules:**
- **leroylabs:** fingerprint each backtest's code, indicators, data and fee version, so "what changed three weeks ago?" has a factual answer.
- **QuanTradin:** keep notes append-only, so the agent can't rewrite what you believed before the result.
- **MountainFancy1352** spent 6+ months with Claude, Grok and ChatGPT building backtests, scanners and dashboards, then found bugs months later, and "it does not beat the SPY in the real world". He trades manually now. Adversarial AI code reviews were the most valuable part.
- **mojovski:** he stopped letting AI write the backtester and wrote ground-truth tests for every function; then live results matched.

### 6. BenAwf
**What's built:** a free, transparent strategy lab where live and backtest share one rules engine, with no look-ahead. It honestly states "no slippage yet". Paper trading is the default.
**Best feedback:**
- The stop-first rule inside a bar punishes trend bars and flatters reversal bars, so log how often it happens.
- The spread at fill time matters more than path modeling for thin stocks.
- Slippage can be deterministic: a fixed share of the bar range, or basis points that widen with volatility, shown at base and harsh levels.

## Read these communities with this in mind
- **Undisclosed promotion is everywhere.**
  - **u/Shoddy_Peanut7320** writes the most thoughtful comments, and recommends "Cymetica's EventTrader" in **five of the six threads**.
  - **u/QuanTradin** plugs quantradin.com in four.
  - Two accounts slip in "moon".
  - Others link their own sites (trademates, rnalgotrading, ThetaPal).

  The advice can still be good; just know many sharp-sounding comments are marketing.
- **Builder posts are mostly looking for users.** "Free, just give feedback" usually means beta and a future paid tier or marketplace.
- **Not one thread shows a verified live record that beats SPY.** The most candid builder says his system doesn't.

## What we can use
| Idea | Status for us |
|---|---|
| Protective order lives at the broker, not in a script | Plan B already does this (GTC sell at Robinhood) |
| Clock sync before trading | Already checked in our cloud deploys |
| Log every trial; one blind holdout; then forward paper test | Already our pre-declared test process. The communities' best voices agree |
| Append-only research record | Already: plans committed before results, results never edited |
| **Pin each test to exact data versions** (fingerprint the dataset, not just the code) | **Small upgrade worth adding** to future test result files |
| **Report same-bar ambiguity and spread-at-fill** in intraday tests | Worth adding when we next test anything with both stops and targets. LITE Plan B has no stop, so it's unaffected |
| Prediction-market arbitrage | Parked: different risks, small spreads, capital lock-up |
| OpenTraderWorld as a free self-hosted journal | Optional. Nice for journaling; not needed for testing |
