# GAnderson's "range, fakeout, killshot" (RFK): pre-declared test #23 plan (October 6, 2026)

- **Written and committed before any code or result.** Research only; no orders. Nothing changes in Plan B or the bots.
- **Owner's request:** "yes run test 23 on the RFK setup please" (Oct 6).
- **Source:** GAnderson's X video (Oct 5), "If I could only use ONE system…". Transcript in `GANDERSON_RFK_TRANSCRIPT_20261006.txt`. His examples were QQQ, CoreWeave and Broadcom, and AppLovin was a live call-out.

## The rule (his words turned into exact checks; all daily bars, split-adjusted)
| Step | Rule |
|---|---|
| Universe (at the close before the fakeout day) | Raw close > $10 and 60-day average dollar volume ≥ $50M |
| **Range** | Over the 20 trading days before the fakeout day: the lowest low is L. The range height (highest high ÷ L − 1) is ≤ 25%. **At least 2 "clear lows":** swing lows (lower than the 2 days before and after) within 2% of L |
| **Fakeout day F** | The low undercuts L; the candle is red (close < open); the close is in the bottom 25% of the day's range ("knife at the close") |
| **Killshot day K** (the very next day) | Closes **above F's high**. **Buy at K's close** (he says he waits for the close) |
| Stop | F's low ("risking that low"). Skip if the stop is more than 20% below the entry |
| Target | **1:1** (entry + the distance to the stop). 2:1 is information |
| Exits | Stop or target from the next day on. A gap past either fills at the open. If both are hit the same day, assume the stop. Otherwise sell at the close of the 20th trading day |

## The account
- $100k cash.
- **1% of equity at risk per trade,** at most 10% of equity per stock, at most 10 positions, one position per stock.
- 0.1% slippage per side.
- When there are more signals than room, the most-traded stocks (60-day dollar volume, exact values) go first.

## Data and windows (the owner's post-COVID default)
- **Data:** daily raw and split-adjusted bars for the 5,259 stocks on disk (test #21's download, Nov 2015 – Oct 2, 2026), plus SPY.
- **Main window:** entries Jan 2, 2020 – Oct 2, 2026; halves 2020–2022 and 2023–2026.
- **Stress:** the same rule from Jan 2016.
- **Survivorship:** only stocks listed in 2026, which flatters long setups.

## Pass checks (main window)
**Bar A:**
1. Profit factor ≥ 1.3.
2. Profitable in both halves.
3. Worst drop ≤ 25%.

**Bar B, vs holding SPY over the same dates:**

4. A worst drop at least 5 points smaller.
5. Growth ÷ |worst drop| higher.

**Labels:**
- **PASS (robust):** it passes, and the 2016–2026 run also beats SPY on growth ÷ worst drop.
- **PASS (post-COVID only).**
- **FAIL.**

**Nothing will be tuned afterwards.**

## Also reported (information only)
- **Every signal on its own,** with no account limits:
  - how often 1:1 comes before the stop (break-even is about 50%);
  - the average result in "R" (multiples of the risk).
- **A plain baseline:** the same entry, stop and target on any liquid stock's close above the previous day's high, after a red day that closed in its bottom 25%, but **without** the range and undercut conditions. This shows whether the range and fakeout add anything.
- **Variants:** a 2:1 target; requiring F to close below L; buying at K's next open.
- **Yearly results;** the most-traded stocks; his examples (Broadcom Oct 2, AppLovin Oct 5) if they're in the data window.

## Checks
- **Unit tests on hand-built bars:** the range, clear lows, fakeout, killshot, exits (gaps, same-day both) and sizing.
- **An independent recount:** signals for 10 random stocks, and the account re-chained from the trade list.
