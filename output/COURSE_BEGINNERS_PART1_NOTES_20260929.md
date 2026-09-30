# "Trading for Beginners Part 1": what he teaches, what's on screen, and what holds up

Built from the full audio transcript (30,000 words) and 293 screenshots taken every 30 seconds. Times like **[1:25]** point to the spot in the video.

**The course in one line:** a UK forex trader teaches a rule-based, check-once-a-day system. Find the trend, wait for a pullback, enter when price turns back, risk 1% per trade, and backtest before using real money. The video is free and ends with a pitch for a paid "30-day challenge". He also links his broker, Trade Nation, several times.

---

## 1. Money math and time [0:07–0:22]
**What he says:** take the income you want each month and divide it by a monthly return. For $500 a month:
- at 2% a month you need $25,000
- at 4% you need $12,500
- at 6% you need $8,333

He says the best traders make "2–6% a month".

**On screen:** a whiteboard with the three divisions.

**Honest take:** the formula is useful. The 2–6% figure is not realistic for most people.
- 2% a month compounds to about 27% a year. 6% a month is about 100% a year.
- Very few professional funds hold those numbers for years.
- A fairer yardstick is the stock market's long-run average of about 10% a year.

**Your goal of $1,000 a week (about $4,333 a month):**

| Monthly return | Account you'd need | What that return means |
|---|---|---|
| 6% | $72,000 | His best-case number |
| 2% | $217,000 | His low-end number |
| ~0.8% (10% a year) | ~$520,000 | The market's long-run average |

**His timeline:** 6 months learning, then 12 months on a demo account, so 18 months before real money. An hour a day, done consistently.

**Honest take:** this is the best advice in the video, and it's what our paper bots do. He also says at [1:35:37] that anyone promising "a set amount of pips per week or set amount of money per week is rubbish". That applies to "$1,000 weeks" too: income from trading comes in unevenly, never as a fixed weekly amount.

## 2. Reading candles [0:22–0:35]
**What he says:**
- Every candle has four prices: open, high, low and close.
- The **body** runs from the open to the close. The **wicks** show how far price went and then got pushed back.
- He calls it a tug of war between buyers and sellers.

**On screen:** a hand-drawn candle diagram, then his charts.

**The key idea:** a green candle with a long upper wick that closes near its open is "bearish" even though it's green. Buyers pushed price up, and sellers shoved it all the way back.

## 3. The six things he checks before a trade [0:35–0:56]
1. **Market condition:** is it trending up (higher highs and higher lows) or down? Only trade in that direction.
   - **On screen:** dollar/yen, a clear uptrend.
2. **Phase:** trends move in steps: a *run*, then a *pullback*, then another run. He enters on the pullback, never at the top of a run.
3. **Support and resistance:** "look left". A level where price turned before often matters again, and old resistance often becomes new support.
   - **On screen:** horizontal lines on past turning points.
   - **Also angular support and resistance:** a trend line drawn through the closes of the pullbacks.
4. **Price slowing down ("deceleration"):** the candles in the pullback get smaller, meaning the pullback is running out of steam.
   - **On screen [0:48]:** Aussie/New Zealand dollar.
5. **Candle patterns** only count at the right spot:
   - a **high-test candle** (shooting star), with a long top wick
   - a **low-test candle** (hammer), with a long bottom wick
   - a **doji**, where open equals close (indecision)
6. **Extras:**
   - **Fibonacci:** a 38.2% pullback is typical of a strong trend; 61.8% is a deeper one.
   - **Round numbers** like 1.1000, which he compares to stopping the petrol pump on a zero.

**His first example trade [0:54]:**
- Enter a sell order just below the shooting star's low.
- Stop loss above its high.
- Target at the previous lows.
- **Result:** it worked.

**Honest take:** the ideas are standard and reasonable. But he says himself that "all of these are in hindsight". Every line and pattern was picked after he already knew the outcome.

Stacking five subjective signs (he calls it "confluence") feels convincing but is hard to test honestly. Two people will draw different lines on the same chart. There is some academic evidence that currency orders cluster at round numbers, so that part isn't made up.

## 4. Order types [0:56–1:13]
**On screen:** a whiteboard list, then live examples on a chart.

| Order | Where it sits | What it does | Plain meaning |
|---|---|---|---|
| Buy limit | Below current price | Buys if price drops there | "Buy cheaper" |
| Sell limit | Above current price | Sells if price rises there | "Sell higher" |
| Buy stop | Above current price | Buys if price breaks up | "Buy the breakout" |
| Sell stop | Below current price | Sells if price breaks down | "Sell the breakdown" |
| Market | Now | Fills right away | "Get me in now" |

**Key lessons:**
- **A stop loss is a job, not an order type.** Any of the orders above can do that job. If you bought, your stop loss must be a *sell*, and since it sits below price it's a sell stop.
- **Always set them in this order: entry, then stop loss, then target.**
- **Don't use market orders for stop losses.**
- On his platform, the "order" button is for later and the "trade" button is for now.
- **Your order is an instruction, not a guarantee of price.**
  - Our breakout test showed what that means: **333 of 929 stops opened past the stop price** the next morning, so those losses were bigger than planned.
  - He mentions this ("nearest possible price") but underplays it.

## 5. Risk 1% per trade and size from the stop [1:13–1:18]
**His example:** a $10,000 account risks 1%, which is $100. The stop is 50 pips away, so $100 ÷ 50 = $2 per pip. A target 100 pips away then pays $200: "2 to 1".

**The same math for stocks:**

> shares = (1% of the account) ÷ (entry price − stop price)

For example, a $90,000 account risks $900. Buy at $100 with a stop at $95: $900 ÷ $5 = 180 shares, an $18,000 position. **The stop distance sets the size, not a gut feeling.**

**Small errors he makes:**
- He says "multiply by 0.001" to get 1%. It's 0.01.
- In the demo trade [2:09], the 249-pip stop allowed only $0.40 a pip. The platform's minimum was $0.50, so he actually risked about $125, or 1.25%. The broker's minimum size quietly broke his own 1% rule.

## 6. The made-up strategy, which is the part we can actually test [1:21–1:35]
**On which chart:** pick the timeframe you can check *at the same time every day*.
- Once a day means the daily chart, which he recommends for beginners.
- Two or three times a day means the 4-hour chart.
- Four or more times a day means the hourly chart.

**The rules, for a downtrend** (flip them for an uptrend):
1. The trend is down (lower lows) and price is in a pullback, ideally into old support that's now acting as resistance.
2. Wait for the **first "lower-low, lower-close" candle:** a day that *closes below the previous day's low*.
3. Place a **sell stop 2 pips below that candle's low.**
4. Put the **stop loss 2 pips above the pullback's highest high.**
5. Put the **target just before the lowest close of the previous run.**
6. After a trade, wait for price to break and close below the low before looking again.

**On screen:** four examples in a row.

| Example | Result | Risk-to-reward |
|---|---|---|
| 1 | Win | +3 to 1 |
| 2 | Loss | −1 |
| 3 | Win | +2.5 to 1 |

"Up $500" on $100 risks. He also explains how it *feels*: example 1 went halfway to the stop before it worked, and it took 6 days.

**The worked sheet example [1:44]:** Aussie dollar, entered Aug 16, 2022.
- Entry 0.7009.
- Stop about 0.7139 (he misreads it on air as 0.7135).
- Target 0.6739, hit Sept 6, 2022.
- About 130 pips of risk for 270 of reward, roughly **2 to 1, and three weeks in one trade.**

**Honest take:** at [1:50] he says outright that this is "not an actual strategy that I have any idea that will produce a profit". It's a teaching example picked in hindsight. But unlike the "confluence" stuff, **the entry, stop and target are exact rules**, so a computer can test them without drawing lines. That's what we did with the TikTok breakout.

## 7. Backtesting and the spreadsheet [1:35–1:50]
**Why he backtests:**
- To know what's normal, for example "every August this seems to happen", so you stay calm through losing streaks.
- Because trading is a business: wins are sales; losses, spreads and fees are overheads.

**On screen:** a Google Sheet with one row per trade.

| Group | Columns |
|---|---|
| Trade basics | entry date and time, pair, timeframe, system (trend, reversal or range), entry type |
| Setup checks | condition ✓, phase ✓, support/resistance touch count (a trend line counts double), Fibonacci level, deceleration yes/no, candle pattern |
| Prices | entry, stop, targets 1–3 |
| Result | close date and time, exit price, P&L |

**His idea:** log every setup, then look for patterns, for example "winners all had 5+ touches, so only take those".

**Honest take:** the habit is excellent. The "then filter" step is how people fool themselves. Scan 15 columns for patterns and you *will* find some by luck.
- **The fix is what our tests do:** write the rule down first, then check it on data you haven't looked at.
- Hand backtesting on a chart also leaks hindsight: your eye sees what happens next.

## 8. Is it profitable? The expectancy formula [1:52–1:55]
**On screen:** the formula handwritten.

> **Expectancy = (1 + W ÷ L) × P − 1**
> - W = average win
> - L = average loss
> - P = win rate

**His example:** wins $200, losses $170, 55% right:

(1 + 1.18) × 0.55 − 1 = **0.20**

Above zero means profitable.

**What 0.20 means in dollars:**
- Each trade earns on average 0.20 × your average loss, which is about **$34 a trade.**
- Check: 0.55 × $200 − 0.45 × $170 = $110 − $76.50 = $33.50. ✓
- **Break-even win rate** = L ÷ (W + L) = 170 ÷ 370 = **46%.**
- With a 1-to-1 payoff you need more than 50% even before costs. That's his point at [1:28]: "right 50% with 1 to 1, you're not going to be profitable."

**Plugging in our TikTok breakout test:**

(1 + 4.4 ÷ 2.9) × 0.391 − 1 = **−0.02**

That's just below zero, which matches its profit factor of 0.94. The formula would have flagged it.

**What he leaves out:**
- **How many trades you need.** 20 hand-picked trades prove nothing; you want 100+.
- **Costs**, which lower W and raise L.
- **Drawdown:** how deep the losing streaks get.

## 9. Brokers and placing a demo trade [1:55–2:16]
**On screen:** the Trade Nation demo dashboard ($10,000 practice money), then a real order ticket on Euro/Aussie dollar.

| Field | Value |
|---|---|
| Order type | Buy stop |
| Entry | 1.5633 |
| Stop loss | 1.5384 (249 pips) |
| Target | Sell limit at 1.5908 (275 pips) |
| Duration | Good till cancelled |

**Broker points he makes:**
- **The spread is the broker's fee.** It's the gap between the buy and sell price, like an airport currency kiosk.
- He likes **fixed spreads** because they make backtests accurate.
- **"B-book" brokers take the other side of your trade,** betting that you'll lose.

**Honest take:**
- The fixed-spread and B-book points are real.
- This section is also an ad; the link is his.
- **For you in the US:** the leveraged currency accounts used in this video (called CFDs) aren't allowed for US retail traders. US forex brokers cap leverage at 50 to 1 on major pairs. Everything else in the course carries over to stocks.

## 10. Leverage, margin and lots [2:16–2:23]
**What he says:**
- **Leverage is like a mortgage.** At 100 to 1, $200 of your money controls a $20,000 position.
- **Margin** is your part of that deal. If losses eat into it, the broker demands more money or closes the trade (a **margin call**).
- **Lot sizes:** a standard lot is 100,000 units, a mini lot 10,000 and a micro lot 1,000.

**Honest take:**
- The mortgage comparison is fair.
- His GameStop explanation is muddled. The unlimited loss there was for people *betting against* the stock.
- The practical version: with a stop loss and 1% risk, leverage mainly changes how much cash is tied up. The real danger is price gapping past your stop.
- Our paper bots use cash only, no margin.

## 11. The pitch at the end [2:23–2:27]
**What he promises:** a paid "30-day challenge" where he can take "someone off the street" to consistently profitable *live* trading in 30 days.

**Honest take:** that contradicts his own advice at [0:12]: 6 months learning, 12 months on demo, and no promises about set income. Treat it as marketing.

---

## Scorecard

**Worth keeping:**
- Risk a fixed 1% per trade.
- Size every position from the stop.
- Set entry, stop and target before you're in.
- Trade with the trend and enter on pullbacks.
- Write your rules down.
- Backtest, then demo, then small real money.
- Judge a system by expectancy over many trades.
- Expect uneven income, never a fixed weekly amount.

**Weak or hype:**
- 2–6% a month.
- Every chart example was chosen in hindsight.
- "Confluence" of hand-drawn lines.
- Filtering the spreadsheet until the winners appear.
- The broker plug.
- The 30-day promise.

**Testable:** the "lower-low, lower-close pullback" strategy from section 6. The rules are exact enough to write down before looking at results, like the breakout test.

## Update: the section 6 strategy was tested (Sept 29, 2026)
The owner approved the test. The plan was committed first (07630a1) and the test run on 5,259 US stocks, 2016–2026. **The long side failed all three checks:**
- Profit factor 0.97.
- $100,000 became $83,200, while SPY returned +349% over the same data.
- Worst drop −42%.
- The video's own expectancy formula gives −0.02.

See [PULLBACK_TEST_RESULTS_20260929.md](PULLBACK_TEST_RESULTS_20260929.md).
