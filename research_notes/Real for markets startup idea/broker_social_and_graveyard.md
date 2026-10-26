# Broker-linked and startup social investing, AI "why is it moving" explainers, and the social-investing graveyard (as of October 18, 2026)

*Compiled October 18, 2026. The shared web-search budget ran out partway through, so the later sections rest on direct fetches of URLs already found. Thin spots are listed under each Gaps heading. Quotes are paraphrased unless marked.*

## 1. Robinhood: social and community features as of October 2026, the status and reception of Robinhood Social, and overlapping features (Cortex, "why is it moving", live streams, prediction markets, Legend)

### Takeaway
Robinhood Social was announced on September 9, 2025. An invite-only beta started March 18, 2026, and it became generally available to all eligible US customers on September 29, 2026. It is free, every profile is KYC-verified, and trades post live from the ledger with P&L. Users can follow, comment, like and trade by hand from the feed. Coming or partly shipped: public-figure trades (via TipRanks), verified commentators and news, a live earnings-call experience, and a widget in Legend. Together with Cortex Digests (an AI note on why a stock may be moving), AI Agents, earnings prediction contracts and Legend, Robinhood is building nearly the founder's whole loop (live price, chart, news, talk, trade) for the founder's own user type, but only inside its own walls. There is little reception data so far: management calls the response strong and has published no engagement numbers.

### Cited Findings

**Timeline**
- Announced September 9, 2025 at HOOD Summit 2025 in Las Vegas as a trading community inside the app. The plan was an invite-only launch to select US customers in early 2026, free, run through a newly created Robinhood subsidiary — [Robinhood newsroom, Sep 10, 2025](https://robinhood.com/newsroom/hood-summit-2025-news/)
- At announcement, Robinhood said it was building Social itself, not buying Dub, and would invite about 10,000 testers first — [TechCrunch, Sep 9, 2025](https://techcrunch.com/?p=3044707)
- Axios framed the launch as Robinhood taking on Reddit and X (headline only; the article returned 403) — [Axios, Sep 10, 2025](https://www.axios.com/2025/09/10/reddit-x-robinhood-social-meme-stock)
- The beta opened March 18, 2026 to 1,000 HOOD Summit attendees, with 10,000 more to follow over the next weeks. Testers were picked on trading activity and frequency plus user research, i.e., the most active traders — [Robinhood newsroom, Mar 18, 2026](https://robinhood.com/us/en/newsroom/robinhood-social-beta); [MediaPost, Mar 19, 2026](https://www.mediapost.com/publications/article/413611/robinhood-launches-social-platform-for-trading-ma.html)
- In March 2026 a spokesperson expected a full rollout by year-end — [Fortune, Mar 18, 2026](https://fortune.com/2026/03/18/robinhood-rolls-out-long-awaited-social-feature-to-let-users-track-and-copy-other-traders/)
- Q1 2026 call (April 28, 2026), per a transcript summary: Social had reached its first 10,000 customers and management called the response strong. Users especially valued verified profiles, returns and trades. Robinhood was shipping requested features weekly (live stock charts, expanded profiles, tools for finding traders), and creators were asking to join — [Bullfincher earnings-call summary](https://bullfincher.io/companies/robinhood-markets/earnings-call)
- Q2 2026 call (July 29, 2026): Tenev said the aim was to open Social to everyone by quarter-end. He said that because Robinhood holds the trading data it can confirm posted trades are real, and that feed ranking and post features were still being tuned. No user numbers were given — [Q2 2026 call transcript (Motley Fool, via Webull)](https://www.webull.com/news/15364304610403328)
- September 29, 2026 (HOOD Summit 2026): Social went live to all eligible US customers — [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/). The support page lists it as rolling out now and available to all eligible customers — [Robinhood support: HOOD Summit 2026 announcements](https://robinhood.com/us/en/support/articles/hood-summit-2026-product-announcements/)

**Features**
- Beta feature set:
  - Trader profiles whose stats and trades are verified live, including when someone enters or exits a position.
  - Discussion, follows, comments, likes, and manual trading from the feed.
  - Trade posts for stocks, single-leg options, crypto and prediction markets.
  - Each trader's 1-year and daily P&L, profit rate and past trades.
  - KYC verification for every profile.
  - Slated for later in the beta: news feeds, futures and multi-leg options posts, and following insiders, hedge funds and politicians.
  - Source: [Robinhood newsroom, Mar 18, 2026](https://robinhood.com/us/en/newsroom/robinhood-social-beta)
- New at GA:
  - Post types for crypto and stock charts, portfolio allocations, and P&L.
  - Insider, politician and hedge-fund trade data from TipRanks, drawn from public filings. Robinhood says it does not verify this data, and these people are not Robinhood customers.
  - Source: [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/)
- Announced as coming soon at GA:
  - Verified market commentators from other websites and news outlets, plus company profiles, to bring breaking market news into the app.
  - A Robinhood Social widget in Legend.
  - A live earnings experience, promised in time for Q3 earnings season, where customers watch earnings calls and trade in real time.
  - Source: [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/)
  - **Conflict:** the support page lists the earnings experience as rolling out later and says customers will be notified — [Robinhood support](https://robinhood.com/us/en/support/articles/hood-summit-2026-product-announcements/)
- Robinhood disclaims user posts as the posters' own views, not its recommendations — [Robinhood newsroom, Mar 18, 2026](https://robinhood.com/us/en/newsroom/robinhood-social-beta)
- **Scale:** MediaPost put Robinhood at about 24 million funded accounts — [MediaPost, Mar 2026](https://www.mediapost.com/publications/article/413611/robinhood-launches-social-platform-for-trading-ma.html)

**Design and regulatory choices**
- **No automatic copying.** Users must copy trades by hand, unlike eToro. Fortune ties Robinhood's caution to two worries: endorsing stocks could count as investment advice, which only registered advisers may give, and influencer accounts could be fake and used for manipulation — [Fortune, Mar 18, 2026](https://fortune.com/2026/03/18/robinhood-rolls-out-long-awaited-social-feature-to-let-users-track-and-copy-other-traders/)
- **Copy trading is a reversal for Robinhood.** TechCrunch called it a striking about-face. In late 2024, Tenev told TechCrunch that copy trading could draw regulators' interest and that Dub was probably too small to be under scrutiny — [TechCrunch, Sep 9, 2025](https://techcrunch.com/?p=3044707)
- **Stated rationale:** active traders lean heavily on social media to follow markets, and it is getting harder to tell what is real online; verified trades are pitched as the fix — [Robinhood newsroom, Sep 10, 2025](https://robinhood.com/newsroom/hood-summit-2025-news/)
- **The fake-screenshot problem:** on Reddit and X, people share picks others imitate, and some post doctored trade screenshots — [Fortune, Mar 18, 2026](https://fortune.com/2026/03/18/robinhood-rolls-out-long-awaited-social-feature-to-let-users-track-and-copy-other-traders/)
- **Moderation is still being worked out.** At beta launch Robinhood said only that it would keep refining its content moderation policies — [Robinhood newsroom, Mar 18, 2026](https://robinhood.com/us/en/newsroom/robinhood-social-beta)
- **Gamification history:** Robinhood dropped its confetti animation in 2021 amid regulatory scrutiny of gamified investing — [NBC Boston/CNBC](https://www.nbcboston.com/news/business/money-report/robinhood-gets-rid-of-confetti-feature-amid-scrutiny-over-gamification-of-investing/2343214/?amp=1)

**Reception so far**
- **Simply Wall St (Mar 28, 2026, on Yahoo Finance):** KYC may curb some fake accounts but will not fully stop AI-driven identity fraud, and copied trading patterns remain possible. It found no adoption data — [Yahoo Finance/Simply Wall St](https://finance.yahoo.com/markets/stocks/articles/robinhood-social-launch-tests-trust-090524835.html)
- **A secondary blog** describes Reddit and media reaction as mixed: excitement about transparency, skepticism about gamification. Its sources are unverified — [SimpleFinanceBlog](https://simplefinanceblog.com/robinhood-social-review/)
- **Dub's founder, Steven Wang,** called Robinhood's move validating. He said Robinhood Social is built for active traders, while Dub serves people without the time to trade actively — [TechCrunch, Sep 9, 2025](https://techcrunch.com/?p=3044707)
- **Robinhood's GA post** gives no user, post or engagement numbers — [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/)
- **Next data point:** Robinhood's Q3 2026 earnings call is scheduled for October 27, 2026 — [Robinhood IR](https://investors.robinhood.com/node/16731/pdf)

**Overlapping Robinhood features**
- **Cortex Digests ("why is it moving"):**
  - Generative AI writes a plain-English note on why a stock may be moving, shown on the stock page.
  - Inputs are breaking news, analyst reports, technical indicators and Robinhood data.
  - It was announced at the 2025 "Lost City of Gold" event, began rolling out in the US in early summer 2025, and reached all UK customers free on August 19, 2025.
  - It does not cover every security.
  - Hundreds of thousands of US customers have used it; 95% of surveyed US users said they like it (self-reported).
  - It is labeled as not investment research or advice.
  - Source: [Robinhood newsroom, Aug 19, 2025](https://robinhood.com/us/en/newsroom/digests-by-robinhood-cortex-uk)
- **Cortex Scanner and custom indicators** (plain-English requests, near real-time matches) were announced for Gold members for early 2026 — [Robinhood newsroom, Sep 10, 2025](https://robinhood.com/newsroom/hood-summit-2025-news/)
- **Robinhood Agents and Agent Apps (HOOD Summit 2026):**
  - In-app AI agents that analyze the market, build strategies and trade from a dedicated agentic account, with manual approval on by default; recurring "Loops" are coming.
  - Paid Agent Apps include:
    - Options Trader by Unusual Whales ($30/mo)
    - Market Interpreter by Wendy ($10/mo)
    - Government Tracking by Quiver Quantitative ($10/mo)
    - ChatterFlow Viral Stocks Detector by Narravance ($8/mo; tracks narratives emerging from social chatter)
    - Fiscal.ai (coming soon)
  - Agentic trading launched in May 2026. More than 150,000 customers have opened agentic accounts, and agents call Robinhood's tools almost 30 million times a day.
  - Source: [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/)
- **Prediction markets:**
  - Earnings contracts (binary options via Cboe on KPIs such as beating earnings) are launching in the prediction-markets hub ahead of Q3 earnings season. They need options approval and carry no fees through year-end — [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/)
  - The support page lists earnings predictions as rolling out later and subject to regulatory approval — [Robinhood support](https://robinhood.com/us/en/support/articles/hood-summit-2026-product-announcements/)
  - On the Q2 call, the CFO said about 1.5 million people had used prediction markets, now closer to 2 million. The transcript's unattributed summary cites $156M in event-contract revenue and 13.6 billion contracts in Q2 2026 — [Q2 2026 call transcript](https://www.webull.com/news/15364304610403328)
- **Legend (desktop):**
  - Launched at the first HOOD Summit (2024); 90+ indicators added since — [Robinhood newsroom, Sep 10, 2025](https://robinhood.com/newsroom/hood-summit-2025-news/)
  - 2026 additions: a Robinhood Trading MCP for running third-party agents natively, the rebuilt "Helios" engine for faster charts, custom indicators later in the year, and the Social widget — [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/)
  - Legend joined Robinhood's $100M+ ARR group in Q2 2026 — [Q2 2026 call transcript](https://www.webull.com/news/15364304610403328)
- **Live events:**
  - Robinhood's earnings call is a livestreamed event with an in-person audience and shareholder questions submitted through Say. Tenev called the Q2 call the largest earnings-event audience yet — [Q2 2026 call transcript](https://www.webull.com/news/15364304610403328)
  - HOOD Summit sessions stream at robinhood.com/presents — [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/)

### Inferences
- **Robinhood is building most of the founder's product for the founder's exact user.** Live quotes and charts already exist. Social adds verified real-time trade posts with reactions. News is coming through verified commentators, live play-by-play through the earnings experience, "why is it moving" through Digests, and a bet on the outcome through earnings contracts. The beta was seeded with the most active traders, which points squarely at the founder's segment: newer, active options traders on Robinhood.
- **Robinhood's built-in advantages:**
  - Verification is free, because the trade ledger is the proof.
  - It has about 24M funded accounts.
  - It earns from trades, so Social can be free.
- **Robinhood's built-in limits:**
  - **Walled garden.** Only Robinhood customers can post verified trades; everyone else shows up only as public-filing data.
  - **Compliance-first.** As a public broker-dealer it chose manual copying only, staged the rollout over about a year (September 2025 announcement to September 2026 GA), and is still refining moderation. That likely mutes raw, fast banter.
  - **No cross-broker identity.** The same trader on Webull or Schwab is invisible.
- **The open lane is narrow.** A broker-neutral, cross-app real-time layer is the one space Robinhood does not occupy, but it is where Commonstock, AfterHour, Blossom and ticker already play (see sections 4 and 6).
- **Robinhood's earnings bundle is the closest incumbent match to "Real."** Live earnings experience plus Social plus earnings contracts amounts to reacting to each play and betting on the result, right where users trade.
- **Reception is untested at scale.** GA came 19 days before these notes. The October 27 earnings call is the first chance for engagement numbers.

### Gaps
- No public metrics for Social's daily users, posts, retention or creator count, and no app-store review analysis specific to Social.
- Unconfirmed whether the live earnings experience shipped for Q3 earnings season (the newsroom and support page conflict).
- What "eligible" means at GA (age, account type, options level) is unstated.
- Axios's Sep 2025 article could not be fetched, and the Q1 2026 transcript details come from an aggregator summary, not the full text.

## 2. eToro: CopyTrader and the social feed (scale, how social drives engagement and revenue, IPO-era disclosures)

### Takeaway
eToro is the scaled proof that broker-integrated social and copy trading can be a profitable business. At end-2024 it had 40M+ registered users, about 3.5M funded accounts, $787M net contribution and $192M net income; funded accounts reached 4.28M in Q2 2026. Social is a layer on a trading business, not a business by itself, and its creator economy follows a steep power law: about 3,300 Popular Investors (0.1% of funded accounts), only 12 with more than $10M copied. eToro still spent heavily on paid acquisition ($500M of $1.2B revenue in 2021, per its CEO). It is now pushing into the US with CopyTrader, an advisory (RIA) license and the TradeZero acquisition.

### Cited Findings
- **F-1 core figures:**
  - 40M+ registered users across 75 countries.
  - About 3.5M funded accounts at Dec 31, 2024.
  - Net contribution of $787M in 2024, up 41% from $557M.
  - Total commission of $931M, up 46%.
  - Net income of about $192.4M, versus $15M in 2023.
  - Adjusted EBITDA of $304M.
  - Source: [eToro F-1 (SEC)](https://www.sec.gov/Archives/edgar/data/1493318/000101376225001589/ea0223534-08.htm)
- **F-1 on social features:** the stated goal is deeper engagement and loyal, long-term relationships, but the filing does not quantify the effect on retention, deposits or revenue in the sections reviewed. It cites research that over 60% of US investors under 35 use social media as a primary source of investment information — [eToro F-1](https://www.sec.gov/Archives/edgar/data/1493318/000101376225001589/ea0223534-08.htm)
- **F-1 risk factors on social and copy trading:**
  - Copy-trading rules are inconsistent across jurisdictions.
  - When many users copy one Popular Investor, large numbers of trades may fail to settle, which raises market-integrity concerns.
  - Users can lose money and complain or sue.
  - Copied strategies may be opaque, creating exposure to market abuse.
  - User posts may be misleading or manipulative.
  - Education tools could be read as investment advice.
  - Regulators are acting against "finfluencers."
  - Negative opinions can be amplified by the social platform itself.
  - Source: [eToro F-1](https://www.sec.gov/Archives/edgar/data/1493318/000101376225001589/ea0223534-08.htm)
- **Creator power law:** more than 3,300 Popular Investors at Dec 31, 2024, about 0.1% of funded accounts; only 12 had more than $10M copied — [Sacra, citing the eToro F-1](https://sacra.com/chat/h/d9dcbcc5-e54d-4699-b54a-c12461eb1977/)
- **Popular Investor pay:** Elite Pro Popular Investors earn 1.5% a year on copied assets up to $20M and 0.5% above that, paid monthly. Eligibility requires a verified, funded account with at least $1,000 in equity and at least one copier — [eToro Popular Investor page](https://etoro.com/popular-investor)
- **Minimum copy:** $200 — [Sacra](https://sacra.com/chat/h/d9dcbcc5-e54d-4699-b54a-c12461eb1977/)
- **CEO Yoni Assia (Nov 2022):** about one in a thousand retail users becomes a Popular Investor. In the prior year, $500M of $1.2B revenue went to marketing (about 40%). At the time eToro had 30M registered users and 2.7M funded accounts — [OMR, Nov 23, 2022](https://omr.com/en/daily/omr-podcasat-etoro-yoni-assia)
- **IPO:** the May 2025 IPO raised $310M and the shares rose 29% on debut — [TechCrunch, Sep 2025](https://techcrunch.com/?p=3044707)
- **US copy trading:**
  - CopyTrader launched in the US in 2025 — [eToro Q4/FY2025 results](https://investors.etoro.com/news-releases/news-release-details/etoro-reports-fourth-quarter-and-full-year-2025-results)
  - US users can copy only other US traders — [TechCrunch, Sep 2025](https://techcrunch.com/?p=3044707)
- **FY2025:**
  - Funded accounts of 3.81M, up 9% from 3.48M; the same results package also shows 3.85M.
  - Assets under administration reported as both $18.5B (up 11%) and $18.4B (up 2%).
  - Source (both figures unreconciled): [eToro Q4/FY2025 results](https://investors.etoro.com/news-releases/news-release-details/etoro-reports-fourth-quarter-and-full-year-2025-results)
- **Q2 2026 (reported Aug 11, 2026):**
  - Funded accounts of 4.28M, up 18%; assets under administration of $19.2B; net contribution of $229M, up 9%; GAAP net income of $53.5M, up 77%.
  - The CFO credited strength in equity trading and Copy Trading activity.
  - New products: Tori, an in-app AI agent; Agent Portfolios; a US RIA (eToro USA Advisors) for Smart Portfolios; and an app store with more than 75 apps.
  - eToro agreed to acquire TradeZero, a US broker for active traders, expected to close in H1 2027.
  - Source: [eToro Q2 2026 results](https://www.etoro.com/news-and-analysis/press-releases/etoro-reports-second-quarter-2026-results/)
- **Conflicting coverage:** a trade-press headline says Q2 2026 revenues fell 11% and the shares dropped 10%. That likely measures something other than net contribution — [FX News Group](https://fxnewsgroup.com/forex-news/retail-forex/etoro-shares-drop-10-as-revenues-fall-11-in-q2-2026-to-229-million/)
- **Industry context:** Brokeree data shows copy trading made up 6–20% of brokers' trading volume in recent years, and 10–20% at firms that promoted it in 2024. Google searches for "copy trading" have risen about 20% a year for four years — [Finance Magnates, Jun 2025](https://www.financemagnates.com/forex/publiccom-terminates-social-trading/)
- **X cashtags:** eToro was the 2023 test partner for X's cashtag-to-broker links, then still Twitter — [Finance Magnates, Oct 2, 2026](https://www.financemagnates.com/forex/brokers/webull-joins-x-cashtag-program-as-social-feed-adds-broker-links/)

### Inferences
- Social pays at eToro because each copy produces commission-bearing trades. The social feed is the engagement layer and CopyTrader is the monetization engine. A pure social or media app does not capture that flow.
- The supply side is a steep power law: a handful of trusted traders carry most copied assets. Any "Real for markets" needs a small set of credible, verifiable voices more than a large crowd.
- Even with viral social mechanics, eToro still buys growth heavily. Social reduces churn; it does not replace marketing.
- eToro's US moves (CopyTrader, RIA, TradeZero for active traders) add a second scaled social-trading incumbent to the US active-trader market in 2026–27.

### Gaps
- Total copied assets, the share of funded accounts that copy, and social-feed engagement metrics were not found in the F-1 sections retrieved (the last ~45k characters were not read). A third-party template's claims ($3.2B copied, 1.1M copy relationships) are unverified.
- No data isolating social's effect on eToro retention or lifetime value.

## 3. Public.com: social features launched, later removed or changed, and why

### Takeaway
Public launched in 2019 as a social investing app: public profiles, a feed where users explained their trades, private and group messaging (2020), later Public Live market shows, Town Halls with executives, and a Learn tab. It went PFOF-free in February 2021 at a $1.2B valuation. On June 5, 2025 it shut its social features ("Sunsetting Social"). Its reasons: the feed's main content, earnings recaps and daily market updates, is now made by AI, and its newer customers are experienced investors. It repositioned as a multi-asset platform led by AI (Alpha from 2023, Generated Assets from 2025).

### Cited Findings
- **May 2020 feature set:** public profiles showing holdings and watchlists, a feed for explaining investment choices, and private and group messaging launched May 7, 2020 — [TechCrunch, May 7, 2020](https://techcrunch.com/2020/05/07/as-investing-apps-boom-public-doubles-down-on-its-social-focus/)
- **COVID growth, March to April 2020:** new customers +80% month over month, trading +100%, time in app +200%, mostly organic and referral-driven. Co-CEO Jannick Malling said uncertain times call for community and that no real social network for investing existed — [TechCrunch, May 7, 2020](https://techcrunch.com/2020/05/07/as-investing-apps-boom-public-doubles-down-on-its-social-focus/)
- **Contrary Research profile:**
  - **Founding:** founded in 2019 (first name Matador) with a social-investing mission; community investing was its first point of difference.
  - **Feed in Oct 2023:** views for trending, following, news, Public Live, learn, town hall and saved. Public Live ran 15–30 minute market shows; Town Halls hosted Fortune 500 executives; "Pulse" connected public companies with retail investors.
  - **PFOF:** went PFOF-free in February 2021.
  - **Users:** over 1M users in its first 18 months; an unverified report put the base at about 3M in March 2023.
  - **Funding:** a $220M Series D at a $1.2B valuation in February 2021; about $308.5M raised in total by October 2023.
  - **Revenue:** none of it from social. Sources are interest on cash, Premium at $8/month, fees, tipping, crypto markups, alternative assets and securities lending.
  - **AI:** Alpha, a GPT-4 assistant, launched in May 2023.
  - Source: [Contrary Research](https://research.contrary.com/company/public)
- **The sunset (announced June 5, 2025):** in a blog post titled "Sunsetting Social," Public said the feed's core use had been people posting earnings-call recaps and market updates, and that this content is now "created by AI—faster, more accurate" — [Finance Magnates, Jun 6, 2025](https://www.financemagnates.com/forex/publiccom-terminates-social-trading/)
- **Other reasons given:** FX News Group framed the change as AI cannibalizing social. It added that Public is now a suite of multi-asset tools whose new customers mostly have extensive investing experience, and that Public will keep expanding Generated Assets and Alpha — [FX News Group, Jun 5, 2025](https://fxnewsgroup.com/forex-news/retail-forex/public-shuts-down-social-trading/)
- **Generated Assets** (May 2025) turns a thematic idea into a custom equity index. Public now positions itself as a multi-asset platform (stocks, options, bonds, margin, crypto via Bakkt) — [Finance Magnates, Jun 6, 2025](https://www.financemagnates.com/forex/publiccom-terminates-social-trading/)

### Inferences
- Social was Public's acquisition story but never its revenue model. Once the company chased higher-value, experienced customers, the feed became a cost centre and a brand mismatch.
- The most common user content, recaps and summaries, is exactly what AI now makes for free. A 2026 social product cannot be built on human-written recaps.
- What AI cannot replace is identity, status, verified skin in the game, and live human reaction while an event is happening. That is the sliver a "Real for markets" would need to own.

### Gaps
- No engagement or retention metrics for Public's feed were found, and no statement on whether moderation or compliance costs played a role.
- The exact shutdown mechanics (comments, follows, message history) were not described in the sources found.

## 4. Commonstock (product, traction, acquisition by Yahoo Finance, what became of it) and Yahoo Finance community features today

### Takeaway
Commonstock (launched 2020) was a broker-agnostic social network where posts and performance came from linked brokerage accounts. It had more than $10B in connected assets and about $25–34M raised from Coatue, QED, Floodgate and others. Yahoo bought it on August 23, 2023 on undisclosed terms and moved all its staff into Yahoo Finance to drive ad-supported engagement and subscriptions. As of October 18, 2026, commonstock.com redirects to Yahoo Finance's "community/join" URL. Yahoo Finance now runs a verified Community tab built on linked-brokerage "real money," where upvotes are weighted by followers' real assets, alongside its older Conversations message boards on each quote page.

### Cited Findings
- **The deal (Axios, first to report):** citing Yahoo Finance GM Tapan Bhat, Yahoo bought Commonstock to fold it into its free and subscription products, driving ad-supported engagement and subscriptions. All Commonstock employees joined Yahoo Finance. Crunchbase put funding at about $34M, and Bhat declined to discuss terms — [Axios, Aug 23, 2023](https://www.axios.com/2023/08/23/commonstock-yahoo-social-investing-platform)
- **Background:** launched in 2020; more than $10B in connected assets; investors included Coatue, QED, Floodgate, Upside Ventures, Resolute Ventures and Abstract Ventures — [FinTech Futures](https://www.fintechfutures.com/m-a/yahoo-finance-builds-out-investor-insights-with-commonstock-acquisition)
- **Funding and audience:** Commonstock raised $25M in 2021. Yahoo Finance had more than 150 million global monthly users. Bhat framed the deal around pre- and post-trade conversations among like-minded investors — [Finextra](https://www.finextra.com/newsarticle/42836/yahoo-buys-social-investing-platform-commonstock)
- **Described as broker-agnostic:** Yahoo called it a broker-agnostic social and community platform for retail insights; deal dated Aug 23, 2023 — [Law360](https://www.law360.com/fintech/articles/1714387/yahoo-buys-retail-investing-social-platform-commonstock)
- **Terms:** undisclosed (per Fortune's 2024 AfterHour coverage) — [Fortune, Jun 17, 2024](https://fortune.com/2024/06/17/exclusive-after-hour-social-trading-startup-raises-4-5-million-seed-round-led-by-founders-fund-and-general-catalyst)
- **What became of it (observed Oct 18, 2026):** commonstock.com returns a 301 redirect to finance.yahoo.com/community/join (that page itself returned 404 to the fetcher) — [commonstock.com](https://commonstock.com)
- **Yahoo Finance Community tab:**
  - Pitched as a community for serious investors where you follow top voices; users post, comment and upvote.
  - Upvotes are expressed in "Follower Assets," described as real money in real brokerages: anonymous, visible once a user has 30+ followers, and based on a rolling average of followers' portfolios. A user's upvotes count in ranking only after they build trust.
  - Insights come only from "real money" in linked brokerage accounts, not portfolios built in Yahoo.
  - Users can appeal removed posts.
  - Source: [Yahoo Help SLN37021](https://help.yahoo.com/kb/SLN37021.html)
- **Yahoo Finance Community guidelines:**
  - **Banned:** false or misleading content (including pump-and-dump), guaranteed-return claims, insider tips or material nonpublic information, posts steering commercial activity off Yahoo, artificially inflated engagement, impersonating experts or companies, and non-substantive or non-financial posts.
  - **User types:** individual investors, regulated financial professionals and other financial professionals, with disclosure rules that vary by type.
  - **Enforcement:** content removal, suspensions, warnings or account termination.
  - Source: [Yahoo Finance Community Guidelines](https://legal.yahoo.com/us/en/yahoo/finance-guidelines/index.html)
- **Conversations boards:** message boards on each stock's page, sorted by "Most recent" or "Top reactions"; login required to post or react — [Yahoo Help SLN29197](https://help.yahoo.com/kb/SLN29197.html)

### Inferences
- Commonstock's outcome fits the category's pattern. A verified, broker-agnostic social network gained assets but not standalone scale, and became a feature inside a giant portal. Yahoo appears to have kept its key mechanics: verified real-money identity and ranking weighted by real assets.
- Yahoo Finance already pairs live price, chart and news with both an open comment board and a verified community. Its gap is speed and real-time feel, not breadth. "One clean place" exists in part; "live and fun" does not.
- Weighting reactions by real money is a tested trust device worth borrowing.

### Gaps
- No Commonstock user or active-user counts, no deal price, and no exact shutdown date for the standalone app.
- No launch date or usage data for Yahoo's Community tab, and no 2025–2026 Yahoo AI features ("key takeaways" and similar) were researched.

## 5. Webull and moomoo: community feeds, live streams, and engagement

### Takeaway
Both brokers have long built a community into the trading app. moomoo (Futu) has the deepest version. In 2021 it reported over 1M daily users in its community and more than 700 companies, fund managers, media and influencers posting and livestreaming. It now runs livestreams of earnings calls and influencer broadcasts with live comments, likes and gifts, plus influencer-run group chats, on Tencent's real-time infrastructure. Webull runs a moderated community with trading surveillance, a "Corporate Connect" product for issuers, and, since autumn 2026, broker links from X cashtags. Neither discloses recent US community engagement.

### Cited Findings
- **Webull scale:** 28.2M registered users at end-June 2026, up about 3.3M year over year; Webull describes its community as integrated with market data and education — [Webull June 2026 operating data](https://www.nasdaq.com/press-release/webull-corporation-reports-june-2026-operating-data-2026-07-15). Also 5.13M funded accounts and $28.5B in customer assets at end-June — [Finance Magnates, Oct 2, 2026](https://www.financemagnates.com/forex/brokers/webull-joins-x-cashtag-program-as-social-feed-adds-broker-links/)
- **X's Cashtag Partner Program** (X covered more fully by another researcher):
  - X launched it in the US on September 15 with Interactive Brokers, moomoo, Coinbase, Kraken and Gemini; Webull joined about two weeks later.
  - Tapping a cashtag opens the asset's live chart and related posts with partner-broker links; trades happen at the broker, not on X.
  - Source: [Finance Magnates, Oct 2, 2026](https://www.financemagnates.com/forex/brokers/webull-joins-x-cashtag-program-as-social-feed-adds-broker-links/)
  - **Conflict:** one search snippet dated Webull's joining to February 2026, but the article itself is dated October 2, 2026.
- **Webull and TradingView (2024):** the integration let Webull users chart, backtest and connect with other traders inside Webull — [Finance Magnates](https://www.financemagnates.com/forex/webull-integrates-tradingviews-advanced-tools-for-traders-in-the-usa/)
- **Corporate Connect:** Webull runs this service for public companies to engage investors (e.g., Upexi joining) — [Nasdaq](https://www.nasdaq.com/articles/upexi-inc-joins-webull-corporate-connect-service-enhance-investor-engagement-and)
- **Webull community moderation (Australia):**
  - Users must accept a binding Community Agreement before posting.
  - Webull monitors daily for market abuse, bullying and harassment; it blocks posts, warns or bans users, and monitors flagged users' trading for manipulation.
  - Regulators can look back seven years.
  - Source: [Webull Australia courseware](https://www.webull.com.au/learn/courseware/vYm9Bg)
- **moomoo 2021:** a moomoo press release described the moo community as having over 1M daily active users and more than 700 companies, fund managers, media and key opinion leaders engaging through posts and livestreams. moomoo also title-sponsored Yahoo Finance's 2021 Berkshire meeting livestream to reach its 13M users — [StockTitan, moomoo press release](https://www.stocktitan.net/news/FUTU/moomoo-inc-clinches-title-sponsorship-for-yahoo-finance-s-exclusive-z9ugmvu5avf0.html)
- **Q3 2023:** moo community engagement and user-generated content rose about 60% from the prior quarter — [Futu Q3 2023 release (AAP)](https://www.aap.com.au/aapreleases/cision20231123ae76485)
- **Q2 2025:** daily users, user content and engagement in the community grew quarter over quarter, and in-app education drew nearly 2M visits — [Futu Q2 2025 release (Barchart)](https://www.barchart.com/story/news/34267128/moomoo-s-parent-company-futu-releases-q2-2025-results-net-income-up-105-yoy-to-us339-million)
- **FY2025 (reported Mar 12, 2026):**
  - 29.18M users and 3.37M funded accounts.
  - FY revenue of $2.94B, up 68.1%; non-GAAP net income of $1.50B.
  - A Moomoo x Nasdaq paper-trading competition drew more than 350,000 entrants.
  - AI coverage expanded to options, IPOs, bonds and ETFs, plus "AI Algo Trading" built from plain-language instructions.
  - No livestream metrics.
  - Source: [Futu FY2025 release](https://digital-release.wboy.com/business/press-releases/cision/20260312CN08754/moomoos-parent-company-futu-achieves-consecutive-growth-in-q4-and-full-year-2025)
- **moomoo live and chat stack (vendor case study, May 8, 2026):**
  - Influencer-created discussion groups with member controls.
  - Livestreams for earnings calls, market events and influencer broadcasts, with real-time comments, gifts and likes, mute and ban tools, and multilingual delivery.
  - Claimed capacity of 10M messages in 30 seconds; vendor claims, unverified.
  - Source: [Tencent RTC case study](https://trtc.io/blog/details/moomoo-tencent-rtc-chat-live-solution)

### Inferences
- The "watch the event live and react" format already exists inside moomoo, for earnings calls in particular, and runs on commodity real-time infrastructure. The technology is not the moat.
- Asian-heritage brokers treat community as a retention feature. None reports US community metrics, which suggests US adoption is modest relative to the overall user base.
- X's cashtag pages (live chart, posts and a broker link) are converging on the founder's "one place for price, chart and talk" from the social-network side, with brokers paying for the traffic.

### Gaps
- No US-specific daily-user, post or livestream-viewership figures for Webull or moomoo. Webull's own livestream features were not confirmed.
- No data on how often moderation or manipulation-surveillance actions fire.

## 6. Blossom, Dub, Autopilot, AfterHour, ticker, and other copy-trading or verified-portfolio social apps: traction and business models

### Takeaway
Two models have traction:
- **Verified-portfolio social networks** (Blossom, AfterHour, ticker; formerly Commonstock) link brokerages read-only to prove positions. They earn from brand partnerships, subscriptions or virtual goods.
- **RIA-registered copy-investing apps** (Dub, Autopilot) automatically mirror portfolios of creators, politicians and funds, and earn from subscriptions.

Blossom is the clearest standalone social success: 750k+ members and more than $6.5M annualized revenue in Q2 2026. Autopilot (about $750M–$1B in assets, 3M downloads, 80k paid subscribers) and Dub ($47M raised, 1M+ downloads) show that a "copy a public figure" hook pulls consumers.

### Cited Findings

**Blossom (Vancouver; founded 2021)**
- **May 2024:** more than 125,000 users, mostly in Canada, adding over 10,000 a month.
  - **Revenue mix:** about two-thirds brand partnerships (e.g., Canadian ETF issuers) and one-third subscriptions; it expected about $1M in 2024 revenue and to be cash-flow positive in 2025.
  - **Seed:** C$2.1M+, about C$1M of it crowdfunded from 793 users (average C$1,277); total raised near $4M.
  - **Strategy:** it scrapped its "Canada's first social brokerage" plan about 10 months earlier. CEO Maxwell Nicholson called it the wrong strategy and brokerages extremely capital-intensive, citing competition and new entrants such as Webull.
  - **Product:** posts backed by linked brokerage activity (verified portfolios), dividend tracking and "Duolingo-style" lessons.
  - **Growth playbook:** influencer ambassadors.
  - Source: [BetaKit, May 21, 2024](https://betakit.com/blossom-closes-2-1-million-to-grow-its-investing-social-network-in-the-us/)
- **June 23, 2026:**
  - **Members:** grew from 250k to over 750k in a year; the US added over 200k (+187%) and is its fastest-growing market.
  - **Revenue:** on track for more than $6.5M annualized revenue in Q2 2026.
  - **Fundraising:** about $2.2M from about 1,000 investors through crowdfunding within roughly a day.
  - **Next:** a UK launch planned for later in 2026.
  - Source: [BetaKit, Jun 23, 2026](https://betakit.com/blossom-social-raises-more-than-2-million-through-frontfundr-campaign)

**Dub (New York; founder Steven Wang)**
- **Feb 2024:** a $17M round led by Tusk Venture Partners, including $2M of SVB debt; individual backers reportedly included Uber's CEO and a Robinhood co-founder — [FinanceFeeds](https://financefeeds.com/dub-raises-17-million-for-unique-us-copy-trading-platform/)
- **May 2, 2025:**
  - A $30M Series A co-led by Notable Capital and Neo, plus $5.5M of SVB debt; $47M raised in total.
  - More than 1M downloads within a year of leaving stealth.
  - A creator program run through dub Advisors pays royalties to investors who publish model portfolios that users mirror in one tap.
  - Source: [Pulse 2.0](https://pulse2.com/dub-30-million-series-a-closed-for-scaling-copy-trading-platform)
- **Pricing and positioning:**
  - Dub auto-copies whole portfolios for a $10/month subscription and launched officially in 2024 — [TechCrunch, Sep 9, 2025](https://techcrunch.com/?p=3044707)
  - In February 2025, Wang criticized Robinhood for making trading easy without guidance, which he likened to gambling, and for misaligned public-company incentives — [TechCrunch](https://techcrunch.com/?p=3044707)

**Autopilot (founder Chris Josephs, creator of the "Pelosi Tracker" account)**
- **November 2025:**
  - Raised $8M to expand from San Francisco to New York and hire engineers and marketers; reported $1B under management and 3M downloads.
  - With Pelosi retiring, it plans to move the roughly $500M following her trades into a broader "general insider trading" portfolio of other members of Congress.
  - Sources: [Techleap news feed](https://finder.techleap.nl/news/feed/autopilot-raises-8m-expands-operations); [Benzinga](https://benzinga.com/z/49021235). The search summary did not say which outlet carried which detail.
- **Oct 2025:** more than $750M in assets, 3M downloads and 80,000 paid subscribers; described as one of the fastest-growing registered investment advisers — [TradersPost event page](https://blog.traderspost.io/article/chris-josephs-copy-trading-at-benzinga-2025)
- **Registry:** an SEC-registered adviser (CRD 331749) with assets listed as undisclosed and "Pelosi Tracker+" at $543.7M committed — [Altss registry profile](https://altss.com/profile/autopilot)
- **Earlier milestones:** $55M invested — [Yahoo](https://sg.news.yahoo.com/traders-invested-55-million-using-193917633.html); more than $400M following Pelosi's trades — [Benzinga](https://benzinga.com/z/49021235)
- **Politics:** Autopilot says it fully supports a ban on congressional stock trading — [KUTV](https://kutv.com/news/nation-world/gridlock-looms-on-congressional-stock-trade-ban-as-parties-clash-over-divestment-senate-democrats-autopilot-nancy-pelosi)

**AfterHour (founder Kevin Xu, "Sir Jack" of WallStreetBets)**
- **June 2024 seed:** $4.5M led by Founders Fund and General Catalyst, with Pear VC. No user count was disclosed. Xu likened markets to a reality TV show everyone plays and framed the mission as credibility, transparency and trust — [Fortune, Jun 17, 2024](https://fortune.com/2024/06/17/exclusive-after-hour-social-trading-startup-raises-4-5-million-seed-round-led-by-founders-fund-and-general-catalyst)
- **Website:**
  - **Product:** verified trades attached to posts (pitched as the end of fake screenshots), live "Signals," a feed, and chat rooms for each ticker.
  - **Claims:** $400M+ in connected portfolio assets, 200,000+ users and 6.9M+ signals sent.
  - **Terms:** free; read-only Plaid connections to more than 1,000 brokerages; disclaims broker-dealer and adviser status.
  - **Staleness signs:** some sections still contain "Lorem Ipsum" placeholder text and the footer reads © 2024.
  - Source: [afterhour.com](https://www.afterhour.com/)
- **App Store:**
  - 4.5 stars from 808 ratings.
  - Large per-stock chat rooms with emoji reactions.
  - A "Copy Trade" button that opens a market order on Robinhood.
  - Paid "Coins" from $2.99 to $419.99, plus real-money raffles (April 2025).
  - A "Trump Tracker" (May 2025); latest update dated "Mar 19," probably 2026.
  - Source: [App Store: AfterHour](https://apps.apple.com/us/app/afterhour-social-copy-trading/id1640766056)

**ticker (The Ticker App, Inc.; launched about 2025)**
- **Features:**
  - Trades post automatically from linked brokerages, with optional "Brokerage Notes" explaining the reasoning.
  - A verified activity feed, head-to-head stock-picking "Duels," buy/hold/sell polls, groups, trending tickers, an AI chat assistant and a daily market recap.
- **Ratings:** 5.0 stars from only 13 ratings.
- **Pricing:** ticker Pro at $7.99 plus small add-on purchases.
- **History:** version 1.1.0 (Dec 18, 2025) added groups, likes and comments; frequent updates through autumn 2026.
- Source: [App Store: ticker](https://apps.apple.com/us/app/ticker-social-investing/id6751128739)

### Inferences
- Verifying portfolios through Plaid or SnapTrade-style read-only links is cheap and widely copied: Commonstock, Blossom, AfterHour, ticker and Yahoo all do it, and Robinhood does it natively. It is table stakes, not a moat.
- Revenue per user in pure social is low. Blossom's run-rate works out to roughly $8–9 per member per year ($6.5M ÷ 750k; computed here). Copy-investing subscriptions earn more but require RIA registration and compliance overhead.
- Every cold-start success leaned on an existing audience or celebrity-style content: Pelosi trades (Autopilot), politician and creator portfolios (Dub), a famous WallStreetBets trader (AfterHour), and paid influencer ambassadors plus user-shareholders through crowdfunding (Blossom).
- AfterHour's drift toward coins, raffles, copy buttons into Robinhood and "Trump Tracker" content suggests a pure ticker-chat product struggles to monetize without gamified or transaction hooks. This is an inference from feature changes, not a company statement.

### Gaps
- No current (2026) user or asset figures for Dub, and no public Autopilot price.
- AfterHour's real active users are unclear. A search snippet cited a 2024 report of about 23,000 users versus the site's 200k+ claim, but the underlying source could not be confirmed.
- ticker's funding and team are unknown.

## 7. New entrants 2024–2026: "live social markets," "Twitch for trading," "Stocktwits competitor," "Real/ESPN for stocks"

### Takeaway
No funded startup was found branded as "Real for stocks" or "ESPN for stocks." The closest live-first attempt, Trading.TV (2021–22, about $14.1M raised, pitched as a Robinhood-Twitch combo), has disappeared under that brand: its domain now redirects to an unrelated-looking wealth manager. Live per-ticker chat survives as a feature (AfterHour, moomoo, Robinhood Social). In 2025–26 venture money went to apps that own the transaction: Fomo ($17M Series A in Nov 2025, $75M Series B in June 2026 at a reported ~$550M valuation, expanding from crypto into equities and prediction markets), Dub and Autopilot. The biggest moves into the founder's space come from incumbents: Robinhood Social with live earnings, X cashtag pages with live charts and broker links, Google Finance's live earnings with AI, eToro's US push, and Yahoo's verified Community.

### Cited Findings
- **Trading.TV:**
  - Pitched at seed as a cross between Twitch and Slack for traders after a $6.1M raise — [Benzinga](https://benzinga.com/z/22549188)
  - Feb 2022: an $8M Series A led by Lightspeed to build a "Robinhood-Twitch" combination where viewers could trade from a creator's video page. Axios also reported the earlier $6.1M seed, led by L Catterton Growth, Activant, Navy Capital and Tribe Capital — [Axios, Feb 16, 2022](https://www.axios.com/2022/02/16/tradingtv-series-a-funding)
  - Came out of stealth in August 2021 on iOS, Android and desktop as a social livestream-and-chat platform for traders and finance creators; Lightspeed took a board seat — [Benzinga](https://benzinga.com/fintech/22/02/25680090/trading-tv-secures-8m-in-round-led-by-lightspeed-venture-partners)
- **Trading.TV's current status (observed Oct 18, 2026):** trading.tv returns a 301 redirect to atlasfinancial.com, a wealth manager (ATFS Advisers LLC, an SEC-registered adviser) that does not mention Trading.TV — [trading.tv](https://trading.tv); [Atlas Financial](https://atlasfinancial.com/)
- **Precedents:**
  - TradingView launched live "Streams" in 2020, billed as a "Twitch for Traders" (TradingView is covered by another researcher) — [Benzinga, Feb 2020](https://www.benzinga.com/fintech/20/02/15429532/twitch-for-traders-tradingview-launches-real-time-streaming-platform-for-investors)
  - A student project, "Sweater," pitched live trading streams and won a University of Georgia accelerator — [UGA Terry College](https://www.terry.uga.edu/streaming-platform-stock-traders-wins-uga-idea-accelerator)
- **Fomo** (crypto-first social trading; another researcher covers crypto platforms):
  - **Nov 2025:** a $17M Series A led by Benchmark ($19M total), with 120k users and about $700M in volume at the time — [TechCrunch, Nov 6, 2025](https://techcrunch.com/2025/11/06/why-benchmark-made-a-rare-crypto-bet-on-trading-app-fomo-with-17m-series-a); see also [Decrypt](https://decrypt.co/347810/morning-minute-fomos-17m-raise-and-the-rise-of-the-everything-apps)
  - **June 2026:** a $75M Series B led by Index Ventures, with Union Square Ventures and Benchmark. Fomo reports 600k+ users and $4B+ in volume and plans to add equities, perpetual futures and prediction markets — [FinTech Global, Jun 24, 2026](https://fintech.global/2026/06/24/fomo-raises-75m-series-b-to-scale-on-chain-trading/)
  - **Valuation:** reported at about $550M, with about $94M raised in total; reports on dates and users don't fully reconcile — [Startup Fortune, Jul 13, 2026](https://startupfortune.com/social-crypto-trading-app-fomo-raises-at-a-550-million-valuation-as-dex-volume-reshapes-the-retail-market/)
- **AfterHour** ($4.5M seed in 2024; live ticker chat rooms) and **ticker** (2025; auto-posted verified trades, Duels, a daily recap) are the closest US stock-social startups found — see section 6 and [App Store: ticker](https://apps.apple.com/us/app/ticker-social-investing/id6751128739)
- **Incumbent moves into the space:**
  - **X:** the Cashtag Partner Program (US, Sept 2026) turns ticker taps into live chart plus posts plus broker links — [Finance Magnates, Oct 2, 2026](https://www.financemagnates.com/forex/brokers/webull-joins-x-cashtag-program-as-social-feed-adds-broker-links/)
  - **Robinhood:** Social at GA, a live earnings experience, verified commentators, and a social-chatter narrative detector (Narravance) among its Agent Apps — [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/)
- **Framing:** Forbes (Nov 2025) cast social trading as a new layer of financial infrastructure (article returned 403; headline and search snippet only) — [Forbes, Nov 7, 2025](https://www.forbes.com/sites/boazsobrado/2025/11/07/why-social-trading-is-the-new-financial-infrastructure-layer/)

### Inferences
- "Twitch for trading" was funded before (Trading.TV, TradingView Streams) and did not yield a lasting standalone brand. Live-first market media has struggled to keep audiences outside earnings and events.
- Venture money in 2025–26 favored products that own the trade or the advisory relationship, not pure social or media. A "Real for markets" with no transaction revenue is swimming against that tide unless it finds a different monetization path, for example premium real-time data, verified-creator subscriptions, or broker referrals like X's.
- The competition is mostly incumbent features, not one startup, so the wedge has to be something incumbents structurally won't do. Candidates:
  - Cross-broker neutrality.
  - Fast, unfiltered banter that a regulated broker won't host.
  - Coverage of off-broker content, such as auditing paid Discord alert groups against market data.

### Gaps
- The search budget ran out before Crunchbase- or PitchBook-style sweeps for 2025–26 seed rounds in "social trading" or "live markets." Smaller or stealth entrants may be missing.
- Trading.TV's actual fate (shutdown, pivot, acqui-hire or domain sale) is unconfirmed.

## 8. AI market explainer products: who auto-generates "why is it moving" or live recaps, and how good are they?

### Takeaway
"Why is it moving" has become a commodity feature. The main products:
- **Robinhood Cortex Digests:** US from summer 2025; free in the UK from Aug 2025; hundreds of thousands of users.
- **Google Finance's AI rebuild:** US from Aug 2025; live earnings with AI summaries from Oct 30, 2025; 100+ countries in 2026.
- **Perplexity Finance:** free real-time data; Pro at $20/month.
- **Others:** Public (Alpha in 2023; AI replaced its social feed in 2025), eToro's Tori agent, moomoo AI, Fiscal.ai (350k+ users, coming to Robinhood Agent Apps) and Fey (absorbed by Wealthsimple in 2025).
- **A long tail of small tools:** Sumari, WhyStockMove, Stock Moves Explained, Acuity Market Companion, Ainvest Market Mover, and Wendy's "Market Interpreter" inside Robinhood.

Quality evidence is thin and mostly self-reported. The best public data point on AI summary errors in finance news is Bloomberg: at least 36 corrections in roughly three months of 2025.

### Cited Findings
- **Robinhood Digests:**
  - AI notes on why a stock may be moving, built from news, analyst reports, technicals and Robinhood data.
  - Not available for every stock.
  - 95% of surveyed US users said they like it (self-reported); labeled as not research or advice.
  - Source: [Robinhood newsroom, Aug 19, 2025](https://robinhood.com/us/en/newsroom/digests-by-robinhood-cortex-uk)
  - At HOOD Summit 2026 Robinhood also listed "Market Interpreter by Wendy" ($10/mo) and "ChatterFlow Viral Stocks Detector by Narravance" ($8/mo) as Agent Apps, with Fiscal.ai coming soon — [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/)
- **Public:** says AI now writes the recaps users used to post, faster and more accurately (company claim) — [Finance Magnates, Jun 2025](https://www.financemagnates.com/forex/publiccom-terminates-social-trading/). Alpha (GPT-4) launched in May 2023 — [Contrary Research](https://research.contrary.com/company/public)
- **Google Finance** (secondary coverage):
  - First tested with US Search Labs users; features rolled out gradually from August 2025.
  - **Live earnings (Oct 30, 2025):** live audio, synced transcripts, and an AI "At a glance" section updated before, during and after calls, with a playback timeline.
  - **Nov 2025:** Deep Search and prediction-market data.
  - A revamped real-time news feed, and explanations of major price moves on specific days.
  - Expanding to 100+ countries; the European launch is dated variously April 8 or May 2026.
  - Sources: [PPC Land](https://ppc.land/google-finance-ai-tools-reach-100-countries-with-local-language-support/); [Neowin](https://www.neowin.net/news/google-finance-expands-in-europe-with-ai-research-and-live-earnings-insights); [Finextra: "Google Finance gets AI reboot"](https://www.finextra.com/newsarticle/46424/google-finance-gets-ai-reboot)
- **Perplexity Finance:**
  - An informal hands-on review (Aug 13, 2025) found it fast, cleanly laid out and well-sourced. Weaknesses: brief summaries, static charts with no indicators, uneven non-US coverage, and no alerts.
  - Data comes from Financial Modeling Prep, and answers are written by GPT-4 or Claude.
  - The free tier includes real-time data; Pro is $20/month.
  - "Why it moved" required follow-up questions rather than being a built-in feature.
  - Source: [Techpoint Africa](https://techpoint.africa/guide/perplexity-finance-review/)
  - A Greek-language source says its heatmaps explain moves on hover and that it launched publicly in August 2025 (unverified) — [SecNews.gr](https://www.secnews.gr/?p=725424)
  - A competitor's benchmark scored Perplexity 45% on FinanceBench's top-100 questions versus 98% for its own product (conflict of interest) — [Fintool](https://fintool.com/benchmark/perplexity-versus-fintool)
  - A forum user reported a misleading answer based on a months-old, undated article — [Motley Fool discussion](https://discussion.fool.com/t/perplexity-et-al/121657)
- **Fey:** Wealthsimple acquired the Montreal AI research app on August 27, 2025, for its earnings analysis, plain-language screening and personalized news feed. Fey's standalone service ended September 30 with subscription refunds, and its founders joined Wealthsimple — [Wealthsimple newsroom](https://newsroom.wealthsimple.com/wealthsimple-acquires-investment-research-platform-fey); [BetaKit](https://betakit.com/wealthsimple-acquires-fey-to-bolster-its-investment-research-capabilities/)
- **Fiscal.ai (formerly FinChat):**
  - Rebranded in June 2025 alongside a $10M Series A led by Portage, with Social Leverage — [TinySeed](https://tinyseed.com/latest/fiscal-ai-10m-future-ai-finance); [Oziel Law](https://oziellaw.ca/stratosphere-technology-inc-closes-10m-usd-series-a-financing/)
  - Earlier: a $1.5M round from Social Leverage in Nov 2023 — [BetaKit](https://betakit.com/finchat-secures-1-5-million-usd-from-social-leverage-to-expand-ai-powered-stock-research-platform)
  - More than 350k registered users (company-reported), with a consumer terminal and a B2B API — [DayTradingToolkit](https://daytradingtoolkit.com/reviews/finchat-review)
  - Pro costs $39/month — [Yespress](https://yespress.io/products/finchat.md)
- **eToro and moomoo:**
  - eToro's Tori agent gives proactive portfolio insights — [eToro Q2 2026](https://www.etoro.com/news-and-analysis/press-releases/etoro-reports-second-quarter-2026-results/)
  - moomoo expanded AI across options, IPOs, bonds and ETFs, plus AI Algo Trading from plain-language instructions — [Futu FY2025](https://digital-release.wboy.com/business/press-releases/cision/20260312CN08754/moomoos-parent-company-futu-achieves-consecutive-growth-in-q4-and-full-year-2025)
- **Long tail of small tools:**
  - "Stock Moves Explained," a connector for AI assistants that adds a confidence score and flags "mystery moves" with no clear cause — [G2](https://ai.g2.com/marketplace/tools/stock-moves-explained)
  - Acuity's "Market Companion," sold to brokers — [Acuity Trading](https://acuitytrading.com/market-companion)
  - Sumari, one-sentence explanations with sentiment and sources — [PeerPush](https://peerpush.com/p/sumari)
  - WhyStockMove, combining news, filings, insider and congressional data — [TrustMRR](https://trustmrr.com/startup/whystockmove)
  - Ainvest's "Market Mover" — [App Store](https://apps.apple.com/us/app/-/id6472856176)
- **Accuracy warning from news AI:**
  - Bloomberg began AI bullet summaries in January 2025 and had corrected at least three dozen by late March. Errors included wrongly saying Trump had already imposed tariffs on Canadian goods and confusing active and passive funds.
  - Bloomberg said about 99% of summaries met its standards.
  - Critics also faulted the summaries' size and prominence.
  - Sources: [TalkingBizNews](https://talkingbiznews.com/media-news/bloomberg-has-a-rocky-start-with-ai-summaries/); [Spyglass](https://spyglass.org/ai-news-summaries/)

### Inferences
- An explainer cannot be the wedge: Robinhood, Google, Perplexity, Public, eToro and moomoo all ship one free or bundled, and dozens of small tools copy the pattern.
- Room left for differentiation:
  - Speed (seconds after a move, not minutes).
  - Timestamped cause and effect (the news landed at 10:31:05 and price moved at 10:31:09).
  - Honest uncertainty ("no clear catalyst" or "mystery move" labels).
  - Pairing the AI note with live human reaction and verified positions.
- At play-by-play speed, attribution errors will be frequent and visible. The Bloomberg record shows even a top newsroom drew dozens of corrections in a quarter. Confidence labels, source links and quick correction tools are product requirements, not nice-to-haves.

### Gaps
- No independent, systematic accuracy or latency benchmark comparing Robinhood Digests, Google Finance and Perplexity "why it moved" explanations. A small test against news timestamps would be needed.
- Yahoo Finance's AI features, and Webull's AI features, were not researched.

## 9. The graveyard (2008–2026): which social investing products shut down, pivoted, or were absorbed, with stated reasons, and the lessons (cold start, moderation, regulation, monetization, trust)

### Takeaway
The recurring pattern: social investing works as a feature attached to a transaction (eToro, Robinhood) or as a niche network with modest revenue (Blossom). Standalone social products usually end in one of three ways:
- Absorbed by a distribution owner on undisclosed terms (Commonstock to Yahoo, Fey to Wealthsimple).
- Pivoted away from the "social" premise (kaChing to Wealthfront).
- Shut down or retreated (Motif, Openfolio, Shares in the UK, Public's social feed, and apparently Trading.TV's brand).

Stated reasons cluster around five themes:
- **Failure to turn engagement into revenue:** kaChing's tiny conversion; Public's social never earning money.
- **Capital intensity of becoming a broker:** Blossom.
- **Customer-acquisition struggles:** Motif.
- **Loss-making geographic expansion:** Shares in the UK.
- **AI making user-written market content redundant:** Public.

### Cited Findings

| Company | Model | Years | Outcome | Stated or reported reason | Source |
|---|---|---|---|---|---|
| kaChing → Wealthfront | Virtual portfolios plus following or copying hand-picked amateur "expert" managers | Late 2000s to early 2010s (exact dates not verified) | Rebranded as Wealthfront; dropped amateurs for professional managers (minimum raised from $3k to $10k), then pivoted again to automated indexing | Secondary accounts say very few users converted (one account says only 5) and VC money arrived faster than assets | [Appcues](https://www.appcues.com/blog/wealthfront-growth-story); [PMF Chronicles](https://pmfchronicles.substack.com/p/wealthfront); [Technologizer](https://technologizer.com/tag/kaching); [Stanford GSB case](https://www.gsb.stanford.edu/faculty-research/case-studies/wealthfront) |
| Openfolio | Portfolio sharing and aggregated returns of linked accounts | Founded 2013 | Ceased operations; about $1.8M raised | No stated reason found | [CB Insights](https://www.cbinsights.com/company/openfolio-corporation); [Financial Planning](https://www.financial-planning.com/news/reinvent_wealth/portfolio-sharing-platforms-online-investings-growing-opportunity-2692807-1.html) |
| Motif Investing | Social and thematic brokerage | ~2010–2020 | Shut in 2020 after about 10 years; accounts moved to Folio, team and technology to Schwab; the portfolio-sharing feature did not carry over; $127M raised | Motif and peers struggled to attract customers (ImpactAlpha) | [FA-Mag](https://www.fa-mag.com/news/motif-investing-announces-plans-to-shut-down-in-may-55367.html?print); [ImpactAlpha](https://impactalpha.com/responsible-robo-advisor-motif-shuts-down-with-folio-and-charles-schawb-divvying-up-the-business/); [Finovate](https://finovate.com/category/motif-investing/) |
| Swell / OpenInvest (adjacent: impact investing) | Retail impact robo-advisors | ~2019 | Swell shut; OpenInvest pivoted to serving advisers | Context only | [ImpactAlpha](https://impactalpha.com/responsible-robo-advisor-motif-shuts-down-with-folio-and-charles-schawb-divvying-up-the-business/) |
| Trading.TV | Livestreams plus chat plus trading from streams ("Robinhood-Twitch") | 2021–? | About $14.1M raised (seed plus Series A, computed); domain now redirects to a wealth manager | Not found | [Axios](https://www.axios.com/2022/02/16/tradingtv-series-a-funding); [Benzinga](https://benzinga.com/fintech/22/02/25680090/trading-tv-secures-8m-in-round-led-by-lightspeed-venture-partners); [trading.tv redirect](https://trading.tv) |
| Commonstock | Broker-agnostic verified social network | 2020–2023 | Acquired by Yahoo (undisclosed terms); staff and product folded into Yahoo Finance; domain redirects to Yahoo's community page | Acquisition, not failure; Yahoo wanted engagement and subscriptions | [Axios](https://www.axios.com/2023/08/23/commonstock-yahoo-social-investing-platform); [commonstock.com](https://commonstock.com) |
| Blossom (pivot) | Planned "Canada's first social brokerage," became a pure social network | 2021–2023 pivot | Survived and grew: 750k+ members, more than $6.5M annualized revenue (Q2 2026) | Called the brokerage plan the wrong strategy; brokerages are extremely capital-intensive; competition and complexity | [BetaKit 2024](https://betakit.com/blossom-closes-2-1-million-to-grow-its-investing-social-network-in-the-us/); [BetaKit 2026](https://betakit.com/blossom-social-raises-more-than-2-million-through-frontfundr-campaign) |
| Shares (France) | App for investing together with friends and sharing trades | 2021– | Closed its loss-making UK business on Aug 30, 2024 to focus on France and the EU; £30M Series A in 2022, about $90M raised in total | Focus on French and EU markets | [BusinessCloud](https://businesscloud.co.uk/news/social-investing-app-shares-shutters-uk-business/); [Tracxn](https://tracxn.com/d/companies/shares/__1Sy5Gi2ATFcc1c9YSEDpVsIdfqRmfLv09bIUTmXsZ1w) |
| Public.com social | Broker with a social feed, live shows and Town Halls | 2019–2025 | Social shut down June 2025 ("Sunsetting Social") | AI now makes the recap content; customers more experienced; refocus on multi-asset trading and AI | [Finance Magnates](https://www.financemagnates.com/forex/publiccom-terminates-social-trading/); [FX News Group](https://fxnewsgroup.com/forex-news/retail-forex/public-shuts-down-social-trading/) |
| Fey | Standalone AI stock research app with news feed | –2025 | Acquired by Wealthsimple; standalone service ended Sep 30, 2025 | Acquisition | [Wealthsimple](https://newsroom.wealthsimple.com/wealthsimple-acquires-investment-research-platform-fey) |
| Robinhood confetti | Gamified celebration animation | –2021 | Removed | Regulatory scrutiny of gamification | [NBC Boston/CNBC](https://www.nbcboston.com/news/business/money-report/robinhood-gets-rid-of-confetti-feature-amid-scrutiny-over-gamification-of-investing/2343214/?amp=1) |

**Cross-cutting evidence by theme**

**Cold start**
- Robinhood seeded Social with its most active traders, 1,000 then 10,000 more, before GA — [Robinhood newsroom, Mar 18, 2026](https://robinhood.com/us/en/newsroom/robinhood-social-beta)
- Blossom used influencer ambassadors and user crowdfunding — [BetaKit 2024](https://betakit.com/blossom-closes-2-1-million-to-grow-its-investing-social-network-in-the-us/)
- Autopilot grew out of the viral Pelosi Tracker account — [Techleap](https://finder.techleap.nl/news/feed/autopilot-raises-8m-expands-operations)
- AfterHour launched on its founder's WallStreetBets fame — [Fortune](https://fortune.com/2024/06/17/exclusive-after-hour-social-trading-startup-raises-4-5-million-seed-round-led-by-founders-fund-and-general-catalyst)
- Robinhood licenses TipRanks data for public figures' trades, and Quiver sells government-trade tracking as a $10/mo Agent App. Public-figure content is cheap to license as a seed — [Robinhood newsroom, Sep 29, 2026](https://robinhood.com/newsroom/hood-summit-2026/)

**Moderation**
- Webull monitors its community daily and checks flagged posters' trading for manipulation — [Webull AU](https://www.webull.com.au/learn/courseware/vYm9Bg)
- Yahoo bans non-financial or non-substantive posts and weights votes by followers' real money — [Yahoo guidelines](https://legal.yahoo.com/us/en/yahoo/finance-guidelines/index.html); [Yahoo Help](https://help.yahoo.com/kb/SLN37021.html)
- Robinhood was still refining its moderation policies at beta — [Robinhood newsroom](https://robinhood.com/us/en/newsroom/robinhood-social-beta)
- eToro's F-1 flags misleading or manipulative user posts as a risk — [eToro F-1](https://www.sec.gov/Archives/edgar/data/1493318/000101376225001589/ea0223534-08.htm)

**Regulation**
- Robinhood allows only manual copying because of investment-advice concerns — [Fortune](https://fortune.com/2026/03/18/robinhood-rolls-out-long-awaited-social-feature-to-let-users-track-and-copy-other-traders/)
- Automatic copying in the US runs through registered advisers: dub Advisors — [Pulse 2.0](https://pulse2.com/dub-30-million-series-a-closed-for-scaling-copy-trading-platform); Autopilot as an RIA — [Altss](https://altss.com/profile/autopilot); eToro USA Advisors — [eToro Q2 2026](https://www.etoro.com/news-and-analysis/press-releases/etoro-reports-second-quarter-2026-results/)
- Copy trading is common in Europe but heavily restricted in the US — [TechCrunch](https://techcrunch.com/?p=3044707)

**Monetization**
- Blossom: two-thirds brand partnerships, one-third subscriptions — [BetaKit 2024](https://betakit.com/blossom-closes-2-1-million-to-grow-its-investing-social-network-in-the-us/)
- AfterHour: paid coins and raffles — [App Store](https://apps.apple.com/us/app/afterhour-social-copy-trading/id1640766056)
- Dub: $10/month — [TechCrunch](https://techcrunch.com/?p=3044707)
- Autopilot: 80k paid subscribers — [TradersPost](https://blog.traderspost.io/article/chris-josephs-copy-trading-at-benzinga-2025)
- Public: none of its revenue came from social — [Contrary](https://research.contrary.com/company/public)
- eToro and Robinhood earn through trading and offer social free — [Robinhood newsroom, Sep 10, 2025](https://robinhood.com/newsroom/hood-summit-2025-news/); [eToro F-1](https://www.sec.gov/Archives/edgar/data/1493318/000101376225001589/ea0223534-08.htm)

**Trust**
- Doctored trade screenshots circulate on Reddit and X — [Fortune](https://fortune.com/2026/03/18/robinhood-rolls-out-long-awaited-social-feature-to-let-users-track-and-copy-other-traders/)
- AfterHour pitches verified trades as the end of fake screenshots — [afterhour.com](https://www.afterhour.com/)
- KYC does not stop AI-driven identity fraud — [Simply Wall St/Yahoo](https://finance.yahoo.com/markets/stocks/articles/robinhood-social-launch-tests-trust-090524835.html)

### Inferences
- **What worked:**
  - Verified identity plus real positions (now standard).
  - Tying social activity to money flow: copying, a trade button, or a broker referral.
  - Public-figure and celebrity content as a cold-start engine.
  - Community ownership or influencer distribution (Blossom).
  - Owning the ledger, so verification and monetization come built in (Robinhood, eToro).
- **What failed:**
  - Trying to become a broker as a startup (capital).
  - Live-stream-first media products (Trading.TV).
  - Generic recap and opinion feeds that AI now replaces (Public).
  - Expanding abroad before product-market fit (Shares).
  - Marketplaces of amateur managers with tiny paid conversion (kaChing).
- **Exits have been small or undisclosed tuck-ins** (Commonstock, Fey). Investors and acquirers have valued these products as features for existing distribution, not standalone platforms.
- **For "Real for markets," a defensible wedge has to sit where incumbents structurally can't or won't go:**
  - **Cross-broker neutrality:** Robinhood Social only covers Robinhood customers.
  - **Off-broker communities:** for example, verifying and scoring paid Discord options-alert groups against market data, a trust problem none of the products above addresses.
  - **Real-time, event-centric co-watching:** earnings, CPI, FOMC, big intraday moves, with speed and personality a regulated broker won't match.
  - **Plus guardrails:** strong moderation and clear lines on advice and manipulation from day one, given the gamification and finfluencer scrutiny documented above.

### Gaps
- Could not verify outcomes or stated reasons for several names often cited in social-investing history: Iris, Kinfo, ayondo, NAGA, Atom Finance, Stockpile, Tip'd, Covestor and ZuluTrade. The web-search budget ran out before targeted searches.
- No first-person founder post-mortems were found for Openfolio, Motif, Trading.TV or Commonstock. The reasons above come from press coverage or are absent.
- Deal values for Commonstock→Yahoo and Fey→Wealthsimple were not disclosed.
