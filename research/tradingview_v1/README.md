# TradingView helpers (owner's free account)

`plan_b_helper.pine` is saved in the owner's TradingView as "Plan B helper: LITE dip rule + my levels" (Pine v6) and added to their chart layout. It replaced the built-in SMA to stay within the free plan's 2-indicator limit (Volume + this).
- **Daily charts:** the 50-day average.
- **Intraday charts (5-minute recommended):** today's 9:30 open (grey), open −1% (orange), and at the 10:00 bar either a green SIGNAL label or a grey dot. Same rule as the LITE bot v1 `evaluate()`.
- **Fill lines:** enter "My LITE fill price" in the indicator's Inputs, and it draws the fill, the +2% sell target and the −20% check level (LITE only).
- **Checked Oct 4 against the bot:** SIGNAL on Sept 30 (the bot bought); none on Sept 29, Oct 1 or Oct 2 (bot: NO_SIGNAL).
- TradingView's consolidated data differs slightly from the bot's IEX bars (Oct 2 open $1,053.26 vs IEX $1,052.98), so borderline days can disagree. The bot's 10:00 email decides.
- Written without indented blocks, so it can be typed into the editor safely.
