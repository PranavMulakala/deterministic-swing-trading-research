# Legal and Regulatory Limits on "Real for markets" (US, as of October 18, 2026)

_Scope: US federal law, plus notable state issues, for a social app covering stocks, options and crypto (live prices, charts, news, a comment on every move). Possible later features: trading, creator alert rooms and game-like predictions. This is research, not legal advice. Market-data licensing is covered by another researcher. The shared web-search budget ran out partway through. After that, only known primary-source URLs were fetched directly, and items not verified are listed under each Gaps heading. Search-result summaries are labeled as such._

---

## 1. Broker-dealer status: when do order routing, transaction-based pay, broker referral or revenue-share deals, or "trade from the app" require registration or a partner? How do apps integrate trading without registering?

### Takeaway
The statutory trigger is being "engaged in the business of effecting transactions in securities for the account of others." The SEC's own guide flags three things as registration indicators:
- pay tied to "the outcome or size of the transaction"
- taking part in solicitation, negotiation or execution
- handling customers' funds or securities

So the bright red lines are per-trade revenue share, splitting payment for order flow, and accepting or routing orders yourself.

The common unregistered pattern is a flat marketing fee (per lead or per funded account) paid by a FINRA member firm. The broker owns KYC, execution and the regulated communications. M1 Finance's flat-fee program with about 1,700 influencers drew a FINRA fine over content and supervision, not over the payment structure.

US white-label broker APIs such as Alpaca's require the partner to be a registered broker-dealer, or an RIA. An unregistered v1 is therefore limited to:
- deep links and referrals
- read-only account linking
- an embedded flow where the partner broker is broker of record and the app is paid flat fees not tied to trades (counsel required)

### Cited Findings
- **Statutory definition.** Exchange Act §3(a)(4)(A): a "broker" is "any person engaged in the business of effecting transactions in securities for the account of others." Section 15(a) requires such persons to register. — [15 U.S.C. 78c (Cornell LII)](https://www.law.cornell.edu/uscode/text/15/78c)
- **SEC Guide to Broker-Dealer Registration: the four questions.** The guide asks whether you:
  - take part in "important parts of a securities transaction," including solicitation, negotiation or execution;
  - receive compensation that depends on or relates to "the outcome or size of the transaction," including trailing commissions;
  - handle "the securities or funds of others";
  - are otherwise engaged in effecting or facilitating securities transactions.

  A "yes" to any of these may mean registration is needed. — [SEC Guide to Broker-Dealer Registration](https://www.sec.gov/reportspubs/investor-publications/divisionsmarketregbdguidehtm.html)
- **SEC Guide on finders.** "Finders" may need to register depending on their activities, including "making referrals to, or splitting commissions with" registered broker-dealers. Associated persons "cannot set up a separate entity to receive commission checks." — [SEC Guide](https://www.sec.gov/reportspubs/investor-publications/divisionsmarketregbdguidehtm.html)
- **SEC Guide on commission sharing.** The only commission-sharing "networking" arrangements the guide describes are for banks, credit unions and insurance agencies, under specific no-action letters and SRO rules. It describes no equivalent carve-out for tech or media platforms. — [SEC Guide](https://www.sec.gov/reportspubs/investor-publications/divisionsmarketregbdguidehtm.html)
- **FINRA Rule 2040(a).** Member firms may not "directly or indirectly, pay any compensation, fees, concessions" to a person who is not a registered broker-dealer but "is required to be so registered." — [FINRA Rule 2040](https://www.finra.org/rules-guidance/rulebooks/finra-rules/2040)
- **FINRA Rule 2040, Supplementary Material .01.** The member must reasonably support its determination that the payee need not register. It may rely on SEC releases, no-action letters or interpretations, or on an opinion from independent, reputable US counsel. It must keep records of the determination and revisit it periodically when payments are ongoing. — [FINRA Rule 2040](https://www.finra.org/rules-guidance/rulebooks/finra-rules/2040)
- **January 2026 SEC no-action letter.** SEC staff allowed broker-dealers to pay transaction-based compensation to pass-through personal-service entities wholly owned by registered representatives, under conditions. The relief does not extend to app operators or referral partners. — [Shu Law alert, Jan 2026 (secondary)](https://shufirm.com/registered-reps-and-broker-dealer-alert-jan-2026)
- **FINRA v. M1 Finance, March 18, 2024: the program.**
  - Fine: $850,000.
  - From January 2020 to April 2023, about 1,700 influencers were paid "a flat fee for each account opened and funded" through unique links, with no cap. More than 39,400 accounts came through the program.
  - M1 supplied influencers with graphics and a "Welcome Guide."
  - — [FINRA news release](https://www.finra.org/media-center/newsreleases/2024/finra-fines-m1-finance-850000-violations-regarding-use-social-media)
- **FINRA v. M1 Finance: what FINRA charged.**
  - Rules cited: 2210, 2010, 3110 and 4511.
  - Violations: posts that were not fair and balanced (one misdescribed margin loans), no review or approval of content before use, no retention of the posts, and no supervisory system.
  - FINRA did not cite the flat-fee payment structure itself.
  - — [FINRA news release](https://www.finra.org/media-center/newsreleases/2024/finra-fines-m1-finance-850000-violations-regarding-use-social-media)
- **Alpaca Broker API (US docs).**
  - The fully-disclosed setup is for "a registered broker-dealer." The omnibus setup is also limited to registered broker-dealers.
  - The RIA setup is for SEC-registered RIAs. In that setup "the account approval process is owned by Alpaca," and the RIA owns "the user experience and most of the communications."
  - — [Alpaca Broker API use cases](https://docs.alpaca.markets/us/docs/use-cases)
- **Alpaca account opening (search-result summary).** For the fully-disclosed setup, the partner must "hold a proper broker-dealer license" and is "the broker on the record." — [Alpaca account opening](https://docs.alpaca.markets/us/docs/account-opening)
- **Conflict on Alpaca.** A search-result summary of Alpaca's docs mentioned a setup for unlicensed fintechs ("Trading/Investing App") that is "only available in select countries." The US use-cases page I fetched did not show it. — [Alpaca docs](https://docs.alpaca.markets/docs/use-cases)
- **Apple App Store Review Guideline 3.2.1(viii).** "Apps used for financial trading, investing, or money management should be submitted by the financial institution performing such services and must have necessary licensing and permissions in the locations where you make them available." — [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- **FINRA attention to brokers' social-platform partners.** FINRA's 2023 sweep update on "Social Media Influencers, Customer Acquisition and Related Information Protection" followed a September 2021 targeted exam. That exam looked at how firms acquire customers through social media and share customer usage data. Brokers' data-sharing with social and marketing partners is an exam focus. — [FINRA Social Media key topic page](https://www.finra.org/rules-guidance/key-topics/social-media)

### Inferences
Integration ladder, from lowest to highest regulatory weight:

| Level | What the app does | Status |
|---|---|---|
| L0 | Prices, charts, news and UGC only | No broker issue |
| L1 | Outbound "Open in Robinhood/Webull" deep links, no compensation | Very low risk |
| L2 | Affiliate or advertising deals paid as a flat fee per lead or funded account, never per trade or by trading volume | Standard pattern (M1, broker affiliate programs) |
| L3 | Read-only brokerage linking through an aggregator to show positions and P&L | No broker-dealer issue in itself; triggers data and privacy duties (see Q7) |
| L4 | Embedded order ticket where a partner broker-dealer is broker of record and owns KYC, options approval, best execution and confirmations; the app is paid flat SaaS or marketing fees | Counsel required; partner contract will impose controls |
| L5 | Own or acquire a broker-dealer, or register as an RIA | Only after product-market fit |

- **Effect of an affiliate deal (L2).** Posts that carry the broker's link become the broker's FINRA 2210 problem, so the broker will impose pre-approval and archiving on the app's paid placements and possibly on sponsored creators.
- **Red lines for an unregistered app:**
  - revenue tied to trades, contracts or volume, including payment-for-order-flow splits;
  - holding or "accepting" orders, or deciding where they route;
  - touching customer money;
  - commission splits paid to creators;
  - "trade this alert" buttons that pre-fill orders, combined with any transaction-linked pay.
- **Strategic implication.** For an MVP, "trade from the app" adds little legal value and a lot of risk. Deep links (L1) give most of the user benefit.
- **Rule 2040 as a market signal.** Because broker partners must document a reasonable basis for every payment to the app, any broker offering per-trade economics to an unregistered app is a warning sign.

### Gaps
- **Per-funded-account bounties.** I found no primary SEC or FINRA guidance on whether a per-funded-account bounty paid to an unregistered app publisher counts as "transaction-based." M1 suggests FINRA tolerated the structure, but that is not a safe harbor.
- **Other platforms' models not verified (search budget exhausted):**
  - TradingView's broker-integration model (not a broker, with brokers embedded);
  - SnapTrade-style "trade through your own broker" APIs;
  - Stocktwits' own broker-dealer history;
  - Public.com's structure.
- **SEC 2020 proposed "finder" exemption.** Status not verified. It covered private placements only.
- **Options-specific broker duties.** Options account approval and Options Disclosure Document delivery under FINRA Rule 2360 fall on the partner broker. Not verified this session.

---

## 2. Investment adviser status: the publisher's exclusion (Lowe v. SEC), and when personalized signals, AI recommendations or paid alert rooms require RIA registration; CFTC commodity trading advisor rules for futures or crypto-derivative signals

### Takeaway
Impersonal, regularly published, disinterested market content fits the Advisers Act publisher exclusion as the Supreme Court read it in *Lowe*. *Lowe*'s newsletter even included specific buy/sell/hold calls.

The exclusion is weakest exactly where this product might go:
- real-time paid alert rooms timed to market moves;
- callers who trade around their own calls;
- AI ideas tailored to a user's portfolio;
- copy-trading or auto-trading.

For futures and crypto-derivative signals, the CTA definition covers paid advice "through publications." Two escapes exist: an exclusion for publishers of general, regularly disseminated data whose advice is "solely incidental," and the Reg. 4.14(a)(9) exemption for advice that neither directs accounts nor is tailored to particular clients.

### Cited Findings
- **Statute.** Advisers Act §202(a)(11) defines an investment adviser as "any person who, for compensation, engages in the business of advising others" about securities. It excludes:
  - (C) broker-dealers whose advice is "solely incidental" and who receive "no special compensation";
  - (D) "the publisher of any bona fide newspaper, news magazine or business or financial publication of general and regular circulation."

  — [15 U.S.C. 80b-2 (Cornell LII)](https://www.law.cornell.edu/uscode/text/15/80b-2)
- ***Lowe v. SEC*, 472 U.S. 181 (1985): holding.** Lowe's newsletters fell within the exclusion, so he was not an "investment adviser." The Court did not reach the First Amendment question. — [Lowe v. SEC (Cornell LII)](https://www.law.cornell.edu/supremecourt/text/472/181)
- ***Lowe*'s three requirements.**
  - "Bona fide" means genuine, disinterested commentary, not promotion by a "tout."
  - The content must not be "attuned to any specific portfolio or to any client's particular needs." The exclusion holds only while communications "remain entirely impersonal" and do not become person-to-person relationships.
  - "General and regular circulation": "regular" means not timed to specific market activity or events.

  — [Lowe v. SEC](https://www.law.cornell.edu/supremecourt/text/472/181)
- ***Lowe*'s facts.**
  - The Lowe letter had 3,000 to 19,000 subscribers and included specific buy, sell or hold recommendations.
  - It published only eight issues in 15 months despite being advertised as semimonthly.
  - The Court found no evidence that publication was tied to market activity or that Lowe traded the securities he discussed.
  - The lower-court injunction against individualized telephone hotline advice was not challenged.

  — [Lowe v. SEC](https://www.law.cornell.edu/supremecourt/text/472/181)
- **SEC staff guidance on robo-advisers (IM Guidance Update No. 2017-02, February 2017).** Robo-advisers "are typically registered investment advisers." They "are subject to the substantive and fiduciary obligations of the Advisers Act." Staff flagged three areas: disclosures, gathering client information to support suitable advice, and compliance programs for automated advice. The guidance notes many robo-advisers "rely solely on questionnaires." — [SEC IM Guidance Update 2017-02](https://www.sec.gov/investment/im-guidance-2017-02.pdf)
- **SEC "AI washing" cases (March 18, 2024).**
  - Delphia and Global Predictions paid $400,000 combined for false AI claims.
  - Global Predictions called itself the "first regulated AI financial advisor."
  - The orders cited Marketing Rule and Advisers Act violations, with this line from Chair Gensler: "Such AI washing hurts investors."

  — [SEC press release 2024-36](https://www.sec.gov/news/press-release/2024-36)
- **SEC v. Gauvin (December 10, 2025).** Gauvin built a Discord following by posing as a successful investment professional and raised about $18.1M. The SEC seeks, among other relief, a bar on his acting as an investment adviser. — [SEC press release 2025-141](https://www.sec.gov/newsroom/press-releases/2025-141-sec-charges-canadian-citizen-fraud-schemes-targeted-retail-investors-discord)
- **Study of 15 paid Discord options-alert communities (Bloomberg, October 7, 2026, as summarized by TokenPost).**
  - Retail buying spiked to about 14.5 standard deviations above normal after alerts.
  - Recommended options rose about 3% in the first minute, and most of the impact faded within about two hours.
  - Subscribers generally lost money after transaction costs, even when they acted almost immediately.
  - The median contract had 3 days to expiry, cost about $1.25 and carried about 30x leverage.
  - Followers reacted most to the riskiest calls.
  - The "finfluencer" generally got in at a lower price. Some contracts saw unusual activity before the alert.
  - Professors Brian Roseman (Oklahoma State) and Russell Jame (University of Kentucky) are quoted. Jame called it closer to gambling than investing.

  — [Bloomberg, Oct 7, 2026](https://www.bloomberg.com/news/articles/2026-10-07/a-30-options-pop-in-mere-minutes-shows-power-of-finfluencers); [TokenPost summary, Oct 10, 2026](https://www.tokenpost.com/news/investing/29610)
- **CFTC: CTA definition and exclusions.** 7 U.S.C. §1a(12)(A) covers anyone who, "for compensation or profit, engages in the business of advising others, either directly or through publications," about futures, security futures, swaps and similar instruments. §1a(12)(B) excludes:
  - news reporters, columnists and editors, lawyers, accountants and teachers;
  - "the publisher or producer of any print or electronic data of general and regular dissemination, including its employees."

  Under §1a(12)(C), these exclusions apply only if the advice is "solely incidental" to the person's business. — [7 U.S.C. 1a (Cornell LII)](https://www.law.cornell.edu/uscode/text/7/1a)
- **CFTC Reg. 4.14(a)(9).** A person is exempt from CTA registration if it does not engage in "(i) Directing client accounts; or (ii) Providing commodity trading advice based on, or tailored to, the commodity interest or cash market positions or other circumstances or characteristics of particular clients." — [17 CFR 4.14 (Cornell LII)](https://www.law.cornell.edu/cfr/text/17/4.14)
- **CFTC Reg. 4.14(a)(10).** A second exemption covers advisers with no more than 15 persons in the prior 12 months who do not "hold itself out generally to the public" as a CTA. — [17 CFR 4.14](https://www.law.cornell.edu/cfr/text/17/4.14)

### Inferences
- **Safe lane for the platform's own content.** These are likely inside the publisher exclusion and outside CTA status when produced the same way for every user:
  - prices, charts and news;
  - "most-discussed" and trending tickers;
  - sentiment gauges;
  - recaps on a regular schedule.

  Two conditions: the company has no position conflicts (adopt a staff personal-trading policy), and support staff and AI never answer "what should *I* do."
- **Why paid real-time alert rooms are the hardest case:**
  - "BTO XYZ 3-day calls @1.20, out at +30%" is timed to market activity, which strains *Lowe*'s "regular" prong.
  - Callers who hold or front-run the trade strain the "bona fide" (disinterested, not a tout) prong. The October 2026 study shows that pattern.
  - If the platform itself sells the subscription, takes a cut, ranks or "verifies" callers, or pushes their alerts, regulators could treat the platform as the publisher whose exclusion is at issue, not just the creator.
- **Personalization triggers that can turn the app into an adviser:**
  - AI or "For You" trade ideas based on a user's linked holdings, risk answers or account size;
  - chat assistants answering "should I buy X with my $5k?";
  - one-on-one direct-message coaching sold through the platform;
  - copy-trading or auto-execution of a creator's trades, which directs client accounts. This also fails Reg. 4.14(a)(9) for futures and crypto derivatives.
- **CTA exposure.** Crypto perpetual futures, futures, event contracts and other swaps fall in CFTC territory. A paid signal room on these is the core business, so the "solely incidental" publisher exclusion is doubtful. The realistic escape is 4.14(a)(9): impersonal advice that never directs accounts.
- **Practical design if creator rooms come later.** Treat these as counsel-gated design options:
  - require monetizing creators who give specific trade calls to be registered (RIA or investment adviser representative), or limit them to education;
  - enforce delayed or after-the-fact "trade journals" instead of live calls;
  - add mandatory position disclosure;
  - impose blackout windows around calls;
  - keep immutable timestamped logs.

### Gaps
- **Precedents not verified in this session (search budget exhausted):**
  - *SEC v. Terry's Tips* (D. Vt. 2006): options newsletter with an auto-trading feature; the publisher exclusion reportedly did not apply.
  - *SEC v. Park* ("Tokyo Joe," N.D. Ill. 2000): internet stock-tip subscription service plus scalping.
  - *CFTC v. Vartuli* (2d Cir. 2000): automatic trading-signal software.
- **Not verified:** state registration thresholds for small advisers (Advisers Act §203A, the $100M dividing line) and state-law publisher exclusions.
- **Not verified:** status of the SEC's 2023 predictive-data-analytics conflicts proposal, reportedly withdrawn in June 2025.
- **No case found:** I found no 2024–2026 SEC or state action charging a paid options-alert room purely with unregistered advice. Actions found were fraud and manipulation cases (see Q3).

---

## 3. User-generated content: Section 230, platform exposure for manipulation and pump-and-dumps run on the platform, recent SEC/DOJ cases, and how platforms responded

### Takeaway
Section 230 generally keeps a platform from being treated as the publisher of users' stock posts. Its limits:
- It has no effect on federal criminal law.
- It does not cover content the platform helped create or develop.
- In the Third Circuit, it does not cover algorithmic recommendations, which *Anderson v. TikTok* treats as the platform's own speech.

The flagship social-media pump-and-dump case is Atlas Trading, which ran on Twitter and Discord.
- December 2022: SEC civil case (about $100M) and a DOJ indictment ($114M).
- The district court dismissed the indictment.
- October 2, 2025: the Fifth Circuit reinstated it on a fraudulent-inducement theory, with no net loss to victims required.
- As of late-2025 reporting, no trial date had been set.

### Cited Findings
- **Section 230 text.**
  - §230(c)(1): "No provider or user of an interactive computer service shall be treated as the publisher or speaker of any information provided by another information content provider."
  - §230(c)(2)(A) protects good-faith removal of "objectionable" material.
  - §230(e)(1): nothing "shall be construed to impair the enforcement of ... any other Federal criminal statute."
  - §230(f)(3): an "information content provider" is anyone "responsible, in whole or in part, for the creation or development" of content.

  — [47 U.S.C. 230 (Cornell LII)](https://www.law.cornell.edu/uscode/text/47/230)
- ***Anderson v. TikTok*, No. 22-3061 (3d Cir., filed August 27, 2024).**
  - Section 230 immunizes platforms only when sued for third-party speech, "not ... for their own expressive activity."
  - TikTok's "For You Page" algorithm that recommended the Blackout Challenge video "was TikTok's own 'expressive activity' ... and thus its first-party speech."
  - The court reversed in part the §230 dismissal.

  — [Third Circuit opinion PDF](https://www2.ca3.uscourts.gov/opinarch/223061p.pdf)
- **SEC v. Atlas Trading defendants (December 14, 2022).** Eight individuals; about $100M in alleged profits.
  - Seven "promoted themselves as successful traders" on Twitter and in Discord stock-trading chatrooms.
  - They posted price targets or said they were buying, holding or adding, then sold without disclosing their plan to sell.
  - A podcast co-host was charged with aiding and abetting.
  - Relief sought: injunctions, disgorgement, penalties and a penny-stock bar.
  - The SEC warned that investors "should be wary of unsolicited advice they encounter online."

  — [SEC press release 2022-221](https://www.sec.gov/newsroom/press-releases/2022-221)
- **Parallel criminal case.** DOJ indicted eight men in a $114M scheme "orchestrated through social media." — [DOJ press release](https://www.justice.gov/opa/pr/eight-men-indicted-114-million-securities-fraud-scheme-orchestrated-through-social-media)
- **Press description of the defendants (search-result excerpt).** Coverage describes nearly 2 million combined followers and an Atlas Trading Discord with over 250,000 members. — [Yahoo Finance](https://finance.yahoo.com/news/appeals-court-revives-houston-traders-153715490.html)
- ***United States v. Constantinescu*, No. 24-20143 (5th Cir., October 2, 2025).**
  - The district court had dismissed under *Ciminelli*, viewing the scheme as depriving victims only of "valuable economic information."
  - The Fifth Circuit reversed. The indictment alleges fraudulent inducement: followers were tricked into parting with money to buy securities. Under *Kousisis* that theory is valid.
  - No net economic loss is required. The defendants' argument that they meant to profit rather than harm was "a distinction without a difference."

  — [FindLaw opinion](https://caselaw.findlaw.com/court/us-5th-circuit/117795982.html); [Quinn Emanuel via CLS Blue Sky](https://clsbluesky.law.columbia.edu/2025/10/16/quinn-emanuel-discusses-fifth-circuit-decision-reinstating-securities-fraud-indictment)
- **Status after remand (press reports).** The Houston Chronicle reports the case was revived and that no trial date had been set in either the criminal or the SEC case. It also reports that Constantinescu missed a February hearing, his lawyer said he had moved to Mexico, and he was accused of threatening prosecutors. — [Houston Chronicle (search-result summary)](https://www.houstonchronicle.com/news/houston-texas/crime/article/appeals-court-revive-finance-bro-case-21126328.php)
- **SEC v. Sabo (May 2023).** Francis Sabo ("Ricky Bobby") moderated a Discord stock-trading forum.
  - He recommended stocks, often saying he had bought or would hold them, then sold into the demand his promotions created.
  - He allegedly made over $1M.
  - He partially settled, with an injunction and monetary sanctions to be set later. The SDTX US Attorney filed criminal charges.

  — [Investment Executive](https://www.investmentexecutive.com/news/regulation/sec-charges-trading-chatroom-moderator/)
- **SEC v. Gauvin (December 10, 2025).** A Discord persona raised about $18.1M through a fund that falsely claimed double-digit monthly returns; about $6.3M was allegedly diverted. EDNY filed parallel criminal charges. The SEC flagged opportunities "promoted through social media or online communities." — [SEC press release 2025-141](https://www.sec.gov/newsroom/press-releases/2025-141-sec-charges-canadian-citizen-fraud-schemes-targeted-retail-investors-discord)
- **Discord Community Guidelines (updated August 29, 2025; effective September 29, 2025).** They prohibit using Discord to "promote, coordinate, or carry out financial scams" and say: "Do not engage in activities that fraudulently generate a profit at the expense of others." There is no explicit pump-and-dump or market-manipulation language. — [Discord Community Guidelines](https://discord.com/guidelines)

### Inferences
- **Where liability can reach a markets UGC app:**
  - Federal criminal exposure (§230(e)(1)) if insiders knowingly help coordinate pumps.
  - Loss of §230 if the app "develops" manipulative content: AI summaries of "what the chat is saying," auto-generated "conviction scores," headlines the app writes.
  - Algorithmic amplification of hot tickers, push notifications ("$XYZ +40%, 12k comments, join the room") and "verified caller" leaderboards. These may be the platform's own speech under *Anderson* (Third Circuit; other circuits differ).
  - Subpoenas and investigations: expect SEC/DOJ requests for chat logs, account identities and timestamps.
- **The fact pattern to design against is consistent.** Promoters post price targets or "buying/holding/adding," then sell into follower demand without disclosure (Atlas, Sabo, and the 2026 Discord options study).
- **Product controls that follow from those facts:**
  - mandatory position tags ("long / short / no position / will sell within X");
  - a ban on undisclosed compensation;
  - friction for low-float, OTC and microcap tickers when comment spikes are unusual;
  - limits on new accounts;
  - rate limits on "buy now" calls;
  - immutable post and edit history with timestamps.
- **Atlas is still live.** Creators with large followings may carry live criminal exposure, so verify and screen creators before paid or featured status.

### Gaps
- ***Universal Communication Systems v. Lycos* (1st Cir. 2007).** Reportedly held that §230 barred claims against a stock message board (Raging Bull) over users' posts about a stock. It is the closest securities-message-board precedent, but my fetch of the opinion failed, so it is unverified this session.
- **SEC civil case against the Atlas defendants.** Current status (stayed, settled, or ruled on) not found.
- **Platform responses.** I found no source showing Discord, X or Stocktwits changed policies specifically because of the Atlas case. Discord's current guidelines are generic anti-fraud rules.
- **Andrew Left/Citron case.** Outcome of the 2024 social-media-related short-report case not researched.

---

## 4. Paid promotion and touting: Securities Act §17(b), FTC endorsement rules, FINRA Rule 2210 and influencer guidance; disclosure duties for paid creators and creators who hold positions

### Takeaway
Three overlapping regimes apply.
- **§17(b) of the Securities Act.** Anyone who publicizes a security for consideration from an issuer, underwriter or dealer must disclose that they were paid and how much (Kardashian: $1.26M).
- **The FTC Act.** The 2024 Consumer Reviews and Testimonials Rule bans fake or AI-generated reviews and testimonials, reviews bought on condition of a particular sentiment, and buying or selling fake follower or view counts. It carries civil penalties.
- **FINRA Rule 2210.** When a broker-dealer pays creators, their posts are treated as the firm's communications. They need to be fair and balanced, approved, retained and supervised (M1).

No single federal rule makes an unregistered creator disclose personal positions. However, trading against one's own undisclosed recommendations is the core fact pattern in the fraud cases.

### Cited Findings
- **Securities Act §17(b).** It is unlawful "to publish, give publicity to, or circulate any notice, circular, advertisement, newspaper, article, letter" that "describes such security for a consideration received or to be received, directly or indirectly, from an issuer, underwriter, or dealer, without fully disclosing the receipt, whether past or prospective, of such consideration and the amount thereof." — [15 U.S.C. 77q (Cornell LII)](https://www.law.cornell.edu/uscode/text/15/77q)
- **SEC v. Kardashian (October 3, 2022).**
  - She was paid $250,000 for an Instagram post about EthereumMax EMAX tokens.
  - She settled for $1.26M: about $260,000 in disgorgement and interest plus a $1M penalty.
  - She agreed not to promote crypto asset securities for three years.
  - The SEC said investors are entitled to know whether publicity about a security is unbiased.

  — [SEC press release 2022-183](https://www.sec.gov/news/press-release/2022-183)
- **FTC Consumer Reviews and Testimonials Rule (announced August 14, 2024; 5-0 vote; effective 60 days after Federal Register publication).** It bans:
  - fake reviews and testimonials, including AI-generated ones;
  - paying for reviews conditioned on a particular sentiment;
  - undisclosed insider reviews;
  - company-controlled "independent" review sites;
  - review suppression;
  - selling or buying "fake indicators of social media influence," such as bot followers or views, used for commercial misrepresentation.

  The FTC can "seek civil penalties against knowing violators." — [FTC press release](https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials)
- **FINRA M1 Finance case.** The first FINRA case over influencer communications. Paid influencer posts were held to Rule 2210's fair-and-balanced standard. Pre-approval, retention and supervisory failures were sanctioned ($850,000). — [FINRA news release](https://www.finra.org/media-center/newsreleases/2024/finra-fines-m1-finance-850000-violations-regarding-use-social-media)
- **FINRA social media guidance.**
  - Third-party posts are generally not firm communications unless the firm has "adopted" them or become "entangled" in preparing them.
  - Firms may not link to third-party content they know or have reason to know is false or misleading.
  - Static content needs principal pre-approval. Interactive content is supervised like correspondence.
  - Business communications must be kept at least three years.
  - Key notices: Regulatory Notices 10-06, 11-39, 17-18 and 19-31; the 2023 influencer and customer-acquisition sweep update (Feb. 28, 2023); a "Social Media-Influenced Investing" report (Dec. 11, 2025); the 2026 Annual Regulatory Oversight Report (Dec. 9, 2025).

  — [FINRA Social Media key topic page](https://www.finra.org/rules-guidance/key-topics/social-media)
- **Proposed Rule 2210 change on projections.** SR-FINRA-2026-004 (filed February 20, 2026) would let members project performance or targeted returns in some circumstances; current Rule 2210 generally prohibits them. — [SEC notice of filing (PDF)](https://www.sec.gov/files/rules/sro/finra/2026/34-104877.pdf)
- **Unverified report on pre-use approval.** A compliance-vendor blog says FINRA Regulatory Notice 26-14 (July 2026) proposed replacing blanket pre-use approval with a risk-based standard. I did not find the notice itself. — [Sedric (vendor blog)](https://www.sedric.ai/blog/influencer-compliance)
- **Positions held by creators.** The Atlas and Sabo cases both turned on promoters saying they were "buying/holding/adding" while selling into follower demand. — [SEC 2022-221](https://www.sec.gov/newsroom/press-releases/2022-221); [Investment Executive on Sabo](https://www.investmentexecutive.com/news/regulation/sec-charges-trading-chatroom-moderator/)

### Inferences
- **Platform rules to adopt from day one:**
  - A compensated-promotion label on any post where the creator received anything of value. For securities, disclose payer and amount (§17(b)).
  - A flat ban on issuer, underwriter or dealer-paid promotion of specific securities, especially small caps and new IPOs. The compliance burden plus pump-and-dump risk is not worth it for a v1.
  - Position disclosure badges.
  - No buying or selling followers or engagement. The app's own growth tactics are covered too: no seeded fake accounts or AI "users" posting testimonials.
  - No "I made $X with Real for markets" testimonials unless genuine and typical-results-compliant. This last point is an inference; the Endorsement Guides were not fetched.
- **If a broker sponsors placements or creators on the app,** expect the broker to require:
  - pre-approval of sponsored content;
  - archiving of creator posts, and possibly comments the firm "adopts";
  - balanced risk disclosure, especially for options and margin;
  - FINRA-compliant performance claims.

  Contracts should allocate this burden explicitly.
- **Options promotion is the most sensitive category.** M1's margin misstatement was the cited example, and options communications carry extra broker-side requirements (not verified).

### Gaps
- **Not fetched:** the FTC Endorsement Guides (16 CFR Part 255, revised 2023) on material-connection disclosure.
- **Not verified:** the SEC Marketing Rule (Advisers Act Rule 206(4)-1) on RIAs paying promoters or using testimonials, and its January 15, 2026 FAQ update (seen only in a search result).
- **No rule found** requiring non-registered creators to disclose holdings. Scalping case law (*SEC v. Capital Gains Research Bureau*, 1963; *Zweig v. Hearst*, 9th Cir. 1979) not verified.
- **FINRA Regulatory Notice 26-14:** unverified.

---

## 5. Game mechanics: when do points, leaderboards, contests or price predictions become illegal gambling, sweepstakes or CFTC-regulated event contracts? Status of prediction markets in 2025–2026

### Takeaway
Free predictions with virtual points that have no cash value and no paid entry fall outside gambling, because there is no consideration and no prize. Apple's own rule describes a lottery as needing "consideration, chance, and a prize."

Adding money changes the regime:
- Paid entry or purchasable currency tied to prizes brings in state gambling and sweepstakes law and the app stores' real-money gaming rules.
- A money-settled "will NVDA close above $200?" contract is a swap. Tied to a single stock, it is a **security-based swap** under SEC jurisdiction.
- Sports and political event contracts are in active litigation and rulemaking: a circuit split, a pending cert petition, and CFTC proposals in June and October 2026.

Real-money predictions mean distributing a regulated exchange's contracts through a futures commission merchant (FCM) or introducing broker (IB) structure, not building them.

### Cited Findings
- **Apple Guideline 5.3.**
  - 5.3.1: "Sweepstakes and contests must be sponsored by the developer of the app."
  - 5.3.2: official rules must be in the app and state that Apple is not a sponsor.
  - 5.3.3: no in-app purchase of credit or currency used in real-money gaming.
  - 5.3.4: real-money gaming needs licensing and geo-restriction and must be free on the App Store; "Lottery apps must have consideration, chance, and a prize."

  Guideline 3.2.2(viii): "Apps that facilitate binary options trading are not permitted." The guidelines were last updated October 16, 2026. — [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- **Google Play real-money policy (search-result summaries).**
  - Real-money gambling, games and contests are generally prohibited unless licensed and approved by Google. Approved apps must be free, avoid in-app billing, and block minors and unauthorized locations.
  - Loyalty programs with real-world prizes are allowed with conditions: game apps must use fixed ratios and schedules (no chance-based rewards); non-game apps may run chance-based contests with disclosed odds and deadlines.
  - Enforcement of minor-blocking for these apps began January 28, 2026.
  - In October 2025 Google tightened rules on sweepstakes and dual-currency casino models.

  — [Google Play real-money gambling, games and contests policy](https://support.google.com/googleplay/android-developer/answer/9877032); [iGaming Expert, 2025](https://igamingexpert.com/news/business/google-sweepstake-policies-2025/)
- **CFTC rulemaking, part 1.**
  - February 4, 2026: the CFTC withdrew its June 2024 proposed ban on political and sports event contracts. This comes from search-result summaries; WilmerHale's alert says only that the 2024 amendments were "never adopted." — [TradeInformer](https://www.tradeinformer.com/regulations/cftc-event-contract-rules-prediction-markets-2026)
  - March 2026: ANPRM.
  - June 2026: NPRM amending Reg. 40.11 and adding Appendix F, with a three-step test (is it an event contract; does it "involve" gaming, unlawful activity, terrorism, assassination or war; is it contrary to the public interest). "Gaming" requires a recreational purpose, governing rules, and outcomes depending on luck, skill or athletic ability. Elections and awards are not gaming. Contracts on injuries, officiating or discrete plays are disfavored. Comments were due July 27, 2026. — [WilmerHale, June 18, 2026](https://www.wilmerhale.com/en/insights/client-alerts/20260618-10-takeaways-from-the-cftc-event-contracts-proposed-rulemaking)
- **CFTC rulemaking, part 2.** On October 9, 2026, the CFTC proposed to define "swap" expressly to include event contracts on sports, politics, culture and weather, with 30-day comments. Chairman Selig called them "commodity derivatives squarely within the CFTC's regulatory remit." — [CFTC press release 9310-26](https://www.cftc.gov/PressRoom/PressReleases/9310-26)
- ***KalshiEX v. Flaherty* (3d Cir. 2026).** A divided panel affirmed Kalshi's preliminary injunction against New Jersey. Sports event contracts on a designated contract market (DCM) are swaps, and the CEA preempts state gambling law (field and conflict preemption). Judge Roth dissented.

  The date conflicts: April 6, 2026 per Justia's docket URL; April 4 per Skadden. — [Justia](https://law.justia.com/cases/federal/appellate-courts/ca3/25-1922/25-1922-2026-04-06.html); [Skadden](https://www.skadden.com/insights/publications/2026/04/third-circuit-affirms-kalshis-preliminary-injunction)
- **Other circuits (as of October 8, 2026).**
  - Ninth Circuit (August 28, 2026): Nevada's gaming laws apply; Kalshi's injunction stays dissolved. The CFTC's existing gaming-contract prohibition was one basis, and proposed rule changes have no legal effect yet.
  - Ninth Circuit (September 2026): tribes are likely to succeed on Indian Gaming Regulatory Act claims.
  - Sixth Circuit (September 25, 2026): upheld denial of an injunction for Ohio and vacated Tennessee's. The CEA would not preempt state law even if the contracts are swaps.
  - Fourth Circuit (Maryland): argued May 2026, undecided. Second Circuit (New York): pending.

  — [Yogonet, Oct 8, 2026](https://www.yogonet.com/international/news/2026/10/08/126758-gaming-regulators-urge-us-supreme-court-to-hear-kalshi-case-decision-could-come-by-june-2027)
- **Supreme Court posture.** New Jersey petitioned for cert in September 2026. Robinhood and Crypto.com asked the Court to review their Ninth Circuit loss to Nevada. Kalshi sought rehearing en banc in the Ninth Circuit. Attorney Daniel Wallach's best case is a decision by June 2027; otherwise likely 2028. — [Yogonet](https://www.yogonet.com/international/news/2026/10/08/126758-gaming-regulators-urge-us-supreme-court-to-hear-kalshi-case-decision-could-come-by-june-2027)
- **Utah (secondary source).** A federal judge reportedly held on August 4, 2026 that federal law does not preempt Utah's anti-gambling laws as applied to Kalshi sports contracts. — [OddsShopper](https://www.oddsshopper.com/articles/prediction-markets/where-is-kalshi-legal)
- **Polymarket US.**
  - Polymarket bought QCEX, a CFTC-registered exchange, for $112M and got a CFTC no-action letter in September 2025.
  - The CFTC issued an Amended Order of Designation in November 2025 for an intermediated model: US users access markets through registered FCMs that handle KYC and custody.
  - The US app rolled out by waitlist in December 2025, starting with sports.
  - Reports conflict on whether direct onboarding has since been approved.

  — [Bitcoin Magazine](https://bitcoinmagazine.com/markets/polymarket-rolls-out-us-app); [pm.wiki](https://pm.wiki/uk/projects/polymarket-us); [MarketsMedia](https://www.marketsmedia.com/polymarket-receives-cftc-approval/); [Decrypt](https://decrypt.co/350003/polymarket-set-us-return-following-approval-cftc); [Unlock BC](https://www.unlock-bc.com/en/polymarket-seeks-cftc-approval-for-us-expansion)
- **Security-based swap definition.** Exchange Act §3(a)(68) covers swaps based on "a single security or loan," "a narrow-based security index," or "the occurrence, nonoccurrence, or extent of the occurrence of an event relating to a single issuer of a security ... provided that such event directly affects the financial statements, financial condition, or financial obligations of the issuer." — [15 U.S.C. 78c (Cornell LII)](https://www.law.cornell.edu/uscode/text/15/78c)
- **Introducing broker definition.** 7 U.S.C. §1a(31): a person who "solicits or accepts orders" for futures, security futures or swaps (among others) and does not take customer money to margin trades. — [7 U.S.C. 1a (Cornell LII)](https://www.law.cornell.edu/uscode/text/7/1a)

### Inferences
- **v1 safe lane.**
  - "Calls" or predictions such as "AAPL green or red by close?" or "beat or miss earnings?", with free entry, points that have no cash value and can't be redeemed or transferred, and leaderboards, badges and streaks.
  - No purchasable currency that can be spent on predictions. The dual-currency sweepstakes model is what states and Google are cracking down on.
  - If prizes are ever offered: a developer-sponsored, no-purchase-necessary sweepstakes with official rules and a free entry method, after counsel review.
- **Paid-entry stock-picking contests.** Skill versus chance is decided state by state; avoid without counsel.
- **Money-settled price predictions:**
  - on a single stock or narrow index: a security-based swap or binary option, SEC territory, and banned by Apple;
  - on broad indices, rates, CPI or crypto: CFTC swaps that must trade on a DCM.

  Either way, the realistic path is partnering with Kalshi, Polymarket US or a broker-run venue. The app would likely need IB status, or a pure referral relationship structured by counsel, because "soliciting" orders for compensation is the IB trigger.
- **Litigation risk is concentrated in sports contracts.** With the Sixth and Ninth Circuits siding with states, embedding sports-style contracts carries state gaming-law risk in those circuits. Economic and financial event contracts appear less contested (inference; the cases are about sports).
- **"Predict the next candle."** As a free points game it is a game. Paid, it is functionally a binary option.

### Gaps
- **Not verified:**
  - California AB 831 (sweepstakes-casino ban; the legislature site returned 403);
  - state sweepstakes registration and bonding rules (e.g., NY, FL);
  - Massachusetts' state-court action against Kalshi.
- **No source found** on whether affiliate-style referrals to a DCM require CFTC/NFA IB registration.
- **No source found** on whether any US DCM lists single-stock-linked event contracts.
- **The Real sports app's own prediction mechanics** were not researched.

---

## 6. Crypto content and features: token promotion rules, and the 2025–2026 federal framework (GENIUS Act, market-structure legislation)

### Takeaway
Showing crypto prices and hosting chat is not itself a regulated activity. The legal risk is in:
- **Promotion:** paid token shills. §17(b) applies if the token is a "digital security"; the FTC Act and fraud law apply regardless.
- **Money-handling features:** custody, swaps, stablecoins, "earn crypto" rewards. These bring in the GENIUS Act, state money-transmission and virtual-currency licensing, and Apple's crypto rules.

Federal market-structure legislation (the CLARITY Act) passed the House in July 2025 but stalled after a failed Senate cloture vote on September 15, 2026. In the meantime, regulators are working from a March 2026 joint SEC/CFTC interpretation, an SEC proposal from August 2026, and a CFTC rule now at OIRA.

### Cited Findings
- **GENIUS Act.**
  - Signed July 18, 2025 (Senate 68-30; House 308-122).
  - Only permitted issuers may issue payment stablecoins in the US.
  - Digital asset service providers may not offer or sell non-permitted payment stablecoins to US persons.
  - Issuers may not pay interest or yield.
  - Effective at the earlier of 18 months after enactment or 120 days after final regulations.

  — [Latham & Watkins US Crypto Policy Tracker](https://www.lw.com/en/us-crypto-policy-tracker/legislative-developments)
- **CLARITY Act (H.R. 3633), timeline.**
  - July 17, 2025: passed the House 294-134.
  - January 29, 2026: Senate Agriculture advanced its companion bill 12-11 on a party-line vote.
  - May 14, 2026: Senate Banking advanced its version 15-9.
  - Core design: CFTC "exclusive jurisdiction" over digital-commodity spot markets, and a registration regime for digital-commodity exchanges, brokers and dealers.

  — [Latham tracker](https://www.lw.com/en/us-crypto-policy-tracker/legislative-developments)
- **September 15, 2026 cloture failure.** The Senate failed cloture on the motion to proceed. Orrick reports 49–50; CNBC is summarized as 50 for and 49 against (conflict). Either way it was far short of 60.
  - Sticking points: ethics rules for officials' crypto holdings, and stablecoin yield.
  - Sen. Tillis voted no to preserve a motion to reconsider.
  - Passage this Congress is "widely viewed as unlikely."

  — [Orrick, Oct 2026](https://www.orrick.com/en/Insights/2026/10/The-CLARITY-Act-Stalls-in-the-Senate-Whats-Next-for-Digital-Asset-Regulation); [CNBC, Sept 15, 2026](https://www.cnbc.com/2026/09/15/senate-cloture-vote-on-clarity-act-fails-dealing-regulatory-setback-to-crypto-industry.html)
- **Interim regime.**
  - March 2026 SEC/CFTC joint interpretation sets out five categories: digital commodities, digital collectibles, digital tools, stablecoins and digital securities. The first three are not securities, but they can still be sold in investment-contract transactions.
  - August 18, 2026: the SEC proposed "Regulation Crypto Assets" (offering exemptions, an investment-contract safe harbor, state preemption for exempt offerings). Comments are due October 20, 2026.
  - September 17, 2026: the CFTC sent its crypto-market rule (RIN 3038-AF80) to OIRA.
  - State money-transmitter, virtual-currency licensing and consumer-protection laws still apply, especially to spot trading and custody.

  — [Orrick](https://www.orrick.com/en/Insights/2026/10/The-CLARITY-Act-Stalls-in-the-Senate-Whats-Next-for-Digital-Asset-Regulation)
- **SEC staff meme coin statement (February 27, 2025).** Typical meme coins are "akin to collectibles," and transactions in them do not involve securities offerings. This is staff guidance with no legal force. Fraud "may still be prosecuted" by other federal or state agencies. — [SEC Division of Corporation Finance statement](https://www.sec.gov/newsroom/speeches-statements/staff-statement-meme-coins)
- **Kardashian.** The touting charge involved a token treated as a crypto asset security. — [SEC 2022-183](https://www.sec.gov/news/press-release/2022-183)
- **Apple Guideline 3.1.5.**
  - Exchanges are allowed only with licensing.
  - Apps facilitating crypto futures or crypto-securities trading "must come from established banks, securities firms, futures commission merchants ('FCM'), or other approved financial institutions."
  - Crypto apps "may not offer currency for completing tasks."

  — [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)

### Inferences
- **Safe lane:** crypto prices, charts, news and chat rooms, alongside stocks.
- **Avoid in v1:**
  - payments from token projects (cash or tokens) for placement or creator promotion;
  - a native token, or points that convert to tokens or crypto (possible security, money-transmission or Apple 3.1.5(v) problems);
  - wallets, custody or swaps;
  - stablecoin "yield" displays presented as an offering.
- **Crypto derivatives signals.** Signals on perps and futures fall under the CTA analysis in Q2. Crypto event contracts fall under the DCM/IB analysis in Q5.
- **Low chance of near-term federal clarity.** A new statute is unlikely before 2027, so the app should assume today's patchwork (SEC taxonomy, CFTC anti-fraud, state law) persists.

### Gaps
- **Not verified:**
  - CFTC anti-manipulation authority over spot crypto (CEA §6(c)(1) / Rule 180.1);
  - recent DOJ crypto pump-and-dump stings (e.g., the October 2024 "Operation Token Mirrors").
- **Not found:** GENIUS Act implementing-regulation status.

---

## 7. App Store and Google Play policies for finance and UGC apps (moderation, reporting, blocking, age ratings); privacy obligations (CCPA, GLBA if handling brokerage data); age limits for minors

### Takeaway
Both stores require UGC apps to:
- filter objectionable content;
- let users report content and block abusive users;
- publish contact information (Apple);
- make users accept terms before posting and run "robust, effective, and ongoing" moderation (Google).

Apple-specific rules:
- Paid in-app digital content, including creator subscriptions, must use in-app purchase, except that US-storefront apps may link out.
- Creator apps need an age-restriction mechanism based on "verified or declared age."
- Trading features "should be submitted by the financial institution performing such services."

Privacy and safety obligations:
- CCPA once thresholds are met.
- GLBA via the FTC Safeguards Rule if the app becomes an "investment advisory company" or "finder."
- COPPA if users under 13 are allowed.
- A TAKE IT DOWN Act notice-and-removal process for intimate images, due May 19, 2026 for UGC platforms.

An 18+ policy is the simplest stance.

### Cited Findings
- **Apple 1.2 (user-generated content).** Apps must include "A method for filtering objectionable material," "A mechanism to report offensive content and timely responses," "The ability to block abusive users," and "Published contact information." — [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- **Apple 1.2.1(a) (creator content).** Creator apps must let users identify content above the app's age rating and "use an age restriction mechanism based on verified or declared age." — [Apple](https://developer.apple.com/app-store/review/guidelines/)
- **Apple 3.1.1 (in-app purchase).**
  - Unlocking "subscriptions ... access to premium content" requires in-app purchase.
  - Tipping digital content providers may use in-app purchase currencies.
  - 3.1.1(a): link-out entitlements "are not required for developers to include buttons, external links, or other calls to action in their United States storefront apps."
  - 3.1.2: subscriptions must last at least seven days.

  — [Apple](https://developer.apple.com/app-store/review/guidelines/)
- **Apple 3.2.1(viii), 3.2.2(viii) and 3.1.5.** These cover trading apps, binary options and crypto (quoted in Q1, Q5 and Q6). The guidelines were last updated October 16, 2026. — [Apple](https://developer.apple.com/app-store/review/guidelines/)
- **Google Play UGC policy.**
  - Apps must "Require users accept the app's terms of use and/or user policy before users can create or upload UGC."
  - They must "implement robust, effective, and ongoing UGC moderation."
  - They must provide "an in-app system for reporting and blocking objectionable UGC and users."
  - They must "Provide safeguards to prevent in-app monetization from encouraging objectionable user behavior."

  — [Google Play UGC policy](https://support.google.com/googleplay/android-developer/answer/9876937)
- **CCPA thresholds and rights.** The law applies to for-profit businesses with:
  - gross annual revenue over $25M, as shown on the AG page with no inflation-adjusted figure; or
  - buying, selling or sharing personal information of 100,000+ California residents or households; or
  - 50%+ of revenue from selling personal information.

  Rights: to know, delete, opt out (including global privacy control), correct, limit use of sensitive data, and non-discrimination. Page updated August 28, 2026. — [California AG CCPA page](https://oag.ca.gov/privacy/ccpa)
- **FTC Safeguards Rule (16 CFR 314.2).** A "financial institution" is one significantly engaged in financial activities. Listed examples include "an investment advisory company" and "a finder" that brings buyers and sellers together. — [16 CFR 314.2 (Cornell LII)](https://www.law.cornell.edu/cfr/text/16/314.2)
- **COPPA amendments (finalized January 16, 2025).**
  - Separate verifiable parental consent before disclosing children's data to third parties, including for targeted ads.
  - Data kept only as long as "reasonably necessary."
  - Biometric and government identifiers added to "personal information."
  - Effective 60 days after Federal Register publication, with one year to comply.

  — [FTC press release](https://www.ftc.gov/news-events/news/press-releases/2025/01/ftc-finalizes-changes-childrens-privacy-rule-limiting-companies-ability-monetize-kids-data)
- **TAKE IT DOWN Act (Pub. L. 119-12, enacted May 19, 2025).**
  - Covered platforms include public sites and apps that "primarily provide a forum for user-generated content."
  - They must set up a notice-and-removal process with clear notice by May 19, 2026.
  - They must remove reported nonconsensual intimate images within 48 hours and make reasonable efforts on known copies.
  - The FTC enforces non-compliance as an unfair or deceptive practice.

  — [47 U.S.C. 223a (Cornell LII)](https://www.law.cornell.edu/uscode/text/47/223a)
- **Google minor-blocking (search-result summary).** Google Play requires apps with real-money gambling, games or contests to block minors using Play Console tools; enforcement began January 28, 2026. — [Google Play policy](https://support.google.com/googleplay/android-developer/answer/9877032)

### Inferences
- **Creator subscriptions on iOS.** They must use in-app purchase, or a US-storefront external link. This affects creator revenue-share math (fee rates not verified this session).
- **App Store risk by integration level.** A pure deep-link app is probably not "used for financial trading" under 3.2.1(viii). Embedded trading likely needs partner involvement and licensing documentation at review (inference).
- **GLBA scope.** It is unclear whether read-only brokerage linking alone makes the app a GLBA "financial institution." Adding adviser or "finder" functions would. Plan for Safeguards-Rule-grade security (risk assessment, encryption, MFA, vendor oversight) before linking accounts.
- **18+ simplifies everything:**
  - avoids COPPA;
  - lines up with brokerage and prediction-market partners (adults only);
  - meets Google's minor-blocking for any contest features;
  - eases Apple creator-content age gating;
  - reduces exposure to state minor social-media laws (not verified).

### Gaps
- **Not verified:** Apple's 2025 age-rating tiers (13+/16+/18+) and its Declared Age Range API.
- **Not verified:** state app-store age-verification laws (Utah, Texas SB 2420, Louisiana) and any injunctions against them.
- **Possible conflict, not verified:** the CCPA inflation-adjusted revenue threshold reportedly rose above $25M from 2025, but the AG page shows $25M.
- **Not verified:** the FTC Safeguards Rule's 500-consumer, 30-day breach-notice requirement, and the 2024 Reg S-P amendments (which apply to broker partners).
- **Not found:** any Apple or Google rule mentioning prediction markets specifically.

---

## 8. Minimum compliance setup for v1 (terms of service, disclaimers, moderation, content policies, record-keeping), and which features should wait until counsel is engaged

### Takeaway
A v1 limited to licensed data, news, UGC commentary and free points-based predictions can run on a standard consumer-social compliance stack plus finance-specific content rules. That means no trading, no broker or issuer money, no paid creator rooms and no personalized AI.

Most of the legal exposure sits in features that should wait for securities and derivatives counsel:
- embedded trading or broker revenue deals;
- paid alert rooms and creator monetization;
- AI personalized ideas and copy-trading;
- real-money predictions;
- crypto token deals.

### Cited Findings
- **App store UGC baselines.** Filtering, reporting, blocking and contact info (Apple 1.2); terms acceptance before posting, robust ongoing moderation and in-app reporting and blocking (Google). — [Apple](https://developer.apple.com/app-store/review/guidelines/); [Google Play UGC](https://support.google.com/googleplay/android-developer/answer/9876937)
- **Good-faith moderation is protected.** §230(c)(2)(A) protects removing "objectionable" material, but nothing in §230 impairs federal criminal enforcement (§230(e)(1)). — [47 U.S.C. 230](https://www.law.cornell.edu/uscode/text/47/230)
- **TAKE IT DOWN process.** Required by May 19, 2026, with 48-hour removal. — [47 U.S.C. 223a](https://www.law.cornell.edu/uscode/text/47/223a)
- **DMCA §512(c) safe harbor.** Requires designating an agent with the Copyright Office and on the site (name, address, phone, email), expeditious takedown on notice, and a repeat-infringer termination policy (§512(i)). — [17 U.S.C. 512 (Cornell LII)](https://www.law.cornell.edu/uscode/text/17/512)
- **Platform's own content.** The *Lowe* conditions keep platform content outside adviser status: bona fide and disinterested, impersonal, regular and not timed to market activity. — [Lowe v. SEC](https://www.law.cornell.edu/supremecourt/text/472/181)
- **Paid-post disclosure (§17(b)) and FTC bans** on fake reviews and testimonials and on fake social-influence metrics. — [15 U.S.C. 77q](https://www.law.cornell.edu/uscode/text/15/77q); [FTC](https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials)
- **Broker-partner recordkeeping standard.** If a broker partner adopts or is entangled in content, FINRA expects at least three-year retention and principal supervision. — [FINRA Social Media page](https://www.finra.org/rules-guidance/key-topics/social-media)
- **No AI-washing.** Do not market AI features as an "AI advisor" or overstate capabilities. — [SEC 2024-36](https://www.sec.gov/news/press-release/2024-36)
- **Privacy:** CCPA thresholds and rights [CA AG](https://oag.ca.gov/privacy/ccpa); COPPA if under 13 [FTC](https://www.ftc.gov/news-events/news/press-releases/2025/01/ftc-finalizes-changes-childrens-privacy-rule-limiting-companies-ability-monetize-kids-data).

### Inferences
**v1 compliance checklist** (synthesized from the sources above; have a startup lawyer review it before launch):
1. **Terms of service:**
   - "information/entertainment only, not investment advice, no recommendation to buy or sell"; no fiduciary relationship;
   - a data-delay and accuracy disclaimer (the data-licensing terms come from the other workstream);
   - eligibility 18+;
   - a license to user content;
   - prohibited conduct: manipulation, coordinated pumps, undisclosed compensation, false performance claims, impersonation, spam, selling signals in DMs, nonconsensual intimate images;
   - account termination rights;
   - dispute-resolution terms (have counsel draft).
2. **Finance-specific community guidelines:**
   - position disclosure;
   - compensation disclosure (§17(b) format: payer and amount);
   - no issuer-paid promotion;
   - extra rules for OTC, low-float and microcap names;
   - no "guaranteed" returns;
   - no solicitation for off-platform paid groups (or a strict policy on it);
   - no screenshots of fabricated P&L.
3. **Moderation stack:**
   - keyword and ticker filters;
   - report, block and mute;
   - a priority queue for tickers with unusual comment or price spikes;
   - limits on new accounts;
   - a ban-evasion process;
   - a TAKE IT DOWN intake form and 48-hour service level;
   - a DMCA agent.
4. **Records and legal process:**
   - retain posts, edits, deletions, moderation actions, account and IP metadata, and precise timestamps (to rebuild pump timelines and answer SEC/DOJ subpoenas);
   - a legal-hold procedure;
   - a law-enforcement request policy.
5. **Rules for the company's own content and staff:**
   - written personal-trading policy (e.g., no trading tickers the company features within a set window);
   - conflict disclosure;
   - regular, impersonal editorial formats;
   - support staff and any AI barred from individualized advice;
   - no "AI advisor" marketing.
6. **Privacy and security:**
   - privacy policy (CCPA-ready);
   - collect as little personal data as possible;
   - no brokerage account linking in v1;
   - age gate at 18+;
   - vendor data agreements.
7. **Marketing:**
   - no fake or seeded reviews, users or engagement;
   - FTC-compliant influencer disclosures for anyone the company pays.
8. **Predictions:**
   - free entry, points with no cash value and no redemption, no purchasable currency;
   - official rules and developer sponsorship if prizes are ever added.

**Features that need counsel first, with the trigger for each:**

| Feature | Legal trigger | Source |
|---|---|---|
| Any per-trade, per-contract or volume-based revenue from brokers; order entry or routing | Broker-dealer registration (Exchange Act §15(a)); FINRA 2040 bars brokers from paying unregistered persons who should register | Q1 |
| Flat-fee broker affiliate deals | Not registration, but FINRA 2210 duties flow down via the broker (M1) | Q1, Q4 |
| Paid real-time alert rooms, creator subscriptions with trade calls, "verified caller" rankings | *Lowe* prongs at risk (timed to market, not disinterested); possible IA status for creators or the platform; CTA for futures and crypto derivatives | Q2 |
| AI "for you" ideas from user holdings; portfolio Q&A; copy or auto-trading | Advice "attuned to any specific portfolio" makes the app an investment adviser; directing accounts fails CTA 4.14(a)(9) | Q2 |
| Sponsored posts from issuers or token projects | §17(b) disclosure; manipulation risk; Kardashian | Q4, Q6 |
| Real-money predictions or prizes | State gambling and sweepstakes law; Apple 5.3 and Google real-money policy; single-stock contracts are security-based swaps; event contracts need a DCM plus FCM/IB; sports contracts in circuit-split litigation | Q5 |
| Wallets, swaps, tokens or "earn crypto" | GENIUS Act; state money transmission; Apple 3.1.5 | Q6 |
| Brokerage account linking | GLBA/FTC Safeguards analysis; CCPA; partner data-sharing scrutiny | Q7 |

### Gaps
- **No benchmarks found** for the cost of counsel or of a fintech compliance program.
- **State-level items not verified:**
  - state investment-adviser and "finfluencer" initiatives (e.g., NASAA);
  - state minor social-media laws;
  - state sweepstakes registration;
  - state money transmission for any payment flows, including creator payouts through the platform. Creator payouts may raise money-transmission questions unless handled through a payment processor's marketplace product (not verified).
