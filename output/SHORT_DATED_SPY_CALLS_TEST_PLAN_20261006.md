# Buying short-dated SPY calls every week: pre-declared test #24 plan (October 6, 2026)

- **Written and committed before any code or result.** Research only; no orders.
- **Owner's request:** "I am looking into buying shorted-dated calls … can we test … if we placed short calls in the past, how would we do" (Oct 6). It follows the $7M SPY 790-call flow post.
- **Note:** following *flow* posts can't be tested; we have no historical flow data. This tests the plain habit of buying short-dated SPY calls.

## Data
- **The SPY option chains already on disk:** Databento OPRA quote snapshots at 10:30 and the close, every trading day 2016–2025 (tests #1 and #10). **There's no 2026 data,** so the window ends Dec 31, 2025.
- **SPY's price** comes from put-call parity on each snapshot, as in test #10. The T-bill rate is the same file as #10.

## The rule
| Step | Rule |
|---|---|
| When | Every week, on its first trading day, at the **close** snapshot |
| Which call | The expiration closest to **7 calendar days** out (4–11 days; ties go to the later date), at the **strike closest to SPY's price** (at the money) |
| Price paid | **The ask** (a realistic fill), plus $0.03 per contract in fees (as in #10) |
| Size | **2% of the account per week** (whole contracts; skip if not even one) |
| Exit | **Hold to expiration.** Its value is the intrinsic value (SPY − strike, or 0) from the parity price at that day's close snapshot |
| Idle cash | Earns the 3-month T-bill rate (as #10) |

## Windows
- **Main:** Jan 2020 – Dec 2025; halves 2020–2022 and 2023–2025.
- **Stress:** 2016–2019, as a separate run.

## Pass checks (main window, vs holding SPY over the same dates)
**Bar A:**
1. Profit factor ≥ 1.3 on the call trades.
2. Profitable in both halves.
3. Worst drop ≤ 25%.

**Bar B:**

4. A worst drop at least 5 points smaller than SPY's.
5. Growth ÷ |worst drop| higher than SPY's.

**Labels:**
- **PASS (robust):** it also beats SPY on growth ÷ worst drop in 2016–2019.
- **PASS (post-COVID only).**
- **FAIL.**

**Nothing will be tuned afterwards.**

## Also reported (information only)
- **The plain facts of buying these calls:**
  - the share that expire worthless;
  - the average and median result per call;
  - the best and worst weeks;
  - the total dollars.
- **Variants:**
  - **1.5% out of the money** (like the 790 call);
  - fills at the **mid** instead of the ask;
  - **5% and 10%** of the account per week;
  - **sell at +100%:** sell at the close-snapshot bid on the first day it's worth double;
  - **all-in:** what $1,000 a week would have made in total.

## Checks
- **Unit tests on a hand-built chain:** expiration and strike choice, sizing, ask fills and fees, settlement and the take-profit.
- **An independent recount:** 10 random weeks' trades from the raw files, and the account re-chained.
