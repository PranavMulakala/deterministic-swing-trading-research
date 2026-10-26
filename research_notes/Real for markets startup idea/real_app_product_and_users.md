# Real (the social sports-data app): feature teardown, UX, and user sentiment, as of October 18, 2026

Scope and method: I used Real's store listings (fetched Oct 18, 2026), Real's public GitBook docs (docs.realapp.link, including a dated changelog running from Jan 2021 to Oct 17, 2026), the 500 most recent US App Store reviews (Apr 11 to Oct 16, 2026, pulled from Apple's public review feed), press pieces from 2022 to 2026, and competitor App Store metadata. Founders, funding, business model, and technology appear only in passing because another researcher covers them. Review content is paraphrased. The only direct quote is the founders' two-word framing in Q1. The WebSearch budget ran out partway through, so Reddit, X, and TikTok threads could not be retrieved; see the Gaps under Q4.

---

## 1. Which app is this exactly? (store names, developer, website, and how it was confirmed)

### Takeaway
The app is **"Real - Sports"** (App Store subtitle "Social sports data"), published by **Real Vault** (listed as Real Vault, Inc. on the App Store and Real Vault, LLC on Google Play, based in Chicago). The website is **realapp.com** (realapp.link redirects there), the docs and help center are at **docs.realapp.link**, and the web app is at realapp.com and realsports.io. It matches the founder's description: each play-by-play entry has its own comment section with emoji reactions, and the company and press both pitch it on speed (often ahead of TV). Press refers to it as "Real," "Real App," or "Real Sports."

### Cited Findings
**Store identity (verified)**
- App Store: "Real - Sports", subtitle "Social sports data". Seller is Real Vault, Inc. Free with in-app purchases. 4.8 stars from 26K ratings (26,211 in Apple's lookup API on Oct 18, 2026), ranked #24 in Sports (Top Free). "Designed for iPhone": iOS 16+, also runs on Apple-silicon Macs and Vision Pro, no iPad version. Size 39.1 MB. English only. — [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162); [iTunes lookup API](https://itunes.apple.com/lookup?id=1514546162&country=us)
- First App Store release Mar 2, 2021. Current version 10.40 was released Oct 18, 2026 at 03:36 UTC (evening of Oct 17 in the US). — [iTunes lookup API](https://itunes.apple.com/lookup?id=1514546162&country=us)
- Store description in brief: a new way to discuss live plays and games, check scores, and follow players and teams, plus predict and compete during live sports. — [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162)
- The App Store copyright line reads Real Vault, LLC (2021) while the seller is Real Vault, Inc. The same developer also publishes "The Rose League" (a Bachelor-franchise fantasy game). — [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162)
- Google Play: "Real - Sports" by Real Vault, package id `vg.real`. About-the-developer lists Real Vault, LLC, Chicago, IL, support@real.vg. 4.3 stars, about 4.55K reviews, 500K+ downloads, rated "Everyone" with a "Users Interact" flag, last updated Oct 16, 2026. — [Google Play listing](https://play.google.com/store/apps/details?id=vg.real&hl=en_US&gl=US)
- The iOS bundle id `vg.real` also shows up in a third-party app index URL (seen in search results, not fetched). — [Appaloosa Scout](https://scout.appaloosa.io/apps/ios/vg.real/10.32)

**Web, docs, community (verified)**
- realapp.link returns a 301 redirect to realapp.com. — [realapp.link](https://www.realapp.link)
- Docs list the web app at realapp.com and realsports.io as a Real Pro feature. — [Real Pro doc](https://docs.realapp.link/basics/real-pro.md); [FAQs](https://docs.realapp.link/basics/faqs.md)
- Official Discord: discord.gg/realapp. — [Collect: Start doc](https://docs.realapp.link/collect/start.md)
- Real calls itself a social sports data platform. It aggregates live contextual data for every play, player performance, team, and game, and offers notifications, very fast updates, comments, polls, leaderboards, and collecting. — [FAQs](https://docs.realapp.link/basics/faqs.md); [Welcome](https://docs.realapp.link/welcome.md)
- Stated mission: build the best live-event interaction platform, centered on sports data rather than media opinion, and avoiding the subjectivity of legacy-media sports apps. — [Welcome](https://docs.realapp.link/welcome.md); [Overview](https://docs.realapp.link/about/overview.md)

**Press confirmation that this is the per-play-comment app**
- Front Office Sports (Apr 13, 2026) calls Real a social box score app. Each new play-by-play entry gets a comment section, and fans respond with emojis the way they would on Slack or Discord. The founders describe the concept as "inverting Twitter": the data point comes first and fans react to it. — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- FanDuel's partner story (Sep 10, 2026) says every play, performance, and box score can become its own conversation. A co-founder calls Real the community layer of sports data. — [FanDuel news](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)

**In passing: founders and company (covered in depth by another researcher)**
- Co-founders are brothers John and Louis Antonelli. The idea dates to a 4 a.m. text in Feb 2020 about reacting to an NBA three with a Drake emoji. Louis was a founding engineer at Guilded (acquired by Roblox). John built the @bball Instagram account. — [FanDuel news](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel); [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/); [Overview doc](https://docs.realapp.link/about/overview.md)
- The Chernin Group led a minority round (amount undisclosed, reported Apr 2026). NBA players Tyrese Haliburton, Grayson Allen, and Tre Jones are among the investors. — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- On Sep 10, 2026, FanDuel became Real's first official and exclusive sportsbook and prediction-market partner. — [FanDuel news](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel); [Yogonet](https://www.yogonet.com/international/news/2026/09/11/126364-real-app-names-fanduel-exclusive-sportsbook-and-prediction-market-partner)

**Scale over time (self-reported or partner-reported; figures conflict)**
- 2021: about 1,000 unique users engaging with an NBA game. — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- Mid-2022: 115K+ MAU near the end of the NBA Finals, averaging about 6 minutes a day. — [GrepBeat, Aug 18, 2022](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
- Apr 2023: about 170K MAU and more than 3M comments in the prior 30 days. — [BetCrunch, Apr 25, 2023](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
- Undated older job post: 950K+ monthly active members across 7 main US leagues. — [Full-Stack Engineer job post](https://docs.realapp.link/jobs/full-stack-engineer-real.md)
- Apr 2026: 700K to 900K DAU and 1.3M MAU, per the founders. About 220K unique users were on the app during Bam Adebayo's 83-point game (March 2026). 50M push notifications go out per day. — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- Undated job post (numbers match 2026): 1.3M+ MAU, 900K+ DAU, over a million people a week. — [Product Designer job post](https://docs.realapp.link/jobs/product-designer.md)
- Sep to Oct 2026: more than 1.5M MAU, more than 1M DAU on the biggest days, over 70% of monthly users return on major game days, more than 250K concurrent users during close games, and nearly 30% of users comment or react. — [Flutter blog, Oct 6, 2026](https://flutter.com/news-media/blogs/how-fanduel-is-bringing-betting-into-the-social-conversation/); [FanDuel news](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel); [Yogonet](https://www.yogonet.com/international/news/2026/09/11/126364-real-app-names-fanduel-exclusive-sportsbook-and-prediction-market-partner)

### Inferences
- The founder's "near-millisecond" impression is not backed by any source. Real's own claims and user tests put it at seconds, and it often beats TV because broadcasts carry a delay (details in Q2a). The real product insight is "faster than the broadcast," not millisecond latency.
- Android shows only 500K+ downloads and about 4.5K reviews, against roughly 26K iOS ratings and 1.3M to 1.5M MAU. That points to an iOS-heavy user base (inference, not verified).

### Gaps
- I could not list the other apps named "Real" (search budget exhausted). The identification rests on the store listing, the `vg.real` package id, the docs, and press descriptions all matching.
- How Real Vault, Inc. and Real Vault, LLC relate is not explained in any source I found.

---

## 2. What is the complete feature set?

### Takeaway
Underneath, Real is a real-time play-by-play scoreboard. **Every play, performance, game, and news "report" is a social object**: you can react with emojis, comment, upvote or downvote, share, save, or collect it as a card. An algorithmic **"Real rating"** scores every play and performance, which decides what surfaces. Layered on top is a large gamified economy: **karma** (free social points from polls and activity), **Rax** (virtual currency you can buy or earn), cards and packs, leaderboards, badges, daily drafts and lineups, a Rax prediction market (since Dec 2025), the "Arena" fantasy game (Oct 17, 2026), and an AI stats assistant, Real Bot (Oct 17, 2026). **Real Pro** ($7.99 a month) unlocks web access, predictions, per-play notifications, and stat trackers. Since Sep 2026, FanDuel odds and markets also sit inside game feeds.

### Cited Findings

#### 2a. Live scores, play-by-play, and speed/latency
- Real describes its updates as lightning fast and calls itself the fastest way to check scores, explore stats, and follow players, teams, and tags. — [Welcome](https://docs.realapp.link/welcome.md); [Overview](https://docs.realapp.link/about/overview.md)
- **Founder claims:** FOS (Apr 2026) reports the founders saw latency in how sports data was being delivered. It says Real's feed often runs a minute or two ahead of the action on TV and that data arrives almost instantly. — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- In 2023 a co-founder said Real is usually faster than TV for every sport it covers, and that bettors often see plays on Real minutes before social media does. A delay setting lets viewers sync the feed to their broadcast. — [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
- In 2022 the founders said play-by-play data was real-time enough that it reaches your phone instantly while you watch on TV. — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
- **Speed-related changelog entries:**
  - May 2021: rebuilt supercharged feed with faster, more accurate updates.
  - Mar 2022: speed upgrade for college basketball scores and plays.
  - **May 2022: "slowmode" setting delays the feed 5 to 120 seconds to match TV or a stream.** This implicitly concedes the feed can run up to 2 minutes ahead.
  - Aug 2022: per-game notification mute for people watching on TV.
  - Oct 2024: faster NFL feed that shows developing plays as "In progress," with stats and penalties updating live.
  - Nov 2024: much faster soccer updates.
  - Oct 2025: NHL moved fully to an official data source.
  - [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Data-quality gating:** Real adds a sport only when real-time stats and good play-by-play data exist. College basketball outside the Power 5 is excluded for that reason (except March Madness). The app flags games with unreliable data (since Oct 2022). — [Sports doc](https://docs.realapp.link/basics/sports.md); [FAQs](https://docs.realapp.link/basics/faqs.md); [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Context attached to each play:**
  - Basketball: point streaks (e.g., N straight points), team runs, team hot and cold shooting streaks, time since the last field goal or three, free throws pending, fouls, challenges, replays, a spread indicator showing who is covering, and possession and bonus indicators.
  - Football: down and distance, NFL live injury statuses (Oct 2026).
  - All major sports: career milestones on plays.
  - "Live situational insights" for MLB (Aug 2026) and NFL/CFB (Aug 2026).
  - [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Real rating:** an algorithm scores each play and performance on objective factors: how close the game is, game time, stat volume, active streaks, importance of the assist, block, or steal, the shooter's efficiency, play distance, and whether the play ties the game, takes the lead, or wins it. The rating number appears next to the Real logo on every play. Player and team "Rankings" add up these ratings over 7 days, 30 days, or a season. The pitch is that this avoids media bias toward star players. — [Real Rating System doc](https://docs.realapp.link/basics/real-rating-system.md)
- **User anecdotes on speed** (App Store reviews; unverified, paraphrased):
  - At a live game, plays appeared in about 5 seconds (May 31, 2026, 5 stars).
  - About 10 seconds behind real life, tested in person (Jul 3, 2026, 5 stars).
  - A couple of seconds on Real versus about 3 minutes on ESPN (Jul 3, 2026, 5 stars).
  - Sometimes updates before the TV does (Sep 27, 2026).
  - Ahead of streams (Sep 12, 2026).
  - Plays appeared at the ballpark almost as they happened (Aug 20, 2026).
  - [App Store review feed, US, most recent 500](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)

#### 2b. Per-play comments and reactions: everything a user can do on a play
- Comments exist on plays, performances, games, "reports" (trades, injuries, birthdays), and posts. — [Comments doc](https://docs.realapp.link/interact/comments.md)
- **On a play or its thread you can** (all from the [Changelog](https://docs.realapp.link/updates/changelog.md) unless noted):
  - **Emoji reactions:** hundreds of custom emojis, up to 30 favorite slots, and favorites appear as quick-select chips under each play (2021). Reactions float live across the screen when others add them (Jun 2021).
  - **Comment and reply:** @mentions; a parent commenter can @all to ping every replier (Oct 2021); reply chains and reply sorting (Aug 2026); GIFs (Aug 2026).
  - **Upvote:** a +5 "super upvote" unlocks at 50K karma. — [Karma doc](https://docs.realapp.link/basics/karma.md)
  - **Downvote:** hides comments and helps the system judge good and bad commenters (Apr 2023).
  - **Edit within 60 seconds,** with visible edit history (Oct 2023).
  - **Report** hateful comments. — [Comments doc](https://docs.realapp.link/interact/comments.md)
  - **Share** a rendered image of a play, performance, comment, or card to social media (Aug 2024), plus an X share button (Aug 2026). **Embed** plays, performances, cards, lineups, and trackers in comments and DMs (2021 to 2025).
  - **Save to albums,** public or private (2021 to 2022).
  - **Jump** to the player's full performance from a play (May 2021). **Watch video** through a link out to the browser (May 2021).
  - **Collect the play** as a "play card" through packs or the marketplace. Big plays (starting with NHL goals) open a 10-minute raffle for first copies (Dec 2023). — [Play Cards doc](https://docs.realapp.link/collect/play-cards.md)
  - **Tag plays** as a community "data analyst" (Oct 2024).
  - **Share approved URLs** in comments (Pro only). — [Real Pro doc](https://docs.realapp.link/basics/real-pro.md)
- **Social-proof and crowd features:**
  - A "Pulse" number in each comment section shows the peak count of people typing at once (Oct 2024).
  - Impression counters on all content (Oct 2022).
  - "Comment summaries" condense a random sample of a large thread (May 2024), with parody voice styles (Jul 2024).
  - Top-upvoted comments are randomly reordered, the way large social apps do it (Jan 2025).
  - [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Status shown on comments:**
  - Owners of a player or team card get their card and serial number under their comments on that player's or team's content, and they rank above others with equal upvotes. — [Player Cards doc](https://docs.realapp.link/collect/player-cards.md); [Team Cards doc](https://docs.realapp.link/collect/team-cards.md)
  - Stadium check-ins mark your comments as checked in (Jul 2023). — [Changelog](https://docs.realapp.link/updates/changelog.md)
  - Flair emoji next to your name at 5K karma. — [Karma doc](https://docs.realapp.link/basics/karma.md)
- **Play-type micro-games:**
  - Emoji challenge: react to a play with the emoji tied to a player (for example, a crown for LeBron) to earn karma and badges. — [FAQs](https://docs.realapp.link/basics/faqs.md)
  - Joke badges for commenting on certain play types within 12 hours, such as 0-for-2 free-throw trips or NHL fights (Dec 2022). — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Karma for commenting** is capped at once a day: +10 for one comment and +10 for one reaction. — [Karma doc](https://docs.realapp.link/basics/karma.md)
- **Gating (2021, may have changed):** commenting unlocked at 200 karma, and top-level comments had a 5-second slowmode until 1,000 karma. — [Changelog](https://docs.realapp.link/updates/changelog.md)

#### 2c. Game chat, groups, DMs
- **Game chat:** a full-screen game chat, filterable between All (plays, performances, and game) and Game only (May 2022). Game chat surfaces the latest comments on that game's plays and performances (Feb 2021) and was moved to the middle tab for easier access (Feb 2021). Pre-game comments reopen before game day (Oct 2021). — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Groups (since Jun 2021):** friends, fan, team, or community groups. Everyone joins a main Real group, which is moderated. Other features:
  - Public groups and admin transfer (Oct 2021).
  - Karma thresholds to join (May 2022).
  - Player and team groups require having favorited that player or team for at least 24 hours (Oct 2022).
  - Group folders and moderator audit logs (Aug 2026).
  - Selecting a group shows that group's comments first in any thread (Feb 2023).
  - [Changelog](https://docs.realapp.link/updates/changelog.md); [FAQs](https://docs.realapp.link/basics/faqs.md)
- **Messaging:** DMs and group DMs (Apr 2021), plus quad DMs for small competitive pods (2023). — [Changelog](https://docs.realapp.link/updates/changelog.md)
- Reviewers mention a "Pro chat" (a paid-members chat) as a social hangout (May and Oct 2026 reviews). — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)
- **Discord:** 10K karma unlocks a role in Real's Discord community. — [Karma doc](https://docs.realapp.link/basics/karma.md)

#### 2d. Profiles, following, reputation (karma), badges, trophies, leaderboards
- **Connections and privacy:** follow and friend other users, privacy settings, and blocking (Feb 2021). Follow counts can be hidden (Apr 2021). Muting is a softer option than blocking (Oct 2021). Mentions, replies, and DMs can be limited to friends only. — [Changelog](https://docs.realapp.link/updates/changelog.md); [FAQs](https://docs.realapp.link/basics/faqs.md)
- **Karma** is Real's free social currency. It earns Rax, unlocks features, wins leaderboard trophies, and earns badges. Unlocks:
  - 1K: profile banner slideshow.
  - 5K: flair emoji.
  - 10K: Discord role.
  - 50K: super upvote.
  - 100K, 200K, and so on: Rax bonuses.
  - [Karma doc](https://docs.realapp.link/basics/karma.md)
- **Ways to earn karma:**
  - Avatar and banner: +100.
  - Each live game feed opened: +10 or more.
  - Pre-game spread poll: +10, or wager up to 100.
  - Pre-game "most points" player poll: 10 to 100, with more for less-popular correct picks.
  - In-game polls at quarter ends, halftime, timeouts, and close games: +5 to +50.
  - Viewing the daily live feed: +10.
  - Daily comment and daily reaction: +10 each.
  - Game of the Day vote: +20.
  - [Karma doc](https://docs.realapp.link/basics/karma.md)
- **Badges:**
  - Emoji-challenge experts, an early-member "Drip" badge, yearly birthday badges, and badges for watching playoff games.
  - Count badges at 10, 50, 500, 1K, 5K, and up for karma, live games watched, upvotes, polls won, and challenges won.
  - Karma-rank badges from #1 through the top 100K (Sep 2022).
  - Stadium check-in badges (2023).
  - [Badges doc](https://docs.realapp.link/interact/badges.md); [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Leaderboards:** per sport, weekly, monthly, season, and playoffs. The top 10 weekly win 5 to 50 Rax and the top 10 monthly win 20 to 200 Rax. The top 3 in a season or playoffs win 1,600, 800, or 400 Rax. Trophies go to the top 500 weekly, top 1,000 monthly, and top 5,000 for season and playoffs. — [Leaderboards doc](https://docs.realapp.link/interact/leaderboards.md)
- **Other leaderboards** (all from the [Changelog](https://docs.realapp.link/updates/changelog.md)):
  - Daily top-1,000 karma leaderboard, paying 100 Rax for 1st down to 10 Rax for 501st to 1,000th (Sep 2023). Pro doubles the payout. — also [Real Pro doc](https://docs.realapp.link/basics/real-pro.md)
  - Per-game top-10 leaderboards (Feb 2023).
  - All-time leaderboards for upvotes, games watched, and polls won (Jun 2023).
  - Global daily, weekly, and monthly karma leaderboards (Jan 2022).
- **Profile surfaces:**
  - Featured card rows and card galleries.
  - "Profile skins" for alternate themed versions of a profile (Dec 2025).
  - Season awards (May 2026).
  - Venue passport: map of stadiums visited and venue tickets (Aug to Sep 2026).
  - Hideable sections (Sep 2026) and profile sharing (Oct 2026).
  - [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Pro customization:** emoji usernames of 1 to 3 emojis, reserved player and team usernames, and 30+ themes or a custom color picker. Everyone gets light and dark modes and an accent color. — [Real Pro doc](https://docs.realapp.link/basics/real-pro.md); [ScreensDesign](https://screensdesign.com/apps/real-sports/)

#### 2e. Predictions, polls, fantasy-style, and betting-adjacent features
- **Poll types:**
  - Pre-game: team spread poll, "most points" player poll.
  - In-game: quarterly head-to-head player polls, halftime spread poll, pre-overtime winner poll, close-game spread polls, NFL "next TD" poll, NHL "next goal" poll.
  - Playoffs: series winner polls.
  - Season-long award polls.
  - Spreads keep polls fair even in lopsided games.
  - [Polls doc](https://docs.realapp.link/interact/polls.md)
- **Poll history** (all from the [Changelog](https://docs.realapp.link/updates/changelog.md)):
  - Polls moved from picking winners to the spread (Jan 2021).
  - MLB polls show moneyline odds (Jun 2022).
  - Results show who picked what (Jun 2023).
  - The app remembers your last karma wager (Apr 2024).
  - Daily home-screen polls such as Game of the Day (Feb 2023).
  - "Dog of the Day" poll (Apr 2025).
- **Fantasy-style modes** (all from the [Changelog](https://docs.realapp.link/updates/changelog.md) unless noted):
  - 1v1 statline "challenges" (Apr 2021).
  - "Brawls," replaced in Aug 2024 by Pro-only **Lineups**: rank the top 5 players in a game by projected Real rating, up to 3 lineups per sport per day, Rax prizes. — [Lineups doc](https://docs.realapp.link/interact/lineups.md)
  - **Daily drafts** (Dec 2024) and paid **draft contests** with a 100-Rax entry and top-50%, 20%, or 10% payouts (Mar 2025).
  - Karma pools (Aug 2024), Daily Streak (Mar 2025), and live and auto-generated trivia for NBA, NHL, and NFL (Jun and Dec 2025).
- **Arena** (launched Oct 17, 2026; Pro-only beta for CFB and NFL):
  - Pick 5 players under a salary cap of 35, plus 5 to 10 "ability" cards bought from a 30-point budget.
  - 7-day head-to-head matchups.
  - Stakes are free or Rax. The winner takes the pot minus a 10% fee.
  - Rules page is dated Oct 9, 2026.
  - [Arena doc](https://docs.realapp.link/interact/arena.md); [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Rax prediction market** (Pro beta since Dec 20, 2025):
  - Community-driven, automated peer-to-peer markets on game winners, with an option to cash out early.
  - Markets cover game winners and total points. Percentages show the crowd's implied likelihood, and lower percentages pay more Rax.
  - Later additions: futures markets and market sharing (Feb to Mar 2026), soccer and WBC markets, a portfolio performance view (Feb 2026), all-time filter and calendar (Jun 2026), shareable portfolio (Aug 2026), and a "ticket stub" design (Aug 2026).
  - [Changelog](https://docs.realapp.link/updates/changelog.md); [Real Pro doc](https://docs.realapp.link/basics/real-pro.md)
- **Pro stat trackers:** set custom over/under lines for player or game stats (e.g., NBA points, rebounds, assists, PRA, threes; NFL yards and TDs) and get notified when they hit. Spread and moneyline trackers were added in Apr 2024. — [Real Pro doc](https://docs.realapp.link/basics/real-pro.md); [Changelog](https://docs.realapp.link/updates/changelog.md)
- **UFC community round judging** (Oct 2025). — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **No cash-out for Rax:** the founders describe the economy as closer to a video game than a sportsbook. Rax purchases are final. — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/); [Rax doc](https://docs.realapp.link/basics/rax.md)
- **FanDuel integration (since the start of the 2026 NFL season, announced Sep 10, 2026):**
  - FanDuel odds, markets, and charts appear in game feeds, play-level views, player performance screens, and team box scores, with contextual markets around key moments.
  - Eligible users are linked straight to FanDuel products.
  - Company sources say it is optional and can be turned off in settings. Louis Antonelli says users had been asking for live odds.
  - [Yogonet](https://www.yogonet.com/international/news/2026/09/11/126364-real-app-names-fanduel-exclusive-sportsbook-and-prediction-market-partner); [FanDuel news](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel); [Flutter blog](https://flutter.com/news-media/blogs/how-fanduel-is-bringing-betting-into-the-social-conversation/)
  - **Conflict:** many Sep 2026 reviewers say the odds were on by default. Company sources call the feature optional but do not say what the default is. — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)
  - A search snippet (pages returned 403, unverified) suggested the first rollout covered New Jersey users. — [PlayNJ](https://www.playnj.com/news/fanduel-partnership-brings-betting-markets-to-real-app/100563/)
- **Current App Store content flags:** 18+; Simulated Gambling and Contests (frequent); Loot Boxes; Messaging and Chat; User-Generated Content. Apple's lookup API reports 17+. — [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162); [iTunes lookup API](https://itunes.apple.com/lookup?id=1514546162&country=us)

#### 2f. Collectibles economy (brief; monetization is another researcher's scope)
- **Rax** is the virtual currency. You can buy it, earn it from karma and leaderboards, or win it in contests. It is spent on cards and packs. — [Rax doc](https://docs.realapp.link/basics/rax.md)
- **Cards:**
  - Player cards cost 200 Rax and team cards 800 Rax. Each has a unique serial number and is tied to a season.
  - Holders earn Rax every game based on the player's Real rating or the team's result.
  - Cards level up through 7 rarity tiers (Common to Iconic) by collecting that player's play and performance cards, with multipliers up to 250x at Iconic 20.
  - Holders can set a custom nickname and avatar for the player or team that they see everywhere in the app.
  - [Player Cards doc](https://docs.realapp.link/collect/player-cards.md); [Team Cards doc](https://docs.realapp.link/collect/team-cards.md)
- **Packs:**
  - Starter (100 Rax, 3 a day), General (200), Yesterday (200; 2,000 available daily, resetting at 10am ET), Player (200+), Team (300).
  - Game packs: 300 per game, released one hour before tip-off, with prices rising from 800 to 1,250 Rax as they sell.
  - [Card Packs doc](https://docs.realapp.link/collect/card-packs.md)
- **Other mechanics:**
  - Prestige: combine 3 identical cards for 3x the rating, stacking up to 27x. — [Prestige doc](https://docs.realapp.link/collect/play-cards/prestige.md)
  - "On This Day": daily Rax claims from past-season cards. — [On This Day doc](https://docs.realapp.link/collect/on-this-day.md)
  - Marketplace and auctions: Pro and high-karma users can list cards. — [Level-up doc](https://docs.realapp.link/collect/level-up-cards.md)
- **Prices:** Real Pro is $7.99 a month or $19.99 for 3 months. Rax bundles run $4.99 to $49.99. — [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162)

#### 2g. Highlights and video
- In 2022 Real had no video or images; it was purely data. — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
- Since May 2021, plays have linked out to high-quality video in Safari or Chrome. — [Changelog](https://docs.realapp.link/updates/changelog.md)
- In 2023 users could tap out to watch a clip. — [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
- A Polish reviewer (Nov 2024) saw short highlight clips, each preceded by a brief ad, and not available for every sport. — [Android.com.pl](https://android.com.pl/tech/843427-real-sports-sprawdzam-aplikacje/)
- A Jul 24, 2026 reviewer says videos are easy to reach and have no ads. This conflicts with the 2024 report. — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)
- **Data visualizations do most of the work instead of licensed video:**
  - Basketball: interactive shot charts with the current attempt blinking, assist breakdowns.
  - Scrubbable momentum charts.
  - Hockey: NHL goal build-up animation.
  - Soccer: goal passing build-ups, heat maps, live ball tracker.
  - Football: NFL route replays with player path and speed (Oct 2025), Next Gen Stats formations.
  - Baseball: hit trajectory, stadium-accurate home-run displays (home run in N of 30 parks), pitch tracking with spin animation (May 2026), spray charts.
  - A "Replay" tool recreates the last moments of a game for social posts, plus throwback game replays.
  - [Changelog](https://docs.realapp.link/updates/changelog.md)

#### 2h. Player and team pages, stats, AI assistant
- **Player screens:**
  - A feed of performances, season stats with league ranks, and splits (last 3/5/10/20 games, home or away, by opponent).
  - Career and all-season views, season switcher, comparison tool, injuries.
  - Salary cap tables and individual contracts for NFL, NBA, MLB, NHL, and WNBA (Aug 2026).
  - [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Team screens:** schedule tab with board or list views (Oct 2026), standings with brackets, power rankings, and an NBA rookie ladder. — [Changelog](https://docs.realapp.link/updates/changelog.md); [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162)
- **Real Bot** (Oct 17, 2026; renamed from "Scout". A separate "Intellisearch" stats search shipped in 2025; whether it is the same lineage is my inference):
  - Plain-English questions over Real's stats, games, plays, cards, polls, and prediction data, with follow-up questions, saved conversations, and shareable answers.
  - Can prepare a prediction, poll answer, or draft lineup, but the user must tap to confirm. It never acts on its own.
  - States its limits: no lineup on/off data, no batter-vs-pitcher matchups, no projections.
  - [Real Bot doc](https://docs.realapp.link/interact/real-bot.md); [Changelog](https://docs.realapp.link/updates/changelog.md)

#### 2i. Notifications
- **"Real Moments":** big moments late in close games, picked by Real, sent to fans of that sport's teams and players and occasionally to everyone, so a large share of users experience the moment together. — [Notifications doc](https://docs.realapp.link/basics/notifications.md)
- **Team alerts:** close-game alerts and game summaries by default; game start and halftime are optional; big-play and performance alerts (e.g., 20+ yard TDs, 12+ straight points, triple-doubles). **Player alerts:** 40+ yard plays, 8+ straight points, season highs. **Tag alerts** are also available. — [Notifications doc](https://docs.realapp.link/basics/notifications.md)
- **Pro alerts:** a notification for every play type for any player (NBA makes, misses, dunks, steals, blocks; MLB at-bats and Ks), filterable by score, time, distance, and exit velocity. — [Real Pro doc](https://docs.realapp.link/basics/real-pro.md)
- **Controls and surfaces:** per-game mute (2022), single-game notifications (Dec 2025), Real-specific notification toggles (Aug 2026), and iOS Live Activities and widgets (May 2026). — [Changelog](https://docs.realapp.link/updates/changelog.md); [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162)
- **Volume:** about 50M push notifications a day (Apr 2026). — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)

#### 2j. Verified and creator accounts
- Real added support for verified player accounts and influencer accounts in Apr 2021. — [Changelog](https://docs.realapp.link/updates/changelog.md)
- NBA players are investors, but I found no evidence they post as verified creators. — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)

#### 2k. Moderation tools and rules
- **Automated filters** block very hateful and explicit content. Human moderators remove hateful comments (since Nov 2022). ChatGPT has screened reported comments since May 2023. WNBA comments are screened by GPT-4o for misogyny under a 3-strike system, and the docs publish the moderation prompt. — [Comments doc](https://docs.realapp.link/interact/comments.md); [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Rules:**
  - Zero tolerance for targeted hate.
  - No serious threats against players or referees; Real describes itself as player-first.
  - No spam or self-promotion, including asking for upvotes.
  - No NSFW content, no doxxing, and no fancy fonts used to dodge filters.
  - Spoilers, gore, and porn are an instant ban.
  - Repetitive "novelty accounts" can be banned.
  - Usernames are held to the same standard as comments.
  - Bans serve as the warning; users appeal to @mod.
  - [Comments doc](https://docs.realapp.link/interact/comments.md); [Rules doc](https://docs.realapp.link/interact/rules.md)
- **User tools:** report, block, mute, and friends-only privacy. — [FAQs](https://docs.realapp.link/basics/faqs.md)
- **Structural controls:** downvotes (2023), karma gates and slowmode for new users (2021), the 24-hour favorite rule for team and player groups (2022), group karma thresholds, group audit logs (2026), and 2FA for sensitive actions (2024). — [Changelog](https://docs.realapp.link/updates/changelog.md)
- Reviewers mention being shadowbanned ("unshadowed" requests, Jul 2026), which suggests shadowbanning is used (user report). — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)

#### 2l. Leagues and sports covered
- **Sports doc (likely out of date):** NBA, NFL, MLB, NHL, UFC, WNBA, Premier League and Champions League, golf, NCAA football, NCAA men's basketball. F1, tennis, and NCAA women's basketball were listed as possible additions. — [Sports doc](https://docs.realapp.link/basics/sports.md)
- **Additions per the changelog:**
  - Soccer: EPL beta (Aug 2024); all five big European leagues, the FA Cup, and MLS (Mar 2026); World Cup.
  - Golf (Apr 2025).
  - WBC and Olympic hockey (Feb 2026).
  - College World Series (Jun 2026).
  - Tennis beta (Aug 2026).
  - [Changelog](https://docs.realapp.link/updates/changelog.md)
- **League count:** the FAQ says 18 leagues, and press uses the same figure. — [FAQs](https://docs.realapp.link/basics/faqs.md); [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)

#### 2m. Web vs mobile
- iPhone only on iOS, with no iPad app. Android has been public since Mar 2021. — [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162); [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Web:** Pro only, at realapp.com and realsports.io. It supports multiple tabs so you can follow several games, and earns a daily "Webmaster" badge. — [Real Pro doc](https://docs.realapp.link/basics/real-pro.md); [FAQs](https://docs.realapp.link/basics/faqs.md)
- **Oct 17, 2026 redesign:** a floating nav bar and "omni search" on mobile. On web: a docked nav, a live "rail," header search, a split game view, and narrower reading widths. Since Jul 2025, shared links render on mobile web. — [Changelog](https://docs.realapp.link/updates/changelog.md)

#### 2n. Real Pro bundle
- Real Pro includes:
  - Web access.
  - Rax predictions.
  - A free daily pack (Real claims about 6,000 Rax, or $50+, of monthly value).
  - 10% bonus Rax on purchases.
  - Custom and emoji usernames.
  - Advanced per-play notifications.
  - Stat trackers.
  - Custom themes.
  - Doubled daily-leaderboard prizes.
  - URL sharing in comments.
  - Early access to new features.
  - [Real Pro doc](https://docs.realapp.link/basics/real-pro.md)

### Inferences
- Real's core move is **turning each data event into a social object** with an objective quality score attached. The score decides what gets attention, which matters most in deciding what to notify about, what to rank, and what becomes a collectible. A markets version would need an equivalent "event rating," such as scoring unusual price moves, volume, option flow, headlines, or halts, to decide which events become threads.
- Much of the product's surface is **gamified prediction with fake money**: spread polls with karma wagers, P2P prediction markets with cash-out, prop-style trackers, and a contest with a 10% rake. Markets already offer real-money trading, so the equivalent "paper prediction" layer would compete with the user's actual brokerage. That makes it a different situation from sports, where most fans don't bet.
- The "simple, clean" feel lives in the scoreboard and feed. Most of the feature count sits in optional economy layers, so an MVP could copy the feed and comments without any of the economy.

### Gaps
- No independent latency measurement exists. Speed evidence is founder claims (often a minute or two ahead of TV) plus user anecdotes (about 2 to 10 seconds behind live at the venue).
- Real's data providers and infrastructure belong to the technology researcher and were not investigated.
- Some docs pages (Sports, Karma amounts, Polls list) are undated and may be stale. One Sep 2026 reviewer said polls were removed and Rax was capped, while another said there were too many new polls. That is unresolved.
- I could not determine whether verified athletes or creators post actively today.

---

## 3. What does the core UX look like, screen by screen, and which design choices make it feel fast, clean, and simple?

### Takeaway
The live feed is the product. Each sport sits in a tab across the top of home. A game opens into a vertical play-by-play feed where each play is a compact card showing a Real rating, tags, context, a reaction counter, and its own thread. A full-screen game chat, box-score tabs, and bottom controls (slowmode, mute, check-in, leaderboard) surround it. Profiles serve as trophy cases for karma, badges, and cards. The speed feel comes from instant pushes and a data-first, opinion-free, mostly video-free feed. Design was engineer-led. Real has advertised for its first full-time designer to lead a full UX revamp (whether the role was filled is unknown), and the Oct 17, 2026 update shipped a new navigation. Many users call the UI clean and easy, but a vocal minority call it confusing and overloaded.

### Cited Findings
**Onboarding (from a recorded walkthrough and screenshot set)**
1. Username with a color choice.
2. Email signup with an optional referral code.
3. Six-digit email verification code.
4. Password.
5. Pick favorite players and teams, using league tabs and search.
6. An intro card explaining a play summary with an "excitement" rating.
7. Live game feed and game dashboards with "Get started."
8. Notification permission prompt.
- A contextual overlay tutorial appears on top of the live UI.
- [ScreensDesign](https://screensdesign.com/apps/real-sports/); [ScreensDesign showcase](https://screensdesign.com/showcase/real-sports)
- A 2024 reviewer said account setup takes a few minutes and asks you to pick sports, players, and leagues. — [Android.com.pl](https://android.com.pl/tech/843427-real-sports-sprawdzam-aplikacje/)

**Home**
- Sports appear as tabs across the top, which makes switching easy. — [Substack review, Jan 22, 2025](https://samantharosewalker.substack.com/p/the-real-mvp-how-the-real-app-is)
- **Sport tab order:** users can reorder sports (2022). Since Sep 2026, sports with live games jump to the front. A setting to turn that off arrived Oct 17, 2026. — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Home content** (all from the [Changelog](https://docs.realapp.link/updates/changelog.md)):
  - A day selector (Jan 2026).
  - Each day shows games, top plays, top performances, and a daily power ranking of performances.
  - "Reports" on trades, injuries, and birthdays.
  - Active streaks and the day's longest plays.
  - Your player cards in action that day, plus a draft module.
  - A trending bar of content with the most impressions in the past minute (Dec 2025).
  - Possession dots and live MLB count, outs, and runners on scoreboard tiles.
  - Game Real ratings on home (Mar 2024).
- The notification panel is at the top of home. A three-bar main menu opens polls, trackers, and the referral dashboard. — [FAQs](https://docs.realapp.link/basics/faqs.md); [Polls doc](https://docs.realapp.link/interact/polls.md)
- A "global live feed" (Jan 2022) merges plays, timeouts, and period changes from all live games across sports into one stream. It was later moved to the Explore/Search tab (Jun 2023). — [Changelog](https://docs.realapp.link/updates/changelog.md)
- Real's 2023 framing: open the app and you see only scores and stats, with no opinion pieces or headlines (paraphrase of a co-founder). — [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)

**Game screen**
- **Layout since the May 2022 redesign:** box scores in the top tabs, controls along the bottom, and a "Feed" tab whose menu filters to Live, Top, All, or Polls (filters from Nov 2021). A scoring-plays-only view was added in Aug 2026. Game chat is full screen. — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Bottom controls:** the settings icon (bottom right) holds slowmode, per-game mute, stadium check-in, and replay. The chart icon (second from left) opens game stats and the game karma leaderboard. — [FAQs](https://docs.realapp.link/basics/faqs.md)
- **Header and pre-game:**
  - Header shows live score, clock (red under one minute in the 4th quarter or OT), timeouts, bonus, a spread bar showing who is covering, and a momentum chart you can scrub.
  - Pre-game info: countdown, team comparison, probable lineups, where to watch, pre-game polls.
  - [Changelog](https://docs.realapp.link/updates/changelog.md)
- Since Sep 2026, FanDuel odds and markets also appear in the game feed and box scores. — [Yogonet](https://www.yogonet.com/international/news/2026/09/11/126364-real-app-names-fanduel-exclusive-sportsbook-and-prediction-market-partner)

**Play-by-play feed item and play screen**
- Each play in the feed shows its own reaction counter and discussion thread. — [ScreensDesign showcase](https://screensdesign.com/showcase/real-sports)
- Plays carry a Real rating, tags such as "lead-taking" or "walk-off," and streak context. — [Real Rating System doc](https://docs.realapp.link/basics/real-rating-system.md); [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
- Since 2021, routine plays (incomplete passes, minor plays) use a compact component, while scoring plays and turnovers get distinct icons. Only NFL scoring plays animate. — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Play detail:** pitch charts and key stats, a rating breakdown, a link to the full performance, a video link, a share image, and the comment thread. — [ScreensDesign showcase](https://screensdesign.com/showcase/real-sports); [Changelog](https://docs.realapp.link/updates/changelog.md)

**Comment thread**
- Threads are nested. Chat supports sticker and emoji reactions, and polls and feed-style posts appear across screens. — [ScreensDesign](https://screensdesign.com/apps/real-sports/)
- Thread features include upvotes and downvotes, reply chains, the Pulse typing count, comment summaries, card-holder flair and serials, and checked-in labels. — [Changelog](https://docs.realapp.link/updates/changelog.md); [Player Cards doc](https://docs.realapp.link/collect/player-cards.md)

**Profile**
- Avatar and banner slideshow, karma count (tap for leaderboards), badges, trophies, featured card rows, galleries, profile skins, season awards, venue passport, and stats such as polls won, games watched, and ranked days. — [Karma doc](https://docs.realapp.link/basics/karma.md); [FAQs](https://docs.realapp.link/basics/faqs.md); [Changelog](https://docs.realapp.link/updates/changelog.md)
- Settings cover notifications by league and category, theme, privacy, account (2FA, delete), and device options such as vibration and video autoplay on cellular. — [ScreensDesign](https://screensdesign.com/apps/real-sports/)

**Navigation**
- A bottom nav with Home, Explore/Search, a center Cards tab, Groups, Activity, and Profile, plus a swipe-out side menu. I reconstructed this tab list from several docs and changelog mentions; it is not an official diagram. — [ScreensDesign](https://screensdesign.com/apps/real-sports/); [Prestige doc](https://docs.realapp.link/collect/play-cards/prestige.md); [FAQs](https://docs.realapp.link/basics/faqs.md)
- A floating nav and omni search replaced it on Oct 17, 2026. — [Changelog](https://docs.realapp.link/updates/changelog.md)

**Design choices that make it feel fast, clean, and simple**
- Data first, no editorial content, no ads. In 2022, no video or images either. — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/); [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
- Developing plays show up live as "In progress" instead of waiting for final stats. Notifications fire on big plays. — [Changelog](https://docs.realapp.link/updates/changelog.md); [Notifications doc](https://docs.realapp.link/basics/notifications.md)
- Fewer taps: swipe between performances (Jan 2025, described as saving lots of taps), quick-select favorite emojis under each play, and the remembered poll wager. — [Changelog](https://docs.realapp.link/updates/changelog.md)
- Most screenshots are dark mode, with an optional accent color. — [ScreensDesign](https://screensdesign.com/apps/real-sports/)
- **Counterpoint:** product design was driven by founding engineers working from loose principles. In an undated job post for its first full-time designer (its user numbers match 2026), Real asked for a full UX revamp and its first design system. — [Product Designer job post](https://docs.realapp.link/jobs/product-designer.md)
- A Jan 2025 reviewer found the amount of information overwhelming at first. — [Substack review](https://samantharosewalker.substack.com/p/the-real-mvp-how-the-real-app-is)

### Inferences
- The UX lesson is that the feed and the thread are the same object. You never leave live context to discuss something, and you never have to search for where the conversation is. That pattern carries over directly to markets: a ticker's event tape where each print or headline has its own thread.
- Real looks simple on day one (scores and a feed) but becomes complex over months (economy, cards, contests). Founders copying it should treat the scoreboard and comments as the product and the economy as optional.

### Gaps
- I found no official screenshot captions; the App Store page exposed none. The screen descriptions come from ScreensDesign's recordings (dates unclear; some screens date to Aug 2024) and the changelog.
- I have no direct look at the Oct 17, 2026 redesigned navigation beyond the changelog text.

---

## 4. Why do fans love it? (ratings, review themes, specific moments and mechanics)

### Takeaway
Ratings are high (iOS 4.8 from about 26K ratings; Android 4.3 from about 4.5K). Among the 380 four- and five-star reviews in the 500 most recent (Apr to Oct 2026), the recurring themes are:
- Speed: about 54 mention fast or instant updates, and many say it runs ahead of TV, streams, or ESPN.
- Beating ESPN: 27 mention ESPN by name.
- Funny live comments and community: 32 mention it.
- Card collecting: 46 mention cards or Rax.
- A clean, easy UI: 32 mention it.

Company and partner metrics back up the game-day habit: over 70% of MAU return on big game days, more than 250K concurrent users in close games, and about 30% of users comment or react. Users describe Real as a replacement for watching the game, a mix of ESPN and Twitter, and a shared sweat with strangers during big moments.

### Cited Findings
**Ratings (verified, Oct 18, 2026)**
- App Store: 4.8 from 26,211 ratings. — [iTunes lookup API](https://itunes.apple.com/lookup?id=1514546162&country=us)
- Google Play: 4.3 from about 4.55K reviews, 500K+ downloads. — [Google Play listing](https://play.google.com/store/apps/details?id=vg.real&hl=en_US&gl=US)
- 2022: more than 4,000 five-star reviews across both stores. — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)
- **Recent sample** (500 most recent US App Store reviews, Apr 11 to Oct 16, 2026; my tally):
  - 71% five-star (355), 5% four-star (25), 2.6% three-star (13), 1.6% two-star (8), 19.8% one-star (99).
  - Monthly averages: Apr 4.93, May 4.13, Jun 4.62, Jul 4.77, Aug 4.62, **Sep 2.90**, Oct 1–16 4.26. The September dip comes from the FanDuel backlash (Q5).
  - [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)
- **Theme counts among the 380 four- and five-star reviews** (keyword tally, approximate): fast, faster, fastest, quick, or instant (54); cards, packs, or Rax (46); comments, community, or chat (32); UI, clean, easy, simple, or smooth (32); ESPN (27); TV, broadcast, or stream (15). — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)

**Engagement metrics (company or partner reported, not audited)**
- Over 70% of MAU return on major game days such as NFL Sundays, more than 250K concurrent users during close games, and about 30% of users actively comment or react. — [Flutter blog, Oct 6, 2026](https://flutter.com/news-media/blogs/how-fanduel-is-bringing-betting-into-the-social-conversation/)
- About 220K unique users during Bam Adebayo's 83-point game (Mar 2026). — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- More than 3M comments in 30 days at about 170K MAU (Apr 2023). — [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
- An investor at the Chernin round said the product resonates with a younger demographic (paraphrase). — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- Founders said in 2022 that some users described Real as an escape from their home lives (paraphrase). — [GrepBeat](https://grepbeat.com/2022/08/18/duke-senior-and-his-two-brothers-getting-real-about-sports-viewing-experience/)

**User anecdotes: specific mechanics and moments** (App Store reviews, paraphrased, 2026 unless noted; [feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json))
- **Ahead of the broadcast:**
  - Gets plays faster than my TV (Jul 14).
  - Live updates a few seconds ahead of my TV; recommended it to 15+ people (Jul 14).
  - Updates faster than TV broadcasts and is useful for games that aren't televised (Aug 25).
  - Notifications faster than the betting apps (Jul 24).
  - Ahead of streams (Sep 12).
- **Replaces watching:**
  - I don't watch games anymore, I just read the app and the funny comments (Jun 30).
  - No longer need a streaming service to follow games (Oct 11).
  - Uses it instead of watching the game (Oct 15).
  - Feels like being at the game (Jun 18).
- **Comments and community:**
  - Every play gets jokes and opinions, and the reviewer has met people through groups (Jul 20).
  - Funny comments and quick updates (Oct 11).
  - Bonding with the chat while melting down over their team (Oct 1).
  - Finds it hilarious when others think the same thing they do (Jun 12).
  - Combines ESPN and Twitter (May 8).
  - The live chat makes you feel part of a community (Aug 29).
- **Beats ESPN:** ESPN is slow to load (Jul 24); haven't opened an ESPN box score since joining Real (Jul 20); faster and more interactive than ESPN (Oct 3).
- **Second screen and multi-game:** check a game when not at home or the TV isn't on (Oct 4); keeping up with multiple games at once (Google Play, Jul 24, 2025, 23 helpful votes). — [Google Play listing](https://play.google.com/store/apps/details?id=vg.real&hl=en_US&gl=US)
- **Stats depth:** assist breakdowns showing who a player passed to most (Google Play, Feb 27, 2025, 46 helpful); feeds and stats a late-arriving bettor would love (Google Play, Jun 5, 2024). — [Google Play listing](https://play.google.com/store/apps/details?id=vg.real&hl=en_US&gl=US)
- **Gamification as a substitute for gambling:** uses Rax as a stand-in for real-money betting (Jul 3); good for people who lose money on other betting apps (Sep 12); the no-real-money pick system with Rax and karma (listing review, Jan 2026). — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json); [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162)
- **Responsive developers:** praise for the devs listening to feedback (listing review, Jan 9, 2024); a reviewer notes the community constantly ratios the founder (Jul 3, 2026). — [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162); [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)
- **Discovery through social:** one reviewer found Real after seeing many sports screenshots on X (Aug 13, 2026). Another credits a streamer, PlaqueBoyMax (Jul 14). Another downloaded it for a YouTube bit (Apr 27). — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)
- **Peak event:** the app's only crash a reviewer remembers was during Bam Adebayo's 83-point game (Jul 14, 2026), matching FOS's account of that night's traffic. — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json); [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)

**Press and third-party reviews**
- A Jan 2025 personal review calls the updates surprisingly fast and sport switching the smoothest the author has used. — [Substack review](https://samantharosewalker.substack.com/p/the-real-mvp-how-the-real-app-is)
- A Nov 2024 Polish review was mixed. It praised stats depth (UFC, soccer heat maps, goal build-ups), called live comments only moderately useful and mostly basketball-focused, described Real as an expanded Flashscore, and said the reviewer would still use X for opinions. — [Android.com.pl](https://android.com.pl/tech/843427-real-sports-sprawdzam-aplikacje/)

### Inferences
- The love comes from three things at once: (1) seeing the event slightly ahead of the broadcast, (2) a crowd reacting to that exact event in seconds, and (3) a lightweight status game (karma, badges, cards) that rewards simply showing up. Speed alone isn't the moat; FotMob, Yahoo, and theScore also claim speed (Q6). The combination is.
- The audience skews young and gaming-native (Roblox/Fortnite comparisons, the investor's demographic remark, review language). A markets product aimed at adult retail traders may need a different tone and stricter controls.

### Gaps
- **Reddit (r/nba, team subreddits, r/sports, r/apps), X, and TikTok posts were not retrieved.** The WebSearch budget ran out, and the TikTok discover page didn't render. Social evidence here is indirect: reviews describing X and streamer discovery, and Real's own X share and screenshot features.
- No independent data (e.g., Sensor Tower) on downloads, retention, or session length beyond company and partner claims and the 2022 figure of about 6 minutes a day.

---

## 5. What do users complain about?

### Takeaway
The dominant 2026 complaint is **the FanDuel sportsbook and odds integration (Sep 10, 2026)**. On that one day, 71 reviews came in and 68 were one or two stars, nearly all about gambling being pushed to a young user base after the founders had promised not to take betting money. The backlash coincided with the App Store age rating becoming 18+. Other recurring complaints: greed and paywalls (cards and P2P trading effectively gated behind Pro and Rax), a toxic and racist comment culture with moderation seen as arbitrary, lag, outages, and wrong plays under heavy traffic, notification spam, and missing basics (no iPad app, no player news, no TV channel listings, sports you can't hide).

### Cited Findings
All items below are user anecdotes from the [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json) (500 most recent US reviews, Apr 11 to Oct 16, 2026), paraphrased, unless another source is cited.

- **Overall:** among the 107 one- and two-star reviews, keyword tallies give 74 on FanDuel, gambling, odds, or selling out; 23 on greed, money, paywall, or Pro pricing; 17 on bugs, lag, loading, crashes, or inaccuracy; 13 on toxicity, moderation, or bans; 4 on logos; 3 on notifications.
- **FanDuel and gambling (Sep 2026):**
  - The partnership was announced Sep 10, 2026. — [FanDuel news](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
  - That day: 71 reviews, 68 at one or two stars, 63 of those about FanDuel, gambling, or odds. Complaints included promoting betting to kids on an app then rated 12+/13+, odds on by default, karma-based parlays, and FanDuel banner ads after an ad-free history.
  - Several cite the founders' earlier public promises, including a quoted X post from roughly 9 months earlier saying Real took no gambling money. Some people say they used Real to help stop gambling. Several cancelled Pro.
  - Some reviewers say most users are under 18. This is unverified, but it fits the investor's younger-demographic remark. — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- **Age rating:** the App Store page now shows 18+, with frequent Simulated Gambling and Contests plus Loot Boxes. Apple's API reports 17+. Google Play still says "Everyone." — [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162); [iTunes lookup API](https://itunes.apple.com/lookup?id=1514546162&country=us); [Google Play listing](https://play.google.com/store/apps/details?id=vg.real&hl=en_US&gl=US)
  - **Conflict:** reviews from Sep 10 describe a 12+ or 13+ rating at that time. When and why it changed is not documented.
- **Earlier gambling-creep complaints:** Rax prediction markets were called a clone of Kalshi and Polymarket (Sep 10). One reviewer says feeds are cluttered with odds talk (Sep 10). FanDuel cites Real's research that about 75% of users who commented on player performances had made betting-related comments. — [FanDuel news](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
- **NFL logos (Oct 2026):** several reviewers say NFL team logos were replaced by text (Oct 6 and Oct 12). One attributes it to the betting deal; that cause is unverified. An Aug 12 reviewer had already complained the logos were outdated.
- **Monetization and greed:**
  - Constant pressure to spend Rax, and trades removed so only the auction house remains (Oct 6, Jul 14).
  - Card collecting effectively behind an $8/month paywall (Sep 10).
  - Price increases with no new content (Aug 10).
  - Pack odds feel rigged after thousands of packs (Sep 1).
  - Rax caps and removed polls (Sep 10).
  - Stop asking for money (Sep 27).
  - When P2P trading was removed is not in the changelog. It may have been replaced by the marketplace and auctions (2025). — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Toxicity and moderation:**
  - Racist and hateful comments, people wishing injuries on players, and the report button feels useless (Jul 7, Jun 12, Aug 2).
  - Toxic teenage users bullying people (Jun 25).
  - Chats full of gamblers harassing athletes (Sep 10).
  - Moderators seen as biased, young, or arbitrary; bans without reason; slow unbans (Jul 1, Jul 11, Jul 28).
  - Even positive reviews mention toxicity (6 of 380), and some name specific trolls.
  - The company acknowledges it can't catch everything quickly. — [Comments doc](https://docs.realapp.link/interact/comments.md)
- **Reliability and accuracy:**
  - Can't handle traffic, laggy and delayed, won't load half the time (Sep 26).
  - Freezes and falls behind on scores (Aug 2).
  - Plays that didn't happen and inaccurate stat tracking (Sep 13).
  - MLB inning dividers hide plays (Sep 25).
  - Comments not appearing (Sep 6).
  - Apple device-check errors at signup (Aug 13, 14).
- **Notifications:** spammed with micro-transaction point alerts like a sportsbook (Oct 8); constant alerts for games the user doesn't care about (Aug 13); live-poll notifications arriving even with live polls turned off (May 18).
- **Complexity:** confusing even after a year, addictive, mixes social-media toxicity with gambling and card games (Oct 13); a dizzying, gamified mess where it's hard to find your own scores (Aug 13); seems confusing at first because there's so much (Jun 10, positive review).
- **Personalization regressions:** live sports forced to the front of the sport list, including tennis and golf the user doesn't follow, with no way to hide sports (Sep 25, 27; Oct 1, 5). Real added a toggle to turn off live sorting on Oct 17, 2026. — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Missing features:** no iPad app (May 5, Jun 26); no per-player news, compared with Sleeper's Rotowire feed (Aug 12); no TV channel or streaming info (Apr 18, Jul 14); thin women's sports beyond the WNBA (Sep 10); missing college baseball and softball and retired-player cards (2025 and 2026). The Polish reviewer flagged English-only and limited soccer coverage (Nov 2024). — [Android.com.pl](https://android.com.pl/tech/843427-real-sports-sprawdzam-aplikacje/)
- **Spoilers:** the rules ban spoilers, but the bigger issue is the feed itself running ahead of TV. Real's fixes are slowmode (5 to 120 seconds) and per-game notification mute. — [Rules doc](https://docs.realapp.link/interact/rules.md); [Changelog](https://docs.realapp.link/updates/changelog.md)

### Inferences
- Real's strongest negative signal is trust: monetization that contradicts the founders' earlier promises, aimed at a young audience. A markets clone faces the same risk in a sharper form (broker affiliate links, payment for referrals, pump-and-dump moderation), with securities-regulation exposure on top. The other researchers should check that.
- Traffic spikes during peak moments (Bam's 83, close games, Sep 2026 lag reports) cause real failures. A markets version would hit its worst peaks at the market open, on CPI or FOMC days, and during earnings.

### Gaps
- Battery drain complaints did not appear in the sample.
- Google Play's negative reviews were not sampled beyond the three surfaced on the listing page.
- The reason for the NFL logo removal, the date P2P trading was removed, and the exact date of the age-rating change are all unverified.

---

## 6. How does Real differ from ESPN, Fox Sports, theScore, Yahoo Sports, Sleeper, Bleacher Report/House of Highlights, FotMob/SofaScore, and other live-game chat products?

### Takeaway
Mainstream apps are built around media (streaming, video, news, editorial takes) or fantasy and real-money picks, and they put chat at the game, team, or league level when they have it at all. Real is built around each data event: every play gets an objective rating and its own thread, reactions, and collectible, and the whole thing is wrapped in a free-to-play status economy. Speed claims are not unique (FotMob, Yahoo, and theScore all advertise fast updates). Real's edge is that its users feel it's faster and that the crowd reacts to the same play together. By Oct 2026 incumbents are converging on parts of the playbook (Yahoo's collectible Milestones and game threads, Sleeper's live game chat, ESPN's phone companion features), and Real is converging toward them with FanDuel odds.

### Cited Findings
**ESPN** (4.65 stars from about 4.18M ratings, rated 12+)
- Streaming-first, with ESPN Unlimited and Select tiers, studio shows, personalized "SC For You" highlights, and "Streamcenter" (watch on TV, engage on phone). Also Multiview for up to 4 streams, Live Activities, and vertical video ("Verts"). — [ESPN on App Store](https://apps.apple.com/us/app/espn-live-sports-scores/id317469184); [iTunes lookup API](https://itunes.apple.com/lookup?id=317469184&country=us)
- Real positions itself against legacy media's subjectivity and editorial highlights that favor stars. — [Welcome](https://docs.realapp.link/welcome.md); [Real Rating System doc](https://docs.realapp.link/basics/real-rating-system.md)
- A 2023 article contrasts ESPN's home screen of opinions and headlines with Real's scores and stats. — [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
- Users say Real is faster and cleaner than ESPN (Q4).

**theScore** (4.82 stars from about 858K ratings, rated 4+, seller Score Media and Gaming Inc.)
- Real-time scores and alerts, very deep in-game stats (its own superlative), odds and lines inside box scores, and chat and messaging for fans around leagues, teams, and games. — [theScore on App Store](https://apps.apple.com/us/app/thescore-sports-news-scores/id285692706); [iTunes lookup API](https://itunes.apple.com/lookup?id=285692706&country=us)
- Its chat is attached to leagues, teams, and games, not to individual plays. That is my reading of the listing; I did not test the app.

**Yahoo Sports** (4.60 stars from about 70K ratings, 17+)
- Play-by-play, win probabilities, and a "Key Plays" feed.
- New "Milestones" let users claim a collectible while a historic moment is happening.
- Points, game streaks, and a shop with streak extenders; a unified profile; real-time game threads, discussions, and live reactions.
- This is the closest incumbent copy of Real-style mechanics.
- [Yahoo Sports on App Store](https://apps.apple.com/us/app/yahoo-sports-scores-and-news/id286058814); [iTunes lookup API](https://itunes.apple.com/lookup?id=286058814&country=us)

**Sleeper** (4.73 stars from about 294K ratings, 17+)
- Fantasy leagues plus real-money "Player Picks" (31 states) and CFTC-regulated "Team Picks" through Sleeper Markets LLC.
- "Live Game Chat" for trash talk, reacting to plays, and sweating games together, plus player and team chat.
- Money-first, with real-cash stakes and 18+ gating.
- [Sleeper on App Store](https://apps.apple.com/us/app/sleeper-fantasy-sports/id987367543); [iTunes lookup API](https://itunes.apple.com/lookup?id=987367543&country=us)
- A Real reviewer points to Sleeper's per-player Rotowire news as something Real lacks (Aug 12, 2026). — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)

**Bleacher Report** (4.60 stars from about 334K ratings, 17+)
- News, highlights, hot takes, community posts, and exclusive shows: media and culture, not data. — [Bleacher Report on App Store](https://apps.apple.com/us/app/bleacher-report-sports-news/id418075935); [iTunes lookup API](https://itunes.apple.com/lookup?id=418075935&country=us)
- A 2022 Real reviewer preferred Real over B/R and its team app. — [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162)

**FotMob** (4.91 stars from about 175K ratings) **and Sofascore** (4.87 from about 78K)
- FotMob is soccer-focused: very fast match updates, live text commentary, xG and shot maps, player ratings, Team of the Week, highlights, TV schedules. It claims 20M+ fans. — [FotMob on App Store](https://apps.apple.com/us/app/fotmob-soccer-live-scores/id488575683)
- Sofascore covers 25+ sports with play-by-play stats, momentum charts, heatmaps, and ratings, and pitches itself as a live second screen. — [Sofascore on App Store](https://apps.apple.com/us/app/sofascore-live-sports-scores/id1176147574); [iTunes lookup API](https://itunes.apple.com/lookup?id=488575683,1176147574&country=us)
- Both share Real's data-visualization DNA (ratings, momentum), but their listings don't feature per-play social threads.
- The Polish reviewer described Real as an expanded Flashscore with a social layer. — [Android.com.pl](https://android.com.pl/tech/843427-real-sports-sprawdzam-aplikacje/)

**Other live-game chat products**
- "Sideline: Reddit Game Threads" wrapped Reddit game threads with spoiler-safe play and pause. It has 52 ratings and was last updated Nov 2022, so it is effectively dormant. — [Sideline on App Store](https://apps.apple.com/us/app/sideline-live-game-threads/id1605296435)
- "Spectate NBA" (Oct 2026) aggregates news and reaction from X, Reddit, YouTube, TikTok, and Instagram for each team, with ads. — [iTunes lookup API](https://itunes.apple.com/lookup?id=1605296435,6752905324&country=us)

**Real's own framing**
- The founders say fans are split across apps for scores, highlights, and discussion, and Real unifies them. — [FanDuel news](https://www.fanduel.com/about/news/real-sports-partner-with-fanduel)
- They also say Real combines features of Discord, Twitter, and Telegram groups, and that sports-news apps bury community features. — [BetCrunch](https://www.betcrunch.com/p/a-real-sports-app-thats-built-on)
- Moving away from general user-generated content toward a sports-data anchor produces more productive interactions, per the founders. — [Overview doc](https://docs.realapp.link/about/overview.md)

**What Real does that the others don't (based on the listings above)**
1. A thread and reaction counter on every individual play, performance, and report.
2. An objective rating on every play that drives ranking, notifications ("Real Moments"), and collectibles.
3. Collectible plays, players, and teams whose value changes with real performance, plus status flair in threads.
4. Free-to-play karma and Rax predictions without real money (until FanDuel's real-money links).
5. Slowmode to sync the feed to your broadcast.
6. Crowd signals: Pulse typing count, trending-in-the-last-minute bar, impression counts.

**What Real lacks that the others have**
- Streaming and licensed video (ESPN), editorial news (B/R, theScore, Sleeper's Rotowire), TV channel listings (FotMob), an iPad app, and real-money products (Sleeper, theScore's odds; Real now partly closes that gap through FanDuel).

### Inferences
- The defensible part of the "Real playbook" is atomic, event-level social plus objective event scoring plus a status economy, not raw speed. In markets, brokers (Robinhood) and TradingView already deliver real-time quotes with no broadcast delay to beat. The equivalent edge would have to come from faster event detection and context (e.g., "TSLA just broke its high of day on 3x volume") and from the crowd reacting to that event, against slower Twitter/X, Stocktwits, and Discord alert groups. This is an inference; no market-app sources were researched here.
- Incumbents copying (Yahoo Milestones and game threads, Sleeper chat) shows the mechanics are copyable. Real's moat is community density at peak moments and four-plus years of iteration (the changelog runs Jan 2021 to Oct 2026).

### Gaps
- Fox Sports and House of Highlights listings were not retrieved; the Fox Sports App Store ID lookup returned nothing.
- I did not hands-on test competitor apps. Comparisons rest on store listings, which are marketing copy.
- No head-to-head latency tests exist in the sources (e.g., Real vs ESPN vs theScore push timing). The "ESPN takes 3 minutes" claim is a single user anecdote.

---

## 7. Which engagement loops bring users back every game?

### Takeaway
Real stacks loops on several timescales:
- **Per game:** open the live feed (karma), make pre-game and in-game poll picks with karma wagers, react and comment on plays, climb the game leaderboard for Rax, and buy limited game packs and big-play raffles.
- **Per day:** daily streak poll, daily top-1,000 karma leaderboard paying Rax, Game of the Day vote, once-a-day comment and react karma, "On This Day" claims, card payouts at 7am ET, pack resets at 10am ET, daily drafts and lineups.
- **Per week and season:** leaderboards, trophies, badges, Arena matchups.

These are fed by heavy push notifications (about 50M a day, plus "Real Moments" that rally users into close games) and by social status (karma ranks, flair, card serials on comments, profile trophy cases, venue passports). Acquisition loops run through shareable play images and screenshots on X and TikTok, plus referral rewards tied to the referred friend watching a live game.

### Cited Findings
**Game-time rituals (per game)**
- Real tells users to open the app during their leagues' game times: discuss plays and pick polls live, then earn Rax and collect after games. — [FAQs](https://docs.realapp.link/basics/faqs.md)
- **Karma for showing up and predicting:** +10 or more for opening each live game feed. Pre-game spread and player polls let you wager up to 100 karma. In-game polls fire at quarter ends, halftime, timeouts, close games, and before overtime. — [Karma doc](https://docs.realapp.link/basics/karma.md); [Polls doc](https://docs.realapp.link/interact/polls.md)
- **Game leaderboards:** the top finishers in each game's karma leaderboard earn Rax and "ranked games." The team-card holder with the most karma in a game earns bonus Rax (e.g., 40 Rax per regular-season NFL game, 60 in the playoffs). — [FAQs](https://docs.realapp.link/basics/faqs.md); [Team Cards doc](https://docs.realapp.link/collect/team-cards.md)
- **Scarcity tied to games:** 300 game packs release an hour before each game at rising prices (800 to 1,250 Rax), and big-play card raffles stay open for 10 minutes after the play. — [Card Packs doc](https://docs.realapp.link/collect/card-packs.md); [Changelog](https://docs.realapp.link/updates/changelog.md)
- **"Events"** (primetime games, opening nights, clinchers, player returns) bring more polls, a karma multiplier, Rax prizes, and a badge for watching live (Oct 2022). — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Being there:** stadium check-ins mark your comments, earn badges, and build the venue passport. — [FAQs](https://docs.realapp.link/basics/faqs.md); [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Live trivia** auto-generated for NBA, NHL, and NFL games (Dec 2025). — [Changelog](https://docs.realapp.link/updates/changelog.md)

**Daily loops**
- Daily top-1,000 karma leaderboard pays 10 to 100 Rax, doubled for Pro. — [Changelog](https://docs.realapp.link/updates/changelog.md); [Real Pro doc](https://docs.realapp.link/basics/real-pro.md)
- **Daily Streak** (Mar 2025): one poll per sport per day. A run of correct answers can be cashed in for escalating Rax, from 5 Rax at 2 straight to 320 Rax at 8, and cashing in resets the streak. — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Small daily karma tasks:** +10 to view the live feed, +10 for one comment, +10 for one reaction, +20 for the Game of the Day vote. — [Karma doc](https://docs.realapp.link/basics/karma.md)
- **Fixed daily times:** player-card Rax pays out at 7am ET; the day's plays enter packs the next morning; 2,000 "Yesterday packs" reset at 10am ET; "On This Day" allows 2 claims per sport per day; Pro gets a free daily pack. — [FAQs](https://docs.realapp.link/basics/faqs.md); [On This Day doc](https://docs.realapp.link/collect/on-this-day.md); [Real Pro doc](https://docs.realapp.link/basics/real-pro.md)
- **Daily contests:** drafts and lineups (Pro), up to 3 lineups per sport per day. — [Lineups doc](https://docs.realapp.link/interact/lineups.md); [Changelog](https://docs.realapp.link/updates/changelog.md)

**Weekly, season, and lifetime loops**
- Weekly, monthly, season, and playoff leaderboards with Rax and trophies; count badges (games watched, upvotes, polls won); karma-rank badges; birthday badges with a 100-karma gift. — [Leaderboards doc](https://docs.realapp.link/interact/leaderboards.md); [Badges doc](https://docs.realapp.link/interact/badges.md); [Changelog](https://docs.realapp.link/updates/changelog.md)
- Arena 7-day matchups (NFL runs Wednesday to Tuesday). — [Arena doc](https://docs.realapp.link/interact/arena.md)
- Card collections stay forever and keep paying through "On This Day," which turns past seasons into daily reasons to open the app. — [FAQs](https://docs.realapp.link/basics/faqs.md)
- Seasonal events such as holiday advent calendars (Dec 2024 and 2025). — [Changelog](https://docs.realapp.link/updates/changelog.md)

**Notification loops**
- About 50M pushes a day (Apr 2026). — [Front Office Sports](https://frontofficesports.com/chernin-group-funding-round-real-app/)
- "Real Moments" pull users into close finishes together. Big-play and performance alerts follow favorited players, teams, and tags. In-game poll notifications. Pro per-play and stat-tracker alerts. — [Notifications doc](https://docs.realapp.link/basics/notifications.md); [Real Pro doc](https://docs.realapp.link/basics/real-pro.md); [Changelog](https://docs.realapp.link/updates/changelog.md)
- Users complain about the volume and about point-earning alerts that feel like a sportsbook (Q5). — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)

**Social status loops**
- **Karma unlocks:** banner slideshow, flair emoji, Discord role, super upvote. — [Karma doc](https://docs.realapp.link/basics/karma.md)
- **Card ownership shown in threads:** card serials as comment flair, a ranking boost on ties, and custom nicknames and avatars for owned players that the owner sees everywhere in the app. — [Player Cards doc](https://docs.realapp.link/collect/player-cards.md)
- **Profile trophy cases:** featured cards, galleries, skins, season awards, venue passport. **Pro identity markers:** emoji usernames, themes. — [Changelog](https://docs.realapp.link/updates/changelog.md); [Real Pro doc](https://docs.realapp.link/basics/real-pro.md)

**Acquisition and virality loops**
- **Share features:** one-tap share images of plays and comments (Aug 2024), an X share button (Aug 2026), an MLB home-run X bot (Oct 2024), a "Replay" tool for social posts, and shareable Real Bot answers and prediction portfolios. — [Changelog](https://docs.realapp.link/updates/changelog.md)
- **Evidence the loop works:** a reviewer joined after seeing Real screenshots on X; reviewers credit TikTok marketing and a streamer. — [App Store review feed](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1514546162/sortby=mostrecent/json)
- **Referrals:** 400 Rax when a referred user watches a live game (up to 10 referrals), plus 20% of their Rax purchases (Dec 2023). Android referrals are not supported. A "referral feature unlocks" item appeared in v10.39 (Sep 2026). — [Changelog](https://docs.realapp.link/updates/changelog.md); [FAQs](https://docs.realapp.link/basics/faqs.md); [App Store listing](https://apps.apple.com/us/app/real-sports/id1514546162)

**Outcome metrics (partner-reported)**
- Over 70% of MAU return on major game days, more than 250K concurrent users in close games, and about 30% of users comment or react. — [Flutter blog](https://flutter.com/news-media/blogs/how-fanduel-is-bringing-betting-into-the-social-conversation/)

### Inferences
- Rough math from FOS's own figures: 50M pushes a day across about 1.3M MAU is roughly 38 pushes per MAU per day, or about 60 per DAU at around 800K DAU. Notifications are a main driver of retention, and also a top complaint. This calculation uses company-reported numbers.
- **What translates to markets:** the natural "game times" are the opening bell, the close, earnings calls, CPI/FOMC releases, and big crypto moves. Mechanics with direct analogs:
  - "Real Moments" → market-wide alerts when something big is happening.
  - Per-event threads → each print, headline, or candle gets a thread.
  - Spread polls → paper "close above or below" polls.
  - Daily streaks and leaderboards → prediction accuracy, not P&L.
  - Card-holder flair → verified "I hold this" badges.
  - Slowmode → not needed, since there is no broadcast delay in markets.
  - Each of these needs careful handling given the gambling and age backlash Real hit.

### Gaps
- No cohort or retention curves, session counts per game, or notification opt-in rates are public. The "70% return on big game days" figure comes from FanDuel and Flutter promotional material, not an audit.
- I could not confirm which loops matter most to retention, since no company or user source ranks them.
