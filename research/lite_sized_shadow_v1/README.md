# LITE "bigger dip, bigger buy" shadow bot v1 (frozen September 30, 2026)

**What it is:** the second paper bot the owner asked for on Sept 30. It runs version 3 from the [LITE dynamic test](../../output/LITE_DYNAMIC_TEST_RESULTS_20260930.md) as a **shadow ledger**, not a second broker account.

**Why a shadow ledger and not a second account:**
- Version 3 buys and sells at exactly the same moments and prices as the running LITE paper bot. The only difference is how many shares it buys.
- So its result follows from the running bot's real paper fills, with the share count changed. A second account would only repeat the same trades.
- All three of Alpaca's paper accounts are in use: the LITE bot, the options bot, and the old ETF bot.
- Two bots trading LITE in one account would collide, and the running bot halts on orders it didn't create.

**The rule (fixed; nothing here gets tuned):**
- For each real paper buy, take that morning's dip (`dip_pct` in the bot's `SIGNAL` event):

  | Dip | Shadow buy |
  |---|---|
  | 1% to under 2% | $40,000 |
  | 2% to under 3% | $60,000 |
  | 3% or more | $80,000 |

- Shadow shares = whole shares that amount buys at the bot's actual fill price.
- The shadow sells when the bot's real +2% sale fills, at the same price.

**What it can't do:**
- It can't place orders.
- It can't change the running bot.
- It reads no keys.

**How to run it** (read-only; `--mark` values an open position at a price you give it):

```sh
ssh <server> 'cat /opt/lite-paper-bot/outputs/lite_paper_bot/events.jsonl' \
  | PYTHONPATH=src:. .venv/bin/python -m research.lite_sized_shadow_v1.shadow - --mark 965.00
```

**Where it shows up:** two extra columns in the weekly scorecard of the [paper test plan](../../output/PAPER_TEST_PLAN_20260929.md): "Shadow realized" and "Shadow open paper loss".

**One blind spot:** if the running bot skips a buy for lack of cash or because of its $72,000 cap, the shadow skips it too. At today's prices, 66 shares cost about $63,000, so this only matters if LITE rises above about $1,090.
