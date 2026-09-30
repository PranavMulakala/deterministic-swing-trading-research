# "ULTIMATE Futures Trading Course (Step-by-Step)": what he says, what's on screen, and what holds up

Built from the full audio transcript (Whisper medium, 67 minutes, no repeated-line loops) and 202 screenshots taken every 20 seconds (23 sheets).
- Times like **[0:44:11]** point to the spot in the video.
- Working files (gitignored): `outputs/tmp/futures2/transcript.txt` and `outputs/tmp/futures2/sheets/`.
- **The video file is only 640×360.** Small print (the trade-plan notes, the spreadsheet) can't be read even at full size, so those numbers come from what he says aloud.

**Who:** Brad Goh (the slides and reviews say "Brad"), who runs the paid **"1% Club"** trading mentorship. He wears its logo throughout.

**The video in one line:** a solid, correct explainer of how futures contracts work (the first 22 minutes). Then a "smart money concepts" scalping method on 5-minute and 1-minute charts, a fake "backtest", a wall of student testimonials, and a pitch for his paid program.

**Plugs:**
- 1% Club student results, and its Trustpilot page (4.8 stars from 74 reviews on screen)
- the prop firms FTMO, The 5%ers and FundedNext
- a futures position-size calculator site
- at the end, an "exclusive" 2-hour masterclass that leads into the paid program

**Related:** the web research on your "90% of futures trading" question is in [FUTURES_STRATEGY_EVIDENCE_20260930.md](FUTURES_STRATEGY_EVIDENCE_20260930.md).

---

## 1. Opening claims [0:00–1:12]
**What he says:**
- "90% of traders blow their futures account in under 90 days."
- He has "crossed over $1 million in profits" this year, trading for nearly 7 years.
- "Hundreds of students" are "6-figure funded traders".
- "The only mentorship program with an endless scroll of real student results."

**Honest take:**
- **None of these are checkable from the video.**
- **"90% in 90 days"** has no source.
- **"$1M this year" and "six figures per month" [1:03:21]:** a claim, not a statement of account.
- **"Funded" is not the same as "paid":** a "6-figure funded" student has passed a prop firm's test, not made six figures. Topstep's own 2025 numbers say only 0.71% of its funded traders ever reached a live account.
- **The testimonials are survivors:** they're picked from the students who succeeded.

## 2. Why futures, and what they are [1:12–7:24]
**What he says:**
- **Regulated leverage:** exchange-traded on CME, instead of offshore brokers.
- **Nearly 24/5 hours:** Sunday evening to Friday evening, with a 5–6 PM New York break each day.
- **Deep liquidity:** you can enter and exit "without slippage".
- **US tax, the "60/40 rule":** 60% of gains are taxed at the long-term rate even when day trading.
- **What a contract is:** a standardized contract to buy or sell later. Hedgers (farmers, airlines) and speculators use them. You don't own the asset, you put up margin. ES = $50 × the index; gold (GC) = 100 ounces.
- **Markets:** indices (ES, NQ, YM), commodities (CL, GC), currencies (6E, 6J). **Start with micros (MES, MNQ):** "the same setups... one 10th of the size."

**Honest take:**
- **Mostly correct.**
  - The 60/40 treatment is real (US "Section 1256" contracts).
  - The hours and the daily break are right.
  - "Start with micros" is sound.
- **"Without slippage" is wrong.** You always pay at least the bid/ask gap, and fast markets slip more.
- **"Institutions can't manipulate futures" isn't backed up.** And retail traders are a tiny slice of futures volume: about 3.5% of CME electronic volume in the last CFTC breakdown.

## 3. Platforms and funding [8:04–13:04]
**What he says:**
- **Platforms:** pick one and stick with it (NinjaTrader, Tradovate, TradingView, Thinkorswim). He uses NinjaTrader and TradingView.
- **Funding:** self-funded or prop firm. His advice: start with **$1,000 of your own money as "market tuition"**. Consider prop firms only after "consistent for six months".

**Honest take:**
- Sensible order.
- **Paper trading costs nothing, and teaches the same platform skills first.** That's what our MNQ collector and paper bots are for.

## 4. Contract specs and position size [13:04–21:30]
**On screen (legible):**

| Contract | Tick size | Tick value | $ per point | Initial margin shown |
|---|---|---|---|---|
| Nasdaq-100 E-mini (NQ) | 0.25 | $5 | $20 | $17,600 |
| **Nasdaq-100 Micro (MNQ)** | 0.25 | **$0.50** | **$2** | $1,760 |
| S&P 500 E-mini (ES) | 0.25 | $12.50 | $50 | $15,400 |
| S&P 500 Micro (MES) | 0.25 | $1.25 | $5 | $1,540 |
| Dow E-mini (YM) | 1 | $5 | $5 | $12,650 |
| Dow Micro (MYM) | 1 | $0.50 | $0.50 | $1,265 |

**Position size:** contracts = risk $ ÷ (stop ticks × tick value).
- His example: a $2,000 account risking 1% is $20.
- An MES stop of 8 ticks is 2 points, which is $10 per contract.
- $20 ÷ $10 = **2 contracts**. ✓

**Contracts expire:** index futures roll every quarter (Mar/Jun/Sep/Dec), commodities roughly monthly. So futures suit day traders more than swing traders.

**Honest take:**
- **Correct and useful.** The tick and point values match CME's contract specs.
- **Margins change over time and by broker.** For MNQ at IBKR, a secondary source put it at about **$4,690 intraday and $6,700 overnight** as of Sept 29, 2026, far above the $1,760 on his slide. Always check the broker's live number.

## 5. Futures in plain dollars (what the video skipped)
Example with the Nasdaq-100 at **25,000**. That's roughly where it was in the Iman video's chart; our IBKR collector records the live level.

| | 1 MNQ contract |
|---|---|
| Exposure you control | 25,000 × $2 = **$50,000** |
| Money you put up (IBKR overnight margin) | about $6,700, so about **7.5× leverage** |
| Nasdaq moves 1% (250 points) | **±$500** |
| Nasdaq gaps 10% overnight (it happened in 2020) | **−$5,000** |
| Costs per round trip | about $1.20 in fees (≈ 2.4 ticks), plus any slippage |

- **Losses can exceed your margin.** If the market gaps past your stop, you owe the difference. That's the standard CFTC futures risk disclosure.
- **Costs on scalps:** a 2-point MNQ stop risks $4 per contract, so $1.20 of fees is **30% of the risk** on every trade. Tiny scalps on micros start deep in the hole.

## 6. The strategy: "Simplified Mechanical Trade Plan" [21:55–44:10]
**Charts:** the 5-minute chart for direction and zones, the 1-minute chart for entries. For slower trading, he says to use 1-hour and 15-minute instead.

**Steps (for a long; shorts are the mirror image):**
1. **Break of structure** on the 5-minute: price takes out the last swing high, so the trend is up.
2. **Mark the demand zone:** the consolidation that launched the break of structure.

   Call it "high probability" only if it meets 3 criteria:
   - it caused the break of structure;
   - it left an "imbalance" (a big candle or gap);
   - it "swept liquidity" (dipped under a prior low first).
3. **Wait for price to come back into the zone.** Do nothing until then.
4. **Don't enter on the first bounce.** It's an "inducement": "smart money" baits retail traders so it can take out their stops.
5. **Entry:**
   - **Aggressive:** after price sweeps the low of the first bounce, go long. Stop just below that "liquidation candle".
   - **Conservative:** wait for a 1-minute "market shift", then buy the pullback into the 1-minute demand zone.
6. **Target: 2R,** twice the stop distance. Set it and leave it.

**On screen:** two worked examples on MES charts.
- Both wins, one long and one short. The short "hit a stop loss. No, price hit a take profit" [0:42:07].
- A "B.A.S.I.L." checklist on the last sheet: Break of structure, Alignment with trend, Sweep of liquidity, Imbalance, Last candle.

**Honest take:**
- **It's "smart money concepts" (ICT-style) vocabulary.** Inducement, liquidity sweeps, order blocks, imbalance. Iman's video ranks ICT among the frauds he exposes.
- **It isn't actually mechanical.** Each of these is a judgement call that two traders would mark differently:
  - "the consolidation that led to the break"
  - "a big candle"
  - "the first reaction"
  - "swept liquidity"
- **"Smart money baits retail" is a story, not evidence.** No data is shown.
- **The two examples are hindsight picks.** He scrolls to spots where it worked.
- **The good part:** a fixed stop, a fixed 2R target, 1% risk, and "set and forget". That's the same money management the course video taught.

## 7. His "backtest" [44:11–45:37]
**What he shows:** a spreadsheet titled "Simplified Mechanical Trade Plan Backtest Results".
- Inputs: start with $1,000, risk 1% a trade, **assume a 45% win rate** at 1:2 risk-reward, 100 trades.
- Result: **+58%** ($580 on $1,000; "$11K" on $20K).

**Honest take: this isn't a backtest.** No price data is involved. He typed in a win rate and computed what it would make.
- **At 45% wins and 2R,** each trade averages +0.35R, so 100 trades compound to about **+40%**.
- **His +58%** needs about 49 wins out of 100, a lucky draw above his own 45% assumption.
- **The whole question is whether 45% at 2R is real.** Break-even at 2R is 33% before costs, and nothing in the video measures his actual win rate.
- **Our five tests show why typed-in win rates aren't evidence.** Every pre-declared test came in lower than the story, and the two strategies from these videos landed around break-even.

## 8. Three tips and the pitch [46:00–67:26]
**The tips:**
1. **"Don't get distracted by the woman in the red dress."** Master one strategy, one style, one market; strategy-hopping resets your skill to zero.
2. **The competence curve:** unconscious incompetence → conscious incompetence ("where 95% of traders quit") → conscious competence → unconscious competence. His inflection point came in year 3.
3. **Trading is exponential, not linear:** "if you don't quit, you can't lose... you are pretty much guaranteed to become successful at trading if you just put in three years, five years."

**His story:** he worked as a busboy for $7 an hour and repeatedly blew $1,000 paychecks. Now "six figures per month", "dream apartment", parents retired.

**The close:** a free "exclusive" 2-hour masterclass that leads into the program.

**Honest take:**
- **Tip 1 has something to it.** Changing strategies after every small losing streak means you never learn anything; our pre-declared tests protect against that too.
- **But "never quit" is the wrong lesson when the evidence says a method doesn't work.** The 97%-of-Brazilian-day-traders study found **no sign that people improved with practice**. Persistence mostly meant losing longer.
- **"Pretty much guaranteed" is the most harmful line in the video.** The best large studies of day traders (Brazil and Taiwan) find about 97–99% don't make money.
- **His story is the survivor.** The busboys who blew their paychecks and never recovered don't make courses.

---

## Scorecard

| Claim or idea | Verdict |
|---|---|
| Contract specs, tick values, $ per point | **Keep.** Correct and matches CME |
| Position size = risk ÷ (stop ticks × tick value) | **Keep.** Same as the course's "size from the stop" |
| Start with micros (MES/MNQ) | **Keep.** Better yet: start on paper |
| 1% risk, fixed stop and 2R target, set and forget | **Keep** |
| Contracts roll quarterly; watch the daily break | **Keep** |
| 60/40 US tax treatment | **True** (Section 1256); check with a tax professional for your case |
| "Without slippage" | **Wrong.** Costs are about 2.4 ticks round trip on MNQ before slippage |
| Margin figures on the slide | **Out of date.** IBKR is about $4.7k–6.7k for MNQ now |
| "Mechanical" smart-money strategy | **Not mechanical.** Its key steps are judgement calls; the examples are hindsight picks |
| +58% "backtest" | **Not a backtest.** A typed-in 45% win rate, and a lucky draw even on that |
| $1M this year, six figures a month, hundreds of funded students | **Unverified marketing** |
| "If you don't quit, you can't lose" / "pretty much guaranteed" | **False,** per the large retail-trader studies |
| Hype level | **High.** The most sales-heavy video so far |

## Is there anything to test?
**Not now, and not fairly.**
- **The rules aren't exact.** "Zone", "imbalance", "first reaction" and "sweep" would all have to be defined by us. A failure could then be blamed on our reading of the rules, and a success could come from how we happened to define them.
- **It needs years of 1-minute futures data,** which we don't have. The MNQ collector has only recorded since Sept 29. Historical 1-minute data would cost money (Databento), and that needs your OK.
- **The honest version of "test it":** paper-trade his exact written plan on MNQ with our IBKR paper account, and log every trade for 8 weeks. That tests the method *as you would execute it*. It's a learning exercise, not a money plan.
