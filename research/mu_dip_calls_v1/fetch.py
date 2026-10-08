"""Data for test #27 (plan: output/MU_DIP_WEEKLY_CALLS_TEST_PLAN_20261008.md). Owner approved the Databento cost
("Yes, approve", Oct 8, 2026; estimated under $1). Hard stop at $5, checked with Databento's free cost endpoint before
every request. The key is never printed. Finished files are skipped on rerun.

1. Alpaca SIP daily bars -> signal days (open <= prior close x 0.98) and 200 random ordinary mornings (seed 27);
   SIP 1-minute bar at 10:00 ET -> MU's 10:00 price.
2. Databento OPRA.PILLAR cbbo-1m, parent MU.OPT, 10:00-10:01 ET -> the call chain (expiring within 25 days).
3. For each contract the backtest would pick (1-week and 2-week rules): that contract's cbbo-1m from 10:01 on the
   entry day to 16:00 on its expiration day.

  PYTHONPATH=src:. .venv/bin/python -m research.mu_dip_calls_v1.fetch
"""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import threading
import http.client
import csv
from datetime import date, datetime, time as dtime, timedelta, timezone
import gzip
import io
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from research.mu_dip_calls_v1.backtest import DATA, LAST, TWO_WEEK, WEEK, osi, parse_osi, pick_contract, load_chain
from research.spy_put_spread_backtest_v1.fetch_databento import api_key

NY = ZoneInfo("America/New_York")
BUDGET = 5.0
DB = "https://hist.databento.com/v0/"


class Databento:
    def __init__(self):
        self.key = api_key()
        self.auth = "Basic " + base64.b64encode((self.key + ":").encode()).decode()
        self.spent = 0.0
        self.lock = threading.Lock()

    def _post(self, path, params):
        body = urllib.parse.urlencode(params).encode()
        for attempt in range(20):
            req = urllib.request.Request(DB + path, data=body, method="POST",
                                         headers={"Authorization": self.auth, "Content-Type": "application/x-www-form-urlencoded"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return r.read().decode()
            except urllib.error.HTTPError as e:
                detail = e.read(400).decode(errors="replace").replace(self.key, "[key]")
                if e.code in (429, 500, 502, 503, 504) and attempt < 19:
                    time.sleep(min(60, 5 * (attempt + 1)))
                    continue
                raise RuntimeError(f"HTTP {e.code}: {detail}") from None
            except (OSError, http.client.HTTPException):
                if attempt == 19:
                    raise
                time.sleep(min(60, 5 * (attempt + 1)))

    def get(self, symbols, stype, start, end):
        p = {"dataset": "OPRA.PILLAR", "symbols": symbols, "stype_in": stype, "schema": "cbbo-1m",
             "start": start.astimezone(timezone.utc).isoformat(), "end": end.astimezone(timezone.utc).isoformat()}
        cost = float(self._post("metadata.get_cost", p))
        with self.lock:
            if self.spent + cost > BUDGET:
                raise SystemExit(f"Budget guard: ${self.spent:.3f} spent, next request ${cost:.4f} would pass ${BUDGET}")
            self.spent += cost  # reserved before the download so parallel workers cannot overshoot
        text = self._post("timeseries.get_range", {**p, "encoding": "csv", "compression": "none", "pretty_px": "true",
                                                   "pretty_ts": "true", "map_symbols": "true"})
        return list(csv.DictReader(io.StringIO(text)))


def alpaca(path):
    """Paced (about 3 requests a second) with retries on Alpaca's 429 rate limit."""
    from research.forward_watch_v1.watch import get
    from research.lite_dip_history_v1.run import DATA as ALPACA
    for attempt in range(10):
        time.sleep(0.35)
        try:
            return get(ALPACA + path)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 9:
                raise
            time.sleep(10 * (attempt + 1))


def daily():
    rows, token = [], None
    while True:
        q = {"timeframe": "1Day", "feed": "sip", "adjustment": "raw", "start": "2019-12-01T00:00:00Z",
             "end": "2026-10-08T00:00:00Z", "limit": 10000}
        if token:
            q["page_token"] = token
        p = alpaca(f"/v2/stocks/MU/bars?{urllib.parse.urlencode(q)}")
        rows += p["bars"]
        token = p.get("next_page_token")
        if not token:
            return rows


def spot_at_10(day):
    start = datetime.combine(date.fromisoformat(day), dtime(10, 0), NY)
    q = {"timeframe": "1Min", "feed": "sip", "adjustment": "raw", "limit": 5,
         "start": start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
         "end": (start + timedelta(minutes=1)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    bars = alpaca(f"/v2/stocks/MU/bars?{urllib.parse.urlencode(q)}").get("bars") or []
    return bars[0]["o"] if bars else None


def build_days():
    path = DATA / "days.json"
    if path.exists():
        return json.loads(path.read_text())
    rows = daily()
    closes = {r["t"][:10]: r["c"] for r in rows}
    days = {}
    ordinary = []
    for i in range(1, len(rows)):
        d = rows[i]["t"][:10]
        if not "2020-01-02" <= d <= LAST:
            continue
        gap = 100 * (rows[i]["o"] / rows[i - 1]["c"] - 1)
        if gap <= -2.0:
            days[d] = {"gap_pct": round(gap, 3), "signal": True, "baseline": False}
        elif d <= "2026-09-30":
            ordinary.append((d, round(gap, 3)))
    for d, gap in random.Random(27).sample(ordinary, 200):
        days[d] = {"gap_pct": gap, "signal": False, "baseline": True}
    for d in sorted(days):
        days[d]["spot10"] = spot_at_10(d)
    out = {"days": days, "closes": closes}
    DATA.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1) + "\n")
    return out


def fetch_chain(db, day, spot):
    out = DATA / "chain" / f"{day}.csv.gz"
    if out.exists():
        return
    start = datetime.combine(date.fromisoformat(day), dtime(10, 0), NY)
    rows = db.get("MU.OPT", "parent", start, start + timedelta(minutes=1))
    d = date.fromisoformat(day)
    keep = []
    for r in rows:
        info = parse_osi(r.get("symbol", ""))
        if not info or info[1] != "C" or not 0 < (info[0] - d).days <= 25:
            continue
        if spot and not 0.85 * spot <= info[2] <= 1.15 * spot:
            continue
        try:
            bid, ask = float(r.get("bid_px_00") or 0), float(r.get("ask_px_00") or 0)
        except ValueError:
            continue
        keep.append([info[0].isoformat(), f"{info[2]:g}", f"{bid:.2f}", f"{ask:.2f}", r.get("ts_recv", "")])
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    with gzip.open(tmp, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["expiration", "strike", "bid", "ask", "ts_recv"])
        w.writerows(keep)
    tmp.replace(out)  # atomic: a stopped run never leaves a half-written file behind


def fetch_hold(db, day, exp, strike):
    sym = osi(exp, strike)
    out = DATA / "hold" / f"{day}_{sym.replace(' ', '')}.csv.gz"
    if out.exists():
        return
    start = datetime.combine(date.fromisoformat(day), dtime(10, 1), NY)
    end = datetime.combine(exp, dtime(16, 0), NY)
    rows = db.get(sym, "raw_symbol", start, end)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    with gzip.open(tmp, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "bid", "ask"])
        for r in rows:
            try:
                w.writerow([r["ts_recv"], f"{float(r.get('bid_px_00') or 0):.2f}", f"{float(r.get('ask_px_00') or 0):.2f}"])
            except ValueError:
                continue
    tmp.replace(out)


def main():
    meta = build_days()
    days = meta["days"]
    print(json.dumps({"signal_days": sum(m["signal"] for m in days.values()), "ordinary_days": sum(m["baseline"] for m in days.values()),
                      "missing_10am_price": sum(m["spot10"] is None for m in days.values())}), flush=True)
    db = Databento()

    def work(day):
        m = days[day]
        fetch_chain(db, day, m["spot10"])
        chain = load_chain(day)
        for dte in ((WEEK, TWO_WEEK) if m["signal"] else (WEEK,)):
            pick = pick_contract(chain, date.fromisoformat(day), m["spot10"], dte)
            if pick and pick[0].isoformat() <= LAST:
                fetch_hold(db, day, pick[0], pick[1])
        return day

    with ThreadPoolExecutor(max_workers=8) as pool:
        for n, _ in enumerate(pool.map(work, sorted(days)), 1):
            if n % 25 == 0:
                print(json.dumps({"days_done": n, "of": len(days), "databento_dollars_this_run": round(db.spent, 4)}), flush=True)
    print(json.dumps({"done": True, "databento_dollars_this_run": round(db.spent, 4)}))


if __name__ == "__main__":
    main()
