# LITE dip bot history replay v1 (September 28, 2026)

A research replay of the rule in `research/lite_paper_bot_v1/PROTOCOL.md` on Alpaca five-minute LITE bars, January 2022 to September 28, 2026. It places no orders and reads market data and the calendar only.

- **Signal:** the bot's own `mornings()` and `evaluate()`, on IEX bars (`--signal-feed iex`, as live) or SIP bars (`--signal-feed sip`).
- **Buy:** at the 10:00 SIP bar open +0.1%, only if that price is within 2% of the 09:55 close.
- **Sale:** at +2% over the fill, rounded up, once a regular-session bar reaches it. A gap at the open sells at the open. `--through-pct` requires trading beyond the target instead.
- **Size:** $60,000 per buy (66 shares at about $910). One position at a time; no stop and no time limit.
- **Cache:** raw bars go to `outputs/lite_history/`, which is gitignored and must not be committed.

Results and caveats: `output/LITE_DIP_BOT_HISTORY_20260928.md`.

```
PYTHONPATH=src:. .venv/bin/python -m research.lite_dip_history_v1.run --signal-feed sip --output output/lite-dip-history-2022-2026-sip.json
PYTHONPATH=src:. .venv/bin/python -m unittest research.lite_dip_history_v1.test_run
```
