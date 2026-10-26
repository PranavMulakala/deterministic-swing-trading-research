# Plan: Roth "VT 80 + AVUV 20" vs "VT 100" (written 2026-10-08, before any AVUV results were computed)

The owner asked to test this first. The question is whether a 20% US small-cap value tilt (AVUV) is an aggressive
choice worth making in the Roth, given that LITE + MU already make up about 59% of invested money.

**Data.** Alpha Vantage monthly adjusted prices through Sep 2026.
- AVUV actual (ER 0.25%) from Oct 2019.
- Before that, **DFSVX** (DFA US Small Cap Value, ER ~0.30%), shifted to AVUV's ER.
- Proxy check: AVUV vs DFSVX correlation and tracking gap over their common months (reported, not tuned).
- Everything else is the same as the Roth study (`analysis.py`): $5,967 start, $6,695/yr (with the match), December
  rebalance, VT = actual fund (today's-mix proxy before Aug 2008).

**Decision rule.** VT + 20% AVUV is adopted only if all three hold.
1. **Forward model:** the median Roth balance at 55 is at least VT's. The CMA model gives small value 4.8% real,
   the same small-cap value as the 401(k) study.
2. **Cost of being wrong:** if small value earns no premium (AVUV = the market's 4.3% real, minus its 0.25% ER),
   the median at 55 is less than 3% below VT's.
3. **Pain:** in the since-2008 stress window, the worst peak-to-trough drop in dollars is no more than 10% deeper
   than VT's.

**Information only (not part of the verdict):**
- the post-COVID backtest (the main window) in dollars;
- the 2000–2026 backtest;
- the bootstrap Monte Carlo (it replays 2000–2026, a strong era for small value, so it flatters AVUV);
- a +1 point premium sensitivity (5.8%);
- correlation with LITE and MU;
- household look-through.
