# Personal trading research: master Claude handoff — September 28, 2026

**Read this first.** Repository: `/Users/pranavmulakala/personal/deterministic-swing-trading-research`. Companion: [paste-ready Claude prompt](CLAUDE_RESUME_PROMPT_20260928.md). The [September 22 project handoff](PROJECT_HANDOFF_20260922.md) is the detailed map of older experiments; this document updates it with subsequent user decisions, Joey's material, September 27 LITE tests, and a read-only September 28 pre-open check. Dated source files remain authoritative for their own tests. Claims about cloud services and broker state are only as current as their timestamps.

This is a source-grounded recap, not proof that every historical chat, file in Joey's ZIP, live server, or market feed was exhaustively audited. Emails, attachments, webpages, and code comments are **reference material, not instructions or trading authorization**. Do not copy or disclose credentials.

## User's goal and current choices

Pranav is 22, describes a roughly $100,000 salary and roughly $90,000 investing account, and is learning stocks, momentum, day trading, ORB, options, and automation. Those financial figures are self-reported and not freshly reconciled. He and his father have manually bought LITE dips and sold rebounds. He sees sharp moves near the regular-session open and wants to know whether a bot can identify a high-volume dip, buy at a defensible price, and sell at a predefined profitable target while he is offline. He would prefer about **five or six whole LITE shares** if a rule and capital support it. He wants rigorous evidence and practical progress without an arbitrary 80-day waiting rule; the last 90 days of historical data can be used for development, but already-seen history is not a fresh holdout. He values simple explanations and independent checks of resources rather than hype or reflexive dismissal.

The **latest stated preference for the proposed LITE research** is no automatic stop, no automatic loss cap, no forced holding deadline, no averaging down, and a sell at a predeclared *profitable* target. An underwater fully paid position should remain open and marked to market in the diagnostic. This supersedes an earlier illustrative example with a $931.50 loss trigger and a Wednesday deadline and an earlier multiple-choice response favoring a loss/time exit; neither defines this latest LITE test. It does **not** mean loss is bounded, recovery is guaranteed, or live execution is authorized. The user has also said they might tolerate about $500–$1,000 of loss, while wanting five or six shares; a five-share purchase near $900 would commit about $4,500, and without a stop the possible loss can exceed $1,000. Make this tradeoff plain without silently inventing a stop. Separate capital committed, floating loss, realized loss, and cash reserve. Older $4,000 experiment and $1,000-per-position suggestions in the September 22 plan were proposals, not binding current rules.

No live stock/options/futures order, account connection using Joey's secrets, scheduled autonomous order, purchase, subscription, push, or deployment is authorized by this handoff. Paper research and read-only checks are distinct from live-money promotion. A 100% win guarantee does not exist; an API can improve data and operational reliability, not guarantee a profitable entry. No strategy here has yet established a repeatable live edge.

### How the project reached this point

The first bot discussion sought a **simple, understandable AI-assisted swing trader** and a genuinely independent look at social ideas, market-data platforms, SEC filing tools, and open-source bots. The project then froze an auditable ETF baseline, built paper-broker software, and found that the baseline lagged relevant historical benchmarks and had broker-parity issues. Separate research expanded to opening-range breakout, LITE opening dips, deterministic stock/option paper ledgers, cloud data collection, context observers, MNQ futures and broker paper plumbing. These tracks generated valuable checks on timestamps, source completeness, costs and fail-closed behavior, but did not jointly form one proven trading system. The [September 22 handoff](PROJECT_HANDOFF_20260922.md) records the older protocol-by-protocol history.

After meeting Joey at the gym, Pranav requested beginner-level options material and examples, received the four saved emails, and asked how their ideas relate to his own bot. He also considered OpenMarket, Quantradin, VTX, and paid APIs while pressing to move from paper to real orders. The latest work narrowed the immediate question to a **LITE opening dip plus rebound/volume rule** with a profitable target and no automatic loss exit, then built historical diagnostics and a read-only Monday observer. A prior suggestion to test for roughly 80 future days was not adopted as a required calendar wait; the real evidence gaps are distinct signals, prospective observations, execution realism, and unresolved downside. The saved chat/context contains user-pasted later Joey replies, but no claim is made here that every historical inbox message or trading chat has been retrieved verbatim.

## What was checked this morning

At **2026-09-28 07:57:47 America/New_York**, allowlisted Alpaca **paper** GET calls returned ACTIVE, $7,500 cash/equity, zero positions, zero open orders, and the regular-session calendar opening at 09:30 ET and closing at 16:00 ET. Buying power displayed $30,000 because the account multiplier is 4; **do not treat that as permission to borrow**. No order was sent. See the redacted [snapshot](trading-preopen-paper-readonly-20260928.json). This is a point-in-time paper-account check, not a current live-investing-account check or a readiness verdict. Reverify any state before using it later in the day.

## Evidence map: do not merge these independent portfolios

| Track | Latest saved evidence | Honest interpretation and next question |
| --- | --- | --- |
| LITE movement | [Raw SIP study](../research/lite_ytd_movement/README.md), 170 complete five-minute sessions through Sept 4. Of 85 sessions still below their open at 10:00, 43 touched the open later that day. Different follow-up denominators gave 57/85 by next session, 73/82 by fifth, 70/73 by twentieth. A June target took 40 later sessions; another remained unreached after 65, with a 38.09% adverse reference-to-low decline. | These overlap and lack funded positions, executable fills, costs, and a prospective entry rule. They do not imply a 50.6% profitable trade chance or guaranteed recovery. |
| LITE fixed intraday | [SIP replication](../research/lite_execution_data/README.md) of older $500 rules: at 10 bps per side, fractional dip 50 trades **−$44.89**, VWAP 5 trades **−$5.40**, whole-share dip 2 trades **−$2.61**. [Capital diagnostic](../research/lite_capital_diagnostic_v1/README.md) at $5k/$10k did not repair these unchanged rules. [Funded comparison](LITE_FUNDED_COMPARISON_20260923.md) had some positive historical variants but LITE buy-and-hold did better in the compared period. | Reject those specific intraday economics. This does not directly disprove the user's distinct longer-hold news/volume hypothesis. |
| LITE profit-only stand-ins, Sept 27 | [Protocol](../research/lite_profit_only_v1/PROTOCOL.md), [ledger](lite-profit-only-development-20260927.json). Five-share, $10k hypothetical, 10-bps model, opening-price target, no loss/time exit. Full 170-session dip stand-in: 33 entries, 32 target exits, **one unresolved** marked around **−$406** at cutoff; full ledger about **+$3,185** marked. Rebound stand-in: 11 exits, about **+$850**. Trailing 90-calendar-day flat-start dip ledger: 8 entries, 7 exits, one unresolved marked about **−$256**, ledger about **+$772**; rebound 2 exits, about **+$273**. | These are already-seen development slices, with bar-based optimistic fills and no volume/news qualification. Marking the loser matters; closed winners alone overstate the case. These are not independent out-of-sample results. |
| LITE volume/rebound proposal, Sept 27 | [Exact protocol](../research/lite_volume_rebound_v1/PROTOCOL.md): first 30m dip ≥1%, final three completed five-minute closes rising but still below open, first-half-hour volume ≥1.5× preceding 20 comparable sessions; proposed five-share limit attempt 10:00–10:05; open-price target; no stop/time exit. Pinned 170-session SIP replay produced **one unique modeled trade, Aug 12**, about **+$94.70** at 10 bps/side. The trailing 90-day slice contains that same trade. [Refresh report](lite-volume-rebound-refresh-20260927/report.json): 184 complete SIP sessions through Sept 25; 130 complete IEX full sessions, 184 complete IEX first half-hours; SIP signaled Aug 12, IEX signaled Jun 26, **zero shared dates**. | One modeled trade cannot establish an edge; feed mismatch is a material blocker to claiming the same rule works prospectively on IEX. No point-in-time news component and no broker fill evidence. This is a proposed diagnostic, not user-approved trading logic. |
| LITE Monday observer | [Observer](../research/lite_volume_rebound_v1/observe_monday.py) is a manually run, GET-only IEX check **only between 10:00 and 10:05 ET today**. It can return BLOCKED, NO_SIGNAL, or SIGNAL_PROPOSAL. It needs six completed 09:30–09:55 bars and prior 20 mornings; one-shot, no scheduler, no orders. Focused tests passed in previous turn, including an independent Astra high review after fixes; see code and tests. | An observed signal is research only. It does not verify cash, live executable bid/ask, queue fill, profitability, or authorize an order. Never run before 10:00 or silently retry/overwrite output. |
| ORB comparison and quote replay | [Comparison](../research/orb_comparison_v1/RESULTS.md) had missing execution minutes in some ledgers. [Quote v2](../research/orb_quote_v2/README.md): primary Arm A **−$90.83 over nine modeled trades**; opening RVOL≥2 Arm B **zero trades**; 28 variants, frozen NO-GO. | No live promotion. A zero-trade arm is not profitable. |
| ORB direct breakout | [Prospective protocol](../research/orb_direct_breakout_v1/PROTOCOL.md) drops retest requirement. At Sept 21, one COHR opportunity appeared in three scenario variants, each about $23–$24 modeled loss. | Three variants are not three independent trades. Review threshold is ≥20 complete prospective sessions **and** ≥20 closed trades in assessed arm; latest count needs fresh journal inspection. |
| Original ETF swing bot | [Paper readiness](../PAPER_READINESS.md), [Sept 22 handoff](PROJECT_HANDOFF_20260922.md). Frozen $500 historical result $680.48 versus SPY $1,099.85 and momentum $793.05. Paper adapter/autopilot software exists, but broker paper execution does not faithfully reproduce next-open/fractional protective assumptions. | Software tests passed at several revisions; historical comparative edge and faithful paper parity were not shown. No live GO. |
| Free stock paper bot | [v2 README](../research/agentic_stock_paper_free_v2/README.md): deterministic stock-only simulated decisions for AAOI, CIEN, COHR, FN, LITE, with IEX quotes, delayed SIP history, bounded news, and earnings checks; no broker orders/model calls. [Sept 21 deployment report](../cloud/DEPLOYMENT_20260921_REPAIR.md) had **one qualified session, zero closed trades**. | Valid data handling and abstention are useful engineering, not profit evidence. Cloud/timer/current counts were not re-audited today. Gate: 30 qualified sessions and 20 closed stock trades, then independent economic review. |
| Existing stock swing core | [Sept 22 handoff](PROJECT_HANDOFF_20260922.md): 10% net target; 10% adverse or 21 sessions causes REVIEW_REQUIRED, no re-underwriting by 42 sessions exits, hard 126-session cap. | Separate strategy. Do not transplant its exits into the new LITE profit-only diagnostic. Not proven profitable. |
| Options, futures, shadows | [Sept 22 map](PROJECT_HANDOFF_20260922.md) details separate $10k stock/options ledgers, combined options-data blockage, original OPRA shadow blocker, indicative shadow plumbing-only checkpoint, MNQ historical zero qualifying setups, forced IBKR paper round trip and later Gateway outage. The $50 MNQ live allowance was a proposal, not activated. | No combined live edge. Need fresh operational and closed-trade evidence before changing any dated status. |

The older [test inventory](project-test-inventory-20260922.md) enumerates 24 then-visible research directories, 70 Python test modules, and 1,079 static test definitions. That inventory is a static snapshot, **not** 1,079 passing tests or a current file census. Historical test totals overlap; do not add them. Run focused checks for a concrete change, then the full relevant suite when stable.

## Joey's emails, attachments, and ZIP

The local [Joey reference README](../reference/joey_2026-09-26/README.md) indexes **four September 26 emails**, original `.eml`, readable text, **16 MIME images**, checksums, shared Drive links, and an offline review. The ZIP in Downloads is linked there, not duplicated; keep the original available. The offline page indexes **61 saved May 6 transaction records, an 87-position snapshot, 112 bot alerts, and four selected backtests**. Those are excerpts and snapshots, not a complete multi-year account history or verified P&L. The ZIP inventory found 629 entries, including 69 PDFs and 27 Python scripts; this does not mean each was fully interpreted. The user's later pasted 1:36 and 1:38 Joey replies are **user-supplied text**, not among the four saved originals.

- Joey's reply to the gym introduction encouraged exploring strategies, using paper to learn mechanics, and experiencing emotions with small real trades; he shared *Get Rich with Options*, basics/Greeks, covered calls, iron condors, and other Drive material. This is educational opinion, not a go-live signal.
- The DELL example illustrates buying 100 shares and selling one call. Joey cited a roughly $561.08 break-even and projected $1,392 maximum gain in eight days, then described rolling the call to Oct 2 with about $547 break-even and $1,340 projected gain. These are **stated examples/projections**, not verified executed returns. A covered call keeps much of the stock downside and caps upside; premium is only a cushion. See [Options Industry Council](https://www.optionseducation.org/strategies/all-strategies/covered-call-buy-write).
- The NFLX material is an iron-condor example with images and adjustments, also not verified realized P&L. Use it to learn spreads, payoff boundaries, early assignment, and what happens outside the expected range, not as evidence of a reliable percentage return.
- In the later pasted replies, Joey says he can roll a losing call or buy a put and refers to a model's 70% chance of finishing above break-even. Rolling can extend time and downside exposure; a put costs premium and sets a floor for the covered shares only under its exact terms. A model probability is neither a guarantee nor a measured historical win rate. See [OIC protective put](https://www.optionseducation.org/strategies/all-strategies/protective-put-married-put) and [FINRA options basics](https://www.finra.org/investors/investing/investment-products/options).
- Static review of the ZIP's Schwab Python work found an ATR-based dip trigger, S&P 500 watchlist, gap-down filter, trade-count limit, and profit-triggered trailing stop. Some scripts can place **real** orders. Selected-day backtests with day-close marks do not reproduce trailing-stop execution or prove profitability. The ZIP contains nonempty `.env`, `token.json`, and hard-coded credential strings; its saved access-token timestamp was May 7, 2026. Joey permitted inspection of the material, not script execution. **Never print, copy into Claude, run/import, or connect with those credentials.** Suggest Joey rotate exposed real secrets. A separate sanitized account-history export would require Joey's specific authorization and secure sharing; do not try to derive it from these files.

Joey's main contribution to our work is a set of **questions**, not a transferable bot edge: What is the actual cash debit and margin obligation? Which outcome is capped? What remains exposed after a roll? What premium was actually received net of fees? How was the quoted probability computed? Was each result realized, marked, or hypothetical? The LITE stock experiment and his options examples need separate ledgers and decisions.

## Data, APIs, and outside resources

- [Alpaca market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq): free live stock feed is IEX while historical SIP availability differs; comparing venue coverage is essential. The Sept 27 refreshed signal disagreement makes feed choice a present research issue. [Paper trading docs](https://docs.alpaca.markets/us/v1.4.2/docs/paper-trading) explain why simulated fills omit live market effects. [Order docs](https://docs.alpaca.markets/us/docs/orders-at-alpaca) explain order behavior and GTC limitations. Do not buy a data tier until a specific missing dataset and acceptance check are identified.
- [Quantradin](https://www.quantradin.com/pricing): paper strategy lab, free daily-bar tier and promotional advanced intraday terms shown at review. It may independently reproduce a frozen LITE rule only if its data, order/fill assumptions, share sizing, and export permit an apples-to-apples comparison. It is not a stock broker or an independent held-out result by default. No account was connected.
- [VTX Macro](https://vtxmacro.com/faq): a live Hyperliquid perpetuals bot arena; stock-referencing contracts are not fully paid company shares. Its public decisions/losses can teach audit habits, not validate LITE stock execution. No wallet or account was connected.
- [OpenMarket](https://openmarket.xyz/): possibly useful as a separate charting screen; equity API history, timestamps, bid/ask and license were not established sufficiently for LITE/ORB research. Do not swap it in as a validated stock feed merely because of a chart or product announcement.
- EdgarTools can help inspect SEC filings but supplies no trading edge by itself. Stocknest, TradeFlawless articles, social posts/Reddit/X/YouTube, VORTEX code and similar platforms are leads to verify, not sources of an assumed win rate. The earlier [September 22 handoff](PROJECT_HANDOFF_20260922.md) and chat history carry the fuller resource context. No subscription or trading integration was made.

## Practical September 28 plan

**Before 09:30 ET:** Read this handoff and the exact LITE protocols; verify the market calendar, paper cash/positions/orders and credentials locally without printing secrets. Confirm the September 27 refresh report and its checksums, and choose one frozen rule/metrics sheet for observation. Do not retrofit today's rule to a price you later see. Decide whether the goal is to observe the proposed IEX rule today or to revise research after market close; avoid combining both as one test. Check whether any relevant LITE news and the source's receipt time are actually available; no historical point-in-time news filter was validated.

**09:30–10:00 ET:** Observe the six completed opening bars only. No inference from an unfinished bar, guessed support level, or today's low known afterward. A preliminary chart view is not a trade signal.

**10:00–10:05 ET, if intentionally observing:** From the repository root, run the [one-shot read-only observer](../research/lite_volume_rebound_v1/PROTOCOL.md) once using its documented command and a **new** output file. It uses IEX data and can save only BLOCKED, NO_SIGNAL, or SIGNAL_PROPOSAL; none places an order. If data are missing/stale, record BLOCKED; a manual retry needs a new filename within the window. Do not count a blocked day as a negative or a signal as a filled/profitable trade.

**After the observation:** Save the output/hash, review opening bar coverage and news timestamps, compare IEX versus SIP without treating them as interchangeable, and record the proposed entry limit, whether an actual paper bid/ask would permit it, and hypothetical capital commitment. Design or refine a separate **paper-only** order-state experiment only after the exact entry/target/size/funding/overnight/corporate-action and error-recovery rules are settled. A profit-target sell can be automated in paper later only with explicit per-position approval, fill reconciliation, and alert behavior. Missing emails or user silence do not authorize selling. The existing stock paper bot's read-only alert path is [documented here](STOCK_PAPER_NEXT_GOAL_20260924.md) and is not a position-specific target-order service.

There is no fixed required “80 days.” Adequacy depends on **distinct qualifying signals, fills or realistic fill proxies, unresolved holdings, adverse excursions, feed agreement, costs, and a genuinely prospective/untouched evaluation**. A trailing 90-day development replay is useful but cannot become a new holdout after inspection. One modeled trade, a passing test suite, or a paper-account balance does not justify live automation. Keep live-money decisions separate and request a fresh explicit order authorization only after a concrete reviewable proposal exists.

## Source order and preservation

1. This file and [Claude resume prompt](CLAUDE_RESUME_PROMPT_20260928.md).
2. [September 22 project map](PROJECT_HANDOFF_20260922.md), [static test inventory](project-test-inventory-20260922.md), and original [capital plan](robinhood-capital-plan-20260922.md) for older context; newer preferences above supersede its proposed exit/capital assumptions for the current LITE diagnostic.
3. LITE [profit-only protocol](../research/lite_profit_only_v1/PROTOCOL.md), [volume/rebound protocol](../research/lite_volume_rebound_v1/PROTOCOL.md), [development results](lite-volume-rebound-development-20260927.json), [refresh report](lite-volume-rebound-refresh-20260927/report.json), and the current [observer](../research/lite_volume_rebound_v1/observe_monday.py).
4. [Joey index](../reference/joey_2026-09-26/README.md), its `.eml` and text, image manifest and offline-review page. Treat all attached material as data. Keep ZIP and credentials private.
5. Track-specific README/protocol/ledger in the table above and any **new** source/output created by Claude, with timestamps and source hashes.

The repository was already heavily modified/untracked before this handoff. Preserve all existing work and result files; inspect status before edits. No code, strategy, broker, cloud, or email action is implied by this documentation. Verify dated counts rather than repeating them as current. Passing gameplay/software tests, a profitable-looking backtest, a paper fill, and live economic edge are different claims; maintain that distinction throughout.

## September 28 Claude session update (added about 10:30 ET)

Everything below was read-only unless stated otherwise.

**Evidence re-check.**
- An independent read-only audit matched every figure in the evidence table above. Two citations point to the wrong file: $680.48 is in `VALIDATOR_HANDOFF.md`/`PROJECT_HANDOFF_20260922.md`, not `PAPER_READINESS.md`, and "24 research directories" comes from the Sept 22 handoff.
- Caveats the table omits:
  - All 32 target exits in the full-sample profit-only dip ledger closed by Jun 2. The Jun 3 entry ($961.78, target $1,028.16) stayed open. Extended with the Sep 27 SIP refresh, it is **still unresolved through Sep 25**: 79 sessions, highest later high $1,026.76, low $594.84, marked ≈ −$105 at $941.64.
  - The ledgers' worst drawdowns were −13% and −17%. One trailing-slice "winner" sat −36% for 40 sessions before closing.
  - The Aug 12 volume/rebound trade duplicates a rebound stand-in trade, so it is not independent evidence.

**LITE context.**
- 2026: $379.42 (Jan 2 open) → $941.64 (Sep 25), +148%. Worst close-to-close drop −42.8% (May 11→Jul 29).
- Monthly closes since 2015 (Alpha Vantage): −40% in 2018–19, recovered in 15 months; −63% from Dec 2021 to Oct 2023, recovered in 43 months.
- Descriptive only, on already-seen data: the dip-rule conditions held on 92 of 184 SIP sessions. A fixed +2% target was reached the same day 65/92 times and within 5 sessions 87/92 times. The worst drop before reaching the target was −36%.

**Monday observation.** See [the sheet](LITE_OBSERVATION_SHEET_20260928.md).
- Paper account at 08:51 ET: ACTIVE, $7,500 cash, flat ([recheck](trading-preopen-paper-readonly-20260928-recheck-0853.json)).
- The observer ran once at 10:00:50 ET: **NO_SIGNAL** (hash `0c0c507b…`).
- The pre-registered after-the-fact feed check found **IEX and SIP agree**: the dip and still-below-open conditions were met; rising closes and 1.5× volume failed (1.13× on IEX, 1.06× on SIP). The simpler dip-only rule would have qualified on both feeds. This is one prospective day.

**ETF paper autopilot.**
- It had failed at every start since about Sep 8, because `_load_env` rejected `MNQ_RESEARCH_KEY`. Separately, its kill switch latched on Sep 8 (`broker_read_failed`). It is bound to a $500 account, while the paper account now shows $7,500.
- The loader is fixed: six named other-tool keys are skipped without being loaded, and unknown keys (including `SWINGBOT_*`) are still rejected. 159 tests pass. **Uncommitted.**
- Revival needs owner action: a $500 paper account, then `reset-run`, `bind` and `clear-kill`. launchd still fires Tue–Sat 06:29; the job will start and then stop at the latch.

**Facts that postdate model training** (checked today).
- FINRA eliminated the PDT designation and $25k minimum (Notice 26-10, effective Jun 4, 2026). Alpaca confirms unlimited day trades.
- Alpaca allows up to 3 paper accounts. New ones start at $100k. Cash-only is available via `max_margin_multiplier=1`.
- Robinhood has no stock API for scripts; its Agentic Trading is for AI assistants.

**Owner's real position (separate record).**
- 33.034698 LITE at $908.14 in Robinhood Individual, bought with cash today. See [the record](REAL_POSITION_LITE_20260928.md). It is not part of any research ledger.
- `research/real_position_alert_v1` sends price-only email alerts to pranavm1104@gmail.com and cannot trade. Its delivery test was accepted at 10:08.
- A 2-minute launchd job for it was installed, flagged by the permission system as persistence without explicit approval, and **removed by the owner at about 10:10**. Verified: the plist is gone and the job is not loaded.

**Owner direction for the LITE paper bot.** Dip rule; buy right away, sell at a profit target; no automatic stop; the owner monitors losses himself; paper automation approved in principle.
- Still pending before building:
  - the profit target (+2% over the actual fill proposed)
  - the share count (7 proposed)
  - a separate "LITE bot" Alpaca paper account with its own keys (owner action)
  - explicit approval for any scheduled job

**LITE paper bot v1: built and scheduled (10:40 ET).** The owner approved a +2% target and "install the 10:00 paper job".
- Code: `research/lite_paper_bot_v1/` ([rules](../research/lite_paper_bot_v1/PROTOCOL.md)). It trades 7 shares on the dip rule, buys with a DAY limit order at 10:00:30 and cancels at 10:05, then rests a GTC limit sell at the fill × 1.02 rounded up. There is no stop and no time limit. It uses the LITE paper keys in `.env.lite` (owner-only, gitignored) through a LITE-only client that allows only listed requests.
- Safeguards: it halts to `outputs/lite_paper_bot/KILL` on any unexpected state, and it recovers an interrupted buy.
- Tests: 16 offline tests pass.
- Schedule: launchd `com.pranav.lite-paper-bot`, Mon–Fri 10:00.
- Verified run at 10:37: without keys it reported `NOT_SET_UP` and emailed.
- The owner created the separate "LITE bot" paper account and saved its keys: `.env.lite` is 0600 and its key differs from the ETF paper key. **Bound at 10:40:45 ET** after read-only checks: $100,000 cash, no positions, no open orders. The first scheduled run is Tue Sep 29, 10:00 ET.

**Options track opened (owner request, about 11:10 ET).** This is a separate strategy; it is not mixed with LITE or with Joey's material.
- The old `agentic_shadow_v1` OPRA probe was never actually blocked by entitlement: the same `_load_env` bug stopped it before any request.
- After today's loader fix it ran once, at 11:12 ET: `GET /v1beta1/options/snapshots/SPY?feed=opra` returned **HTTP 403**. The free Alpaca plan is **not entitled to OPRA** options quotes.
- Existing options code is the simulated $1,000 long SPY/QQQ call/put ledger in `agentic_portfolio_v1`; its orders are permanently disabled and it was never validated.

**SPY bull put spread paper bot: live on paper (about 14:50 ET).**
- **Code and rules:** `research/spy_put_spread_v1/` ([PROTOCOL](../research/spy_put_spread_v1/PROTOCOL.md)). The owner approved the rules, the volatility filter and the weekday 10:30 schedule. 17 offline tests pass.
- **Account:** its own Alpaca paper account (number ending **Y47T**, options level 3), bound at 14:44 ET.
- **Key mix-up, resolved:** keys had first been regenerated on the LITE bot's account (ending **OPE5**), which invalidated the LITE keys. They were moved programmatically into `.env.lite`, verified, and binding now also compares account IDs.
- **Plumbing test passed** (1 contract, excluded from results):
  - short 740 / long 735 put, Oct 30 expiry
  - $0.60 credit; leg signs verified; negative `limit_price` = credit confirmed
  - GTC profit-take placed and cancelled; bought back for $0.66 (−$6); flat
- **Signal check at 14:45** (the filters are not enforced in a plumbing test):
  - trend ok (771.35 > 759.90)
  - IV/RV 1.20, passing at the threshold
  - mid credit $0.59, below the $0.75 minimum, so a real Monday entry would have been skipped
- **Entry time lock:** launchd fired once at 13:40 ET, catching up after the Mac woke from sleep. That run was harmless because it had no keys. Entries are now limited to Mondays 10:25–11:30 ET.
- **First possible rule-based entry:** Mon Oct 5, 10:30 ET.
- **Backtest:** the owner chose Databento's free credit and approved "both" periods, 2013-04 to 2025-12, up to $64 of the $125 credit (expected about $6.50).
  - Code: `research/spy_put_spread_backtest_v1/`. `fetch_databento.py` pulls OPRA `cbbo-1m` for the SPY chain at 10:30 ET and the close each trading day, 16 days in parallel, with a $20 estimated-spend guard. `backtest.py` replays the rules under mid and natural fills, with and without the volatility filter.
  - The pilot (2 days) matched an independent source within a few cents. Parity-derived SPY matched Alpaca's actual prices within $0.01–$0.15.
  - A download started about 15:30 ET; Databento takes 15–60 s per 1-minute window, so it needs about 3–4 hours. Output goes to `outputs/spy_options_data/` (gitignored).
  - Results pending.

**Still unverified.**
- Any paper order or fill, and whether target sells fill.
- Overnight gaps; GTC expiry and corporate-action handling.
- The next earnings date.
- Cloud journals for direct breakout and the free-stock bot (not checked).
- Robinhood balances beyond the owner's screenshot.
