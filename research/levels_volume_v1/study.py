"""Pre-declared test #22, a correlation study (plan: output/LEVELS_SWEEPS_VOLUME_STUDY_PLAN_20261006.md): do previous-day,
premarket and hourly-candle levels, liquidity sweeps and volume spikes tell us anything about what momentum stocks do
next, beyond chance? Research only; no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.levels_volume_v1.study

Every level is compared with placebo levels a little above and below it (same stock, same day). Daily tests use the
split-adjusted bars from test #21's download; "momentum" = top 20% of liquid stocks (raw close > $10, 60-day dollar
volume >= $50M) by 6-month return, all at the prior close. Intervals come from resampling whole trading days.
"""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
import random

from research.levels_volume_v1.fetch import groups
from research.provenance_v1.provenance import write_manifest
from research.stocks_in_play_orb_v1.fetch import NOT_STOCKS

ROOT = Path(__file__).resolve().parents[2]
DAILY = ROOT / "outputs/orb_play_data/daily"
SPY_FILE = ROOT / "outputs/orb_play_data/SPY_all.json.gz"
INTRA = ROOT / "outputs/levels_volume_data"
OUT = ROOT / "output/levels-volume-study-results.json"
DETAIL = INTRA / "study_detail.json.gz"

MIN_PRICE, MIN_DVOL, DVOL_DAYS, MOM_DAYS, MOM_TOP = 10.0, 50e6, 60, 126, 0.20
LEVEL_PLACEBOS = (-0.01, -0.005, 0.005, 0.01)
SWEEP_PLACEBOS = (-0.02, -0.01, 0.01, 0.02)
SPIKE_MULT, CALM_MULT, SPIKE_MOVE, VOL_DAYS = 2.0, 1.5, 0.04, 50
BUCKETS = ((0.04, 0.06), (0.06, 0.10), (0.10, math.inf))
HORIZONS = (1, 5, 20)
STALL_MIN, RETURN_MIN = 0.05, 0.0025
DAILY_MAIN, DAILY_STRESS = ("2020-01-02", "2026-10-02"), ("2016-01-01", "2019-12-31")
DAILY_HALVES = (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2026", "2023-01-01", "2026-12-31"))
INTRA_MAIN = ("2022-01-03", "2026-10-02")
INTRA_HALVES = (("2022-2023", "2022-01-01", "2023-12-31"), ("2024-2026", "2024-01-01", "2026-12-31"))
BOOT, SEED = 1000, 22


def read(path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


# ---------- event rows (pure) ----------

def resistance(o, h, c, level):
    """A level above the open: (eligible, touched, stalled = closed back below it, close vs level once touched)."""
    if level is None or not o < level:
        return [0, 0, 0, 0.0]
    if h < level:
        return [1, 0, 0, 0.0]
    return [1, 1, int(c < level), c / level - 1]


def support(o, low, c, level):
    """A level below the open: (eligible, touched, held = closed back above it, close vs level once touched)."""
    if level is None or not o > level:
        return [0, 0, 0, 0.0]
    if low > level:
        return [1, 0, 0, 0.0]
    return [1, 1, int(c > level), c / level - 1]


def level_row(kind, o, h_or_l, c, level, placebos=LEVEL_PLACEBOS):
    """The real level then each placebo, 4 numbers each."""
    out = []
    for lv in [level] + [None if level is None else level * (1 + k) for k in placebos]:
        out += (resistance if kind == "resistance" else support)(o, h_or_l, c, lv)
    return out


def sweep_row(low, high, c, level, after, side, placebos=SWEEP_PLACEBOS):
    """Sweep and reclaim: side "low" = traded under the level and closed above it; "high" = over it, closed below.
    (count, next-day excess return) for the real level then each placebo."""
    out = []
    for lv in [level] + [level * (1 + k) for k in placebos]:
        hit = (low < lv < c) if side == "low" else (high > lv > c)
        out += [1, after] if hit and after is not None else [0, 0.0]
    return out


def bucket_of(move):
    m = abs(move)
    return next((b for b, (lo, hi) in enumerate(BUCKETS) if lo <= m < hi), None)


def spike_row(move, vol, avg_vol, forward, up=True):
    """(spike count, spike sum, calm count, calm sum) per gain bucket for one day; forward = excess return or None."""
    out = [0, 0.0, 0, 0.0] * len(BUCKETS)
    if forward is None or not avg_vol or not (move >= SPIKE_MOVE if up else move <= -SPIKE_MOVE):
        return out
    b = bucket_of(move)
    if vol >= SPIKE_MULT * avg_vol:
        out[4 * b], out[4 * b + 1] = 1, forward
    elif vol < CALM_MULT * avg_vol:
        out[4 * b + 2], out[4 * b + 3] = 1, forward
    return out


# ---------- effects from summed rows ----------

def stall_effect(s):
    """Stall (or hold) rate at the real level minus the placebos' average; None if any rate is undefined."""
    rates = [s[4 * i + 2] / s[4 * i + 1] if s[4 * i + 1] else None for i in range(5)]
    if any(r is None for r in rates):
        return None
    return rates[0] - sum(rates[1:]) / 4


def sweep_effect(s):
    means = [s[2 * i + 1] / s[2 * i] if s[2 * i] else None for i in range(5)]
    if any(m is None for m in means):
        return None
    return means[0] - sum(means[1:]) / 4


def spike_effect(s):
    """Spike minus calm average forward return within each gain bucket, weighted by spike counts."""
    num = den = 0.0
    for b in range(len(BUCKETS)):
        n_s, sum_s, n_c, sum_c = s[4 * b:4 * b + 4]
        if n_s and n_c:
            num += n_s * (sum_s / n_s - sum_c / n_c)
            den += n_s
    return num / den if den else None


def summed(agg, dates):
    rows = [agg[d] for d in dates if d in agg]
    return [sum(col) for col in zip(*rows)] if rows else None


def boot(agg, dates, stat, n=BOOT, seed=SEED):
    """Effect on these dates, its 95% interval and two-sided p, resampling whole days."""
    rows = [agg[d] for d in dates if d in agg]
    if not rows:
        return None
    est = stat([sum(col) for col in zip(*rows)])
    if est is None:
        return None
    rng, draws = random.Random(seed), []
    for _ in range(n):
        v = stat([sum(col) for col in zip(*rng.choices(rows, k=len(rows)))])
        if v is not None:
            draws.append(v)
    draws.sort()
    below = sum(v <= 0 for v in draws) / len(draws)
    above = sum(v >= 0 for v in draws) / len(draws)
    return {"effect": est, "low": draws[int(0.025 * len(draws))], "high": draws[int(0.975 * len(draws)) - 1],
            "p": max(min(1.0, 2 * min(below, above)), 1 / len(draws)), "days": len(rows)}


def holm(ps):
    """Holm-adjusted p-values, same order as given (None stays None)."""
    idx = sorted((p, i) for i, p in enumerate(ps) if p is not None)
    out, running = [None] * len(ps), 0.0
    for rank, (p, i) in enumerate(idx):
        running = max(running, min(1.0, (len(idx) - rank) * p))
        out[i] = running
    return out


def add(agg, date, key, row):
    if not any(row):
        return
    cur = agg.setdefault(key, {}).get(date)
    agg[key][date] = row if cur is None else [a + b for a, b in zip(cur, row)]


# ---------- daily part ----------

def stock_files():
    return sorted(p for p in DAILY.glob("*.json.gz") if p.name[:-8] not in NOT_STOCKS)


def prior_series(raw, split):
    """Per day k: (liquid, 6-month return) as of the close before day k, or None without enough history.
    Liquid = raw close > $10 and 60-day average dollar volume >= $50M."""
    pdv = [0.0]
    for r in raw:
        pdv.append(pdv[-1] + r[3] * r[4])
    out = [None] * len(raw)
    for k in range(max(DVOL_DAYS, MOM_DAYS + 1) + 1, len(raw)):
        j = k - 1
        dvol = (pdv[j + 1] - pdv[j + 1 - DVOL_DAYS]) / DVOL_DAYS
        out[k] = (raw[j][3] > MIN_PRICE and dvol >= MIN_DVOL, split[j][3] / split[j - MOM_DAYS][3] - 1)
    return out


def momentum_cutoffs(files):
    """{date: 6-month return at the 80th percentile of that day's liquid stocks}."""
    cross = {}
    for p in files:
        b = read(p)
        for d, m in zip(b["date"], prior_series(b["raw"], b["split"])):
            if m and m[0]:
                cross.setdefault(d, []).append(m[1])
    return {d: sorted(v)[int((1 - MOM_TOP) * len(v))] for d, v in cross.items()}


def daily_events(b, cutoffs, spy, agg, per_stock):
    dates, raw, split = b["date"], b["raw"], b["split"]
    n = len(dates)
    vols = [s[4] for s in split]
    prior = prior_series(raw, split)
    for k in range(1, n):
        m = prior[k]
        if not (m and m[0]):
            continue
        d = dates[k]
        groups = ["liquid"] + (["momentum"] if d in cutoffs and m[1] >= cutoffs[d] else [])
        po, ph, pl, pc = split[k - 1][:4]
        o, h, low, c = split[k][:4]

        def excess(hz):
            if k + hz >= n or dates[k] not in spy or dates[k + hz] not in spy:
                return None
            return split[k + hz][3] / c - 1 - (spy[dates[k + hz]] / spy[dates[k]] - 1)

        nxt = excess(1)
        rows = {"h1": level_row("resistance", o, h, c, ph), "pdl_support": level_row("support", o, low, c, pl),
                "h4": sweep_row(low, h, c, pl, nxt, "low"), "h4_mirror_pdh": sweep_row(low, h, c, ph, nxt, "high")}
        move = c / pc - 1
        avg = sum(vols[k - VOL_DAYS:k]) / VOL_DAYS if k >= VOL_DAYS else None
        for hz in HORIZONS:
            fwd = excess(hz)
            rows[f"h5_{hz}d"] = spike_row(move, vols[k], avg, fwd)
            rows[f"h5_down_{hz}d"] = spike_row(move, vols[k], avg, fwd, up=False)
        for g in groups:
            for key, row in rows.items():
                add(agg[g], d, key, row)
            st = per_stock.setdefault(g, [0] * 11)
            r1, r4, r5 = rows["h1"], rows["h4"], rows["h5_5d"]
            for i, x in enumerate(r1[:3] + r4[:2] + [r5[0], r5[2], r5[4], r5[6], r5[8], r5[10]]):
                st[i] += x


# ---------- intraday part ----------

def day_shape(bars):
    """(open, high, low, close) of a regular session from its 5-minute bars."""
    return bars[0][1], max(x[2] for x in bars), min(x[3] for x in bars), bars[-1][4]


def hourly_levels(bars, open_today):
    """Yesterday's hourly-candle highs above today's open, excluding yesterday's high: the lowest one (or None);
    plus the lower of yesterday's two 4-hour candle highs if it's above the open."""
    highs = {}
    for m, _, h, _, _, _ in bars:
        b = (m - 570) // 60
        highs[b] = max(highs.get(b, h), h)
    top = max(highs.values())
    one_hour = min((v for v in highs.values() if v != top and v > open_today), default=None)
    first = max((x[2] for x in bars if x[0] < 810), default=None)
    second = max((x[2] for x in bars if x[0] >= 810), default=None)
    four = None
    if first is not None and second is not None and first != second:
        four = min(first, second)
        four = four if four > open_today else None
    return one_hour, four


def intraday_events(b, agg, per_stock):
    for k in range(1, len(b["date"])):
        y, t = b["bars"][k - 1], b["bars"][k]
        if not y or not t:
            continue
        d = b["date"][k]
        o, h, low, c = day_shape(t)
        pdh = max(x[2] for x in y)
        one_hour, four = hourly_levels(y, o)
        pre = b["pre"][k]
        rows = {"h2": level_row("resistance", o, h, c, pre[0] if pre else None),
                "h3": level_row("resistance", o, h, c, one_hour),
                "h3_4h": level_row("resistance", o, h, c, four),
                "h1_intraday": level_row("resistance", o, h, c, pdh),
                "pml_support": level_row("support", o, low, c, pre[1] if pre else None)}
        for key, row in rows.items():
            add(agg, d, key, row)
        st = per_stock
        for i, x in enumerate(rows["h2"][:3] + rows["h3"][:3]):
            st[i] += x


# ---------- reporting ----------

def window_dates(agg_key, lo, hi):
    return sorted(d for d in agg_key if lo <= d <= hi)


def rates(s):
    """Plain-word numbers for a level row: reach and stall/hold rates, real vs placebo average."""
    if not s:
        return None
    reach = [s[4 * i + 1] / s[4 * i] if s[4 * i] else None for i in range(5)]
    stall = [s[4 * i + 2] / s[4 * i + 1] if s[4 * i + 1] else None for i in range(5)]
    past = s[3] / s[1] if s[1] else None
    pl = [x for x in stall[1:] if x is not None]
    return {"events": int(s[0]), "touched": int(s[1]), "reach_pct": _pct(reach[0]),
            "reach_pct_placebo_half_pct": _pct((reach[2] + reach[3]) / 2) if reach[2] and reach[3] else None,
            "stall_pct": _pct(stall[0]), "stall_pct_placebos": _pct(sum(pl) / len(pl)) if pl else None,
            "avg_close_vs_level_pct": _pct(past)}


def _pct(x):
    return None if x is None else round(100 * x, 2)


def judge(main, halves, threshold):
    if not main or any(h is None for h in halves):
        return False
    same = all((h["effect"] > 0) == (main["effect"] > 0) and h["p"] < 0.05 for h in halves)
    return main.get("p_holm", 1) < 0.05 and same and abs(main["effect"]) >= threshold


def main():
    files = stock_files()
    spy_b = read(SPY_FILE)
    spy = {d: x[3] for d, x in zip(spy_b["date"], spy_b["bars"])}
    cutoffs = momentum_cutoffs(files)
    agg, per_stock = {"liquid": {}, "momentum": {}}, {}
    for p in files:
        ps = {}
        daily_events(read(p), cutoffs, spy, agg, ps)
        if ps:
            per_stock[p.name[:-8]] = ps
    intra = {"main": {}, "ai_hardware": {}, "LITE": {}}
    intra_stock = {}
    main_group, extra = groups()
    for sym in main_group + extra:
        path = INTRA / f"{sym}.json.gz"
        if not path.exists():
            continue
        st = intra_stock.setdefault(sym, [0] * 6)
        intraday_events(read(path), intra["main" if sym in main_group else "ai_hardware"], st)
        if sym == "LITE":
            intraday_events(read(path), intra["LITE"], [0] * 6)

    tests = [("H1 previous-day high stall", agg["momentum"].get("h1", {}), stall_effect, DAILY_MAIN, DAILY_HALVES, STALL_MIN),
             ("H2 premarket high stall", intra["main"].get("h2", {}), stall_effect, INTRA_MAIN, INTRA_HALVES, STALL_MIN),
             ("H3 yesterday's 1-hour candle high stall", intra["main"].get("h3", {}), stall_effect, INTRA_MAIN, INTRA_HALVES, STALL_MIN),
             ("H4 sweep of yesterday's low, next day", agg["momentum"].get("h4", {}), sweep_effect, DAILY_MAIN, DAILY_HALVES, RETURN_MIN),
             ("H5 up-day volume spike, next 5 days", agg["momentum"].get("h5_5d", {}), spike_effect, DAILY_MAIN, DAILY_HALVES, RETURN_MIN)]
    primary = []
    for name, a, stat, win, halves, thr in tests:
        res = boot(a, window_dates(a, *win), stat)
        hs = [boot(a, window_dates(a, lo, hi), stat) for _, lo, hi in halves]
        primary.append({"name": name, "main": res, "halves": dict(zip([h[0] for h in halves], hs)), "threshold": thr})
    adj = holm([t["main"]["p"] if t["main"] else None for t in primary])
    for t, p in zip(primary, adj):
        if t["main"]:
            t["main"]["p_holm"] = p
        t["real_correlation"] = judge(t["main"], list(t["halves"].values()), t["threshold"])
    for t, (_, a, stat, _, _, _) in zip(primary[:1] + primary[3:], [tests[0], tests[3], tests[4]]):
        t["stress_2016_2019"] = boot(a, window_dates(a, *DAILY_STRESS), stat)
    info = {}
    for g in ("momentum", "liquid"):
        for key in ("h1", "pdl_support"):
            info[f"{g}_{key}_rates"] = rates(summed(agg[g].get(key, {}), window_dates(agg[g].get(key, {}), *DAILY_MAIN)))
        for key, stat in (("h4", sweep_effect), ("h4_mirror_pdh", sweep_effect)):
            s = summed(agg[g].get(key, {}), window_dates(agg[g].get(key, {}), *DAILY_MAIN))
            info[f"{g}_{key}"] = {"effect_pct": _pct(stat(s)) if s else None, "events": int(s[0]) if s else 0,
                                  "avg_next_day_excess_pct": _pct(s[1] / s[0]) if s and s[0] else None}
        for hz in HORIZONS:
            for key in (f"h5_{hz}d", f"h5_down_{hz}d"):
                s = summed(agg[g].get(key, {}), window_dates(agg[g].get(key, {}), *DAILY_MAIN))
                info[f"{g}_{key}"] = {"effect_pct": _pct(spike_effect(s)) if s else None,
                                      "spikes": int(sum(s[0::4])) if s else 0, "calm": int(sum(s[2::4])) if s else 0}
    for g, a in intra.items():
        for key in ("h1_intraday", "h2", "h3", "h3_4h", "pml_support"):
            info[f"intraday_{g}_{key}_rates"] = rates(summed(a.get(key, {}), window_dates(a.get(key, {}), *INTRA_MAIN)))
    lite = read(INTRA / "LITE_daily_recent.json.gz") if (INTRA / "LITE_daily_recent.json.gz").exists() else None
    if lite:
        v, c = [x[4] for x in lite["bars"]], [x[3] for x in lite["bars"]]
        info["lite_latest_day"] = {"date": lite["date"][-1], "volume_vs_50d_avg": round(v[-1] / (sum(v[-51:-1]) / 50), 2),
                                   "move_pct": _pct(c[-1] / c[-2] - 1), "close": c[-1]}
    out = {"plan": "output/LEVELS_SWEEPS_VOLUME_STUDY_PLAN_20261006.md", "primary": primary, "info": info,
           "momentum_days": len(cutoffs)}
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
    with gzip.open(DETAIL, "wt") as f:
        json.dump({"cutoffs": cutoffs, "per_stock_daily": per_stock, "per_stock_intraday": intra_stock}, f)
    write_manifest(OUT, code=["research/levels_volume_v1/study.py", "research/levels_volume_v1/fetch.py"],
                   data=[str(SPY_FILE), str(DETAIL)] + [str(INTRA / f"{s}.json.gz") for s in main_group + extra
                                                         if (INTRA / f"{s}.json.gz").exists()],
                   params={"main_daily": DAILY_MAIN, "main_intraday": INTRA_MAIN, "boot": BOOT, "seed": SEED})
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
