"""Independent recount for test #22, written separately from study.py (own parsing, plain loops).

1. The momentum cut-off (80th percentile of liquid stocks' 6-month return) on 5 random days, from all daily files.
2. For 10 random stocks: H1 (previous-day high: eligible / reached / closed back below), H4 (sweep-and-reclaim of
   yesterday's low: count and summed next-day excess return) and H5 (up-day spike and calm counts per gain bucket,
   5-day horizon), for both the liquid and the momentum groups.
3. For 5 random intraday stocks: H2 (premarket high) and H3 (yesterday's nearest 1-hour candle high) counts.

  PYTHONPATH=src:. .venv/bin/python -m research.levels_volume_v1.verify
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
DAILY = ROOT / "outputs/orb_play_data/daily"
INTRA = ROOT / "outputs/levels_volume_data"
SKIP = {"SPY", "BTCUSD", "BTCUSD_BITSTAMP"}


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def history(raw, split, k):
    """(liquid, six-month return) known at the close before day k."""
    if k < 128:
        return None
    j = k - 1
    dollars = 0.0
    for i in range(j - 59, j + 1):
        dollars += raw[i][3] * raw[i][4]
    return raw[j][3] > 10.0 and dollars / 60 >= 50e6, split[j][3] / split[j - 126][3] - 1


def main():
    files = sorted(p for p in DAILY.glob("*.json.gz") if p.name[:-8] not in SKIP)
    detail = read(INTRA / "study_detail.json.gz")
    theirs_cut = detail["cutoffs"]
    rng = random.Random(22)
    sample_days = sorted(rng.sample(sorted(theirs_cut), 5))
    pick = rng.sample(files, 10)
    spy_b = read(ROOT / "outputs/orb_play_data/SPY_all.json.gz")
    spy = {d: x[3] for d, x in zip(spy_b["date"], spy_b["bars"])}
    cross, loaded = {d: [] for d in sample_days}, {}
    for p in files:
        b = read(p)
        if p in pick:
            loaded[p.name[:-8]] = b
        where = {d: i for i, d in enumerate(b["date"])}
        for d in sample_days:
            k = where.get(d)
            h = history(b["raw"], b["split"], k) if k is not None else None
            if h and h[0]:
                cross[d].append(h[1])
    report, ok = {}, True
    for d in sample_days:
        vals = sorted(cross[d])
        mine = vals[int(0.8 * len(vals))]
        same = abs(mine - theirs_cut[d]) < 1e-12
        ok &= same
        report[f"cutoff {d}"] = {"match": same, "independent": round(mine, 6), "study": round(theirs_cut[d], 6)}
    cut_all = theirs_cut                                  # checked on 5 days above; used for the group split below
    for sym, b in loaded.items():
        raw, split, dates = b["raw"], b["split"], b["date"]
        counts = {"liquid": [0] * 11, "momentum": [0] * 11}
        for k in range(1, len(dates)):
            h = history(raw, split, k)
            if not (h and h[0]):
                continue
            groups = ["liquid"] + (["momentum"] if dates[k] in cut_all and h[1] >= cut_all[dates[k]] else [])
            o, hi, lo, c = split[k][:4]
            prev_h, prev_l, prev_c = split[k - 1][1], split[k - 1][2], split[k - 1][3]
            row = [0] * 11
            if o < prev_h:
                row[0] = 1
                if hi >= prev_h:
                    row[1] = 1
                    row[2] = 1 if c < prev_h else 0
            if k + 1 < len(dates) and dates[k] in spy and dates[k + 1] in spy and lo < prev_l < c:
                row[3] = 1
                row[4] = split[k + 1][3] / c - 1 - (spy[dates[k + 1]] / spy[dates[k]] - 1)
            move = c / prev_c - 1
            if move >= 0.04 and k + 5 < len(dates) and dates[k] in spy and dates[k + 5] in spy:
                avg = sum(split[i][4] for i in range(k - 50, k)) / 50
                slot = 0 if move < 0.06 else (1 if move < 0.10 else 2)
                if split[k][4] >= 2 * avg:
                    row[5 + 2 * slot] = 1
                elif split[k][4] < 1.5 * avg:
                    row[6 + 2 * slot] = 1
            for g in groups:
                counts[g] = [a + x for a, x in zip(counts[g], row)]
        theirs = detail["per_stock_daily"].get(sym, {})
        for g in ("liquid", "momentum"):
            t = theirs.get(g, [0] * 11)
            same = all(abs(a - b) < 1e-9 for a, b in zip(counts[g], t))
            ok &= same
            report[f"{sym} {g}"] = {"match": same, "independent": [round(x, 6) for x in counts[g]],
                                    "study": [round(x, 6) for x in t]}
    intra_syms = sorted(detail["per_stock_intraday"])
    for sym in rng.sample(intra_syms, min(5, len(intra_syms))):
        b = read(INTRA / f"{sym}.json.gz")
        mine = [0] * 6
        for k in range(1, len(b["date"])):
            y, t = b["bars"][k - 1], b["bars"][k]
            if not y or not t:
                continue
            o, c = t[0][1], t[-1][4]
            hi = max(x[2] for x in t)
            pre = b["pre"][k]
            if pre and o < pre[0]:
                mine[0] += 1
                if hi >= pre[0]:
                    mine[1] += 1
                    mine[2] += c < pre[0]
            hours = {}
            for x in y:
                slot = (x[0] - 570) // 60
                hours[slot] = max(hours.get(slot, x[2]), x[2])
            top = max(hours.values())
            above = [v for v in hours.values() if v != top and v > o]
            if above:
                lvl = min(above)
                mine[3] += 1
                if hi >= lvl:
                    mine[4] += 1
                    mine[5] += c < lvl
        theirs = detail["per_stock_intraday"][sym]
        same = mine == theirs
        ok &= same
        report[f"intraday {sym}"] = {"match": same, "independent": mine, "study": theirs}
    print(json.dumps({"all_match": ok, **report}, indent=1))


if __name__ == "__main__":
    main()
