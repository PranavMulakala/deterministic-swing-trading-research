# MNQ paper-trading plan: 8 weeks (DRAFT for your review, September 30, 2026)

**Status: APPROVED by the owner on Sept 30, 2026 at about 9:50 AM ET, with Option A (the existing frozen rule).** It starts Oct 5 if Step 0 holds. Paper money only. No real-money step can come out of this plan, whatever the result.

**Why we're doing it:** goal part 2, which you approved on Sept 30: "paper-trade MNQ for 8 weeks with rules written first, judged against SPY." It's for learning how futures trading actually behaves. It isn't an income plan.

## Two caveats up front
1. **The rule has no independent evidence behind it.**
   - It came from Reddit examples and was written down on Sept 8, before any data was looked at.
   - The only historical check (4 days in early September) found **zero qualifying setups**.
   - So this run tests the plumbing and teaches the mechanics. It doesn't test a strategy we have reason to believe in.
2. **It may trade very rarely.**
   - The rule is strict, and the risk limit is small ($12.50 a trade).
   - Eight weeks could produce a handful of trades, or none.
   - The plan says in advance what we conclude in that case.

## Step 0: the bot has to stay up first (needs you, about 10 minutes)
**What I found this morning (read-only check of the server, 9:06 AM ET):**
- **The IBKR Gateway is stopped.** It shut itself down cleanly at 7:45 PM ET on Sept 29 (23:45 UTC). That matches IBKR's daily "auto logoff" timer.
- **Nothing restarts it.** The server only restarts the Gateway after a crash, not after a clean exit. So each login currently buys one day of data.
- **The collector and the strategy program are still running,** but they're waiting on a Gateway that isn't there (`GATEWAY_LOGIN_OR_API_REQUIRED`).
- **Yesterday's data was captured:** about 9.4 million quotes and 1.1 million trades in total are stored.

**The fix (two changes, both need your OK because they're settings on your server and your IBKR login):**
1. **In the Gateway's own settings** (you, through the same private login screen as yesterday): switch "Auto logoff" to **"Auto restart"**. IBKR then keeps the session alive through the week; a fresh login is normally needed about once a week, after the weekend.
2. **On the server** (me, with your OK): make the Gateway service start again whenever it exits. This is a one-line change to the service file.

**Done when:** the Gateway is still connected the morning after its first overnight restart, without you touching it.

## What runs
- **Where:** the IBKR **paper** account on your cloud server, the same one that's already set up. One December 2026 Micro Nasdaq contract (**MNQZ6**). It expires Dec 18, after this test ends, so there's no contract roll.
- **Pretend account:** **$5,000**, tracked separately from the paper account's balance.
- **Rules:** the ones already written and frozen on Sept 8 and Sept 21. Nothing new is invented for this test:
  - [the signal](../research/mnq_feasibility_v1/PROTOCOL.md)
  - [how orders are placed](../cloud/ibkr_paper_v1/PAPER_EXECUTION_PROTOCOL.md)

## The rules, in plain language
**When it looks:** 9:45 to 11:30 AM New York time, on full trading days only.

**The setup (a "stretched too far, now snapping back" trade):**
1. Price pushes up to **yesterday's high** and is unusually far above the day's average price. "Unusually far" means more than 3 standard deviations above VWAP, the volume-weighted average price since 9:30.
2. The **next 1-minute bar closes below** the low of that stretched bar.
3. Then the bot **sells short 1 contract**, betting on a fall back to the average.

The mirror image at **yesterday's low** is a buy.

**Exits, all set the moment it enters:**
- **Target:** the day's average price (VWAP) at the moment of entry.
- **Stop:** two ticks beyond the extreme of those two bars.
- **Time:** out by noon, no matter what.

**Size and safety limits:**

| Limit | Value |
|---|---|
| Contracts | 1 MNQ ($2 per point) |
| Most it plans to lose on one trade | **$12.50** (0.25% of $5,000), including fees |
| Reward must be at least | 1.5× the risk, after fees |
| Trades per day | at most 2 |
| Daily loss pause | down **$25** in a day → no more trades that day |
| Whole-test stop | pretend account down **5% from its peak** (about $250) → the test ends |
| Fees seen on paper | about $0.61 per side, $1.22 per round trip |

- **What $12.50 means in practice:** after fees, the stop can only be about **5 points** away. MNQ often moves 5 points in seconds, so many setups won't fit the risk limit. Those are logged and skipped. The stop is never squeezed to make a trade fit.
- **A stop isn't a guarantee.** In a fast market the fill can be worse than the stop price, so a loss can exceed $12.50.

## Dates
- **Proposed window:** Monday **Oct 5** to Wednesday **Nov 25**, 2026.
- **Trading days:** **38 full sessions.** Thanksgiving (Nov 26) and the half day after it (Nov 27) are excluded in advance.
- **Start condition:** Step 0 is done, and the bot has one complete previous session on record. If Step 0 slips, the start moves to the next Monday and the window stays 8 weeks.

## Nothing changes during the 8 weeks
- **No rule changes.** Not the signal, the stop, the target, the times, or the risk limits.
- **Plumbing fixes only.** A fix for a crash or a reporting bug is allowed. Each one gets logged with its date, and trades before and after it are marked.
- **Missed days stay missed.** If the Gateway is down, that day counts as "not covered". We don't go back and guess what would have happened.

## What gets logged
- **Every signal:** taken or skipped, with the reason (didn't fit $12.50, reward too small, spread too wide, already paused).
- **Every order, fill and fee,** from IBKR's own records.
- **The pretend account's value** at each day's close.
- **Every pause and every outage,** with times.
- **Paper vs model:** for each trade, how the real paper fill compared with what the simulator expected (price and timing).

## Weekly scorecard (every weekend)

| Line | Example |
|---|---|
| Sessions covered / possible | 5 / 5 |
| Setups seen → fit the risk limit → taken | 3 → 1 → 1 |
| Wins / losses | 1 / 0 |
| Net P&L after fees, this week and total | +$14 / +$14 |
| Pretend account | $5,014 |
| Worst drop so far | −$0 |
| **SPY over the same dates on $5,000** | +$62 |
| Paper fill vs model | 1 tick worse on entry |
| Incidents | Gateway re-login Sunday |

## How it's judged (fixed now)
**The SPY comparison:** $5,000 put into SPY at the Oct 5 open and valued at the Nov 25 close, dividends included, next to the pretend account's final value. Both are reported in dollars every week.

**Be ready for this:** the bot risks $12.50 a trade, so even a good 8 weeks might be +$50 to +$100. SPY can easily move ±$250 on $5,000 in 8 weeks. Eight weeks can't prove the rule beats SPY or loses to it. So the verdict has three possible outcomes:

| Outcome | When | What we conclude |
|---|---|---|
| **Not enough to judge** | Fewer than **10** closed trades | The rule is too rare at this risk size. No verdict on profit. Decide whether it's worth any more time. |
| **Did not work** | 10 or more trades, and net P&L after fees is **at or below $0**, or profit factor is below 1.3, or the 5% stop was hit | Stop. No retuning, no extension. |
| **Worth more paper time** | 10 or more trades, net P&L **above $0**, profit factor at least **1.3**, the 5% stop never hit, and paper fills within 2 ticks of the model on average | Write a new plan for a longer paper run. Still no real money. |

**Whatever the outcome:** the final report states plainly how the pretend account did next to the $5,000 in SPY.

## What would stop the test early
- The pretend account falls 5% from its peak (the rule's own stop).
- IBKR's records and the bot's records disagree about an order or a position. Halt until it's explained.
- The Gateway is down for **5 sessions in a row.** Pause and decide with you.
- You say stop.

## What I need from you
1. **Yes or no to this plan,** or edits.
2. **Step 0:** about 10 minutes to log into the Gateway, change one setting, and OK my one-line server change.
3. **About once a week:** a Gateway re-login after the weekend (about 5 minutes), when the bot emails that it needs it.
4. **Your choice on the rule:**
   - **Option A (what this draft assumes):** run the existing frozen rule, knowing it may trade rarely.
   - **Option B:** we first write a different rule. Under goal part 3, that needs independent evidence, and I don't have an intraday rule on a single index that has it.

## Costs
- **New spending: $0.** Paper account, existing server, existing market-data subscription.
- **Real money at risk: $0.**

## Approval and Step 0 log (Sept 30, 2026)
- **Approved:** the owner said "Yes" to the plan and chose Option A.
- **Step 0 diagnosis, corrected:**
  - "Auto restart" was already on in the Gateway.
  - At 23:45 UTC the Gateway writes its restart file, starts a fresh copy of itself and exits.
  - The service's `KillMode=control-group` then killed that fresh copy along with the old process.
  - The same thing happened on Sept 21, which caused the Sept 22 outage.
- **Fix applied at 10:03 ET (owner approved; the owner logged in again at 10:04):**
  - The service now runs a small wrapper. It stays alive while any Gateway java process is running, so the fresh copy survives.
  - If no Gateway process is left, the service restarts to a login screen (`Restart=always`).
  - The change is in `cloud/ibkr_paper_v1/install_gateway.sh` and in a drop-in on the server.
- **Open question:** the Gateway's log still prints "Daily auto-restart is not enabled" at login. What that line means isn't confirmed.
- **Still to verify:** the first overnight restart, tonight at 23:45 UTC (7:45 PM ET). Step 0 is done only if the collector is still `COLLECTING_REALTIME` tomorrow morning without a new login.
