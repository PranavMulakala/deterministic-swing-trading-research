# LITE dip bot: history check at $60,000 per buy (September 28, 2026, evening)

Historical replay only. This is not live or paper evidence. Code: `research/lite_dip_history_v1/run.py` (5 tests). Results: `output/lite-dip-history-2022-2026-sip.json` and `-iex.json`.

**What was replayed.** The LITE paper bot's exact rule:
- **Signal:** in the first 30 minutes, LITE dips at least 1% below the 09:30 open, and the 09:55 bar still closes below the open.
- **Buy:** one position at a time, at 10:00 at the price +0.1%.
- **Sell:** a GTC sale at +2% over the fill. There is no stop and no time limit.
- **Size:** each buy spends **$60,000**, which is 66 shares at about $910. That is the size the owner set this evening.
- **Fills:** a sale needs the regular-session price to reach the target. A gap above the target at the open sells at the open.
- **Data:** main results use **SIP** signals, meaning complete market data. **IEX**, what the bot reads live, is shown in brackets as a check. In 2022–2024, IEX lacked complete morning bars on 445 of 753 days, so the IEX results for those years mostly reflect missing data. In 2026, both feeds were complete and nearly identical.
- **Why these windows:** the owner suggested judging the bot on this year and last year, because LITE's growth changed its behavior. Those windows are the main result. 2022–2024 is LITE's most recent fall (−63%) and is kept only as a stress test of what happens if the boom ends.

## Results by period (SIP signals; IEX in brackets)

| Period | Sales | Realized profit | Weeks with ≥ $1,000 realized | Average per week | Longest stretch with no sale | Worst paper loss on one holding | Worst drop from peak |
|---|---:|---:|---:|---:|---:|---|---:|
| **2026** (Jan 2 – Sep 28) | 59 [56] | +$79,946 [+$76,362] | **31 of 40** [29] | $1,999 [$1,909] | 7 weeks [7] | −$21,658 (−36%; bought Jun 16 at $933.24, sold Aug 12) | −$21,185 |
| **2025** | 28 [37] | +$38,403 [+$50,402]; marked +$34,536 with a buy still open | **18 of 53** [24] | $725 [$951] | 25 weeks [17] | −$32,080 (−53%; bought Jan 24 at $98.24, sold Jul 17) | −$29,719 [−$24,597] |
| **Jan 2025 – Sep 2026** | 85 [92] | +$115,956 [+$125,568] | 48 of 92 [53] | $1,260 [$1,365] | 25 weeks [17] | −$32,080 | −$29,719 [−$24,597] |
| *Stress: 2022–2024* | 1 [51] | +$1,200 [+$65,263]; marked **−$10,757** at the end | **1 of 157** [41] | $8 [$416] | **156 weeks** [32] | **−$39,713** (−66%; bought Jan 18, 2022 at $104.90) | −$39,302 [−$22,736] |

The January 18, 2022 buy finally sold on **July 28, 2025**, 884 trading days (about 3½ years) after it was made.

## If the bot had been switched on at the start of a month: its first year (SIP)

- **36 start months in 2022–2024:**
  - $1,000 weeks in a median **27%** of weeks (range 0%–60%).
  - Realized profit: median about $32,000 (range $0–$71,000).
  - **12 of 36** ended the year below where they started once the open paper loss is counted. Worst drop from peak was up to −$32,000.
  - Switched on in November 2022: no sale for the entire year.
- **9 start months in 2025 (January–September):**
  - $1,000 weeks in a median **74%** of weeks (range 34%–83%).
  - Realized profit: median about $96,000 (range $38,000–$105,000).
  - None ended the year down. Worst drop from peak was up to −$30,000.
- **IEX check:** 2022–2024 had a median of 28%, with 2 of 36 years ending down. 2025 had a median of 75%.

## What this shows

1. **The $1,000 weeks came from LITE's boom, not from the rule alone.** They came about 3 weeks in 4 during 2026 and after spring 2025. In 2022–2024 they came about 1 week in 4, and some years had none.
2. **The downside has no floor.** Each $60,000 buy can sit for months or years. Paper losses of $21,000–$40,000 happened in every period tested, including this year (June–August).
3. **One unlucky day decides the result.** The 2022–2024 result swings from +$65,263 to −$10,757 depending only on whether the January 18, 2022 buy happened. This is path dependence, not a stable edge.
4. **Upside is capped, but downside is not.** $60,000 of LITE simply held from January 2, 2025 ($85.52 at 10:00) would be worth about $646,600 at the September 28 close ($921.66); the bot made about $116,000–$126,000. In falls, the bot held its full $60,000 all the way down anyway. This is hindsight on a stock chosen because it rose. It is not a recommendation to buy and hold.
5. **Limits of this replay:**
   - It uses 5-minute bars, not real fills. It assumes paying 0.1% over the 10:00 price.
   - A touch of the target counts as a sale. Requiring the price to trade 0.1% beyond the target cut 2025–2026 profit by about $3,000.
   - No taxes are included. Alpaca charges no commissions.
   - It covers only LITE, and only 2022–2026.
   - The rule and the size were chosen after seeing 2026, so the 2026 figures are in-sample.
   - There was no point-in-time news data, so news sentiment is untested.

## Status

- The paper bot runs 66 shares from its 10:00 ET run on September 29 (commit 4eb55c0). Its paper account holds $100,000 and has no positions.
- Nothing here justifies live trading at this size. The replay's own worst cases (−$32,000 in 2025, −$40,000 in 2022–2025) are the amounts to plan around.
