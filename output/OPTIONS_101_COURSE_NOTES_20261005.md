# Options 101 (options-101.com): course notes in plain words (October 5, 2026)

- **Source:** https://options-101.com, a free site with no ads, built by Agustin Lebron (ex-Jane Street options trader, now at EquiLibre Technologies). Course 1, "Introduction to Financial Options", is taught Fall 2026 at Charles University, Prague.
- **Read in the browser** from the interactive slides; no files downloaded. A summary in my own words.
- **Published so far: 2 of 12 lectures.**
  - Lecture 1: slides, video (https://youtu.be/aovS4gffQB8) and PDF (5.3 MB).
  - Lecture 2: slides and PDF (114 KB).
- **Still to come:** put-call parity, pricing by replication, Black-Scholes, implied volatility, delta, gamma/theta/vega and P&L, volatility smiles and surfaces, no-arbitrage bounds, "financial time", stochastic volatility.
- **Assignments:** put-call parity, writing an options pricer in Python, hedging a portfolio, and building an arbitrage-free volatility surface.

## Lecture 1: What is an option?
- **Why it matters:** options are everywhere (insurance, refundable bookings, mortgages you can refinance, startup stock options). The maths connects probability and economics.
- **Explicit non-goal:** "We will not teach you profitable trading strategies." He says making money trading is extraordinarily hard, and that course sellers and influencers make money off their students, not from trading. That matches our 12 tests.
- **Basics:**
  - **A stock** is a share of a company's equity (what's left after debts). **Shorting** means borrowing a share, selling it, and buying it back later.
  - **A call** is the right, not the obligation, to buy at a fixed price (the strike). **A put** is the right to sell at the strike.
  - **Every contract specifies** the underlying, strike, expiry, American (exercise any time) vs European (only at expiry), and physical vs cash settlement.
- **At expiry,** a call is worth max(price − strike, 0) and a put max(strike − price, 0).
  - **A positive payoff can still be a loss:** pay $6 for a $100 call, stock ends at $103; you exercise for $3 but lose $3 overall. **Break-even = strike + premium.**
- **The other side:** every buyer faces a seller (the "writer"). The seller collects the premium and must deliver if assigned; they can't say no. *This is the cash-secured-put seller's position from test #10.*
- **First no-arbitrage rule:** better terms can't cost less. A lower-strike call is worth at least as much as a higher-strike call (puts are the reverse).
- **History:** options on Dutch East India Company shares in the 1600s; a 1688 book describing them; Bachelier's maths in 1900; the CBOE and Black-Scholes in 1973; VIX futures in 2004.

## Lecture 2: The value of optionality
- **Core idea:** an option lets you keep the good outcomes and walk away from the bad ones, so **uncertainty creates option value.**
- **Example:** a steady utility stock and a biotech awaiting a drug trial, both at $100.
  - A $100 call on the utility is worth about $0, because nothing surprising will happen.
  - On the biotech (either $50 or $400), the same call is worth about $42.86, even though both stocks' average expected price is $100.
- **Same average, wider spread → a more valuable option.** Options are really bets on volatility, and on the shape of the possible outcomes, not just the average.
- **Why not exercise early:** an option = intrinsic value (what you'd get exercising now) + time value (the remaining chance of something better). Exercising throws away the time value, so **selling the option is usually better than exercising it.** Exceptions include dividends and interest.
- **More time can't hurt an American option,** since it contains all the shorter one's rights.
- **Time and volatility trade places:** a typical move scales like volatility × √time. 40% volatility over 3 months ≈ 20% volatility over 12 months.

## How this connects to our research
- **Why option sellers win often but don't beat the market (test #10):** sellers are paid for uncertainty. The price already reflects the spread of outcomes, so a high win rate is built in, and the big losses come from the tails.
- **Why the "75% chance of profit" credit spread from TikTok is about break-even:** "chance of profit" comes from option prices, which already price the distribution.
- **Why LITE options would be expensive:** LITE's ~4.9% daily moves (very high volatility) make its options pricey, on top of the Lumentum policy banning them for the owner.
- **Worth following as the next lectures are posted,** especially implied volatility and the Greeks (lectures 6–8). Those explain the numbers on Robinhood's options screen.

## Extra points from the Lecture 1 video (transcript pasted by the owner; my summary)
- **Who he is:** an electrical engineer who later ran Jane Street's London options desk (Europe, Eastern Europe, Africa). The course is adapted from how Jane Street trains its interns and new hires.
- **Prior trading "knowledge" can be a negative:** there's so much bad information online that it has to be unlearned.
- **The simple arbitrages** (e.g. a lower-strike call priced below a higher-strike one) **really were free money until the late 1970s / early 80s.** Today they essentially never appear in real markets.
- **Selling options "is free money"** (said sarcastically): it works out about 98% of the time, and the other 2% really hurts. *That's test #10 in one sentence.*
- **Options trading is negative-sum:** one side's gain is the other's loss, and the exchange and broker take fees on top.
- **A stock is like a call with a strike of zero:** shareholders get wiped out in bankruptcy but never owe more.
- **Sunk-cost lesson:** if your call is worth something at expiry, exercise it (or sell it) even if you lost money overall. The premium you already paid shouldn't affect today's decision.
- **Mechanics:**
  - **Bid and ask:** there are always two prices; you buy at the ask and sell at the bid.
  - **Separate markets:** every strike and expiry is its own market.
  - **Auto-exercise:** options that finish in the money are exercised automatically at expiry unless you instruct otherwise.
  - **Margin:** if you *sell* an option, the broker requires margin (extra cash) and can close you out. If you *buy* one, the most you can lose is what you paid.
  - **The clearing house:** it guarantees trades between brokers; your broker guarantees you.
- **His warning about "buy now, pay later"-style products:** companies increasingly embed options because people don't know how to value them.
