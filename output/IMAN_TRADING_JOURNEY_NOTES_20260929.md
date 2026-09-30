# Iman Trading, "My Final Trading Guide – Built by Filming My ENTIRE Journey": what he says, what's on screen, and what holds up

Built from the full audio transcript (Whisper medium, 93 minutes, no repeated-line loops) and 186 screenshots taken every 30 seconds (21 sheets). Times like **[1:25:33]** point to the spot in the video.
- Working files (gitignored): `outputs/tmp/iman/transcript.txt` and `outputs/tmp/iman/sheets/`.

**The video in one line:** a YouTuber tells the story of three years spent learning to day-trade Nasdaq futures, from his first shaky week in Sept 2022 to steady prop-firm payouts from mid-2024. It covers how he learned, not the exact rules he trades.

**It is not a strategy video.** His actual method ("Categorical Trading") is in a separate video that he links. He says so himself [0:42:54]: "this entire video has nothing to do with me teaching my personal trading strategy".

---

## 1. His claims up front [0:00–1:45]
**What he says:**
- Since 2024 he has withdrawn **24 payouts from prop-firm funded accounts, totalling $25,191** [0:00:33].
- He's "up over $5,000" across 4 funded accounts that can currently pay out.
- "I am not a full-time trader. I have never sold a course and my guides will always be 100% free."

**On screen:** a hand-drawn timeline, "2024 → Today (November 2025): 24 payouts, $25,191".

**Dollar check:**

| | Amount |
|---|---|
| Total payouts | $25,191 |
| Period | about Mar 2024 to Nov 2025, roughly 20 months |
| Per month | about $1,260 |
| Per week | about **$290** |
| Evaluation fees paid | not stated (he says to "factor in the cost of an evaluation" [1:27:52]) |

**Honest take:**
- **The good:** this is a modest, believable figure. He doesn't claim to be rich, and he says it's not enough to trade full-time.
- **The limits:** it's gross payouts, before evaluation fees and the accounts he lost. There's no full profit-and-loss statement, so we can't check his net result.
- **Selection bias:** we're watching the one person who stuck it out and made a video. We don't see the people who spent three years and stayed at break-even.

**Against your $1,000-a-week goal:** after about three years of near-full-time work, he averages roughly $290 a week in payouts.

## 2. Phase 1: pure beginner experiments [1:45–24:50]
He trades micro futures from a blank chart and talks through every thought. The notable bits:

- **"Not all pullbacks pull back"** [0:01:58]: sometimes the pullback just keeps going.
- **He was shaking on a roughly $20 trade** [0:02:56]. That's because he used a real account. He later calls this stupid: "there is zero benefit to not using a sim account when you're new" [0:09:25].
- **Moving the stop:** he kept moving his stop loss out of anxiety. Looking back, he says to set it and leave it: "you just accept the target and risk for what it is... and extract the lessons later" [0:10:00].
- **Big candles are outliers** [0:02:31]: the longer a candle gets, the less likely it is to keep going.
  - This is stated as fact with no data behind it. He also warns later against beginners using words like "never" and "always".
- **"If everyone else thinks it would happen too based on beginner knowledge, of course it's not going to work. If it did work, none of us would be called beginners."** [0:07:17]
  - This is the same point as our four failed tests.
- **Take lots of trades on a practice account.** "Your brain filters out the pretend trades... making you think you were right more often than you really were" [0:08:36].

**On screen:** dozens of 20-second and 5-minute Nasdaq charts with stop (red) and target (green) lines, plus a "Best Loser Wins" table on why traders avoid taking losses.

## 3. What he took from the first month [0:24–0:44]
- **Reminder notes:** write down the mistakes you keep making, reread them several times an hour, and update them weekly [0:26:28].
- **Don't generalise from a handful of examples.** "Don't put yourself in a box until you've really tested out everything for a long time and can actually back up a definitive statement with proof" [0:28:07].
- **Two market states:**
  - **Consolidation (chop):** price is more likely to stay where it has been.
  - **Direction (trend):** price is more likely to go somewhere new.
  - His later strategy is built on sorting the market into one of these two [0:12:09].
  - **On screen [sheet 8]:** "All price action exists on a spectrum... between consolidation and direction."
- **His worst habit:** buying at the top of a range and selling at the bottom, betting on a breakout. "It worked sometimes, but not nearly enough times to offset the losses" [0:33:16].
- **Timeframes are just filters.** A 3-minute, 8-minute or 24-minute chart shows the same price moves, only drawn differently [0:30:36].
- **The turning point, "superscalping" [0:40–0:44]:** very quick trades in the morning session, practice account only. It was his first green day.

**Futures math shown on screen [0:43:44]:**
- On the same day, a drop was 98.5 points on NQ (**$1,970** per contract, so $20 a point) and 22.5 points on ES (**$1,125**, so $50 a point).
- His point: a one-point slip on entry hurts less on NQ, because NQ moves more points for the same move.
- Micro contracts are 1/10 the size: MNQ is $2 a point and MES is $5 a point. That matches his "four points being $20" on MES [0:37:40].

## 4. First draft of a strategy, Dec 2022 [0:45–0:59]
- **Sizing stop and target from volatility:** he tried setting them from ATR, the average size of recent candles. One example was a 5-point stop and a 7-point target when things got more volatile [0:46:11].
- **Auto-breakeven:** a platform feature that moves the stop to the entry price once a trade is up a set amount. His conclusion was that whether it helps depends on how price is moving [0:47:26].
- **Keep a spreadsheet.** He recorded:
  - stop and target sizes, and whether they were fixed or moved
  - ATR
  - price conditions
  - time of day
  - profit or loss

  **On screen [sheet 11]:** his first sheet, with 3 sessions: +40.28, −2 and +40.
- **Key data point [0:53:42]:** "win rate over a long period... doesn't mean anything... unless you separate the sessions where you allowed moving the stop loss and profit targets versus keeping everything stationary."
  - This is why we pre-declare tests and never mix rule versions.
- **Two paths to profit [0:54:08]:**
  - **Systematic:** 100% rules; a computer could run it.
  - **Discretionary:** a system plus judgement calls.

  He says both are possible and both are hard. Most profitable traders he knows use some discretion, and "that part cannot be taught... only learned through experience" [0:56:20].
- **On screen [sheet 13]:** his Dec 2022 reminder document. It includes "Switch biases quickly. Go ham," "First line ATR 6 is perfect for 3–4," and "Consider trading YM?"

## 5. Five months of refining, with setbacks [0:59–1:17]
- **A letter to himself [1:03:35]:** he hit his max daily loss on 5 of 7 days because he kept chasing 30–40-point moves.
  - Chasing those moves "worked for a bit," and his biggest winning day was "the exact way you should not be trading". His lesson: "You never base a system on the outliers."
- **His rule afterwards:** no trades over about 15 points.
- **Risk-reward has to match your win rate [1:08:17].** A system that wins often should use small targets. This is the same idea as the course's expectancy formula.
- **Sizing up broke him.** "Trading well came to an end after I tried sizing up to 2 contracts" (on-screen caption, sheet 15).
- **Wanting big wins works like a slot machine.** A rare big win lights up the same reward system in the brain as gambling does [1:10:50].
- **Failure is the best teacher,** because wins can reward luck [1:15:25].

## 6. Prop firms and payouts [1:17–1:28]
**How he explains prop firms [1:17:05]:**
- You pay a fee (about $100) for an evaluation.
- If you hit the profit target, the firm "funds" you, and you keep most of what you make.
- If you blow the account, you owe nothing, but you pay again to retry.

**His own path:**

| Date | What happened |
|---|---|
| Apr 2023 | Started trying evaluations ("I obviously was not" ready) |
| Oct 2023 | Passed his first evaluation, after several attempts, over a month and about 100 trades |
| Oct 2023 – Jan 2024 | Kept that funded account alive about 3 months as a "basically break even trader", then lost it, with no payout |
| Dec 9, 2023 | Finished the written guide to his strategy ("final draft") |
| Mar 2024 | First payout, $2,382.12 (on screen: payment email) |
| Jul 2024 onward | "Consistently withdrawing profits... each month. Not an enormous amount" |
| 2025 | Promoted to a live account with one firm after 5 straight payouts (on screen: the firm's email) |

**Honest take on prop firms:**
- **The structure:** your downside is capped at the fee. That's safer than risking your own $50k.
- **But the firms earn most of their money from evaluation fees,** and most people who buy evaluations never get a payout. Plan for several paid resets.
- **"Funded" accounts are often simulated.** Payouts come from the firm under its own rules: drawdown limits, consistency rules, and payout caps. His "promotion to a live account" suggests his earlier funded accounts weren't live.
- **His website ranks prop firms.** Review pages like that usually earn referral fees. The video doesn't say whether his does, so treat his firm rankings as possibly paid.

## 7. The final stage and general advice [1:28–1:33]
- **"Final stage":** you can look back at any old trade and say whether it followed your system, without knowing whether it won.
- **Moving the stop costs double [1:25:02].** He moved a stop to save $20, lost $80 instead of making $100, and was $180 worse off. At a 1:1 risk-reward, moving stops breaks the math.
- **His live window is about 10 minutes a day.** 85–100% of that is noise he ignores, with 1–5 moments where "the odds are no longer 50-50" for him [1:24:12].
- **Automate the guardrails.** Have the platform lock you out at your max daily loss instead of relying on willpower [1:32:26].
- **Other advice:**
  - "Do not pay for courses, private communities, or anything. And do not get attached to any trading figures" [1:18:43].
  - "Never risk money you can't afford to lose" [1:33:01].
- **On screen at the end:** his free website, links to his psychology videos, and a plug for his free prop-trader Discord.

---

## Scorecard

| Claim or idea | Verdict |
|---|---|
| Practice on a sim for months before real money | **Keep.** Same as the course, and same as our paper-first rule |
| Set stop and target up front, never move them mid-trade | **Keep.** His own $180 example shows why |
| Separate your stats by rule version | **Keep.** This is why we pre-declare tests |
| Don't build a system around rare big wins | **Keep** |
| Risk-reward must match the win rate | **Keep.** Same as the expectancy formula |
| Automate max-daily-loss lockouts | **Keep.** Our bots already have kill files and checkpoints |
| Sizing up brings old problems back | **Keep.** Relevant to your $50–70k LITE idea |
| "Big candles are less likely to continue" | **Unproven.** Stated as fact with no data |
| $25,191 in payouts over about 20 months | **Plausible but unchecked.** Gross, before fees and failed accounts; one survivor |
| "Everything in trading can be learned for free" | **Fair.** His site is free; prop-firm rankings may carry referral fees |
| Hype level | **Low.** Much lower than the TikToks or the course; he's frank about the years of break-even |

## Is there anything to test?
**No, not as a pre-declared rule test.**
- There are no exact entry or exit rules. He describes "superscalping" and a discretionary 10-minute morning window, and says the discretionary part "can only be learned through experience."
- His strategy video ("Categorical Trading") would be the place to look for rules. He calls that one discretionary too.
- The time scale is wrong for our data. He trades 20-second Nasdaq futures charts. Our 10 years of history is daily stock bars. Our MNQ collector records real-time futures data, but only since it was revived on Sept 29, which isn't enough to test anything.

**The one checkable claim:** "the longer a candle gets, the less likely it is to continue." We could test a daily-bar version on our 5,259 stocks, with no download needed. For example: after a daily candle bigger than 2× the 20-day ATR, does the next day continue in the same direction less than 50% of the time?
- This would be a fact check, not a trading strategy.
- I'd only run it if you want it, with the plan committed first as usual.

## What this means for you
- **The most honest video so far.** His own numbers are the useful part:
  - about 2 years from his first trade to steady payouts;
  - about 70,000 words of notes;
  - roughly $290 a week in payouts at the end.
- **It points the same way as our four failed tests.** Obvious chart rules don't pay. Where there's an edge, it comes from a lot of careful, recorded work, and the money is modest at first.
- **Link to the next video:** he trades NQ and MNQ, the same contract our IBKR paper collector records. The futures video should explain contract sizes, margin, and why losses can exceed margin.
