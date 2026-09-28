# Our trading learning notebook

> **September 22, 2026 orientation:** See the [current project handoff](output/PROJECT_HANDOFF_20260922.md) for all experiments, updated broker/cloud status, LITE opening-dip evidence, and the Claude review prompt. The dated material below retains its original scope; it is not a current status report for every project track. Frozen strategies and historical evidence are unchanged.


Last updated: September 8, 2026.

This is the plain-language companion to our MNQ experiment. We will update it as
we do new work in this project. It is a project file, not an automatic background
service. Examples labeled **made up** are lessons, not real trading results.

## Where we are today

We have built a practice measuring machine. We have not yet fed it real MNQ data.
So we do **not** know our signal success rate, actual profit, or worst account loss.
The existing stock/ETF data cannot answer the MNQ question.

Think of testing a car: first we check that the speedometer and brakes work in
the workshop. Then we test the car on a track. A good workshop test does not mean
the car has already won a race.

Our program can now find the proposed chart pattern, check the quoted entry,
calculate risk, skip trades that do not fit, simulate exits and keep a money
ledger. The workshop tests use invented prices on purpose.

## Lesson 1: What are we trying to find out?

We are asking three questions:

1. **Does it fit?** Can one MNQ contract use the setup's proper stop without
   exceeding our planned loss budget?
2. **Does anything remain after costs?** The broker and the spread take money
   from the result, even when our direction is right.
3. **Can the account survive the rough parts?** Several losses, gaps or a broken
   data feed matter more than a screenshot of one winner.

MNQ is a small Nasdaq-100 futures contract. Small does not mean harmless. Its
profit or loss changes by $2 when the index moves one point, for one contract.
The smallest price step, called a **tick**, is 0.25 points and is worth $0.50.
Four ticks = one point = $2. [CME specifications](https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.contractSpecs.html)

## Lesson 2: The jar of money

Our pretend starting jar contains $5,000. Our initial proposed per-trade budget is
0.25% of that, or **$12.50**. That is the planned loss if the stop works as modeled,
not the amount we pay to buy a futures contract and not a guaranteed maximum loss.

**Margin** is the broker's deposit requirement to let you hold a contract. A low
margin requirement does not mean a trade is low risk. It is like a rental-car
deposit: it does not tell you how expensive an accident could be.

A **stop** is the price where our reason for being in the trade is no longer good.
It is our planned exit alarm. Prices can jump past that alarm, so the actual exit
can be worse. Our program models the next available quote instead of pretending
we always get the alarm price.

We do not move a stop closer merely because we want a trade to fit the jar.
That would change the strategy. We skip it and count the skip.

## Lesson 3: Buying and selling have different prices

At a market stall, the seller might ask $10.25 for an item, while someone will
only buy it back for $10.00. Buying and immediately selling loses $0.25.

Those two prices are **ask** (what we pay to buy) and **bid** (what we get to sell).
Their difference is the **spread**. A chart's last-traded price is neither a
promise to sell to us nor a promise to buy from us.

That is why we need historical trades **and** bid/ask quotes. A one-minute candle
is a summary; it cannot always tell us which price came first or what we could
have received at the exact moment we acted.

**Slippage** means getting a worse price while our action travels to the market.
We test several extra slippage amounts rather than assume instant perfect fills.

## Lesson 4: A made-up trade, in dollars

Imagine the quoted buy price is 25,000.00 and the setup's stop is 24,996.00.

- Distance: 4 points = 16 ticks.
- Price loss for one MNQ: 16 × $0.50 = $8.
- Suppose entry plus exit fees total $2. This is an example, not a verified fee.
- With no extra slippage, planned loss = **$10**, which fits $12.50.
- With one extra tick of slippage on entry and one on exit, add $1: **$11**.

Now imagine the setup needs a 12.5-point stop (50 ticks). Price risk alone is
**$25**. It does not fit our $12.50 budget, even before fees. This is what we
learned from the second Reddit post. Starting with one contract and later adding
more contracts is a different position-size policy.

With a $2 fee assumption and no extra slippage, the maximum allowable distance
from the quoted entry to the stop is **21 ticks / 5.25 points**. With one tick of
extra slippage each way, it is **19 ticks / 4.75 points**. These are ceilings,
not instructions to place stops at those distances.

## Lesson 5: What is our setup?

**VWAP** is an average price where busy prices get more votes than quiet prices.
It resets at 09:30 New York time in this experiment.

The bands measure how spread out the prices have been around that average. Being
far from the average does not guarantee that price will come back.

Our proposed long setup is: price reaches the prior day's low while unusually
far below VWAP, then the next completed minute closes above the setup minute's
high. A short mirrors this at the previous day's high. We aim toward the VWAP
recorded when confirmation happens, with the stop beyond the two-minute extreme.

**Long** means we benefit if price rises. **Short** means we benefit if it falls.
The program waits for the confirmation minute to finish before planning an entry.
It must not peek at later prices to make an earlier decision look clever.

The exact definitions live in
[the protocol](research/mnq_feasibility_v1/PROTOCOL.md). We write them down before
looking at the market results so we can tell whether an idea worked honestly.

## Lesson 6: Count the misses too

Imagine we find 100 patterns. Only 60 have quotes good enough to measure, and 12
of those fit our risk budget. **Made-up example:**

- 12 / 100 = 12% of all patterns are known to fit.
- 12 / 60 = 20% of measurable patterns fit.
- The remaining 40 patterns have unknown execution quality.

We report both percentages and the unknowns. Hiding the 40 would make the data
look better than it is. A budget-fit rate is also not a winning-trade rate.
Even a trade that fits can lose.

## Lesson 7: A pause is a smoke alarm

Our proposed daily pause begins at a 0.5% loss from that day's starting equity:
initially **$25**. Our account review pause begins after a 5% fall from the
highest observed account value: initially **$250**.

The high-water mark works like a line marking the highest water level in a jar.
If the account grows to $5,200, a 5% decline from there is $260. The review line
would be $4,940. It is not always fixed at $4,750.

We count the estimated value of open trades, not just trades already closed.
The program requests an exit when a loss pause triggers and blocks new entries.
An exit takes time, so these alarms cannot promise that losses stop exactly there.
The account review pause remains latched for the rest of the test.

We also stop trusting the full result if the quote feed goes missing while we
have a position. Unknown prices are not safely assumed to stay the same.

## Lesson 8: Why better data is the next useful purchase

An indicator is like a calculator. Data is what we type into it. An expensive
calculator cannot repair wrong or missing numbers.

For this experiment, the suggested starting source is **Databento historical
MNQ trades and top-of-book quotes**, bought in a small, quoted batch. We do not
need to subscribe to everything or buy an indicator. Keep research expenses
separate from the $5,000 simulated trading jar and track them as project costs.

The request plan and account steps are in
[DATA_CONTRACT.md](research/mnq_feasibility_v1/DATA_CONTRACT.md). The exact dollar
quote and any signup credits must be checked in the user's account. No purchase
has been made. A vendor importer still needs validation against the actual export.

## Lesson 9: What would count as progress toward real money?

First: our calculations match hand-worked examples and the money ledger balances.
Next: actual MNQ data passes quality checks and we measure all three questions.
Then: we test separately on data we did not use to change the rules, and compare
the simulated fills with a paper broker's fills and positions.

More money, a bigger model, or a paid indicator cannot promise a profitable
algorithm. We can move efficiently through the checks, but cannot truthfully
promise when the evidence will support using real money.

## Lesson 10: Checking the price before buying the data

An API key is like a private door key. Our program reads `MNQ_RESEARCH_KEY`
from the local `.env` file and sends it only to Databento to prove access.
We do not print it, copy it into reports, or put it into Git.

On September 8, 2026, that access check worked. We then asked the free pricing
service what our small data sample would cost. This is like asking a shop for
a price before checking out. No market data was downloaded or purchased.

The estimate is **about $11.07** for one contract, **MNQU6**, covering five
09:30-16:00 New York sessions from August 31 through September 4, plus contract
definitions. August 31 gives the strategy its previous-day warmup information.
The definitions describe which contract we are studying; they still need to be
downloaded and checked. The quote does not prove our trading idea works.

The earlier billing screenshot showed $125 of credits. If those credits remain
available and apply to this purchase, they should cover the estimated usage.
We have not rechecked that balance. A cost estimate is not a guaranteed final bill.

We use the exact contract symbol through the API because the website's Select
button picked the whole MNQ family. The saved estimate and exact request details
are in [databento-quote-20260908.json](research/mnq_feasibility_v1/runs/databento-quote-20260908.json).
The next step is a small approved download, followed by data checks and an importer.

## Lesson 11: Our data arrived — what did we actually prove?

After you approved the purchase, the price check stayed below $12. Databento's
completed jobs report **about $11.07 in data usage**. That does not tell us whether
credits paid for it or whether money reached your card; we have not checked the
final billing settlement.

We downloaded **28 files**, about **1.56 GB**, and checked every file's digital
fingerprint, called a **SHA256 checksum**, against Databento's list. Think of this
as checking that all the pages in a delivered book arrived unchanged.

We also opened and scanned the data. It contains **82,515,039 market-data records**
across five days, plus five contract definitions. Records include order-book
changes and trades. The counts match Databento's totals, and every one of the
390 trading minutes in each day contains trades. The contract definitions confirm
that one MNQU6 tick is 0.25 index points, worth **50 cents** per contract.

There is a small timing detail we must keep: the exchange's event clock and the
provider's arrival clock differ. We found 26 records outside the event-time
window even though their arrival time is inside our request. The importer must
handle that openly. We kept the original files unchanged.

This proves the download arrived intact and passed the checks we ran. It does
not prove the exchange feed contains every event, or that our trading idea earns
money. Next comes translating the files into our simulator, checking that
translation, and then measuring the strategy. We have not placed any trades.

See the [download receipt](research/mnq_feasibility_v1/runs/DATABENTO_DOWNLOAD_RECEIPT.md)
for the exact scope, record counts, and remaining limits.

## Lesson 12: Our first real-data test found no setups

We translated the files into **3,536,838 eligible trade records** and
**78,978,175 completed-event quote records**. A single exchange event can create
several data messages. We wait for its completion flag before considering its
quote, like waiting for someone to finish a sentence before interpreting it.
We preserved source order and recorded the 26 excluded time-boundary records.

Every minute's price bar, average price (VWAP), and price variation matched a
separate calculation. We checked the faster replay against the original engine
using both carefully constructed and randomized examples before running the data.
The original strategy, stop rules, and risk amounts stayed unchanged.

**Result: zero complete qualifying setups from September 1 through September 4.**
August 31 supplied the previous day's information. A separate condition check
also found zero: none of the eligible setup-minute closes exceeded the required
three-standard-deviation band during the entry window.

This means **no simulated trades**, not a successful money-making strategy.
The percentage of signals that fit $12.50 is **unknown**, because there were no
signals to measure. Likewise, $0 trading profit and $0 observed drawdown do not
tell us how profitable or risky an actual trade would be. The $11.07 history
expense remains a research expense.

The next useful experiment is more dates under the same rules, chosen before
opening their trading outcomes. We can ask the free API for the price first.
Any further data purchase needs its own approval. We will not weaken a rule just
to make the computer produce trades, and we still need verified broker fees
before calling any cost assumption realistic for your account.

See [the first real-data report](research/mnq_feasibility_v1/runs/pilot-01/REPORT.md)
and its [separate signal check](research/mnq_feasibility_v1/runs/pilot-01/independent-signal-check.json).

## Lesson 13: Buying data does not buy certainty

You asked whether another $56 of history could give us a profitability percentage
that lets us start using real money quickly. **No purchase can prove that.**
The history helps us investigate; the answer can be positive, negative, or still
unknown. Twenty days of prices can still contain very few qualifying trades.

Winning often is different from earning money. Imagine winning $8 six times and
losing $15 four times. You won 60% of the time, but collected $48 and lost $60:
you are down $12 before fees. We care about how much remains after both wins,
losses, and costs, and how uncertain that estimate is.

Our current sample contains no complete setups, so it gives us no measured win
rate. The next question is whether the strict setup occurs often enough to test.
I obtained a cheaper first-stage quote: **about $20.63 for trade-only data and
definitions across the same 20 August sessions**, compared with **$54.96** for
all MBP-1 data. No additional purchase was made during this comparison.

Trade-only data can locate signals using our exact rules. We would then need
quotes for every signal day to test the prices we could trade at. That second
stage costs extra; the combined cost is not guaranteed to be cheaper if many
days have signals. We must keep the combined purchase within the approved budget.

Before considering live money, we need results on separate unexamined periods,
real broker costs and sizing, and forward paper trading that behaves correctly.
There is no magic win-rate percentage or number of trades that makes future
profits certain. Finding that an idea is too rare, too costly, or too large for
our account is also useful progress.

The [research decision note](research/mnq_feasibility_v1/RESEARCH_DECISION.md)
explains the proposed stages and evidence needed in more detail.

## Lesson 14: Faster research can tell us to stop

We finished the extra August history batch for **$20.63 of data usage**. You
raised the website's monthly limit to $75, but we kept our separate $56 research
budget. We did not spend the rest just because it was available.

Think of the strategy as a door with three locks. The price must be unusually
far from its average, touch a level from yesterday, and then reverse in our
specified way. All the locks must open together before there is a trade.
In 19 new test days there were **zero complete setups**. Only one candidate
minute passed the unusual-price test; it failed the other two locks. A separate
calculation checked the answer. The earlier four test days and an extra free
check of the day connecting the two datasets also had zero setups: 24 distinct
test sessions altogether, not 24 trades.

This does not mean a 0% win rate. It means **we have no trades from which to
calculate a win rate**. We also cannot tell whether one contract fits our
$12.50 risk budget without an actual setup and executable prices. We stopped
further purchases for this version. Its old rules remain unchanged so the result
stays honest. A new idea must get its own written rules and fresh evaluation.

We also built a receipt checker for paper trading. One receipt comes from our
simulator; another must come from the real broker's pretend-money account.
It compares entries, exits, fees, positions and the cash left over. Today the
broker receipt is missing, so it correctly says **not ready**. Invented receipts
help test the checker but do not prove that a strategy earns money.

The proposed small live experiment would use no more than one MNQ, up to
$12.50 planned risk per trade, a $25 daily loss trigger and a $50 total loss
allowance that winning trades do not refill. Those are **proposals for later
approval**, not money we have permission to trade now. A bad fill or fast price
move can exceed a trigger; the numbers are not a guarantee of maximum loss.
The budget calculator is offline and cannot place trades or enforce a broker
stop. Actual paper integration and evidence still have to come first.

Read the [current decision](research/mnq_live_trial_v1/READINESS.md) for what is
finished and what still requires data, a broker account, or your approval.

## Lesson 15: Connecting is different from trading

On September 10, 2026 (UTC), Webull's sandbox accepted our saved credentials
and returned five test accounts. The check placed **zero orders**. The sanitized
receipt is in `outputs/paper/webull_sandbox_connection.json`.

An environment variable is a labeled box. Your boxes were named
`PAPER_TRADING_APP_KEY` and `PAPER_TRADING_APP_SECRET`. Earlier checks looked
for boxes with `API` instead of `APP` in the names. The credentials were there;
the check was looking under the wrong labels. The working checker accepts both
naming styles and rejects conflicting values. We did not change your `.env`.
The first network attempt also failed at DNS inside the restricted command
environment; the approved network-enabled check succeeded. A cloud-looking
hostname alone did not establish that we had a different copy of your files.

Think of this result as successfully opening the practice room. It does not
mean we have practiced yet, that MNQ is enabled in the right account, or that
our strategy makes money. We still need to verify the futures account and data
access, then compare paper execution with our simulator. Live readiness is
unchanged by this authentication check.

To repeat the connection check, run from the project folder:

```sh
outputs/tmp/webull-check-venv/bin/python scripts/check_webull_sandbox.py
```

This command requires network access and the existing isolated Python runtime
(Webull SDK 3.0.0 and python-dotenv). It allows only the sandbox's configuration
and account-list GET requests, verifies TLS, blocks redirects, and prints no
credentials or account identifiers. The endpoint and account-list check follow
[Webull's official SDK guide](https://developer.webull.com/apis/docs/sdk/).

## Lesson 16: A practice room can have only one practice instrument

We reached Webull's futures practice account and confirmed it had no positions
or working orders when checked. Its contract directory recognizes September
2026 MNQ (`MNQU6`). But asking the sandbox for MNQ prices returned this message:
`only these symbols are supported:[mesmain]`.

Think of it like a driving game that lists many cars but only lets this test
mode practice with one car. A list entry does not mean the whole practice
experience is available. `MESmain` follows a different index from MNQ, so its
results cannot answer our MNQ question.

We have not shown that paying would remove this restriction. We saved the
evidence and a support question instead of buying something on a guess. There
were no paper orders and no real-money orders. The existing comparison tool
correctly says it still needs actual broker receipts and matching simulator
receipts. An empty account is not a successful strategy test.

The [September 10 readiness report](research/webull_sandbox_v1/READINESS.md)
shows what worked, what failed, and the exact next dependency. A follow-up is
scheduled for 06:15 Pacific on September 10 to check for changes before the
06:30 cash-market open. It cannot automatically approve or start trading.

## Tiny glossary

| Word | Everyday meaning |
|---|---|
| Signal | A pattern that meets our written entry conditions |
| Execution | The price and timing of getting into or out of a trade |
| Fees | Charges for the transaction, separate from price movement |
| Round trip | One entry plus its exit |
| Net P&L | Profit or loss after the costs included in the calculation |
| Drawdown | A fall from an earlier account high |
| Backtest | Replaying old market data using fixed rules |
| Paper trading | Practicing with pretend money and a simulated broker |
| Synthetic fixture | Invented data that tests our program, not our strategy's profitability |
| Edge | Positive expected results after costs; a high win rate alone is not enough |
| Overfitting | Changing rules to match the past so closely that they may fail on new data |

## Questions we will answer with real data

- How many signals did we find and how many were measurable?
- What were the actual entry-to-stop distances?
- How many fit $12.50, and why were others rejected?
- Did costlier assumptions erase the result or change which trades entered?
- How large were the losses, and when did the pause rules trigger?
- Which facts are measured, which are assumptions, and which remain unknown?

## September 10: our program reached the IBKR practice account

Think of the API as a telephone between our program and the broker. Today,
the call connected. The broker confirmed the correct practice account and
the exact September MNQ contract. IBKR uses the running Trader Workstation
app for this connection, so we did not need another secret API key.

The next question is whether we can hear actual prices. IBKR confirmed
delayed-data mode in the second check, but no prices arrived during its
30-second observation. That means the telephone connection works, but we
have not yet verified the price feed. We have not tested buying or selling
with pretend money, and this does not tell us whether the strategy earns money.

We installed the official SDK and checked five software safety cases. The
checker can ask questions but blocks order requests. No trades were sent
and no data subscriptions were purchased. See the
[IBKR connection report](research/ibkr_paper_v1/READINESS.md) for measured results.

The follow-up still received no MNQ prices. We found that IBKR has a separate
permission form for letting a program receive market data. Enabling the socket
connection does not complete that form. We need to inspect its actual status
after Client Portal login; it is a possible cause, not a proven diagnosis yet.
The checker now distinguishes hearing a price, hearing both a buying and a
selling price, and hearing real-time prices. Those are three different things.

## September 13: we found an unfinished permission step

We checked the real account settings. IBKR says the API data permission has
not been certified, and there is no CME market-data subscription. The permission
form is now open for you to read and sign if you agree. It is a contract, so
this needs your informed decision. Completing it is one step; we still need
to verify subscription eligibility, paper data sharing and actual quotes.

The data agreement also limits sharing data with others. Our checker now keeps
quote numbers in its local file and prints only health-check results. We must
check the permitted use before sending broker data to a hosted dashboard or LLM.

You then signed the API form, and IBKR confirmed that API data access is enabled.
That finishes the permission step. The next question is your market-data
subscriber classification. “IBKR Pro” is a service-plan name; it does not by
itself mean you are a professional market-data subscriber. That classification
depends on your actual work, registrations and use of the data.
# September 13: the connection works, but the price feed is still unfinished

Think of TWS as a telephone. We have confirmed that our program can call the
correct practice account and ask about the correct MNQ contract. That does not
mean prices are arriving: today's short check still received no prices.

The API acknowledgement and Non-Professional classification are now saved.
CME's basic price subscription is listed in this account at $1.55 per month.
IBKR separately requires $500 in account equity plus the subscription cost.
That $500 is money held in the account, not a $500 data fee. Subscription fees
reduce the balance over time. Sharing the live account's subscription with the
paper account is another setting, currently off. We have not bought the feed or
changed that setting. We must verify actual prices after setup; no paper trades
or real-money trades have been placed by this check.

## September 21 — the price connection works

Think of market data like a radio: we now receive the broadcast in our practice account. Our 20-second check received real-time buying and selling quotes for December MNQ. September MNQ has expired, so the diagnostic now explicitly selects December. This does not mean the strategy makes money or that orders work. Next we must test practice orders and compare their results with our simulation. No real or practice orders were placed by this check.

## September 21 — moving the practice desk off the laptop

A cloud server is a rented computer that keeps running when your Mac is off. We installed IB Gateway there and a separate collector that can record December MNQ during the strategy's regular session. It still needs your paper login; a running program does not mean it has access to prices. IBKR may ask you to sign in again each week.

Our report schedule is 15 minutes before the stock-market regular open and 15 minutes after its close, normally 6:15 a.m. and 1:15 p.m. Pacific. Futures have longer hours, but trading overnight would be a different experiment. Holidays and early closes come from a checked calendar.

Email delivery is still being connected: the existing DigitalOcean server blocks Gmail SMTP ports, so a Gmail app password alone will not work there. We are preparing an HTTPS sender. No automated email delivery is claimed until a message arrives.

Twenty complete practice sessions is our proposed first review, not a graduation date. We need actual qualifying trades, realistic costs, reliable stops, and evidence that the results are more than luck. The earlier 24 evaluated MNQ sessions had zero setups, so waiting a fixed number of days cannot establish profitability. Forced test trades do not count as strategy evidence.

### September 21 — what the cloud setup has actually proved

- The cloud is a rented computer. IB Gateway and the data recorder now run there;
  closing the laptop does not stop those server processes.
- We verified real-time December MNQ trades and quotes. This is like checking that
  our camera is recording. It does not mean the robot has started trading.
- Two storage problems were found and repaired under the real stream. We keep the
  interruptions in the evidence instead of pretending today was a complete day.
- The recorder now connects before the opening bell but only saves session ticks
  inside the research window. A coverage check looks for missing minutes, long
  quote gaps and bad timestamps. Passing that check still does not prove profit.
- The broker's daily restart setting is saved. We must see an overnight recovery
  work; occasional broker sign-in can still be necessary.
- Email scheduling is installed, but no email has been delivered yet. Our cloud
  provider blocks Gmail SMTP, so the earlier app-password plan cannot work on this
  server. An approved HTTPS email provider and a received test are still needed.
- Automated broker-paper orders, actual fill costs and the simulation comparison
  are separate unfinished steps. We have not enabled real-money orders.

### September 21 — why the broker API is still read-only

The cloud account is verified as a paper account. Its read-only switch lets our
program look at prices and account records, but prevents order requests. IBKR also
rejected a harmless margin/fee preview through that same order interface. We have
not changed the switch yet: expanding that permission needs your confirmation.

We built the beginnings of the paper execution system: it writes a trade plan to
its notebook before sending, remembers uncertain attempts after a restart, and
checks that fills belong to our account and order. Missing fees stay unknown.
The streaming indicator arithmetic matches the old engine on an invented test
story. Thirty-one software tests passed on both computers. None of that means an
actual broker paper trade has been executed or that the strategy makes money.

A native bracket uses a linked entry, profit limit and protective stop. That is a
different execution method from the original simulation, so it has a separate
candidate protocol. The matching simulator is now implemented as a candidate;
we still need actual broker order/recovery tests before enabling automatic entries.

### September 21 — a simulation is a measuring ruler

The new simulator describes what we expect a linked entry, target and stop to do.
It will be our ruler for comparing actual paper fills. It does not predict the
exchange queue or guarantee that the broker fills an order at our chosen price.
For example, a fast price jump can make a stop lose more than its planned budget.
If fees are missing, the program says profit after fees is unknown.

We now have 41 passing software tests on the laptop and the cloud server. Loss
pauses also survive a program restart, even if prices recover afterward. The
program that sends broker orders and acts on these pauses is still unfinished.
At 10:30 AM Pacific the server was recording real-time prices with no deployment
restart, but automatic paper orders and email delivery were still disabled.

### September 21 — checking the recorder and broker notebook

The adapter translated 38,902 real recorded events from a five-minute interval
without changing their order or rounding trade sizes. IBKR leaves the exchange
name blank on these trade messages; we preserve that blank and rely on the
separately verified CME contract. Passing five minutes does not prove a whole
session is complete or that our prices equal another data provider's prices.

A fresh read-only broker check at 10:38 AM Pacific showed no positions or open
orders. We now check the age and completion of those account queries before
using them. An empty recent-history result cannot prove an uncertain old order
never filled, so it cannot give the robot permission to send that order again.
There are now 53 passing tests locally and on the server. Real order execution
tests still await the paper API permission change; no orders were sent here.

### September 21 — the server now has an after-school check

After the market session ends, a separate server job checks the day's recording.
It compares the strategy's rules with that day only when the recording is complete
and the immediately previous market session provides valid warmup data. Friday
can be Monday's previous session, but an incomplete Friday cannot be replaced with
Thursday just to make the test pass.

“Unknown because data is missing” and “checked everything and found zero signals”
are different report results. The program now preserves that distinction. Its
saved results include checksums identifying the code and source observations.
This job has no network connection and cannot send broker orders.

Sixty tests now pass on both computers. The new server timer successfully read the
recording database and is waiting for the session to end. Its first real completed
session calculation, broker order tests and delivered email are still unverified.

### September 21 — our report mailbox works

The server now sends reports using Resend over HTTPS. We checked your Gmail inbox
and found both the first test and a test sent by the actual scheduled service.
This is like checking that the letter arrived, instead of only watching someone
drop it in the mailbox. Your Gmail app password stayed on your computer.

Reports are scheduled 15 minutes before and after our research session: usually
6:15 AM and 1:15 PM Pacific on trading days. The cloud server does this; your Mac
does not have to be open. We still need to observe the first scheduled deliveries
and overnight broker restart. IBKR may occasionally ask you to log in again.

### September 21 — a rehearsal is not a filled trade

You approved paper API requests. The broker gave a pretend-order estimate of
$0.61 in fees for one order and about $4,731 in initial margin. Margin is money
the broker requires as security; it is not the most you can lose. That estimate
would use most of our $5,000 research allocation. It is not permission to go live.

We also sent three order instructions marked “do not transmit” and received
cancellation confirmations with no fills. IBKR does not show those untransmitted
instructions through its open-order API. Therefore we cannot claim we have tested
the linked entry, target and protective stop. The lesson: each test proves only
what we actually observed. Automatic paper entries remain disabled while those
checks and the execution supervisor are unfinished.

### September 21 — the first actual simulated execution test

We have now gone beyond “do not transmit.” A real order reached IBKR's simulated
broker. The first test verified a bracket and cancelled it without a fill. The
second bought one simulated MNQ contract, verified the protective stop, cancelled
the native exits, confirmed those cancellations, and sold the one remaining
contract. The broker reported $0.61 per fill, or $1.22 for the round trip. The
account ended with zero exposure and no working orders.

This was a deliberately forced equipment test. It is excluded from strategy
profit, win rate and qualifying-trade counts. We have not yet observed a natural
stop fill or target fill in this new setup. Paper fills also do not prove that
real-money orders would receive the same prices.

The automatic supervisor is now implemented. It keeps the $5,000 research
allocation, one-contract maximum, at most two attempts per day, $12.50 planned
trade risk, $25 daily loss pause and 5% high-water drawdown pause. Smaller account
equity can tighten those limits. Stops can slip, so these are planned limits,
not guaranteed maximum losses. The program reserves $4 for round-trip fees and
pauses if actual recorded fees exceed that reserve.

Think of “armed” as turning on the robot, and “eligible” as giving it permission
for one particular action. The robot must still see complete warmup data, a real
strategy signal, fresh prices, affordable margin and acceptable risk. Monday's
mid-session recording is incomplete. If Tuesday is captured completely, Wednesday
is the earliest normal session that could use it as warmup. A session with no
qualifying setup should produce no trade.

If the program crashes with an uncertain order, it keeps the journal and blocks
new entries instead of guessing and sending the same trade again. Existing broker
protection must be inspected during recovery. This deliberate pause is different
from an unfinished order sender. Overnight authentication recovery and complete
sessions still need real observation; software tests cannot manufacture them.

The cloud supervisor is now enabled and armed. We deliberately terminated just
that new process while the account was flat and entries were blocked. The service
manager restarted it automatically, and it returned to the same warmup gate with
no strategy orders. That proves flat-state process recovery, not recovery of an
active position or renewal of the broker's login. All 87 current tests pass on
both computers. The first full prospective session still has to happen.

### September 22: the robot was awake, but its broker connection was unavailable

The cloud sent its morning email without needing the Mac. At 6:15 and 6:30 a.m.
Pacific it reported that the Gateway API was unavailable. That message means the
collector did not complete its connection handshake; it does not tell us whether
the password expired, the Gateway stopped, or another connection problem occurred.
There were no opening quotes, so today cannot be called a complete practice day.

Think of the cloud as a robot's body and the broker login as its visitor badge.
Keeping the body awake does not guarantee that the badge stays valid. IBKR normally
requires a weekly login after its Sunday reset and can invalidate a badge earlier.
We should plan that login outside the morning session, but cannot promise that an
unexpected interruption will never happen while you sleep.

We found that urgent connection alerts were limited to market hours. The local
fix watches overnight too, filters brief restarts, and reports a stable recovery.
91 tests passed locally. It is NOT installed on the cloud yet: server connections
timed out from the current mobile network, and the provider console needs login.
An alert is a warning light, not a repair. We still need to inspect and recover the
actual Gateway and observe a successful overnight restart before claiming that
recovery works. A separate outside monitor is needed to notice a whole-server
failure, because a stopped server cannot email about its own failure.
