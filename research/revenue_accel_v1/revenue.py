"""Quarterly revenue per company from the saved SEC frames (test #20). Pure functions; no network.

Each revenue tag keeps its own quarterly series, so a growth rate always compares a quarter with its year-ago quarter
under the same tag (the first tag, in priority order, that has both). A fiscal year's untagged quarter is derived per tag
as the fiscal-year total minus its three tagged quarters (by their own dates, so June or September fiscal years work
too). Each value keeps its period end date, which decides when it counts as known (period end + the plan's lag).
"""
from __future__ import annotations

from datetime import date, timedelta
import gzip
import json

from research.revenue_accel_v1.fetch_frames import CONCEPTS, OUT, QUARTERS, YEARS, path_for  # noqa: F401


def load_frames():
    """{concept: {"q": {cik: [(label, start, end, val)]}, "y": {cik: [(start, end, val)]}}} from the saved frames."""
    out = {}
    for c in CONCEPTS:
        q, y = {}, {}
        for p in QUARTERS + YEARS:
            path = path_for(c, p)
            if not path.exists():
                continue
            with gzip.open(path, "rt") as f:
                rows = json.load(f)
            for cik, start, end, val in rows:
                if not start:
                    continue
                if len(p) == 8:
                    q.setdefault(int(cik), []).append((p[2:], start, end, float(val)))
                else:
                    y.setdefault(int(cik), []).append((start, end, float(val)))
        out[c] = {"q": q, "y": y}
    return out


def quarter_label(start, end):
    """The calendar quarter holding the period's midpoint (how SEC's frames label quarters)."""
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    mid = a + (b - a) / 2
    return f"{mid.year}Q{(mid.month - 1) // 3 + 1}"


def quarterly(frames):
    """{cik: [{"2024Q3": (end_date, revenue), ...} for each revenue tag, in priority order]}.

    A fiscal year's missing quarter (its Q4, whatever the calendar) is derived per tag as the fiscal-year total minus
    the three quarters of the same tag that fall inside it (all dated by their own start/end); result must be > 0."""
    result = {}
    for k, c in enumerate(CONCEPTS):
        qrows, yrows = frames.get(c, {}).get("q", {}), frames.get(c, {}).get("y", {})
        for cik, rows in qrows.items():
            series = result.setdefault(cik, [{} for _ in CONCEPTS])[k]
            for label, start, end, val in rows:
                series.setdefault(label, (end, val))
            for ys, ye, total in yrows.get(cik, []):
                lo = date.fromisoformat(ys) - timedelta(days=10)
                hi = date.fromisoformat(ye) + timedelta(days=10)
                inside = [r for r in rows if date.fromisoformat(r[1]) >= lo and date.fromisoformat(r[2]) <= hi]
                if len(inside) != 3:
                    continue
                missing = total - sum(r[3] for r in inside)
                last_end = max(date.fromisoformat(r[2]) for r in inside)
                if missing <= 0 or last_end >= date.fromisoformat(ye):
                    continue
                start = (last_end + timedelta(days=1)).isoformat()
                series.setdefault(quarter_label(start, ye), (ye, missing))
    return result


def prev_label(label, back=1):
    y, q = int(label[:4]), int(label[5])
    n = y * 4 + (q - 1) - back
    return f"{n // 4}Q{n % 4 + 1}"


def fingerprint(series, as_of, lag_days=90, max_age_days=200):
    """The plan's numbers for the latest quarter known by `as_of`, or None if it's stale or a needed quarter is missing.

    `series`: one company's per-tag quarterly revenue (from `quarterly`). Only quarters that ended at least `lag_days`
    before `as_of` count. Q0 is the latest of them under any tag; it must have ended within `max_age_days` of `as_of`
    (a company that stopped filing isn't current). Each growth rate uses the first tag holding both the quarter and its
    year-ago quarter. Returns (q0_revenue, g0, g1, g2); q0_revenue is from the tag used for g0."""
    day = date.fromisoformat(as_of)
    cutoff = day - timedelta(days=lag_days)
    known = [{lab: v for lab, (end, v) in s.items() if date.fromisoformat(end) <= cutoff} for s in series]
    ends = {}
    for s in reversed(series):
        for lab, (end, _) in s.items():
            if date.fromisoformat(end) <= cutoff:
                ends[lab] = end
    if not ends:
        return None
    q0 = max(ends)
    if (day - date.fromisoformat(ends[q0])).days > max_age_days:
        return None
    out = []
    for lab in (q0, prev_label(q0), prev_label(q0, 2)):
        year_ago = prev_label(lab, 4)
        pair = next(((s[lab], s[year_ago]) for s in known if lab in s and year_ago in s), None)
        if pair is None or pair[0] <= 0 or pair[1] <= 0:
            return None
        out.append(pair)
    return out[0][0], out[0][0] / out[0][1] - 1, out[1][0] / out[1][1] - 1, out[2][0] / out[2][1] - 1


def flagged(fp, min_rev=50e6, min_growth=0.25, min_accel=0.10, need_accel=True):
    """True if the fingerprint passes the plan's size, growth and speeding-up rules."""
    if fp is None:
        return False
    rev, g0, g1, g2 = fp
    if rev < min_rev or g0 < min_growth:
        return False
    return (g0 - g1 >= min_accel and g1 >= g2) if need_accel else True
