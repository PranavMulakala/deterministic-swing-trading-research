# Test #28 plan: OWLS Capital alerts, last month, scored as a follower (written October 8, 2026, before checking prices)

- **Owner's request (Oct 8):** "backtest everything the alerts you've seen from everyone here… for the last month and see who was the most profitable and who's the most legit."
- **Source:** the paid OWLS Capital Discord (the owner's subscription), channel **all-alerts**, which re-posts every analyst's alert with a timestamp.
  - Read only. Raw messages are kept in `outputs/owls_alerts/` (gitignored, private paid content; never committed or shared).
- **Window:** alerts posted **Sep 8 – Oct 8, 2026**.
- **Already looked at:** two weeks of message text (Sep 25 – Oct 8) and three spot checks of option prices, done in the review. No systematic price checks yet.

## Turning messages into trades
- **Per analyst:** each **entry** is a message naming a specific option (ticker, strike, call or put, and an expiration or "0DTE") with an entry price. Each **exit** is a later message from the same analyst about that position: a trim, "all out", "out", a stop hit, or "cut".
- **Missing expiration:** a same-day expiration ("0DTE") if the analyst says so, or for SPX/SPY scalps posted during market hours. Otherwise the nearest weekly expiration on or after the entry date. Any case where this choice is ambiguous is marked "ambiguous" and reported separately.
- **No exit message:** the position is valued at the option's last price on its expiration day, or on Oct 8 if it hasn't expired.
- **Not scored:** commentary, levels, watchlists, "would have worked", and stock (common share) trades. Stock trades are listed but not scored as options.

## Follower scoring (main)
- **Entry:** the option's traded price in the **minute after** the alert. Use the 1-minute bar's **high** (a conservative fill), or that minute's close if only one trade.
- **Exit:** each exit message sells an equal share of the position. For example, "trim", "trim", "all out" sells ⅓, ⅓, ⅓. The price is the 1-minute bar's **low** in the minute after the message (conservative).
- **Size:** $1,000 per alert (fractional contracts) so every alert counts equally.
- **Prices:**
  - Alpaca option 1-minute bars (free) for stocks and ETFs.
  - Databento for SPX index options, only after the owner approves the quoted cost.
- **Also reported:** the "posted" result, using the analyst's own stated prices or % where given, so the gap between posted and real follower results is visible.

## Report (dollars first)
- **Per analyst:**
  - alerts scored;
  - follower total $ and $ per alert;
  - win %;
  - best and worst alert;
  - posted vs. follower result;
  - share of alerts with a posted exit;
  - share of losses the analyst acknowledged.
- **Ranked by follower $ per alert.**
- **"Legit" signals:**
  - posted prices that match real prices at alert time;
  - losses acknowledged;
  - an exit posted for every entry.

## Honest limits, stated up front
- Messages are free text; reading them into trades involves judgment. Every trade is listed with its source message time, so it can be checked.
- One month is a small sample. It shows **followability and honesty** better than long-run skill.
