"""Score EdwardAlerts' Discord option alerts as a follower would have traded them. Paper scoring only; never trades.

The alert log is `outputs/edward_alerts/alerts.json` (gitignored): one entry per #trade-ideas alert, with its later
"UP x% AT y" updates. Prices come from Alpaca OPRA one-minute bars.

Follower conventions ($1,000 per alert; the same as the Oct 11 review and test #28):
  - entry: the HIGH of the first minute after the alert is posted;
  - an exit at one of his updates: the LOW of the first minute after the update is posted.
Exit rules scored side by side:
  - last_update: sell everything after his last update (no update = held);
  - split_updates: sell an equal piece after each update (no update = held);
  - hold: no exit (marked at the last bar; after expiration, at intrinsic value from the stock's close);
  - tp30 / tp50 / tp100: your own limit order at +30% / +50% / +100% over your entry, otherwise held.

  PYTHONPATH=src:. .venv/bin/python -m research.edward_alerts_v1.score          # markdown table
  PYTHONPATH=src:. .venv/bin/python -m research.edward_alerts_v1.score --json
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "outputs/edward_alerts/alerts.json"
STAKE = 1000.0
RULES = ("last_update", "split_updates", "hold", "tp30", "tp50", "tp100")


def occ(a):
    e = date.fromisoformat(a["expiry"])
    return f"{a['underlying']}{e:%y%m%d}{a['cp']}{int(round(a['strike'] * 1000)):08d}"


def _get(url):
    from research.forward_watch_v1.watch import get
    return get(url)


def option_bars(symbol, start, end):
    out, token = [], None
    while True:
        q = {"symbols": symbol, "timeframe": "1Min", "start": start, "end": end, "limit": 10000}
        if token:
            q["page_token"] = token
        r = _get("https://data.alpaca.markets/v1beta1/options/bars?" + urllib.parse.urlencode(q))
        out += r.get("bars", {}).get(symbol, [])
        token = r.get("next_page_token")
        if not token:
            return out


def stock_close(symbol, day):
    q = {"timeframe": "1Day", "start": day, "end": day, "feed": "sip", "adjustment": "raw"}
    bars = _get(f"https://data.alpaca.markets/v2/stocks/{symbol}/bars?" + urllib.parse.urlencode(q)).get("bars") or []
    return bars[0]["c"] if bars else None


def first_after(bars, ts):
    minute = ts[:16]
    return next((b for b in bars if b["t"][:16] > minute), None)


def score_alert(a, now=None, bars=None, expiry_close=None):
    """Pure given `bars` (and `expiry_close` once expired); fetches them otherwise."""
    now = now or datetime.now(timezone.utc)
    expired = now.date() > date.fromisoformat(a["expiry"])
    if bars is None:
        # The free OPRA feed refuses requests that end within the last ~15 minutes.
        end = f"{a['expiry']}T21:00:00Z" if expired else (now - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
        bars = option_bars(occ(a), a["ts"][:17] + "00Z", end)
    e = first_after(bars, a["ts"])
    if e is None:
        return {"id": a["id"], "contract": occ(a), "status": "no trades yet"}
    entry = e["h"]
    after = [b for b in bars if b["t"] >= e["t"]]
    if expired:
        if expiry_close is None:
            expiry_close = stock_close(a["underlying"], a["expiry"])
        k = a["strike"]
        mark = max(0.0, (expiry_close - k) if a["cp"] == "C" else (k - expiry_close)) if expiry_close is not None else after[-1]["c"]
    else:
        mark = after[-1]["c"]
    exits = {"hold": mark}
    ups = [first_after(bars, u["ts"]) for u in a.get("updates", [])]
    ups = [u["l"] for u in ups if u]
    exits["last_update"] = ups[-1] if ups else mark
    exits["split_updates"] = sum(ups) / len(ups) if ups else mark
    for name, tp in (("tp30", 1.3), ("tp50", 1.5), ("tp100", 2.0)):
        hit = any(b["h"] >= entry * tp for b in after[1:])
        exits[name] = entry * tp if hit else mark
    pnl = {r: round(STAKE * (exits[r] / entry - 1), 2) for r in RULES}
    return {"id": a["id"], "contract": occ(a), "posted": a["price"], "entry": entry, "mark": round(mark, 2),
            "status": "expired" if expired else "open", "his_last_update": a["updates"][-1]["note"] if a.get("updates") else "none",
            "peak": max(b["h"] for b in after), "pnl": pnl}


def summarize(rows):
    done = [r for r in rows if "pnl" in r]
    tot = {k: round(sum(r["pnl"][k] for r in done), 2) for k in RULES}
    return {"alerts": len(done), "with_updates": sum(r["his_last_update"] != "none" for r in done),
            "never_updated": sum(r["his_last_update"] == "none" for r in done), "total_by_rule": tot,
            "per_alert_by_rule": {k: round(v / len(done), 2) for k, v in tot.items()} if done else {}}


def table(rows, summary):
    lines = ["| Alert | Posted | Your entry | Peak | Now/expiry | His last update | Sell at his last update | Hold | Your +50% limit |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "pnl" not in r:
            lines.append(f"| {r['id']} | | | | | {r['status']} | | | |")
            continue
        p = r["pnl"]
        lines.append(f"| {r['id']} ({r['status']}) | {r['posted']} | {r['entry']} | {r['peak']} | {r['mark']} | {r['his_last_update']} | "
                     f"{p['last_update']:+,.0f} | {p['hold']:+,.0f} | {p['tp50']:+,.0f} |")
    t = summary["total_by_rule"]
    lines.append(f"| **Total ({summary['alerts']} alerts, {summary['never_updated']} never updated)** | | | | | | "
                 f"**{t['last_update']:+,.0f}** | **{t['hold']:+,.0f}** | **{t['tp50']:+,.0f}** |")
    lines.append("")
    lines.append("All rules, total $ on $1,000 per alert: " + ", ".join(f"{k} {v:+,.0f}" for k, v in t.items()))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    alerts = json.loads(LOG.read_text())
    rows = [score_alert(x) for x in alerts]
    s = summarize(rows)
    print(json.dumps({"rows": rows, "summary": s}, indent=1) if a.json else table(rows, s))


if __name__ == "__main__":
    main()
