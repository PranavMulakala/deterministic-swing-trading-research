# "Stocks in Play" opening-range breakout (Zarattini, Barbon & Aziz 2024): pre-declared test #21 plan (October 5, 2026)

- **Written and committed before any data was downloaded and before any result.** Research only; no orders. Nothing changes in Plan B, the bots, MNQ or the EP watch.
- **Owner's request:** "Can you also do a test 21 simultaneously" (Oct 5). It comes from the owner's observation that morning traders focus on **volume** and on finding the right stock.
- **The paper:** "A Profitable Day Trading Strategy For The U.S. Equity Market" (SSRN 4729284, Feb 2024; Swiss Finance Institute working paper). 2016–2023, over 7,000 US stocks.
  - **Reported for the top-20 version:** **+1,637% total, 41.6% a year, Sharpe 2.81, worst drop 12%**, after $0.0035/share commissions, with up to 4× leverage.
  - It's a working paper, not peer-reviewed.
  - **Our window 2024 – Oct 2026 is new data the paper never saw**, a genuine forward check of a published result.

## The rule (as published)
| Step | Rule |
|---|---|
| Universe (each morning, known before trading) | Opening price **> $5**; average volume over the previous 14 days **≥ 1M shares**; 14-day average true range (ATR) **> $0.50**. All in **raw** (unadjusted) prices |
| "In play" | **Opening relative volume** = the 9:30–9:35 volume ÷ the average 9:30–9:35 volume over the previous 14 days. It must be **≥ 1.0 (100%)**. Take the **20 highest** each day |
| Direction | First 5-minute candle closes **up → long**; **down → short**; unchanged → no trade |
| Entry | A stop order at the first candle's **high** (long) or **low** (short): filled when a later 5-minute bar trades through it, at that level or at the bar's open if it gaps past |
| Stop | **10% of the 14-day ATR** away from the entry |
| Exit | At the stop, or at the **day's close** |
| Size | **1% of the account at risk per trade:** shares = 1% of equity ÷ (0.1 × ATR) |

## Our account conventions (decided now)
- **Cash only (main):** each position is capped at **1/20 of equity (5%)**, so all 20 fit without borrowing. That's the QuantConnect re-creation's cap.
- **Information:** the paper's **4× leverage** version (cap 20% per position).
- **Sides:**
  - **Main verdict: long trades only.** The owner's stock accounts can't short; the same convention as tests #8 and #18.
  - **Information:** both sides together (the paper's version) and shorts alone.
- **Costs:** **$0.0035/share** commission (the paper's) **plus 0.01% slippage per side** (our intraday convention). Information: before costs, and with 0.05% slippage.
- **Same-bar ambiguity:** if the entry bar also reaches the stop, **assume the stop**. The rate and the flip are reported.
- **Survivorship:** prices come from the 5,259 stocks listed in 2026, so delisted stocks are missing. That's stated as a bias.

## Windows
- **Main (decides the verdict):** Jan 2, 2020 – Oct 2, 2026 (the owner's post-COVID default). Halves: **2020–2022** and **2023–2026**.
- **Information:**
  - **The paper's own period 2016–2023** (did we reproduce it?);
  - **2024 – Oct 2026 alone** (after the paper).

## Pass checks (main window, long-only, cash account)
**Bar A:**
1. Profit factor ≥ **1.3**.
2. Profitable in **both halves**.
3. Worst drop no worse than **−25%**.

**Bar B (vs holding SPY over the same dates):**
4. A worst drop at least **5 points smaller** than SPY's.
5. Growth ÷ |worst drop| **higher** than SPY's.

**Labels:**
- **PASS (robust):** it also beats SPY on growth ÷ worst drop in 2024–2026 alone.
- **PASS (2020–2023 only):** it passes the main window but not 2024–2026 alone.
- **FAIL:** any check fails.

**Nothing will be tuned afterwards:** no other ranges, stops, thresholds, stock counts or filters.

## Data (needs the owner's OK; free; Alpaca SIP, the same source as tests #8, #15 and #16)
1. **Raw daily bars**, Dec 2015 – Oct 2026, for the 5,259 stocks: about 1,400 requests.
2. **The 9:30–9:35 bar** for every stock passing the daily filters, every day: about 45,000 requests. This is the slow part, about 4–5 hours in the background, paced under the rate limit.
3. **Full-day 5-minute bars** for each day's top 20: about 2,700 requests.

**In total:** about 49,000 requests, **~5 hours** in the background, about **100–150 MB** stored (gitignored). Resumable.

## Checks
- **Unit tests on hand-built bars:**
  - the filters;
  - relative volume;
  - top-20 ranking;
  - direction;
  - stop entries, including gaps;
  - the ATR stop;
  - the close exit;
  - same-bar handling;
  - sizing with the cap.
- **An independent recount** of 15 random days: selection and trades, from the raw files with separate code. Plus the account re-chained from the trade list.
