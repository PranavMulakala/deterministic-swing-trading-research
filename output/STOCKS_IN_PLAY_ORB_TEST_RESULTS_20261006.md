# Test #21: "Stocks in Play" 5-minute opening-range breakout (Zarattini, Barbon & Aziz 2024): results (October 6, 2026)

- **Plan:** [STOCKS_IN_PLAY_ORB_TEST_PLAN_20261005.md](STOCKS_IN_PLAY_ORB_TEST_PLAN_20261005.md), committed (adb90c8) before any data.
  - Implementation notes were added with the code, before any result (11298f8).
  - The **1-minute re-check** was declared after the 5-minute result and before any 1-minute data (06371e3).
- **Code:** `research/stocks_in_play_orb_v1/`:
  - `rules.py`, `data.py`, `fetch.py`, `backtest.py` (5-minute run);
  - `fetch1m.py`, `backtest1m.py` (1-minute re-check);
  - 11 unit tests;
  - `verify.py`, an independent recount.
  - All committed before each run (4296e5a, f9ccae6, 87196fc, 11298f8, 06c2b3b, fb29645).
- **Data:** Alpaca SIP, Jan 2016 – Oct 2, 2026, for the 5,259 stocks on disk (two bitcoin files in that folder were excluded). About 15,000 requests in total (the plan estimated 49,000; batching 400 stocks per request cut it):
  - raw and split-adjusted daily bars;
  - each stock's 9:30–9:35 bar on every day it could qualify (2.6M stock-days);
  - full-day 5-minute bars and then 1-minute bars for each day's top 20 (53,759 picks).
  - 630 MB on disk (gitignored), more than the plan's 100–150 MB estimate.
- **Results:**
  - `output/stocks-in-play-orb-test-results.json` (5-minute run);
  - `output/stocks-in-play-orb-1min-recheck-results.json` (1-minute re-check);
  - both with provenance manifests.
- **Checks:**
  - 11 unit tests pass.
  - **The independent recount matched both runs exactly:**
    - the top 20 on 15 random days, rebuilt from the raw files;
    - all 125 trades on those days;
    - the whole account ($13,303 and $33,729);
    - SPY.

## Verdict: FAILED, on 5-minute bars and on the 1-minute re-check

| Jan 2020 – Oct 2, 2026, long only, cash account | $100k became | Per year | Worst drop | Profit factor | Checks passed |
|---|---|---|---|---|---|
| **5-minute bars, as declared** (unclear entry bar = stopped) | **$13,303** | −25.9% | −86.8% | 0.44 | 0 of 5 |
| 5-minute bars, unclear entry bar = not stopped (info) | $619,321 | +31.1% | −4.4% | 1.56 | 5 of 5 |
| **1-minute re-check, as declared** (decides) | **$33,729** | −14.9% | −67.8% | 0.71 | **0 of 5** |
| 1-minute, unclear entry minute = not stopped (info, the best case) | **$242,375** | +14.1% | −6.3% | 1.26 | 4 of 5 (profit factor under 1.3) |
| **Holding SPY** | **$260,559** | +15.3% | −33.8% | | |

By the re-check's pre-declared reading ("fails both → FAIL"), **test #21 fails**:
- **The rule as declared loses two-thirds of the account** on 1-minute bars.
- **Even the best case, where every unclear minute goes our way, ends $18k below SPY** and misses the 1.3 profit-factor bar. Its only advantage is a much smaller worst drop.

## Why the result swings so much: the stop is tinier than one bar
- **The paper's stop is 10% of the stock's average daily range,** a median of **0.39% of the price.** These are the day's most active stocks, so a single minute often moves more than that. Among trades that ended on their entry minute, that minute's median range was **1.07%**.
- **So the minute that triggers the buy often also touches the stop, and bars can't show which came first:**
  - **5-minute bars:** 79% of trades ended on their entry bar under the declared rule. In 45% of those, the only "touch" was the bar's **opening price, before the buy**.
  - **1-minute bars:** that fell to 53% of trades, but three-quarters of those were still unresolved (table below).
- **Finer data moved both versions toward each other:** the pessimistic one from $13k to $34k, the optimistic one from $619k down to $242k.
  - The true answer lies somewhere between, and only trade-by-trade (tick) data could narrow it further.
  - **Even the optimistic edge of that range doesn't beat SPY.**

| Long trades ending on their entry bar | 5-minute | 1-minute |
|---|---|---|
| All trades | 13,892 | 13,898 |
| Ended on the entry bar (declared rule) | 11,026 (79%) | 7,336 (53%) |
| …certain (bought at the open then fell through, or closed below the stop) | 3,694 | 1,797 |
| …the bar **opened** below the stop (the touch was probably before the buy) | 4,994 | 3,873 |
| …dipped below the stop, order unknown | 2,338 | 1,666 |

## Did we reproduce the paper?
The paper reports **+41.6%/yr, 2016–2023** for its version: both directions, top 20, up to **4× leverage**.

| The paper's version on our data | Unclear minutes = stopped | Unclear minutes = not stopped |
|---|---|---|
| 1-minute, 2016–2023 | $100k → $105 (wiped out) | (not run for this window) |
| 1-minute, 2020 – Oct 2026 | $100k → $72 | $100k → **$35.4 million** (+139%/yr) |
| 1-minute, 2024 – Oct 2026 (after the paper) | $100k → $1,170 | |

- **With 4× leverage, the answer is "wiped out" or "absurdly rich"** depending only on who wins the race inside a single minute. The paper's +41.6% sits inside that range, so our data can neither confirm nor reject it.
- **What decides it, the fill on a stop order in a fast-moving stock, is where real trading costs bite hardest.**
  - Our main run already charges $0.0035/share plus 0.01% slippage per side.
  - With 0.05% slippage, the declared 1-minute version falls to **$19,613**.
  - Before any costs, it's still only **$46,313**.

## Information only (1-minute re-check unless noted)
| Version | $100k became | Worst drop |
|---|---|---|
| Both directions (cash, 5% per stock) | $10,260 | −91% |
| Shorts only | $29,663 | −72% |
| Long, 4× leverage | $1,156 | −99% |
| Long, before costs | $46,313 | −56% |
| Long, 0.05% slippage | $19,613 | −81% |
| Long, 2016–2023 (the paper's years) | $39,716 vs SPY $269,645 | −60% |
| Long, 2024 – Oct 2026 (after the paper) | $57,182 vs SPY $168,172 | −44% |

- **Activity:**
  - about 8 long trades a day;
  - 9% winners (the declared version) to 14% (best case);
  - most-traded: HTHT, FUTU, WMG, KNX, DT, ZM, XP, GFL, MDB, GME.
- **Data checks:**
  - 414 picks had an unchanged first candle (no trade);
  - 6 (5-minute) and 9 (1-minute) picks had no later bars;
  - 6 entries were too small for one share.
- **Survivorship:** delisted stocks are missing, which mostly flatters a long-only rule.

## What this means
- **The "morning volume" idea is right about where the action is:** the stocks with unusual opening volume move a lot.
- **This rule doesn't turn that into money a cash account can keep.** Its stop is so tight that the result depends on what happens inside the first minute after the buy.
  - The cautious reading loses most of the account.
  - The generous reading still trails SPY.
  - The paper's headline needs 4× leverage, shorting, and the generous reading all at once.
- **This matches the day-trading evidence from earlier:** most retail day traders lose (Chague et al. 2019; Barber et al. 2014).
- **Nothing changes in Plan B, the bots, MNQ or the EP watch.**

**Score:** 21 pre-declared tests. Only #14 passed, and it ties the market since 2000.
