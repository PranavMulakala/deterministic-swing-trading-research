# Owner's tweets, Oct 6, 2026: SPY 790-call flow, the "9 waves" list, and GAnderson's RFK setup

**Read through the fxtwitter mirror** (x.com is blocked in the browser panel); replies weren't readable. The video was transcribed with Whisper medium (`GANDERSON_RFK_TRANSCRIPT_20261006.txt`) and checked against frame sheets.

## 1. SPY $790 calls expiring Oct 14 (kiantrades, "top blast?"; snorlax_uw / Unusual Whales, 187k views)
- **The trade:** about 60–65k contracts were bought at roughly $1.06–1.08 when SPY was near $778. That's about $7M in premium, 8 days to expiry, and **82× the existing open interest**, so it's a new position.
- **To profit at expiry, SPY needs to be above about $791,** roughly +1.5% in 6 trading days.
- **Today (Alpaca's free indicative options data):** the calls opened at $1.04, briefly hit $1.88, and closed at $1.12. SPY closed at $779.09.
- **What it is and isn't:**
  - It's one large trader's view, or one leg of a larger position (a hedge, or a sold stock or futures position we can't see).
  - It isn't a signal a follower can use. By the time it's posted, the price has already moved.
  - Research on option volume predicting returns (Pan & Poteshman 2006) found the information is short-lived. Copying published flow arrives late.
  - Most short-dated calls expire worthless.

## 2. "The real 10x stocks are hidden in these 9 waves" (Haywhykomo)
- **What it is:** a list of about 45 of the most popular AI-theme stocks, already up a lot. It's a hindsight list, not a method; no rule says when to buy or sell.
- **The same day it was posted,** wave 2 had a bad day: Seagate −9%, Western Digital −7%, on Toshiba's drive expansion. Theme lists don't protect against that.
- **Our related tests:**
  - #17: picking the strongest volatile stocks gave a −84% worst drop.
  - #20: the "LITE fingerprint" lost to SPY.

## 3. GAnderson, "range, fakeout, killshot" (RFK), daily candles
- **The rule as described:**
  1. A range with several clear lows.
  2. Price undercuts those lows and closes near the day's low, a bearish "fakeout".
  3. The next day closes above that bearish day's high: buy at that close.
  4. The stop goes at the bearish day's low; the target is 1:1 or 2:1.
  - He says about 60% of his entries use it.
- **His examples:**
  - QQQ, CoreWeave and Broadcom, all cherry-picked winners.
  - **Broadcom** (entry Oct 2 at $355.14, stop $343.29) is at $375.81 on Oct 6, so it has passed 1:1.
  - **His live AppLovin call** (signal Oct 5 at $281.97, stop $266.84) is at $278.78, down 1.1% on day one.
- **Our evidence:**
  - It's a daily version of "sweep and reclaim".
  - Test #22 H4: a sweep of yesterday's low that closes back above did no better the next day than nearby prices (0.00%).
  - The CRT tests (#8, #9) failed on SPY/QQQ.
  - RFK adds more conditions (a multi-low range, a close near the low, then a close above the prior high), so it's not identical. It's precise enough for a proper pre-declared test on our daily data for 5,259 stocks.
