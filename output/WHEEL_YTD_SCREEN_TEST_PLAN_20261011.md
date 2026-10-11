# Test #33 plan: a $50k wheel on this year's screened movers (written October 11, 2026, before any 2026 option data for these stocks)

- **Owner's request (Oct 11):** test "pot 2" (a $25–50k wheel next to Plan B) "year to date… targeting stocks that are going bullish up now and still have room to grow like LITE or MU."
- **Avoiding hindsight:** the list is picked using **only data up to Dec 31, 2025**, then the wheel runs **Jan 2 – Oct 9, 2026**. Picking 2026's winners and testing them on 2026 would prove nothing (tests #17 and #19).
- **Not fully blind:** Claude wrote the screen rules on Oct 11, knowing LITE and MU rose a lot in 2026. The rules only use 2025 information, but their design wasn't blind. That's a known bias toward this kind of stock.
- **Paper research only;** no orders. Dollars first, no SPY line. Comparison: holding each stock.
- **Looked at before writing this plan:** the screen's output as of Dec 31, 2025 (prices, 2025 returns and volatility only). No 2026 option data, no wheel results.

## The stock list (frozen)
**Screen:** `research/wheel_screen_v1/screen.py --as-of 2025-12-31`, using daily bars on disk.
- **Filters:**
  - common stock (no funds/ETFs, by Alpaca asset name);
  - raw close ≤ $500;
  - 60-day average dollar volume ≥ $200M;
  - close > 50-day average > 200-day average;
  - 2025 return ≥ +30%;
  - within 15% of the 52-week high.
- **Result:** 87 passed. The **10 most volatile** (60-day realized volatility) are the test list:

| # | Stock | Dec 31, 2025 price | 2025 return | Volatility |
|---|---|---|---|---|
| 1 | PRAX (Praxis Precision Medicines) | $294.74 | +283% | 234% |
| 2 | LITE (Lumentum) | $368.59 | +339% | 97% |
| 3 | RKLB (Rocket Lab) | $69.76 | +174% | 89% |
| 4 | RIVN (Rivian) | $19.71 | +48% | 78% |
| 5 | HL (Hecla Mining) | $19.19 | +291% | 77% |
| 6 | RNA (Atrium Therapeutics) | $72.13 | +148% | 76% |
| 7 | AG (First Majestic Silver) | $16.66 | +204% | 75% |
| 8 | COHR (Coherent) | $184.57 | +95% | 73% |
| 9 | STX (Seagate) | $275.39 | +219% | 69% |
| 10 | CVNA (Carvana) | $422.02 | +108% | 68% |

(MU was #11 at 66% volatility and is not in the list; it was already tested in #32.)

## Rules (main version: "pot 2" as proposed to the owner on Oct 11)
- **Engine:** test #32's code (`research/wheel_lite_mu_v1/`), with test #29's conventions.
- **Accounts:** **ten separate $50,000 accounts**, one per stock, each starting at 15:45 on Jan 2, 2026. Fractional contracts.
- **Sell a put:** the expiration closest to 7 days (4–13; fallback 4–45, counted), delta closest to −0.30 (−0.25 to −0.35), at the bid − $0.03.
- **Take profit:** buy back the first minute the ask ≤ 50% of the sale price.
- **If assigned, sell calls:** same expiration and delta rules, **never below the price paid** (if nothing qualifies, sell nothing that day).
- **Skip earnings:** never sell a contract whose life includes an earnings session (SEC 8-K Item 2.02 filings, the same definition as test #32's `skip_earnings`).
- **End:** Oct 9, 2026, with open options at mid.

## Report (dollars first)
- **Per stock:** ending value, $ per week (average and median), weeks ≥ $1,000, worst week, worst month, worst drop, premiums collected vs true total, assignments, stuck weeks, and holding the stock with $50k from Jan 2, 2026.
- **The typical account:** the average and the median of the 10 accounts, and the best and worst one. This answers "if I had wheeled one of these with $50k this year."
- **$25k view (information):** the same rules with whole contracts only on $25,000. Stocks priced over ~$250 can't be traded and sit in T-bills.

## Pass bar (pre-declared, main version)
- **C1:** the **average** of the ten $50k accounts makes **≥ $1,000 a week** (Jan 2 – Oct 9, 2026).
- **C2:** at least **7 of 10** accounts are profitable.
- **C3:** the **median** account's worst drop is **≤ 25%**.
- **Verdict:** **PASS** if C1–C3 all hold, otherwise **FAIL** (partial passes described in words).

## Information versions
| Version | Change |
|---|---|
| `with_earnings` | earnings allowed (test #32's main rules) |
| `whole_25k` | whole contracts, $25,000 accounts |
| `hold_to_expiry` | no 50% buyback |

## Data and cost
- Databento OPRA `cbbo-1m` via the same engine. Separate folder `outputs/wheel_ytd_data/`.
- **Hard stop $15.** The owner was told "a few dollars"; if the free estimate exceeds $15, ask first.
- Earnings dates from SEC EDGAR (free).

## Checks
- **Unit tests:** the stock list loads exactly as frozen above; the 2026 window; earnings-skip on by default; the settings reach the engine unchanged.
- **An independent verifier** (adapting `research/wheel_lite_mu_v1/verify.py`) that recomputes 12 random contracts from the raw quotes and each account's final value.
- **Provenance manifest.**

## Correction before any result (Oct 11, 2026, after the code check and before the paid run)
- **Stock #6 "RNA":** on Dec 31, 2025 the symbol was **Avidity Biosciences**, not Atrium Therapeutics. Alpaca now shows Atrium's name under the old symbol.
- **The deal:** Novartis bought Avidity for $72.00 cash plus 0.1 Atrium share per share, effective Feb 27, 2026.
- **The list stays frozen.** Avidity is what the screen picked that day.
- **How the account is treated:**
  - It wheels until Feb 25, the last day RNA options traded, with any open option valued at its last mid.
  - Shares convert on Feb 27 at $72 plus 0.1 × Atrium's close. After that the account holds T-bills.
  - Holding RNA gets the same treatment.
  - This makes RNA close to a cash account, which helps C2/C3 and drags C1. This is disclosed and will be shown separately.
- **Earnings timing:** each filing's acceptance time is read from its EDGAR index page, because SEC API time bases differ by company. The session rule is unchanged from test #32.
- **First Majestic (AG):** files 6-K, not 8-K. A 6-K whose headline says "Financial Results" counts as an earnings release.
