"""Forward paper watch for test #16, Qullamaggie's episodic pivot (output/EP_FORWARD_WATCH_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.ep_watch_v1.watch --morning [--print]   # 10:50 ET watch list
  PYTHONPATH=src:. .venv/bin/python -m research.ep_watch_v1.watch --evening [--print]   # 17:05 ET paper ledger

Paper only: no orders, no broker account. Read-only Alpaca SIP data (15-minute delayed on the free plan) and SEC EDGAR
filing times. The rule is imported unchanged from research/ep_test_v1/backtest.py; every evening the whole forward
ledger is rebuilt from freshly fetched data, so prices stay on one consistent (split- and dividend-adjusted) scale.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
import statistics
import time
import urllib.parse
from zoneinfo import ZoneInfo

from research.ep_test_v1 import backtest as bt
from research.ep_test_v1.candidates import GAP, LOOKBACK, MIN_ADV_USD, PREFILTER_VOL
from research.ep_test_v1.fetch_intraday import regular

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "outputs/ep_watch"
NY = ZoneInfo("America/New_York")
START_DAY, LAST_EVENT_DAY, STOP_DAY = "2026-10-06", "2027-01-08", "2027-02-12"
HISTORY_DAYS, CATCH_UP_DAYS = 200, 30


def universe():
    return json.loads((HERE / "universe.json").read_text())


def shift(day, days):
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def utc(day, hour, minute):
    t = datetime.fromisoformat(f"{day}T{hour:02d}:{minute:02d}:00").replace(tzinfo=NY)
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- data sources (real ones; tests pass fakes with the same methods) ----------

class Alpaca:
    def __init__(self, pause=0.35):
        from research.lite_paper_bot_v1.bot import credentials
        self.key, self.secret = credentials()
        self.pause = pause

    def get(self, url):
        from research.lite_dip_history_v1.run import fetch
        for attempt in range(6):
            try:
                out = fetch(url, self.key, self.secret)
                time.sleep(self.pause)
                return out
            except Exception:
                time.sleep(3 * (attempt + 1))
        raise RuntimeError("Alpaca request failed 6 times")

    def trading_days(self, start, end):
        from research.lite_dip_history_v1.run import PAPER
        return [d["date"] for d in self.get(f"{PAPER}/v2/calendar?start={start}&end={end}")]

    def bars(self, symbols, timeframe, start, end):
        """Multi-symbol SIP bars (adjustment=all), every page: {symbol: [bar, ...]}. `end` is capped 16 minutes back."""
        from research.lite_dip_history_v1.run import DATA
        cap = (datetime.now(timezone.utc) - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = min(end, cap)
        out = {}
        for i in range(0, len(symbols), 100):
            q = {"symbols": ",".join(symbols[i:i + 100]), "timeframe": timeframe, "feed": "sip", "adjustment": "all",
                 "sort": "asc", "limit": 10000, "start": start, "end": end}
            token = None
            while True:
                if token:
                    q["page_token"] = token
                page = self.get(f"{DATA}/v2/stocks/bars?{urllib.parse.urlencode(q)}")
                for s, rows in (page.get("bars") or {}).items():
                    out.setdefault(s, []).extend(rows)
                token = page.get("next_page_token")
                if not token:
                    break
        return out


class Sec:
    def __init__(self):
        self._map = None

    def rows(self, symbol):
        """Item 2.02 8-K rows [[acceptanceDateTime, filingDate, items], ...], or None if the ticker has no SEC CIK."""
        from research.ep_test_v1.fetch_edgar import SUBMISSIONS, TICKERS_URL, earnings_rows, get_json, norm
        if self._map is None:
            self._map = {norm(r["ticker"]): int(r["cik_str"]) for r in get_json(TICKERS_URL).values()}
        cik = self._map.get(norm(symbol))
        if cik is None:
            return None
        sub = get_json(f"{SUBMISSIONS}CIK{cik:010d}.json")
        return earnings_rows(sub["filings"]["recent"]) if sub else []


# ---------- pure pieces (unit-tested) ----------

def daily_series(rows):
    rows = sorted(rows, key=lambda r: r["t"])
    return {"date": [r["t"][:10] for r in rows], "open": [r["o"] for r in rows], "high": [r["h"] for r in rows],
            "low": [r["l"] for r in rows], "close": [r["c"] for r in rows], "volume": [float(r["v"]) for r in rows]}


def gap_candidates(series, days):
    """Test #16's candidate superset (research/ep_test_v1/candidates.py) for the given days: {day: [symbols]}."""
    out = {}
    for s, b in series.items():
        idx = {d: n for n, d in enumerate(b["date"])}
        for d in days:
            i = idx.get(d)
            if i is None or i < LOOKBACK + 1 or b["close"][i - 1] <= 0:
                continue
            adv, adv_usd, _ = bt.prior_stats(b, i)
            if adv_usd >= MIN_ADV_USD and b["open"][i] >= GAP * b["close"][i - 1] and b["volume"][i] >= PREFILTER_VOL * adv:
                out.setdefault(d, []).append(s)
    return {d: sorted(v) for d, v in sorted(out.items())}


def morning_row(symbol, b, today_open, bars, accepted, prev_day, today):
    """One line of the 10:50 list. b = daily series up to yesterday; bars = today's 5-minute bars to 10:30."""
    i = len(b["date"])
    adv, adv_usd, adr = bt.prior_stats(b, i)
    row = {"symbol": symbol, "gap_pct": round(100 * (today_open / b["close"][-1] - 1), 1),
           "earnings": bt.earnings_ok(accepted, prev_day, today)}
    early = [x for x in bars if x[0] < bt.OR_END]
    if not early:
        return {**row, "status": "no 5-minute data yet"}
    vol_ratio = sum(x[5] for x in bars if x[0] < 600) / adv if adv else 0.0
    orh, low = max(x[2] for x in early), min(x[3] for x in early)
    width = (orh * (1 + bt.COST) - low) / (orh * (1 + bt.COST))
    row.update({"vol_ratio": round(vol_ratio, 2), "orh": round(orh, 2), "low": round(low, 2),
                "width_pct": round(100 * width, 1), "adr_pct": round(100 * adr, 1)})
    if not row["earnings"]:
        row["status"] = "no earnings 8-K in the window (info list only)"
    elif vol_ratio < bt.VOL_MULT:
        row["status"] = f"fails volume ({vol_ratio:.2f}x a normal day; needs 1.0x)"
    elif width > adr:
        row["status"] = f"fails range so far (stop {100 * width:.1f}% away vs its normal {100 * adr:.1f}% day)"
    else:
        row["status"] = f"PASSES so far: paper buy if it trades above ${orh:.2f} after 10:30; stop = day's low (now ${low:.2f})"
    return row


def price_at_1030(bars):
    early = [x for x in (bars or []) if x[0] < bt.OR_END]
    return early[-1][4] if early else None


def event_log(cands, daily, intraday, accepted, spy, spy_intraday):
    """Every liquid 10%+ gap-up: 10:30 price -> close 5 and 20 trading days later, minus SPY over the same span."""
    spy_close = dict(zip(spy["date"], spy["close"]))
    rows = []
    for day, syms in cands.items():
        spy_ref = price_at_1030(spy_intraday.get(day))
        for s in syms:
            b = daily.get(s)
            if not b or day not in b["date"]:
                continue
            i = b["date"].index(day)
            if i < LOOKBACK + 1:
                continue
            adv, adv_usd, _ = bt.prior_stats(b, i)
            ref = price_at_1030(intraday.get((s, day)))
            if adv_usd < MIN_ADV_USD or b["open"][i] < GAP * b["close"][i - 1] or not ref or not spy_ref:
                continue
            row = {"symbol": s, "day": day, "earnings": bt.earnings_ok(accepted.get(s, []), b["date"][i - 1], day),
                   "gap_pct": round(100 * (b["open"][i] / b["close"][i - 1] - 1), 1)}
            for h in (5, 20):
                j = i + h
                if j < len(b["date"]) and b["date"][j] in spy_close:
                    row[f"d{h}"] = round(100 * (b["close"][j] / ref - 1) - 100 * (spy_close[b["date"][j]] / spy_ref - 1), 2)
            rows.append(row)
    return rows


def summarize(values):
    if not values:
        return {"n": 0}
    out = {"n": len(values), "mean": round(statistics.mean(values), 2), "median": round(statistics.median(values), 2),
           "pct_positive": round(100 * sum(v > 0 for v in values) / len(values))}
    if len(values) >= 2 and statistics.stdev(values) > 0:
        out["t"] = round(statistics.mean(values) / (statistics.stdev(values) / math.sqrt(len(values))), 2)
    return out


def phase(today):
    if today < START_DAY:
        return "before"
    if today <= LAST_EVENT_DAY:
        return "events"
    if today <= STOP_DAY:
        return "tracking"
    return "finished"


# ---------- jobs ----------

def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, default=str) + "\n")
    tmp.replace(path)


def sec_rows(sec, symbols, refresh):
    """Cached Item 2.02 rows per symbol (outputs/ep_watch/edgar); `refresh` symbols are re-read from SEC."""
    out = {}
    for s in symbols:
        path = OUT / "edgar" / f"{s}.json"
        cached = load_json(path, None)
        if cached is None or s in refresh:
            rows = sec.rows(s)
            old = (cached or {}).get("rows") or []
            merged = None if rows is None and not old else sorted({tuple(r) for r in (rows or []) + old})
            cached = {"rows": [list(r) for r in merged] if merged is not None else None}
            save_json(path, cached)
        if cached["rows"] is not None:
            out[s] = bt.acceptance_times(cached["rows"])
    return out


def morning(api, sec, today):
    days = api.trading_days(shift(today, -45), today)
    if today not in days or phase(today) != "events":
        return None
    prev = [d for d in days if d < today]
    uni = universe()
    hist = {s: daily_series(r) for s, r in api.bars(uni, "1Day", utc(prev[0], 0, 0), utc(prev[-1], 23, 0)).items()}
    first = api.bars(uni, "5Min", utc(today, 9, 30), utc(today, 9, 35))
    gaps = []
    for s, b in hist.items():
        opens = [x[1] for x in regular(first.get(s, [])) if x[0] == 570]
        if not opens or len(b["date"]) < LOOKBACK + 1 or b["date"][-1] != prev[-1]:
            continue
        _, adv_usd, _ = bt.prior_stats(b, len(b["date"]))
        if adv_usd >= MIN_ADV_USD and opens[0] >= GAP * b["close"][-1]:
            gaps.append((s, opens[0]))
    syms = [s for s, _ in gaps]
    bars = {s: regular(r) for s, r in api.bars(syms, "5Min", utc(today, 9, 30), utc(today, 10, 30)).items()} if syms else {}
    accepted = sec_rows(sec, syms, refresh=set(syms))
    rows = [morning_row(s, hist[s], o, bars.get(s, []), accepted.get(s, []), prev[-1], today) for s, o in gaps]
    rows.sort(key=lambda r: (not r["earnings"], -r["gap_pct"]))
    save_json(OUT / "morning" / f"{today}.json", rows)
    return rows


def morning_text(today, rows):
    earn = [r for r in rows if r["earnings"]]
    other = [r for r in rows if not r["earnings"]]
    lines = [f"EP watch {today}: paper only, nothing is bought. Test #16 rules, frozen Oct 5. Data delayed 15 minutes.", ""]
    if not rows:
        lines.append("No 10%+ gap-ups on liquid stocks this morning.")
    lines.append(f"Earnings gap-ups of 10%+ ({len(earn)}):")
    for r in earn:
        detail = (f"  vol {r['vol_ratio']}x, 1st-hour high ${r['orh']}, low ${r['low']}" if "orh" in r else "")
        lines.append(f"- {r['symbol']} gap +{r['gap_pct']}%{detail}\n    {r['status']}")
    if other:
        lines += ["", f"Other 10%+ gap-ups, no earnings 8-K ({len(other)}; info only): " +
                  ", ".join(f"{r['symbol']} +{r['gap_pct']}%" for r in other[:15]) + (" ..." if len(other) > 15 else "")]
    lines += ["", "The paper ledger (what the rule actually did) arrives at 5:05 PM."]
    return "\n".join(lines)


def evening(api, sec, today):
    p = phase(today)
    days = api.trading_days(shift(START_DAY, -HISTORY_DAYS), today)
    if today not in days or p in ("before", "finished"):
        return None
    forward = [d for d in days if START_DAY <= d <= today]
    cands = load_json(OUT / "candidates.json", {})
    recent = [d for d in forward if d >= shift(today, -CATCH_UP_DAYS) and d <= LAST_EVENT_DAY]
    if recent:
        uni = universe()
        hist = {s: daily_series(r) for s, r in api.bars(uni, "1Day", utc(shift(recent[0], -45), 0, 0),
                                                         utc(today, 23, 0)).items()}
        for d, syms in gap_candidates(hist, recent).items():
            cands[d] = sorted(set(cands.get(d, [])) | set(syms))
        save_json(OUT / "candidates.json", cands)
    syms = sorted({s for v in cands.values() for s in v})
    accepted = sec_rows(sec, syms, refresh=set(cands.get(today, [])))
    daily = {s: daily_series(r) for s, r in api.bars(syms + ["SPY"], "1Day", utc(shift(START_DAY, -HISTORY_DAYS), 0, 0),
                                                       utc(today, 23, 0)).items()}
    spy = daily.pop("SPY")
    intraday, spy_intraday = {}, {}
    for d, ss in cands.items():
        got = api.bars(ss + ["SPY"], "5Min", utc(d, 9, 30), utc(d, 16, 0))
        for s, r in got.items():
            if s == "SPY":
                spy_intraday[d] = regular(r)
            else:
                intraday[(s, d)] = regular(r)
    usable = {d: [s for s in ss if s in daily] for d, ss in cands.items()}
    for b in daily.values():
        b["_idx"] = {d: n for n, d in enumerate(b["date"])}
    base = spy["close"][spy["date"].index(forward[0]) - 1]
    spy_curve = [(d, bt.START_CASH * spy["close"][spy["date"].index(d)] / base) for d in forward if d in spy["date"]]
    ledgers = {}
    for name, kw in (("main", {}), ("all_catalysts", {"earnings": False})):
        events, reasons, _ = bt.build_events(usable, daily, intraday, accepted, **kw)
        trades, curve, skipped = bt.portfolio(events, daily, forward)
        ledgers[name] = {"events": events, "trades": trades, "curve": curve, "skipped": dict(skipped),
                         "reasons": dict(Counter(reasons.values()))}
    log = event_log(usable, daily, intraday, accepted, spy, spy_intraday)
    snapshot = {"day": today, "phase": p, "spy_curve": spy_curve, "ledgers": ledgers, "event_log": log,
                "candidate_days": sum(len(v) for v in cands.values())}
    save_json(OUT / "ledger" / f"{today}.json", snapshot)
    return snapshot


def evening_text(snap):
    today, spy_value = snap["day"], snap["spy_curve"][-1][1]
    lines = [f"EP paper ledger {today}: paper only, nothing is bought. Test #16 rules, frozen Oct 5; rebuilt from fresh data.",
             f"$100,000 in SPY from the Oct 5 close is now ${spy_value:,.0f}.", ""]
    for name, label in (("main", "Main rule (earnings EP)"), ("all_catalysts", "All catalysts (info only)")):
        led = snap["ledgers"][name]
        value = led["curve"][-1][1] if led["curve"] else bt.START_CASH
        closed = [t for t in led["trades"] if not t["open"]]
        open_ = [t for t in led["trades"] if t["open"]]
        lines.append(f"{label}: ${value:,.0f} ({100 * (value / bt.START_CASH - 1):+.2f}%), {len(closed)} closed, "
                     f"{len(open_)} open, {sum(t['pnl'] for t in closed):+,.0f} realized.")
        for t in led["trades"]:
            if t["entry_date"] == today:
                lines.append(f"  NEW paper buy: {t['symbol']} at ${t['fill']:.2f}, stop ${t['stop']:.2f}, ${t['cost_basis']:,.0f}")
            if t.get("exit_date") == today:
                lines.append(f"  CLOSED: {t['symbol']} {t['exit_kind']} {t['pnl']:+,.0f} ({(t['r'] or 0):+.2f}R)")
        for t in open_:
            lines.append(f"  open: {t['symbol']} since {t['entry_date']}, {t['pnl']:+,.0f} marked")
    log = snap["event_log"]
    lines += ["", f"Event log since Oct 6: {len(log)} liquid 10%+ gap-ups "
                  f"({sum(r['earnings'] for r in log)} with earnings). Return after the 10:30 price, minus SPY:"]
    for label, group in (("earnings", [r for r in log if r["earnings"]]), ("other", [r for r in log if not r["earnings"]])):
        for h in (5, 20):
            s = summarize([r[f"d{h}"] for r in group if f"d{h}" in r])
            if s["n"]:
                lines.append(f"  {label}, day {h}: n={s['n']}, average {s['mean']:+.2f}%, median {s['median']:+.2f}%, "
                             f"{s['pct_positive']}% beat SPY" + (f", t={s['t']}" if "t" in s else ""))
    lines += ["", "Pre-declared: drift is 'shown' only if the earnings day-20 average is above 0 with t >= 2.0 (final "
                  "report after Feb 12, 2027)."]
    return "\n".join(lines)


def email(subject, body, idempotency):
    from research.real_position_alert_v1.monitor import resend_key, send
    return send(subject, body, resend_key(), idempotency)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--morning", action="store_true")
    parser.add_argument("--evening", action="store_true")
    parser.add_argument("--print", action="store_true", help="print instead of emailing")
    parser.add_argument("--day", help="override today's date (testing)")
    args = parser.parse_args()
    today = args.day or datetime.now(NY).date().isoformat()
    if phase(today) == "finished":
        marker = OUT / "FINISHED"
        if not marker.exists():
            body = ("The EP forward watch ended on Feb 12, 2027 as planned. Please switch off the ep-watch timers; "
                    "the final results doc is next.")
            print(body) if args.print else email("EP watch finished", body, "ep-watch-finished")
            save_json(marker, {"at": today})
        return
    api, sec = Alpaca(), Sec()
    if args.morning:
        rows = morning(api, sec, today)
        if rows is None:
            print(json.dumps({"day": today, "morning": "skipped (not a trading day or outside the event window)"}))
            return
        body = morning_text(today, rows)
        n = sum(r["earnings"] for r in rows)
        print(body) if args.print else email(f"EP watch {today}: {n} earnings gap-up{'s' if n != 1 else ''}", body,
                                             f"ep-watch-morning-{today}")
    if args.evening:
        snap = evening(api, sec, today)
        if snap is None:
            print(json.dumps({"day": today, "evening": "skipped (not a trading day or outside the window)"}))
            return
        body = evening_text(snap)
        print(body) if args.print else email(f"EP paper ledger {today}", body, f"ep-watch-evening-{today}")


if __name__ == "__main__":
    main()
