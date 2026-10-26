# Data Costs, Licensing, and Real-Time Technology Feasibility for "Real for Markets"

*Research date: October 18, 2026. Unless a document carries its own date, every price below was read from the vendor's or plan administrator's page on Oct 18, 2026. The shared web-search budget ran out partway through; after that only primary pages at known URLs were fetched. Items marked "(search summary)" were taken from search-result summaries of SEC or Federal Register filings and were not opened directly. Where a vendor could not be checked (Finnhub, Benzinga, Kaiko, Barchart, Cboe Global Cloud, Nasdaq Cloud Data Service), it is listed under Gaps rather than assumed.*

## 1. US equities: SIP vs proprietary feeds vs IEX, pro vs non-pro, per-user and enterprise fees, delayed data, and what a startup must sign

### Takeaway
For a non-broker startup, real-time consolidated (SIP) prices cost about $6,500/month in fixed plan fees plus about $3.00 per non-professional user per month today (CTA Tape A + Tape B + UTP Tape C, $1 each). Under the new CT Plan that replaces CTA/UTP on April 1, 2027, the fixed fees are about $7,500/month and per-user fees slide from $0.90 to $0.25 per person per tape. Fifteen-minute delayed stock data has no per-user fees and becomes completely fee-free under the CT Plan. Cheaper real-time options exist: Cboe One at $0.25/user or a $15,000/month digital-media license, Nasdaq Basic, IEX, and vendor-modeled "fair value" prices with no exchange fees. Each one gives up some completeness or accuracy compared with the full SIP.

### Cited Findings
**CTA (Tapes A and B: NYSE-listed and other exchange-listed stocks). Current schedule, no effective date printed:**
- Non-professional subscriber fee: $1.00/month per subscriber on Network A and $1.00 on Network B, payable by the vendor serving the non-pro — [CTA Schedule of Market Data Charges](https://www.ctaplan.com/publicdocs/ctaplan/Schedule_of_Market_Data_Charges.pdf)
- Professional device fees: Network A is $45 (1–2 devices), $27 (3–999), $23 (1,000–9,999) or $19 (10,000+); Network B is $23 — [CTA](https://www.ctaplan.com/publicdocs/ctaplan/Schedule_of_Market_Data_Charges.pdf)
- Per-quote-packet alternative: $0.0075 per packet per network. A vendor may cap it at $1.00 per network per month for each non-pro, and must audit its quote meter — [CTA](https://www.ctaplan.com/publicdocs/ctaplan/Schedule_of_Market_Data_Charges.pdf)
- Redistribution charge: $1,000/month per network. It applies to any entity that makes data available to anyone other than its own employees — [CTA](https://www.ctaplan.com/publicdocs/ctaplan/Schedule_of_Market_Data_Charges.pdf)
- Data access charges, indirect: Network A $750 (last sale) and $1,250 (bid-ask); Network B $400 and $600. Direct: A $1,250/$1,750; B $750/$1,250 — [CTA](https://www.ctaplan.com/publicdocs/ctaplan/Schedule_of_Market_Data_Charges.pdf)
- Non-display fees: Network A $2,000 each for last sale and quotes; Network B $1,000 each — [CTA](https://www.ctaplan.com/publicdocs/ctaplan/Schedule_of_Market_Data_Charges.pdf)
- Broker-dealer enterprise maximum: $686,400/month (A) and $520,000/month (B). It is available only to SEC-registered broker-dealers, for their brokerage customers — [CTA](https://www.ctaplan.com/publicdocs/ctaplan/Schedule_of_Market_Data_Charges.pdf)
- Consolidated volume may be displayed free. If it appears next to non-consolidated prices (e.g., a single-exchange feed), the screen must carry the statement "Real-time quote and/or trade prices are not sourced from all markets." — [CTA](https://www.ctaplan.com/publicdocs/ctaplan/Schedule_of_Market_Data_Charges.pdf)
- CTA's form of vendor contract is referred to as the "Agreement for Receipt and Use of Market Data" — [CTA](https://www.ctaplan.com/publicdocs/ctaplan/Schedule_of_Market_Data_Charges.pdf)

**UTP (Tape C: Nasdaq-listed stocks). Current data policies; the PDF metadata shows a March 10, 2025 label date:**
- Non-pro: $1/month per subscriber. Professional: $24/month (raised April 1, 2018). Per query: $0.0075 — [UTP Data Policies](https://www.utpplan.com/DOC/Datapolicies.pdf)
- Real-time direct access $2,500/month and indirect access $500/month. The external real-time redistributor fee is $1,000/month, in place since Jan 1, 2014 — [UTP](https://www.utpplan.com/DOC/Datapolicies.pdf)
- Delayed data: delayed subscriber usage is "not currently fee liable". The external delayed redistributor fee is $250/month plus a $250/year delayed administrative fee. End-of-day data is not fee liable — [UTP](https://www.utpplan.com/DOC/Datapolicies.pdf)
- Non-pro enterprise cap: $648,000/month. It is available only to vendors registered as broker-dealers — [UTP](https://www.utpplan.com/DOC/Datapolicies.pdf)
- Non-display: $3,500/month per category (electronic trading system, own behalf, on behalf of customers) — [UTP](https://www.utpplan.com/DOC/Datapolicies.pdf)
- A "query" must not auto-update unless each pushed update is recorded, so streaming quotes are metered per update — [UTP](https://www.utpplan.com/DOC/Datapolicies.pdf)
- "Controlled product": the vendor controls both the entitlements and the display. An "uncontrolled product" (e.g., a raw data feed or API to users) needs prior written approval for each recipient — [UTP](https://www.utpplan.com/DOC/Datapolicies.pdf)
- Every subscriber counts as professional unless qualified as non-professional, and non-pro data is licensed only for personal use. The vendor must give each external subscriber a Subscriber Agreement or equivalent, or indemnify the plan by using its own account agreement that carries equivalent protections. Vendors must be able to report each subscriber's pro/non-pro status — [UTP](https://www.utpplan.com/DOC/Datapolicies.pdf)
- The delay interval is 15 minutes. A prominent delay message is required (examples given: "Data Delayed 15 minutes", "Del-15"). Subscriber agreements are not required for delayed or end-of-day data on controlled products — [UTP](https://www.utpplan.com/DOC/Datapolicies.pdf)
- Multi-security derived data is not fee liable today. Single-security derived data is generally fee liable at the underlying rates — [UTP](https://www.utpplan.com/DOC/Datapolicies.pdf)

**Cboe DataShop's combined SIP estimate (stocks):**
- Non-pro real-time about $3.00/month and pro $66–$92/month. Real-time access $3,500/month, real-time redistribution $3,000/month, delayed access $250/year, delayed redistribution $250/month, non-display $9,500/month. Delayed per-user stock fees are listed as "not offered" (i.e., no per-user charge) — [Cboe DataShop SIP fees](https://datashop.cboe.com/sip-fees)
- To get UTP data you sign the UTP Level 1 Vendor Agreement and file a Data Feed Request and a System Description. Billing starts the day after UTP approval — [Cboe DataShop](https://datashop.cboe.com/sip-fees)

**New CT Plan (replaces CTA and UTP on April 1, 2027):**
- The CT Plan becomes operative, with its fees and policies effective, on April 1, 2027. DataCT LLC replaces NYSE and Nasdaq as administrator. New agreements, a Data Usage Agreement and a Distribution Agreement covering Tapes A/B/C, must be signed by March 1, 2027, or the firm loses authorization to receive CT data. The migration portal opened Sept 1, 2026 and licensing opened Oct 1, 2026 — [consolidatedtape.com](https://www.consolidatedtape.com/); notice also on [utpplan.com](https://www.utpplan.com/)
- Professional fee per individual: $26 (Tape A, flat, replacing the $45/$27/$23/$19 tiers), $23 (B), $24 (C) — [CT Plan fee schedule](https://www.consolidatedtape.com/fees/fees-docs.html)
- Non-professional fee per individual, the same scale on every tape, with each rate applying only to users within that band: 1–2,000 at $0.90; 2,001–50,000 at $0.75; 50,001–250,000 at $0.60; 250,001–1,000,000 at $0.40; over 1,000,000 at $0.25 — [CT Plan fees](https://www.consolidatedtape.com/fees)
- Per quote: $0.0075 per packet, capped at the applicable pro or non-pro rate. Non-pro enterprise cap: $648,000 (A), $490,000 (B), $648,000 (C) — [CT Plan fee schedule](https://www.consolidatedtape.com/fees/fees-docs.html)
- Real-time redistributor fee: $1,155/month per tape. Delayed and end-of-day redistribution is not fee liable but still needs an explicit license — [CT Plan fee schedule](https://www.consolidatedtape.com/fees/fees-docs.html); [CT Plan fees](https://www.consolidatedtape.com/fees)
- Indirect access (last sale / bid-ask): Tape A $865/$1,445; Tape B $460/$695; Tape C $230/$345. Direct: A $1,445/$2,025; B $865/$1,445; C $1,155/$1,735. Delayed data access is not fee liable — [CT Plan fee schedule](https://www.consolidatedtape.com/fees/fees-docs.html)
- Non-display, per category, each for last sale and bid-ask: $2,315 (A), $1,155 (B), $2,025 (C) — [CT Plan fee schedule](https://www.consolidatedtape.com/fees/fees-docs.html)
- Using derived data carries no fee; creating derived data is fee liable as non-display use. Consolidated volume display has no fee, nor does delayed or end-of-day display. The display-policy non-compliance fee is $3,000/month — [CT Plan fee schedule](https://www.consolidatedtape.com/fees/fees-docs.html)
- Eliminated: the $250/month delayed redistributor fee, the $250/year delayed administrative fee, and the single-security derived-data fee. Display of derived data is no longer fee liable on any tape — [CT Plan fees](https://www.consolidatedtape.com/fees)
- Policies: classification is use-based, with one qualification and attestation across all tapes. Each natural person is counted once regardless of devices or apps. There is one uniform 15-minute delayed-data license, no usage reporting for delayed or end-of-day redistribution, and attribution guidance for displays, APIs, datasets and AI services — [CT Plan policies](https://www.consolidatedtape.com/policies)
- Date discrepancy: one CT page says the fee schedule was approved June 27, 2026; the fee document header says June 26, 2026 and cites a Second Amendment approved March 26, 2026 — [consolidatedtape.com](https://www.consolidatedtape.com/); [CT Plan fee schedule](https://www.consolidatedtape.com/fees/fees-docs.html)

**Proprietary and single-venue alternatives:**
- Cboe One covers Cboe's four US stock exchanges (BZX, BYX, EDGX, EDGA). Summary (top-of-book) feed: external distribution $5,000/month with user fees credited against it up to that amount; pro $10; non-pro $0.25; data consolidation fee $1,000/month. A Digital Media License costs $15,000/month and covers TV, websites and mobile for informational, non-trading use. Enterprise: $50,000/month — [Cboe One](https://www.cboe.com/market_data_services/us/equities/cboe_one/)
- Cboe One Premium (up to 48 levels of depth): external distribution $12,500, pro $15, non-pro $0.50, Digital Media License $25,000, enterprise $100,000 — [Cboe One](https://www.cboe.com/market_data_services/us/equities/cboe_one/)
- First-time Summary subscribers get one month without the external distribution fee. A Small Retail Broker program serves brokers with up to 10,000 investors — [Cboe One](https://www.cboe.com/market_data_services/us/equities/cboe_one/)
- Cboe says Cboe One quotes are within 1% of the NBBO 97.95% of the time on average (internal analysis using 2026-10-15 data). It gives no latency figures — [Cboe One](https://www.cboe.com/market_data_services/us/equities/cboe_one/)
- NYSE BQT (NYSE, NYSE Arca and NYSE American BBO and trades), from the NYSE pricing guide dated October 9, 2026: per-user access fee $850/month for display-only vendors (or $6,250 full access fee); redistribution $2,500; pro $18; non-pro $1.00; enterprise $50,000; digital media enterprise $65,000. Vendors can credit external user fees against the redistribution fee up to its amount — [NYSE Proprietary Market Data Pricing Guide, Oct 9, 2026](https://www.nyse.com/publicdocs/nyse/data/NYSE_Market_Data_Pricing.pdf)
- Nasdaq Basic, historical fees (search summary; Nasdaq's own pages timed out or returned 404 on Oct 18, 2026). A 2014 filing set non-pro fees at $0.50 (Nasdaq-listed) + $0.25 (NYSE-listed) + $0.25 (NYSE MKT-listed) per month and pro at $13 (Nasdaq-listed). It also set a $1,500/month distributor fee and per-query fees of $0.0025/$0.0015/$0.0015. A 2017 exhibit describes a $100,000/month broker-dealer enterprise license for non-pros — [Federal Register, July 22, 2014](https://www.govinfo.gov/content/pkg/FR-2014-07-22/pdf/2014-17144.pdf); [SEC 34-72620](https://www.sec.gov/file/34-72620)
- Intrinio says Nasdaq Basic covers all US-listed stocks but about 16% of total volume. It lists the exchange fees as $1,500/month for last sale only or $2,000/month with bids and asks; the product is now enterprise-plan only — [Intrinio Nasdaq Basic](https://intrinio.com/products/nasdaq-basic)
- IEX (search summary): real-time TOPS costs $500/month and DEEP $2,500/month, charged since July 1, 2022. DEEP+ was offered free, and a filing proposed $3,500/month from Oct 1, 2025 (whether that took effect is unconfirmed). Delayed data is free — [Federal Register, June 17, 2025](https://www.govinfo.gov/content/pkg/FR-2025-06-17/html/2025-10975.htm); [SEC IEX filing 34-104060](https://www.sec.gov/files/rules/sro/iex/2025/34-104060.pdf)

### Inferences
- **Exchange-fee math if every user gets real-time SIP stock data** (all non-pro, received indirectly through a vendor, last sale plus bid-ask; vendor fees excluded):

| Users | Current CTA+UTP (through Mar 2027) | CT Plan (from Apr 1, 2027) |
|---|---|---|
| 1,000 | $6,500 fixed + $3,000 = **~$9,500/mo** | $7,505 fixed + $2,700 = **~$10,200/mo** |
| 10,000 | $6,500 + $30,000 = **~$36,500/mo** | $7,505 + $23,400 = **~$30,900/mo** |
| 100,000 | $6,500 + $300,000 = **~$306,500/mo** | $7,505 + $203,400 = **~$210,900/mo** |

  The current fixed fees are indirect access ($2,000 A + $1,000 B + $500 UTP) plus redistribution ($1,000 × 3). The CT fixed fees are indirect access ($2,310 + $1,155 + $575) plus redistribution ($1,155 × 3). At 100,000 users that is roughly $3.07 per user today versus $2.11 under the CT Plan.
- **Professional users are expensive.** One pro costs about $92/month today ($45 + $23 + $24) and $73/month under the CT Plan ($26 + $23 + $24). If any users, such as people who sell paid Discord alerts, trade as a business or are licensed, they may need pro classification. The legal researcher covers the definitions.
- **Brokers have a structural edge.** Robinhood-style brokers can cap their non-pro fees under the broker-dealer enterprise maximums ($686,400 / $520,000 / $648,000), which today are limited to registered broker-dealers. A startup pays per user. Whether the CT Plan's enterprise cap is also broker-only is unclear (see Gaps).
- **Cheaper real-time paths for a social app:**
  - Cboe One Summary per-user model, total = max($5,000, users × $0.25) + $1,000: about $6,000/month at 1k or 10k users and about $26,000 at 100k. The $15,000 Digital Media License (informational, non-trading) wins above roughly 60,000 users.
  - Nasdaq Basic: about $1,500/month distributor fee plus about $1/user at historical rates (unverified for 2026).
  - Massive's FMV stream: no exchange fees (see Question 2).
- **Hybrid model:** give free users delayed, modeled (FMV) or Cboe One prices, and entitle only paying or opted-in users to SIP real-time. Exchange fees then scale with paying users. Under the CT Plan the first 2,000 real-time users cost $2.70/month each across three tapes, so even a $5–10/month premium tier covers stock data.
- **Per-query metering on tap:** a snapshot when the user taps, with no auto-refresh, costs $0.0075 per quote packet per tape. A casual user who checks 20 quotes a month costs about $0.15 per tape instead of $0.90, but any streaming "live" view hits the cap quickly.
- **Delayed data is close to free.** Today it costs roughly $250–$500/month in delayed redistributor and admin fees. From April 2027 it is $0 in exchange fees, though a license is still required. It suits the "box score" and history views, but not the live-reaction moment the product depends on.
- **Paperwork:** a startup launching in 2027 must sign the CT Plan Data Usage and Distribution agreements before March 1, 2027, unless a vendor provides display under the vendor's own license. It must also run non-pro qualification (an onboarding attestation) and monthly usage reporting.

### Gaps
- Current official Nasdaq Basic and Nasdaq Last Sale fees: Nasdaq pages returned 404 or timed out, and only 2014–2022 filing figures were found via search summaries.
- Whether access fees apply when a startup receives SIP data through a vendor's websocket rather than a vendor-controlled display. This depends on the vendor contract and classification; Cboe's estimate includes $3,500 of access fees.
- Whether the CT Plan non-pro enterprise cap is limited to broker-dealers, and whether "per-person" counting means entitled users or active users.
- Market share of Cboe One's four venues and of IEX was not found in a primary source.
- NYSE's definition of "digital media enterprise" was not in the pricing guide.

## 2. Data vendors suited to a startup that displays data to the public: pricing, websockets, latency

### Takeaway
Most cheap developer plans (Massive individual, Twelve Data, Tiingo, Alpaca, ThetaData individual) are licensed for personal or internal use only and cannot legally power a public app. Real display licenses start around $1,750–$2,500/month before exchange fees. The notable exception is Massive (formerly Polygon.io): its $2,499/month Stocks Business plan streams a proprietary "fair market value" price and advertises "No Exchange Fees or Approvals". No business vendor checked published hard latency numbers.

### Cited Findings
- Polygon.io rebranded as Massive effective Oct 30, 2025. Existing APIs and accounts keep working and both domains run in parallel (search summary of press release) — [EIN Presswire](https://www.einpresswire.com/article/863823068/polygon-io-is-now-massive); [FISD](https://fisd.net/polygon-io-is-now-massive)
- Massive individual stock plans: Basic $0 (end of day, 5 calls/min), Starter $29 (15-minute delayed, websockets), Developer $79 (adds trades), Advanced $199 (real-time, adds quotes); 20% off annual. Benzinga, TMX and ETF Global partner datasets are $99/month each, individual use — [Massive pricing](https://massive.com/pricing)
- Massive Stocks Business: $2,499/month. It includes unlimited calls, 20+ years of history, flat files, snapshots, and real-time FMV with streaming FMV and minute aggregates, and is listed as "No Exchange Fees or Approvals" — [Massive business pricing](https://massive.com/business)
- Massive real exchange-data expansions: Full Market (SIP) $1,999/month, Nasdaq Basic $1,999, Cboe EDGX $1,999, IEX $499, Full Market Delayed $499, NYSE Imbalances $399, all with additional exchange fees. Financials & Ratios is $699/month. Qualifying startups get 25%+ off the first year; Enterprise is custom — [Massive business pricing](https://massive.com/business)
- Massive FMV is a proprietary, algorithmically derived real-time estimate of a security's fair price, delivered by websocket for stocks, options, forex and crypto, and sold only on Business plans — [Massive FMV docs](https://massive.com/docs/websocket/stocks/fair-market-value.md)
- Databento plans:
  - Usage-based: live data billed per message plus pass-through license fees, but not available for its US Equities dataset.
  - Standard: $199/month, live data with no license fees, apparently personal use on up to 2 devices.
  - Plus: $1,750/month in license fees, annual contract, adds external distribution and real-time and delayed distribution rights.
  - Unlimited: $4,500/month.
  - Redistribution rights vary by dataset, and most can be redistributed after 24 hours. No numeric latency claims appear on the page — [Databento pricing](https://databento.com/pricing)
- Alpaca, individual plans: the free plan is real-time IEX only, with 30 websocket symbols and indicative options. Algo Trader Plus ($99/month) covers all US exchanges plus OPRA with unlimited websocket symbols — [Alpaca data](https://alpaca.markets/data); [Alpaca market data docs](https://docs.alpaca.markets/docs/about-market-data-api)
- Alpaca Broker API data tiers: Standard is real-time IEX or 15-minute delayed SIP, with options +$1,000/month. StandardPlus3000 is $500/month; StandardPlus5000 is $1,000/month with options; StandardPlus10000 is $2,000/month. Neither page addresses showing data to non-customers — [Alpaca market data docs](https://docs.alpaca.markets/docs/about-market-data-api)
- Twelve Data individual plans: Basic $0, Grow $79, Pro $229, Ultra $999/month, labeled internal display or non-display use. Commercial pricing is on a separate page that was not retrieved, and the page's credit figures are internally inconsistent — [Twelve Data pricing](https://twelvedata.com/pricing)
- Tiingo: Starter $0, Power $30/month, internal commercial $50/month ($499/year). Licenses cover internal use only, with no display or sharing; redistribution is priced per product or through sales. It offers an IEX feed and a firehose — [Tiingo pricing](https://www.tiingo.com/about/pricing)
- Intrinio: Nasdaq Basic is enterprise-plan only with "sub-second latency". It also lists 15-minute delayed SIP (100% of volume, "minimal exchange fees"), delayed Cboe One, IEX real-time, and "EquitiesEdge" (real-time with no exchange, per-user or display fees at one flat monthly rate, amount not listed) — [Intrinio](https://intrinio.com/products/nasdaq-basic)
- Alpha Vantage premium: $49.99–$249.99/month for 75–1,200 requests/min, with annual plans at ten months' price. Realtime and 15-minute delayed US data need a separate entitlement process, and commercial display terms are not stated — [Alpha Vantage premium](https://www.alphavantage.co/premium/)
- Cboe DataShop sells SIP access directly. Applicants file the UTP agreements through it, and no charges apply until approvals are processed — [Cboe DataShop](https://datashop.cboe.com/sip-fees)

### Inferences
- **Lowest-cost legal "live price" for a public app at any user count:** Massive Stocks Business at $2,499/month, or about $1,875 with the startup discount. FMV is a modeled estimate, not an exchange quote, so it can differ from the price a user sees in Robinhood. It should be labeled, and the founder must confirm display rights and user caps in the contract.
- **Real consolidated prices:** Massive Business + Full Market costs about $4,500/month in vendor fees, plus the exchange fees in Question 1. Databento Plus is $1,750/month in license fees plus data usage.
- **Individual-tier stacks are not legal for public display.** Many hobby "stock social" apps prototype on Alpaca free, Massive $29, Tiingo or Twelve Data. These plans prohibit showing data to others, so the MVP budget must assume a business license from day one, or a delayed or modeled product.
- **"Fast" will be judged on what users compare against.** No vendor published p50/p99 feed latency, so the founder should benchmark finalists side by side against the Robinhood app.

### Gaps
- Finnhub (pricing page did not render), Barchart OnDemand (empty page), Nasdaq Cloud Data Service, Cboe Global Cloud, Xignite, QuoteMedia and dxFeed pricing were not retrieved.
- Massive Business display rights, user limits and websocket latency for FMV; Massive options and crypto business pricing (those tabs did not render).
- Whether Databento Plus includes or passes through exchange per-user fees for external display, and its usage charges for US equities.
- Twelve Data and ThetaData commercial pricing.
- Real-world costs and latency reports from r/algotrading and Hacker News were not gathered because the search budget ran out.

## 3. Options (OPRA): real-time and delayed display costs, vendors, unusual options activity

### Takeaway
OPRA charges $1.25 per non-professional user per month (tiered down above 75,000 users) plus a $1,500/month redistribution fee, or $650 for a query-only service with no auto-refresh. Usage-based billing caps at $1.25 per non-pro. Delayed options data carries no per-user fees, but OPRA's own schedule applies the redistribution fee to delayed redistribution too, while a 2026 vendor guide says delayed redistribution is fee-free. Cheap vendor plans are personal use only. Unusual-options-flow APIs start around $750/month.

### Cited Findings
- **OPRA fee schedule:**
  - Professional: $31.50 per display device (since Jan 1, 2018).
  - Non-professional, by band: up to 75,000 at $1.25; 75,001–150,000 at $1.15; 150,001–250,000 at $1.00; 250,001–500,000 at $0.75; above 500,000 at $0.60.
  - Usage-based alternative: $0.0075 per quote packet or $0.03 per full options chain, capped at $1.25/month per non-pro. Requests for delayed and historical data are not counted.
  - Redistribution: $1,500/month, or $650 for a "query service only" with no auto-refresh. It applies to redistribution "whether on a current or delayed basis"; only historical-only redistribution is exempt.
  - Access and other fees: indirect access $600 for pros receiving a feed; direct access $1,000; non-display $2,000 per category; hosted-solution fees $100 each or $10,000 enterprise (current data), $50 or $5,000 (delayed).
  - Data counts as delayed 15 minutes after transmission and as historical after the next trading day's open — [OPRA Fee Schedule](https://cdn.opraplan.com/documents/OPRA_Fee_Schedule.pdf)
- OPRA's website says it charges no usage-based or device-based fees for delayed data — [OPRA](https://www.opraplan.com/)
- ThetaData's guide (May 29, 2026) says there are no OPRA fees for using or redistributing data delayed more than 15 minutes, though vendor registration may be needed. It gives pro $31.50, non-pro $1.25 (ThetaData pays this for its own non-pro subscribers), redistributor $1,500 or $650 query-only, and non-display $2,000/category, and says commercial users must contact sales and register with OPRA — [ThetaData OPRA fee guide](https://thetadata.net/articles/2026-05-29-opra-fee-guide-for-options-market-data). On delayed redistribution this **conflicts with** the [OPRA Fee Schedule](https://cdn.opraplan.com/documents/OPRA_Fee_Schedule.pdf) and with [Cboe DataShop](https://datashop.cboe.com/sip-fees), which lists delayed options redistribution at $650.
- ThetaData individual options plans: Value $40, Standard $80, Pro $160/month, all real-time, personal use only with no redistribution. Commercial use is handled separately — [ThetaData pricing](https://www.thetadata.net/pricing)
- Massive individual options plans: Starter $29 and Developer $79 (15-minute delayed, real-time Greeks and IV), Advanced $199 (real-time quotes, "Non-pros only"), all individual use. Business options pricing was not visible — [Massive options pricing](https://massive.com/pricing?product=options)
- Alpaca Algo Trader Plus ($99/month, individual) includes real-time OPRA. Broker API options data costs +$1,000/month on the Standard tier — [Alpaca market data docs](https://docs.alpaca.markets/docs/about-market-data-api)
- Unusual Whales for Business:
  - Startup: $750/month ($625/month billed annually), 160,000 requests/day, websocket, options order flow, congressional and insider trades, labeled "personal or commercial use"; redistribution needs approval.
  - Startup + Kafka: $3,000/month ($2,500 annually).
  - Professional/Enterprise: custom, with delayed data available — [Unusual Whales for Business](https://unusualwhales.com/pricing/enterprise). A third-party guide citing $150/month as of June 2026 conflicts with this (search summary, unverified).
- Alpha Vantage lists a "Realtime Options Trending" endpoint among its options APIs — [Alpha Vantage documentation](https://www.alphavantage.co/documentation/)

### Inferences
- **OPRA exchange fees if every user streams real-time option quotes** (vendor fees excluded):

| Users | Calculation | Monthly |
|---|---|---|
| 1,000 | $1,500 + 1,000 × $1.25 | ~$2,750 |
| 10,000 | $1,500 + 10,000 × $1.25 | ~$14,000 |
| 100,000 | $1,500 + 75,000 × $1.25 + 25,000 × $1.15 | ~$124,000 |

- **Query-only design** (tap to load a chain, no auto-refresh) qualifies for the $650 redistribution rate. Per-chain usage fees ($0.03 per chain, capped at $1.25) are much cheaper for casual users.
- **Buy unusual-options-activity alerts instead of computing them.** Computing them from raw OPRA trades is a non-display or derived use ($2,000/category under OPRA) and means handling the full OPRA firehose. Buying the feed (Unusual Whales about $750/month) is cheaper for an MVP, subject to approval to show it to users.
- **Options are the founder's home turf** (paid Discord options-alert groups). A credible wedge could show delayed or query-only chains to everyone and real-time chains to paying users.

### Gaps
- The official answer on whether OPRA's $1,500/$650 redistribution fee applies to a delayed-only startup; sources conflict, so confirm with OPRA.
- Massive options Business pricing, ThetaData commercial pricing, and Benzinga's unusual options activity API pricing (Benzinga's API page returned 403).
- Cheddar Flow, FlowAlgo and Tradytics API availability and terms.

## 4. Crypto: exchange websockets and aggregators

### Takeaway
Crypto is the cheapest asset class to show live. Major exchanges' public websockets need no authentication or fee, and aggregator commercial licenses run $29–$999/month with attribution and no-resale clauses. The display and redistribution terms of the exchange feeds themselves could not be verified.

### Cited Findings
- Coinbase Exchange: the market data feed (`wss://ws-feed.exchange.coinbase.com`) needs no authentication, while the "direct" feed is authenticated. Channels include ticker, level2 and heartbeat. Clients must subscribe within 5 seconds and must handle dropped or out-of-order messages. The docs page has no redistribution terms, and Coinbase's market-data legal page returned 403 — [Coinbase websocket overview](https://docs.cdp.coinbase.com/exchange/websocket-feed/overview)
- Kraken websocket v2 ticker: no auth fields in its subscribe examples. It carries bid/ask, last price and 24-hour stats, and updates on every trade or on best bid/offer changes. The page has no rate-limit or redistribution terms — [Kraken WS v2 ticker](https://docs.kraken.com/api/docs/websocket-v2/ticker)
- CoinGecko API:
  - Demo: free, attribution required, 60-second freshness.
  - Basic: $35/month ($29 annual), 100k credits, 5 websocket sockets, 10-second freshness.
  - Analyst: $129/month, 500k credits, 10 sockets, real-time.
  - Lite $499 (2M credits) and Pro $999 (5M credits).
  - Paid plans must prominently show "Data provided by CoinGecko" with a link and may not resell or sub-license the API. Redistribution or white-label needs Enterprise — [CoinGecko API pricing](https://www.coingecko.com/en/api/pricing)
- CoinMarketCap API:
  - Basic: free, 60-second updates. Builder: $29, 60-second updates.
  - Startup: $79/month, real-time, 10 websocket connections.
  - Growth $299, Professional $699, Enterprise custom.
  - Commercial licenses cover one product with up to 100,000 users, and data must be an integrated part of a larger product, never a standalone resale — [CoinMarketCap API pricing](https://coinmarketcap.com/api/pricing/)
- Alpaca's free market data plan includes crypto, and Tiingo offers a crypto firehose, but Tiingo's licenses are internal use only — [Alpaca data](https://alpaca.markets/data); [Tiingo pricing](https://www.tiingo.com/about/pricing)

### Inferences
- **MVP crypto stack:** CoinMarketCap Startup ($79) or CoinGecko Analyst ($129) for licensed display, plus direct Coinbase and Kraken websockets for a tick-level "tape" if their terms allow display (verify).
- **At 100,000 users,** CoinMarketCap's 100k-user commercial cap and CoinGecko's no-redistribution clause probably mean an Enterprise plan.
- **24/7 crypto keeps the "live game" running on weekends,** when stock markets are closed. That matters for an engagement product modeled on live sports.

### Gaps
- Coinbase, Kraken and Binance.US terms on displaying or redistributing their market data in third-party apps; Binance.US websocket details.
- Kaiko pricing (enterprise, not public; not retrieved) and Massive crypto business pricing.

## 5. Event data for auto-generated "plays": news, filings, halts, macro calendar, earnings, live call audio

### Takeaway
Many of the best "play" triggers are free and fast. EDGAR's submissions API usually reflects a new filing within a second; Nasdaq's halt RSS refreshes every minute; Fed meeting calendars are public. Paid news (Benzinga) and live earnings-call audio and transcripts (Quartr) have no published prices, and rights to rebroadcast earnings-call audio could not be confirmed.

### Cited Findings
- EDGAR APIs on data.sec.gov are free and need no authentication or API keys. The submissions API typically updates in under a second after dissemination, and XBRL in under a minute, with longer delays at peak times. Bulk ZIPs are rebuilt nightly around 3:00 a.m. ET. CORS is not supported, so calls must come from a server — [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- SEC fair-access rules allow at most 10 requests/second, and scripts must declare a User-Agent with a company name and contact email. A fee-based EDGAR Public Dissemination Service (PDS) exists for push delivery — [SEC Accessing EDGAR Data](https://www.sec.gov/os/accessing-edgar-data)
- EDGAR's "Latest Filings" Atom feed lists recent filings with form type, company, CIK, accession number and timestamps (40 entries covering 20 unique filings when checked) — [EDGAR latest filings feed](https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom)
- Nasdaq's trading-halt RSS has a 1-minute TTL. Each item carries symbol, halt date and time, market, reason code, pause threshold and resumption times; the Oct 18, 2026 snapshot had 16 items — [Nasdaq halts RSS](https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts)
- Halt codes: T1 news pending; T2 news released; T12 additional information requested; H10 SEC suspension; H11 regulatory concern; LUDP volatility pause; LUDS straddle volatility pause; M volatility pause for an exchange-listed issue; IPO1 IPO not yet trading — [Nasdaq halt codes](https://www.nasdaqtrader.com/Trader.aspx?id=TradeHaltCodes)
- Remaining FOMC meetings: Oct 27–28 and Dec 8–9, 2026 (December includes projections). The 2027 meetings are Jan 26–27, Mar 16–17, Apr 27–28, Jun 8–9, Jul 27–28, Sep 14–15, Oct 26–27 and Dec 7–8. Dates are tentative, and minutes come out three weeks after each decision — [Federal Reserve FOMC calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
- Alpha Vantage lists NEWS_SENTIMENT, earnings call transcripts, earnings and IPO calendars, and CPI, nonfarm payroll and fed funds endpoints — [Alpha Vantage documentation](https://www.alphavantage.co/documentation/). Premium plans cost $49.99–$249.99/month, and commercial display terms are not stated — [Alpha Vantage premium](https://www.alphavantage.co/premium/)
- Benzinga data is available through Massive at $99/month per dataset for individual use; business pricing is by contact — [Massive pricing](https://massive.com/pricing); [Massive business](https://massive.com/business). Benzinga's own API page returned 403.
- Tiingo's News API has 3 months of queryable history; commercial clients needing up to 15 years must contact sales. Standard licenses are internal use only — [Tiingo pricing](https://www.tiingo.com/about/pricing)
- Quartr API covers live audio of earnings calls, conferences, capital markets days and AGMs, plus word-by-word live transcripts described as "near-zero latency". It adds archived audio and transcripts, filings, slides and AI summaries for 16,000+ companies in 65+ markets. Pricing is sales-led (enterprise and bundle options), and neither page covers rights to display or rebroadcast audio — [Quartr API](https://quartr.com/api); [Quartr pricing](https://quartr.com/pricing)

### Inferences
- **Mapping plays to sources** (the "play-by-play" equivalent):

| Play | Source | Cost |
|---|---|---|
| Price and volume spikes | Market data feed (derived) | Included in data plan |
| Halt or resume | Nasdaq RSS, about 1-minute polling | Free |
| SEC filing just dropped (8-K, Form 4, S-1) | EDGAR submissions API | Free, under 1 second |
| Fed decision or CPI print | Fed and BLS calendars | Free |
| Headline | Benzinga via a vendor | Paid, price unknown |
| Earnings call live quote | Quartr live transcript | Paid, price unknown |
| Unusual options flow | Unusual Whales | ~$750/month |

- **Halts:** the 1-minute RSS TTL means halts arrive slower than in broker apps. Instant halt and LULD alerts would need real-time SIP messages (not verified here).
- **Earnings audio:** the safest MVP is to link to or embed the company's own IR webcast and post licensed transcript snippets as "plays", rather than rebroadcasting audio, until Quartr (or similar) confirms display rights in writing.

### Gaps
- Benzinga, Finnhub and other news API prices; BLS release-schedule page (not fetched); earnings-calendar vendor prices (e.g., Wall Street Horizon); EDGAR PDS subscription cost.
- Rights to rebroadcast company earnings webcasts, and Quartr's license terms and price.
- Latency of SIP halt and LULD messages compared with the Nasdaq RSS.

## 6. Charting: TradingView Lightweight Charts, Advanced Charts and widgets, alternatives

### Takeaway
TradingView Lightweight Charts is free under Apache-2.0, including commercial use, but requires a visible TradingView attribution link; an on-chart logo option satisfies it. Advanced Charts is free for companies' public web projects but carries TradingView branding and has no trading. Trading Platform, which allows trading from the chart, is proprietary with an unstated cost. None of them includes market data.

### Cited Findings
- Lightweight Charts is Apache-2.0. The license requires naming TradingView as the product's creator, including the NOTICE-file attribution, and linking to tradingview.com on a page users can reach. The `attributionLogo` chart option puts that link on the chart and satisfies the requirement — [Lightweight Charts on GitHub](https://github.com/tradingview/lightweight-charts)
- TradingView's comparison of its charting products:
  - Lightweight Charts: personal and commercial use; streaming updates with your own data.
  - Advanced Charts: proprietary and free, but companies only, for public web projects or apps; no personal, hobby, study or testing use; self-hosted with your own data; no direct trading; TradingView logo.
  - Trading Platform: everything in Advanced Charts plus trading from the chart through broker API integration; needs a datafeed; branding can be turned off; cost not stated.
  - Widgets: TradingView-hosted iframes with data included — [TradingView charting libraries](https://www.tradingview.com/free-charting-libraries/)
- Extra real-time exchange data bought on TradingView works only on the TradingView website, not in widgets — [TradingView pricing](https://www.tradingview.com/pricing/)
- TradingView consumer plans (billed annually): Basic $0, Essential $12.95/month, Plus $29.95, Premium $59.95, Ultimate $199.95. Real-time exchange data (Nasdaq, NYSE, CME and others) is a separate add-on, and only Ultimate is available to professional users — [TradingView pricing](https://www.tradingview.com/pricing/)

### Inferences
- Lightweight Charts gives the founder the TradingView look he likes at $0, with only an attribution link. Its cost is engineering time plus licensed data.
- Widgets are not a substitute for an app's own data. They show TradingView's data on TradingView's terms and can't be used to build "every play" overlays.
- Advanced Charts could be a later upgrade (free for a company's public site). Trading Platform licensing matters only if the app adds in-chart trading.

### Gaps
- Licensing and pricing for Highcharts Stock, SciChart, amCharts, KLineCharts and ChartIQ were not retrieved.
- Lightweight Charts' current version and bundle size are not stated on its README; it calls its size close to that of static images.

## 7. Real-time architecture: fan-out, managed-service pricing, achievable and perceivable latency, engineering posts, and the MVP cost picture

### Takeaway
Fanning out ticks and chat to 100,000+ users is a solved problem. Open-source stacks (Elixir/Phoenix as Discord uses, Centrifugo in Go) have public benchmarks of 1–2 million connections on modest hardware. Managed services (Ably, Pusher, Stream) are the fastest way to start, but their per-message or per-user pricing grows with fan-out and becomes a large bill at 100,000 users. A realistic tick-to-screen budget of about 100–300 ms is achievable (inference). Users perceive under 100 ms as instant, so beyond a solid baseline, speed is not the differentiator; whether the price is real-time, delayed or modeled matters far more.

### Cited Findings
**Engineering posts and benchmarks:**
- Discord reached nearly 5 million concurrent users with millions of events per second. Each user has a websocket "session" process and each server ("guild") has an Elixir process that fans out to sessions; one Erlang VM hosted up to 500,000 sessions. Its Manifold library batches sends by destination node and spreads them across cores while preserving order. A semaphore applies backpressure so overloaded services fail fast. Lesson: publishing from one large process can take seconds at peak, so the sending must be distributed — [Discord: scaling Elixir to 5M concurrent users](https://discord.com/blog/how-discord-scaled-elixir-to-5-000-000-concurrent-users)
- Discord's Midjourney server had more than 10 million members with over 1 million online. Fan-out cost grows roughly quadratically with server size: 1,000 online users posting once each creates 1 million notifications. "Relays" handle up to 15,000 sessions each, and making about 90% of user-guild connections "passive" (no updates until the user opens the server) cut fan-out work by about 90% — [Discord: Maxjourney](https://discord.com/blog/maxjourney-pushing-discords-limits-with-a-million-plus-online-users-in-a-single-server)
- Phoenix (Elixir) held about 2 million websocket connections on one 40-core, 128 GB server. After sharding pub/sub, a broadcast reached 2 million subscribers in about 1 second (over 5 seconds before sharding) — [Phoenix: road to 2M websocket connections](https://phoenixframework.org/blog/the-road-to-2-million-websocket-connections)
- Centrifugo (Go, open source) handled 1 million websocket connections delivering about 500,000 messages/second (28 million per minute, ~100-byte messages) with 200 ms p99 delivery latency. That took 20 pods using about 40 CPUs and 27 GB RAM (about 30 KB per connection) plus 5 Redis shards at about 0.32 CPU each — [Centrifugo million-connection benchmark](https://centrifugal.dev/blog/2020/02/10/million-connections-with-centrifugo)
- Slack uses stateful Channel Servers assigned by consistent hashing, plus regional Gateway Servers that hold websocket subscriptions. A message goes from webapp to admin server to channel server to every subscribed gateway and then to clients. Global delivery takes about 500 ms, with tens of millions of connected clients — [Slack Engineering: Real-time Messaging](https://slack.engineering/real-time-messaging/)

**Managed service pricing:**
- Ably:
  - Free: 200 concurrent connections, 6M messages/month.
  - Standard: $29/month plus usage, 10k connections.
  - Pro: $399/month plus usage, 50k connections.
  - Enterprise: custom, with a 99.999% SLA.
  - Usage rates: messages $2.50 per million (as low as $0.50 with volume); connection-minutes $1.00 per million; channel-minutes $1.00 per million.
  - Ably advertises 6.5 ms message delivery latency, not as an SLA — [Ably pricing](https://ably.com/pricing)
- Ably counts 1 inbound message per publish plus 1 outbound per subscriber that receives it: 1 publish to 10 subscribers is 11 messages, or 12 with echo. Billing rounds message size up to 5 KiB chunks — [Ably message counting](https://ably.com/docs/platform/pricing/message-counting)
- Pusher Channels plans:

| Plan | Price/month | Concurrent connections | Messages/day |
|---|---|---|---|
| Sandbox | Free | 100 | 200k |
| Startup | $49 | 500 | 1M |
| Pro | $99 | 2,000 | 4M |
| Business | $299 | 5,000 | 10M |
| Premium | $499 | 10,000 | 20M |
| Growth | $699 | 15,000 | 40M |
| Plus | $899 | 20,000 | 60M |
| Growth Plus | $1,199 | 30,000 | 90M |
| Enterprise | Custom | — | — |

  Source: [Pusher Channels pricing](https://pusher.com/channels/pricing/)
- Stream Chat:
  - Build: free, 1,000 MAU, 100 concurrent connections.
  - Start: $399/month annual or $499 monthly, 10,000 MAU, 500 concurrent.
  - Elevate: $599/$675, same limits.
  - Overage: $0.09 per extra MAU and $0.99 per concurrent connection over the limit.
  - A "Maker" account is free for teams under 5 people with under $10k monthly revenue — [Stream Chat pricing](https://getstream.io/chat/pricing/)
- Cloudflare Durable Objects:
  - Requests: $0.15 per million after 1M included.
  - Duration: $12.50 per million GB-seconds after 400,000 included, with each object billed as 128 MB.
  - Outgoing websocket messages are free; incoming messages bill at 20:1.
  - The hibernation API stops duration charges while idle.
  - The examples include a $5/month minimum — [Cloudflare DO pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/)
- Durable Object limits: a soft limit of 1,000 requests/second per object, and received websocket messages up to 32 MiB. The maximum number of websockets per object is not stated — [Cloudflare DO limits](https://developers.cloudflare.com/durable-objects/platform/limits/)
- DigitalOcean server prices for self-hosting: Basic $24/month (2 vCPU, 4 GB, 4 TB transfer) and $48 (4 vCPU, 8 GB, 5 TB); CPU-Optimized $84 (4 vCPU, 8 GB, 5 TB) and $168 (8 vCPU, 16 GB, 6 TB). Inbound bandwidth is free — [DigitalOcean droplet pricing](https://www.digitalocean.com/pricing/droplets)

**What latency users can perceive:**
- Under 0.1 s feels instantaneous; under 1 s keeps the user's flow of thought; around 10 s is the limit of attention (Jakob Nielsen, 1993, updated 2014) — [NN/g response time limits](https://www.nngroup.com/articles/response-times-3-important-limits/)
- Google's RAIL model: respond to input within 100 ms (handlers within 50 ms) and produce each frame in about 10 ms of a 16 ms (60 fps) budget. 0–100 ms feels immediate and 1,000 ms+ loses focus — [web.dev RAIL](https://web.dev/articles/rail)
- People can identify images shown for as little as 13 ms (MIT, Mary Potter, Jan 2014). That is about recognition, not about reacting to a price change — [MIT News](https://news.mit.edu/2014/in-the-blink-of-an-eye-0116)
- Broker-side order processing: Alpaca advertises 1.5 ms order processing on its OMS v2 (its own marketing figure) — [Alpaca Broker API](https://alpaca.markets/broker)

### Inferences
- **Realistic tick-to-screen budget for a web or mobile MVP:**

| Hop | Estimate | Basis |
|---|---|---|
| Exchange to SIP or vendor | Microseconds to a few ms | Not verified (see Gaps) |
| Vendor websocket to your ingest server, same region | Single-digit to tens of ms | Not verified |
| Your fan-out layer | ~6.5 ms (Ably claim) to ~200 ms p99 (Centrifugo under heavy load) | Cited; Slack's global ~500 ms is the slow end for chat |
| Last mile to the phone | Tens of ms | Not verified |
| Render one frame | 10–16 ms | RAIL |

  A well-built app should land around 100–300 ms median from vendor tick to pixels, under the 1-second "flow" threshold and near the 100 ms "instant" threshold. Below that, gains are invisible to users.
- **Throttle the stream.** Since a frame is about 16 ms and people cannot read prices that fast, conflating ticks to roughly 4–10 updates per second per symbol, and batching reactions every 100–250 ms, cuts message volume 10–100× with no visible loss.
- **Chat in hot rooms grows like Discord's guilds.** It needs fan-out relays, passive or lazy subscriptions for rooms not on screen, and aggregated reaction counts instead of one message per reaction.
- **Assumptions behind the infrastructure cost estimates** (not sourced; adjust as needed):
  - About 5% of monthly active users connected on average during market hours (10% at peak).
  - About 2 messages/second delivered per connected user (conflated price updates plus chat and reactions), each well under 5 KiB.
  - 6.5 hours × 21 trading days = 491,400 market-seconds per month.

| MAU | Avg / peak concurrent | Outbound messages/month | Ably (list $2.50/M; volume $0.50/M) | Pusher plan | Self-hosted Centrifugo or Phoenix (DigitalOcean) | Stream Chat for chat |
|---|---|---|---|---|---|---|
| 1,000 | 50 / 100 | ~49M | ~$150–$400 | Pro $99 | 1 × $24–$48 | Free tier |
| 10,000 | 500 / 1,000 | ~491M | ~$1,260 list, ~$275 volume | Growth $699 | ~$100–$150 (2 servers) | ~$900–$1,000 (Start + concurrency overage) |
| 100,000 | 5,000 / 10,000 | ~4.9B | ~$12,700 list, ~$2,900 volume (Pro base) | Beyond Growth Plus, Enterprise | ~$250–$400 (2–3 × $84 CPU-optimized plus Redis) | ~$18,000 list (90k extra MAU × $0.09 + 9,500 extra connections × $0.99), so self-host or negotiate Enterprise |

  - Ably's range at 1,000 MAU includes inbound publishes. The Pusher plan choice assumes Pusher, like Ably, counts each delivery; that is not verified.
  - Self-hosting: the 100k-MAU peak (about 20k messages/second to 10k connections) is about 4% of Centrifugo's benchmark load. Bandwidth of about 0.75 TB/month fits inside the included transfer.
  - Cloudflare Durable Objects: about $170/month for 200 live symbol rooms at any viewer count, because outgoing messages are free. Hot symbols must be sharded because of the 1,000 requests/second soft limit.
- **Combined MVP monthly cost, two ends of the range** (inference from the figures in Questions 1–7):

| MAU | Lean | Full real-time for every user |
|---|---|---|
| 1,000 | **~$3.5k–$6.5k/mo** (includes OPRA delayed/query-only redistribution of $650–$1,500, delayed SIP fees of ~$250–$500 until the CT Plan, and the optional $750 Unusual Whales feed at the top end) | **~$17k–$18k/mo**: Massive Business + Full Market ~$4.5k + SIP ~$9.5k + OPRA ~$2.75k + crypto/events/infra ~$0.5k–$1k |
| 10,000 | **~$3.5k–$8.5k/mo** (top end buys Ably and Stream) | **~$50k–$57k/mo**: $4.5k + SIP $30.9k–$36.5k + OPRA $14k + ~$1–2k |
| 100,000 | **~$5k–$38k/mo** (low end self-hosts; high end buys Ably and Stream at list price) | **~$345k–$465k/mo**: $4.5k + SIP $210.9k (CT Plan) to $306.5k (current) + OPRA $124k + ~$5k–$30k |

  - The lean stack is Massive FMV $2,499 (~$1,875 with the startup discount), Full Market Delayed $499, delayed or query-only options, CoinGecko or CoinMarketCap at $79–$129, free EDGAR, halt and Fed feeds, Alpha Vantage $50–$250 for calendars and news sentiment, an optional Unusual Whales $750, and infrastructure plus chat at $25–$400.
  - At 10,000 MAU the lean stack is the same, plus chat if bought.
  - At 100,000 MAU the lean stack may need enterprise upgrades from Massive and CoinMarketCap.
  - **Hybrid** (realistic): give real-time SIP and OPRA only to paying users. At 100,000 MAU with 5,000 subscribers, stocks cost about $19.7k (CT Plan) and options about $7.75k, for roughly $27k/month on top of the lean base. A $10/month tier at 5% conversion ($50k/month) covers it.
- **Kafka, NATS and Redis** fit behind the websocket edge for ingest, replay and cross-node pub/sub, as Centrifugo uses sharded Redis. None of the cited systems delivers to end users directly from Kafka.

### Gaps
- No Robinhood, Stocktwits, TradingView or sports-app engineering posts were retrieved; robinhood.engineering now redirects to the Robinhood newsroom, and the search budget ran out.
- Measured SIP and vendor feed latency, and typical US last-mile round-trip times. The UTP site lists a "Latency Charts" section, but no figures were shown.
- Pusher's message-counting rule, the maximum websockets per Durable Object, and managed Redis and cloud egress prices.
- All concurrency and message-rate assumptions above are unsourced and should be validated with a prototype.

## 8. Adding trading later without becoming a broker: broker APIs, aggregators, latency, economics, deep links

### Takeaway
Three paths avoid becoming a broker-dealer:
- Referral or deep-link to brokers, which is TradingView's lead-generation model.
- An aggregator: SnapTrade costs $2 per connected user per month with trading where the brokerage supports it.
- A broker-as-a-service: Alpaca Broker API, where Alpaca is the FINRA/SIPC broker and the app gets accounts, KYC and stock, options and crypto trading. Its partner pricing is unpublished.

Plaid Investments is read-only. No third-party stock-trading API from Robinhood could be verified.

### Cited Findings
- Alpaca Broker API supports onboarding with KYC-as-a-service and business accounts. It trades stocks (11k+, fractional, extended and 24/5 hours), options levels 1–3, 35+ crypto coins (24/7) and fixed income. Partners choose fully disclosed, omnibus or "OmniSub" account models. It offers SSE events and FIX, and claims 1.5 ms order processing, 600,000+ daily orders self-cleared (April–May 2025) and 99.99% uptime since January 2025. Alpaca Clearing is a FINRA/SIPC self-clearing broker-dealer, and "non-registered technology partners" can use its KYC service. No partner pricing or revenue share is published — [Alpaca Broker API](https://alpaca.markets/broker)
- SnapTrade:
  - Build: free, up to 5 brokerage connections, trading included.
  - Launch: $100/month plus $2 per connected user per month (real-time, trading included) or $1 per user (daily, read-only).
  - Personal or OAuth users are free for a limited time, and Custom plans have volume discounts.
  - Trading works only where the brokerage supports it, and the page lists no per-trade fees — [SnapTrade pricing](https://snaptrade.com/pricing)
- Plaid Investments returns balances, holdings and investment transactions (`/investments/holdings/get`). The page does not mention placing trades — [Plaid Investments](https://plaid.com/products/investments/)
- tastytrade's Open API is REST/JSON for equities, options, futures and crypto, with order placement including OTO/OCO/OTOCO orders, streaming market data and an MCP server for AI agents. Eligibility and partner terms are not stated — [tastytrade developer portal](https://developer.tastytrade.com/)
- TradingView has 100+ integrated brokers (Alpaca, IBKR, Webull, TradeStation, Saxo, OANDA, Binance and others). Brokers implement a REST API whose specification is shared only after signing an agreement. Brokers get a profile with reviews and an "Open account" button that sends free leads to their sign-up page, with access to over 100 million users — [TradingView brokerage integration](https://www.tradingview.com/brokerage-integration/)

### Inferences
- **Sequencing:**
  1. Ship deep-links and referral buttons first. TradingView's model shows brokers will give integration and leads value without the platform holding accounts.
  2. Add read-only position sync through SnapTrade (about $1–$2 per connected user per month) so people can flex verified P&L in the social feed. This is likely a stronger social feature than trading itself.
  3. Add in-app order tickets through SnapTrade or Alpaca only after product-market fit.
- **Order speed is dominated by hops, not the broker's engine.** Alpaca claims 1.5 ms OMS processing, so perceived order latency mostly comes from the aggregator and network round trips plus the user's broker. A social app routing through SnapTrade would likely be slower than the broker's own app, so "fastest trading" is a weak wedge for a non-broker.

### Gaps
- Revenue share or referral economics for Alpaca Broker API, DriveWealth, Tradier and IBKR; none were retrieved.
- The scope of Robinhood's official API; the docs page did not render. A crypto-only trading API is believed to exist but is unverified here.
- Schwab Trader API terms (403); IBKR web API and OAuth third-party approval (403); SnapTrade's per-broker trading support list (did not render).
- Broker deep-link URL schemes; measured order latency through SnapTrade.

## 9. Why TradingView users experience lag when trading through brokers (technical causes)

### Takeaway
No primary source documents TradingView's order latency, and the broker integration spec is gated behind an agreement. The sourced facts point to architectural causes rather than slow exchanges: a broker-implemented REST bridge to 100+ brokers of uneven quality, chart prices that may come from a different feed than the broker executes against, and a heavy browser front end.

### Cited Findings
- TradingView's broker integration is a REST API that each broker implements. The specification is shared only after the broker signs an agreement, and more than 100 brokers are integrated — [TradingView brokerage integration](https://www.tradingview.com/brokerage-integration/); the public spec page shows only a title — [TradingView REST API spec](https://www.tradingview.com/rest-api-spec/)
- Trading from the chart requires connecting to a broker's data stream and order routing ("Trading Platform"); Advanced Charts has no direct trading — [TradingView charting libraries](https://www.tradingview.com/free-charting-libraries/)
- TradingView sells extra real-time exchange data separately per exchange, and it works only on the website — [TradingView pricing](https://www.tradingview.com/pricing/)
- A non-consolidated feed can differ from the NBBO a broker executes against. For example, Cboe One quotes are within 1% of the NBBO 97.95% of the time — [Cboe One](https://www.cboe.com/market_data_services/us/equities/cboe_one/). CTA requires a "not sourced from all markets" statement when non-consolidated prices are shown with consolidated volume — [CTA](https://www.ctaplan.com/publicdocs/ctaplan/Schedule_of_Market_Data_Charges.pdf)
- Browser responsiveness targets are 100 ms for input response and about 10 ms of script work per 16 ms frame. Heavy pages that exceed them feel laggy — [web.dev RAIL](https://web.dev/articles/rail)
- A modern broker OMS processes orders in milliseconds (Alpaca claims 1.5 ms) — [Alpaca Broker API](https://alpaca.markets/broker)

### Inferences
Likely causes, in rough order of probability:
1. Extra network hops and REST round trips through each broker's integration layer, which varies by broker and where it is hosted.
2. Order and position status updates that may be fetched by request rather than pushed (unverified; see Gaps). Fills would then appear late even when execution was fast.
3. Chart-versus-broker data mismatch. A user on a free or partial data feed sees a "last price" that differs from the broker's NBBO, and experiences it as lag or slippage.
4. Front-end load from many indicators and panes on the browser main thread.
5. Broker-side risk checks and payment-for-order-flow routing, which vary by broker but are usually not the bottleneck given millisecond OMS numbers.

**Implication for the wedge:** the founder's "TradingView is laggy when trading" thesis mostly reflects integration architecture that a non-broker app would inherit, or make worse, if it also routed orders through third parties. The speed advantage the product can own is the live feed: real-time prices, plays and reactions delivered in about 100–300 ms. It cannot own order execution.

### Gaps
- Whether TradingView polls broker endpoints for order and position status, and at what intervals. The spec is now gated, so this could not be verified; if it does poll, status updates lag by up to the polling interval.
- First-hand user reports of TradingView order lag (Reddit, TradingView forums, Hacker News) were not collected because the search budget ran out.
- No TradingView engineering posts on order routing were found or retrieved.
