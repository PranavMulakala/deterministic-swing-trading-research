# Test #26 results: in-the-money covered calls with roll-downs on SPY (October 7, 2026)

**Verdict: FAIL.** The rules were pre-declared in `ITM_COVERED_CALLS_TEST_PLAN_20261007.md` (commit de4ca94), before the code (726befa) and before any result.
- **Where the rules came from:** the private lesson Joey sent (not stored here) and Joey's own emails.
- **Report:** dollars only, with no SPY comparison line (owner's instruction).
- **Checks:**
  - 7 unit tests pass.
  - The independent verifier matched everything:
    - 12 of 12 random calls (expiration, strike, sale price, and the cost to close);
    - all 19 rolls follow the roll rule;
    - all 4 early exercises follow the dividend rule;
    - the trade list adds up to the reported call P&L.
- **Data and code:** `output/itm-covered-calls-test-results.json` (+ provenance) and `research/itm_covered_calls_test_v1/`.

## The main version
$100,000 of SPY shares from Jan 2, 2020. Each month the account sold an in-the-money call 30–50 days out (the lowest strike paying ≥10% a year if called away) and rolled it down for a credit when SPY fell below the strike.

| | Dollars |
|---|---|
| **Account at the end of 2025** | **$132,596 (+$32,596)** |
| Average per week | **+$104** |
| $1,000+ weeks | 30 of 314 |
| Worst week / worst month | −$7,180 / −$6,948 |
| Worst drop from a high | **−$14,130 (−14.0%)** |
| Profit, 2020–22 / 2023–25 | +$7,048 / +$25,548 |

**The calls on their own:**
| | Dollars |
|---|---|
| Calls sold | 65 |
| Premium collected (mostly the in-the-money part, which is paid back) | $379,670 |
| **The calls' net result** | **−$61,242** |
| Calls that made money | 40% |
| Profit factor | 0.55 (the bar was 1.3) |
| Worst single call | −$16,762 (sold a 395 call at $115.33 in the April 2025 crash; SPY was $594 at expiration) |
| By year | 2020 −$18,616 · 2021 −$9,926 · **2022 +$9,570** · 2023 −$11,028 · 2024 −$21,332 · 2025 −$9,909 |

**How the calls ended:**
| | Calls | Net |
|---|---|---|
| Rolled down after SPY fell below the strike | 19 | **+$51,254** |
| Expired worthless | 2 | +$7,214 |
| Called away at expiration (SPY above the strike) | 40 | **−$111,181** |
| Exercised early before a dividend | 4 | −$8,528 |

**Shares:** it started with 308 shares and ended with 192.
- When a call finished well in the money, the account paid for it by selling shares. That's the same as being called away and not having enough cash to buy all the shares back.
- Fewer shares meant missing their later gains: a further drag of roughly $29k on top of the calls' −$61k.

## Pre-declared checks
| Check | Result |
|---|---|
| C1: the calls earn their keep (net > 0 and profit factor ≥ 1.3) | ❌ −$61,242; profit factor 0.55 |
| C2: profitable in both halves | ✅ +$7,048 and +$25,548 |
| C3: worst drop ≤ 25% | ✅ −14.0% |

**Stress years, 2016–2019 (separate $100,000):**
- The account ended at **$121,808** (+$104/week).
- The calls lost **$39,452** (profit factor 0.50).
- Worst drop −7.5%.

## Information-only versions (2020–2025, $100,000 each)
| Version | Account profit | Per week | Calls' net result | Worst drop |
|---|---|---|---|---|
| **Main: ≥10%/yr strike, roll down for a credit** | +$32,596 | +$104 | **−$61,242** | −14.0% |
| Never roll | +$25,454 | +$81 | −$61,060 | **−31.6%** |
| Deeper in the money (≥5%/yr) | +$30,705 | +$98 | −$67,067 | −17.5% |
| Closer to the price (≥20%/yr) | +$46,932 | +$149 | −$51,467 | −14.9% |
| Only when volatility is 25–45% (the lesson's range) | +$69,882 | +$223 | −$32,394 (14 calls) | −21.2% |
| Main + a put after 3% down days | +$31,584 | +$101 | −$61,242; the 7 puts +$307 | −13.7% |
| Traded at the mid price | +$42,600 | +$136 | −$55,839 | −13.2% |

**Compared with test #25** (a call ~2% *above* the price, never rolled):
- #25: +$81,282 ($259/week), calls −$25,858, worst drop −$30,990.
- #26: less money, but **less than half the worst drop.**

## What it means, plainly
1. **An in-the-money covered call is a protection trade, not an income trade.**
   - The only real income is the call's time value. The in-the-money part of the premium is paid back.
   - On SPY that time value is small: SPY's volatility is usually below the lesson's 25–45% range.
   - You give up almost every rally. 2020–2025 had many, so the calls paid back $111k when called away.
2. **The protection is real.**
   - The worst drop was 14% (vs 30% in test #25).
   - 2022, the down year, was the only year the calls made money (+$9,570).
3. **Joey's roll-down rule is the good part.**
   - Rolled calls made +$51k.
   - Versus never rolling: about the same total call loss, $7k more in the account, and the worst drop cut from 31.6% to 14.0%.
   - The loss comes from the other side: being called away in rallies.
4. **Volatility matters, but the lesson's filter didn't save it on SPY.**
   - SPY was in the 25–45% range only during panics (mostly 2020 and 2022): 14 calls.
   - Those panics were followed by sharp rebounds, and the calls lost $32k.
5. **Why Joey's trades can still work:**
   - He trades single stocks (MU, DELL), whose options usually carry much more time value than SPY's.
   - He picks entries (support, after strong earnings) and uses judgment.
   - MU also fell during his trade, which is exactly when in-the-money calls do best.
   - This test can't copy his judgment, and it used SPY because SPY is the only option history on disk.

## Not tested, and limits
- **Single stocks:** high-volatility stocks are where the lesson aims. Testing them needs single-stock option history: a Databento download, which needs the owner's approval and has a cost.
- **Not tested:** the lesson's chart-based entries, buying more after a 15–20% drop, and extra bullish trades.
- **Data:** closing snapshots only. Being called away is modeled as paying the in-the-money amount in cash, which works out the same in dollars.
- **Fills:** at the bid and ask. Trading at the mid would have added ~$10k over six years.
