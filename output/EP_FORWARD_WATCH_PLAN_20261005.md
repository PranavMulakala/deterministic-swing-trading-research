# Forward paper watch of test #16 (Qullamaggie's episodic pivot): pre-declared plan (October 5, 2026)

- **Owner's request:** "yes set up the forward paper watch" (Oct 5, after the test #16 results).
- **Committed before any forward data exists:** the first watched day is Tue Oct 6, 2026.
- **Paper only:** no orders and no broker account. Read-only Alpaca market data (the LITE paper key, as the scanner uses) and SEC EDGAR filing times (User-Agent with the owner's approved Gmail).
- Nothing changes in Plan B, the bots or MNQ.

## What runs
- **Where and when:** on the cloud server, as its own system user, Monday–Friday on trading days.
- **10:50 AM ET email: "EP watch".** Every 10%+ gap-up on a liquid stock that morning (20-day average dollar volume ≥ $20M), marked with:
  - whether an earnings 8-K came out between the previous close and 10:30;
  - the first-30-minute volume ÷ a normal day's;
  - the first-hour high and the day's low so far;
  - whether it passes test #16's rule so far: the paper buy trigger (above the first-hour high after 10:30) and the stop (the day's low).
  - Data is 15 minutes delayed (free plan). The list is for watching and learning.
- **5:05 PM ET email: "EP paper ledger".** The record of truth, rebuilt every evening from fresh data:
  - **Main ledger:** test #16's exact rule (earnings EP), $100,000 paper, 1% risk, 25% cap.
  - **Info ledger:** the same rule without the earnings requirement ("all catalysts").
  - Today's paper entries and exits, open positions, and both ledgers' value against $100,000 in SPY from the Oct 5 close.
  - The event log below, so far.

## No tuning
- **The rules are imported unchanged** from `research/ep_test_v1/backtest.py` (test #16, commit 2bdb22a): the same functions for the signal, entry, stop, day-3 half, 10-day trail, sizing and cash timing. The deploy manifest records the file hashes.
- **Universe:** the same 5,259 US stocks as the backtest (listed as of Sep 2026). New listings aren't added.

## Dates
- **New events:** Tue Oct 6, 2026 – Fri Jan 8, 2027 (about 3 months, including the October–November earnings season).
- **Tracking continues** for open positions and for the event log's 20-day outcomes **until Fri Feb 12, 2027**.
- **Then the job stops itself** (one "finished" email) and the timers get switched off.

## Honest expectation
- **The ledgers will barely trade.** The exact rule traded about twice a year in 2016–2026 (15 trades), and "all catalysts" about 8 a year. Expect 0–1 main trades and about 2 info trades.
- **So the ledgers can't prove or disprove anything.** They show whether live behavior matches the backtest, and they show what the rule actually does.

## Added now (before any forward data): a forward event log, the real measurement
- **Every liquid 10%+ gap-up** in the window, split into **earnings** (8-K in the window, as in the rule) and **other**.
- **Reference price:** the price at 10:30 (the close of the 10:25 five-minute bar).
- **Outcomes:** the stock's close **5 and 20 trading days later** ÷ the reference price − 1, **minus SPY's return** over the same span (SPY's 10:30 price on the event day to its close on that day).
- **Expected count:** about 60–100 earnings gap-ups (2,549 in 10.7 years in the backtest data, more in recent years).
- **Pre-declared reading:** "evidence that earnings gap-ups keep drifting up" only if the **average 20-day excess return is above 0 with a t-statistic ≥ 2.0**. Otherwise not shown.
  - This is the forward version of the Martineau (2021) question.
  - It's information for future decisions, not a trading signal.

## Reporting
- Each weekend scorecard adds one line: both ledgers vs SPY, the number of events, and the event log's average outcomes so far.
- **A final results doc after Feb 12, 2027.**
