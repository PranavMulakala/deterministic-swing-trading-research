# Methodology and limits

## What this is

Version 1 is a deterministic research system for a frozen list of 15 liquid US ETFs. It is long/cash-only, starts with $500, allows fractional shares, and cannot submit broker orders. The LLM is outside the signal, sizing, risk, and execution paths.

The strategy buys an oversold pullback only when the adjusted close is above its 200-day simple moving average and RSI(2) is below 10. The signal is computed after the close and filled at the next available bar's open. Each position gets a fixed 2 x ATR(14) stop based on that entry open, exits after a close above SMA(20), or reaches a 20-session time stop. Close-derived exits fill at the next available open. Stops use the stop price unless the market gaps below it, in which case the open is used.

## Costs and risk

Every buy and sell applies 1 bp of half-spread, 2 bp of slippage, and 0.1 bp of fees. These are explicit assumptions, not observed historical quotes. Planned loss includes modeled costs at entry and stop. The isolated risk manager limits a trade to 0.5% of current equity, aggregate open planned risk to 3%, and new entries after 2% realized loss in a day. Fractional sizes round down to six decimals. The global kill switch and duplicate-order guard are tested; live execution remains disabled.

## Data provenance

The fetch step uses Yahoo Finance's unofficial chart endpoint. Adjusted OHLC is derived by multiplying raw OHLC by adjusted-close/raw-close for each session. The downloader records per-file SHA-256 checksums, date coverage, and row counts in `data/pinned/manifest.json`; reproduction refuses changed files.

Important limitations: Yahoo can revise history and provides no service guarantee; this snapshot is only immutable after it is downloaded and checksummed. The proportional OHLC adjustment is an approximation. Volume is not adjusted. There are no historical bid/ask quotes. The static current ETF universe creates survivorship/availability bias, and funds launched later have shorter histories. Daily OHLC cannot resolve intraday path when several levels are touched. Results are therefore research evidence, not proof of an executable edge.

## Evaluation

The preregistered in-sample period ends 2020-12-31. The untouched out-of-sample period begins 2021-01-01 and ends 2026-08-31. Both use identical code and assumptions. Comparisons are cost-adjusted SPY buy-and-hold and a monthly top-three 126-session momentum portfolio that requires positive momentum and price above SMA(200), with next-session-open rebalancing.

No parameter optimizer is included. Any future modification must create a new strategy/config ID and cannot overwrite v1 results. A plausible reason for the strategy to work is short-horizon mean reversion inside diversified, persistent ETF uptrends. It is invalidated as an implementation if event-ordering, risk, or reproducibility tests fail; it is invalidated as a candidate edge if OOS results are economically weak after costs or meaningfully worse than the preregistered benchmarks.
