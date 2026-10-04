# How volatile is LITE, and when does it move? (Oct 3, 2026)

Descriptive only, not a rule (the LITE formula freeze runs until late Nov). Code: `research/lite_volatility_v1/run.py`; numbers: `output/lite-volatility-20261003.json`.

## Rank among big stocks (last 252 trading days, through Sept 28)
| | LITE | Rank |
|---|---|---|
| Average daily move (up or down) | **4.9%** | **#3 of the 306** most-traded S&P 500 stocks (median 1.5%; SPY 0.6%) |
| Annualized volatility | 97% | #4 of 306 (median 32%) |
| Average high-to-low range in a day | 8.1% | |
| Days moving 5%+ | **109 of 252** (43%) | |
| Among all 387 big, liquid US stocks ($300M+/day) | | #10 |

S&P 500 top 10 by average daily move: SNDK 5.7, BE 5.4, **LITE 4.9**, MRNA 4.2, COHR 4.1, SMCI 4.0, WDC 3.9, **MU 3.9**, STX 3.7, MRVL 3.6. MU is #8.

## LITE's trading day (249 sessions, Oct 3, 2025 – Oct 2, 2026)
| Half hour (ET) | Avg high-low range | Share of the day's volume | Day's high set here | Day's low set here |
|---|---|---|---|---|
| **9:30–10:00** | **5.4%** | **22%** | **49%** | **44%** |
| 10:00–10:30 | 3.0% | 12% | 8% | 11% |
| 10:30–11:00 | 2.4% | 9% | 6% | 10% |
| 11:00–11:30 | 2.0% | 7% | 4% | 4% |
| 11:30–15:30 | 1.2–1.6% each | 4–6% each | 1–5% each | 2–4% each |
| 15:30–16:00 | 1.5% | 12% | 12% | 8% |

**First three hours (9:30–12:30):** median high-to-low swing **6.9%**. A 2%+ swing happened on 100% of days, 3%+ on 98%, 5%+ on 81%.

**But from a 10:00 buy, by 12:30:** +2% came first on about **41%** of days, −2% came first on **45%**, and neither on 14%. +3% was touched on 31% of days.

## Reading it
- LITE is one of the most volatile big stocks in America: about 8× SPY's daily movement.
- **Most of the action is the first 30 minutes and the last 30.** The day's high or low is set in the first half hour on about 9 days in 10.
- **Big swings don't make a direction.** From a 10:00 buy, +2% and −2% are close to a coin flip. A swing you can see afterwards isn't one you can catch in advance. That's the same lesson as the "+2% every day" check (98% of days in hindsight, about half from a real entry).
