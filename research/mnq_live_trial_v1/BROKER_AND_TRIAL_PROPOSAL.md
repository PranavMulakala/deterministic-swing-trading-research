# MNQ broker and limited-live-trial proposal

Prepared 2026-09-08 America/Los_Angeles. Status: **PROPOSED — NO LIVE AUTHORIZATION, NO BROKER ACCOUNT VERIFICATION**.

The fastest practical route is to investigate **Tradovate/NinjaTrader paper execution in parallel with historical research**, using the existing Python rules and a Mac-compatible API. This is provisional: retail API eligibility, recurring costs, and market-data permissions must be confirmed for the actual account before funding or subscribing specifically for this integration. Nothing in this document establishes a profitable strategy or permits a live order.

## What is verified, and what is missing

**Verified locally:** the frozen `../mnq_feasibility_v1/config.json` specifies $5,000 initial research equity, 0.25% planned trade risk, 0.5% daily loss pause, 5% high-water drawdown pause, one contract, and two entries per day. Broker fees remain illustrative in that configuration. This proposal does not edit those rules.

**Verified in official documentation:** the capabilities and public prices below. These are documentation observations, not successful account tests. Margin and entitlement terms can change and depend on the account.

**Missing:** chosen broker, approved futures permissions, current available account equity, real-time API data entitlement, actual all-in MNQ fees, account-specific margin, connected paper account, captured paper fills, and approval of any live trial. A Databento historical-data key does not establish any of these.

## Broker comparison for this project

| Area | IBKR Pro / TWS API | Tradovate / NinjaTrader |
|---|---|---|
| Python and Mac path | Official Python socket API connects to TWS or IB Gateway; current requirements include an opened, funded **IBKR Pro** account. [IBKR requirements](https://www.interactivebrokers.com/docs/tws-api/doc/notes-limitations/requirements) | Current official REST API supports custom applications. API credentials are issued by NinjaTrader; the default documented test host is the demo environment. [API setup](https://docs.ninjatrader.com/api/getting-started) |
| Paper environment | Official TWS API paper account is available after regular-account approval and funding. Simulated execution can differ from live. [Paper API](https://www.interactivebrokers.com/docs/tws-api/doc/notes-limitations/limitations/paper-trading) | NinjaTrader advertises unlimited platform simulation and a 14-day live-data trial. This does **not** establish retail API eligibility. [Platform pricing](https://ninjatrader.com/pricing/) |
| Retail API eligibility | Funded Pro account and suitable trading permissions; no claim that an unfunded demo is sufficient. | Published Tradovate support requirements are live equity **greater than $1,000**, CME Information License Agreement, and a paid API Access add-on. New developer documentation lists issued credentials but does not quote retail eligibility or price. Resolve these details in the chosen account before buying anything. [Tradovate requirements](https://tradovate.zendesk.com/hc/en-us/articles/4408927027987-How-Do-I-Get-Access-to-the-Tradovate-API), [current developer setup](https://docs.ninjatrader.com/api/getting-started) |
| Public MNQ margin snapshot | The retrieved US table lists **$4,609.81 intraday initial**, $2,961.83 intraday maintenance, and **$6,585.45 overnight initial**. $5,000 minus that intraday initial requirement leaves about $390.19 before costs. This is a narrow buffer, not an account-specific approval. [IBKR margins](https://www.interactivebrokers.com/en/trading/margin-futures-fops.php?ex=us&hm=us&ot=0&pm=0&rgt=0&rsk=1&rst=1) | NinjaTrader's table, labelled **as of 2026-08-31**, lists MNQ **$100 day** and **$4,647.32 initial**. It says intraday requirements can change without notice. Recheck applicability to the user's selected account, especially Tradovate-branded accounts. [NinjaTrader margins](https://ninjatrader.com/pricing/margins/) |
| Published broker commission | Lowest-volume MNQ rate is **$0.25 per contract per side**, plus applicable exchange/regulatory fees. It is not a $0.50 all-in round trip. [IBKR futures commissions](https://www.interactivebrokers.com/en/pricing/commissions-futures.php) | NinjaTrader Free plan advertises **$0.39 per micro contract per side**, plus exchange, clearing, and NFA fees. The monthly plan is $99; it is unnecessary to start this low-frequency experiment. The current all-in schedule did not expose an MNQ row in the retrieved page, so no all-in amount is claimed. [Plan pricing](https://ninjatrader.com/pricing/), [all-in schedule](https://ninjatrader.com/pricing/commissions/) |
| Real-time data | CME Real-Time L1 is publicly listed at **$1.55/month for qualifying non-professionals**, subject to eligibility and account permissions. Unsubscribed US futures paper data is delayed 10 minutes. Verify API access and paper sharing, not just a chart displaying prices. [Data pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php), [paper delays](https://www.interactivebrokers.com/en/trading/papertrader-delayed-data.php) | Funded platform plans advertise top-of-book data. The API uses a separate market-data token/socket; a token or platform quote does not prove the required API entitlement. Exact retail API/data recurring charges are **unverified**. [Platform pricing](https://ninjatrader.com/pricing/), [market-data authentication](https://docs.ninjatrader.com/market-data/authentication) |

**Recommendation/inference:** investigate Tradovate/NinjaTrader first because its documented intraday MNQ margin is more workable for $5,000 and its REST path avoids rebuilding the strategy in a Windows desktop environment. IBKR remains an alternative if the user already has a usable account or account-specific margin differs. A low broker margin does not reduce the dollars lost per point or make a trade fit our risk limit.

NinjaTrader Desktop/NinjaScript is a Windows path; Web runs on a Mac browser. Platform access and algorithm deployment are distinct. Buying a Windows environment or porting the strategy would add work that the existing Python/API path may avoid. [Platform comparison](https://ninjatrader.com/trading-platform/)

## Exact user setup steps

1. Identify any existing IBKR, Tradovate, or NinjaTrader account and whether futures/paper trading is approved. If none exists, start the selected broker's application personally and answer identity, experience, residency, and financial questions accurately. Do not put passwords, identity documents, or API secrets in chat.
2. Before funding for API eligibility, check the account's API Access screen or obtain official support confirmation of: eligibility for an individual using a personal Python algorithm; required deposit; current API add-on price; CME agreements; real-time **trade-by-trade and bid/ask API** entitlement and total monthly charge; simulation access and expiry; simultaneous UI/API limits. No message to support has been sent on the user's behalf.
3. Review that concrete recurring-cost quote. The previously approved $56 is a historical research purchase budget, not approval for a broker deposit, monthly subscriptions, or live losses.
4. Once the chosen account is eligible, enable its paper environment and establish the research's $5,000 paper equity or an explicit $5,000 virtual risk ledger if the broker simulator cannot represent it. Keep an immutable starting balance and never reset it to conceal losses.
5. Configure the **paper account only** for program access. Store credentials locally using the project's secret-handling process. Grant only the account/data/order permissions needed for paper execution; restrict the runner to the verified demo account/environment. A port or account-name prefix alone is insufficient proof.
6. Capture account identity, exact MNQ contract/expiry, market-data timestamps, margin and fee details, and a read-only reconciliation snapshot. Validate the raw feed against the frozen trade/VWAP calculation before permitting paper orders.
7. Exercise the paper runner and compare every order/fill to the simulation. Native broker protection and discrepancies must be understood before the final live proposal.

The current Tradovate support documentation describes an option allowing API orders with an external market-data source. This is **not** permission to bypass data licensing, and the present Databento purchase is historical only. Any external live feed needs its own verified entitlement and cost. [External-data order option](https://tradovate.zendesk.com/hc/en-us/articles/4403100181651-Do-I-Need-a-Market-Data-Subscription-Through-Tradovate-to-Perform-Trades)

## What paper execution must demonstrate

Run a deterministic signal engine against the exact recorded feed and send only its qualified decisions to the broker's paper environment. Persist event/receive/decision/submission/acknowledgment/fill timestamps, signal identifiers, contract IDs, order and execution IDs, sides, quantities, prices, fee provenance, rejection reasons, position snapshots, pause events, and configuration hashes. Include missed and rejected signals; do not select only winning fills.

Measure signal agreement first, then entry/exit price differences in ticks, latency distributions and extremes, costs, missed/partial/rejected fills, protective-order acknowledgment, cash/position agreement, and loss-budget consumption. Broker paper fills are simulated measurements, not exchange queue positions or evidence of live fill quality. IBKR specifically states top-of-book fill simulation and simulated stops/complex orders. [IBKR paper limitations](https://api.ibkr.com/en/trading/tws.php)

**A material modeling difference must be resolved:** the frozen protocol triggers stops and targets on the executable liquidation side and uses the first valid quote at least 100 ms later, with adverse slippage. A normal broker-native profit-taking **limit** order is a different exit mechanism. Broker-native stops may also use different triggers. Preserve the historical baseline and define a separate broker execution version; test and disclose the difference instead of claiming exact parity. See `../mnq_feasibility_v1/PROTOCOL.md`, especially its execution and broker-semantics limitations.

Tradovate advertises server-held brackets, and IBKR documents parent/child brackets. These support a protective design, but do not prove that our exact order is accepted, active, correctly linked, or guaranteed to fill at its stop. Verify actual parent/child status, cancellation/OCO behavior, restart recovery, and protection after a local disconnect in paper testing. [Tradovate bracket capability](https://info.tradovate.com/advanced-trading-technology), [IBKR bracket construction](https://www.interactivebrokers.com/docs/tws-api/doc/orders/place-order/adding-a-profit-taker-and-stop-loss)

Operational cases must include stale/invalid data, duplicate messages, unknown submission outcome, delayed/rejected protection, restart with an existing position, unavailable broker connection, a time exit, and reconciliation after cancellation. A failed or unknown submission is reconciled before retrying. Fault-injection trades used to exercise these cases are labelled engineering tests and excluded from strategy-performance evidence.

Current NinjaTrader documentation describes expiring tokens, session/connection limits, rate penalties and account risk parameters; the runner must handle these rather than assuming an always-connected API. IBKR likewise documents periodic reauthentication. [NinjaTrader authentication and limits](https://docs.ninjatrader.com/api/authentication), [IBKR reauthentication](https://www.interactivebrokers.com/docs/tws-api/doc/tws-settings/daily-weekly-reauthentication)

## Proposed limited-live budget — requires later explicit approval

This is a **separate, tighter trial overlay**, not a change to the frozen research. At $5,000 starting equity:

| Control | Proposed rule |
|---|---|
| Position | One verified outright MNQ contract at most; no adding to a position, no simultaneous strategies in the trial account/ledger. |
| Planned risk per entry | At most **min($12.50, 0.25% of start-day trial equity)** after expected round-trip fees and modeled slippage. Never move a structural stop closer just to fit. |
| Daily stop | At **min($25, 0.5% of start-day trial equity)** loss from the day start, including fees and executable marked open P&L: cancel entries, request flattening, reconcile, and latch the pause until review/next allowed session. |
| Entry count | At most two entries per day; rejected/uncertain/partial attempts require explicit state accounting so retries do not evade the intended limit. |
| Total experiment loss | **$50** proposed maximum loss budget, tracked as cumulative negative net realized trade results plus current unrealized loss and remaining exit-fee reserve. Winning trades do not replenish this allowance. Pause at the threshold and require a fresh review. |
| Existing drawdown pause | Preserve the frozen **5% high-water drawdown** review pause as an additional condition. The tighter trial controls normally act first. |
| Entry admission | New planned loss must also fit the remaining daily and total trial allowances. If even one contract does not fit, skip the trade. |
| Trial review boundary | Stop after the first **five completed round trips or five monitored sessions**, whichever occurs first. This is an operational review boundary, not a statistical proof threshold or an automatic extension. |
| Supervision | User/operator available during the trial window, independent broker UI access, and tested cancel/flatten/reconciliation procedure. No unattended first live trial. |
| Immediate failure pause | Unknown position, duplicate/excess exposure, stale data, or unacknowledged/rejected protection halts new entries immediately; use the tested recovery procedure without waiting for a monetary limit. |

The percentages, dollar overlays, and five-trade/session review boundary are **proposals for approval**, not universal quant standards. Live approval must name the broker/account, exact contract, execution version, approved dates/window, operating person, loss limits, costs, and evidence package. It expires at the stated review boundary and does not authorize automatic scaling or another strategy.

These are **loss-trigger budgets, not guaranteed maximum losses**. Market gaps, protection limits, execution delay, disconnection, or fees can overshoot them. One MNQ is $2 per index point and $0.50 per tick; a 10-point move alone is $20, before costs. [CME MNQ specifications](https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.html)

Research-data purchases and recurring platform/data costs should be shown separately from trading P&L and approved separately; they still count toward the user's total project spending.

## Completion and timing boundary

An [offline budget evaluator](TRIAL_BUDGET_EVALUATOR.md) now makes the proposed
limits and accounting reviewable with synthetic regression tests. Its policy
is explicitly `NOT_APPROVED`, with orders disabled. It checks supplied snapshots
only; it does not enforce limits at a broker or establish live readiness.

Work that can proceed now: historical screening, execution specification, offline reconciliation/failure tests, comparison report formats, and this source-backed broker proposal. These tasks can run concurrently.

Work requiring the user or external state: broker choice and application, truthful eligibility declarations, any deposit/subscription approval, real-time feed activation, paper account connection, observed future qualifying signals, and final live approval. Exact elapsed time depends on those dependencies. No calendar date or fixed small trade count turns a negative or uninformative strategy into a live candidate.

The final decision requires both sufficient historical/held-out strategy evidence under realistic costs **and** satisfactory paper execution evidence. Passing software tests or completing the paper checklist does not establish an edge. If the frozen setup remains too rare, unprofitable after costs, or incompatible with one-contract risk sizing, this version should not proceed to a live trial.
