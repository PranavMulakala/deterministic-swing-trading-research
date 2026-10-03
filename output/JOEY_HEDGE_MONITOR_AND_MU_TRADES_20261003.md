# Joey's Oct 3 emails: the "Dynamic Hedge Monitor" and his two MU trades

Private: Joey's material. Two emails (8:56 and 8:59 AM ET, Oct 3) with three screenshots and no code or files, so nothing was run. Numbers are re-derived here from the screenshots. Evidence and math only, not advice. MU put prices are Alpaca indicative mids at Friday's close.

## 1. The "Dynamic Hedge Monitor" (mock MSTR example)
**What it is:** when a big stock position falls close to its breakeven, the tool lists the put options you could buy, and ranks them by how small your worst-case loss would be. It also shows SPY and VIX. In the mock: 500 MSTR shares, breakeven $155.53, MSTR at $150, puts expiring Nov 3.

**Its math checks out:** max loss = (breakeven + put price − strike) × shares. For the $164 put: (155.53 + 14.60 − 164) × 500 = **$3,065**, at a cost of **$7,300**.

**What the ranking really picks:** max loss per share = (breakeven − price) + the put's time value. The first part ($5.53 × 500 = **$2,765**) is already lost, because the stock is below breakeven. So "lowest max loss" just means "least time value", which always favors the deepest in-the-money put.
- The "BEST" $164 put leaves a worst case of $2,765 already lost + $300 of insurance cost.
- **Selling the shares at $150 locks in the same $2,765,** with no $7,300 cash outlay.
- With the $164 put, the position only makes money again **above $170.13** (breakeven + put price) by Nov 3.
- The tool's own footnote says deeper in-the-money "acts more like selling". The $164 put cancels 92% of the stock's moves (delta −0.92).

**Fair points:** the math is right; it's protection for 31 days ("even if MSTR goes to zero", while the put lasts); and checking the bid/ask spread (≤ 15%) is sensible.
**Limits:**
- It's a menu, not a prediction.
- Protection bought *after* a drop costs more: the mock shows VIX +18%.
- The protection expires, so you pay again every month.
- Puts come in **100-share contracts**.

**Priced for my MU** (50.96 shares @ $1,079.08; 1 put covers 100 shares, so it over-covers about 49 shares):
| Put | Cost (1 contract) | My worst case at expiry, about | vs my −20% limit (−$10,998) |
|---|---|---|---|
| Oct 30 $1,000 | $2,548 | −$6,578 | smaller |
| Nov 20 $1,000 | $4,130 | −$8,160 | smaller |
| Nov 20 $950 | $2,539 | −$9,117 | slightly smaller |
| Dec 18 $1,000 (includes earnings) | $5,896 | −$9,926 | slightly smaller |
| Dec 18 $900 | $2,692 | −$11,818 | **bigger** |

The Nov 20 puts cost about 4.6–7.5% of the position's $55k value for ~7 weeks. Below the strike, the extra 49 shares' worth of put coverage gains money (a net short).

## 2. Joey's MU covered call (200 shares)
| | |
|---|---|
| Shares | 200 @ $1,074.71 ($214,942) |
| Sold | 2 × MU $1,020 calls expiring Oct 30 @ $72.35 = **$14,470 received** |
| Breakeven | $1,074.71 − $72.35 = **$1,002.36** |
| Best case (MU ≥ $1,020 on Oct 30) | shares called away at $1,020: −$10,942 + $14,470 = **+$3,528 (about 1.6% in 4 weeks)** |
| MU at $1,200 on Oct 30 | still **+$3,528**. Plain shares would have made +$25,058 |
| MU at $860 | about **−$28,500**. Only $72/share of cushion |
| Analyzer's "chance of profit" | about 64–70% (implied by option prices, the same idea as my MU odds) |

**In plain terms:** he gave up everything above $1,020 for $72 a share now. The call is already in the money, so most of that $72 is just the $54.71 by which MU sits above $1,020. The real income is the $17.64/share of time value (= the $3,528). It behaves like owning about 66 shares instead of 200 (delta 66.4), with almost all of the downside.
**Why it doesn't fit my position:** a covered call needs 100 shares per contract, and I have 50.96. In a stock that rose about 6× in a year, capping the upside has historically been the expensive part.

## 3. Joey's "bearish diagonal" on MU (expires Mon Oct 5)
| Leg | |
|---|---|
| Sold 1 MU $1,055 put, Oct 5 | +$420 |
| Bought 1 MU $840 put, Jan 15, 2027 | −$2,401 |
| Net cost | **$1,981** |

At Monday's close (from his chart):
| MU on Monday | Result |
|---|---|
| About $1,048–$1,094 (analyzer: about 42% chance) | profit, at most about **+$497** near $1,059 |
| Above about $1,094 | small loss, about −$300 to −$500 |
| $970 (−10%) | about **−$6,000** |
| $840 | about **−$15,000** |

**In plain terms:** for the next trading day this is a **bet that MU stays near $1,055**, not a bearish bet. The short $1,055 put loses $100 for every $1 MU falls below $1,055, and the far-away $840 January put barely helps in one day. The "bearish" part is the January put, which pays only if MU falls below $840 (about −22%) by January.
**His plan if it drops:** "roll the short put down and out for a credit". That postpones and stretches out the risk; it doesn't remove a loss.
**Risk/reward this weekend:** at most about +$500, against about −$6,000 on a 10% drop.

## What this means for me
- **Policy:** options on **LITE** are banned for me (the Lumentum policy). MU options are allowed.
- **Evidence so far:** our only pre-declared options test (SPY put spread) **failed** its holdout. None of Joey's three structures has been tested here.
- **Simplest equivalents for my 50.96 MU shares:** my sell note (−20% limit) is free and needs no contracts. A put sets a hard floor, but the Nov 20 ones cost about 4.6–7.5% of the position for ~7 weeks.
