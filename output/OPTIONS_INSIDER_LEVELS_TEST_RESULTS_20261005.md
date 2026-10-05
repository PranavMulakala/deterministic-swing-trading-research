# Test #12: Options Insider's premarket levels vs made-up levels: results (October 5, 2026)

- **Plan:** [OPTIONS_INSIDER_LEVELS_TEST_PLAN_20261005.md](OPTIONS_INSIDER_LEVELS_TEST_PLAN_20261005.md), committed (d720926) before any call was extracted. The addendum (0dcdaa5) was committed after extraction but before any scoring or price lookup.
- **Code:** `research/oi_levels_test_v1/score.py` (9 unit tests), committed before any calls existed (cec9742).
- **Results:** `output/oi-levels-test-results.json` (+ `.provenance.json`) and `output/oi-levels-test-results-sensitivity.json`.
- **Source:** his 20 most recent free premarket streams on YouTube, Aug 25 – Oct 2, 2026.
  - Read 100% through YouTube's transcript panel by 4 agents, blind to prices.
  - Only the call lists with ≤15-word audit quotes were kept; no full transcripts.
- **Data:** Alpaca SIP 5-minute bars, regular session, for each call's own day.
  - The first scoring run hit data rate limits on ~95 symbol-days. They were re-downloaded slowly with retries before the final run, and all succeeded.

## Verdict: NO EDGE. His levels did no better than made-up levels.

| | His calls | Made-up calls (same stock, same day, prices shifted ±0.4–1.5%) |
|---|---|---|
| Calls scored | 499 | 1,996 |
| Triggered on the day | 203 (41%) | 817 |
| **Success rate when triggered** | **26.1%** | **28.0%** |
| Average result per triggered call (as if traded, before costs) | −0.06% | −0.08% |

- **Difference: −1.9 points.** The bootstrap 95% range is −6.9 to +3.3, so there's no real difference either way.
- **Pre-declared checks:**
  - Beat made-up levels by ≥5 points: ✗.
  - Interval excludes zero: ✗.
- **The sensitivity version gives the same answer.** With the 30 "hold"-worded calls recoded as breakouts: 28.7% vs 29.6% (−0.9 points, range −5.4 to +3.8). No edge.

## What was extracted (100% of the 20 streams)
- **513 stock/ETF calls** with a price:
  - 205 "if it gets above X";
  - 200 "pullback/bounce at X";
  - 59 "if it breaks below X";
  - 35 "fade at X";
  - plus the 30 sensitivity recodes.
- **14 dropped:**
  - 5 levels were more than 15% from the real price (misheard numbers);
  - 9 had no data, including "SpaceX", which has no ticker.
- **Not scorable, excluded and counted:** 234 futures levels (NQ/ES/RTY/YM/GC/CL), 11 yield remarks and 6 crypto.
- **Housekeeping exclusions:** 114 repeats of the same call, 80 unclear numbers, 80 "other day / other" and 36 with no price.
- **Spot-check:** 5 random calls checked against the transcript at their timestamps (NBIS 208–212 fade → 186; AMD retest 491; AMD hold 582–584; NVDA over 228; QQQ over 720 → 726). All 5 were recorded correctly.

## Information-only breakdowns (not part of the verdict; small groups are noisy)
| Group | Triggered | His success | Made-up success | Difference |
|---|---|---|---|---|
| "Get above X" breakouts | 99 | 33.3% | 33.9% | −0.6 |
| Pullback/bounce at X | 57 | 28.1% | 25.0% | +3.1 |
| "Break below X" shorts | 28 | 10.7% | 23.1% | −12.4 |
| Fades at supply | 19 | 5.3% | 13.7% | −8.4 |
| Index ETFs (SPY/QQQ/IWM) | 58 | 13.8% | 20.0% | −6.2 |
| Single stocks | 145 | 31.0% | 30.5% | +0.5 |
| Calls with a stated target | 74 | 12.2% | 15.8% | −3.6 |
| "Top watch" names | 29 | 31.0% | 22.9% | +8.2 (but −0.34% average result) |
| MU | 3 | 1 of 3 | — | too few to judge |

## Plain takeaway
- **59% of his calls never set up on the day.** When they did, about 1 in 4 reached his target before breaking his level, the same as made-up levels nearby.
- **His bearish calls (shorts, fades) and his SPY/QQQ calls were worse than made-up levels;** his bullish stock calls were about equal.
- **The only group that looked better, "top watch", is 29 calls,** with a negative average result. That's not evidence.
- **The free premarket streams are fine for market colour and learning the vocabulary,** but on this month of data his levels don't contain information you can't get from any nearby round number.
- **Test record: 12 pre-declared tests; none showed an edge over simple alternatives.**
