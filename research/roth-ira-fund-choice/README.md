# Roth IRA fund choice: VT vs VTI+VXUS (70/30, 80/20) vs VOO, plus growth tilts

Research as of 2026-10-07. This is decision support, not financial advice, and I'm not a licensed advisor. You
place your own orders. Prices run through Sep 30, 2026 (monthly, dividend-adjusted, Alpha Vantage); fund
profiles (expense ratios, holdings, sectors) are Alpha Vantage `ETF_PROFILE` dated Oct 2; quotes are the Oct 6
close. Everything regenerates with `python fetch_profiles.py` and then `python analysis.py` (seed 20261007,
10,000 paths, about 3 seconds). The engine is the 401(k) study's (`../401k-fund-choice/analysis.py`).

## Bottom line

**What the evidence favors for the Roth: 100% VT, with the $250 every two weeks going into VT automatically.
No growth tilt.** Keep the taxable plan at VTI/VXUS and the 401(k) as is.

Why VT wins here even though it costs a little more:

1. **It's the only option that doesn't share an index with your taxable account.** Your taxable plan holds VTI
   and VXUS. If the Roth buys VTI or VXUS every two weeks, then there is never a 30-day window without a Roth
   purchase. Any loss you sell for taxes in the taxable account becomes a wash sale. A wash sale triggered by an
   IRA purchase loses the deduction **permanently** (IRS Rev. Rul. 2008-5). In taxable it would only be
   deferred. VT tracks a different index (FTSE Global All Cap), so it doesn't block harvesting.
   - Example: a 2022-style −20% year on the $78k taxable index money is a ~$15.6k loss. At your ~24% federal
     plus ~5% Georgia rate, harvesting it is worth about **$4,500** up front (mostly a deferral, since your cost basis drops). That loss can offset the short-term gains
     from your 2026 LITE trading.
   - VT's extra fee is about **$1.40 a year** on today's $5,967.
2. **The fee gap is small.** VT is 0.06%. The same 62/38 mix built from VTI+VXUS is 0.038%. Over 33 years
   that's about **$2,500 less at 55** (today's dollars) out of a ~$564k median, or 0.45%.
3. **VT's one tax weakness doesn't apply in a Roth.** VT can't pass through the foreign tax credit, because
   less than 50% of its assets are foreign. A Roth gets no credit anyway, so VT belongs in the Roth more than
   anywhere else you hold money.
4. **One ticker means one recurring order and no rebalancing.** VT rebalances itself at market weights
   (today about 62% US / 38% international).
5. **It's the most diversifying choice against LITE.** International stocks have the lowest correlation with
   LITE (0.27–0.28 vs 0.33–0.37 for US and growth funds). Section 5 explains why the Roth can only move this a
   little.

**Close second: VTI/VXUS 70/30.** Choose it only if you will **never** tax-loss harvest VTI or VXUS in
taxable. It's slightly cheaper and matches your taxable plan.
**VOO** is also wash-sale-safe against VTI, but it adds no international or small/mid exposure. Its post-COVID
lead (15.3% a year) is the same US-large-tech run that LITE already gives you.

## Update Oct 8: VT 80 + AVUV 20 tested. It passed the rules declared beforehand.

The plan was written before any result: [`AVUV_TILT_PLAN_20261008.md`](AVUV_TILT_PLAN_20261008.md). Code:
`avuv_tilt.py`. Full tables: [`results/avuv_tilt.md`](results/avuv_tilt.md). AVUV is US small-cap value
(0.25% ER, 739 stocks), mostly banks, consumer, energy and industrial companies. It holds no LITE and no MU, and
only 5% of it is tech. Before Oct 2019 it's proxied by DFSVX. Over their 83 common months the two moved almost
identically (correlation 0.993), and AVUV did 1.2%/yr *better*, so the proxy doesn't flatter the tilt.

| Decision rule (declared first) | Result |
|---|---|
| 1. Forward-model median at 55 ≥ VT's | **PASS**: $575k vs $564k (+$11k) |
| 2. If small value earns no premium, the cost is under 3% | **PASS**: −0.1% (about −$500) |
| 3. Worst dollar drop since 2008 is ≤ 1.10× VT's | **PASS**: −$49.7k vs −$52.7k (0.94×) |

| In dollars ($5,967 start + $557.92/mo) | VT | VT 80 + AVUV 20 | VT 80 + QQQM 20 |
|---|---|---|---|
| Post-COVID (main): ending | $88,105 | $88,793 | $93,195 |
| Post-COVID: worst drop | −$4,295 | −$3,658 | −$4,246 |
| Since 2008: ending | $407,534 | $416,684 | $497,059 |
| Since 2008: worst drop / worst 12 months | −$52,662 / −$44,518 | −$49,735 / −$41,338 | **−$67,221 / −$56,457** |
| Monte Carlo median at 55 (no / base / +1 pt premium) | $564k | $564k / $575k / $599k | $576k (zero-skill) |

What this means:
- **The tilt is a cheap bet with a small expected payoff.** If small value's long-run premium shows up, it adds about
  $11–35k at 55. If it doesn't, it costs about $500.
- **It also diversifies you a little.** Its correlation with MU is 0.38, versus 0.51 for VT and 0.53 for QQQ.
- **It isn't aggressive in the "more swings" sense.** Its worst drop in percent was a bit deeper than VT's
  (−44.9% vs −43.4% since 2008). But the overall bumpiness was about the same.
- **The QQQM tilt Reddit likes made the most in the backtests,** which ran during tech's best era. It also had the
  biggest dollar drops, and in the forward model (zero skill) it adds nothing. For you it would also buy more MU.
- **The real cost is patience.** The tilt fell up to **10.7% behind plain VT from Dec 2016 to Mar 2020,** and
  only caught up in Oct 2022. It trailed VT in about a third of rolling 3-year windows (at worst by 3.2%/yr).
  If six years of looking wrong would make you sell, plain VT is the better choice for you.
- **The bootstrap (info only, +$110k) flatters the tilt** because it replays 2000–2007, a great era for small value.
  It doesn't count toward the verdict.

**Setup if you adopt it:**
- Invest the $5,967 as about $4,774 VT + $1,193 AVUV.
- Then two recurring buys every 2 weeks:
  - **$200 VT + $50 AVUV** at the current $250;
  - or **$231 VT + $58 AVUV** if you raise it to $289 to max the $7,500 limit.
- Once a year, if AVUV has drifted outside 15–25%, point new money at the side that's behind. No selling needed.
- AVUV doesn't clash with anything for wash-sale purposes. Your 401(k) holds VSMAX, a different index (small-cap
  blend).

## Check these first (they change the household numbers, not the Roth answer)

| Item | What I used | Why it matters |
|---|---|---|
| **LITE position** | Your figure: ~27% of total assets ≈ **$47k (~41 sh @ $1,133.40)** | The project's records say Plan B's 46.13 sh were sold Oct 6 (+$1,016.54) and you were flat. I assume you re-bought after that. `research/market_brief_v1/positions.json` still lists the old 46.13 sh. |
| **MU 50.97 sh** (~$53.3k @ $1,045.56) | Shown both ways | The records still show it held. If it is, **LITE + MU = 58% of everything you own** and your taxable index money is only ~$25k, not ~$78k. |
| **$16k 2026 tax reserve** | Not subtracted | Earlier notes set aside ~$16k for 2026 taxes, on top of the $25k emergency cash. If both are cash, the taxable index money shrinks by $16k. |
| 401(k) balance | ~$18k ($16,825 on Sep 29 + ~1 paycheck) | Too small to change the conclusions. |
| 2026 Roth contributions so far | Unknown | Section 6 covers the $7,500 limit. |

## 1. Costs (Alpha Vantage net expense ratios)

| Roth option | Blended ER | Per year on $10k | Dividend yield |
|---|---|---|---|
| VT | 0.060% | $6.00 | 1.55% |
| VTI 62 / VXUS 38 (VT's mix, DIY) | 0.038% | $3.75 | — |
| VTI 70 / VXUS 30 | 0.036% | $3.60 | — |
| VTI 80 / VXUS 20 | 0.034% | $3.40 | — |
| VOO | 0.030% | $3.00 | 0.98% |
| VTI only | 0.030% | $3.00 | 1.01% |
| VT 80 + QQQM 20 | 0.078% | $7.80 | — |
| QQQM | 0.150% | $15.00 | 0.44% |

VXUS 0.05%, yield 2.51%. Alpha Vantage lists VUG at 0.03% and SCHG at 0.04%. **The expense ratio is the
smallest factor in this decision.**

## 2. Overlap with your 401(k) and taxable

| Roth candidate | Index it tracks | Same index elsewhere in your accounts | Wash-sale conflict with taxable harvesting |
|---|---|---|---|
| **VT** | FTSE Global All Cap | none | **none** |
| VTI | CRSP US Total Market | taxable VTI (70% of the plan) | **yes**, every two weeks |
| VXUS | FTSE Global All Cap ex US | taxable VXUS (30%) **and** 401(k) VTSNX (35%) | **yes** |
| VOO | S&P 500 | 401(k) S&P 500 fund (45%) | not with VTI/VXUS |
| QQQM | Nasdaq-100 | none | none |

- **By holdings, everything overlaps.** The S&P 500 is about 85% of the total US market by value, and VT is
  essentially VTI plus VXUS. So the Roth's fund choice doesn't add or remove companies from your household. It
  changes the **weights** (section 5) and the **tax plumbing** (above).
- **A separate issue in your taxable account: VXUS shares an index with the 401(k)'s VTSNX.** That fund buys
  every paycheck. Rev. Rul. 2008-5 covers IRAs; whether a 401(k) purchase triggers a wash sale is a gray area.
  If you ever harvest VXUS, the usual swap is a fund on a different index (e.g. IXUS, MSCI-based). Ask a tax
  pro before relying on it.

## 3. Backtests ($5,967 start + $557.92 a month, rebalanced each December)

**Main view: post-COVID, Jan 2020 – Sep 2026 (81 months)**

| Option | CAGR | Max drop | Worst 12m | Ending (of $51,158 in) |
|---|---|---|---|---|
| VT | 12.5% | −25.5% | −20.8% | $88,105 |
| VTI 62 / VXUS 38 (DIY) | 12.9% | −25.5% | −20.6% | $88,913 |
| VTI 70 / VXUS 30 | 13.2% | −25.4% | −20.1% | $89,714 |
| VTI 80 / VXUS 20 | 13.7% | −25.2% | −19.4% | $90,737 |
| VTI only | 14.7% | −24.8% | −19.5% | $92,723 |
| VOO | 15.3% | −23.9% | −18.2% | $95,230 |
| Tilt: VT 80 + QQQM 20 | 14.4% | −26.9% | −21.6% | $93,195 |
| Tilt: QQQM 100 | 21.1% | −32.5% | −32.5% | $113,897 |

**Stress test, Jan 2000 – Sep 2026 (321 months; the VT row uses today's 62/38 mix as a proxy before 2008)**

| Option | CAGR | Max drop | Worst 12m |
|---|---|---|---|
| VT (proxy) | 7.3% | −53.8% | −46.4% |
| VTI 70 / VXUS 30 | 7.5% | −53.2% | −45.8% |
| VTI 80 / VXUS 20 | 7.8% | −52.4% | −45.0% |
| VOO | 8.3% | −50.9% | −43.3% |
| VTI only | 8.4% | −50.8% | −43.3% |
| Tilt: QQQM (QQQ before 2020) 100 | 8.9% | **−81.1%** | **−67.3%** |

- **More US always won.** In every window, the more US in the mix, the better it did. That was the 2010s–2020s
  pattern: US large-cap tech beat the world. As usual, the post-COVID window flatters tech.
- **The full history should decide the growth-tilt question,** because the risk there is a deep, long drop.
  Over 2000–2026, QQQ earned only 0.5%/yr more than VTI, with a −81% drawdown and a −67% worst year.
- **Since VT launched (Aug 2008), real VT trailed its "today's mix" DIY version by 0.8%/yr.** That gap isn't
  the fee. VT held about 55% international in 2008, and international lagged. It's the market-weight design
  working as intended.

## 4. Monte Carlo to age 55 (today's dollars; 10,000 paired paths)

| Option | Bootstrap median (P10–P90) | Forward-CMA median (P10–P90) |
|---|---|---|
| VT | $560k ($241k–$1.36M) | **$564k** ($243k–$1.37M) |
| VTI 62 / VXUS 38 (DIY) | $563k | $567k |
| VTI 70 / VXUS 30 | $591k | $561k |
| VTI 80 / VXUS 20 | $625k | $550k |
| VOO | $683k | $520k |
| VTI only | **$700k** | $529k |
| Tilt: VT 80 + QQQM 20 | $617k | $576k ($231k–$1.48M) |
| Tilt: QQQM 100 | $817k ($205k–$3.22M) | $561k (**$154k**–$2.10M) |

How to read this:
- The **bootstrap** reshuffles 2000–2026, so it assumes the US keeps beating the world.
- The **CMA** model uses the 401(k) study's forward returns: US 4.2–4.3% real, international 5.0%. In that
  model, the ranking reverses.
- **Which option "makes the most money" depends entirely on the US vs international bet, not on fees.** VT
  holds the market-weight answer, so it doesn't need that bet to go right.
- **A growth tilt's extra expected return is assumed, not shown.** With zero skill (the CMA model), QQQM's
  median equals VT's, its bad case is $88k worse, and its typical worst drop is −65% vs −46%.

## 5. Tax location, growth tilt, and LITE

**Does a growth tilt belong in the Roth? Not for you, now.**
- **The textbook rule:** "put the highest-growth assets in the Roth". It's about where to hold assets you
  already want. It isn't a reason to add risk you don't otherwise want.
- **You already have a big tilt in LITE.** It's ~32% of your stocks on its own. That pushes your household to
  **~50% information technology vs 35% in the total US market.** If MU is still held, it's ~76%.
- **QQQM's 4th-largest holding is MU (5.1%),** and it holds LITE at 0.35%. A QQQM tilt would buy more of the
  stocks you already own.

**Household look-through: the Roth barely moves it**

| | Roth = VT | Roth = 70/30 | Roth = VOO | Roth = QQQM |
|---|---|---|---|---|
| International share of stocks (no MU) | 21.5% | 21.1% | 19.9% | 19.9% |
| Info-tech share of stocks (no MU) | 50.4% | 50.5% | 50.8% | 51.6% |
| LITE share of stocks (look-through) | 31.6% | 31.6% | 31.6% | 31.6% |
| **If MU is still held:** LITE + MU share of all assets | 57.9% | 57.9% | 57.9% | 58.1% |

- **The Roth is ~3.4% of what you own,** so its fund choice moves your household mix by about 1.5 points at
  most.
- **The levers that change your concentration are the LITE (and MU) position sizes and where new taxable money
  goes.** For example, putting the next taxable dollars into VXUS until international is back near your 30%
  target. Those calls are yours.
- **For scale:** LITE's worst replayed hold in this project was −55%. On ~$47k that's about **−$26k, or 15% of
  everything you own,** before any index fund moves.
- **International in taxable is still the right place.** VXUS gets the foreign tax credit there (very roughly
  0.15–0.25%/yr of the international slice). VT in the Roth doesn't waste anything, since VT can't pass the
  credit through anywhere.

## 6. What to set up in Robinhood (you place these; nothing was placed)

**A. Invest the $5,967 already in the Roth**
- **Lump sum:** about 37 shares of VT at ~$160.70. Fractional dollar amounts work. Historically, investing a
  lump sum beat spreading it out about two-thirds of the time.
- **Or spread it:** if a lump sum feels bad, split it into 3 buys over 6 weeks. The cost of waiting is small
  either way.
- The $117 transfer bonus can be invested. The 5-year hold only limits moving it out.

**B. Recurring deposit (Roth IRA → Transfers → Recurring)**
- $250 every 2 weeks from your bank, on payday +1.
- **Tax year 2026** until you hit the 2026 IRA limit of **$7,500** (income limits don't affect you at $99k).
  Then switch to **2027**. You can contribute for 2026 until Apr 15, 2027.
- First, check the app's 2026 contribution total. If most of the $5,967 was contributed for 2026, only about
  6 more deposits fit this year.
- $250 × 26 = $6,500 a year. Maxing $7,500 takes **$289 every two weeks**.
- The 3% Gold match (~$7.50 per deposit, ~$195 a year) needs Gold to stay active ($5/mo). Matched money has
  its own hold period; check its terms before ever moving the account.

**C. Recurring investment (search VT → Trade → Recurring)**
- **VT, $250, every 2 weeks,** funded from the Roth IRA's cash, starting 1–2 business days after the deposit
  lands.
- **If the app offers your bank as the funding source for an IRA recurring investment, that one setting does
  both B and C. Use one method, not both,** or you'll contribute twice.

**D. Housekeeping**
- Turn on **dividend reinvestment** for the Roth.
- Once a month, put any idle match or dividend cash into VT.
- **Never buy VTI, VXUS, LITE or MU inside the Roth,** because of the wash-sale trap in section 1.
- No rebalancing is needed with one fund.

## Assumptions and limits

- **Proxies and returns:** before each ETF existed, its older share class is used, adjusted to the ETF's
  expense ratio (VTSMX/VTSAX→VTI, VGTSX/VTSNX→VXUS, VFINX/VFIAX→VOO, QQQ→QQQM, VIGRX→VUG). Returns are
  total returns with dividends reinvested and are already net of foreign tax withheld.
- **VT's mix:** 62.3/37.7 US/intl, estimated by regressing VT on VTI and VXUS over Oct 2023–Sep 2026
  (tracking error 0.25%/yr). It's used for the Monte Carlo and the pre-2008 proxy. VT's real mix floats with
  market values.
- **API gaps:** Alpha Vantage's VT and VXUS holdings and sector lists are truncated to US listings. VXUS's
  info-tech share (~13%) and the 401(k) mid/small funds' share (~13%) are approximations. LITE and MU count
  as 100% information technology.
- **Household inputs:** the household numbers use your reported figures plus the project's position records.
  They aren't read from Robinhood or Empower.
- **Taxes:** tax effects are estimates. The wash-sale point is settled law for IRAs (Rev. Rul. 2008-5); the
  401(k) version is not. A tax pro should confirm before you rely on harvesting.
- **Not a forecast:** the Monte Carlo spreads (e.g. $241k–$1.36M for VT) are the honest message.

## Files

- `fetch_profiles.py`: caches `ETF_PROFILE` and `GLOBAL_QUOTE` (key from `.env.news`, never printed).
- `analysis.py`: backtests, Monte Carlo, household look-through, correlations.
- `data/raw/`: monthly prices (fetched with the 401(k) study's `fetch.py`). `data/profiles/`: fund profiles
  and quotes.
- `results/results.json`, `results/tables.md`: every number above. `charts/post_covid.png`,
  `charts/since_2008.png`.
