# LITE funded comparison — September 23, 2026

**Research-only decision: no stock trading rule is selected.** The user asked to
examine plausible approaches beyond the original dip idea. This new offline
comparison uses already-seen January 2–September 4 LITE price history. It is not
an unseen test, a test of discretionary news judgment, an Alpaca paper order, or
evidence that automated real-money trading should start.

The separate [protocol](../research/lite_funded_comparison_v1/PROTOCOL.md)
declares five entry cases: 10-, 15- and 30-minute opening dips, a confirmed
30-minute rebound, and a late-day decline. Every case has its **own $4,000 cash
ledger**, one LITE position at a time, at most $1,000 debit per entry, no margin
and no automatic loss stop. For comparison only, a completed close 3% above
entry triggers a sale at the next bar open, or an open position exits at the next
session open after a 10-session deadline. These are **proposed research assumptions**, 
not approved paper or live rules. Five- and twenty-session deadlines and 25-bp
per-side costs are reported as sensitivity, not optimized winners.

## Primary comparison: 10-session deadline, 10 bp each side

All dollars are hypothetical net marked P&L on the independent $4,000 ledger.
An unresolved position is marked using the September 4 regular-session close
less modeled exit cost; it is **not** a closed trade.

| Case | Candidate days | Entries | Closed | Still open | Net marked P&L | Worst daily portfolio drawdown | Worst closed-position adverse excursion |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dip after 10 min | 85 | 34 | 33 | 1 | +$570.31 | −9.16% | −22.87% |
| Dip after 15 min | 87 | 40 | 39 | 1 | +$1,163.92 | −5.80% | −25.52% |
| Dip after 30 min | 87 | 38 | 37 | 1 | +$949.95 | −4.94% | −24.47% |
| Two rising closes after dip | 12 | 10 | 10 | 0 | +$350.14 | −2.32% | −14.45% |
| Late-day decline | 59 | 32 | 31 | 1 | +$1,070.51 | −5.94% | −22.28% |

The $1,000 ticket LITE buy-and-hold control marked **+$1,313.46** and SPY
buy-and-hold **+$120.20**; cash marked $0. The single-name LITE control
outperformed every timed case in this period. A separate daily mark calculation
put its worst $4,000-ledger drawdown at **−20.51%**, versus **−2.30%** for the
SPY control, so the timed cases did reduce observed drawdown in this sample.
This does not make buy-and-hold or any timed case a recommended trade: exposure
and turnover differ, and both controls remain open at the cutoff. The selected
LITE sample rose strongly, and every LITE strategy benefited from that trend.
The timing rules cannot be credited with a repeatable advantage on these results.

Adverse outcomes matter despite the positive totals: the 10-, 15-, 30-minute
and late-day cases had 5, 2, 4 and 2 losing closed trades, respectively. Their
worst closed-trade P&L was approximately −$160, −$111, −$156 and −$144 on
the roughly $1,000 ticket. Positions in the first three cases reached modeled
adverse excursions beyond 22%. The rebound case's 10 closed trades were all
positive here, but it generated only 12 candidate days and is particularly
sensitive to feed differences. It cannot establish a win rate for future trades.

The five- and twenty-session deadline checks remain in [the full result JSON](lite-funded-comparison-20260923-verified/results.json).
Changing the deadline changes which signals can be funded, so P&L cannot be
interpreted as the isolated effect of waiting longer. Likewise, 25-bp cost cases
can take different trade paths; higher-cost P&L is not a same-trade comparison.

## Data and execution gates

The historical simulation uses pinned **raw consolidated SIP five-minute bars**.
Alpaca Basic provides free real-time **IEX-only** stock data; historical SIP is
available only after at least a 15-minute delay without a subscription.
On the 118 days where the older adjusted IEX snapshot has a complete session and
the raw SIP session is also complete, the simple entry decisions differed:

| Case | IEX signal days | SIP signal days | Disagreeing days |
|---|---:|---:|---:|
| Dip 10 min | 61 | 62 | 5 |
| Dip 15 min | 62 | 64 | 4 |
| Dip 30 min | 56 | 60 | 4 |
| Rebound 30 min | 5 | 8 | 7 |
| Late-day decline | 46 | 44 | 2 |

This overlap check is a **signal-only diagnostic**, not a matched execution
backtest: IEX history is adjusted and incomplete on 52 of 170 calendar sessions,
while SIP is raw and complete here. Still, the disagreement prevents treating
the free live feed as a faithful drop-in for the SIP results, especially for
the rebound rule. Spending $99/month would buy consolidated live market data,
but should wait for a specific research or operational need; it would not
repair selection bias, absent historical news or missing fill evidence.

The model buys and sells at a later five-minute **bar open** plus 10 or 25 bp
per side. Those opens are neither verified asks/bids nor actual fills. It lacks
quote age, spread, partial fills, order queue, latency, auction effects, halts,
broker rejects, taxes and corporate-action-adjusted multi-day accounting.
Historical article metadata lacks original text and receipt times, so no news
filter or sentiment advantage was tested. The user's $800/$810–820 example
levels were not treated as live instructions or fitted to past lows.

The [Alpaca paper documentation](https://docs.alpaca.markets/us/docs/paper-trading)
says paper fills differ from live execution and do not account for several live
frictions. Its [market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
describes the free IEX/live versus delayed SIP distinction. Neither the existing
$7,500 paper account nor the active DigitalOcean server is a running stock-order
strategy.

## Verification and next decision

The new five focused tests passed with bytecode writing disabled. A separate
Decimal replay checked every trade's debit, proceeds, quantity cap, chronology,
nonnegative cash and all 30 scenario terminal ledgers. Source hashes were
checked against the pinned SIP manifest. This verifies internal accounting, not
price executability or economic edge. The earlier exploratory output remains
preserved; [the verified result](lite-funded-comparison-20260923-verified/results.json)
is the one summarized here. Frozen experiments were not changed.

The next useful step is **not a count of arbitrary paper days**. Choose a
specific paper-only rule and resolve the user's manual-loss review and final
holding deadline, then test whether its decision-time data, executable quotes,
paper orders and account reconciliation work. The simple price-only comparison
does not justify choosing the historical highest-P&L arm. A prospective,
genuinely unseen evaluation is required before claiming a repeatable edge.
