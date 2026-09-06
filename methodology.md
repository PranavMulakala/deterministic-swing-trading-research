# Methodology and limits

## What this is

Version 1 is a deterministic research system for a frozen list of 15 liquid US ETFs. It is long/cash-only, starts with $500, allows fractional shares, and cannot submit broker orders. The LLM is outside the signal, sizing, risk, and execution paths.

The strategy buys an oversold pullback only when the adjusted close is above its 200-day simple moving average and RSI(2) is below 10. The signal is computed after the close and filled at the next available bar's open. Each position gets a fixed 2 x ATR(14) stop based on that entry open, exits after a close above SMA(20), or reaches a 20-session time stop. Close-derived exits fill at the next available open. Stops use the stop price unless the market gaps below it, in which case the open is used. For comparable terminal equity, any position still open on the final evaluation date is forcibly liquidated at that date's adjusted close with modeled sell costs. This is an evaluation-boundary convention, not an ordinary strategy exit; it affected five trades across both reported splits.

## Costs and risk

Every buy and sell applies 1 bp of half-spread, 2 bp of slippage, and 0.1 bp of fees. These are explicit assumptions, not observed historical quotes. Planned loss includes modeled costs at entry and stop. The isolated risk manager limits a trade to 0.5% of current equity, aggregate open planned risk to 3%, and new entries after 2% realized loss in a day. Fractional sizes round down to six decimals. At a $500 scale, cash already deployed can make a valid pending signal calculate to zero quantity; these are logged as rejections and reported separately rather than silently discarded. The global kill switch and duplicate-order guard are tested; live execution remains disabled.

The frozen historical run produced zero daily-loss-halt rejections. The backtest can exercise this path when one or more previously scheduled exits realize at least 2% loss at the open before later pending entries are considered; an integration test now proves that event ordering. Intraday protective stops occur after that day's open entries in the daily-bar model, so they cannot cancel entries already filled earlier at the open. A future broker-paper engine must evaluate the same rule continuously from actual, timestamped fill events rather than infer intraday order from daily OHLC.

## Data provenance

The fetch step uses Yahoo Finance's unofficial chart endpoint. Adjusted OHLC is derived by multiplying raw OHLC by adjusted-close/raw-close for each session. Yahoo's adjusted-close field is intended to reflect splits and cash distributions, so the back-adjusted OHLC used here has total-return-style semantics: dividends are implicit in the adjusted price series and are not posted as separate cash ledger entries. This is equivalent to assuming distribution reinvestment through the adjusted series, not simulating the timing or fractional mechanics of an actual dividend payment. The downloader records per-file SHA-256 checksums, date coverage, and row counts in `data/pinned/manifest.json`; reproduction refuses changed files.

Important limitations: Yahoo can revise history and provides no service guarantee; this snapshot is only immutable after it is downloaded and checksummed. The proportional OHLC adjustment is an approximation. Volume is not adjusted. There are no historical bid/ask quotes. The static current ETF universe creates survivorship/availability bias, and funds launched later have shorter histories. Daily OHLC cannot resolve intraday path when several levels are touched. Results are therefore research evidence, not proof of an executable edge.

## Evaluation

The preregistered in-sample period ends 2020-12-31. The untouched out-of-sample period begins 2021-01-01 and ends 2026-08-31. Both use identical code and assumptions. Comparisons are cost-adjusted SPY buy-and-hold and a monthly top-three 126-session momentum portfolio that requires positive momentum and price above SMA(200), with next-session-open rebalancing. The deliberately simple momentum implementation fully liquidates and equally repurchases its selected names at each rebalance, including names that remain selected; this applies the stated costs conservatively but creates more turnover than a production portfolio optimizer would.

No parameter optimizer is included. Any future modification must create a new strategy/config ID and cannot overwrite v1 results. A plausible reason for the strategy to work is short-horizon mean reversion inside diversified, persistent ETF uptrends. It is invalidated as an implementation if event-ordering, risk, or reproducibility tests fail; it is invalidated as a candidate edge if OOS results are economically weak after costs or meaningfully worse than the preregistered benchmarks. Post-validation clarifications are recorded in `preregistration/v1_post_validation_addendum.md`; the original v1 preregistration and frozen config remain unchanged in Git history.

## Paper-execution layer and non-equivalence to the frozen backtest

The post-validation paper adapter is an operational harness, not a claim that the frozen v1 experiment is deployable unchanged.

Alpaca's current order documentation says fractional equity orders support DAY time-in-force, while whole-share orders support GTC. A DAY protective stop expires at the close and cannot protect an overnight swing position. The adapter therefore rejects fractional entries and submits only whole-share market/GTC OTO entries whose child is a broker-native stop. This is stricter than the frozen backtest, which sizes fractional shares. At $500, the difference can materially increase zero-quantity rejections.

The live scanner requests Alpaca daily bars using the fixed IEX feed and `adjustment=all`. The frozen backtest uses pinned Yahoo adjusted OHLC. Both use the same indicator formulas and frozen parameters, but vendor, feed, and corporate-action adjustments may differ.

Alpaca's paper documentation describes additional simulation limits: Paper Only accounts receive IEX market data; dividends and regulatory fees are not simulated; eligible orders are randomly partially filled 10% of the time; and pattern-day-trader checks are simulated. The OTO child is not active until its parent entry completely fills. The operational reconciler therefore treats an observed partial entry as unprotected and halts new submissions. Because paper cash excludes those external movements, the journal also reconciles observed cash to its $500 baseline plus or minus exact broker-confirmed fill notionals, with a one-cent tolerance. Paper results still cannot be assumed to represent live fills.

The backtest fills entries at the next bar's exact open. The human-approved adapter deliberately submits only during regular market hours after a fresh quote and owner confirmation. Its fill may be after the opening print. The approved maximum-entry reference is only a pre-submit guard; the market fill can be worse, and a stop may fill below its stop price during a fast or gapping market. Reconciliation measures risk from the actual entry fill and latches the kill switch if the observed fill breaches the approved risk ceiling. The journal records actual broker fills so these implementation shortfalls can be measured, but paper outcomes are not directly interchangeable with the frozen backtest distribution.

These constraints are why `PAPER_READINESS.md` records a no-go verdict for a faithful v1 paper trial. Resolving them requires a new pre-registered execution specification, more capital/whole-share sizing, or a different broker whose documented order semantics satisfy fractional persistent native stops. It must not be treated as a silent v1 parameter change.
