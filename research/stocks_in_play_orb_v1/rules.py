"""Shared selection rules for test #21, the "Stocks in Play" opening-range breakout
(plan: output/STOCKS_IN_PLAY_ORB_TEST_PLAN_20261005.md). Used by the download and by the backtest. Pure functions.

Every filter is in that day's own (as-traded) units: the previous 14 trading days' split-adjusted bars are converted
with the day's split factor, so a split never fakes a huge range or a sudden volume jump.
"""
from __future__ import annotations

LOOKBACK, MIN_PRICE, MIN_AVG_VOLUME, MIN_ATR, MIN_RV, TOP_N = 14, 5.0, 1_000_000.0, 0.50, 1.0, 20
NAN = float("nan")


def daily_metrics(raw, split):
    """raw, split: [o, h, l, c, v] per trading day (same dates). Returns [(avg volume, ATR, split factor)] per day,
    volume and ATR over the previous 14 days in that day's units (NaN until 15 days of history exist).
    The split factor is raw close / split-adjusted close (e.g. 10 before a 10-for-1 split, 1 after)."""
    factor = [r[3] / s[3] if s[3] else NAN for r, s in zip(raw, split)]
    tr = [NAN] + [max(s[1] - s[2], abs(s[1] - p[3]), abs(s[2] - p[3])) for p, s in zip(split, split[1:])]
    vol = [s[4] for s in split]
    out = []
    for k, f in enumerate(factor):
        if k <= LOOKBACK:
            out.append((NAN, NAN, f))
        else:
            out.append((sum(vol[k - LOOKBACK:k]) / LOOKBACK / f, sum(tr[k - LOOKBACK:k]) / LOOKBACK * f, f))
    return out


def tradeable(open_price, avg_volume, atr, min_price=MIN_PRICE):
    """The paper's universe: opening price > $5, 14-day average volume >= 1M shares, 14-day ATR > $0.50."""
    return open_price > min_price and avg_volume >= MIN_AVG_VOLUME and atr > MIN_ATR


def relative_volume(today, previous):
    """Today's 9:30-9:35 volume over the previous 14 days' average (already in today's share units)."""
    if len(previous) < LOOKBACK:
        return NAN
    avg = sum(previous) / len(previous)
    return today / avg if avg > 0 else NAN


def in_play(candidates, n=TOP_N):
    """candidates: [(symbol, relative volume)] that are tradeable. The n highest with relative volume >= 1.0;
    exact ties by symbol."""
    rows = sorted((-rv, s) for s, rv in candidates if rv >= MIN_RV)
    return [s for _, s in rows[:n]]


def direction(first_bar):
    """First 5-minute candle [o, h, l, c, ...]: up -> 1 (long), down -> -1 (short), unchanged -> 0 (no trade)."""
    return (first_bar[3] > first_bar[0]) - (first_bar[3] < first_bar[0])
