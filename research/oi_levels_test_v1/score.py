"""Scoring for pre-declared test #12: Options Insider levels vs placebo levels
(output/OPTIONS_INSIDER_LEVELS_TEST_PLAN_20261005.md). Research only; no orders.

  PYTHONPATH=src:. .venv/bin/python -m research.oi_levels_test_v1.score

Reads the blind-extracted calls in outputs/tmp/oi_streams/*_calls.json, downloads Alpaca SIP 5-minute bars for each
(symbol, stream date) with the LITE paper account's read-only data keys (cached in outputs/oi_levels_data/), scores
every call and its 4 shifted placebos, and writes output/oi-levels-test-results.json.

One fill detail the plan left open: a bounce (fade) entry is a resting limit at the zone edge, so when the trigger
bar opens beyond the edge the fill is that bar's open (min(edge, open) for bounces, max(edge, open) for fades).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
import glob
import json
from pathlib import Path
import random
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
CALLS = ROOT / "outputs/tmp/oi_streams"
CACHE = ROOT / "outputs/oi_levels_data"
OUT = ROOT / "output/oi-levels-test-results.json"
NY = ZoneInfo("America/New_York")
INDEX_ETFS = {"SPY", "QQQ", "IWM", "DIA"}
STOCK_SHIFTS, INDEX_SHIFTS = (-0.015, -0.0075, 0.0075, 0.015), (-0.0075, -0.00375, 0.00375, 0.0075)
TYPES = ("LONG_IF_ABOVE", "SHORT_IF_BELOW", "SUPPORT_BOUNCE", "RESISTANCE_FADE")


def score(call, bars, shift=0.0):
    """bars: regular-session 5-minute bars [{'o','h','l','c'}...] for the call's day. Returns a result dict."""
    lo, hi = call["level_low"] * (1 + shift), call["level_high"] * (1 + shift)
    a, b = min(lo, hi), max(lo, hi)
    target = call["target"] * (1 + shift) if call.get("target") is not None else None
    p = 0.005 if call["symbol"] in INDEX_ETFS else 0.01
    kind = call["type"]
    long_side = kind in ("LONG_IF_ABOVE", "SUPPORT_BOUNCE")
    trig = None
    for i, x in enumerate(bars):
        if (kind == "LONG_IF_ABOVE" and x["c"] > b) or (kind == "SHORT_IF_BELOW" and x["c"] < a) or \
                (kind == "SUPPORT_BOUNCE" and x["l"] <= b) or (kind == "RESISTANCE_FADE" and x["h"] >= a):
            trig = i
            break
    if trig is None:
        return {"status": "not_triggered"}
    t = bars[trig]
    if kind in ("LONG_IF_ABOVE", "SHORT_IF_BELOW"):
        entry = t["c"]
    elif kind == "SUPPORT_BOUNCE":
        entry = min(b, t["o"])
    else:
        entry = max(a, t["o"])
    if target is None:
        target = entry * (1 + p) if long_side else entry * (1 - p)
    if (long_side and target <= entry) or (not long_side and target >= entry):
        return {"status": "target_already_reached"}

    def pct(exit_px):
        return (exit_px / entry - 1) * 100 * (1 if long_side else -1)

    # A bounce/fade can fail on its own trigger bar's close; the target is checked from the next bar on.
    if kind == "SUPPORT_BOUNCE" and t["c"] < a:
        return {"status": "failure", "pct": pct(t["c"]), "bar": trig}
    if kind == "RESISTANCE_FADE" and t["c"] > b:
        return {"status": "failure", "pct": pct(t["c"]), "bar": trig}
    for j in range(trig + 1, len(bars)):
        x = bars[j]
        hit = x["h"] >= target if long_side else x["l"] <= target
        fail = x["c"] < a if long_side else x["c"] > b
        if fail:  # includes the same-bar case: counted as a failure (cautious)
            return {"status": "failure", "pct": pct(x["c"]), "bar": j}
        if hit:
            return {"status": "success", "pct": pct(target), "bar": j}
    return {"status": "expired", "pct": pct(bars[-1]["c"])}


def fetch_day(symbol, day, key, secret):
    from research.lite_buy_timing_v1.run import bars as alpaca_bars
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{symbol}_{day}.json"
    if path.exists():
        return json.loads(path.read_text())
    d = date.fromisoformat(day)
    rows = alpaca_bars(symbol, "5Min", f"{day}T08:00:00Z", f"{(d + timedelta(days=1)).isoformat()}T04:00:00Z",
                       key, secret, adjustment="raw")
    session = []
    for r in rows:
        t = datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(NY)
        if t.date().isoformat() == day and 570 <= t.hour * 60 + t.minute < 960:
            session.append({"m": t.hour * 60 + t.minute, "o": r["o"], "h": r["h"], "l": r["l"], "c": r["c"]})
    daily = alpaca_bars(symbol, "1Day", f"{(d - timedelta(days=10)).isoformat()}T00:00:00Z", f"{day}T00:00:00Z",
                        key, secret, adjustment="raw")
    prev = [r["c"] for r in daily if r["t"][:10] < day]
    out = {"bars": session, "prev_close": prev[-1] if prev else None}
    path.write_text(json.dumps(out))
    return out


def rate(results):
    trig = [r for r in results if r["status"] in ("success", "failure", "expired")]
    return (sum(r["status"] == "success" for r in trig) / len(trig) if trig else None), len(trig)


def summarize(rows):
    real = [r["real"] for r in rows]
    plac = [p for r in rows for p in r["placebo"]]
    rr, rn = rate(real)
    pr, pn = rate(plac)
    pct_real = [r["pct"] for r in real if "pct" in r]
    pct_plac = [p["pct"] for p in plac if "pct" in p]
    return {"calls": len(rows), "real_triggered": rn, "real_success_rate_pct": round(100 * rr, 1) if rr is not None else None,
            "placebo_triggered": pn, "placebo_success_rate_pct": round(100 * pr, 1) if pr is not None else None,
            "diff_pts": round(100 * (rr - pr), 1) if rr is not None and pr is not None else None,
            "real_avg_pct": round(sum(pct_real) / len(pct_real), 3) if pct_real else None,
            "placebo_avg_pct": round(sum(pct_plac) / len(pct_plac), 3) if pct_plac else None,
            "real_status": dict(Counter(r["status"] for r in real))}


def bootstrap(rows, n=10_000, seed=12):
    rng = random.Random(seed)
    diffs = []
    for _ in range(n):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        rr, _ = rate([r["real"] for r in sample])
        pr, _ = rate([p for r in sample for p in r["placebo"]])
        if rr is not None and pr is not None:
            diffs.append(rr - pr)
    diffs.sort()
    return round(100 * diffs[int(0.025 * len(diffs))], 1), round(100 * diffs[int(0.975 * len(diffs)) - 1], 1)


def main():
    from research.lite_paper_bot_v1.bot import credentials
    key, secret = credentials()
    files = sorted(glob.glob(str(CALLS / "*_calls.json")))
    calls, dropped, excluded = [], Counter(), Counter()
    streams = []
    for f in files:
        s = json.loads(Path(f).read_text())
        streams.append({"id": s["id"], "date_et": s["date_et"], "calls": len(s["calls"]), "excluded": len(s["excluded"])})
        for e in s["excluded"]:
            excluded[e["reason"].split()[0].lower()] += 1
        for c in s["calls"]:
            c = {**c, "id": s["id"], "date_et": s["date_et"], "symbol": c["symbol"].upper().lstrip("$")}
            if c["type"] not in TYPES or c.get("level_low") is None or c.get("level_high") is None:
                dropped["bad_fields"] += 1
                continue
            calls.append(c)
    rows = []
    for c in calls:
        try:
            day = fetch_day(c["symbol"], c["date_et"], key, secret)
        except Exception:  # e.g. a symbol Alpaca doesn't list ("SPACEX" placeholder): dropped and counted
            dropped[f"no_data:{c['symbol']}"] += 1
            continue
        if not day["bars"]:
            dropped["no_bars"] += 1
            continue
        ref = day["prev_close"] or day["bars"][0]["o"]
        if abs(c["level_low"] / ref - 1) > 0.15 or abs(c["level_high"] / ref - 1) > 0.15:
            dropped["level_over_15pct_from_prev_close"] += 1
            continue
        shifts = INDEX_SHIFTS if c["symbol"] in INDEX_ETFS else STOCK_SHIFTS
        rows.append({"call": c, "real": score(c, day["bars"]),
                     "placebo": [score(c, day["bars"], d) for d in shifts]})
    overall = summarize(rows)
    lo, hi = bootstrap(rows)
    overall["bootstrap_95pct_diff_pts"] = [lo, hi]
    groups = defaultdict(list)
    for r in rows:
        c = r["call"]
        groups[f"type:{c['type']}"].append(r)
        groups["index_etfs" if c["symbol"] in INDEX_ETFS else "single_stocks"].append(r)
        if c.get("top_watch"):
            groups["top_watch"].append(r)
        if c["target"] is not None:
            groups["stated_target"].append(r)
        else:
            groups["no_stated_target"].append(r)
        if c["symbol"] == "MU":
            groups["MU"].append(r)
    verdict = {"1_success_rate_beats_placebo_by_5pts": (overall["diff_pts"] or -99) >= 5.0,
               "2_bootstrap_interval_excludes_zero": lo > 0}
    verdict["edge_shown"] = all(verdict.values())
    out = {"plan": "output/OPTIONS_INSIDER_LEVELS_TEST_PLAN_20261005.md", "streams": streams,
           "calls_extracted": len(calls), "calls_scored": len(rows), "dropped": dict(dropped),
           "excluded_in_extraction": dict(excluded), "overall": overall, "verdict": verdict,
           "groups": {k: summarize(v) for k, v in sorted(groups.items())},
           "call_results": [{**{k: r["call"][k] for k in ("id", "date_et", "ts", "symbol", "type", "level_low",
                                                          "level_high", "target", "top_watch")},
                             "real": r["real"], "placebo_status": [p["status"] for p in r["placebo"]]} for r in rows]}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    from research.provenance_v1.provenance import write_manifest
    write_manifest(OUT, code=["research/oi_levels_test_v1/score.py"], data=files,
                   params={"stock_shifts": STOCK_SHIFTS, "index_shifts": INDEX_SHIFTS})
    print(json.dumps({k: out[k] for k in ("calls_extracted", "calls_scored", "dropped", "excluded_in_extraction",
                                          "overall", "verdict", "groups")}, indent=1))


if __name__ == "__main__":
    main()
