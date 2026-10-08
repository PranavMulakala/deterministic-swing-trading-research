# Test #28 results: OWLS Capital alerts, Sep 8 – Oct 8, 2026, scored as a follower

- **Plan:** `OWLS_ALERTS_BACKTEST_PLAN_20261008.md`, committed before any price check.
- **Method:**
  - 886 alert messages from the owner's paid all-alerts feed were turned into 362 option positions by three helper passes.
  - Each position was priced with Alpaca 1-minute option bars (free, including SPX index options).
  - **274 positions scored.** Not scored: 71 with no trade near the alert time (the contract couldn't be matched or was illiquid) and 17 that weren't scorable (stock trades, spreads, positions opened before the window).
  - Raw messages and trade lists stay private in `outputs/owls_alerts/` (gitignored).
- **Report:** dollars only, **$1,000 per alert**. Research, not advice.

## Main rule (pre-declared): buy at the high of the minute after the alert, sell at the low of the minute after each exit post
| Analyst | Alerts | Follower total | Per alert | Win % | Posted avg % | Follower avg %, same trades | Exit posted |
|---|---|---|---|---|---|---|---|
| ab | 19 | −$1,775 | −$93 | 37% | +76% | +1% | 26% |
| eli-alerts (SPX 0DTE) | 23 | −$2,578 | −$112 | 48% | +29% | −5% | 100% |
| muggzone-options | 78 | −$17,726 | −$227 | 23% | +55% | +2% | 31% |
| tt | 20 | −$4,595 | −$230 | 35% | +112% | +23% | 50% |
| jon-and-kian | 3 | −$1,043 | −$348 | 0% | +22% | −7% | 0% |
| eva | 6 | −$2,254 | −$376 | 17% | −17% | −38% | 100% |
| shabs-sky-alerts (SPX 0DTE) | 106 | **−$45,570** | **−$430** | 22% | +142% | +49% | 16% |

**Verdict:** under the pre-declared rule, **no analyst made money for a follower** in this month.

## Information only (written after the main result): fill and "runner" assumptions
- **Mid-of-minute fills** (minute close in and out):
  - tt +$71/alert (55% wins); eli +$26 (65%); ab −$27; mugg −$140; shabs −$312; eva −$305.
- **Mid fills, and runners sold at the last trim** instead of being held when no final exit was posted:
  - ab +$237 (74%); tt +$113 (60%); eli +$26; mugg −$68; shabs −$171; eva −$305.
- **Entry slippage:** the strict rule pays on average 10% more than that minute's close on Shabs' 0DTE entries.

## What it means
1. **Posted results overstate what a follower gets.** On the same trades:
   - Shabs posted +142% vs +49% for a follower;
   - AB +76% vs +1%;
   - TT +112% vs +23%;
   - Mugg +55% vs +2%.
   - Posts quote the best moment; a follower buys a minute later and sells a minute after the exit post.
2. **Shabs (the 0DTE lotto channel) is the worst for followers.**
   - 106 alerts in a month.
   - **66 got no exit post**, so 0DTE runners mostly expired worthless.
   - The follower result is negative under every assumption: −$171 to −$430 per alert, $18k–46k lost on $1,000 per alert.
3. **Mugg (78 alerts) is negative under every assumption** too.
4. **The only positive results need the friendlier assumptions** (fills at mid, runners sold with the last trim):
   - **AB** (swings with scaled trims), **TT** and **Eli** (SPX, posts every exit).
   - Their samples are small (19–23 alerts).
5. **Jon & Kian and Eva are mostly longer-dated swings.** Few were scorable within a month (illiquid contracts, many still open), so this test says little about them.

## Limits
- **One month is a small sample.**
- **Reading free-text messages into trades involves judgment.** About 29 exit posts couldn't be matched to an entry.
- **Some alerts couldn't be priced:** 71 had no trade within 5 minutes, which hits long-dated swing alerts hardest.
- **Strict fills are harsh on 0DTE;** mid fills are more forgiving than a phone-notification follower would really get. The truth for a fast follower is likely in between.
