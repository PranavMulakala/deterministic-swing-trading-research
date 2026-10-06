"""Descriptive study (Oct 6, owner's question; NOT a pre-declared test, and Plan B is unchanged): when during the
regular session does LITE move most, when does it tend to rise or fall, and when do the day's high and low usually
happen? Every 5-minute bar from 9:30 to 16:00 ET, Oct 2023 - Sep 2026 (SIP, raw), with SPY over the same days for
comparison. Research only.

  PYTHONPATH=src:. .venv/bin/python -m research.lite_intraday_timing_v1.study
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import gzip
import json
import math
from pathlib import Path
import statistics
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
FILES = {"LITE": ROOT / "outputs/lite_history/LITE_5min_sip_2022-01-01_2026-09-28.json.gz",
         "SPY": ROOT / "outputs/crt_sweep_data/SPY_5min_sip_2016-01-01_2026-10-02.json.gz"}
OUT = ROOT / "output/lite-intraday-timing-20261006.json"
NY = ZoneInfo("America/New_York")
WINDOW = ("2023-10-02", "2026-09-28")
HALVES = (("Oct 2023 - Mar 2025", "2023-10-02", "2025-03-31"), ("Apr 2025 - Sep 2026", "2025-04-01", "2026-09-28"))
SLOTS = list(range(570, 960, 5))                       # bar start, minutes after midnight ET


def label(m):
    return f"{m // 60}:{m % 60:02d}"


def sessions(path):
    """{date: {minute: (o, h, l, c, v)}} for regular-session bars."""
    with gzip.open(path, "rt") as f:
        rows = json.load(f)
    days = defaultdict(dict)
    for r in rows:
        t = datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(NY)
        m = t.hour * 60 + t.minute
        d = t.date().isoformat()
        if 570 <= m < 960 and WINDOW[0] <= d <= WINDOW[1]:
            days[d][m] = (r["o"], r["h"], r["l"], r["c"], r["v"])
    return {d: b for d, b in days.items() if len(b) >= 75 and 570 in b and 955 in b}   # full sessions only


def day_rows(bars):
    """Per slot: (return of that bar vs the previous bar's close, or open for 9:30), cumulative from the open."""
    o = bars[570][0]
    prev, out = o, {}
    for m in SLOTS:
        if m not in bars:
            continue
        c = bars[m][3]
        out[m] = (c / prev - 1, c / o - 1)
        prev = c
    return out


def tstat(xs):
    if len(xs) < 3:
        return 0.0
    sd = statistics.stdev(xs)
    return statistics.mean(xs) / (sd / math.sqrt(len(xs))) if sd else 0.0


def p_two_sided(t):
    return math.erfc(abs(t) / math.sqrt(2))


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def extreme_times(bars):
    hi = max(SLOTS, key=lambda m: (bars[m][1] if m in bars else -1e18, -m))
    lo = min(SLOTS, key=lambda m: (bars[m][2] if m in bars else 1e18, m))
    return hi, lo


def bucket(m):
    return label(570 + (m - 570) // 30 * 30)


def analyse(days, dates):
    per_slot = defaultdict(list)
    cum = defaultdict(list)
    vol_share = defaultdict(list)
    hi_b, lo_b = defaultdict(int), defaultdict(int)
    hi_b_up, lo_b_up, hi_b_dn, lo_b_dn = (defaultdict(int) for _ in range(4))
    up_days = 0
    for d in dates:
        bars = days[d]
        rows = day_rows(bars)
        total_v = sum(b[4] for b in bars.values())
        for m, (r, c) in rows.items():
            per_slot[m].append(r)
            cum[m].append(c)
            vol_share[m].append(bars[m][4] / total_v if total_v else 0)
        hi, lo = extreme_times(bars)
        hi_b[bucket(hi)] += 1
        lo_b[bucket(lo)] += 1
        up = bars[955][3] > bars[570][0]
        up_days += up
        (hi_b_up if up else hi_b_dn)[bucket(hi)] += 1
        (lo_b_up if up else lo_b_dn)[bucket(lo)] += 1
    n = len(dates)
    slots = []
    for m in SLOTS:
        xs = per_slot[m]
        t = tstat(xs)
        slots.append({"time": label(m), "mean_pct": round(100 * statistics.mean(xs), 4),
                      "median_pct": round(100 * statistics.median(xs), 4),
                      "up_share_pct": round(100 * sum(x > 0 for x in xs) / len(xs), 1),
                      "avg_abs_move_pct": round(100 * statistics.mean(abs(x) for x in xs), 3),
                      "volume_share_pct": round(100 * statistics.mean(vol_share[m]), 2),
                      "above_open_share_pct": round(100 * sum(x > 0 for x in cum[m]) / len(cum[m]), 1),
                      "avg_vs_open_pct": round(100 * statistics.mean(cum[m]), 3),
                      "t": round(t, 2), "p": p_two_sided(t)})
    for s, ph in zip(slots, holm([s["p"] for s in slots])):
        s["p_holm"] = round(ph, 4)
        s["p"] = round(s["p"], 4)
    pct = lambda dct, k: {b: round(100 * v / k, 1) for b, v in sorted(dct.items(), key=lambda kv: (len(kv[0]), kv[0]))}
    return {"days": n, "up_days_pct": round(100 * up_days / n, 1), "slots": slots,
            "high_time_pct": pct(hi_b, n), "low_time_pct": pct(lo_b, n),
            "high_time_pct_up_days": pct(hi_b_up, max(up_days, 1)), "low_time_pct_up_days": pct(lo_b_up, max(up_days, 1)),
            "high_time_pct_down_days": pct(hi_b_dn, max(n - up_days, 1)),
            "low_time_pct_down_days": pct(lo_b_dn, max(n - up_days, 1))}


def plan_b_days(days, dates):
    """Days the 10:00 rule would fire (dip >= 1% below the open by 10:00, still below the open at 10:00): when did the
    day's low come, and where did LITE close vs the 10:00 price?"""
    out = {"signal_days": 0, "low_before_10": 0, "low_10_to_12": 0, "low_12_to_14": 0, "low_after_14": 0,
           "close_above_1000_price": 0, "max_gain_after_1000_pct": []}
    for d in dates:
        b = days[d]
        o = b[570][0]
        win = [m for m in range(570, 600, 5) if m in b]
        if 595 not in b or min(b[m][2] for m in win) > o * 0.99 or b[595][3] >= o:
            continue
        out["signal_days"] += 1
        _, lo = extreme_times(b)
        key = "low_before_10" if lo < 600 else "low_10_to_12" if lo < 720 else "low_12_to_14" if lo < 840 else "low_after_14"
        out[key] += 1
        p10 = b[595][3]
        out["close_above_1000_price"] += b[955][3] > p10
        out["max_gain_after_1000_pct"].append(max(b[m][1] for m in SLOTS if m >= 600 and m in b) / p10 - 1)
    g = out.pop("max_gain_after_1000_pct")
    n = max(out["signal_days"], 1)
    out.update({k: round(100 * v / n, 1) for k, v in list(out.items()) if k != "signal_days"})
    out["reached_plus_2pct_same_day_pct"] = round(100 * sum(x >= 0.02 for x in g) / n, 1)
    out["median_best_gain_after_1000_pct"] = round(100 * statistics.median(g), 2) if g else None
    return out


def main():
    data = {s: sessions(p) for s, p in FILES.items()}
    common = sorted(set(data["LITE"]) & set(data["SPY"]))
    out = {"note": "descriptive, not a pre-declared test; Plan B unchanged", "window": WINDOW, "days": len(common)}
    for s in ("LITE", "SPY"):
        out[s] = analyse(data[s], common)
        out[s]["halves"] = {name: analyse(data[s], [d for d in common if a <= d <= b]) for name, a, b in HALVES}
    out["LITE"]["plan_b_signal_days"] = plan_b_days(data["LITE"], common)
    for name, a, b in HALVES:
        out["LITE"]["halves"][name]["plan_b_signal_days"] = plan_b_days(data["LITE"], [d for d in common if a <= d <= b])
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"days": out["days"], "up_days": out["LITE"]["up_days_pct"]}, indent=1))


if __name__ == "__main__":
    main()
