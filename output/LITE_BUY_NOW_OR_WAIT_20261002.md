# LITE: buy now or wait for a dip? (Oct 2, 2026, 11:05 ET)

Evidence only. Not a recommendation; the decision is mine. Code: `research/lite_buy_timing_v1/run.py`; numbers: `output/lite-buy-timing-20261002.json`. Data: Alpaca SIP daily bars from 2016, 5-minute bars 2022–26, today's 1-minute bars.

## Where LITE is right now
| | |
|---|---|
| Last trade (11:05 ET) | **$1,067.53** |
| Yesterday's close | $1,045.78 |
| Today's open | $1,053.26 |
| Today's low | $1,037.24 at 9:55 (−1.5% from the open) |
| Today's high | $1,084.30 at 10:49 (+2.9% from the open) |
| Average price paid today (VWAP, to 10:49) | $1,062.39 |
| 52-week closing high before today | $1,053.09, so **today is above it** |
| News in the last 24 h | none |

**Today's 1-minute chart in words:** it dipped for 25 minutes after the open, bottomed at 9:55, rallied about 4.5% to 10:49, and has given back about 1.5% since. The paper dip bot saw the 9:55 price back above the open, so its rule said NO_SIGNAL.

## 1. If I wait for a dip, does it come? (20 trading days ≈ 1 month)
| Dip I wait for (from $1,067.53) | Price | Came, 2025–26 | Came, near a 52-wk high, 2025–26 | Came, 2016–24 (stress) | When it didn't come, LITE was (2025–26 median) |
|---|---|---|---|---|---|
| −5% | $1,014 | 73% | 71% | 66% | **+23% higher** |
| −10% | $961 | 46% | 47% | 41% | **+22% higher** |
| −15% | $907 | 32% | 26% | 21% | +20% higher |
| −20% | $854 | 21% | 9% | 8% | +18% higher |

How fast: a −5% dip usually came within **2 days**; a −10% dip within about **4 days** (2025–26).

## 2. Who did better after a month: buy now, or wait?
"Wait" = buy exactly at the dip price if it comes, else stay in cash. Average 20-day results:

| | Buy now | Wait for −5% | Wait for −10% |
|---|---|---|---|
| 2025–26 boom | **+14.4%** | +10.2% | +4.2% |
| 2016–24 stress | +2.1% | +1.4% | +1.1% |
| Days waiting beat buying now (2025–26) | | 73% | 47% |

**What this says:**
- Waiting for **−5%** usually works (about 7 times in 10), but on average it **lost** to buying now in the boom. The misses, when LITE ran +20% or more without me, cost more than the small discounts saved.
- Waiting for **−10%** is a coin flip on whether it comes. When it doesn't, I'm in cash while LITE is about +22% higher.
- **All of these averages lean on 2025–26, when LITE rose about 12× ($84 → $1,068).** In 2016–24, buying now and waiting came out about the same. Which one wins depends mostly on whether the boom continues, and nobody knows that.

## 3. Today's chart pattern (dipped ≥1% below the open, back above it by 9:55)
| What happened next | Days shaped like today (2025–26, n = 94) | All days (2025–26, n = 433) |
|---|---|---|
| Up from 11:00 to the close | 61% | 51% |
| Fell 2%+ below the 11:00 price later that day | 35% | 35% |
| Up the next day | 61% | 56% |
| Up 5 days later | 65% | 61% (median +3.0%) |

That's only a few points better than an ordinary LITE day, on overlapping samples, so it's **within noise**. The four chart-pattern tests we pre-declared all failed (breakout, pullback, first-hour turn, trailing exit). I wouldn't treat any 1-minute pattern as an edge.

## 4. Dollar math at $1,067.53, against my $38k combined limit
| | 30 shares | 50 shares | 70 shares |
|---|---|---|---|
| Cost | $32,026 | $53,377 | $74,727 |
| +20% target ($1,281) | +$6,405 | +$10,675 | +$14,945 |
| −10% ($961), "a normal LITE week" | −$3,203 | −$5,338 | −$7,473 |
| **−20% limit ($854)** | −$6,405 | **−$10,675** | −$14,945 |
| −43% (this year's May–July drop) | −$13,771 | −$22,952 | **−$32,133** |

- Short-term gains are taxed at about 29% for me, so +$10,675 is about **+$7,600 after tax**.
- The $38k limit covers **everything** combined. LITE plus MU together have to fit inside it in a −43% kind of drop.
- **Split option:** half now, half at −10%. Using the averages above, that lands roughly halfway: about +9% in the boom and about +1.6% in the stress window. It just halves both the regret of missing the run and the regret of buying the top.

## 5. Things that don't change either way
- **Earnings:** Lumentum usually reports its September quarter in early November (date not confirmed). That's the biggest scheduled gap risk for any position.
- **Lumentum policy:** cash shares only. No options, no shorting, no margin; limit orders are "discouraged" (my dad works there).
- **My sell note** (`LITE_SELL_NOTE.md`) applies from my real fill price: +20% target, −20% limit, decided on closing prices.
- **Over 10 years, holding the index beat every rule we tested.** A single stock that has risen 12× is the opposite of that, so the position size matters more than the entry price.

---

## Follow-up (1:30 PM): does LITE offer +2–3% every day?
Code: `research/lite_buy_timing_v1/daily_opportunity.py`; numbers: `output/lite-daily-opportunity-20261002.json`. Uses 5-minute SIP bars; no fees or slippage.

| Share of trading days where… | 2025–26 boom (435 days) | 2022–24 (747 days) |
|---|---|---|
| A +2% move existed **in hindsight** (buy the low, sell a later high) | 98% | 67% |
| …the same with +3% | 84% | 35% |
| The high reached the **open +2%** | 61% | 35% |
| Buying at **10:00**, it reached +2% later that day | 53% | 27% |
| …reached +3% | 33% | 11% |
| From 10:00, +2% came **before** −2% | 44% | 26% |
| On days +2% never came: close vs the 10:00 price | median −1.4%, worst −16.7% | median −0.5%, worst −8.6% |

**"Buy at 10:00 whenever flat, hold until +2%"** (one position at a time):
- **2025–26:** 113 sales, about 1.3 a week. The longest hold was 122 trading days, and the worst dip while holding was **−55%**.
- **2022–24:** **1 sale in 3 years.** It bought in Jan 2022, fell as far as **−67%**, and was still holding at the end of 2024.

**Today:** buying at 10:00 ($1,053) would have reached +3.7% by 10:49. But the dip rule didn't fire, and on about half of boom days the same buy didn't reach +2% at all.

**Dollars at 15 shares (about $16k):** +2% = $320. Every day for a year would be $80k, but that isn't what the history shows. In the boom, the pace was about $420 a week before tax, with months stuck in a −55% hole. In 2022–24, it was one $320 sale and then a −$10,700 hole lasting years.

Descriptive only. A "buy every day" rule would be a new formula, so it goes on the parked list (freeze until late Nov).
