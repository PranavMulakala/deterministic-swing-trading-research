# Do Options Insider's levels work better than random levels? Pre-declared test #12 (October 5, 2026)

Written and committed **before** any of his calls were extracted or scored. Research only; no orders. The owner asked: "pull his levels from 20 streams and test them… make sure you pull 100% of everything".

## Source
His **20 most recent free premarket streams** on YouTube (@VincentDesiano), titled "[LIVE] PRE MARKET PREP" or "[LIVE] PRE-MARKET LIVE STREAM". The market-open trading streams are excluded because they aren't premarket level calls. Newest first:
diFp-S8FXjQ, jF7lxEEVtnA, RU8IbrGlo2w, CRtB7eS_N8c, AoXfHxkqkBQ, QdDX5Cq8luc, kcUkPZBzTiE, oV2m0yOBcYc, ccJBkGmrHWg, FHdO3T3FqUY, E5vAuQgG-MQ, 9xTKzTR0FKI, ukihNSG2quI, UFNzbml1XqU, wtv8j8866p8, pL5RfQ54i4g, jLgW35b9LQU, sEgraGdo1QU, HyCr80lQCcI, YALhjgUnIv8.

- **Text:** read through YouTube's own transcript panel (nothing downloaded) and kept as private working copies in `outputs/tmp/` (gitignored, never published).
- **Stream date:** the broadcast start date from the video page.

## Step 1: extracting calls (done blind; nobody looks at prices while extracting)
**Every** explicit price call for a **US-listed stock or ETF** is logged, with the timestamp and a short quote for audit. Call types:
- **LONG_IF_ABOVE:** "if X gets/holds above L…", "reclaim L", "break and retest L", "over L → T".
- **SHORT_IF_BELOW:** "if X fails/loses/breaks below L → T".
- **SUPPORT_BOUNCE:** "pullback long to L", "demand at L", "watch for a bounce off L".
- **RESISTANCE_FADE:** "fade the supply at L", "short off L".

**How levels and targets are recorded:**
- A level can be a single price or a zone ("615–618"). Targets are recorded where he states them.
- Spoken shorthand is turned into full prices (e.g. "744.64").
- A stock or ETF level more than 15% away from the previous day's close is treated as a misheard number: it's dropped and counted.
- **Excluded and counted:**
  - futures (NQ, ES, RTY, YM, GC, CL), crypto (BTC) and yields, which we have no intraday data for;
  - generic remarks with no price;
  - levels given for a different day.
- If the same call is repeated in one stream, it counts once.

## Step 2: scoring each call on the stream's own day
- **Data:** Alpaca SIP 5-minute bars, regular session 9:30–16:00 ET.
- **Zones:** a zone [a, b] has a "trigger edge" and a "fail edge". A single price uses a = b = L.

| Type | Triggered when | Success | Failure |
|---|---|---|---|
| LONG_IF_ABOVE | first 5-min close above b | high reaches T | a 5-min close below a, first |
| SHORT_IF_BELOW | first 5-min close below a | low reaches T | a 5-min close above b, first |
| SUPPORT_BOUNCE | first bar whose low touches b or lower | high reaches T | a 5-min close below a, first |
| RESISTANCE_FADE | first bar whose high touches a or higher | low reaches T | a 5-min close above b, first |

- **Entry price:** the trigger bar's close for LONG_IF_ABOVE / SHORT_IF_BELOW; the zone edge (b or a) for bounce/fade.
- **No stated target:** T = entry ± 1.0% for single stocks, ± 0.5% for index ETFs (SPY, QQQ, IWM, DIA), in the call's direction.
- **A target already passed at the trigger:** recorded as "target already reached"; excluded from rates and counted.
- **Neither success nor failure by 16:00:** the call "expired". It's scored by the close vs entry for the % outcome, and counted as **not** a success in the success rate.
- **If success and failure land in the same 5-minute bar,** it's counted as a failure (cautious).
- **Not triggered all day:** reported separately, not in the rates.
- **% outcome per triggered call (as if traded):** exit at T, at the failing bar's close, or at the 16:00 close. Before costs.

## Step 3: placebo (random-level) comparison, the core of the test
- Each call is repeated with **all its prices shifted** by d = −1.5%, −0.75%, +0.75% and +1.5% for single stocks. For index ETFs the shifts are halved: −0.75%, −0.375%, +0.375%, +0.75%.
- Scoring is identical. This gives 4 "made-up" calls per real call, same symbol, same day, same shape.
- If his levels carry real information, his calls should succeed more often than the made-up ones.

## Verdict, fixed now
His levels **show an edge** only if both hold:
1. **Success rate:** among triggered calls, his success rate beats the placebo calls' success rate by **at least 5 percentage points**.
2. **Statistical check:** a bootstrap over calls (10,000 resamples, resampling each real call together with its 4 placebos) gives a 95% interval for (real − placebo) success rate that **excludes zero**.

Also reported, information only:
- the average % outcome of real vs placebo calls;
- results by call type, by stock vs index ETF, and for the calls he labelled "top watch";
- MU calls specifically.

**Nothing will be tuned afterwards:** no other shifts, targets, bar sizes or windows.

## Known limits
- Extraction from speech involves judgment. Every call carries a timestamp and quote so it can be audited, and a sample will be spot-checked against the transcript.
- He often gives futures levels (NQ/ES), which can't be scored here. Only stock and ETF calls count.
- 20 streams is about one month; the result covers Sept–Oct 2026 only.
