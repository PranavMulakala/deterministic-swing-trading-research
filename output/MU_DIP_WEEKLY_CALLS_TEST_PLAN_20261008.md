# Test #27 plan: buy ~1-week MU calls on mornings MU opens down 2%+ (written October 8, 2026, before any option data)

- **Owner's idea (Oct 8):** "buy 1-week MU calls on mornings when MU opens down 2%+, sell at +100% or at Friday's close… go back… since 2020."
- **Download approved:** "Yes, approve" (Databento, estimated under $1, hard stop at $5).
- **Paper research only;** no orders. Dollars only, with no SPY comparison line (owner's instruction).
- **What was looked at before writing this plan:** only the count of signal days from MU's daily prices (182 since 2020). No option prices and no outcomes.

## Data
- **MU stock prices:** Alpaca SIP daily bars (signals, expiration-day closes) and 1-minute bars (MU's price at 10:00 ET). MU had no stock split in 2020–2026.
- **MU option quotes:** Databento OPRA.PILLAR `cbbo-1m` (best bid/ask each minute).
  - The whole MU chain in the 10:00–10:01 ET minute of each trade day, used to pick the contract.
  - Then the chosen contract alone, from 10:01 on the entry day through 16:00 on its expiration day.

## Rules (main version)
1. **Signal:** MU's regular-session open ≤ the prior close × 0.98 (opened down 2% or more).
2. **Contract at 10:00 ET:**
   - **Type and expiration:** a call whose expiration is closest to **7 calendar days** away (within 4–11 days; ties go to the later one).
   - **Strike:** the strike closest to MU's 10:00 price (ties go to the higher strike).
   - **Quote:** it must have a bid and an ask above zero in that minute.
3. **Entry:** pay the **ask** at 10:00, plus $0.03 a contract.
4. **Size:** **$1,000 per trade.** Fractional contracts are used so every trade risks the same dollars. The average whole-contract cost is reported too.
5. **Exit, whichever comes first:**
   - **Target:** the first minute (from 10:01 on the entry day) where the **bid ≥ 2 × the entry ask**. Sell at that bid, minus $0.03 a contract.
   - **Otherwise, at expiration:** the call is worth its intrinsic value at MU's close on its expiration day, max(MU close − strike, 0). In practice that's "sell at Friday's close".
6. **Overlap:** every signal is its own trade, even if an earlier one is still open.
7. **Excluded:** trades whose expiration is after Oct 7, 2026, since the result isn't known yet.

## Comparison: the same rule on ordinary mornings
**200 random non-signal trading days** in Jan 2, 2020 – Sep 30, 2026 (random seed 27), with exactly the same contract, entry and exit rules. This answers whether the "down 2%" morning matters, or whether buying a weekly call any morning would do as well.

## Windows
- **The whole period:** Jan 2, 2020 – Oct 7, 2026.
- **Halves:** 2020–2022 and 2023–2026.

## Report (dollars first)
- **Totals:** trades, total P&L, average and median per trade, and P&L by year.
- **Hit rates:** % that win, % that hit +100%, % that expire worthless.
- **Extremes:** the best and worst trade, and the longest losing streak.
- **The same numbers for the comparison days.**

## Pass bar (pre-declared)
- **C1:** total P&L > 0 after costs.
- **C2:** both halves profitable.
- **C3:** average P&L per trade > the comparison days' average per trade.
- **Verdict:** **PASS** if C1–C3 all hold, otherwise **FAIL**.

## Information-only versions
| Version | Change |
|---|---|
| `target_50` | sell at +50% instead of +100% |
| `no_target` | hold every call to expiration |
| `gap_3pct` | only mornings down 3% or more |
| `two_week` | expiration closest to 14 days (11–18) |

## Checks before results
- **Unit tests:**
  - contract pick: expiration and strike ties;
  - target fill at the first qualifying minute;
  - expiration value;
  - $1,000 sizing.
- **An independent verifier** that re-reads the raw quote files for 12 random trades and recomputes the contract, entry, exit and P&L.
