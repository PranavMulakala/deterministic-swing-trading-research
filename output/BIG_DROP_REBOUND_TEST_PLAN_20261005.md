# Buy a strong stock after a big one-day drop, hold up to 2 weeks: pre-declared test #19 plan (October 5, 2026)

- **Written and committed before any result.**
- **Done beforehand:** only a count of how many drop events exist (no returns). Research only; no orders. Nothing changes in Plan B, the bots, MNQ or the EP watch.
- **Owner's request:** "Run it 100% please". The idea came from Western Digital falling about 10% on Oct 2 and bouncing back.
- **Evidence behind it:** short-term losers tend to bounce a little (Jegadeesh 1990; Lehmann 1990). Against it: news-driven drops tend to keep sliding (Chan 2003), and the bounce is often eaten by costs.

## The rule (main)
| Step | Rule |
|---|---|
| Big and liquid | Average dollar volume over the 60 trading days **before** the drop ≥ **$200M** (unaffected by splits; no price filter, a test #15 lesson) |
| Strong / in an uptrend | The close **the day before** the drop is above its **200-day average** |
| Big drop | The day's close is **at least 10% below** the previous close |
| Buy | At **that day's close** (the owner's "put money on it before the day ended"); 0.1% cost per side |
| Sell | A standing limit at **+20%**, filled the first later day it trades there (at the open if it gaps above). Otherwise **sell at the close of the 10th trading day** after buying (2 weeks). No stop |
| Size | **10% of the account per trade,** at most 10 positions, cash only. If more stocks qualify than free slots, the **biggest drops go first.** One position per stock |

## Data
- **Stocks:** daily bars on disk for 5,259 US stocks (Alpaca SIP, split- and dividend-adjusted, Jan 2016 – Sep 28, 2026).
- **Benchmark:** SPY from the same files (dividends included).
- **Feasibility count:** 2,162 qualifying drops in 526 stocks. 2016–2019 had only 6–53 a year; 2020–2026 had 84–525 a year (2025: 490; 2026 so far: 525).

## Windows (the owner's post-COVID default)
- **Main (decides the verdict):** Jan 2, 2020 – Sep 28, 2026. Halves: **2020–2022** and **2023–2026**.
- **Stress check:** Oct 2016 (after the 200-day warm-up) – Sep 2026. It's weak, because there were few events before 2020.

## Pass checks (main window)
**Bar A:**
1. Profit factor ≥ **1.3**, with positions open at the end marked.
2. Profitable in **both halves**.
3. Worst drop no worse than **−25%**.

**Bar B (vs holding SPY over the same dates):**
4. A worst drop at least **5 points smaller** than SPY's.
5. Growth ÷ |worst drop| **higher** than SPY's.

**Labels:**
- **PASS (robust):** it also passes all 5 in the stress window.
- **PASS (post-COVID only):** it passes the main window only.
- **FAIL:** any check fails.

**Required before trusting a PASS:** a re-check with delisted stocks. Stocks that fell 10% and later went bust are missing from the data, which flatters this rule. That needs the owner's OK for a download.

**Nothing will be tuned afterwards:** no other drop sizes, filters, targets, holding times or position sizes.

## The owner's question, answered directly
- **How often a +20% gain came within 2 weeks** (the "doubles up" dream), versus how often the stock **fell another 10%** first.
- The win rate, average and median return per trade, and the worst trade.

## Also reported (information only, decided now)
- **Variants:**
  - buy at the **next day's open** instead of the close;
  - **no +20% target** (just hold 10 days);
  - **no uptrend filter;**
  - costs **0.25%** per side.
- **Detail:**
  - profit and loss by year;
  - the most-traded stocks;
  - news-day context is not available, so it isn't reported.
- Provenance manifest.

## Checks
- **Unit tests on hand-built prices:**
  - the signal (drop size, uptrend, liquidity);
  - the +20% fill (including a gap above);
  - the 10th-day exit;
  - slot limits with biggest-drop-first;
  - one position per stock.
- **An independent recount:** for 6 random stocks, every signal and its outcome, from the raw files with separately written code.
