# Test #32 plan: the weekly wheel on LITE and MU (written October 10, 2026, before any LITE/MU option data)

- **Owner's request (Oct 10):** "do test 32 on LITE and MU". The question: can selling weekly puts (and then calls, once assigned) on the owner's own two stocks make **$1,000 a week**, and what's the worst stretch?
- **LITE options:** the owner reports (Oct 10) that their father checked with Lumentum and LITE options are fine for them.
- **Paper research only;** no orders. Dollars first. **No SPY line** (owner's instruction). Comparison: just holding the same stock.
- **Looked at before writing this plan:** nothing about LITE/MU options. Test #29 (the five-stock wheel) is still running; none of its results have been seen.
- **Engine:** the same code as test #29 (`research/wheel_test_v1/`, committed in ef5e22b, not modified), with the settings below. Test #29's judgment calls (15:45 decision time, Black-Scholes delta from the mid, half days skipped, fills, splits, dividends, T-bill interest on cash) carry over unchanged.

## Data
- **Stocks:** Alpaca SIP raw daily bars, 15:45 one-minute bars, splits and dividends (neither stock split in 2020–2026; MU pays a small dividend).
- **Options:** Databento OPRA.PILLAR `cbbo-1m`, as in test #29: the 15:45 chain on days a sleeve sells, and each sold contract's minutes until expiration.
- **Separate data folder and budget:** `outputs/wheel_lite_mu_data/`, **hard stop $12** (the owner was told "a few dollars"; if the free cost estimate comes in above $12, ask the owner first).
- **Cash interest:** the same T-bill series as test #29.

## Rules (main version)
1. **Two separate $100,000 accounts**, one for LITE and one for MU, starting at 15:45 on Jan 2, 2020. Results are reported per $100,000, so they scale: at $77,400, multiply by 0.774.
2. **Fractional contracts** (as in test #29), so each account always uses its full $100,000. The whole-contract version is reported too: one LITE or MU contract now costs about $100,000–110,000.
3. **Sell a put (no shares held):** the expiration closest to **7 days** away (4–13 days; if none, the nearest within 4–45, counted), the strike below the price with delta closest to **−0.30** (allowed −0.25 to −0.35), at the bid minus $0.03 a contract.
4. **Take profit at 50%:** buy it back the first minute the ask is **≤ 50% of the sale price**, at the ask plus $0.03. Sell the next one at 15:45 that day, or the next day if after 15:45.
5. **At expiration:** if the close is below the put strike, buy the shares at the strike; if not, it expires worthless.
6. **Shares held: sell a covered call** with the same expiration rule, delta closest to **0.30** (0.25–0.35), and **a strike at or above the price paid for the shares**: never lock in a loss (ScottishTrader's rule). If no call qualifies, sell nothing that day and keep the shares.
7. **At expiration:** if the close is above the call strike, the shares are sold at the strike; back to step 3.
8. **End:** Oct 9, 2026, with open options valued at mid.

## Comparison
**Just holding:** $100,000 of LITE and $100,000 of MU bought at 15:45 on Jan 2, 2020, dividends to cash.

## Windows
- **Main:** Jan 2, 2020 – Oct 9, 2026. Halves: 2020–2022 and 2023 – Oct 9, 2026.
- **Recent view (information):** Jan 2, 2025 – Oct 9, 2026, the owner's preferred LITE window.

## Report (dollars first)
- **Per account and combined:**
  - premiums collected vs the true total (premiums − buybacks + share gains and losses + dividends + interest);
  - average and median $ per week, % of weeks ≥ $1,000, worst week, worst month, worst drop in $ and %;
  - times assigned and called away;
  - weeks spent stuck holding shares with no call allowed (rule 6);
  - fallback expirations.
- **Holding:** the same dollar numbers.

## Pass bar (pre-declared, main version)
- **C1:** the two accounts together ($200,000) average **≥ $1,000 a week**.
- **C2:** each account is profitable in **both halves**.
- **C3:** each account's worst drop is **≤ 25%**.
- **Verdict:** **PASS** if C1–C3 all hold, otherwise **FAIL** (partial passes described in plain words). Holding is shown next to it as information, not as a check.

## Information-only versions (one change each)
| Version | Change |
|---|---|
| `no_basis_floor` | calls at delta 0.30 even below the price paid |
| `delta_20` | target delta 0.20 (0.15–0.25): further away, less premium |
| `hold_to_expiry` | no 50% buyback |
| `skip_earnings` | never sell a contract whose life includes an earnings date (from SEC 8-K Item 2.02 filing dates, free) |
| `whole_contracts` | whole contracts only; an account that can't afford one sits in T-bills |

## Checks before results
- **Unit tests:**
  - the 50% buyback;
  - the call strike floor, including the "nothing qualifies" day;
  - the earnings skip;
  - the settings reaching the shared engine unchanged.
- **The test #29 verifier approach** applied to 12 random contracts (6 per stock), recomputed from the raw quote files.
- **Provenance manifest.**
