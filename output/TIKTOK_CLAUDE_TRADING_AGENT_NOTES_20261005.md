# TikTok (@ai.with.andrew): "Claude trades for you": notes and fact-check (October 5, 2026)

- **Source:** the owner's file `~/Downloads/v1c044g50000db01kdvog65hgqli15sg.MP4` (48 s).
- **Transcribed with Whisper medium + screenshots every 3 s** (`outputs/tmp/tiktok_b4/v1/`, private). The summary below is in my own words.

## What it claims
1. Claude can be connected to "Liquid", a trading app covering stocks, crypto, forex, commodities and prediction markets, and to **QuiverQuant** (insider trades, politicians' trades, institutional activity).
2. You give Claude a strategy, e.g. watch one investor's disclosed trades through the day. It compares them with your portfolio, analyses the trade and sends you a recommendation.
3. A routine can keep checking automatically, and you can paper-trade first.
4. **On-screen:** futures P&L boxes (+$775, +$3,220), the caption "claude trades FOR YOU", a QuiverQuant congressional-trades table (filings 20–34 days after the trade), and a phone portfolio app with a "CLAUDE AI" account (+1.92%).

## Fact-check
- **Connecting Claude to outside tools and running scheduled routines is real.** It's what this project already does: the paper bots, the daily brief and scheduled checks.
  - The specific "Liquid" connector couldn't be verified here. Giving any AI order-placing access to a real brokerage is a serious risk; this project's rule is no real orders.
- **The P&L boxes and "trades for you" caption are marketing, not evidence.** No track record is shown.
- **Copying politicians' trades:**
  - **Disclosures are late:** members of Congress have up to 45 days; the screenshot shows 20–34 days.
  - **Funds that do exactly this,** checked here with Alpaca data from Feb 8, 2023 to Mar 20, 2025 (the latest date with data for all three): **NANC +47.4%** (Democrats' trades), **KRUZ +25.5%** (Republicans' trades), **SPY +41.6%**.
  - So the results are mixed and roughly market-like.
  - Academic studies are also mixed: an early one found senators beat the market; later ones found no reliable edge.
- **"Paper trade first" is the one genuinely good piece of advice,** and it's what this project does.

## Verdict
- **True in the narrow sense:** Claude can be wired to data and a broker and run routines.
- **Not evidence of a profitable strategy.** The infrastructure it shows already exists here.
- **Politician-copying is not a proven edge.** It could be paper-tested if wanted, but there's no reason to expect it to beat SPY by much.
