"""Quarterly revenue per company from the saved SEC frames (test #20). Pure functions; no network.

For each calendar quarter, a company's revenue comes from the highest-priority revenue tag that has it. A fiscal
year's untagged quarter is derived per tag as the fiscal-year total minus its three tagged quarters (by their own dates,
so June or September fiscal years work too). Each value keeps its period end date, which decides when it counts as known
(period end + the plan's lag).
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
    """{cik: {"2024Q3": (end_date, revenue), ...}}: the first revenue tag (priority order) wins each quarter.

    A fiscal year's missing quarter (its Q4, whatever the calendar) is derived per tag as the fiscal-year total minus
    the three quarters of the same tag that fall inside it (all dated by their own start/end); result must be > 0."""
    result = {}
    for c in CONCEPTS:
        qrows, yrows = frames.get(c, {}).get("q", {}), frames.get(c, {}).get("y", {})
        for cik, rows in qrows.items():
            for label, start, end, val in rows:
                result.setdefault(cik, {}).setdefault(label, (end, val))
        for cik, years in yrows.items():
            mine = qrows.get(cik, [])
            for ys, ye, total in years:
                lo = date.fromisoformat(ys) - timedelta(days=10)
                hi = date.fromisoformat(ye) + timedelta(days=10)
                inside = [r for r in mine if date.fromisoformat(r[1]) >= lo and date.fromisoformat(r[2]) <= hi]
                if len(inside) != 3:
                    continue
                missing = total - sum(r[3] for r in inside)
                last_end = max(date.fromisoformat(r[2]) for r in inside)
                if missing <= 0 or last_end >= date.fromisoformat(ye):
                    continue
                start = (last_end + timedelta(days=1)).isoformat()
                result.setdefault(cik, {}).setdefault(quarter_label(start, ye), (ye, missing))
    return result


def prev_label(label, back=1):
    y, q = int(label[:4]), int(label[5])
    n = y * 4 + (q - 1) - back
    return f"{n // 4}Q{n % 4 + 1}"


def fingerprint(quarters, as_of, lag_days=90):
    """The plan's numbers for the latest quarter known by `as_of`, or None if any needed quarter is missing.

    Returns (q0_revenue, g0, g1, g2) with growth versus the same quarter a year earlier."""
    cutoff = date.fromisoformat(as_of) - timedelta(days=lag_days)
    known = [lab for lab, (end, _) in quarters.items() if date.fromisoformat(end) <= cutoff]
    if not known:
        return None
    q0 = max(known)
    labels = [q0, prev_label(q0), prev_label(q0, 2)]
    vals = []
    for lab in labels:
        year_ago = prev_label(lab, 4)
        if lab not in quarters or year_ago not in quarters:
            return None
        now, before = quarters[lab][1], quarters[year_ago][1]
        if now <= 0 or before <= 0:
            return None
        vals.append(now / before - 1)
    return quarters[q0][1], vals[0], vals[1], vals[2]


def flagged(fp, min_rev=50e6, min_growth=0.25, min_accel=0.10, need_accel=True):
    """True if the fingerprint passes the plan's size, growth and speeding-up rules."""
    if fp is None:
        return False
    rev, g0, g1, g2 = fp
    if rev < min_rev or g0 < min_growth:
        return False
    return (g0 - g1 >= min_accel and g1 >= g2) if need_accel else True
