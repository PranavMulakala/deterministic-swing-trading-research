# Incumbent places US retail traders talk about stocks, crypto and options in real time (Stocktwits, TradingView, X, Reddit, paid Discord/Telegram/Whop groups), as of October 18, 2026

Research notes for the "Real for markets" report. Every bullet has a source; third-party estimates, self-selected reviews and older facts are flagged. Two kinds of evidence are first-party: (a) live captures of the Stocktwits and TradingView TSLA pages made on Oct 18, 2026, and (b) the founder's own price-checked audits of four paid Discord alert groups (local files in `output/`).

**Process note:** the web-search budget, which all researchers share, ran out partway through. After that I could only open pages I already had links for. Items left open because of this are marked in the Gaps sections (mainly Reddit chat features, Reddit complaint threads about TradingView, and any official TradingView/Stocktwits MAU numbers).

---

## 1. Platform snapshot: scale, what a ticker page offers, how real-time it is, how each makes money, and what changed in 2025–2026

### Takeaway
Every incumbent now has some version of a per-ticker page, but each is built for a different job than a fast, clean, shared "every move" experience:
- **Stocktwits** is a message board with sentiment. It claims 10M+ users, but third-party traffic and app numbers are far lower and falling.
- **TradingView** is a charting tool (100M+ users) whose social layer is secondary. It retired public chats on Sept 30, 2026.
- **X** is a general feed that only added live price charts on cashtags in April 2026.
- **Reddit** is threaded discussion with no market data.
- **Paid Discord, Telegram and Whop rooms** are closed alert channels with no built-in data.

### Cited Findings

| Platform | Scale (dated) | Ticker / live experience | How real-time | How it makes money | 2025–2026 changes |
|---|---|---|---|---|---|
| Stocktwits | Company says 10M+ users ([Sept 2025 release](https://ipsnews.net/business/2025/09/15/stocktwits-and-polymarket-join-forces-the-worlds-largest-prediction-market-and-the-worlds-largest-social-platform-for-finance-launch-new-earnings-markets/); [June 2026 release](https://www.nasdaqprivatemarket.com/news/npm-in-the-news/stocktwits-and-nasdaq-private-market-press-release/)). Third-party estimates: 13.5M web visits in Sept 2026, down from 21.1M in July ([Semrush](https://tr.semrush.com/website/stocktwits.com/overview)); about 497K iOS MAU ([AppGoblin](https://appgoblin.info/apps/389157776)) | Quote, "Full Chart" link, message Feed, News, Sentiment meter, Earnings, polls, trending rail, "AI Agent", ads ([TSLA page, Oct 18, 2026](https://stocktwits.com/symbol/TSLA)) | No real-time or delayed label on the page ([TSLA page](https://stocktwits.com/symbol/TSLA)). App quotes can sit stale until reload ([WallStreetZen](https://www.wallstreetzen.com/blog/stocktwits-review/)) | Ads, Ad-Free and Edge subscriptions, newsletters, partner deals ([WallStreetZen](https://www.wallstreetzen.com/blog/stocktwits-review/)) | Cryptotwits (May 2025), Polymarket markets (Sept 2025), private-company pages (June 2026) (see §2) |
| TradingView | Company says "100M+ traders and investors" ([About](https://www.tradingview.com/about/)). Similarweb shows 229.7M visits for Sept 2026; the label is unclear on whether that is one month or three ([Similarweb](https://www.similarweb.com/website/tradingview.com/)). Brokers page shows a counter labeled "Trades with real money" at 442,161,391; it appears to be cumulative ([Brokers](https://www.tradingview.com/brokers/)) | Price, chart, news, community Ideas, a link to Minds, technicals, forecasts, options tab, connect-a-broker ([TSLA page](https://www.tradingview.com/symbols/NASDAQ-TSLA/)) | Free US stock data is real-time but from Cboe only. Primary-exchange data is a paid add-on ([support](https://in.tradingview.com/support/solutions/43000473924)) | Subscriptions at $12.95–$199.95/mo (billed annually) plus data add-ons ([Pricing](https://www.tradingview.com/pricing/)). Broker integration is listed as a business offering ([About](https://www.tradingview.com/about/)) | Public chats retired Sept 30, 2026 ([support](https://in.tradingview.com/support/solutions/43000591339-using-public-chats/)) |
| X | About 600M monthly users, per Musk in Feb 2026 ([Yahoo Finance](https://finance.yahoo.com/news/elon-musk-x-launch-smart-074443907.html)) | Smart Cashtags: tapping a ticker opens a live price chart plus related posts (iPhone, US and Canada, Apr 14, 2026) ([Yellow](https://yellow.com/news/x-smart-cashtags-crypto-stock-charts)) | Described as "real-time"; no data provider named ([Crypto Briefing](https://cryptobriefing.com/x-launches-smart-cashtags-crypto-stock-tracking-pilots-in-app-trading/)) | X Money with a Visa card launched invite-only in July 2026 ([AP via Las Vegas Sun](https://lasvegassun.com/news/2026/jul/28/elon-musk-launches-invite-only-x-money-with-a-visa/)) | Smart Cashtags, a Wealthsimple trading pilot in Canada, X Money (see §4) |
| Reddit (r/wallstreetbets) | 19.9M subscribers "as of 2026" ([Wikipedia](https://en.wikipedia.org/wiki/R/wallstreetbets)) | No ticker pages. Discussion happens in threads, including daily discussion threads ([AWS Marketplace / Quiver](https://aws.amazon.com/marketplace/pp/prodview-6fzr5ffwsnyra)) | Comment threads, no price sync. Third-party trackers poll every 5–15 minutes ([AltIndex](https://altindex.com/wallstreetbets)) | Not researched (gap) | Public subscriber counts replaced by 7-day Visitors and Contributions (Sept 2025) ([Creator Handbook](https://www.creatorhandbook.net/reddit-replaces-subreddit-subscriber-counts-with-new-engagement-metrics/)) |
| Discord / Telegram / Whop | Discord: 200M+ MAU "as of December" (2025, per a Jan 7, 2026 report) ([Storyboard18](https://www.storyboard18.com/amp/social-media/discord-files-confidentially-for-ipo-reports-87132.htm)). Telegram: over 1B MAU, Mar 2025 ([Wikipedia](https://en.wikipedia.org/wiki/Telegram_(software))). Whop trading products: about $18.5–19.9M per month in estimated creator revenue ([WhopTrends](https://whoptrends.com/blog/best-trading-communities-whop-2026)) | No ticker pages. Alerts are text posts plus %-gain screenshots ([founder's Demon Alerts review](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/DEMON_ALERTS_REVIEW_20261011.md)) | Push notifications. Followers fill on average 15–19% worse than the posted price (see §6) | Memberships at $29–$300+/mo ([WhopTrends](https://whoptrends.com/blog/best-trading-communities-whop-2026)). Whop's take rate is about 5.5% ([Sacra](https://sacra.com/c/whop/)) | Discord filed confidentially for an IPO (Jan 2026). Tether put $200M into Whop at a $1.6B valuation (Feb 2026) ([Sacra](https://sacra.com/c/whop/)) |

### Inferences
- The combination the founder describes (price, chart, discussion and news on one ticker page) already exists in at least three places (§7). What nobody does well is speed (chat in sync with each price move), cleanliness (spam, ads, clutter) and trust (verified track records).
- X is the incumbent moving fastest toward the founder's idea and has by far the most distribution. TradingView is moving away from live public chat.

### Gaps
- No platform publishes current audited MAU or DAU for its finance users. Stocktwits and TradingView figures are company marketing claims or third-party estimates.
- Reddit's and X's revenue models as they relate to finance discussion were not researched.

---

## 2. Stocktwits: features and redesigns, sentiment and trending tools, brokerage / prediction-market / data ventures, reputation

### Takeaway
Stocktwits is the closest existing version of the idea. Its ticker page has a quote, a chart link, a live message stream, a sentiment meter, news, earnings, polls, Polymarket odds on some pages, and an AI agent. But it runs on a 2008-era message-board model. It has a poor reputation (bots, pump-and-dump promoters, opaque bans, ad clutter), it left brokerage in April 2024, and third-party data puts active use far below its "10M+ users" headline. Its 2025–2026 moves are partnerships, crypto, media and AI add-ons, not a rebuilt real-time core.

### Cited Findings

**Scale**
- **Company claims:** a "10 million–strong" community and "over 10 million users," calling itself the largest social platform for investors and traders ([Sept 15, 2025 press release](https://ipsnews.net/business/2025/09/15/stocktwits-and-polymarket-join-forces-the-worlds-largest-prediction-market-and-the-worlds-largest-social-platform-for-finance-launch-new-earnings-markets/)). The June 8, 2026 release says "10 million registered users," with no MAU, message or page-view figures ([Nasdaq Private Market](https://www.nasdaqprivatemarket.com/news/npm-in-the-news/stocktwits-and-nasdaq-private-market-press-release/)).
- **History:** Wikipedia lists 8M+ registered users. Earlier figures were about 230K active members in 2013, 3M users in 2020 and 5M on the 2021 homepage dashboard ([Wikipedia](https://en.wikipedia.org/wiki/StockTwits)).
- **Web traffic (third-party estimate):** 13.51M visits in Sept 2026, against 20.42M in August and 21.1M in July. That is about −34% month over month, and organic search traffic fell about 31% to 4.05M ([Semrush, updated Oct 11, 2026](https://tr.semrush.com/website/stocktwits.com/overview)).
- **iOS app (third-party estimate, crawled Oct 14, 2026):**
  - about 497K MAU;
  - 10.3M lifetime installs;
  - 207K ratings, averaging 4.8 stars;
  - install trend labeled "declining";
  - estimated iOS revenue of $50K+ per month, 77% from ads and 23% from in-app purchases ([AppGoblin](https://appgoblin.info/apps/389157776)).
  - An earlier search snippet of the same site showed about 2.1M MAU, so these estimates are unstable.
- **Message volume:** an academic dataset of Stocktwits posts from 2008–2022 reportedly shows growth stalling after 2018 at about 28K messages a day, with an average near 300K a day during the 2021 meme-stock surge ([ResearchGate dataset paper](https://www.researchgate.net/publication/396279575_StockTwits_Comprehensive_records_of_a_financial_social_media_platform_from_2008_to_2022)). I took these figures from the search-result abstract; the full text was blocked (403).
  - A secondhand claim credits Lindzon with "200,000+ ideas and messages daily," unverified ([Bullish Bears](https://bullishbears.com/stocktwits-review/)).

**What a ticker page has today (TSLA page, captured Oct 18, 2026)** ([Stocktwits TSLA](https://stocktwits.com/symbol/TSLA))
- **Quote:** last price, day change, after-hours move, volume and a "07:59 PM EDT" timestamp, with a "Full Chart" link.
- **Tabs:** Feed, News, Sentiment, Earnings, "NewFutures", Fundamentals, Info.
- **Sentiment:** a bullish/bearish slider scored 58 ("Bullish").
- **Other modules:**
  - an unlabeled 1,069,699 figure (probably the watcher count; not confirmed);
  - "Top Discussions" polls;
  - a trending rail (ETH, TRUMP, DJT, EWY, SOL…);
  - top navigation with "AI Agent," Trending, News and Earnings;
  - two ad blocks with a "Remove ads" upsell, and an app-download prompt.
- **No data provider or real-time/delayed disclaimer** is visible.
- Some posts quoted Polymarket odds themselves. Prediction-market modules appear only on selected pages (see 2025–2026 changes below).

**Features described by a third party (WallStreetZen review, updated Sept 19, 2025)** ([WallStreetZen](https://www.wallstreetzen.com/blog/stocktwits-review/))
- **Trending** ranks assets by how much they are discussed, with a 1–100 sentiment score based on post volume and tone.
- **Watchlists and market lists** come with a live feed of related posts.
- **Posts** run up to 1,000 characters, plus comments, @mentions and DMs.
- **News items** are mostly under 100 words.
- **Earnings calendar:** users can listen to earnings calls and track sentiment live.
- **"AI Insights"** summarizes fundamentals, technicals and community data.
- **Newsletters:** The Daily Rip and others.
- **Events:** in-person events and an on-air "Daily Rip Live" show (added July 2025).
- **Older features:** Discover (Dec 2017), Rooms (Aug 2018) and Premium Rooms (Oct 2018) ([Wikipedia](https://en.wikipedia.org/wiki/StockTwits)).

**How real-time it is**
- In the mobile app, ticker data can stay unchanged until the page is reloaded. Mobile crashes were reported in 2025, and the reviewer recommends the web version ([WallStreetZen](https://www.wallstreetzen.com/blog/stocktwits-review/)).
- An Oct 1, 2026 Trustpilot review says the message stream stops working exactly when it is most needed, with long delays at other times ([Trustpilot](https://www.trustpilot.com/review/www.stocktwits.com)). This is unverified and self-selected.

**How it makes money**
- **Subscriptions** (web, as of Sept 2025):
  - Ad Free: $8/mo or $85/yr;
  - Edge: $22.95/mo or $229.50/yr (sentiment data, more market lists, research tools, longer posts).
  - App Store tiers: Plus at $7.99/mo, an $11/mo tier, Edge at $29.99/mo, and lifetime Plus at $399.99 ([WallStreetZen](https://www.wallstreetzen.com/blog/stocktwits-review/)).
- **Ads** on symbol pages ([TSLA page](https://stocktwits.com/symbol/TSLA)), plus newsletters including partner newsletters through Beehiiv ([WallStreetZen](https://www.wallstreetzen.com/blog/stocktwits-review/)).
- **Partnerships:**
  - Polymarket, billed as Stocktwits' "largest-ever strategic partnership" (terms not disclosed) ([press release](https://ipsnews.net/business/2025/09/15/stocktwits-and-polymarket-join-forces-the-worlds-largest-prediction-market-and-the-worlds-largest-social-platform-for-finance-launch-new-earnings-markets/));
  - Gemini as official crypto exchange partner and Grayscale, both tied to Cryptotwits ([Benzinga/FinanceWire](https://www.benzinga.com/content/45346216/stocktwits-launches-cryptotwits-bridging-traditional-finance-and-crypto-for-10m-investors));
  - private-company pages that carry a call-to-action linking to Nasdaq Private Market ([NPM](https://www.nasdaqprivatemarket.com/news/npm-in-the-news/stocktwits-and-nasdaq-private-market-press-release/)).
- **Data licensing (old):** in 2013, data sales to clients such as Bloomberg and Google made up about half of revenue. In July 2024 it partnered with Quartr to offer content through an API ([Wikipedia](https://en.wikipedia.org/wiki/StockTwits)).
- **Funding:** $30M raised at a $210M valuation in Dec 2021 ([Wikipedia](https://en.wikipedia.org/wiki/StockTwits)).

**Brokerage history and 2024–2026 changes**
- **Leadership:** Howard Lindzon returned as CEO in 2024; Shiv Sharma is President and COO ([Wikipedia](https://en.wikipedia.org/wiki/StockTwits); [Forbes, May 12, 2025](https://www.forbes.com/sites/digital-assets/2025/05/12/stocktwits-jumps-on-the-crypto-bandwagon/), seen only as a search snippet; the page returned 403).
- **Brokerage timeline:**
  - April 2019: TradeApp announced (subsidiary ST Invest LLC);
  - Feb 2022: crypto trading;
  - July 2022: equities ([Wikipedia](https://en.wikipedia.org/wiki/StockTwits));
  - the 2022 crypto launch partnered with FTX.US, which later collapsed ([FXEmpire](https://fxempire.com/news/article/stocktwits-partners-ftx-to-launch-crypto-services-888664); [BusinessWire 2022](https://businesswire.com/news/home/20220203005358/en/Stocktwits-Launches-Crypto-Trading));
  - Sept 2023: options trading and more sentiment data announced ([BusinessWire 2023](https://www.businesswire.com/news/home/20230919886927/en)).
- **April 2024 exit from brokerage:** Public took over the TradeApp brokerage accounts.
  - Axios reported more than 15,000 accounts for under $10M and called it Stocktwits' exit from stock brokerage ([Axios](https://www.axios.com/pro/fintech-deals/2024/04/16/public-acquires-stocktwits-trading-accounts)). The press release said "tens of thousands" of customers.
  - Lindzon said the company was doubling down on core social, community and real-time discussion, with focus on earnings conversation and 24/7 crypto ([fintech.global](https://fintech.global/2024/04/22/public-expands-investment-frontier-with-acquisition-of-stocktwits-tradeapp/)). That article wrongly says "Public acquired Stocktwits"; only the brokerage accounts moved.
- **May 12, 2025, Cryptotwits:** a crypto section built on sentiment and community, with 17,000+ coin pages, a real-time coin watchlist, and Gemini and Grayscale as partners. It is information only, not trading ([Benzinga/FinanceWire](https://www.benzinga.com/content/45346216/stocktwits-launches-cryptotwits-bridging-traditional-finance-and-crypto-for-10m-investors)).
- **July 2025:** acquired the AI startup Thematic and launched "Daily Rip Live" ([WallStreetZen](https://www.wallstreetzen.com/blog/stocktwits-review/)).
- **Sept 15, 2025, Polymarket "Official Prediction Markets partner":**
  - earnings-outcome markets embedded on ticker pages and in streams;
  - "mention markets" on which words appear in earnings calls;
  - watchlists showing live probabilities;
  - a tap-through to Polymarket to trade;
  - first rolled out to selected US users ([press release](https://ipsnews.net/business/2025/09/15/stocktwits-and-polymarket-join-forces-the-worlds-largest-prediction-market-and-the-worlds-largest-social-platform-for-finance-launch-new-earnings-markets/); [Finance Magnates](https://www.financemagnates.com/cryptocurrency/polymarket-brings-earnings-prediction-markets-into-stocktwits/)).
- **June 8, 2026, private-company pages:** symbol pages for private companies using Nasdaq Private Market data (price, funding rounds, 409A valuations). Some carry Polymarket modules on IPO timing and valuation, with more coverage planned through 2026 ([NPM](https://www.nasdaqprivatemarket.com/news/npm-in-the-news/stocktwits-and-nasdaq-private-market-press-release/)).
- **Seen Oct 18, 2026:** an "AI Agent" entry in the top navigation ([TSLA page](https://stocktwits.com/symbol/TSLA)). I found no announcement for it.

**Reputation and complaints**
- **Trustpilot** rates it 1.3/5 from 82 reviews, 89% of them 1-star. The reviews are unverified and Stocktwits doesn't invite them ([Trustpilot](https://www.trustpilot.com/review/www.stocktwits.com)). Recurring themes:
  - bots and deliberate disinformation (Oct 2025);
  - descriptions of it as a pump-and-dump site (Mar 2024, May 2026);
  - slurs and harassment left up (Jul and Dec 2025);
  - bans for skeptical or bearish posts, and mutes triggered by mass-reporting (Jun 2025; Mar, May and Jun 2026);
  - too many ads, and a dated feel (Nov 2025, May 2026);
  - claims that paying members get leniency (Sept 2026).
- **WallStreetZen's cons:**
  - posts are not editorially reviewed;
  - pump-and-dump "gangs," bots and scammers;
  - much of the content is trivial clutter;
  - the premium tier is expensive ([WallStreetZen](https://www.wallstreetzen.com/blog/stocktwits-review/)).
- **Pump-and-dump use:** a Substack analysis describes pumping microcap and OTC stocks on Stocktwits as a recurring pattern ([Fintel Brief](https://fintelbrief.substack.com/p/marketing-for-a-pump-and-dump-scheme); secondary). There is even an open-source bot built to scalp Stocktwits pump-and-dumps ([GitHub](https://github.com/ajbenz18/Stocktwits-Scalper)).
- **Twitter adopted cashtags in 2012,** and Lindzon said Twitter had "hijacked" Stocktwits' $TICKER idea ([Wikipedia](https://en.wikipedia.org/wiki/StockTwits)). Saying this weakened Stocktwits' original hook is my inference.

### Inferences
- **Features aren't the problem.** Stocktwits shows that putting quote, stream, sentiment and news on one page isn't enough. Its problems are trust, moderation, speed under load and clutter.
- **A large dormant user base.** Taken together, "10M registered," about 0.5M estimated iOS MAU, falling web visits and a trending rail full of crypto and meme names suggest most registered users are inactive and activity is concentrated in speculative names. All of these numbers are third-party estimates.
- **Its business model rewards clutter.** It makes money from attention: ads, newsletters, and partner modules from Polymarket, Gemini and NPM. That leaves room for an ad-light product built around speed.
- **Moderation is an opening.** Users describe moderation as opaque and driven by mass-reporting. A clean rival would need visible rules and designs that make promoting a stock harder, such as showing whether a poster holds a position.

### Gaps
- No official 2025–2026 MAU, DAU or messages-per-day figures.
- Whether quotes are real-time or delayed (nothing on the page says).
- Current data-licensing revenue.
- Polymarket module usage.
- What the "NewFutures" tab is.
- Details of the "AI Agent" launch.
- A 2023 SEC inquiry mentioned by a data aggregator could not be confirmed.

---

## 3. TradingView: Ideas, Minds, chats and streams, broker integrations, the founder's lag claim, data delays, outages, social complaints

### Takeaway
TradingView is a charting company with a social layer, and in 2026 it pulled back from that layer's most "live" part: public chats were retired on Sept 30, 2026 because they need heavy moderation.

The founder's claim about lag when trading holds up as documented user complaints:
- tastytrade users on TradingView's own broker-review pages describe delays of 3 to 15+ seconds;
- Trustpilot reviews describe lag and charts that won't load in volatile markets;
- the status page lists trading-related incidents in 2026.

TradingView's help center points to one structural cause: the order panel uses the broker's quotes, which are often delayed unless you pay the broker for real-time data, so the price on the chart and the fill can differ. Robinhood is not an integrated broker at all.

### Cited Findings

**Scale and business**
- **Company description:** "a charting platform and social network" with "100M+ traders and investors worldwide." Market data comes from ICE Data Services, reference data from FactSet, and filings from Quartr ([About, 2026](https://www.tradingview.com/about/)).
- **Older cumulative figure:** 550M unique users since 2011, reported in 2021 ([IBS Intelligence](https://ibsintelligence.com/ibsi-news/tradingview-hits-record-550-million-unique-users)). That is cumulative, not monthly.
- **Similarweb, Sept 2026:** 229.7M visits and a global rank of #120. The page may be labeling a 3-month total ([Similarweb](https://www.similarweb.com/website/tradingview.com/)).
- **Trading through TradingView:** the brokers page counts 442,161,391 "trades with real money" (cumulative, as of Oct 2026) ([Brokers](https://www.tradingview.com/brokers/)).
- **Funding:**
  - $298M raised at a $3B valuation in 2021, led by Tiger Global, and described as profitable ([The Block](https://www.theblock.co/post/120628/charting-platform-tradingview-raises-298-million-at-3-billion-valuation));
  - 75% of revenue from individual subscriptions, year not stated ([FinanceFeeds](https://financefeeds.com/tradingview-lands-3-billion-valuation-recent-funding-round/));
  - Dealroom's paywalled third-party ranges: $2.5–5B valuation and $100–500M revenue ([Dealroom](https://dealroom.co/companies/tradingview/)).

**Pricing (Oct 2026, billed annually)** ([Pricing](https://www.tradingview.com/pricing/))

| Plan | Price | Charts per tab | Indicators per chart | Price alerts |
|---|---|---|---|---|
| Basic | $0 | 1 | 2 | 3 |
| Essential | $12.95/mo | 2 | 5 | 20 |
| Plus | $29.95/mo | 4 | 10 | 100 |
| Premium | $59.95/mo | 8 | 25 | 400 |
| Ultimate | $199.95/mo | 16 | 50 | 1,000 |

- Professionals can only buy Ultimate.
- Real-time NASDAQ, NYSE and CME data is sold separately, requires a paid plan or trial, and can't be refunded.

**Data delays and paid data**
- **Default US stock data is real-time from Cboe and free,** because Cboe charges no per-user fees ([support](https://in.tradingview.com/support/solutions/43000473924)).
  - Cboe handles 25%+ of US stock trading, so it produces fewer price updates.
  - Differences show up most on 1-minute charts, on thinly traded tickers, and in pre- and post-market trading.
  - NASDAQ, NYSE and NYSE Arca real-time data must be bought. TradingView has to collect the exchanges' fees and report who accesses the data.
  - TradingView pages name the free feed variously as Cboe BZX (older pages and third-party guides) or Cboe One (a newer page), per search summaries of its support pages ([support](https://www.tradingview.com/support/solutions/43000471705-how-to-purchase-additional-market-data/)).
  - Third-party guides put add-ons at about $2–10/mo per exchange or $9.95 for a US bundle; these are affiliate sites, not verified ([DayTradingToolkit](https://daytradingtoolkit.com/trading-tools-tutorials/tradingview-pricing-explained)).
- **Order panel caveat:** even with a TradingView data package, quotes on the order panel and buy/sell buttons can stay delayed, because they come straight from the broker ([support](https://my.tradingview.com/support/solutions/43000739323/)).
  - TradingView warns this can mean fills at unexpected prices, especially in fast markets.
  - Some broker integrations require a real-time data subscription bought from the broker.
- **TradeStation example:** if the broker's feed for a symbol is delayed, Ask and Bid in the order panel and DOM (the price ladder) are delayed too. TradingView data packages cover charts, watchlists and screeners only. Verifying a TradeStation account avoids paying twice ([support](https://in.tradingview.com/support/solutions/43000719858-why-is-the-data-delayed-in-the-order-panel-and-dom-on-my-tradestation-account/)).

**Social features**
- **Current list:** Ideas (Popular, Editors' picks, For you, Following), Pine Script community scripts, Minds (short per-symbol posts, under a ticker's Discussions tab), broker reviews, DMs with moderators, and "The Leap" trading competitions with real-money prizes ([support](https://in.tradingview.com/support/solutions/43000761245)).
- **Minds** launched in beta in Dec 2022, when only paying members could post ([TradingView blog](https://www.tradingview.com/blog/en/introducing-minds-35320)). It came to the mobile apps in Aug 2023 ([TradingView blog](https://www.tradingview.com/blog/en/minds-in-tradingview-mobile-app-39626)).
- **Public chats were retired on Sept 30, 2026** ([support](https://in.tradingview.com/support/solutions/43000591339-using-public-chats/)).
  - The new Chats allows only one-to-one and private group chats, and switching over is permanent.
  - TradingView's stated reason: public chats need a lot of moderation to stay constructive.
  - Earlier help pages said posting in public chats needed 5 reputation points.
- **I found no current information on TradingView "Streams"** (see Gaps).
- **TSLA symbol page (captured Oct 18, 2026)** ([TradingView TSLA](https://www.tradingview.com/symbols/NASDAQ-TSLA/)):
  - price and performance tiles, "Key facts" summary cards, key stats, earnings and financials;
  - Benzinga-sourced news and 10 community Ideas, labeled as opinions rather than verified analysis;
  - only a "See all minds" link, with no live posts on the page;
  - technicals, analyst forecasts, seasonals, and options, ETF and bond tabs;
  - an FAQ entry on connecting a broker.
  - The page doesn't say whether prices are real-time.

**Broker integrations and trading through TradingView**
- **33 brokers listed** ([Brokers](https://www.tradingview.com/brokers/)). US-relevant ones include Webull, tastytrade, TradeStation, Interactive Brokers, Tradovate, NinjaTrader, AMP, moomoo, Public, Alpaca, Tradier, TradeZero, Fidelity (stocks and ETFs), Coinbase Advanced, Kraken and Gemini.
- **Robinhood and E*TRADE are not listed** ([Brokers](https://www.tradingview.com/brokers/)).
- **Webull example:** users can trade US stocks, ETFs and ADRs from TradingView charts through a connected Webull account (early 2024) ([Finance Magnates via TradingView News](https://fr.tradingview.com/news/financemagnates:4c1c37346094b:0-webull-expands-collaboration-with-tradingview-includes-trading-from-charts/)).

**Checking the founder's claim: complaints about lag or failures when trading through TradingView**
- **tastytrade's page on TradingView** (4.1 rating from about 1.1K ratings) has several reviews describing ([tastytrade reviews](https://www.tradingview.com/broker/tastytrade/reviews/)):
  - serious lag on market and limit orders;
  - 10–15 seconds to adjust chart limit orders and 3–5 seconds on market orders when trading 0DTE (same-day-expiry) options;
  - 15+ seconds before trades show up on tastytrade's side;
  - orders freezing.
  - Review dates are shown without a year, and at least one review is about 1.5 years old. Some reviewers blamed TradingView rather than the broker; one raised their rating to 5 stars after deciding TradingView was the problem (per the search-result summary of the same pages).
- **Other brokers** (non-US or CFD-focused; context only):
  - Phillip Nova users report 2–5 seconds from order entry to execution ([reviews](https://in.tradingview.com/broker/phillip_nova/reviews));
  - FP Markets and Vantage users report lag, disconnections and blank charts at peak hours ([FP Markets](https://www.tradingview.com/broker/FPMarkets); [Vantage](https://www.tradingview.com/broker/VantageMarkets/reviews/));
  - IG publicly acknowledged that delayed data when connected to TradingView can make trading from its charts impractical ([IG reviews](https://in.tradingview.com/broker/IG_com/reviews)).
- **Trustpilot** withholds TradingView's TrustScore over a guidelines breach and says it removed a number of fake reviews. There are 1,357 reviews, 62% of them 1-star ([Trustpilot](https://www.trustpilot.com/review/tradingview.com)). Recent reviews (Sept–Oct; the year isn't shown but they are the newest on the page) describe:
  - delays bad enough to make real-time tracking unusable (Oct 5);
  - charts that won't load in high volatility (Sept 17);
  - needing to reload every minute or two (Sept 26);
  - a stop-loss reported as hit that the user says was never set (Oct 16);
  - a broker connection that broke after one day (Sept 10).
- **Status-page incidents in 2026** ([status.tradingview.com/history](https://status.tradingview.com/history)):
  - trading-related:
    - Tradovate broker issues, Jan 28 (about 2h57m);
    - "Issues in Trading" and in charts, Mar 6 (about 3h05m);
    - Tradovate login issue, Jun 10 (about 2h19m);
  - other:
    - technical alerts partly unavailable, Jul 1–3 (about 2 days 8 hours);
    - watchlist loading problems, Jan 15–16 (about 15h47m);
    - FXCM charts not updating, Mar 2 (about 12h26m).
  - 2025 incidents were mostly alert outages (Jan 20, May 23, Jul 17, Nov 22) plus paper-trading problems in Nov 2025.
  - Third-party monitors disagree: one shows no 2026 incidents ([UptimeRobot](https://uptimerobot.com/is-it-down/tradingview/2026/)).

**Complaints about the social side**
- A reviewer says they were banned from Minds for posting without a chart and that scammers were tolerated (Oct 15) ([Trustpilot](https://www.trustpilot.com/review/tradingview.com)).
- Reviewers also complain about AI support-chat loops with no human, and a "Co-Pilot" pop-up on charts they couldn't remove (Sept 2026) ([Trustpilot](https://www.trustpilot.com/review/tradingview.com)).
- I found few sourced complaints about Ideas quality beyond this, because of the search limit (see Gaps).

### Inferences
- **The claim is fair, but the causes are mixed:**
  - TradingView is a front end that sends orders to each broker's systems;
  - order-panel quotes come from the broker and may be delayed;
  - the free chart feed is Cboe-only and differs from where the order actually fills;
  - the app or browser struggles at peak volatility;
  - the platform has outages.
  - No source measures how much delay TradingView itself adds, and reviewers disagree on whether the broker or TradingView is at fault.
- **The founder can't trade Robinhood through TradingView at all.** His frustration is more likely the three-app workflow: charts in TradingView, orders in Robinhood, alerts in Discord. That supports the fragmentation thesis.
- **Retiring public chats is both a warning and an opening.** It shows how expensive live public chat is to moderate, even for a profitable company with 100M+ users. It also means users who wanted live public rooms lost them 18 days ago.
- **Free real-time data can be enough to start.** Primary-exchange data carries per-user fees and reporting duties. A startup could launch with a Cboe-style feed that has no per-user fees, as TradingView's free tier does, or with crypto. TradingView's own help center says the Cboe feed is good enough for most analysis.

### Gaps
- No current official MAU, DAU, Ideas or Minds volumes.
- When the retirement of public chats was first announced.
- No independent measurement of order latency through TradingView.
- Whether a Robinhood integration is planned.
- Reddit complaint threads about TradingView lag (reddit.com could not be fetched).
- Whether TradingView "Streams" still exist.
- Sourced complaints about the quality of Ideas.

---

## 4. X (Twitter): cashtags and 2025–2026 finance features, and complaints about bots, scams and noise

### Takeaway
X has the biggest real-time finance audience, and in 2026 it moved closest to the founder's idea:
- **Smart Cashtags** (launched April 14, 2026 on iPhone in the US and Canada) show a live price chart and a feed of related posts behind every ticker you tap.
- **Trading** is a Wealthsimple trade button, in Canada only.
- **X Money** (with Visa) launched invite-only in July 2026.

But all of this sits inside a ranked general-purpose feed with heavy bot spam and a history of promoter fraud, and X says it will not act as a broker.

### Cited Findings
- **Scale:**
  - Musk said X reaches about 600M monthly users (Feb 2026) ([Yahoo Finance](https://finance.yahoo.com/news/elon-musk-x-launch-smart-074443907.html));
  - third-party roundups cite about 557–611M MAU and about 250–259M DAU, plus Similarweb mobile data showing daily use falling. All of these are unaudited ([Charle Agency roundup](https://charleagency.com/articles/twitter-x-statistics/)).
- **Cashtag history:**
  - Twitter adopted cashtags in 2012 ([Wikipedia: StockTwits](https://en.wikipedia.org/wiki/StockTwits));
  - a 2022 version showed price charts and market data but no trading, and was later discontinued ([Yahoo Finance](https://finance.yahoo.com/news/elon-musk-x-launch-smart-074443907.html)).
- **Feb 14–15, 2026 announcement:** head of product Nikita Bier said users would be able to buy and sell stocks and crypto from the timeline within a couple of weeks ([Yahoo Finance](https://finance.yahoo.com/news/elon-musk-x-launch-smart-074443907.html)).
  - He then clarified that X won't execute trades or act as a broker. Smart Cashtags would be data tools (live prices, charts, asset info) that hand users off to partner brokers or exchanges ([Stocktwits News, updated Mar 5, 2026](https://stocktwits.com/news-articles/markets/cryptocurrency/x-brings-direct-crypto-trading-with-smart-cashtag/cZR4yNcR4tq)).
- **April 14, 2026 launch** ([Crypto Briefing](https://cryptobriefing.com/x-launches-smart-cashtags-crypto-stock-tracking-pilots-in-app-trading/); [Yellow](https://yellow.com/news/x-smart-cashtags-crypto-stock-charts)):
  - iPhone, US and Canada;
  - tapping a cashtag opens a live price chart next to related posts;
  - X suggests matching assets or contract addresses so similar tickers aren't confused;
  - a Wealthsimple pilot in Canada opens a pre-filled trade ticket;
  - web, Android and other countries planned "soon";
  - Bier said the goal goes beyond charts and that trading should be frictionless, because X content is actionable.
  - No data provider was named, and US trading was not enabled at launch. I found no later confirmation of US trading.
- **X Money:**
  - in limited beta in Feb 2026 ([Yahoo Finance](https://finance.yahoo.com/news/elon-musk-x-launch-smart-074443907.html));
  - early public access expected in April ([Crypto Briefing](https://cryptobriefing.com/x-launches-smart-cashtags-crypto-stock-tracking-pilots-in-app-trading/));
  - July 28, 2026: AP reported an invite-only launch with an X-branded Visa debit card, a 6% yield and real-time transfers ([AP via Las Vegas Sun](https://lasvegassun.com/news/2026/jul/28/elon-musk-launches-invite-only-x-money-with-a-visa/)). I saw only the headline and search snippet; the page was paywalled (402).
  - The snippets also say invites went only to paying X members, that a Visa Direct partnership handles wallet funding, and that crypto is planned for later in 2026 (unverified secondary reports via search; e.g., [exchange4media](https://www.exchange4media.com/digital-news/x-money-elon-musk-to-launch-in-app-financial-system-on-x-in-april-2026-152781.html)).
- **Bots and spam:**
  - In early Jan 2026, CryptoQuant's CEO said bots pushed more than 7.7M crypto posts in one day, which got crypto content blocked or downranked ([Stocktwits News](https://stocktwits.com/news-articles/markets/cryptocurrency/x-brings-direct-crypto-trading-with-smart-cashtag/cZR4yNcR4tq)).
  - In Feb 2026, X restricted API access for "InfoFi" and engagement-reward apps, citing AI spam and manipulation ([Yahoo Finance](https://finance.yahoo.com/news/elon-musk-x-launch-smart-074443907.html)). It also said it would block apps that use "claim your fees" mechanics to drive spam ([Stocktwits News](https://stocktwits.com/news-articles/markets/cryptocurrency/x-brings-direct-crypto-trading-with-smart-cashtag/cZR4yNcR4tq)).
  - **Academic evidence (older but structural, 2017 data):** of 25,957 suspicious accounts behind cashtag spikes, 71% were classified as bots. Coordinated bots tag low-value OTC stocks alongside big NASDAQ and NYSE names to borrow their attention ([Cresci et al., 2018](https://ar5iv.labs.arxiv.org/html/1804.04406)).
- **Enforcement involving Twitter/X:**
  - **Atlas Trading:** the SEC charged eight influencers in Dec 2022 over a roughly $100M scheme promoted on Twitter and Discord ([SEC 2022-221](https://www.sec.gov/news/press-release/2022-221)); the DOJ put the gain at $114M ([Engadget](https://www.engadget.com/sec-stock-manipulation-fraud-charges-discord-twitter-172056536.html)). A district court dismissed the criminal indictment in March 2024 ([Bullish Bears](https://bullishbears.com/atlas-trading-lawsuit/)). The Fifth Circuit reinstated it on Oct 2, 2025 ([Justia](https://law.justia.com/cases/federal/appellate-courts/ca5/24-20143/24-20143-2025-10-02.html); [CLS Blue Sky](https://clsbluesky.law.columbia.edu/2025/10/16/quinn-emanuel-discusses-fifth-circuit-decision-reinstating-securities-fraud-indictment)).
  - **Andrew Left (Citron Research):** convicted in early June 2026 in Los Angeles of a securities-fraud scheme count plus 12 trade counts. Prosecutors said he used his large social following, including Citron's Twitter account, to move prices and then exit almost immediately (in one example, less than two hours after a post), earning at least $21M. Sentencing was set for Aug 31, and he plans to appeal ([Bloomberg Law](https://news.bloomberglaw.com/california-brief/short-seller-andrew-left-found-guilty-of-securities-fraud); [Wachtell memo](https://www.wlrk.com/FirmMemos/WLRK/WLRK.29978.26.pdf)). I didn't check the sentencing outcome.
- **X as the free funnel for paid rooms:** in the founder's paid VIP Discord, a member asked why the group charges when the seller posts the same calls on X ([founder's EdwardAlerts VIP review, Oct 12, 2026](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/EDWARD_VIP_REVIEW_20261012.md)).

### Inferences
- **X is the most dangerous competitor.** It has distribution, now the core screen (ticker, live chart, posts), and a path to payments and trading through partners.
- **Its weak spots:**
  - the feed is ranked rather than a chronological per-ticker room;
  - it is noisy and spam-prone;
  - Smart Cashtags is new, iPhone-first, and US trading isn't live.
- **Where a newcomer could win:** live per-ticker sync, moderation built for finance, and focus.
- **Trading is left to partners.** Because X won't be a broker, "trade from the conversation" stays open to partners, as Wealthsimple shows.

### Gaps
- Smart Cashtags' data provider and latency, and whether the post feed is ranked or chronological.
- Adoption metrics.
- Status of Android, web and US trading as of Oct 2026.
- X's prediction-market partnerships (left to the other researcher).
- Finance-specific usage statistics.

---

## 5. Reddit (r/wallstreetbets and similar): daily threads, live features, moderation, 2025–2026 changes, limits for real-time discussion

### Takeaway
r/wallstreetbets is huge (19.9M subscribers as of 2026) and culturally central, but Reddit is a threaded forum with no market data:
- the daily discussion thread is a fast-moving pile of comments with no price or chart sync;
- third-party trackers scrape it every 5–15 minutes;
- in Sept 2025 Reddit hid public subscriber counts in favor of weekly visitor and contribution counts;
- WSB's history shows its moderation can be overwhelmed at peak moments.

### Cited Findings
- **Size:** 6.2M on Jan 29, 2021 → 13.6M in Feb 2023 → 19.9M "as of 2026" ([Wikipedia](https://en.wikipedia.org/wiki/R/wallstreetbets)).
- **Sept 9, 2025 metrics change** ([Creator Handbook](https://www.creatorhandbook.net/reddit-replaces-subreddit-subscriber-counts-with-new-engagement-metrics/); [Finviz](https://finviz.com/news/164140/reddit-to-replace-subreddit-member-counts-with-active-engagement-metrics); [Social Samosa](https://www.socialsamosa.com/news-2/reddit-member-count-new-engagement-metrics-10067678)):
  - public subscriber counts replaced by "Visitors" (unique visitors over 7 days, on a rolling 28-day average) and "Contributions" (posts and comments not removed, over 7 days);
  - moderators limited to five subreddits that each get more than 100K weekly visitors (about 0.1% of mods affected).
- **Peak-moment strain (Jan 2021):**
  - WSB mods briefly made the subreddit private, saying their automated tools were overwhelmed by the flood of new users ([Wikipedia](https://en.wikipedia.org/wiki/R/wallstreetbets));
  - Discord banned the WSB server on Jan 27, 2021 for hate speech and misinformation, then helped restore it ([GameRevolution](https://www.gamerevolution.com/news/672877-wallstreetbets-subreddit-private-discord-banned); [Engadget](https://www.engadget.com/discord-bans-reddit-wallstreetbets-022921453.html));
  - Reddit said bot activity was within normal bounds ([CBS News](https://www.cbsnews.com/news/wallstreetbets-reddit-bot-activity/));
  - archived copies show a ban on "market manipulation" at the top of the rules by April 2020 ([Malay Mail](https://www.malaymail.com/news/money/2021/01/30/gamestops-reddit-rally-puts-scrutiny-on-social-media-forums/1945298)).
- **Third parties fill the real-time and data gap:**
  - AltIndex monitors WSB about every 15 minutes, though its tracker page says every 5 minutes ([AltIndex](https://altindex.com/wallstreetbets));
  - YoloStocks says it streams comments with a 5-minute refresh ([YoloStocks](https://yolostocks.live/));
  - Quiver Quantitative sells an intraday feed of WSB Daily Discussion thread mentions on AWS Marketplace ([AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-6fzr5ffwsnyra)).
  - One aggregator snapshot showed only 233 comments in the Oct 2, 2026 Daily Discussion thread. That is probably partial and unreliable (seen in a search summary only).
- **No 2025–2026 WSB-specific moderation, rule or ban changes turned up** in searches, which mostly returned 2021 coverage ([Wikipedia](https://en.wikipedia.org/wiki/R/wallstreetbets)).

### Inferences
- **WSB's appeal is culture,** meme humor and daily thread energy, not tools. Nothing on Reddit ties a comment to the price move it reacts to. That third parties scrape and resell WSB activity shows demand for "chat plus live data" exists.
- **The Sept 2025 metrics change makes community size harder to compare.** Startups should cite weekly visitors when they become visible, not legacy subscriber counts.

### Gaps
- WSB's current weekly visitors and contributions (reddit.com could not be fetched).
- Daily-thread comment volumes.
- Reddit's 2025–2026 chat and live features, and whether communities still have chat channels.
- How Reddit's API pricing affects live third-party tools (not sourced here).
- Sizes of r/options, r/stocks and r/thetagang.

---

## 6. Paid Discord, Telegram and Whop trading communities and alert groups: how they work, pricing, scale, tools, problems

### Takeaway
Paid alert rooms are a real market:
- Whop's trading category is estimated at $18.5–19.9M a month in creator revenue across roughly 21–29K products, about 31% of Whop. Options alerts alone are about $3.8M a month.
- Typical prices run $29–$300 a month.
- They run on Discord (200M+ MAU) and Telegram (1B+ MAU).

They deliver live "play-by-play" as text alerts and %-gain screenshots with no built-in market data. The founder's own price-checked audits of four groups show posted results far better than what followers could actually get. Regulators keep flagging stock promotion through social media and chat apps.

### Cited Findings

**Scale and economics**
- **Discord:** 200M+ MAU "as of December" (2025, per a Jan 7, 2026 report). It filed confidentially for a US IPO (Bloomberg, Jan 2026; Goldman Sachs and JPMorgan), and revenue comes mainly from Nitro subscriptions ([Storyboard18](https://www.storyboard18.com/amp/social-media/discord-files-confidentially-for-ipo-reports-87132.htm)). A pre-IPO tracker reported no IPO by June 30, 2026 ([TechStackIPO](https://techstackipo.com/ipo/discord); via search snippet).
- **Telegram:** over 1B MAU (Mar 2025). Groups hold up to 200K members and channels have no subscriber limit. It earns from Premium, sponsored messages and "Stars," and Durov said it turned profitable in Dec 2024 ([Wikipedia](https://en.wikipedia.org/wiki/Telegram_(software))).
- **Whop (Sacra estimates)** ([Sacra](https://sacra.com/c/whop/)):
  - annualized net revenue of $142M (Oct 2025), up from $56M at end-2024;
  - monthly GMV of about $80M (Dec 2024) rising to about $100M (Mar–Apr 2025);
  - $2.67B cumulative GMV (Feb 2026);
  - take rate about 5.5% (early 2025);
  - Series B of $50M+ at an $800M valuation (Jul 2024, Bain Capital Ventures);
  - $200M from Tether at a $1.6B valuation (Feb 2026);
  - growth driven largely by sports picks and crypto trading signals.
  - An investor's post put Whop at about $2B GMV and $142M ARR in net revenue ([Colin Gardiner on X](https://x.com/ColinGardiner/status/1990164197032841721)).
  - Sacra's "$60.2M platform MRR" appears to measure creators' gross product revenue, not Whop's net revenue.
- **WhopTrends, Mar 7, 2026 (unofficial estimates)** ([WhopTrends](https://whoptrends.com/blog/best-trading-communities-whop-2026)):
  - 28,899 trading products, about $18.5M a month in revenue, 2.4M members;
  - "Options Alerts": 1,927 products, $3.83M a month (average $1,991 per product);
  - "Trading Education": $5.13M; "Futures Signals": $1.87M.
  - Top-10 examples:
    - Blxq Invests (options): $29/mo, 10,601 members;
    - Owls Options Traders: $60 per 4 weeks, 3,304 members, about $218K a month;
    - Options Insider Pro: $199/mo;
    - Trade With Insight: $219/mo;
    - CTG Capital: $300/mo;
    - a prop-firm group at $1,250/mo.
- **WhopTrends, Feb 15, 2026** ([WhopTrends](https://whoptrends.com/blog/whop-creator-earnings-data-2026)):
  - trading at $19.9M a month, 31% of an estimated $64.2M platform total;
  - 21,079 trading products, 4,282 earning anything, median $333 a month among those;
  - across all of Whop, 87.8% of products earn $0 and the top 1% take 56.5% of revenue.

**How they work: the founder's own audits (Sept–Oct 2026; local files, research only)**
- **OWLS Capital** (paid Discord; an "all-alerts" channel reposts every analyst's alert with a timestamp) ([test #28 results](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/OWLS_ALERTS_BACKTEST_RESULTS_20261008.md); [plan](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/OWLS_ALERTS_BACKTEST_PLAN_20261008.md)):
  - 886 alert messages became 362 option positions; 274 were scored against Alpaca's 1-minute options price data.
  - Under the rule written down before scoring (buy at the high of the minute after the alert, sell at the low of the minute after the exit post), no analyst made money for a follower from Sept 8 to Oct 8, 2026.
  - On the same trades, posted average gains far exceeded what followers got: +142% vs +49%, +76% vs +1%, +112% vs +23%.
  - The 0DTE channel posted 106 alerts, and 66 never got an exit post.
  - OWLS charged $63 per 4 weeks ([EdwardAlerts review](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/EDWARDALERTS_REVIEW_20261011.md)). It is probably the same group as Whop's "Owls Options Traders," but that is a name match only, not confirmed.
- **"Demon Alerts"** (one of about 15 alert channels in the paid "Optionality Pro" tier; the server also runs a referral program and warns about impersonators DMing for money) ([review](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/DEMON_ALERTS_REVIEW_20261011.md)):
  - 30 buy alerts, posted as text like "BTO $SPY 772c 10/05 @0.75," often with no stop;
  - all 35 screenshots in the window are cropped %-gain strips of winners, with no dollars or exits;
  - a follower buying in the minute after an alert paid on average 19% more than the posted price, up to 50% more;
  - every exit rule a follower could actually repeat lost about $3.1K–$5.7K at $450 per alert;
  - only hindsight selling at his final brag post made +$7.6K.
- **EdwardAlerts** (free server, then a VIP tier at about $60) ([free review](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/EDWARDALERTS_REVIEW_20261011.md); [VIP review](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/EDWARD_VIP_REVIEW_20261012.md)):
  - free-server entry prices were accurate, but losing trades were never followed up;
  - VIP: 26 alerts; followers paid on average 15% above the posted price;
  - his own stated trim rule produced −$1,215 at $300 per alert, while hindsight exits gave +$3,593;
  - the server funnels toward a promised course and mentorships;
  - two "independent" sellers are friends and alerted the same COIN contract four minutes apart.
- **Tools and data:** alerts are plain text plus screenshots, and updates are posts, not live data. Followers act on phone notifications ([OWLS results, limits section](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/OWLS_ALERTS_BACKTEST_RESULTS_20261008.md)). Checking any claim meant pulling options minute data from Alpaca separately ([all reviews above](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/DEMON_ALERTS_REVIEW_20261011.md)). Whop grew out of the trading and Discord community space ([WhopTrends](https://whoptrends.com/blog/best-trading-communities-whop-2026)), and a membership typically buys access to a Discord community ([Sacra](https://sacra.com/c/whop/)).

**Documented problems and regulation**
- Sellers of trading signals usually aren't registered advisers, and listings make aggressive earnings promises. The FTC's $2.4M RagingBull settlement over stock-tip claims is the reference case, though it is older ([Sacra](https://sacra.com/c/whop/)).
- **Atlas Trading:** SEC and DOJ case over a scheme run on Discord and Twitter, reinstated by the Fifth Circuit on Oct 2, 2025 (§4) ([SEC](https://www.sec.gov/news/press-release/2022-221); [Justia](https://law.justia.com/cases/federal/appellate-courts/ca5/24-20143/24-20143-2025-10-02.html)).
- **FBI IC3 warning, Jul 3, 2025 ("ramp-and-dump" via investment clubs)** ([IC3](https://www.ic3.gov/PSA/2025/PSA250703)):
  - at least a 300% rise in victim complaints in 2025 vs 2024;
  - clubs recruited through social media ads and moved to messaging apps;
  - members may be bots or fake accounts;
  - promoters impersonate brokerages or well-known analysts.
- **FINRA alert, Dec 9, 2025** ([FINRA](https://www.finra.org/investors/insights/investment-group-imposter-scams)):
  - a big spike since fall 2023 in complaints about fraudulent "investment groups" on social media and encrypted chats such as WhatsApp;
  - they often start with well-known stocks, then move victims into low-priced, thinly traded ones.
- **Chicago case, March 2025:** seven people were indicted after victims were steered into WhatsApp groups pushing a single stock; $214M was seized ([ABC7 Chicago](https://abc7chicago.com/16077714); via search snippet).
- **Platform risk:** Discord's Jan 2021 ban of WSB's server shows a host platform can remove a community overnight ([Engadget](https://www.engadget.com/discord-bans-reddit-wallstreetbets-022921453.html)).

### Inferences
- **The demand is proven.** People pay $60–$300 a month for speed, conviction and company in the moment.
- **The failures are verification and fills.** Posted prices are better than what followers can get, losers go unreported, and screenshots show only winners. A fair, automatic "box score" (timestamped calls checked against live quotes, which the founder has already prototyped) could be a wedge, both for followers and for honest alert-sellers.
- **Hosting paid alert-sellers or follow buttons brings regulatory exposure** (SEC, FINRA, FTC). Disclosure and anti-pump design need to be built in from the start.

### Gaps
- Official Whop trading-category figures (only unofficial estimates exist).
- Counts of Discord trading servers and their members.
- Scale of US stock groups on Telegram.
- Which alert bots (e.g., webhook-to-Discord tools) groups commonly use; my sources don't document this.
- Discord's own policies on paid trading servers.
- Any 2026 SEC action aimed specifically at Discord alert groups (none found).

---

## 7. Does anyone already put live price, chart, live comments and news on one clean ticker screen, and why hasn't it become the central place?

### Takeaway
Yes. At least three incumbents already show live (or near-live) price, a chart, a comment stream and news on one ticker page:
- **Stocktwits,** for years;
- **TradingView,** through symbol pages and Supercharts with Minds;
- **X,** through Smart Cashtags since April 2026.

None became the central "every move" place, because each fails on at least one of speed, cleanliness and trust, or social density:
- Stocktwits on trust, clutter and declining traffic;
- TradingView on social, with public chat retired and Minds tucked behind a link;
- X on noise and bots, with no per-ticker live room and a feature that is brand-new and iPhone-first;
- Reddit on having no data at all;
- Discord on being closed, paid silos with no data.

### Cited Findings
- **Stocktwits** has quote, chart link, live Feed, News, Sentiment, Earnings, polls, trending and an AI Agent on one page ([TSLA page](https://stocktwits.com/symbol/TSLA)), with Polymarket odds on some pages ([press release](https://ipsnews.net/business/2025/09/15/stocktwits-and-polymarket-join-forces-the-worlds-largest-prediction-market-and-the-worlds-largest-social-platform-for-finance-launch-new-earnings-markets/)).
  - It is held back by spam, pump-and-dumps, opaque bans and ads ([Trustpilot](https://www.trustpilot.com/review/www.stocktwits.com); [WallStreetZen](https://www.wallstreetzen.com/blog/stocktwits-review/));
  - by stale app quotes and stream failures at peak ([WallStreetZen](https://www.wallstreetzen.com/blog/stocktwits-review/); [Trustpilot](https://www.trustpilot.com/review/www.stocktwits.com));
  - and by falling third-party traffic estimates ([Semrush](https://tr.semrush.com/website/stocktwits.com/overview)).
- **TradingView's symbol page** has price, chart link, news, Ideas and a Minds link ([TSLA page](https://www.tradingview.com/symbols/NASDAQ-TSLA/)).
  - Live public chat was retired on Sept 30, 2026 over moderation load ([support](https://in.tradingview.com/support/solutions/43000591339-using-public-chats/)).
  - Prices in the trading panel can differ from the chart's feed ([support](https://my.tradingview.com/support/solutions/43000739323/)).
- **X Smart Cashtags** show a live price chart with related posts ([Yellow](https://yellow.com/news/x-smart-cashtags-crypto-stock-charts)), but inside a bot-heavy feed ([Stocktwits News](https://stocktwits.com/news-articles/markets/cryptocurrency/x-brings-direct-crypto-trading-with-smart-cashtag/cZR4yNcR4tq); [Cresci et al.](https://ar5iv.labs.arxiv.org/html/1804.04406)).
- **Reddit** offers threads only. Live data comes from third-party scrapers refreshing every 5–15 minutes ([AltIndex](https://altindex.com/wallstreetbets)).
- **Discord alert rooms** have no integrated quotes; "proof" is cropped screenshots ([Demon review](/Users/pranavmulakala/personal/deterministic-swing-trading-research/output/DEMON_ALERTS_REVIEW_20261011.md)).
- **The founder's broker, Robinhood, can't trade through TradingView** ([Brokers](https://www.tradingview.com/brokers/)). His day therefore spans at least three apps: TradingView for charts, Robinhood for orders, Discord for alerts.

### Inferences
- **The opening isn't being first to combine the pieces;** it's being the first to make the combination feel live and trustworthy, along these lines:
  1. **Live sync:** chat timestamped and anchored to the price tick or candle it reacts to. The "play" in sports maps to a price move, a big print, a headline, a halt, or an earnings line item.
  2. **Structured moments:** earnings calls, Fed decisions, CPI, the open, 0DTE power hour, run like game threads.
  3. **A clean, ad-light interface.**
  4. **Trust:** optional verified positions and fills, and calls scored automatically against live quotes (the founder's audit method, turned into a product).
  5. **Finance-specific moderation against promoters.**
- **Main risks:**
  - X copying fast with vastly more distribution;
  - exchange data licensing costs (Cboe-type free feeds or crypto lower them);
  - moderation cost, as TradingView's retreat shows;
  - regulatory exposure if the product hosts paid alert-sellers.

### Gaps
- No direct measurements of comment-stream or quote latency on any platform.
- No retention or engagement data comparing these ticker pages.
- No user research on which "moments" retail traders most want to watch together. This would need interviews or a prototype test.
