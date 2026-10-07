"""Forward watch (owner's request, Oct 7, 2026: "test forward, not just backward"): every idea the owner brings in (tweets,
Joey's picks, newsletter calls) is followed as if $10,000 had gone into it, next to the same $10,000 in SPY from the
same moment. Paper only: read-only market data, no orders. Dollars first.

  PYTHONPATH=src:. .venv/bin/python -m research.forward_watch_v1.watch --print     # print today's table
  PYTHONPATH=src:. .venv/bin/python -m research.forward_watch_v1.watch             # email it (the server's 16:45 job)

Ideas live in ideas.json. Kinds: "stock" (bought at `entry`, or at the open/close of `added`; optional stop and target,
checked on daily bars: a gap past either fills at the open, both in one day counts as the stop), "basket" (the $10,000
split equally, each stock bought at the open/close of `added`), and "option" (bought at `entry` per share, valued at the
daily close of the option, then at its intrinsic value on expiration day).
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import urllib.parse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
IDEAS = Path(__file__).resolve().parent / "ideas.json"
OUT = ROOT / "outputs/forward_watch"
NY = ZoneInfo("America/New_York")
STAKE = 10_000.0


def get(url):
    from research.lite_dip_history_v1.run import fetch
    from research.lite_paper_bot_v1.bot import credentials
    key, secret = credentials()
    return fetch(url, key, secret)


def daily_bars(symbols, start, end):
    """{symbol: [(date, o, h, l, c)]}, raw prices, from Alpaca SIP daily bars (paged)."""
    from research.lite_dip_history_v1.run import DATA
    out, token = {}, None
    while True:
        q = {"symbols": ",".join(symbols), "timeframe": "1Day", "feed": "sip", "adjustment": "raw", "limit": 10000,
             "start": f"{start}T00:00:00Z", "end": end}
        if token:
            q["page_token"] = token
        page = get(f"{DATA}/v2/stocks/bars?{urllib.parse.urlencode(q)}")
        for s, rows in (page.get("bars") or {}).items():
            out.setdefault(s, []).extend((r["t"][:10], r["o"], r["h"], r["l"], r["c"]) for r in rows)
        token = page.get("next_page_token")
        if not token:
            return out


def option_closes(symbol, start, end):
    from research.lite_dip_history_v1.run import DATA
    q = {"symbols": symbol, "timeframe": "1Day", "start": f"{start}T00:00:00Z", "end": end, "limit": 1000}
    page = get(f"{DATA}/v1beta1/options/bars?{urllib.parse.urlencode(q)}")
    return [(r["t"][:10], r["c"]) for r in (page.get("bars") or {}).get(symbol, [])]


def entry_price(bars, idea):
    if idea.get("entry") is not None:
        return idea["entry"]
    day = next((b for b in bars if b[0] >= idea["added"]), None)
    if day is None:
        return None
    return day[1] if idea.get("entry_at") == "open" else day[4]


def stock_result(bars, idea, entry):
    """(value of $1 at entry now, status) for a stock idea, applying its stop/target from the day after `added`."""
    stop, target = idea.get("stop"), idea.get("target")
    after = [b for b in bars if b[0] > idea["added"]]
    if stop is not None and target is not None:
        for d, o, h, l, c in after:
            if o <= stop:
                return o / entry, f"stopped (gap) {d} at {o:.2f}"
            if o >= target:
                return o / entry, f"target hit (gap) {d} at {o:.2f}"
            if l <= stop:
                return stop / entry, f"stopped {d} at {stop:.2f}"
            if h >= target:
                return target / entry, f"target hit {d} at {target:.2f}"
    last = bars[-1]
    return last[4] / entry, "open"


def evaluate(ideas, bars, spy, options, today):
    """Rows of dollars for each idea and its SPY twin, plus totals."""
    rows = []
    for idea in ideas:
        if idea["kind"] == "option":
            series = options.get(idea["symbol"], [])
            entry = idea["entry"]
            if today >= idea["expires"]:
                und = [b for b in bars.get(idea["underlying"], []) if b[0] <= idea["expires"]]
                value = max(und[-1][4] - idea["strike"], 0.0) if und else 0.0
                status = f"expired {idea['expires']} (SPY {und[-1][4]:.2f})" if und else "expired"
            else:
                value = series[-1][1] if series else entry
                status = f"open, last {value:.2f}"
            growth = value / entry
            spy_entry = next((b[4] for b in spy if b[0] >= idea["added"]), None)
            note = ""
        elif idea["kind"] == "stock":
            b = bars.get(idea["symbol"], [])
            entry = entry_price(b, idea)
            if not b or entry is None:
                rows.append({"idea": idea["name"], "status": "no price data"})
                continue
            growth, status = stock_result(b, idea, entry)
            spy_entry = entry_price(spy, {**idea, "entry": None})
            note = (f"{idea['symbol']} {entry:.2f} -> {b[-1][4]:.2f}" if status == "open"
                    else f"{idea['symbol']} {entry:.2f} -> sold {entry * growth:.2f} (now {b[-1][4]:.2f})")
        else:
            parts, missing = [], []
            for s in idea["symbols"]:
                b = bars.get(s, [])
                e = entry_price(b, idea)
                if not b or e is None:
                    missing.append(s)
                    continue
                parts.append((s, b[-1][4] / e))
            growth = sum(g for _, g in parts) / len(parts) if parts else 1.0
            best = max(parts, key=lambda x: x[1]) if parts else None
            worst = min(parts, key=lambda x: x[1]) if parts else None
            status = f"{len(parts)} stocks" + (f" (no data: {', '.join(missing)})" if missing else "")
            note = (f"best {best[0]} {100 * (best[1] - 1):+.1f}%, worst {worst[0]} {100 * (worst[1] - 1):+.1f}%"
                    if parts else "")
            spy_entry = entry_price(spy, {**idea, "entry": None})
        spy_growth = spy[-1][4] / spy_entry if spy_entry else 1.0
        rows.append({"idea": idea["name"], "source": idea["source"], "since": idea["added"], "status": status,
                     "note": note, "value": round(STAKE * growth, 2), "profit": round(STAKE * (growth - 1), 2),
                     "spy_profit": round(STAKE * (spy_growth - 1), 2)})
    good = [r for r in rows if "profit" in r]
    totals = {"ideas": len(good), "invested": STAKE * len(good), "profit": round(sum(r["profit"] for r in good), 2),
              "spy_profit": round(sum(r["spy_profit"] for r in good), 2),
              "beating_spy": sum(r["profit"] > r["spy_profit"] for r in good)}
    return rows, totals


def render(rows, totals, today):
    lines = [f"Forward watch, {today}: every idea as if $10,000 went in, next to the same $10,000 in SPY.",
             "Paper only. No orders.", ""]
    for r in rows:
        if "profit" not in r:
            lines.append(f"- {r['idea']}: {r['status']}")
            continue
        lines.append(f"- {r['idea']}  (since {r['since']}; {r['source']})")
        lines.append(f"    ${r['value']:,.0f} now, {r['profit']:+,.0f}   vs SPY {r['spy_profit']:+,.0f}   [{r['status']}]"
                     + (f"  {r['note']}" if r["note"] else ""))
    lines += ["", f"All {totals['ideas']} ideas: {totals['profit']:+,.0f} on ${totals['invested']:,.0f}; "
                  f"the same money in SPY: {totals['spy_profit']:+,.0f}. Beating SPY: {totals['beating_spy']} of {totals['ideas']}."]
    return "\n".join(lines)


def run(today=None):
    ideas = json.loads(IDEAS.read_text())
    today = today or datetime.now(NY).date().isoformat()
    first = min(i["added"] for i in ideas)
    start = (date.fromisoformat(first) - timedelta(days=5)).isoformat()
    end = (datetime.now(timezone.utc) - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
    symbols = sorted({s for i in ideas for s in (i.get("symbols") or [i.get("symbol")] if i["kind"] != "option" else [])}
                     | {i["underlying"] for i in ideas if i["kind"] == "option"} | {"SPY"})
    bars = {}
    for k in range(0, len(symbols), 100):
        bars.update(daily_bars(symbols[k:k + 100], start, end))
    options = {i["symbol"]: option_closes(i["symbol"], i["added"], end) for i in ideas if i["kind"] == "option"}
    rows, totals = evaluate(ideas, bars, bars["SPY"], options, today)
    OUT.mkdir(parents=True, exist_ok=True)
    hist_path = OUT / "history.json"
    history = json.loads(hist_path.read_text()) if hist_path.exists() else {}
    history[today] = {"rows": rows, "totals": totals}
    hist_path.write_text(json.dumps(history, indent=1) + "\n")
    return render(rows, totals, today), totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args()
    body, totals = run()
    if args.print:
        print(body)
        return
    from research.real_position_alert_v1.monitor import resend_key, send
    today = datetime.now(NY).date().isoformat()
    subject = f"Forward watch {today}: ideas {totals['profit']:+,.0f} vs SPY {totals['spy_profit']:+,.0f}"
    send(subject, body, resend_key(), f"forward-watch|{today}")
    print(json.dumps({"emailed": True, "totals": totals}))


if __name__ == "__main__":
    main()
