# Options-bot research brief — September 28, 2026

This is a web research brief compiled by a research agent for the new, separate **options track**. It is research only: no trade or real-money recommendation. Vendor and self-reported figures are labeled. Items the agent could not verify are listed at the end. The numbered sources come from the agent's report; the URLs are below.

## Session facts checked directly

- **OPRA access:** Alpaca OPRA options quotes on the free plan returned **HTTP 403** (probe at 11:12 ET).
- **LITE vs SPY option costs** (free "indicative" feed, 10/23–11/13 expiries, 12 contracts nearest the money):

  | | LITE | SPY |
  |---|---|---|
  | Median bid-ask gap | $9.78 (≈$980 per contract) | $0.08 |
  | Gap as share of mid price | 14.2% | 0.6% |
  | Median implied volatility | about 73% | about 14% |

  The indicative feed is approximate, so these are directional only.

## What retail builders automate

- **The wheel** (cash-secured puts, then covered calls once assigned):
  - Common rules: about 0.20–0.30 delta, 30–45 DTE, close at 50% profit or at 21 DTE [1].
  - Alpaca publishes an official wheel template [2].
  - Capital is strike × 100 per contract [3].
  - SPY wheel backtest, 2007–24: 5.6–7.4%/yr vs 10.0% buy-and-hold, with drawdowns of −16% to −39% vs −51%. Most of the return came from the stock [1].
  - Critique: the strategy adds exposure as prices fall [4].
- **Credit spreads and iron condors:** SPX 16/10-delta put spreads at 45 DTE, 2007–24, won 92.5% of trades but returned 9.0%/yr vs 10.1%, with a −39.5% drawdown lasting 833 days [5].
- **0DTE:**
  - Vendor data: 87% of Option Alpha bot positions are opened for a credit [7].
  - One self-reported survivor sells far-OTM strikes and uses stop-limit exits [8].
  - A widely reported blow-up came from increasing size after losses in Dec 2025 [9][10].
- **LLM agents trading through broker MCP servers** is now common: Alpaca, tastytrade, Robinhood [11–13].
- **Paper vs live:** anecdotally, one strategy won 82% on delayed paper data but 45% live [14].

## Evidence beyond anecdotes

| Index | Period | Return | Volatility | Max drawdown | Sharpe | Source |
|---|---|---|---|---|---|---|
| Cboe PUT (put-writing) | 2007–Aug 2026 | 7.1%/yr (S&P TR 11.0%) | 10.7% (15.4%) | −32.7% (−50.9%) | 0.52 (0.61) | [15] |
| Cboe BXM (covered calls) | 1986–Aug 2026 | 8.6%/yr (11.2%) | 10.7% (15.2%) | −35.8% (−50.9%) | 0.56 (0.57) | [16] |

- Both indexes are hypothetical and exclude costs and taxes.
- **Volatility risk premium:** VIX averaged 19.3% vs 15.1% realized volatility, 1990–2018 [17].
- **Retail results:**
  - Retail lost about $2.1B from Nov 2019 to Jun 2021, mainly from buying short-dated options; spread costs were about $6.4B [18].
  - Retail 0DTE SPX trading lost about $241k–$350k per day [19].
  - Option buyers around earnings lose 5–9% [20].
  - Counterpoints: [21][22].

## Brokers and data

- **Alpaca paper:**
  - Level 3 (spreads, condors) is on by default [23]. Multi-leg orders must be covered within the order [6]. Only DAY/GTC orders, and multi-leg orders cannot carry stops [24].
  - Options $0.01+ in the money are auto-exercised; positions without enough buying power are liquidated before expiry [24][25].
  - Paper fills happen at the NBBO with 10% random partial fills and no slippage [28].
  - Historical options data starts Feb 2024 and has no historical quotes [34][35].
  - Real-time OPRA costs $99/mo [33].
- **Robinhood agentic trading:** options since Jun 2026, long orders only, reportedly single-leg only, and no paper mode [13][29–31].
- **Other brokers:** IBKR [39–41], tastytrade [42–44], Tradier [36–38], Schwab (no paper trading through the API, per third parties) [45].
- **Real bid/ask history:**
  - Cheapest: ThetaData at $40/$80/$160 per month [47][48].
  - Spot checks: Databento, with $125 of free credit [52–54].
  - Other providers: ORATS $199–899/mo [49], Cboe DataShop about $300/mo [50][51], Massive (formerly Polygon) $199 for historical quotes [46].

## Screening norms

- **Liquidity:** a bid-ask spread under 5–10% of the premium is tolerable; over 15–20% is costly. Open interest should be in the hundreds [56–58].
- **IV rank and IV percentile** definitions: [59].
- **Earnings:** IV crush example [60].
- **Size:** one contract = 100 shares [3].

## Pitfalls

- Early assignment, especially short calls before an ex-dividend date [63][64]. Alpaca assignment events must be polled [65].
- Pin risk [69] and exercise cutoffs [66].
- Wide spreads [18].
- IV crush [60].
- Buying-power lockup and leverage [3][4].
- Rolling that compounds losses [67][10].
- Live options need separate approval at Alpaca [65].
- PDT replaced by intraday margin rules as of Jun 4, 2026 [68].

## Unverified

- Reddit was blocked, so there are no direct posts from r/thetagang, r/options or r/algotrading.
- The Schwab paper claim is third-party only.
- Robinhood's single-leg limit is from a competitor's review.
- Not confirmed: whether Alpaca paper simulates early assignment, and which data feed its paper fill engine uses.
- The DataShop price comes from a third-party cart check. Databento doesn't publish per-GB rates. ThetaData's pricing page and docs disagree on history depth.
- Some pages carried text aimed at AI agents; it was ignored.

## Sources
1. https://spintwig.com/spy-wheel-45-dte-options-backtest/ · https://wheelstrategy.substack.com/p/cash-secured-put-delta
2. https://github.com/alpacahq/options-wheel
3. https://www.fidelity.com/learning-center/investment-products/options/options-strategy-guide/shortput-cashsecured
4. https://earlyretirementnow.com/2024/09/17/the-wheel-strategy-doesnt-work-options-series-part-12/
5. https://spintwig.com/short-spx-vertical-put-45-dte-s1-signal-options-backtest/
6. https://docs.alpaca.markets/us/docs/options-level-3-trading
7. https://optionalpha.com/blog/0dte
8. https://earlyretirementnow.com/2026/01/30/options-trading-series-part-14-year-2025-review/
9. https://en.wikipedia.org/wiki/David_Chau
10. https://optionstrategist.substack.com/p/a-tragic-tale-of-too-much-risk
11. https://github.com/alpacahq/alpaca-mcp-server
12. https://github.com/tastytrade/tastytrade-mcp
13. https://robinhood.com/us/en/newsroom/robinhood-is-now-open-to-agents/
14. https://forum.alpaca.markets/t/paper-trading-options-pricing/17795
15. https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_PUT-Index.pdf
16. https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_BXM-Index.pdf
17. https://www.cboe.com/insights/posts/white-paper-shows-volatility-risk-premium-facilitated-higher-risk-adjusted-returns-for-put-index/
18. https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13285
19. https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf
20. https://www.timdesilva.me/files/papers/losing_optional.pdf
21. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4682388
22. https://cdn.cboe.com/resources/education/research_publications/Retail_Profitability.pdf
23. https://alpaca.markets/blog/level-3-options-trading-now-available-with-alpacas-trading-api/
24. https://docs.alpaca.markets/us/docs/options-trading
25. https://docs.alpaca.markets/us/docs/options-trading-overview
26. https://alpaca.markets/learn/how-to-trade-0dte-options-on-alpaca
27. https://alpaca.markets/blog/alpaca-introduces-index-options-paper-trading/
28. https://docs.alpaca.markets/us/docs/paper-trading
29. https://robinhood.com/us/en/support/articles/trading-with-your-agent/
30. https://x.com/RobinhoodApp/status/2065441614659482094
31. https://nexustrade.io/blog/robinhood-agentic-trading-mcp-review-20260708
32. https://alpaca.markets/support/what-are-the-fees-associated-with-options-trading
33. https://alpaca.markets/data
34. https://docs.alpaca.markets/us/docs/historical-option-data
35. https://alpaca.markets/sdks/python/api_reference/data/option/historical.html
36. https://tradier.com/individuals/pricing
37. https://docs.tradier.com/docs/market-data
38. https://docs.tradier.com/reference/brokerage-api-trading-place-order
39. https://www.ibkrguides.com/clientportal/aboutpapertradingaccounts.htm
40. https://interactivebrokers.github.io/tws-api/market_data.html
41. https://www.interactivebrokers.com/en/pricing/commissions-options.php
42. https://tastytrade.com/api/
43. https://tastytrade.com/pricing/
44. https://developer.tastytrade.com/docs/sandbox/
45. https://autoview.com/guides/does-schwab-support-paper-trading/
46. https://massive.com/pricing?product=options
47. https://www.thetadata.net/pricing
48. https://thetadata.net/docs/Articles/Getting-Started/Subscriptions.html
49. https://orats.com/data-api
50. https://datashop.cboe.com/option-eod-summary
51. https://stockmarketstack.com/tools/cboe-datashop
52. https://databento.com/pricing
53. https://databento.com/blog/opra-improvements-coming-soon
54. https://concretumgroup.substack.com/p/spx-options-database-databento-vs
55. https://davidariasfinance.com/scripts/free-options-data/
56. https://theoptionsbench.com/guides/how-to-tell-if-an-option-is-liquid/
57. https://www.tradingblock.com/blog/options-liquidity
58. https://support.tastytrade.com/support/s/solutions/articles/43000435395
59. https://support.tastytrade.com/support/s/solutions/articles/43000539059
60. https://www.optionseducation.org/news/the-crush-is-real
63. https://www.optionseducation.org/referencelibrary/faq/options-assignment
64. https://optionalpha.com/learn/dividend-assignment-risk
65. https://blog.traderspost.io/article/alpaca-paper-trading
66. https://www.optionseducation.org/referencelibrary/faq/options-exercise
67. https://robinhood.com/us/en/support/articles/options-rolling
68. https://www.finra.org/rules-guidance/notices/26-10
69. https://en.wikipedia.org/wiki/Pin_risk
