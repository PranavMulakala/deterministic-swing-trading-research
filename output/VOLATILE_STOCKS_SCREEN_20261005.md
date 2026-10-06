# Big stocks that swing like LITE (about 5% a day), and the strategies people use on them (October 5, 2026)

- **Data:** daily prices on disk for 5,259 US stocks, over the last 60 trading days to Sep 28, 2026.
- **Code and numbers:** `research/lite_like_screener_v1/swing_screen.py` → `output/volatile-stocks-screen-20261005.json`.
- **Descriptive only: not a buy list.** Today's wildest stocks aren't tomorrow's winners (test #15).

## The filter
- **"Big":** at least $300M traded a day and a price of at least $10. That's 406 common stocks, and the typical one moves **1.7% a day**.
- **LITE:** moves **4.9% a day** on average (up or down), 5%+ on 47% of days, with $3.9B traded a day.
- **"Swings like LITE":** an average daily move of at least 4%.

## The answer: 31 others
| Theme | Stocks (average daily move) | Up or down over 1 year |
|---|---|---|
| AI chips, optics, memory, servers (the LITE/MU bet) | AXTI 7.9%, AAOI 5.8%, SNDK 5.5%, CRDO 5.0%, SMTC 4.9%, ALAB 4.8%, COHR 4.8%, TSEM 4.3%, MRVL 4.0%, DELL 4.0%, SMCI 4.0% | 10 up (+33% to +1,717%), SMCI −10% |
| AI cloud and data centers (many ex-bitcoin miners) | CIFR 6.5%, NBIS 5.7%, HUT 5.2%, IREN 5.2%, WULF 4.7%, CRWV 4.5%, APLD 4.3%, DOCN 4.2% | 6 up; IREN −10%, CRWV −33% |
| Crypto | MARA 4.7%, RIOT 4.6%, CRCL 4.5%, BMNR 4.2%, MSTR 4.0% | 4 down (−25% to −48%); RIOT +29% |
| Power for AI | BE 5.0%, OKLO 4.2% | BE +283%, OKLO −69% |
| Health and biotech | MRNA 7.0%, TEM 4.1% | MRNA +702%, TEM +10% |
| Quantum and space | QBTS 4.2%, ASTS 4.2% | QBTS −36%, ASTS +24% |
| Software | HUBS 4.1% | −60% |

**What they have in common:**
- **They swing both ways.** 21 of 31 rose over the year and 10 fell. The median one gained +38%.
- **Deep drops are normal.** The median worst drop within the year was **−56%**, and 29 of 31 fell 40% or more at some point. LITE's was −43%.
- **Mostly one bet:** the AI build-out (chips, data centers, power) plus crypto. They tend to fall together.

## Strategies people use on stocks like these, and what our tests found
| Strategy | Idea | Our evidence | Verdict |
|---|---|---|---|
| Buy the morning dip, sell +2% (Plan B) | Volatile stocks bounce | Test #15: on 100 volatile stocks picked without hindsight, $100k → $93k vs SPY $171k. 96% winners, sunk by a few that never came back | Works only on stocks that keep rising, which you can't know in advance |
| Buy strength (breakouts, momentum) | Leaders keep leading | Test #3 (our version) lost money. Academic momentum is real but crashes (C2 "US Stock Momentum" −30.5% in July 2026) | The one with real evidence, but expect deep drops |
| Earnings gap-ups (Qullamaggie's EP) | A surprise keeps drifting | Test #16: too rare to judge (15 trades in 10 years); the looser version made money per trade but only about 8 trades a year | Being watched live (the new EP emails) |
| Opening-range breakout | Trade the break of the first minutes | Published tests fail after costs; ours were no-go | Skip |
| Sell options (covered calls, cash-secured puts) | Big swings mean big premiums | Our SPY versions trailed SPY. On a 5%-a-day stock one crash can wipe out months of premium. **LITE options are banned for you** | Advanced; paper first |
| Size by the swing (~1% of the account at risk per trade) | Smaller positions in wilder stocks | Not a profit strategy, a survival rule. LITE swings about 3× a typical big stock (4.9% vs 1.7%), so the same risk needs about ⅓ the position | The most useful habit |
| Own the theme, not one stock | A sector ETF like SMH | SMH 2016–2025: +31.2%/yr, worst drop −45%, vs −40% to −80% for single names | The simplest way to keep the AI bet with less blow-up risk |
