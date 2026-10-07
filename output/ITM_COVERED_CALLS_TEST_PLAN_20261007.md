# Test #26 plan: in-the-money covered calls with roll-downs (Joey's method) on SPY (written October 7, 2026, before any code or result)

- **Why:** test #25 (a plain covered call ~2% above the price, never rolled) lost $25,858 on the calls. The owner asked Joey for his rolling rules.
- **Joey's answer (Oct 7, 12:08 PM):** rolling is "experience and market conditions". He sent an Options Animal lesson on advanced covered calls instead.
  - The lesson is **private**: Joey asked that it not be shared. It is not stored in this repository. The rules below are a short paraphrase of the parts that can be turned into rules.
- **The lesson matches what Joey actually did.**
  - DELL (Oct 1): he closed his 560 call and opened a 545 **in-the-money** call a month out, which is a roll down and out.
  - He was fine being called away for ~4% in ~30 days. The lesson's examples are 3.7% in 30 days and 4.2% in 44 days.
- **Report:** dollars only.
  - money per week, $1,000 weeks, worst week, month and drop;
  - what the calls (and, in one version, the puts) added or cost.
  - **No SPY comparison line** (owner's instruction).
- **Paper research only.** No orders.

## Where each rule comes from
| Rule | Source |
|---|---|
| Sell an **in-the-money** call (strike below the price) against the shares | Lesson; Joey's DELL 545 call |
| 30–50 days to expiration | Lesson; Joey's "a month out" |
| Pick the strike by its **annualized return if called away**, and only trade if it "beats SPY" | Joey, Oct 7 email |
| The normal exit is being called away at expiration | Lesson; Joey's DELL plan |
| When the stock falls, buy back the call and sell a **lower** strike further out, **only for a net credit** | Lesson (first bearish adjustment); Joey's MU and DELL rolls |
| Add a long put (45+ days) after a sharp drop on bad news | Lesson (collar); Joey buys puts "when truly bearish" |
| Implied volatility of 25–45% is preferred | Lesson |

**Not tested** (they need judgment or spare cash):
- the lesson's chart-based entry setups (support, earnings gaps, channel bottoms). The account always owns the shares, as in #25.
- buying more shares after a 15–20% drop (the account has no spare cash);
- extra bullish trades when the stock runs away.

## The question
If you own SPY shares and sell an in-the-money call against them each month, rolling it down when SPY falls, how many dollars does that make? And do the calls earn their keep?

## Data (the same as test #25)
- **SPY option quotes:** Databento OPRA closing snapshots, 2016–2025 (`outputs/spy_options_data`).
  - Strikes reach about 30% below the price; expirations run 25–65 days out.
- **SPY's price:** from put-call parity (test #10's helper).
- **Cash:** earns the 3-month T-bill rate.
- **Dividends:** Alpaca, 37 ex-dates, Jun 2016 – Dec 2025. Mar 2016 is missing (stress years only).

## Rules (main version)
1. **Start:** $100,000 at the close of Jan 2, 2020.
   - Buy whole SPY shares at the parity price + $0.01.
   - Leftover cash earns T-bill interest.
2. **Sell a call** on any day with no call open: the first day, after each expiration or assignment, and any later day if none was sold.
   - **Contracts:** one per 100 shares (whole contracts).
   - **Expiration:** closest to **40 days**, within **30–50** days. Ties go to the later one.
   - **Strike:** look only at strikes **below** SPY with a bid above zero.
     - For each, the return if called away = (strike − (SPY − bid)) ÷ (SPY − bid), annualized × 365 ÷ days.
     - Pick the **lowest strike** (the most protection) whose annualized return is **at least 10%** (about SPY's long-run yearly gain, Joey's "beats SPY").
     - **If no strike reaches 10%, sell nothing that day**, and try again the next day.
   - **Fill:** at the **bid**, minus $0.03 a contract.
   - **No new call on the trading day before an ex-dividend date.** Deep in-the-money calls are often exercised that night. The account waits one day.
3. **Expiration:** if SPY is above the strike, the call is settled at its intrinsic value, (SPY − strike) × 100 per contract.
   - This equals being called away and buying the shares back at the same price.
   - It is paid from cash. If cash runs short, the account sells whole shares at SPY's price to cover it.
   - Otherwise the call expires worthless.
4. **Early exercise before a dividend:** on the trading day before an ex-dividend date, if the open call is in the money and its time value (mid − intrinsic) is less than the dividend, it is exercised.
   - It is settled at intrinsic value that day. The shares still collect the dividend; with cash settlement this is the same money as being called away and buying back after the ex-date.
5. **Roll down (the lesson's first bearish adjustment):** on any close where SPY is **below the open call's strike** and the call has **7 or more days** left:
   - Pick a new call with rule 2's expiration and strike rules, using today's SPY.
   - **Roll only for a net credit:** the new call's bid must be above the old call's ask.
     - Buy back the old call at the ask + $0.03 a contract; sell the new one at the bid − $0.03.
   - If there's no qualifying new call or no net credit, keep the old call and check again the next day.
   - With fewer than 7 days left, let it expire (rule 3).
6. **Dividends:** credited to cash on the ex-date for shares held.
7. **Account value each day:** shares × SPY + cash − open calls at mid × 100 (+ open puts at mid × 100 in the collar version).
8. **Each sold call is one trade.** Its P&L is the credit minus what it cost to close: the buy-back on a roll, or the intrinsic paid at expiration or early exercise.

## Information-only versions (same rules, one change each)
| Version | Change |
|---|---|
| `no_roll` | never roll (shows what the roll-down rule adds or costs) |
| `ann5` | strike rule needs only 5% annualized (deeper in the money, more protection, less income) |
| `ann20` | strike rule needs 20% annualized (closer to the price, more income, less protection) |
| `iv_band` | new calls (not rolls) only when SPY's ~30-day implied volatility is **25–45%** (the lesson's range) |
| `collar_on_drops` | main rules **plus** a put whenever SPY closes **3%+ below the prior close** and no put is open |
| `mid_fill` | trade every option at the mid price |
| `shares_only` | never sell calls (shows the calls' own dollar effect) |

- **`iv_band`'s volatility estimate:** take the at-the-money call and put at the expiration closest to 30 days. Volatility ≈ (call mid + put mid) ÷ (0.8 × SPY × √(days ÷ 365)).
- **`collar_on_drops` puts:**
  - one put per call contract;
  - expiration closest to 50 days, within 45–65;
  - the strike nearest SPY (ties go higher);
  - bought at the ask + $0.03;
  - held to expiration and settled at intrinsic.
  - Their P&L is reported separately.

## Windows
- **Main:** Jan 2, 2020 – Dec 31, 2025, with halves 2020–2022 and 2023–2025.
- **Stress:** Jan 4, 2016 – Dec 31, 2019, from its own $100,000.

## Pass bar (main version; the same bar as test #25; dollars only)
- **C1:** the calls earn their keep: total call P&L > 0 **and** a call profit factor ≥ 1.3.
  - Profit factor = winning calls' P&L ÷ |losing calls' P&L|.
- **C2:** the account is profitable in both halves.
- **C3:** the worst drop from a high is ≤ 25%.
- **Verdict:**
  - **PASS** if C1–C3 all hold;
  - **PASS (post-COVID only)** if they hold in the main window but C1 fails in the stress window;
  - **FAIL** otherwise.

## Checks before results
- **Unit tests:**
  - the strike pick (lowest strike reaching 10% annualized; none → no sale);
  - the roll (only below the strike, only with 7+ days left, only for a net credit);
  - early exercise before an ex-date and no sale that day;
  - settlement with a cash shortfall;
  - the collar put on a −3% day.
- **An independent verifier**, written separately:
  - re-picks 12 random main-version calls from the raw CSVs (expiration, strike, sale bid, and how each one closed);
  - checks that every roll happened on a close below the old strike with 7+ days left and a net credit;
  - checks that the trade list adds up to the reported call P&L.
