# LITE IEX observation sheet — Monday September 28, 2026

Prepared 08:45–09:00 ET by Claude before the regular session. Research observation only: **no order of any kind is part of this sheet.** Rule source: [volume/rebound protocol](../research/lite_volume_rebound_v1/PROTOCOL.md); master context: [Sept 28 handoff](TRADING_MASTER_HANDOFF_20260928.md).

## Pre-open checks (done)

| Check | Result | Evidence |
| --- | --- | --- |
| Paper account, read-only GET at 08:51:19 ET | ACTIVE; $7,500 cash; $7,500 non-margin buying power ($30,000 margin buying power, **not** to be used); 0 positions; 0 open orders | [recheck JSON](trading-preopen-paper-readonly-20260928-recheck-0853.json) |
| Calendar | Regular sessions 09:30–16:00 Mon Sep 28 through Fri Oct 2 | same file |
| Clock agreement | Broker vs local clock about 1 s apart (observer tolerates 60 s) | same file |
| Saved IEX history | `verified_history()` passed offline: all 22 refresh-manifest hashes, report status, calendar through Sep 25, all 20 prior IEX mornings present | no network, no credentials |
| Observer safety | Client allowlists GET on `/v2/calendar`, `/v2/clock`, `/v2/stocks/LITE/bars` only; host pinned to `paper-api.alpaca.markets` / `data.alpaca.markets`; parent client separately blocks mutation | `research/lite_execution_data/collect.py:21-30`, `src/swingbot/paper_config.py:10-11` |
| Focused tests | `test_observe_monday`, `test_run`, `test_refresh`, `lite_profit_only_v1.test_run`: OK (fake clients only) | run 08:49 ET |
| Scheduled jobs | No crontab. launchd `com.pranav.swingbot.paper-autopilot` fires Tue–Sat 06:29 (not Monday) and has **failed at startup since about Sep 8** (`.env` parser rejects `MNQ_RESEARCH_KEY`). It uses the same paper account. Left untouched. | `outputs/paper/autopilot-error.log` |

Frozen-file SHA-256 at 08:52 ET:

- `run.py` (contains `decision()`): `bfa8de27…6a2`, identical to the runner hash in the Sept 27 development result.
- `observe_monday.py`: `7f6712a8…e02`.
- `refresh.py`: `d9c7b96b…626`, identical to the refresh manifest's runner hash.
- `PROTOCOL.md`: `24411bc8…895`. This differs from the development result's recorded `d53b614f…`, because the refresh/observer sections were appended after that run. No git history exists for `research/`, so the unchanged rule paragraph cannot be proven byte-for-byte; the executable rule in `run.py` can.

## The frozen rule, with today's numbers filled in

At 10:00 ET, using only the six **completed** IEX five-minute bars stamped 09:30, 09:35, 09:40, 09:45, 09:50, 09:55:

1. **Dip:** the lowest low of those six bars is at or below 99% of the IEX 09:30 bar's open.
2. **Rebound:** the 09:45 close < 09:50 close < 09:55 close, and the 09:55 close is still below the IEX 09:30 open.
3. **Volume:** total IEX volume of those six bars is at least **36,737 shares**, which is 1.5 × 24,491.15, the mean over the prior 20 IEX mornings (Aug 28 → Sep 25).

The volume bar is high. Only 2 of the prior 20 mornings (42,353 and 45,175) cleared 36,737. Historically the full rule fired on IEX once in about 164 evaluable sessions (Jun 26), and on SIP once (Aug 12), on different days.

If all three hold, the observer writes a SIGNAL_PROPOSAL. It contains a research limit equal to the 09:55 close, valid only for the 10:00–10:05 bar, a research target equal to the IEX 09:30 open, and 5 shares. That is a proposal on paper, not an order, not a fill, and not a check of cash or the live quote.

Note that the IEX 09:30 "open" is the first IEX trade, not Nasdaq's official opening-cross price. The two can differ.

## The run (manual, once)

Run once, **between 10:00:30 and 10:02 ET**, so the 09:55 bar has finalized and there's time to retry. From the repository root:

```sh
PYTHONPATH=src .venv/bin/python -m research.lite_volume_rebound_v1.observe_monday --refresh output/lite-volume-rebound-refresh-20260927 --output output/lite-monday-observation-20260928.json
```

- **Never run it before 10:00.** Outside the window it still writes a BLOCKED file and uses up the filename.
- If it returns BLOCKED because of data, one manual retry inside the window is allowed, with a **new** filename (`…-retry1.json`). No scheduler and no silent retries.
- **BLOCKED** means the data or timing was unavailable. It is not a "no" and doesn't count as a negative day. **NO_SIGNAL** is the rule's normal state. **SIGNAL_PROPOSAL** is research only.

## After the run

1. Save the output file's SHA-256 next to this sheet.
2. After about 10:20 ET, SIP data older than 15 minutes becomes queryable on the free plan. Evaluate the same `decision()` on today's SIP first half hour against the SIP prior-20 baseline from the saved refresh. Record whether the feeds agree. Neither feed substitutes for the other.
3. Only if a proposal fired: GET the SIP quotes for 10:00–10:05 and record whether the national best ask ever reached the limit. A reachable ask is still not proof of a queue fill.
4. Don't tune any threshold to what today showed. Today is one prospective observation.

## Capital arithmetic (no stop, no deadline)

Priced at Friday's close of $941.64. These are marked (unrealized) losses while a position stays open, and the capital is committed until the target fills.

| LITE decline from entry | 1 share | 2 shares | 5 shares | 6 shares |
| --- | ---: | ---: | ---: | ---: |
| Capital committed | $942 | $1,883 | $4,708 | $5,650 |
| −10% | −$94 | −$188 | −$471 | −$565 |
| −20% | −$188 | −$377 | −$942 | −$1,130 |
| −38.09% (the Jun 3 case, target unreached after 65 sessions) | −$359 | −$717 | −$1,793 | −$2,152 |
| −42.8% (LITE's 2026 close-to-close drop, May 11 → Jul 29) | −$403 | −$806 | −$2,015 | −$2,418 |

With 5 shares, a $500 loss arrives at a 10.6% decline and a $1,000 loss at 21.2%. With 6 shares, those are 8.8% and 17.7%. Without a stop, nothing enforces the $500–$1,000 tolerance. Share count is the only lever that bounds it in advance, and that choice is yours to make; this sheet does not make it.

## Context captured, not used by the rule

- LITE in 2026: $379.42 at the Jan 2 open, $941.64 at the Sep 25 close (+148%); highest close $1,052.61 (May 11), lowest $324.17 (Jan 16). This was a strong rising year, which flatters any buy-the-dip rule that never sells at a loss.
- News since Friday 16:00 (Alpha Vantage, retrieved about 08:53 ET): six items, all about Form 4 insider sales by one executive (1,000 shares on Sep 24–25 under a 10b5-1 plan adopted May 19). No earnings or guidance item appeared. This is not a point-in-time news filter.
- Next earnings date: **not verified.** The calendar lookup returned an unusable reply. Check the company's investor-relations page before any multi-week hold.

## Feed-check script, written before today's data

`research/lite_feed_check_20260928/compare.py`, SHA-256 `1c1ee2044c1c13f86f6ea254cbbe2339b2f7e429410eb99bc65a9de5055a7e91`, recorded 08:56:35 ET. Its offline tests passed 4/4 (fake client). It refuses to run before 10:20 ET.

## Observation result

Ran once at 10:00:50 ET, after all frozen-file checksums passed. Result: **NO_SIGNAL** (`RULE_NOT_MET`), feed IEX, orders sent 0. Output `output/lite-monday-observation-20260928.json`, SHA-256 `0c0c507b5acf5c48dbd853aa60761185ec9ed31b40e3af2fb049146b88cf10b8`. Which condition failed is checked by the after-the-fact feed comparison (after 10:20 ET).

## Feed comparison (after the fact)

Ran once at 10:25:01 ET with the pre-registered script (hash verified). IEX and SIP **agree: no signal**. Both feeds met the 1% dip and still-below-open conditions, and both **failed** the rising-closes and 1.5x-volume conditions (IEX 1.13x, SIP 1.06x). So the simpler dip-only rule would have qualified on both feeds today. Report `output/lite-feed-check-20260928/report.json`, SHA-256 `5823511c8851d4a41df7b5914dbc27927d7cdd490cd43766cc57f76b1150361e`.
