# Pre-market quant and Robinhood live-pilot assessment

**Research session: READY. Real-money pilot: NO-GO.**

The requested pre-market goal is to reduce uncertainty and identify a justified
path to live trading, not to guarantee returns or turn on orders by a deadline.
September 9 cloud readiness is verified in [the deployment report](READINESS_20260909.md).
The new historical capital diagnosis is separate from that frozen forward sample.

## What tonight actually established

The additional study tested all $500/$5,000/$10,000 whole-share cases, both entry
styles, both costs, and matched one-/five-minute execution: 36 deterministic
scenarios. All 385 trade records and 5,400 daily rows reconciled independently;
all original $500 controls matched. No original source, strategy, cloud schedule,
credentials or brokerage account changed.

At 10 bps per side, the 170-session dip test ended at $4,625.84 from $5,000 and
$9,177.95 from $10,000. Six larger-capital cases lost; two stayed in cash. Of 50
baseline dip trades, 43 hit the modeled stop. Only seven trades were profitable.
The VWAP baseline had five trades, four losers. More capital was a feasibility
change, not the missing evidence of positive expectancy. Full results and limits:
[capital diagnosis](../research/lite_capital_diagnostic_v1/README.md).

The previously frozen quote/trade ORB study also failed its economic acceptance
conditions: primary A ended at $4,909.17 from $5,000 with nine trades; B made none.
These are prior development data, not new or independent evidence. See the
[preserved ORB report](../research/orb_quote_v2/README.md). A few profitable upcoming
days would not erase those findings or establish a 100% reliable strategy.

## Current gates

| Gate | Evidence | Verdict |
|---|---|---|
| Cloud research setup | 14 caught-up streams; tested automatic timer; source and ledger integrity; $5k/$10k arms | PASS for research |
| Capital sizing | Whole shares can fit many more signals under unchanged 0.5% planned risk | Feasible in simulation only |
| Economic case | All trading larger-capital LITE cases lost; ORB acceptance failed | FAIL for current rules |
| Unseen evidence | One completed forward date; September 9 capital arms have no completed date yet | Insufficient |
| Fast live decisions | Collector deliberately waits 20 minutes; replay after close; historical bars may be revised | Not a live decision feed |
| Robinhood account/connector | Official capability documented; zero Robinhood tools callable in this session | Unverified here |
| Broker execution contract | Exact IOC/limit/protection/TIF/partial-fill/retry/latency behavior not observed | Unverified |
| Unattended live operations | No verified broker restart/reconciliation or external alert/kill workflow | Unverified |

## Robinhood: what is confirmed, and what is not

Robinhood documents an official Trading MCP at `https://agent.robinhood.com/mcp/trading`.
It uses a dedicated Agentic account for order placement, while granting connected
agents read access across Robinhood accounts. Authentication/onboarding is an owner
action; nothing was connected or created during this work.
[Official overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/).

Documented equity capabilities include real-time quotes for up to 20 symbols,
tradability checks, positions/order history, order review, placement and cancellation.
An order review is a simulator, not an observed fill. Robinhood also distinguishes
cash-account settlement from limited-margin use of unsettled funds and says Agentic
margin borrowing is not enabled. These published features do not establish this
owner's account configuration, exact order schema, protection lifecycle, latency or
an available paper-trading environment.
[Official trading tools](https://robinhood.com/us/en/support/articles/trading-with-your-agent/).

The connector may exist in another app/session; it was not present among this
session's callable tools. No account/balance/position/order data was fetched.
Do not substitute unofficial password/session-cookie clients for missing access,
and do not paste secrets into chat. Use personal-account OAuth when the owner is awake.

## Shortest justified next steps

1. Keep tomorrow's frozen comparisons collecting; do not route these unchanged
   strategies to real money. Record no-trade outcomes and failures as evidence.
   The configured 20-session/trade thresholds permit review only, not promotion.
2. Develop a new, explicit hypothesis only after diagnosing entry/exit failure.
   Declare the stock universe, rule, costs and future evaluation period before
   testing it. News cannot rescue the existing record without point-in-time
   original receipt evidence and a separately declared experiment. No threshold,
   stop or holding-period search was performed tonight.
3. Prepare a separate real-time, no-order shadow observation once owner-authorized
   data access is available. Capture bar/quote event time, local receipt time,
   revision and decision time, spread, size and missed/late decisions. Compare
   observations against frozen signal logic. A documented real-time quote tool
   does not prove the end-to-end 1/2-second ORB assumptions are achievable.
4. With the official connector callable, inspect only the intended personal
   account and needed quote/tradability/schema information first. Verify account
   restrictions, funds actually available, order types/TIF and protection support.
   $5,000/$10,000 research cash is not a deposit or authorization to risk that amount.
5. Only after an economic candidate and execution contract justify it, specify a
   separate order-lifecycle trial: partial fills, cancel races, uncertain submission,
   restart deduplication, protective exits and close-of-session recovery. Use
   fixtures/review first and a supported paper environment where available.
   Actual broker actions require a separately authorized trial; a successful
   simulator review alone cannot certify placement or live fills.
6. A real-money pilot, if later justified, needs an explicit owner allocation and
   loss budget, observed control/alert behavior and new authorization. It is not
   enabled by more LLM reasoning or by meeting tonight's research deadline.

No upgrade was purchased, no orders were placed, and no automatic strategy
promotion was enabled. The new work accelerated a decision: current software is
ready to gather research, but current evidence does not justify a real-money pilot.

## Goal closeout — September 9, 00:05 Pacific

Final read-only cloud verification at 07:05:46 UTC confirmed both direct and
scheduled readiness READY, all 14 streams caught up within the intentional delay,
zero collector errors, and enabled collection/research/reference timers. The
unattended 07:02:36 UTC research run completed successfully. All 20 research pins,
16 dashboard files, original artifacts and parent result sections remained intact;
the $5,000/$10,000 arms correctly await their first completed September 9 session.
Orders remain disabled. [Captured evidence](verification/20260909/state-goal-closeout.json).

The eight new local diagnostic tests passed again at closeout, and `git diff
--check` passed. This local diagnostic was not deployed over the frozen release.
The pre-market assessment goal is complete; it does not mean that a profitable or
live-ready strategy has been achieved. Collection does not depend on the owner's
Mac staying awake. Future uptime and data delivery cannot be guaranteed by this
point-in-time health check.
