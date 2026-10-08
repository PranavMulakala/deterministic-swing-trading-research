"""Test #28 (plan: output/OWLS_ALERTS_BACKTEST_PLAN_20261008.md): score one month of OWLS Capital Discord alerts as a
follower. Inputs: event CSVs extracted from the owner's all-alerts feed (outputs/owls_alerts/events_chunk*.csv, private,
gitignored). Prices: Alpaca option 1-minute bars (free; SPX index options via SPXW). Read-only research; no orders.

Follower rule: buy at the HIGH of the 1-minute bar in the minute after the alert; each later trim/exit message sells an
equal share at the LOW of the bar in the minute after it; anything not exited is valued at the last price on the
expiration day (or on Oct 8, 2026 if not yet expired). $1,000 per alert.

  PYTHONPATH=src:. .venv/bin/python -m research.owls_alerts_v1.score
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
import glob
import gzip
import json
from pathlib import Path
import statistics
import time
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/owls_alerts"
CACHE = DATA / "bars"
OUT_PRIVATE = DATA / "scored_trades.json"
OUT = ROOT / "output/owls-alerts-test-results.json"
START, END, LAST_DAY = "2026-09-08", "2026-10-08T23:59:59", date(2026, 10, 8)
STAKE = 1000.0
SKIP_ANALYSTS = ("bobby-spx-coms", "giul-heatseeker")


def get_bars(occ, start, end):
    """1-minute bars [(minute_iso, o, h, l, c)] cached per contract."""
    from research.forward_watch_v1.watch import get
    from research.lite_dip_history_v1.run import DATA as ALPACA
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{occ}.json.gz"
    if path.exists():
        with gzip.open(path, "rt") as f:
            return [tuple(x) for x in json.load(f)]
    rows, token = [], None
    while True:
        q = {"symbols": occ, "timeframe": "1Min", "start": start, "end": end, "limit": 10000}
        if token:
            q["page_token"] = token
        for attempt in range(8):
            try:
                time.sleep(0.3)
                page = get(f"{ALPACA}/v1beta1/options/bars?{urllib.parse.urlencode(q)}")
                break
            except Exception:
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError("bars failed " + occ)
        rows += [(b["t"][:16], b["o"], b["h"], b["l"], b["c"]) for b in (page.get("bars") or {}).get(occ, [])]
        token = page.get("next_page_token")
        if not token:
            break
    with gzip.open(path, "wt") as f:
        json.dump(rows, f)
    return rows


def occ_symbol(und, exp, cp, strike):
    root = "SPXW" if und == "SPX" else und
    return f"{root}{exp:%y%m%d}{cp}{round(float(strike) * 1000):08d}"


def fridays_after(d, n=6):
    out, x = [], d
    while len(out) < n:
        if x.weekday() == 4:
            out.append(x)
        x += timedelta(days=1)
    return out


def next_weekday(d):
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def load_events():
    rows = []
    for p in sorted(glob.glob(str(DATA / "events_chunk*.csv"))):
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                r = {k: (v or "").strip() for k, v in r.items()}
                if r.get("ts", "") >= START and r.get("ts", "") <= END:
                    rows.append(r)
    return sorted(rows, key=lambda r: r["ts"])


def build_positions(events):
    """Match trims/exits to entries per analyst. Returns (positions, unmatched)."""
    positions, unmatched = [], []
    for e in events:
        a, kind = e["analyst"], e["kind"]
        if a.split(":")[0] in SKIP_ANALYSTS or e.get("cp") == "S":
            continue
        if kind == "E":
            positions.append({"analyst": a, "und": e["underlying"].upper().lstrip("$"), "strike": e["strike"],
                              "cp": e["cp"], "expiry": e["expiry"], "ts": e["ts"], "posted_entry": e["price"],
                              "pre_existing": "pre-existing" in e.get("note", "").lower(), "exits": [], "adds": 0,
                              "closed": False, "note": e.get("note", "")})
            continue
        und = e["underlying"].upper().lstrip("$")
        cands = [p for p in positions if p["analyst"] == a and not p["closed"]
                 and (und in ("", "?") or p["und"] == und)
                 and (not e["strike"] or not p["strike"] or abs(float(p["strike"]) - float(e["strike"])) < 1e-6)
                 and (not e["cp"] or not p["cp"] or p["cp"] == e["cp"])]
        if not cands:
            unmatched.append(e)
            continue
        p = cands[-1]
        if kind == "A":
            p["adds"] += 1
            continue
        p["exits"].append({"ts": e["ts"], "price": e["price"], "pct": e["pct"], "kind": kind, "note": e.get("note", "")})
        if kind == "X":
            p["closed"] = True
    return positions, unmatched


def bar_at_or_after(bars, minute_iso, max_minutes):
    for b in bars:
        if b[0] >= minute_iso:
            t0 = datetime.fromisoformat(minute_iso)
            if (datetime.fromisoformat(b[0]) - t0) <= timedelta(minutes=max_minutes):
                return b
            return None
    return None


def minute_after(ts):
    t = datetime.fromisoformat(ts).replace(second=0, microsecond=0) + timedelta(minutes=1)
    return t.strftime("%Y-%m-%dT%H:%M")


def resolve_expiry(p):
    d = date.fromisoformat(p["ts"][:10])
    x = p["expiry"].upper()
    if x and x[0].isdigit() and len(x) == 10:
        return [date.fromisoformat(x)], "stated"
    if x == "0DTE" or (not x and p["und"] == "SPX"):
        return [d], "0dte"
    if x == "1DTE":
        return [next_weekday(d)], "1dte"
    if x == "2DTE":
        return [next_weekday(next_weekday(d))], "2dte"
    return fridays_after(d, 5), "inferred"


def score_position(p):
    if p["pre_existing"] or not p["strike"] or p["cp"] not in ("C", "P"):
        return None, "not_scorable"
    exps, how = resolve_expiry(p)
    t0 = minute_after(p["ts"])
    best = None
    for exp in exps:
        if exp < date.fromisoformat(p["ts"][:10]):
            continue
        occ = occ_symbol(p["und"], exp, p["cp"], p["strike"])
        end_day = min(exp, LAST_DAY)
        bars = get_bars(occ, p["ts"][:10] + "T13:00:00Z", end_day.isoformat() + "T21:00:00Z")
        entry = bar_at_or_after(bars, t0, 5)
        if not entry:
            continue
        posted = float(p["posted_entry"]) if p["posted_entry"] else None
        gap = abs(entry[4] / posted - 1) if posted else 0.0
        if best is None or gap < best[3]:
            best = (exp, occ, bars, gap, entry)
        if how != "inferred":
            break
    if best is None:
        return None, "no_price_at_entry"
    exp, occ, bars, gap, entry = best
    fill_in = entry[2]  # high of the minute after the alert
    exits = p["exits"]
    n_x = sum(1 for x in exits if x["kind"] == "X")
    n = len(exits) if n_x else len(exits) + 1
    proceeds, legs = 0.0, []
    for x in exits:
        b = bar_at_or_after(bars, minute_after(x["ts"]), 30)
        if b is None:
            later = [b for b in bars if b[0] >= minute_after(x["ts"])]
            b = later[0] if later else bars[-1]
        legs.append({"ts": x["ts"], "fill": b[3], "kind": x["kind"]})
        proceeds += b[3] / n
    remainder = None
    if not n_x:
        last = [b for b in bars if b[0][:10] <= min(exp, LAST_DAY).isoformat()]
        remainder = last[-1][4] if last else 0.0
        proceeds += remainder / n
    follower_pct = 100 * (proceeds / fill_in - 1) if fill_in > 0 else None
    posted_entry = float(p["posted_entry"]) if p["posted_entry"] else None
    posted = []
    for x in exits:
        if x["pct"]:
            try:
                posted.append(float(x["pct"]))
                continue
            except ValueError:
                pass
        if x["price"] and posted_entry:
            posted.append(100 * (float(x["price"]) / posted_entry - 1))
    return {"analyst": p["analyst"].split(":")[0], "who": p["analyst"], "ts": p["ts"], "contract": occ, "expiry_how": how,
            "posted_entry": posted_entry, "price_at_alert": entry[4], "posted_vs_real_gap_pct": round(100 * gap, 1),
            "follower_entry": fill_in, "exits": legs, "held_remainder_value": remainder, "n_exit_msgs": len(exits),
            "closed_by_analyst": bool(n_x), "follower_pct": round(follower_pct, 1) if follower_pct is not None else None,
            "follower_pnl": round(STAKE * follower_pct / 100, 2) if follower_pct is not None else None,
            "posted_pct": round(statistics.mean(posted), 1) if posted else None, "note": p["note"]}, "ok"


def summarize(trades):
    out = {}
    for a in sorted({t["analyst"] for t in trades}):
        ts = [t for t in trades if t["analyst"] == a and t["follower_pnl"] is not None]
        main = [t for t in ts if t["posted_vs_real_gap_pct"] <= 50]
        if not main:
            continue
        pnl = [t["follower_pnl"] for t in main]
        posted = [t["posted_pct"] for t in main if t["posted_pct"] is not None]
        out[a] = {"alerts_scored": len(main), "follower_total_$": round(sum(pnl), 2),
                  "follower_$_per_alert": round(statistics.mean(pnl), 2), "follower_median_$": round(statistics.median(pnl), 2),
                  "follower_win_pct": round(100 * sum(p > 0 for p in pnl) / len(pnl), 1),
                  "best_$": max(pnl), "worst_$": min(pnl),
                  "posted_avg_pct": round(statistics.mean(posted), 1) if posted else None,
                  "follower_avg_pct_same_trades": round(statistics.mean(t["follower_pct"] for t in main if t["posted_pct"] is not None), 1) if posted else None,
                  "share_with_exit_posted_pct": round(100 * sum(t["closed_by_analyst"] for t in main) / len(main), 1),
                  "entry_price_mismatch_dropped": len(ts) - len(main),
                  "inferred_expiry": sum(t["expiry_how"] == "inferred" for t in main)}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["follower_$_per_alert"]))


def main():
    events = load_events()
    positions, unmatched = build_positions(events)
    trades, reasons = [], {}
    for p in positions:
        t, why = score_position(p)
        reasons[why] = reasons.get(why, 0) + 1
        if t:
            trades.append(t)
    summary = summarize(trades)
    DATA.mkdir(parents=True, exist_ok=True)
    OUT_PRIVATE.write_text(json.dumps({"trades": trades, "unmatched_exits": unmatched}, indent=1) + "\n")
    OUT.write_text(json.dumps({"plan": "output/OWLS_ALERTS_BACKTEST_PLAN_20261008.md", "window": [START, END[:10]],
                               "events": len(events), "positions": len(positions), "position_outcomes": reasons,
                               "unmatched_exit_messages": len(unmatched), "by_analyst": summary}, indent=1) + "\n")
    print(json.dumps({"events": len(events), "positions": len(positions), "outcomes": reasons,
                      "unmatched_exits": len(unmatched), "by_analyst": summary}, indent=1))


if __name__ == "__main__":
    main()
