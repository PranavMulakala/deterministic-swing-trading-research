# Real (Real Vault, Inc.): company, growth, go-to-market, business model and technology (state as of Oct 18, 2026)

Compiled Oct 18, 2026. Almost every usage metric below is self-reported by the company or its founders (LinkedIn posts, interviews, job posts). None is audited, and I found no third-party app-intelligence estimates (Sensor Tower, Appfigures, data.ai) for Real. Quotes are paraphrased unless marked. The infrastructure observations in section 7 come from my own lookups of public DNS records and Real's public web-app bundle on Oct 18, 2026, and they could change.

## 1. Identity: which "Real", the legal company, the website, and how it was confirmed

### Takeaway
- **App:** "Real - Sports", subtitle "Social sports data". Bundle/package ID is vg.real.
- **Company:** Real Vault, Inc., doing business as "Real". Its privacy policy, last updated in 2020, still names Real Vault, LLC. It is based in Chicago.
- **Website:** realapp.com. The older domain realapp.link redirects there; real.vg is still used for the API and the support email.
- **How I confirmed it:** the App Store and Google Play developer listings, the company's own terms of use, and press coverage that describes per-play comment threads and emoji reactions on live NBA play-by-play.

### Cited Findings
- **App Store listing (viewed Oct 18, 2026)** — [App Store](https://apps.apple.com/us/app/real-sports/id1514546162)
  - Name "Real - Sports", subtitle "Social sports data". Seller is Real Vault, Inc. Developer website is realapp.link. The copyright line reads 2021 Real Vault, LLC.
  - Category Sports; free with in-app purchases; rated 18+, with "Simulated Gambling" listed as frequent content.
  - 4.8 stars from about 26K ratings. Ranked #24 in Sports (Top Free).
  - Runs on iPhone (iOS 16+), Apple-silicon Macs, and visionOS.
- **Other apps from the same developer:** the Apple developer page for Real Vault, Inc. lists only one other app, "The Rose League", a fantasy game for The Bachelor — [Apple developer page](https://apps.apple.com/us/developer/real-vault-inc/id1135666985)
- **Google Play listing (viewed Oct 18, 2026)** — [Google Play](https://play.google.com/store/apps/details?id=vg.real&hl=en_US)
  - Developer "Real Vault", package vg.real. 500K+ downloads; 4.3 stars from about 4.55K reviews.
  - Content rating Everyone, marked "Users Interact". Last updated Oct 16, 2026.
  - Support email is support@real.vg; the privacy policy is hosted on docs.realapp.link.
  - A search-engine summary claimed a 4.9-star Play rating; the live page shows 4.3.
- **Terms of use (last updated Oct 1, 2023)** — [Real Terms of Use](https://docs.realapp.link/policies/terms-of-use)
  - The agreement is with Real Vault, Inc., doing business as "Real". It covers realapp.link, real.vg and the iOS and Android apps.
  - Arbitration and court venue are in Cook County, Illinois.
- **Privacy policy (last updated Dec 20, 2020):** names Real Vault, LLC, doing business as "Real" — [Real Privacy Policy](https://docs.realapp.link/policies/privacy-policy)
- **Website behavior:** realapp.link 301-redirects to realapp.com. The homepage title is "Real Sports App", and the web app loads its code from realsports.io (my fetch, Oct 18, 2026) — [realapp.com](https://www.realapp.com/)
- **LinkedIn company page "Real App" (URL slug real-vault)** — [LinkedIn company page](https://www.linkedin.com/company/real-vault)
  - Headquarters Chicago; founded 2020; size listed as 2–10 employees.
  - Claims 18 leagues, 1M+ daily active members and 50M+ live in-game notifications per day.
- **Press that matches the product description:**
  - The app grabs data feeds and turns them into a feed of plays; each play has its own comment thread, and fans react with emojis — [BetCrunch, Apr 25, 2023](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
  - Front Office Sports calls it a social box-score app that combines live stats and play-by-play with social and gaming features — [Front Office Sports, Apr 13, 2026](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- **Name collisions:** unrelated companies named RealPlay Sports and RealSport also exist. Crunchbase calls the matching company "Real Sports App" — [Crunchbase: Real Sports App](https://www.crunchbase.com/organization/real-sports-app); [Crunchbase: RealPlay](https://www.crunchbase.com/organization/realplay); [Crunchbase: RealSport](https://www.crunchbase.com/organization/realsport)

### Inferences
- The entity moved from an LLC (privacy policy, 2020) to "Inc." (terms, 2023). That is consistent with converting to a C-corp before taking venture money, but the timing is undisclosed.
- The brand stack is Real (product), Real Vault (legal entity) and realapp.com (website). The founders reused one developer account for an earlier app and the current one.

### Gaps
- I could not locate an incorporation filing showing the date or state for Real Vault, Inc.

## 2. Founders, backgrounds, and pivots or earlier products

### Takeaway
- **The founders:**
  - Louis Antonelli is the older brother and leads engineering. He has a Cornell CS degree, was the first engineer at Guilded (a Discord competitor that Roblox acquired in 2021), and is 34.
  - John Antonelli is 24 and leads growth. He has a Duke CS degree (class of 2023), grew a Vine sports-edit account, and built the @bball Instagram account to roughly 0.9–1M followers.
  - A middle brother, Jimmy, did part-time design early on. Their mother runs finance.
- **Origin:** the idea came on Feb 19, 2020. A private beta followed in January 2021 and the public launch in March 2021.
- **Precursor:** The Rose League, a Bachelor fantasy app that Louis built with his now-wife. They typed in events by hand. Real is the same "live feed plus social" concept, fed automatically by sports data.

### Cited Findings
- **The idea:** On Feb 19, 2020, during John's freshman year, Louis texted him the idea of a real-time app for discussing and reacting to NBA play-by-play — [Duke Mag (by John Antonelli), Apr 30, 2025](https://dukemag.duke.edu/stories/entrepreneurial-vision)
  - FanDuel's write-up says the text came around 4 a.m. Its example was reacting to a Fred VanVleet three with a Drake emoji — [FanDuel, Sep 10, 2026](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
  - Real's own docs describe the same Drake-emoji origin — [Real docs: Overview](https://docs.realapp.link/about/overview)
- **Launch timeline:**
  - Private beta Jan 10, 2021 (photo caption) and launch in March 2021 (article text) — [GrepBeat, Aug 18, 2022](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
  - The changelog's first entry is dated Jan 26, 2021. The Android app went public on Mar 19, 2021 — [Real changelog](https://docs.realapp.link/updates/changelog)
  - Front Office Sports says beta in 2020 and official launch in 2021 — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- **Louis Antonelli:**
  - Age 34. Founding engineer at Guilded, which Roblox acquired — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - Cornell computer science graduate; first engineer at Guilded — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
  - Real's job page calls him a full-stack engineer with 9+ years of experience — [Real job post](https://docs.realapp.link/jobs/full-stack-engineer-real)
  - His LinkedIn shows Real Vault, Cornell and the Greater Chicago Area. On Aug 16, 2021 he posted congratulations to the Guilded team on its acquisition — [Louis Antonelli LinkedIn](https://www.linkedin.com/in/louis-antonelli/)
  - A contact-data site lists him as CEO. This is unverified — [Datanyze](https://www.datanyze.com/companies/real-sports/556249218)
- **Guilded:** a chat and community platform for gamers and esports, competing with Discord. Roblox bought it on Aug 16, 2021 for $90M and shut it down on Dec 19, 2025 — [Wikipedia: Guilded](https://en.wikipedia.org/wiki/Guilded)
- **John Antonelli, audience background:**
  - Age 24 (April 2026). Grew social audiences for more than a decade, including a large Vine account and @bball on Instagram — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - Duke class of 2023, CS. Started Vine in 2014 and reached 75K followers in nine months. Grew @bball to 900K+ between 2015 and 2019, while in high school — [Duke Mag](https://dukemag.duke.edu/stories/entrepreneurial-vision)
  - On TBPN he said his Vine page passed roughly 100K in six months. It was built on faceless highlight edits set to songs, including a viral Odell Beckham Jr. catch — [TBPN transcript, Sep 23, 2026](https://share.transistor.fm/s/e6c9bcc4/transcription)
- **John's @bball follower count, as reported over time:**
  - 875K+ in 2022 — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
  - Nearly 1M — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - 1M+ — [FanDuel](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
- **John's location:** LinkedIn says Chicago — [John Antonelli LinkedIn](https://www.linkedin.com/in/johnmantonelli/). A Crunchbase snippet places him in New York, which conflicts — [Crunchbase](https://www.crunchbase.com/organization/real-sports-app)
- **Jimmy Antonelli:** the middle brother joined part-time to lead design — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/). In May 2022 John described the company as bootstrapped by three brothers — [John LinkedIn, May 20, 2022](https://www.linkedin.com/posts/johnmantonelli_startup-sports-tech-activity-6933466447604064256-4fSG)
- **Team in April 2026:** five people. John runs growth, Louis leads engineering with two engineers (Sam and Chris), and their mother leads finance. Jimmy is not mentioned — [John LinkedIn, Apr 13, 2026](https://www.linkedin.com/posts/johnmantonelli_in-february-2020-i-woke-up-to-a-text-from-activity-7449584221846773760-J85X); [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- **New hire:** Evan Abramson officially joined on Jun 22, 2026 to lead Partnerships & Growth. He had advised the company before that — [John LinkedIn, Jun 22, 2026](https://www.linkedin.com/posts/johnmantonelli_excited-to-have-evan-abramson-officially-activity-7474924230468366336-IfWO)
- **Earlier product, The Rose League:**
  - Louis co-founded it with his now-wife. It tracked stats from The Bachelor and peaked at about 50,000 users — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - On TBPN, Louis said the two of them entered every event by hand during live broadcasts for about four years, reaching about 50K weekly users. Real is that live-feed concept without manual data entry — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
- **Pivots inside Real (all dated in the changelog):**
  - Virtual currency Rax launched May 3, 2022.
  - Serial-numbered team, sport and player "passes" launched Aug–Oct 2022.
  - The Real Pro subscription and a play-card collectibles beta launched Apr 14, 2023.
  - A full card economy followed, with packs, boosters and a marketplace and auctions in 2023–2025.
  - Rax-denominated prediction markets launched in beta on Dec 20, 2025.
  - [Real changelog](https://docs.realapp.link/updates/changelog)
  - The FanDuel odds partnership followed in September 2026 — [FanDuel](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)

### Inferences
- The founding pair combines owned distribution (John's network of fan and meme pages) with experience building real-time chat (Louis at Guilded). Both matter more to this story than capital did.
- The Rose League shows the "live event feed plus social reactions" format worked with hand-entered data before Real existed. Real automated the feed.
- **Lesson for Real for markets:** a founder with an existing creator or audience network in the target niche is the closest analog to John's role. For markets, that means traders who run FinTwit accounts, Discord alert groups, or YouTube and TikTok channels.

### Gaps
- Louis's formal title (CEO or CTO) is not confirmed by a primary source.
- Jimmy's current role is unknown.
- I don't know whether The Rose League is still operating.

## 3. Funding: rounds, amounts, dates, investors, valuation

### Takeaway
- **Bootstrapped first:** Real ran on the founders' savings through at least August 2022.
- **Pear VC:** invested at an undisclosed date. Pear's site tags the company "Series A".
- **Chernin Group round:** announced Apr 13, 2026 and led by The Chernin Group (TCG).
  - Amount and valuation were not disclosed. TCG took a minority stake and the founders kept control.
  - NBA players and creators joined as angels.
- **Totals:** one aggregator lists $12.1M raised in total, which I could not verify. No valuation has been reported.

### Cited Findings
- **Bootstrapping:**
  - As of August 2022 the founders had funded Real entirely from personal career savings, had taken no outside money, and believed they were close to sustainability — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
  - In May 2022 John called Real entirely bootstrapped by three brothers — [John LinkedIn, May 20, 2022](https://www.linkedin.com/posts/johnmantonelli_startup-sports-tech-activity-6933466447604064256-4fSG)
- **Chernin round (Front Office Sports exclusive, Apr 13, 2026)** — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/); [FOS post on X, Apr 13, 2026](https://x.com/FOS/status/2043754258441375811)
  - TCG led. Both sides declined to give the amount or valuation, saying only that it was a minority stake and the founders retain control.
  - Other venture investors: Pear Ventures, Tamarisk Lane and Operator Partners.
  - NBA players: Tyrese Haliburton, Grayson Allen and Tre Jones.
  - Creators: Clix (Cody Conrod) and Kenny Beecham.
  - Executives: former ESPN EVP Connor Schell and CAA Sports co-head Mike Levine.
  - Stated use of proceeds: add sports, including tennis and F1.
- **John's announcement post** — [John LinkedIn, Apr 13, 2026](https://www.linkedin.com/posts/johnmantonelli_in-february-2020-i-woke-up-to-a-text-from-activity-7449584221846773760-J85X)
  - Describes TCG as a strategic investor, chosen after about a year of getting to know each other.
  - Funds are going into tennis, F1 and global soccer, and deeper coverage of existing leagues.
  - The athlete and creator investors were early users who share the app with their audiences.
- **Why TCG, per the founders:** the money let them avoid taking quick sponsorship deals from sportsbooks or prediction markets. TCG's Mike Kerns called Real the fastest-growing sports app he had seen and said it grew with almost no paid marketing — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- **TCG's track record, as summarized by Front Office Sports** — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - Took a majority stake in Barstool in 2016 at a $15M valuation; Penn later bought the company for $551M.
  - Incubated The Action Network, which sold to Better Collective for $240M.
  - Led The Athletic's seed round; the New York Times later bought it.
  - Holds a controlling stake in MeatEater.
  - Its Food52 investment did not work out.
- **Pear VC:** its portfolio lists "Real Sports" under Consumer, tagged "Series A", and links to realapp.link. No investment date is shown — [Pear VC companies](https://pear.vc/companies/)
- **Aggregators, which disagree:**
  - VCBacked: $12.1M total, with the last funding dated Apr 13, 2026. Investors Pear VC and TCG; round type "Venture – Series Unknown"; headquarters Chicago. It does not name its underlying source — [VCBacked](https://www.vcbacked.co/company/real-sports-app)
  - Crunchbase lists two investors (TCG and Pear VC) and hides the amount (search snippet only) — [Crunchbase](https://www.crunchbase.com/organization/real-sports-app)
  - Tracxn says Real has raised no funding, which looks outdated — [Tracxn](https://tracxn.com/d/companies/real-sports/__kpeImbrfmUcwwIHURGlmNm4KWOuVFyUqGnY0pu4DW84)

### Inferences
- Pear's "Series A" tag and VCBacked's $12.1M dated to the announcement day suggest the TCG-led round may be a Series A of about $12M. That is unconfirmed, because Front Office Sports says the amount was undisclosed.
- Real hit roughly 400K MAU (March 2024) and about 1M MAU (2025) before any institutional lead round was made public. The money came after strong engagement, not before.
- **Lesson for Real for markets:**
  - Bootstrapping to real engagement is feasible with a 2–3 person team.
  - Strategic angels (athletes and creators) doubled as distribution.
  - A media-savvy strategic investor delayed dependence on betting sponsorships.

### Gaps
- Pear's check size and date.
- Any pre-seed or SAFE rounds.
- Valuation.
- Revenue, burn and runway. None of these is disclosed.

## 4. Growth: users, engagement, rankings, viral moments (2021 → Oct 2026)

### Takeaway
- **Scale:** Real grew from about 1,000 MAU at its NBA-only launch in March 2021 to about 1.3–1.5M MAU and 0.7–1.1M DAU in 2026, with no meaningful paid marketing.
- **Stickiness is the standout:**
  - WAU/MAU ran 74–79% in 2022–2024.
  - Founders imply DAU/MAU of about 70% at peak.
  - About 30% of MAU comment.
- **Spikes:** usage jumps on huge single moments. Bam Adebayo's 83-point game on Mar 10, 2026 drew 220K concurrent users and 919K DAU.
- **Caveat:** all figures are company-reported.

### Cited Findings

| Date | Metric (company-reported unless noted) | Source |
|---|---|---|
| Mar 2021 | About 1,000 MAU at the public App Store and Play Store launch, NBA only | [John LinkedIn, May 2022](https://www.linkedin.com/posts/johnmantonelli_startup-sports-tech-activity-6933466447604064256-4fSG); also 1,000 unique users engaging with an NBA game in 2021, per [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/) |
| May 20, 2022 | 108K+ MAU and 80K+ WAU (WAU/MAU about 74%); 20M+ minutes spent in the prior 30 days; 4 leagues (NBA, NFL, NHL, NCAA men's basketball) | [John LinkedIn, May 2022](https://www.linkedin.com/posts/johnmantonelli_startup-sports-tech-activity-6933466447604064256-4fSG) |
| Aug 2022 | 115K+ monthly active members near the end of the 2022 NBA Finals; about 6 minutes per day on average; 4,000+ five-star reviews | [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/) |
| Apr 2023 | About 170K MAU; 3M+ comments in the prior 30 days | [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on) |
| 2023 | 250K+ monthly active members. Unverified: from a search snippet of Duke I&E news; the page did not load | [Duke I&E news](https://entrepreneurship.duke.edu/duke-ie-network/duke-ie-network-news/) |
| Mar 18, 2024 | 400K+ MAU and 315K+ WAU (about 79%), growing 2.5x year over year; 7 main US leagues. From a hiring post Louis reposted | [Louis Antonelli LinkedIn](https://www.linkedin.com/in/louis-antonelli/) |
| Undated (my estimate: mid-2024 to mid-2025, because it still cites 7 leagues) | 950,000+ MAU; 7 main US leagues; goal of reaching millions of MAU within 12 months | [Real job post: Full-Stack Engineer](https://docs.realapp.link/jobs/full-stack-engineer-real) |
| Feb 2025 (Super Bowl LIX) | Peak of 411,000 "live viewers" | [Duke Mag](https://dukemag.duke.edu/stories/entrepreneurial-vision) |
| 2025 (recap posted Jan 2, 2026) | Reached 1M monthly and 1M weekly active users. 2025 NBA Finals Game 7 was the first game with 500K+ unique live viewers. Kevin Durant, Cooper Flagg, Haliburton and hundreds of other pros are active. Billions of impressions from Real screenshots on X, Instagram and TikTok | [John LinkedIn, Jan 2, 2026](https://www.linkedin.com/posts/johnmantonelli_what-a-year-for-real-sports-reached-1m-activity-7412933140261810176-uNxt) |
| Mar 10–11, 2026 (Bam Adebayo's 83-point game) | Peak 220K concurrent in-app users; 919K DAU, described as bigger than any Super Bowl, NBA Finals or World Series; 510.7K+ unique users viewed the game live; Bam's performance drew 103K+ comments and about 3M impressions | [John LinkedIn, Mar 11, 2026](https://www.linkedin.com/posts/johnmantonelli_real-sports-peaked-at-220000-concurrent-activity-7437648059917979648-EjgH); game facts (83 points vs. Washington, Mar 10, 2026, second-most in NBA history) from [ESPN](https://www.espn.com/nba/story/_/id/48168945) and [Wikipedia](https://en.wikipedia.org/wiki/Bam_Adebayo%27s_83-point_game) |
| Apr 13, 2026 | 700K–900K DAU; 1.3M MAU; 50M push notifications per day; about 220K peak concurrent (Bam game); almost no paid marketing | [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/) |
| 2026, undated | 1.3M+ MAU and 900K+ DAU; more than 1M people use it weekly. From a job post | [Real job post: Product Designer](https://docs.realapp.link/jobs/product-designer) |
| Jun 1, 2026 | First time reaching 1M DAU, during Game 7 of the Western Conference Finals; next target 2M | [John LinkedIn, Jun 1, 2026](https://www.linkedin.com/posts/johnmantonelli_1-million-daily-actives-on-real-sports-activity-7467239030129266688-Vbha) |
| About Sep 2026 | NFL season opener drew 505.9K+ live viewers. From a company LinkedIn post about a month before Oct 18 | [LinkedIn company page](https://www.linkedin.com/company/real-vault) |
| Sep 10, 2026 | More than 1M DAU on the biggest days; about 75% of users who commented on player performances left at least one comment clearly tied to betting | [FanDuel](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel) |
| Sep 23, 2026 | Host put MAU at about 1.5M and the founders did not dispute it. Daily actives peaked at about 1.1M. The machine transcript garbles the ratio's name, but context implies DAU/MAU of about 70% at peak. 30% of monthly users leave comments. About 50M notifications per day on average. About 200K concurrent during the Bam game | [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription) |
| Oct 18, 2026 | App Store: #24 in Sports (Top Free), 4.8 stars from about 26K ratings. Google Play: 500K+ downloads, 4.3 stars from 4.55K reviews | [App Store](https://apps.apple.com/us/app/real-sports/id1514546162); [Google Play](https://play.google.com/store/apps/details?id=vg.real&hl=en_US) |

- **Seasonality and geography, per the founders on TBPN** — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
  - The World Cup was big for Real. Summer, when only baseball is on, is the natural lull.
  - Big moments such as the Bam game, the NBA Finals and the Super Bowl drive very high concurrency.
  - Australia is a strong market. The founders said it is their third-biggest city by users, and AFL is the most-requested addition.
- **Founders' framing:** the app competes as a daily habit rather than a viewing destination. Many users follow alone at home and want community, or a second screen — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
- **Third-party ranking (unverified):** AppBrain reportedly lists Real's best rank as #28 in Top Grossing Sports in Australia. This comes from a search snippet; the page returned 403 — [AppBrain](https://www.appbrain.com/appstore/real-sports/ios-1514546162)

### Inferences
- **Implied growth rate:** MAU went from about 108K (May 2022) to about 400K (Mar 2024) to about 1.3M (Apr 2026). That is roughly 1.8–2x per year.
- **Platform split:** Google Play shows only 500K+ lifetime downloads against more than 1.3M MAU, so usage likely skews heavily to iOS (and web).
- **The engagement moat:**
  - WAU/MAU near 75–80% and about 30% of users posting are far above typical social apps, where most users only lurk.
  - The TBPN host also said most communities are about 99% lurkers.
- **Concurrency design target:** infrastructure has to absorb a single viral moment (220K concurrent watching one player).
- **Lesson for Real for markets:** the analogous "game nights" are CPI and FOMC releases, after-close mega-cap earnings, and 0DTE expiration afternoons. Plan capacity for event-driven spikes, not average load.

### Gaps
- No Sensor Tower, Appfigures or data.ai estimates of downloads, revenue or retention for Real were found.
  - My web-search budget ran out partway through, so a follow-up could still find some.
  - Sensor Tower-sourced coverage I found was category-level only: sports-app downloads hit a record in Q2 2026 on the World Cup. It does not break out Real (search snippet) — [Mobile Marketing Reads](https://www.mobilemarketingreads.com/sports-news-statistics-live-scores-apps-hit-record-137-million-downloads-in-q2-2026/)
- No D1, D7 or D30 retention cohorts were disclosed.
- "Live viewers" and "unique live viewers" are never defined against "concurrent".
- No 2025–26 app-wide comment totals were found beyond single-game figures.

## 5. Go-to-market and cold start: first users, community density, partnerships, referrals

### Takeaway
- **Start narrow:** Real launched NBA-only and seeded itself through John's friends who run NBA meme and fan pages; its first ~1,000 users came from there.
- **Make the data shareable:** Real turned "data as content" into a format creators screenshot and post. John encourages and sometimes pays creators to show Real's scoreboards.
- **Athletes:** pro players use the app, and some invested.
- **Referral rewards** are paid in virtual currency.
- **Discord** serves as the core community.
- **Expansion:** one league at a time, timed to the start of each season.
- **Paid acquisition:** almost none.

### Cited Findings
- **Cold start through meme and fan pages** — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
  - Real started with only the NBA. Per John, its first thousand users were his friends who run meme and fan pages, such as NBA Centel, NBA Central and Legion Hoops.
  - He encouraged them to work Real into their posts, since they were already posting about big games.
- **Creators:** Real seeds content with creators who talk about games, and encourages or pays them to use Real's scoreboard on screen — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription). John says Real is backed by thousands of sports creators — [John LinkedIn, Apr 13, 2026](https://www.linkedin.com/posts/johnmantonelli_in-february-2020-i-woke-up-to-a-text-from-activity-7449584221846773760-J85X)
- **Codifying fan-page content:** as a page owner, John used to make graphics of a game's top three stats. Real automates that content, which he calls the most shareable score app — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription); [John LinkedIn, Sep 25, 2026](https://www.linkedin.com/posts/johnmantonelli_from-vine-to-real-appreal-app-reals-the-activity-7509319719758229504-qM1s)
  - Fans screenshot early-game stat lines (for example, a player starting 0-for-11) to mock or praise players and drive narratives — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
  - The 2025 recap claims billions of impressions from Real screenshots on X, Instagram and TikTok — [John LinkedIn, Jan 2, 2026](https://www.linkedin.com/posts/johnmantonelli_what-a-year-for-real-sports-reached-1m-activity-7412933140261810176-uNxt)
- **Shareability features in the changelog** — [Real changelog](https://docs.realapp.link/updates/changelog)
  - Charity and fan-page links in player and team popups (Jan 2021).
  - "Replay" to recreate a game's final moments for posting on social (Oct 2021).
  - One-tap share and save of play images (Aug 2024).
  - An MLB home-run bot on X (Oct 2024).
  - An X share button (Aug 2026).
- **Why basketball first:**
  - The idea was literally reacting to NBA play-by-play — [Duke Mag](https://dukemag.duke.edu/stories/entrepreneurial-vision); [FanDuel](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
  - John's existing audience was basketball (@bball) — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - GrepBeat gives no explicit rationale — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
- **Athletes:**
  - Verified player and influencer accounts have been supported since Apr 3, 2021 — [Real changelog](https://docs.realapp.link/updates/changelog)
  - Haliburton, Allen and Tre Jones invested — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - Durant, Cooper Flagg and hundreds of other pros are active — [John LinkedIn, Jan 2, 2026](https://www.linkedin.com/posts/johnmantonelli_what-a-year-for-real-sports-reached-1m-activity-7412933140261810176-uNxt)
  - The founders say players check their own stats on Real at halftime, naming Tre Jones as an example — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
- **Referral program** — [Real changelog](https://docs.realapp.link/updates/changelog); [Real FAQ](https://docs.realapp.link/basics/faqs)
  - Jul 27, 2023: 10 Rax per signup (20 for Pro members).
  - Dec 15, 2023: 400 Rax when a referred user watches a live game (up to 10 referrals, so 4,000 Rax), plus 20% of all Rax the referred user ever buys.
  - Jan 2024: the referral-code field moved to the first step of signup.
  - Anti-abuse rules: referrals fail if the device had Real installed before, and Android referrals aren't supported.
- **Community gamification** — [Real changelog](https://docs.realapp.link/updates/changelog); [Real docs: Karma](https://docs.realapp.link/basics/karma)
  - Join-Discord buttons have been in the app since March 2021.
  - Reaching 10,000 karma unlocks a Discord role.
  - Karma is earned for entering live game feeds, polls and daily comments, which rewards simply showing up during games.
- **League expansion sequence** — [Real changelog](https://docs.realapp.link/updates/changelog)
  - NBA (2021).
  - NFL beta on Sep 12, 2021, at the start of the season.
  - NCAA men's basketball Top 25 (Dec 2021).
  - NHL (Feb 19, 2022).
  - MLB (mid-2022).
  - UFC beta (Jul 2023).
  - WNBA (May 2024).
  - EPL soccer beta (Aug 2024).
  - Golf (Apr 2025).
  - The five major European soccer leagues plus FA Cup and MLS (Mar 2026).
  - College baseball (Jun 2026).
  - Tennis beta (Aug 2026).
  - The total reached 18 leagues — [Real FAQ](https://docs.realapp.link/basics/faqs); [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- **Audience mix:** over the last 1.5–2 years much of Real's usage has come from fantasy players and bettors tracking their bets — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription). About 75% of users who comment on player performances post betting-related comments — [FanDuel](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
- **Next growth levers, per the founders:** making the app more fun with friends, and curating sub-communities around recurring meme moments (for example, fans tracking Brandin Podziemski's chase for 30 points). Groups can nest under any piece of content — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)

### Inferences
- Community density came from concentrating all fans of one league, on that league's game nights, into per-play threads, rather than spreading them thin across many topics.
- **Lessons for Real for markets:**
  - The equivalents of NBA meme pages are FinTwit and X accounts, options-flow pages, Discord alert-group owners, and finance TikTok and YouTube creators.
  - A free, watermarked, screenshot-friendly live "box score" for a ticker or earnings print, which those creators post anyway, is the cold-start lever.
  - Pick one "league" with dense, recurring, concurrent events, such as mega-cap earnings season or 0DTE SPX and SPY.
  - Pay referral rewards in in-app currency.

### Gaps
- No acquisition-cost figures were found.
- No data on creator payments (amounts, how many creators), conversion, or channel attribution.
- No ambassador-program terms were found beyond referrals.

## 6. Business model: what Real monetizes today and what's planned

### Takeaway
Real makes money from three sources today:
- **Real Pro subscription:** $7.99 per month or $19.99 for three months.
- **Rax virtual currency:** in-app purchases from $4.99 to $49.99. Rax buys digital collectible cards and packs and funds Pro-only peer-to-peer prediction markets. Rax cannot be cashed out.
- **FanDuel partnership (since September 2026):** FanDuel is the exclusive sportsbook and prediction-market partner, with live odds in game feeds. Terms are undisclosed; the founders describe it as an additional revenue stream.

There is no real-money wagering. Advertising is not evident; the 2022 stance was no ads. Revenue is undisclosed. John's framing is the one quote I keep: "Pokémon for sports" ([Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)).

### Cited Findings
- **In-app purchase list (Oct 18, 2026)** — [App Store](https://apps.apple.com/us/app/real-sports/id1514546162)
  - Real Pro: monthly $7.99; 1 month $7.99; 3 months $19.99.
  - Rax: 400 or 750 Rax for $4.99; 800 for $9.99; 1,700 or 5,000 for $19.99; 4,500 or 14,000 for $49.99.
- **Real Pro**
  - Launched Apr 14, 2023 — [Real changelog](https://docs.realapp.link/updates/changelog)
  - Monetization-relevant perks — [Real docs: Real Pro](https://docs.realapp.link/basics/real-pro):
    - Full web app (multiple games in tabs).
    - Rax predictions.
    - A free daily pack, which the docs value at 6,000 Rax a month.
    - 10% bonus Rax on purchases.
    - Advanced per-player notifications.
    - Custom over/under stat trackers (for example points + rebounds + assists).
    - Doubled leaderboard prizes; links in comments; early access.
- **Rax virtual currency**
  - Launched May 3, 2022 — [Real changelog](https://docs.realapp.link/updates/changelog). John called it revenue-generating that month — [John LinkedIn, May 20, 2022](https://www.linkedin.com/posts/johnmantonelli_startup-sports-tech-activity-6933466447604064256-4fSG)
  - Apple in-app purchase for Rax added Dec 15, 2022 — [Real changelog](https://docs.realapp.link/updates/changelog)
  - Rax can be bought, earned through karma and leaderboards, or won. Purchases are final — [Real docs: Rax](https://docs.realapp.link/basics/rax); [Real Terms of Use](https://docs.realapp.link/policies/terms-of-use)
- **Collectibles economy** — [Real FAQ](https://docs.realapp.link/basics/faqs); [Real docs: Card Packs](https://docs.realapp.link/collect/card-packs)
  - Player and team cards earn Rax daily based on real game performance. Play cards level them up through 7 rarity tiers; booster cards add multipliers.
  - Packs cost 100 to 1,250 Rax, with daily caps.
  - Game packs: 300 drop an hour before each game, with prices rising from 800 to 1,250 Rax as they sell.
  - A Rax marketplace and auctions were added Jun–Sep 2025 — [Real changelog](https://docs.realapp.link/updates/changelog)
- **Front Office Sports on the model** — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - It is a virtual-bucks model like Roblox and Fortnite.
  - Louis says there is no cash-out, which makes it closer to a video game than a sportsbook.
  - Pregame polls resemble bets but involve no real money.
- **Prediction markets in Rax**
  - Pro-only beta launched Dec 20, 2025: community-driven game-winner markets denominated in Rax, automated and peer-to-peer, with "cashout" of positions inside the app. That cashout is in Rax only; per Front Office Sports there is no real-money cash-out.
  - Futures markets were added Feb–Mar 2026.
  - [Real changelog](https://docs.realapp.link/updates/changelog)
  - Any user can wager karma (not Rax) on pre-game spread polls, up to 100 karma per game — [Real docs: Karma](https://docs.realapp.link/basics/karma)
- **FanDuel partnership (announced Sep 10, 2026)** — [FanDuel](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
  - FanDuel is Real's only sportsbook and prediction-market partner.
  - Odds appear in game feeds, player performance screens and team box scores, starting in the 2026 NFL season.
  - Users can turn betting content off.
  - John's announcement called FanDuel the exclusive live-odds partner and odds a core missing piece of sports data — [John Antonelli LinkedIn](https://www.linkedin.com/in/johnmantonelli/)
- **The founders on the FanDuel choice (TBPN)** — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
  - They talked to essentially every real-money gaming operator before choosing FanDuel, which they call another revenue stream.
  - They treat odds as another data source and as conversation fodder.
  - They plan real-time line-movement charts and discussion threads for every market.
  - They say they signed up millions of gamblers in the last couple of years.
- **FanDuel in the code:** the web app bundle contains a FanDuel-branded odds module and a link to sportsbook.fanduel.com — [Real web app bundle](https://realsports.io/ad70ad31/index.js)
- **Deal economics:** affiliate, revenue share or fixed fee is not disclosed — [FanDuel](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
- **Evolution of stance:** in April 2026 the founders said TCG's money let them skip quick sportsbook and prediction-market sponsorship money — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/). Five months later they chose a single exclusive partner — [FanDuel](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
- **Ads**
  - In 2022 Real ran no advertising, citing data-privacy concerns — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
  - The terms contain a boilerplate clause for advertisers — [Real Terms of Use](https://docs.realapp.link/policies/terms-of-use)
  - The iOS privacy label lists Advertising Data as linked to the user, and Usage Data as used to track — [App Store](https://apps.apple.com/us/app/real-sports/id1514546162)
  - Google Play's data-safety section says no data is shared with third parties — [Google Play](https://play.google.com/store/apps/details?id=vg.real&hl=en_US)
- **Earlier monetization:** serial-numbered team, sport and player "passes" came with perks such as unlimited group comments and Rax prizes (Aug–Oct 2022) — [Real changelog](https://docs.realapp.link/updates/changelog)
- **Payments stack, from the web bundle:** a RevenueCat integration and Apple Pay purchase path (likely mobile), plus Stripe as the web checkout path — [Real web app bundle](https://realsports.io/ad70ad31/index.js)

### Inferences
- Until September 2026, revenue was likely almost entirely in-app purchases (Pro and Rax). The FanDuel deal adds a business-to-business line (likely affiliate or partnership fees), but the mix can't be quantified.
- The "no cash-out" design is deliberate. It keeps Real out of real-money gambling regulation while capturing betting-adjacent engagement.
- **Most transferable pieces for Real for markets:**
  - A roughly $8/month "Pro" tier for advanced alerts, custom trackers and multi-game (multi-ticker) web views.
  - Virtual-currency collectibles and predictions with no cash-out.
  - One exclusive partner, where a broker or exchange would play the sportsbook's role.
  - Before copying any of these, the securities, FINRA, CFTC and advertising rules need checking by whoever covers regulation. A broker affiliate is not legally equivalent to a sportsbook affiliate.

### Gaps
- Revenue, ARPU, paying share of users, Pro subscriber count and Rax sales volumes are all undisclosed.
- FanDuel economics are undisclosed.
- I could not confirm whether any ads currently run.

## 7. Technology: data sources, how speed is delivered, the stack, data rights

### Takeaway
- **Data is bought, not built:** feeds come from commodity vendors (Sportradar, Genius Sports; Stats Perform for golf), plus NFL Next Gen Stats, an official NHL feed since October 2025, and some scraping. The founders describe raw facts as unowned and commoditized.
- **Speed is mostly not adding delay:** feeds are fanned out over WebSockets (socket.io) and about 50M push notifications a day, triggered by an in-house play-rating algorithm. Nothing exotic at the edge.
- **Stack:** React and React Native with JavaScript, PostgreSQL, AWS Oregon (us-west-2) behind nginx, and CloudFront and Fastly CDNs. Three engineers use AI-assisted coding.
- **Gaps on the public record:** no engineering blog, published latency numbers, or data-rights dispute were found.

### Cited Findings
- **Data vendors, per John on TBPN:** live sports data is pretty commoditized and comes from Genius Sports and Sportradar, and Real also scrapes a lot of data. Facts like a made three aren't owned by the leagues or anyone. Real's value-add is context, such as historical milestones and scoring streaks — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
- **Vendors visible in the code:** the web app ships attribution logos for Sportradar, Genius Sports and NFL Next Gen Stats. Its golf data-source list names SportRadar and StatsPerform — [Real web app bundle](https://realsports.io/ad70ad31/index.js)
- **Official NHL data:** the changelog says NHL data fully uses an official source as of Oct 31, 2025 — [Real changelog](https://docs.realapp.link/updates/changelog)
- **Earlier press on data and speed:**
  - Feeds come from the leagues; Louis says they are basically instant — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - Real pulls from major providers and adds proprietary tags (walk-off, lead-taking shot) and supplementary data (shot streaks, exit velocity). It is usually faster than TV across its sports and offers a delay to sync with broadcasts — [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
  - In 2022 Louis said play-by-play data had only recently become real-time enough for this product — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
- **Data-quality gating** — [Real docs: Sports](https://docs.realapp.link/basics/sports); [Real FAQ](https://docs.realapp.link/basics/faqs); [Real changelog](https://docs.realapp.link/updates/changelog)
  - New sports are added only when quality real-time play-by-play exists.
  - College basketball outside the Power 5 conferences is excluded for lack of reliable real-time data.
  - Since October 2022 the app flags games whose data is unreliable.
- **Speed and latency work over time** — [Real changelog](https://docs.realapp.link/updates/changelog); [Real FAQ](https://docs.realapp.link/basics/faqs)
  - May 2021: a "supercharged" feed with faster, more accurate updates.
  - Sep 2021: logic moved to the backend so data changes need fewer app updates.
  - Mar 2022: alpha of a college-basketball speed upgrade.
  - May 2022: "slowmode" lets users delay the feed 5–120 seconds to match TV or a stream.
  - Oct 2024: a faster NFL feed that shows plays as "In progress" and updates when penalties or reviews change outcomes.
  - Nov 2024: much faster NHL updates.
- **Real-time transport (my inspection of the public web bundle, Oct 18, 2026)** — [Real web app bundle](https://realsports.io/ad70ad31/index.js); [realapp.com](https://www.realapp.com/)
  - The web app includes the socket.io client library, which uses WebSockets with a long-polling fallback and auto-reconnect.
  - Its configuration names a WebSocket endpoint at web.realsports.io.
  - Other hosts: APIs at web.realapp.com and mobileweb.realapp.com, a session service at id.real.vg, a media service at mediaservice.real.vg, and staging at staging.real.vg.
  - The web app is a single-page JavaScript app with an empty HTML shell.
- **Hosting (my DNS lookups, Oct 18, 2026, matched against AWS's published IP ranges)** — [AWS IP ranges](https://ip-ranges.amazonaws.com/ip-ranges.json)
  - web.realsports.io (WebSockets), api.real.vg, mediaservice.real.vg and www.realapp.com resolve to AWS EC2 in us-west-2 (Oregon). api.real.vg answers with JSON from an nginx server.
  - realapp.com, realsports.io, media.realapp.com and id.real.vg resolve to Amazon CloudFront.
  - web.realapp.com and mobileweb.realapp.com resolve to the Fastly CDN (their DNS points to a Fastly hostname).
- **Stack, from job posts**
  - Undated GitBook post: React and React Native with JavaScript; SQL, preferably PostgreSQL; a back-end language; keeping the app responsive during live events; being available on big sports weekends — [Real job post: Full-Stack Engineer](https://docs.realapp.link/jobs/full-stack-engineer-real)
  - March 2024 LinkedIn post: staff-level full-stack, US-only, full-time — [Louis Antonelli LinkedIn](https://www.linkedin.com/in/louis-antonelli/)
  - First-ever full-time designer opening: until then, design was done by the founding engineers — [Real job post: Product Designer](https://docs.realapp.link/jobs/product-designer)
- **Other third-party services seen in the web bundle** — [Real web app bundle](https://realsports.io/ad70ad31/index.js)
  - RevenueCat (purchases) and Stripe.
  - An AppsFlyer signup-tracking interface, which is stubbed out on web; this suggests AppsFlyer attribution on mobile, but that is an inference.
  - Cloudflare Turnstile bot challenge on web.
- **Notification engine**
  - About 50M per day — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/); [LinkedIn company page](https://www.linkedin.com/company/real-vault)
  - On TBPN: alerts fire on Real's play ratings. Example: a "cycle watch" alert only when a player needs a single, double or homer, not the unlikely triple. The founders say ESPN's and Bleacher Report's score apps mostly send halftime and final alerts, while Real sends real-time ones — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
  - Alert types: "Real Moments" for the ends of close games, team alerts, player streaks and big plays, and tag alerts — [Real docs: Notifications](https://docs.realapp.link/basics/notifications)
- **Rating algorithm**
  - Objective inputs: game closeness, time, streaks, shot distance, efficiency, and game-tying or game-winning context — [Real docs: Rating System](https://docs.realapp.link/basics/real-rating-system)
  - The 0–10 scale can exceed 10 for historic games. Fans now cite the ratings in MVP and rookie debates — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
- **Team and shipping speed:** Louis plus engineers Sam and Chris — [John LinkedIn, Apr 13, 2026](https://www.linkedin.com/posts/johnmantonelli_in-february-2020-i-woke-up-to-a-text-from-activity-7449584221846773760-J85X). The team hasn't grown, but with AI tools release cadence went from every 3–4 months to every 2–3 weeks — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
- **AI features**
  - Real Bot, formerly "Scout" and "Intellisearch", launched Oct 17, 2026. It answers stats questions from Real's own data and says when data is missing — [Real docs: Real Bot](https://docs.realapp.link/interact/real-bot); [Real changelog](https://docs.realapp.link/updates/changelog)
  - AI comment summaries arrived in May 2024 — [Real changelog](https://docs.realapp.link/updates/changelog)
- **Data rights and disputes**
  - I found no lawsuits or disputes.
  - Real's terms say play videos and team and player images belong to the NBA and its partners, and that Real uses them in a news and reporting capacity — [Real Terms of Use](https://docs.realapp.link/policies/terms-of-use)
  - Since May 2021, plays have linked out to video in Safari or Chrome. Whether Real hosts any video itself is not stated — [Real changelog](https://docs.realapp.link/updates/changelog)
  - **Legal backdrop:** in NBA v. Motorola (2d Cir. 1997) the court held that game facts transmitted by a pager service were not copyrightable, and it narrowed "hot news" misappropriation claims — [Wikipedia: NBA v. Motorola](https://en.wikipedia.org/wiki/National_Basketball_Ass%27n_v._Motorola,_Inc.)

### Inferences
- **Where Real's speed comes from:**
  - Licensed low-latency feeds of the kind bettors also use.
  - Not adding delay: data goes straight from ingestion to WebSocket fan-out and push notifications.
  - Rating plays fast enough to trigger alerts in the moment.
  - It runs from a single AWS region with CDN in front, not custom edge compute. A small team can build this.
- **What actually differentiates Real:** derived content — ratings, tags, streaks and context — on top of commodity data. That derived content makes raw data shareable and drives notifications.
- **Implications for Real for markets (to verify):**
  - Unlike sports facts, real-time exchange data, especially OPRA options data, is typically licensed with redistribution and display fees. The "commoditized and scrapeable" assumption probably does not carry over. The market-data researcher should verify this.
  - Delayed or derived data, such as "unusual activity" tags, could be a cheaper wedge.
  - The stack itself is easy to replicate: React Native, Postgres, a socket.io-style fan-out, push alerts, and a rating engine.

### Gaps
- No engineering blog, tech talks or published latency figures (in milliseconds).
- Push provider unknown (APNs and FCM directly vs. a vendor).
- Unknown whether the mobile apps use the same WebSocket endpoint as the web app.
- Which sources are scraped vs. licensed, and data costs, are not disclosed.

## 8. Moderation: toxicity, spam and bots in live games at scale

### Takeaway
- **Layered automated filtering since launch:** a keyword lookup table catches about 80–85% of bad content, a fast classifier about 10% more, and an LLM handles the rest. Every reply is scanned in real time.
- **Human and user layers:** human moderators and user reports back up the automation.
- **Cheap structural friction:** karma gates for commenting, slowmode for new users, and a 24-hour wait before joining team groups.
- **Bans as warnings,** plus a GPT-4o three-strike system for WNBA comments.
- **Tone:** the founders deliberately keep trash talk alive for their 18–30 audience.

### Cited Findings
- **Louis on TBPN** — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
  - AI has moderated comments since day one, and every reply is now scanned in real time.
  - A lookup table catches about 80–85%, a very fast classifier catches about another 10%, and the rest goes to a current LLM, with escalation when needed.
  - The audience skews 18–30, so they keep some edge and trash talk; the goal is never having to shut down live chats.
  - Chats are split by box score and play rather than one giant game chat.
- **Real's docs** — [Real docs: Comments](https://docs.realapp.link/interact/comments)
  - Automated systems block very hateful and explicit language; human comment moderators remove hate; users can report.
  - WNBA comments are moderated with ChatGPT-4o under a three-strike system. The published prompt targets misogyny in a women's-basketball context, allows criticism of play, and ignores out-of-context profanity.
- **Friction and safety mechanisms in the changelog** — [Real changelog](https://docs.realapp.link/updates/changelog)
  - Feb 27, 2021: commenting unlocks at 200 karma, with a 5-second slowmode on top-level comments until 1,000 karma.
  - Jun 18, 2021: the main group is moderated to the comment guidelines.
  - Oct 10, 2022: joining player and team groups requires having favorited that player or team for at least 24 hours.
  - Nov 22, 2022: support for human comment moderators.
  - Apr 14, 2023: comment downvoting, used to hide comments.
  - May 24, 2023: ChatGPT moderates reported comments.
  - Oct 2, 2023: a 60-second edit window with visible edit history.
  - Dec 2, 2024: automatic two-factor checks for sensitive actions on new devices.
  - Jan 21, 2025: top-upvoted comments are randomly re-ordered.
  - Aug 9, 2026: group audit logs for moderators.
- **Rules** — [Real docs: Rules](https://docs.realapp.link/interact/rules); [Real docs: Comments](https://docs.realapp.link/interact/comments); [Real docs: Real Pro](https://docs.realapp.link/basics/real-pro)
  - No explicit warnings; a ban is the warning, and banned users can appeal to @mod.
  - Automatic bans for discriminatory language, threats, spoilers, gore and porn.
  - Flame-baiting, doxxing and harmful misinformation are removed or banned.
  - "Novelty accounts" can be banned.
  - Dodging filters with alternate fonts earns a ban strike.
  - Link posting is a revocable Pro-only privilege.
- **Anti-bot and anti-fraud**
  - The terms ban automated access and automated account creation — [Real Terms of Use](https://docs.realapp.link/policies/terms-of-use)
  - The web app uses Cloudflare Turnstile — [Real web app bundle](https://realsports.io/ad70ad31/index.js)
  - Referral rules exclude previously used devices and Android — [Real FAQ](https://docs.realapp.link/basics/faqs)
  - Users can restrict mentions, replies and DMs to friends only, and block, mute and report — [Real FAQ](https://docs.realapp.link/basics/faqs)

### Inferences
- The cost-efficient pattern is cheap filters first, then a classifier, then an LLM only for the residue. This is what lets a three-engineer team moderate hundreds of thousands of concurrent commenters. It also keeps LLM costs bounded.
- Karma gating and slowmode act as low-cost spam and bot brakes during game spikes.
- **Market-specific abuses to plan for:** ticker spam and pump-and-dump promotion, undisclosed paid promotion, impersonated "gurus", and links to paid groups. These may carry securities-law implications that need verification.

### Gaps
- Moderator headcount, removal volumes and false-positive rates.
- Which classifier and LLM vendors are used today, beyond the WNBA GPT-4o mention.
- Any regulatory or app-store moderation incidents.

## 9. Competition, risks, and what's next

### Takeaway
- **Competitors:**
  - Legacy score apps (ESPN, Bleacher Report).
  - Fan communities on X, Reddit, Instagram and TikTok; Discord and Telegram groups.
  - Live chats on X, YouTube and Twitch.
- **Real's edge:** speed, data-native threads per play, push alerts, and progression through badges, karma and cards.
- **Main risks:**
  - Dependence on data vendors.
  - Seasonality.
  - Being adjacent to betting, with age-gating inconsistencies.
  - A tiny team.
  - Moderation at scale.
- **Next:**
  - Tennis, F1 and global soccer, plus deeper data in existing leagues.
  - Live odds and line-movement charts through FanDuel.
  - The AI bot and social and friends features.
  - A 2M-DAU goal.
  - Non-sports live events (The Bachelor, Love Island, elections) are deferred until Real dominates sports.

### Cited Findings
- **Competitors the founders and press name**
  - ESPN (cluttered with opinion), Twitter (misinformation, noise), and Discord and Telegram groups — [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
  - Comparisons to X, Reddit, Discord, YouTube and Twitch chats, and to Roblox and Fortnite — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - X has added game-level live chat. Social platforms lack profile progression. Legacy score apps don't send real-time play alerts — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
- **Strategic interest from betting operators:** the TBPN host argued betting and prediction-market companies would covet Real's engagement — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription). FanDuel's president praised Real's community — [FanDuel](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
- **What's next, per the founders and the company**
  - Tennis and F1 with the TCG money — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
  - Tennis, F1, global soccer and deeper league coverage — [John LinkedIn, Apr 13, 2026](https://www.linkedin.com/posts/johnmantonelli_in-february-2020-i-woke-up-to-a-text-from-activity-7449584221846773760-J85X)
  - A target of 2M DAU — [John LinkedIn, Jun 1, 2026](https://www.linkedin.com/posts/johnmantonelli_1-million-daily-actives-on-real-sports-activity-7467239030129266688-Vbha)
  - From TBPN — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription):
    - Line-movement charts and per-market discussion.
    - Friend features.
    - Curated sub-communities.
    - A possible community vote on obscure sports.
    - Non-sports live events appeal to them, but only after dominating sports, which the founders still see as a 10x opportunity.
  - From the docs: coverage of every sport with reliable live data, and historical data going back to the 1990s — [Real docs: Sports](https://docs.realapp.link/basics/sports); [Real FAQ](https://docs.realapp.link/basics/faqs)
  - Shipped Oct 17, 2026: Real Bot and Arena, a Pro head-to-head card game — [Real changelog](https://docs.realapp.link/updates/changelog)
- **Risk evidence**
  - **Seasonality:** a summer lull, and short events like the Olympics are hard to justify in engineering time — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
  - **Betting adjacency:** about 75% of performance commenters post betting-related comments — [FanDuel](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
  - **Age gating is inconsistent across platforms:**
    - iOS is rated 18+ for simulated gambling — [App Store](https://apps.apple.com/us/app/real-sports/id1514546162)
    - The terms allow users 13+ with parental consent — [Real Terms of Use](https://docs.realapp.link/policies/terms-of-use)
    - Google Play rates it Everyone — [Google Play](https://play.google.com/store/apps/details?id=vg.real&hl=en_US)
  - **Data dependence:** sport coverage depends on data availability — [Real docs: Sports](https://docs.realapp.link/basics/sports); some data is scraped — [TBPN transcript](https://share.transistor.fm/s/e6c9bcc4/transcription)
  - **Tiny team:** five people in April 2026, and the first full-time designer had not yet been hired — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/); [Real job post: Product Designer](https://docs.realapp.link/jobs/product-designer)
- **Analyst and investor views:** TCG's Kerns called it the fastest-growing sports app he'd seen — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/). BetCrunch framed Real as one of many verticalized media startups — [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)

### Inferences
- **The copyable formula:**
  1. One league with dense nightly concurrent events.
  2. A founder with a creator network in that niche.
  3. Objective data as the content, not opinion-driven user posts.
  4. Threads per event and per play.
  5. A rating engine that makes data shareable and drives alerts.
  6. Gamified progression (karma, badges).
  7. Monetization only after engagement: Pro tier, virtual currency, then one exclusive partner.
- **Ways markets differ that the co-founder report must address:**
  - Data licensing costs and redistribution rules.
  - Securities and advertising regulation, plus manipulation risk in ticker chat.
  - Event structure: continuous trading 6.5 hours a day vs. discrete plays, so a "play" must be defined (for example a large print, an unusual options sweep, an earnings line item, a halt, or a level break).
  - Audience overlap with Real's bettor and fantasy users, who are similar to retail options traders, could be strong.

### Gaps
- No independent analyst coverage or market sizing for Real.
- No app-intelligence estimates.
- No churn or retention data.
- No disclosed revenue to judge whether the monetization layers work at scale.
