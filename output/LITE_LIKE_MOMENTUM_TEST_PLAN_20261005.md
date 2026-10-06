# Can picking the strongest LITE-like stocks beat just holding SMH? Pre-declared test #17 plan (October 5, 2026)

- **Written and committed before any result.**
- **Done beforehand:** only a count of how many stocks met the "LITE-like" bar each month (no returns).
- Research only; no orders. It changes nothing in Plan B, the bots, MNQ or the EP watch.
- **Owner's request:** "plan test 17 … and let's see" (Oct 5). Window: post-COVID (the owner's default from Oct 5), with the longer history reported as a stress check.

## The idea in plain words
Every month, find the big stocks that swing like LITE. Of those, own the 5 that rose most over the last 6 months. Re-pick monthly. Is that better than simply holding SMH, the chip ETF?

This is "momentum" applied to volatile stocks. Momentum has real independent research behind it (Jegadeesh & Titman 1993 and many since). It's also known for sudden crashes, worst in volatile stocks (Daniel & Moskowitz, "Momentum Crashes", 2016).

## The rule (main)
| Step | Rule |
|---|---|
| When | Signals at each month's last close; trades at the **next trading day's open** (so no look-ahead) |
| "Big" | Average dollar volume over the prior 60 trading days ≥ **$300M** (unaffected by splits, a test #15 lesson; no price filter) |
| "Swings like LITE" | Average absolute daily move over the prior 60 trading days ≥ **4%** (LITE today: 4.9%) |
| "Strongest" | The highest **6-month return** (126 trading days to the month-end close), which **must be above 0** |
| Hold | The top **5**, **equal weight** (20% each). **Empty slots are held in SMH** |
| Rebalance | Monthly: sell what dropped out, buy what came in, reset to equal weights |
| Costs | 0.1% per side on every dollar traded |
| No stops | Positions are only changed at the monthly rebalance |

## Data
- **Stocks:** the daily bars on disk (5,259 US stocks, SIP, adjusted, Jan 2016 – Sep 28, 2026).
- **SMH, SPY, QQQ:** fresh Alpaca SIP daily bars (adjusted, dividends included).
- **Feasibility count** (stocks meeting both bars each month):
  - 2016–2019: 0–3, so this period is mostly SMH by construction;
  - 2020–2026: a median of 4 (2023) to 42 (2026) a month.

## Windows
- **Main (decides the verdict):** first trade at the open of **Jan 2, 2020**, last value at the **Sep 28, 2026** close.
- **Stress check:** first trade at the open of **Oct 3, 2016**, through the same end date. It's weak here, because before 2020 almost no stock qualified and the strategy mostly holds SMH.

## Pass checks (main window, all must hold, vs holding SMH from the same open)
1. **More growth:** a yearly growth rate above SMH's.
2. **More growth per unit of pain:** yearly growth ÷ |worst drop| above SMH's.
3. **Not one lucky stretch:** beats SMH in both halves, **2020–2022** and **2023 – Sep 2026**.

**Outcome labels:**
- **PASS (robust):** all 3 hold, and the stress-check run also has better growth ÷ worst drop than SMH.
- **PASS (post-COVID only):** all 3 hold, but the stress check doesn't.
- **FAIL:** any check fails.

**Required before anyone trusts a PASS:** the data only has stocks still listed in 2026. Volatile stocks that later delisted (bankruptcies, failed SPACs, meme collapses) are missing, which **flatters** this rule. A PASS must be re-checked with delisted stocks added. That needs a download, so the owner's OK first.

**Nothing will be tuned afterwards:** no other thresholds, lookbacks, number of stocks or fill rules.

## Also reported (information only, decided now)
- **Variants:**
  - top **3** instead of 5;
  - **12-1 month** momentum (the academic standard);
  - **no** "must be above 0" filter;
  - costs 0.25% per side.
- **Comparisons:** vs SPY and QQQ.
- **Detail:**
  - yearly returns;
  - worst month;
  - share of months beating SMH;
  - months with empty slots held in SMH;
  - the most-held stocks;
  - turnover.
- Provenance manifest.

## Checks
- **Unit tests on hand-built prices:**
  - eligibility;
  - ranking with the "above 0" filter and SMH filling;
  - trading at the next open with costs;
  - marking value between rebalances.
- **An independent recount**, with separately written code:
  - the picks for 6 random months;
  - the whole value path from month-to-month open prices, matching within 0.5%.
