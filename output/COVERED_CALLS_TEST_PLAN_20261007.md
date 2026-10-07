# Test #25 plan: covered calls on SPY (written October 7, 2026, before any result)

- **Owner's request (Oct 7):** "run test 25 on covered calls… do not compare this to holding SPY". This follows Joey's MU trade (+$2,481: the shares lost $5,582, the sold calls made $9,190).
- **Report:** dollars only.
  - money per week, $1,000 weeks, worst week, month and drop;
  - what the sold calls added or cost in dollars.
  - **No SPY comparison line** (owner's instruction).
- **Paper research only.** No orders.

## The question
If you own SPY shares and sell a call against them every month, how many dollars does that make, and do the calls themselves earn their keep?

## Data
- **SPY option quotes:** Databento OPRA closing snapshots, 2016–2025 (`outputs/spy_options_data`, the same data as tests #10 and #24).
- **SPY's price:** from put-call parity, using test #10's helper.
- **Cash interest:** 3-month T-bill rate on idle cash.
- **SPY dividends:** Alpaca corporate actions. 37 dividends, Jun 2016–Dec 2025.
  - The Mar 2016 dividend is missing, which affects the stress years only.

## Rules (main version)
1. **Start:** $100,000 at the close of Jan 2, 2020.
2. **Buy SPY shares:** whole shares only, at the parity price plus $0.01 a share. Leftover cash earns T-bill interest.
3. **Sell calls on each "sell day":** the first day, then each call's expiration day after it settles.
   - **Contracts:** one call per 100 shares owned (whole contracts; any odd-lot shares stay uncovered).
   - **Expiration:** the one closest to **30 days** out (21–45 days; ties go to the later one).
   - **Strike:** the first strike at or above **SPY × 1.02** (about 2% above the price), with a bid above zero.
   - **Fill:** at the **bid**, minus $0.03 a contract.
4. **Settle each call on its expiration day:**
   - **If SPY is above the strike:** the call is settled for its intrinsic value, (SPY − strike) × 100 per contract. This is the same as the shares being called away and bought back at the same price.
     - Paid from cash. If cash runs short, sell whole shares at the parity price to cover it.
   - **Otherwise:** it expires worthless.
5. **Dividends:** credited to cash on the ex-date, for shares held at the prior close.
6. **Account value:** valued each day as shares × SPY + cash − open calls at the mid price × 100.

## Information-only versions (same rules, one change each)
| Version | Change |
|---|---|
| `atm_30d` | strike closest to SPY (at the money) |
| `otm5_30d` | first strike at or above SPY × 1.05 |
| `weekly_otm1` | ~7-day expiration (4–11 days), first strike at or above SPY × 1.01 |
| `mid_fill` | sell at the mid price instead of the bid |
| `shares_only` | never sell calls (the same account without the calls) |

- **Why `shares_only` is here:** it shows the calls' own dollar effect. It isn't the main headline.

## Windows
- **Main window:** Jan 2, 2020 – Dec 31, 2025.
- **Halves:** 2020–2022 and 2023–2025.
- **Stress:** Jan 4, 2016 – Dec 31, 2019, run separately from its own $100,000.

## Pass bar (main version, pre-declared; dollars only)
- **C1:** the sold calls earn their keep: total call P&L > 0 **and** a call profit factor ≥ 1.3.
  - Profit factor = sum of winning calls' P&L ÷ |sum of losing calls' P&L|.
- **C2:** the account is profitable in both halves.
- **C3:** the worst drop from a high is ≤ 25%.
- **Verdict:**
  - **PASS** if C1–C3 all hold.
  - **PASS (post-COVID only)** if they hold in the main window but C1 fails in the stress window.
  - **FAIL** otherwise.

## Checks before results
- Unit tests:
  - the call pick (expiration and strike);
  - settlement above and below the strike;
  - a dividend credit;
  - a cash shortfall covered by selling shares.
- An independent verifier, written separately, that:
  - re-picks random main-version calls from the raw CSVs;
  - re-checks their sale price and expiration value;
  - checks that the trade list adds up to the reported call P&L.
