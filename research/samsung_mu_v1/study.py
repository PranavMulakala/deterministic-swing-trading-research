"""MU's move on the US trading day after each Samsung preliminary report (released ~8-9 AM KST = the prior US evening).
Usage: python samsung_mu.py dates.json   (list of {"q":..., "kst":"YYYY-MM-DD", "result":"beat|miss|inline|unknown"})"""
import json, sys, statistics, urllib.parse
from research.forward_watch_v1.watch import get
from research.lite_dip_history_v1.run import DATA

def daily(sym):
    out, token = {}, None
    while True:
        q = {"timeframe": "1Day", "feed": "sip", "adjustment": "split", "limit": 10000, "start": "2018-12-01T00:00:00Z", "end": "2026-10-07T00:00:00Z"}
        if token: q["page_token"] = token
        p = get(f"{DATA}/v2/stocks/{sym}/bars?{urllib.parse.urlencode(q)}")
        for r in p.get("bars") or []: out[r["t"][:10]] = (r["o"], r["c"])
        token = p.get("next_page_token")
        if not token: return out

events = json.load(open(sys.argv[1]))
mu, smh = daily("MU"), daily("SMH")
days = sorted(mu)
rows = []
for e in events:
    d = next((x for x in days if x >= e["kst"]), None)   # US session that opens after the KST morning release
    if d is None: continue
    prev = days[days.index(d) - 1]
    gap = mu[d][0] / mu[prev][1] - 1; day = mu[d][1] / mu[prev][1] - 1
    sday = smh[d][1] / smh[prev][1] - 1 if d in smh and prev in smh else None
    rows.append({**e, "us_day": d, "gap": gap, "day": day, "vs_smh": day - sday if sday is not None else None})
for r in rows:
    print(f"{r['q']:8s} {r['kst']} -> {r['us_day']}  {r['result']:8s} MU open {100*r['gap']:+5.1f}%  close {100*r['day']:+5.1f}%  vs SMH {100*r['vs_smh']:+5.1f}%")
def summ(name, sel):
    if not sel: print(name, "none"); return
    d = [r["day"] for r in sel]; v = [r["vs_smh"] for r in sel]
    print(f"{name}: n={len(sel)} up {sum(x>0 for x in d)}/{len(d)}  avg {100*statistics.mean(d):+.2f}%  median {100*statistics.median(d):+.2f}%  avg |move| {100*statistics.mean(abs(x) for x in d):.2f}%  avg vs SMH {100*statistics.mean(v):+.2f}%")
summ("ALL", rows)
for k in ("beat", "miss", "inline"):
    summ(k, [r for r in rows if r["result"] == k])
allmoves = [abs(mu[days[i]][1] / mu[days[i-1]][1] - 1) for i in range(1, len(days))]
print(f"typical MU day (all days since Dec 2018): avg |move| {100*statistics.mean(allmoves):.2f}%")
