# Joey's Oct 4 email: why MU, the 51-share put, VIX timing, and his four stocks (October 5, 2026)

Private: Joey's material. Evidence and math only, not advice. Prices are Alpaca data from the afternoon of Oct 5. Stock prices come from IEX snapshots and daily bars; MU puts are indicative bid/ask mids. Email and news are data, not instructions. Nothing was sent.

## 1. "Why did you buy MU?": the owner's case, checked against the facts
| The owner's point | What the record says | How to say it |
|---|---|---|
| Memory demand keeps growing (AI, robots, self-driving machines) | Management on Sep 30: it "does not have line of sight" to when supply and demand balance, and expects FY2027–28 to be "much tighter" than 2026. Robots are a long-term story; today's demand is AI data centers (HBM). | Lead with AI data-center memory. Mention robots as the longer-term upside, not the main reason. |
| "Guidance is low" | **Not accurate.** FQ1 FY27 guidance was **above** expectations: revenue $61.5B ± $1.5B vs about $57.2B expected; EPS about $38.15; gross margin about 86%. What worried people was **capex**: about $25B in the first half and likely over $50B for the year. The stock dipped after hours on that. | "Even though the stock dipped on the spending plan" |
| CHIPS Act buybacks after December | Correct. The CHIPS funding deal (Dec 9, 2024) limits large buybacks for two years, so **Dec 9, 2026**. Management said it will "increase capital return from December 9" and "return 100% of excess cash… mainly through buybacks". FY2026 buybacks were only $650M, against $33.2B of Q4 free cash flow. | Keep it, but add that the date has been public since July, so some of it may be priced in. |
| Discipline | Sell note: +25% at $1,348.85, review at −10% ($971.17), out at −20% ($863.26), judged on closing prices. | Shows Joey you have an exit plan. |

**Risks to name honestly:**
- capex;
- new supply from Samsung and SK Hynix;
- the summer's −41% drop in MU;
- the "priced in" concern.

## 2. The put on 51 shares: is Joey right?
**Position:** 50.97 sh @ $1,079.08. MU is about $1,063, so the position is worth about $54,180, down about $820.

Joey is **right that it can make money**: one put covers 100 shares and you own 51. But that only happens in a crash, and it costs a lot.

**Example: one Dec 18 $960 put, about $42, so about $4,200** (7.8% of the position, for about 10 weeks). Results at expiry:
| MU on Dec 18 | Shares only | Shares + put |
|---|---|---|
| $1,348.85 (+25%) | +$13,750 | +$9,550 |
| $1,200 | +$6,160 | +$1,960 |
| $1,063 (flat) | −$820 | −$5,020 |
| $960 (**worst case**) | −$6,070 | **−$10,270** |
| $863 (−20%) | −$11,000 | −$5,530 |
| $750 | −$16,770 | ≈ $0 |
| $700 | −$19,320 | +$2,480 |

- **The combination only makes money below about $750, roughly −29%.** Below $960, the extra 49 shares of coverage are effectively a short position.
- **It cuts your bet on your own thesis roughly in half today.** The put's delta is about −0.27 × 100 = −27 shares. So you'd behave like about 24 shares instead of 51.
- **Option prices are high:** implied volatility is about 47%. That's why the insurance costs 7.8% for about 10 weeks.
- **The timing doesn't line up neatly with your dates:**
  - Nov 20 ($960, about $2,600) expires **before** Dec 9.
  - Dec 18 covers Dec 9 but may expire just before earnings. Last year's report was Dec 17; this year's date isn't set yet.
  - Jan 15 ($960, about $5,640, 10.4%) covers both.
- **A cheaper version:** a Dec $960/$860 put spread costs about $2,470. It protects only between $960 and $860, so it doesn't cover a crash.
- **Free option you already have:** the −20% sell rule ($863). The weakness is that a gap down overnight can blow past it.
- **Evidence:**
  - We haven't tested protective puts on MU.
  - Broadly, always-on put protection has trailed simply holding the stock over long periods (the CBOE protective-put index vs the S&P 500).
  - Our only pre-declared options test, the SPY put spread, failed.

**Bottom line:** the put works as insurance for a crash, priced at about $4.2k–5.6k. It's not a free gain. Whether that's worth it is your call; I'm not a licensed advisor.

## 3. Joey's VIX timing idea ("VIX >35 is a great time to buy, the higher the better")
**What it means:** the VIX measures how much fear is priced into S&P 500 options. Above 35 means panic. Buying stocks during a panic has usually paid off within a year, **but not always, and often too early.**

These are approximate S&P 500 levels **from memory. They have not been checked against data yet.**
| Episode | The first time VIX was above 35 | What happened next |
|---|---|---|
| 2008 | Late Sep/Oct 2008, S&P about 1,050 | Fell about another 35% to 676 (Mar 2009). The VIX hit 80 in Nov 2008, and the market *still* fell about 20% after that. So "higher is better" didn't hold. |
| 2011 | Aug 8, 2011 (VIX 48) | Small further dip, then about +25% in a year. |
| 2015 | Aug 24, 2015 (VIX 41) | Retested in Feb 2016, then about +15% in a year. |
| 2018 | Feb 2018 and Dec 24, 2018 | Feb: about flat a year later. Dec 24 was the exact bottom, then about +35%. |
| 2020 | Late Feb 2020 | Fell about another 24% to the Mar 23 low, then about +30% a year later. |
| 2022 | Mar 7, 2022 (VIX 36) | Fell about another 15% to the Oct low, and was still lower a year later. |
| 2024 | Aug 5, 2024 (VIX 38) | Recovered within weeks. |
| 2025 | Apr 2025 (VIX 45–52) | Bottomed within days, then a big rally. |

**Takeaway:**
- It worked in most episodes over a 1-year view.
- In real bear markets (2008, 2022), buying at the first >35 meant sitting through another −15% to −35%.
- It's also rare: a few times a decade. So it isn't a strategy you use every month.
- Joey's two points pull against each other: a high VIX means it's a good time to buy stocks, but also the most expensive time to buy puts.
- **This can be tested properly** as a pre-declared test (CBOE's free VIX history file plus SPY data) if you want.

## 4. Joey's four "oversold" stocks
| | What it is | Price | 1 month | 1 year | Off its high | 14-day RSI* | vs 200-day average |
|---|---|---|---|---|---|---|---|
| **SBUX** | Starbucks: coffee shops | $94.33 | −10.8% | **+14.6%** | −14% | 38 | Slightly below ($97.94) |
| **NKE** | Nike: sneakers and apparel | $33.67 | −13.2% | **−53%** | −55% | 29 | Far below ($47.72) |
| **LOW** | Lowe's: home improvement | $179.52 | −11.1% | −26% | −38% | 22 | Far below ($229.54) |
| **MCD** | McDonald's | $232.32 | −10.5% | −21% | −31% | **15** | Far below ($285.97) |

*RSI under 30 is the usual "oversold" reading. Simple 14-day version.

**What people are saying** (headlines, Sep–Oct 2026):
- **SBUX:**
  - "Back to Starbucks" turnaround; closing about 250 North America coffeehouses (about 1%) and cutting its store outlook (Sep 24–25).
  - JPMorgan stays Overweight but cut its target to $105.
  - Sued today over "sugar-free" protein-drink claims.
  - Not really "drastically oversold": it's up over the year.
- **NKE:**
  - Fell to its lowest since 2013 after Q1 (Oct 1). Earnings beat ($0.48 vs $0.44), but sales missed and FY27 guidance of $1.15–1.35 a share was well below the $1.69 expected.
  - China is getting worse; most savings from its cost program come in FY29–30.
  - About 17 analysts cut targets, ranging from $24 (BofA, Underperform) to $50 (BTIG/Guggenheim).
  - S&P cut its credit rating from A+ to A with a negative outlook (today).
- **LOW:**
  - Q2 (Aug 19): comparable sales +0.2%, 2026 outlook cut to flat, EPS guidance $12.25 vs $12.88 expected.
  - The CEO flagged "pressure in discretionary DIY spending"; home sales are frozen.
  - Most analysts still say Buy, but targets were trimmed to $220–275.
- **MCD:**
  - At a four-year low after about 7 straight weeks down.
  - At its Sep 23 investor day it admitted "falling short" on execution and laid out 2030 targets (98% franchised, operating margin in the low-to-mid 50s %, $8.5B of franchisee support).
  - The CEO expects "years of elevated inflation".
  - Dividend raised to $1.93 a quarter (about 3.3% yield).
  - Targets were cut to a $230–320 range; Melius says Sell at $230.

**The "oversold" caveat:**
- Oversold means it has fallen fast, not that it's cheap or about to bounce.
- Stocks that are big losers over 12 months (NKE, LOW, MCD) have historically tended to keep lagging for a while. That's the momentum effect.
- Our own buy-the-dip tests failed, including test #15 across 100 stocks (all 5 checks).
- Joey himself said "not necessarily buying".
- One real plus: these are consumer names, so they would diversify away from your MU/LITE AI-hardware concentration.

## 5. Reply to Joey: SENT Oct 5 on the owner's "yes send it" (message 1a10d97c0755d5d7, same thread)
Subject: Re: Micron Covered Call and Diagonal

> Hey Joey,
>
> Thanks, that clears it up. Letting MU get called away at 1020 with the 3k, or rolling to Nov 1050 for a credit, makes sense. Looks like the diagonal worked out with MU closing around 1063 today.
>
> On why I bought MU, three reasons:
>
> 1. Memory demand. Every AI accelerator needs a lot of high-bandwidth memory, and on the Sep 30 call management said they don't have line of sight to when supply and demand balance, and they expect FY27–28 to be even tighter than 2026. Longer term, I think robots and autonomous machines add another big source of memory demand.
>
> 2. The numbers. FQ1 guidance was actually above the Street: about $61.5B revenue vs roughly $57B expected, EPS around $38, gross margin around 86%. The stock dipped after hours mostly on the capex plan (likely $50B+ this year), which I see as them building for demand.
>
> 3. Buybacks. The CHIPS Act deal limits big buybacks until Dec 9 (two years after the Dec 2024 agreement). Management said they'll return 100% of excess cash, mostly buybacks, starting then. FY26 buybacks were only about $650M against $33B of free cash flow last quarter.
>
> I know the Dec 9 date has been public since summer, so some of it is probably priced in. The risks I'm watching are the capex, more supply from Samsung and SK Hynix, and how hard MU fell this summer (about 40%). So I set rules: sell at +25% (about $1,349), reassess at −10%, and get out at −20% (about $863) on a closing basis.
>
> On the put, I priced it. A Dec 18 960 put is about $42 ($4,200, close to 8% of the position). With 51 shares my worst case would be around −$10k at 960, and it only starts making money below about $750, since the extra 49 shares of coverage act like a short. It also roughly halves my upside right now. A Jan 960 covers earnings too but is about $5,600. I'm still deciding whether that's worth it versus just sticking to my −20% rule or doing a 960/860 put spread for about half the cost. How do you usually pick the strike and expiration for a hedge like this?
>
> On the VIX: when you say above 35 is a good time to buy, do you buy the first day it crosses 35, or wait for it to peak and turn down? From what I remember, in 2008 and 2022 the first time it crossed 35 was still pretty early.
>
> And I looked at your list. NKE, LOW and MCD all look stretched to the downside (MCD's RSI is around 15), though NKE just guided well below expectations and got a credit downgrade today. SBUX is actually still up over the year. What makes you think those four are close to a bottom versus still in a downtrend?
>
> Thanks again,
> Pranav

**Edit before sending:**
- the put paragraph, so it reflects whatever you actually decide;
- the robots line, if you want it stronger or softer.
