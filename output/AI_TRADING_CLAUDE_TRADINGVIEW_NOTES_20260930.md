# "AI Trading Full Course" (Mind Math Money): connecting Claude to TradingView. What he says, what's on screen, and what holds up

Built from the full audio transcript (Whisper medium, 70 minutes, no repeated-line loops) and 211 screenshots taken every 20 seconds (24 sheets).
- Times like **[0:57:02]** point to the spot in the video.
- Working files (gitignored): `outputs/tmp/futures/transcript.txt` and `outputs/tmp/futures/sheets/`. The folder is named "futures" because that's what we expected the file to be.

**This is not the futures video.** The file `videoplayback.mp4` is a course on using Claude (the AI) inside TradingView (a charting website). The only futures-looking content is a gold-bar-and-oil-pump picture in the first frame.

**Conflict of interest:** the video is about the AI model family I belong to. I've judged it by the same standard as the other videos.

**The video in one line:** a YouTuber connects Claude to TradingView with a free, unofficial add-on. He then shows Claude:
- marking swing highs and lows
- drawing support and resistance
- adding indicators
- reading several timeframes
- writing and backtesting a moving-average strategy on Bitcoin
- doing position-size math

**What it's selling:**
- a TradingView affiliate link ("30 days Premium + $15 bonus")
- his own trading-journal and candlestick-mug store
- his website and free course playlist

---

## 1. What "AI trading" means [0:05–0:11]
**What he says:**
- AI trading ranges from "AI helps with 10% of the work" to fully automated systems.
- Institutions have used AI for decades, and "that edge is now open to everyone": retail traders "have access to the same powerful models as the top traders on Wall Street."
- In this course, AI is an assistant and you make the final call.

**On screen:**
- a sketch of a spectrum from "AI-assisted analysis" to "AI-driven systems"
- a "What AI Can and Can't Do" slide: it **can** read charts, apply technical analysis, do math and stay objective; it **can't** predict the future or guarantee profits ("nothing can")

**Honest take:**
- "Can't predict the future or guarantee profits" is right. It's the most important line in the video.
- "Same access as Wall Street" is misleading. Big firms' edge was never access to a chatbot. It's speed, data, execution costs and capital, and a chat model doesn't give you those.
- "Learning AI now is a real edge over traders who wait" isn't backed by any evidence in the video.

## 2. Connecting Claude to TradingView [0:11–0:22]
**What he says:**
- It uses the "TradingView MCP", a free open-source bridge on GitHub (`tradesdontlie/tradingview-mcp`, about 4.3k stars on screen).
- It has four pieces:
  - Node.js
  - the bridge
  - TradingView desktop launched in **debug mode**
  - one line in Claude's settings
- It needs the TradingView desktop app on a **paid plan**, plus the Claude desktop app.
- He pastes an install prompt from his website and lets Claude walk him through the setup.

**On screen:**
- the GitHub page, with a big "This is not an official TradingView tool" warning
- the README: "not affiliated with, endorsed by, or associated with TradingView"
- his install prompt
- Claude confirming "TradingView is connected and healthy"

**Honest take:**
- He does say to read the GitHub disclaimers before installing. Good.
- **"Debug mode" opens a local control port on the TradingView app.** Any program on your computer that can reach that port can drive TradingView. It's a real security trade-off, and he glosses over it.
- Under your rules, installing third-party software like this is your decision, and security settings are yours to change. **I haven't installed anything.**
- We don't need it for research. Our Python scripts on Alpaca data already do the same things, and they're repeatable and pre-declared.

## 3. How to prompt Claude about a chart [0:19–0:22]
**On screen, "Prompt the question, not the chart":**
- Claude already sees the asset, the timeframe and every candle, so ask the question directly.
- One task at a time.
- Share your own view and let Claude challenge it.
- Name the concept you mean ("market structure", "supply and demand").

**Demo:** "What is Bitcoin trading at right now?" Claude answered $63,187 (Bitstamp spot), which matched the chart.

**Honest take:** these are good prompting habits. The "let it challenge your view" tip is the most useful one.

## 4. The four chart workflows [0:22–0:47]

| Workflow | What Claude did on screen | His verdict | Honest take |
|---|---|---|---|
| **1. Market structure** [0:22] | Marked major swing highs and lows on daily Bitcoin and called the trend "downtrend" | Highs "very clean", one questionable low | Fine as a second opinion. There's no data showing swing labels predict anything. |
| **2. Support and resistance** [0:27] | Drew 12 levels since 2024: all-time high ~$124–126k, ~$108–112k, a support zone ~$57–60k | "Super impressive, not perfect" | These are hindsight lines. A level that "held" three times is only visible afterwards. Nothing measures whether the levels help. |
| **3. Indicators** [0:34] | Added a purple 50-day SMA; looked up and set Linda Raschke's MACD (3-10-16) on its own | Solved "in one shot" | Accurate: 3/10/16 is the known Raschke setting. Adding indicators by chat saves clicks; it isn't an edge. |
| **4. Multiple timeframes** [0:41] | Asked clarifying questions first, then flipped daily / 1-hour / 5-minute: "bearish but trying to bottom", "neutral range", "bullish intraday" | "Pretty solid" | A description of the chart, not a forecast. He checked it by eye, not against what happened next. |

**Useful tip:** asking Claude to ask *you* questions before starting [0:44:13] is a good habit for any AI task.

## 5. Building and backtesting a strategy [0:47–1:01]
**His strategy (exact rules, on screen):**
- **Market:** Bitcoin/USD (Bitstamp), daily candles.
- **Buy** when a daily candle **closes above** the 50-day simple moving average (SMA).
- **Sell** when a daily candle **closes below** it.
- Long only, one position at a time.
- $10,000 start, full account in each trade.

**The backtest (Claude wrote it in TradingView's strategy tester):**
- The window was "calibrated" to start May 15, 2015, so that it holds exactly 100 trades.
- Results table, read from the screenshot [0:57]:

| | No commission | 0.1% commission per side | Buy and hold Bitcoin |
|---|---|---|---|
| Net profit on $10k | +$5.85M (+58,548%) | **+$4.80M (+47,962%)** | +$2.69M (+26,876%) |
| Yearly growth (CAGR) | 53.4% | 51.3% | — |
| Win rate | 30% (30/100) | 29% (29/100) | — |
| Profit factor | 2.28 | 2.12 | — |
| Worst drop | — | **−54%** | −83% (2018) |

- **Claude's own summary on screen:**
  - "The strategy's edge here isn't really the buying, it's the not holding through bear markets."
  - It lost 71 of its 100 trades.
  - It's "one asset over one historical period that happened to trend beautifully... there's no guarantee the next decade rewards trend-following the same way."
- **His takeaway:** "moving averages are often better used to avoid downside than to maximize upside."

**Honest take:**
- **Credit where due:** he added commissions, compared against buy and hold, and said up front, "I'm not saying that this is a good trading strategy at all."
- **Hindsight asset choice:** he picked Bitcoin, which went from $236 to about $63,000 over this window. Almost any "stay in while it's rising" rule looks brilliant on the best-performing asset of the decade.
- **Hindsight window:** the start date was chosen after the fact to give a round 100 trades. It's one run with no untouched later period to check it against.
- **Missing costs:**
  - 0.1% per side is at the cheap end for retail crypto, and there's no slippage.
  - In a taxable account, every sell is a taxable event, often at short-term rates.
- **Still a 54% drop.** That's more than double our 25% limit. The table says "less bad than buy and hold's 83%", not "safe".
- **The "done in an afternoon" slide** ("weeks of strategy design, done in an afternoon"): coding a backtest in an afternoon is real. Knowing whether the result will hold up is the slow part, and AI doesn't speed that up.

## 6. Risk management with AI [1:01–1:05]
**Demo:**
- He drew a long position on Bitcoin: entry $63,926, stop $61,317, target $71,752, a 3:1 reward-to-risk setup.
- He asked for a size that risks 2% of a $10,000 account.

**Claude's answer:**
- Risk budget: $200.
- Risk per coin: $2,609.
- Size: **0.0767 BTC**, about $4,900, roughly 49% of the account, with no leverage.
- It also noticed that TradingView's position tool was still set to a $1,000 account and offered to fix it.

**Check:** $200 ÷ $2,609 = 0.0767. ✓ The target is $7,826 above entry, which is 3.0× the $2,609 risk. ✓

**Honest take:**
- This is the most useful workflow in the video. It's the same "size from the stop" rule the course taught.
- A calculator or one line of Python does it too. The AI adds convenience, not an edge.

## 7. Using AI safely and wrap-up [1:05–1:10]
**On screen:**
- Verify key price levels against the chart yourself.
- Claude sees live prices, not the news behind them, unless you ask it to look.
- "AI prepares. You decide and execute."

**The end:** a pitch for likes, comments ("write 'full course'"), and his free course playlist on market structure, "smart money concepts" and Fibonacci.

**Honest take:** "AI prepares, you decide" matches our own setup: Claude runs research and paper bots, and real-money decisions are yours.

---

## Scorecard

| Claim or idea | Verdict |
|---|---|
| AI "can't predict the future or guarantee profits" | **Keep.** The most honest line in the video |
| Verify whatever the AI draws or calculates | **Keep** |
| Ask the AI to ask you clarifying questions first | **Keep.** A good general habit |
| Position sizing from the stop (2% risk → 0.0767 BTC) | **Keep.** The math checks out |
| Always compare with buy and hold, and include fees | **Keep.** It's what we do; he actually did it |
| "Retail now has the same edge as Wall Street" | **Hype.** Access to a chatbot is not their edge |
| "Learn AI now or get left behind"; "you will make more money" | **Hype.** No evidence shown |
| 50-SMA strategy beat Bitcoin buy and hold 1.8× | **True on screen, but hindsight.** One asset, one lucky decade, one run, 54% drop |
| Support/resistance and structure drawn by AI | **Unproven.** Looks tidy; nobody measured whether it helps |
| TradingView MCP install | **Your call.** Unofficial, needs a paid plan, opens a local debug port. Not needed for our research |
| Hype level overall | **Medium.** Mostly a tool demo with some honest caveats; sponsor link and store plugs |

## Is there anything to test?
**Yes, one exact rule: the 50-day SMA cross.** Buy on a daily close above the 50-day SMA, sell on a daily close below it, long only.

**The fair question isn't "did it beat Bitcoin 2015–2026?" but "does it hold up somewhere he didn't hand-pick?"** A pre-declared test could run on data already on disk, with no download:
- **Main test: SPY, 2016 to Sept 28, 2026.** Compare the 50-SMA rule with buy and hold at 0.1% per side, using the same pass bar as before:
  - profit factor ≥ 1.3
  - profitable in both 2016–2020 and 2021–2026
  - max drawdown ≤ 25%
  - plus one extra check: does it beat SPY buy and hold or cut the worst drop meaningfully?
- **Optional second test:** the same rule across our 5,259 stocks, to see whether it "avoids the downside" on single names.
- **Optional Bitcoin re-check:** a free Alpaca crypto download, but only with your OK, since it's a new download.

**My expectation, stated before any numbers:** on SPY it will probably cut the worst drops (like 2020 and 2022) but trail buy and hold in total return, because of whipsaws in choppy years. If you want it, I'll write the plan and commit it before computing anything, as usual.

## What this means for you
- **As a tool demo, the useful parts are ones we already have:** sizing math, backtests that include fees and compare with buy and hold, and "AI prepares, you decide."
- **The headline numbers ($5.85M from $10k) come from picking Bitcoin with hindsight.** Claude said so on screen.
- **Still waiting:** the actual futures video (contract sizes, margin, and how losses can exceed margin, tying into our MNQ collector).
