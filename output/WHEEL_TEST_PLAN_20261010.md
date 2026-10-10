# Test #29 plan: the Reddit "wheel" on AVGO, CRM, AMZN, META, CBOE (written October 10, 2026, before any option data)

- **Owner's request (Oct 10):** "The wheel with Post 1's exact rules on his stocks (AVGO, CRM, AMZN, META, CBOE), 2020–2026, counting share gains and losses."
- **Source:** r/CoveredCalls post "Collected $6,980 in premiums in Sept. $44.7k in premiums ($39.5k net) over 25 weeks on sub 200k capital." The poster is the developer of wheelstrategyoptions.com.
  - His stated rules: sell **0.25–0.45 delta**, usually **under 14 days** to expiration, and **close at 70–80% of the premium captured**.
  - His capital: about $200k (average deployed $132k).
- **This fills the gap test #26 left open:** single high-volatility stocks instead of SPY.
- **Paper research only;** no orders. Dollars first. Comparison: holding the same five stocks (the poster's own question), not SPY.
- **Looked at before writing this plan:** Databento cost quotes only (free endpoint) and the stocks' Apr–Oct 2026 closes used in the Oct 10 Reddit review. No option prices and no outcomes.

## Data
- **Stock prices:** Alpaca SIP, raw (unadjusted).
  - Daily bars for expiration-day closes and account values.
  - The 1-minute bar at 15:45 ET on each decision day for the stock price used to pick contracts.
  - Splits (AMZN 20:1 on Jun 6, 2022; AVGO 10:1 on Jul 15, 2024) and dividends from Alpaca corporate actions.
- **Option quotes:** Databento OPRA.PILLAR `cbbo-1m` (best bid/ask each minute).
  - The whole chain for one minute (15:45–15:46 ET) on each day the account needs to sell a new contract.
  - The chosen contract alone, from 15:46 on the sale day through 16:00 on its expiration day (for the 75% buyback and the expiration value).
  - META traded as **FB** until Jun 8, 2022 (parent `FB.OPT`), then `META.OPT`.
- **Cash interest:** 3-month T-bill rate (`research/spy_put_spread_backtest_v1/tbill_3m_monthly.csv`, extended through Sep 2026 from FRED series TB3MS if the owner approves that small download; otherwise the Dec 2025 rate carried forward, disclosed).
- **Cost guard:** checked with Databento's free cost endpoint before every request. Hard stop at the dollar limit the owner approves. Files cached, so nothing is bought twice.

## Rules (main version)
1. **Start:** $200,000 cash at the 15:45 snapshot of Jan 2, 2020, split into **five $40,000 sleeves**, one per stock. Each sleeve runs on its own; cash never moves between sleeves.
2. **Size: fractional contracts.** A put is sized so its collateral equals the sleeve's cash: contracts = cash ÷ (strike × 100). A call covers all shares held: contracts = shares ÷ 100.
   - **Why:** $40,000 can't secure even one AMZN put before its 2022 split (about $300,000 a contract) or one AVGO put before 2024. Fractional sizing gives each stock the same dollars throughout. Whole contracts are reported as information.
3. **Decision time:** 15:45 ET on any trading day a sleeve has no open option.
4. **Phase 1, no shares: sell a cash-secured put.**
   - **Expiration:** the one closest to **7 calendar days** away, within **4–13 days** ("under 14"); ties go to the later one.
     - If no expiration falls in 4–13 days (likely on CBOE, which may list only monthlies), use the nearest expiration within 4–45 days. These "fallback" trades are counted and reported.
   - **Strike:** below the stock price, with a bid above zero, and whose Black-Scholes delta (from its own mid-price implied volatility, the T-bill rate, no dividends) is **closest to −0.35**. It must be within **−0.25 to −0.45**; if none qualifies, skip the day.
   - **Fill:** at the **bid**, minus $0.03 a contract.
5. **Phase 2, holding shares: sell a covered call** on all shares, using the same expiration and fill rules, with the call strike above the stock price and delta closest to **+0.35** (within 0.25–0.45).
   - **No cost-basis floor** in the main version: the poster didn't state one. The floor is an information version.
6. **Early close ("70–80% captured"):** from the minute after the sale, the first minute when the **ask ≤ 25% of the sale price** (75% captured), buy it back at that **ask**, plus $0.03 a contract.
   - If that happens before 15:45, the sleeve sells the next contract at 15:45 the same day; otherwise at 15:45 the next trading day.
7. **Expiration (if not closed early):** judged on the stock's official close on the expiration day.
   - **Put, close < strike:** assigned. The sleeve buys contracts × 100 shares at the strike and moves to phase 2.
   - **Call, close > strike:** called away. Shares are sold at the strike and the sleeve returns to phase 1.
   - **Otherwise:** it expires worthless and the sleeve sells again at 15:45 the next trading day.
   - Early assignment is not modelled (disclosed).
8. **Splits:** shares are multiplied by the split ratio. An option that would still be open on a split's ex-date is bought back at the mid price on the trading day before, and the sleeve sells again on the ex-date under the normal rules.
9. **Dividends:** credited to the sleeve's cash on the ex-date for shares held at the prior close.
10. **Idle cash:** earns the T-bill rate daily, including put collateral (as most brokers pay interest on cash).
11. **Account value each day:** cash + shares × close − open options at the mid price.
12. **End:** Oct 9, 2026. Options still open are valued at their last mid price.

## Comparison: just holding the same five stocks
$40,000 of each stock bought at the 15:45 price on Jan 2, 2020 (fractional shares), dividends to cash (earning T-bills), never rebalanced.

## Windows
- **Main:** Jan 2, 2020 – Oct 9, 2026 (the owner's post-COVID default).
- **Halves:** 2020–2022 and 2023 – Oct 9, 2026.
- **Stress window (2016–2019):** not bought now. It's offered after the results (about $5–8 more).

## Report (dollars first)
- **The headline the poster would see vs the real result:** "premiums collected" (all premium kept) next to the true total P&L (premiums − buybacks + share gains and losses + dividends + interest).
- **Per week:** average and median $ per week, the share of weeks ≥ $1,000, the worst week and month, the worst drop from a high.
- **Per stock:** premiums, share P&L, total, times assigned and called away, and the dollars given up when shares were called away below the later price.
- **Hit rates:** % of contracts closed early at 75%, expired worthless, assigned or called away; count of fallback expirations.
- **Holding the five stocks:** the same dollar numbers.

## Pass bar (pre-declared, main version)
- **C1:** the wheel's final value ≥ holding the same five stocks.
- **C2:** the wheel is profitable in both halves.
- **C3:** the wheel's worst drop from a high is ≤ 25%.
- **Verdict:** **PASS** if C1–C3 all hold; otherwise **FAIL**. Results that pass only some checks are described as such (e.g. "less risk, less money").

## Information-only versions (one change each)
| Version | Change |
|---|---|
| `delta_25` | target delta 0.25 (band 0.20–0.30) |
| `delta_45` | target delta 0.45 (band 0.40–0.50) |
| `hold_to_expiry` | no 75% early close |
| `basis_floor` | call strike must also be ≥ the price the shares were assigned at |
| `whole_contracts` | whole contracts only; a sleeve that can't afford one sits in T-bills |

## Checks before results
- **Unit tests:**
  - expiration choice, including ties and the 4–45 day fallback;
  - delta pick and the band limits;
  - the 75% buyback minute;
  - assignment and call-away at expiration, including close = strike;
  - a split while holding shares;
  - fractional sizing;
  - a dividend credit.
- **An independent verifier**, written separately, that re-reads the raw quote files for 12 random contracts and recomputes the pick, sale, buyback/expiration and P&L, and checks that the trade list adds up to each sleeve's final value.
- **Provenance manifest** (`research/provenance_v1/provenance.py`), as for every test.
