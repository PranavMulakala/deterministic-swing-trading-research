# Is "90% of futures trading is trend following, breakout and opening-range breakout" true? Evidence check (September 30, 2026)

Web research done for the owner's question after a Google/Gemini search. It's general information, not personal investment advice.

**How strong each source is:**
- **[Strong]** peer-reviewed research or regulator data
- **[Moderate]** practitioners or index providers
- **[Weak]** blogs, vendors, or working papers that haven't been peer-reviewed
- **[Unverified]** couldn't be confirmed from the original source

## The short answer
- **The "90%" figure has no source.** No CFTC, CME or academic source sorts futures trading by strategy type.
- **Most futures volume comes from automated market makers and high-frequency firms.** Individuals are a small slice.
- **Trend following has real long-run evidence,** but only as a diversified, many-market, long-and-short portfolio, and it has long dry spells.
- **Published opening-range-breakout results leave out spread and slippage.** Replications that add realistic costs find about zero edge.
- **Large studies of retail day traders find that about 97–99% don't make money.**

## 1. Who actually trades futures
- **[Strong]** A CFTC staff study of all CME electronic futures volume, 2010–2016 (Fett & Haynes, *The Futures Trading Landscape*, 2017, [link](https://www.cftc.gov/sites/default/files/idc/groups/public/@economicanalysis/documents/file/oce_futureslandscape.pdf)):
  - Principal trading firms (mostly automated market makers and high-frequency traders): **51%**
  - Banks and dealers: 16%
  - Asset managers: 8%
  - Individuals: **about 3.5%**, as of June 2016
- **[Strong]** Automated trading systems were on at least one side of **62–67% of equity-index futures volume** (Haynes & Roberts, CFTC, 2015, [link](https://www.cftc.gov/sites/default/files/idc/groups/public/@economicanalysis/documents/file/oce_automatedtrading.pdf)).
- **[Strong]** The CFTC's weekly Traders in Financial Futures report sorts traders by type (dealers, asset managers, leveraged funds, others). It reports positions, not strategies.
- **[Unverified]** Micro E-mini contracts were reportedly about 40% of equity-index contracts traded in 2025. This comes from a search snippet of a CME release; the page didn't load. Micros are 1/10 the size, so their share of dollar exposure is much smaller.

## 2. Trend following ("managed futures" / CTAs)
- **[Strong]** Moskowitz, Ooi & Pedersen, "Time Series Momentum," *Journal of Financial Economics* (2012), [link](https://www.sciencedirect.com/science/article/pii/S0304405X11002613). Across 58 futures markets, returns over the past 1–12 months tend to continue.
- **[Strong/Moderate]** Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following Investing" (AQR 2014; *Journal of Portfolio Management* 2017), [link](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf).
  - Setup: 67 markets, long and short, each scaled to the same risk.
  - Result: 11.2% a year after typical fees, 1880–2013. This is a hypothetical backtest.
- **[Strong, a critique]** Huang et al., "Time series momentum: Is it there?" *JFE* (2020), [link](https://doi.org/10.1016/j.jfineco.2019.08.004). Market-by-market, the evidence is statistically weak.
- **[Moderate]** Real results from the SG Trend Index (the 10 largest trend-following funds, since 2000):
  - About 4.9% a year overall.
  - Roughly flat from 2009 to 2013, and down in 2016 and 2018.
  - +27% in 2022.
  - Worst drop about −21%.
- **What this means for us:** the evidence is for a diversified, low-leverage portfolio across dozens of markets. It says nothing in favor of trading one index intraday.

## 3. Opening range breakout (ORB)
- **[Weak]** Zarattini & Aziz, "Can Day Trading Really Be Profitable?" (SSRN 2023), [link](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622). Not peer-reviewed; Aziz runs a day-trading education business.
  - Rule: trade QQQ in the direction of the first 5-minute bar.
  - Reported a big edge, but modelled **commission only, no spread or slippage**.
- **[Weak]** Zarattini, Barbon & Aziz (SSRN 2024), [link](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284):
  - Plain ORB on all stocks: 3.2% a year, below the S&P 500.
  - Only a hand-built "stocks in play" filter looked strong, again with no slippage.
- **[Weak] Independent replications:**
  - A [GitHub replication](https://github.com/giovannibrusco/zarattini-2023-orb-qqq) matched the QQQ result. Adding 2–4 cents a share of slippage cut the profit from about $139k to about $4.9k, and 76% of it came from 2022 alone.
  - An [MQL5 test](https://www.mql5.com/en/blogs/post/776235) found about zero edge after costs on index CFDs.
- **[Unverified]** Fetna, "Opening-Range Breakout Does Not Survive Trading Costs" (SSRN, Sept 2026), [link](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7428398).
  - Reported: 225 pre-registered ORB versions on 9 futures markets, and **0 of 225 passed after costs**.
  - Only the search summary was read.
- **[Moderate]** Syu et al. (IEEE, about 2019), [link](https://ieeexplore.ieee.org/document/8641124/). Reports profits on index futures at very low assumed costs, after tuning a setting, so data-mining risk.

## 4. What happens to retail day traders
- **[Strong]** Chague, De-Losso & Giovannetti, "Day Trading for a Living?" (2019), [link](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101). Brazilian mini-index futures, people who day-traded on more than 300 days:
  - **97% lost money.**
  - Only 0.4% earned more than a bank teller's wage.
  - No sign that people got better with practice.
- **[Strong]** Barber, Lee, Liu & Odean (*Journal of Financial Markets*, 2014), [link](https://www.sciencedirect.com/science/article/abs/pii/S1386418113000190). Taiwan: **under 1%** of day traders are reliably profitable after fees.
- **[Strong]** ESMA (2018), [link](https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors). **74–89%** of retail CFD accounts lose money.
- **[Moderate]** Topstep's own 2025 disclosure, [link](https://www.topstep.com/risk-disclosure):
  - 16.8% passed the paid evaluation.
  - 33.3% of funded traders got any payout.
  - **0.71%** reached a live account.

## 5. MNQ (Micro E-mini Nasdaq-100) facts

| Item | Value | Source / strength |
|---|---|---|
| Size | $2 × the Nasdaq-100 index | [CME specs](https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.contractSpecs.html) (Strong) |
| Tick | 0.25 point = $0.50 | CME specs (Strong) |
| CME exchange fee | about $0.35 per side | Moderate |
| NFA fee | $0.01 per side (from Jul 2026) | Strong |
| IBKR commission | about $0.25 per side | Moderate |
| All-in cost | about **$1.20 per round trip** (≈ 2.4 ticks), before slippage | — |
| IBKR margin | about **$4,690 intraday / $6,700 overnight** as of Sept 29, 2026 | Secondary source; IBKR's page didn't load |

- **[Unverified]** IBKR reportedly doesn't give the lower intraday margin to cash or IRA accounts.
- **Losses can exceed what you deposit.** This is the standard CFTC risk disclosure (17 CFR 1.55, [link](https://www.law.cornell.edu/cfr/text/17/1.55)).

## Couldn't verify
- The Sept 2026 ORB paper, which was read only through a search summary.
- CME's micro-share figure.
- IBKR's own margin and fee pages, which returned errors.
- The exact SG Trend yearly table.
