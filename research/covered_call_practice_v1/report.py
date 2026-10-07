"""Daily dollars email for the owner's covered-call practice (paper account ...U036; output/COVERED_CALL_PRACTICE_LOG.md).
Read-only: GET account and positions from Alpaca paper; never places, changes or cancels orders. Dollars only, no SPY.

  PYTHONPATH=src:. .venv/bin/python -m research.covered_call_practice_v1.report --print   # print today's report
  PYTHONPATH=src:. .venv/bin/python -m research.covered_call_practice_v1.report           # email it (server, 16:50 ET)
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import re
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/covered_call_practice"
NY = ZoneInfo("America/New_York")
PAPER = "https://paper-api.alpaca.markets"
START = 100_000.0
ACCOUNT_SUFFIX = "U036"
OCC = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")


def credentials(path=ROOT / ".env"):
    vals = {}
    for line in path.read_text().splitlines():
        m = re.fullmatch(r"\s*(?:export\s+)?(ALPACA_PAPER_API_KEY|ALPACA_PAPER_API_SECRET)\s*=\s*(.*?)\s*", line)
        if m:
            vals[m[1]] = m[2].strip("\"'")
    return vals["ALPACA_PAPER_API_KEY"], vals["ALPACA_PAPER_API_SECRET"]


def get(path, key, secret):
    req = urllib.request.Request(PAPER + path, headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def summarize(positions, today):
    """Group stock + short calls by underlying; dollars for each position."""
    shares, calls = {}, {}
    for p in positions:
        m = OCC.match(p["symbol"])
        if m and m[3] == "C" and float(p["qty"]) < 0:
            calls.setdefault(m[1], []).append({
                "symbol": p["symbol"], "n": -int(float(p["qty"])), "strike": int(m[4]) / 1000,
                "expiry": date(2000 + int(m[2][:2]), int(m[2][2:4]), int(m[2][4:])),
                "sold_at": float(p["avg_entry_price"]), "now": float(p["current_price"])})
        elif not m:
            shares[p["symbol"]] = {"qty": float(p["qty"]), "cost": float(p["avg_entry_price"]), "price": float(p["current_price"])}
    rows = []
    for sym in sorted(set(shares) | set(calls)):
        s = shares.get(sym, {"qty": 0.0, "cost": 0.0, "price": 0.0})
        row = {"symbol": sym, "shares": s["qty"], "cost": s["cost"], "price": s["price"],
               "shares_pnl": (s["price"] - s["cost"]) * s["qty"], "calls": [], "flags": []}
        premium = call_now = called_value = 0.0
        for c in calls.get(sym, []):
            premium += c["sold_at"] * 100 * c["n"]
            call_now += c["now"] * 100 * c["n"]
            called_value += (c["strike"] - s["cost"]) * 100 * c["n"] + c["sold_at"] * 100 * c["n"]
            days = (c["expiry"] - today).days
            row["calls"].append({**c, "expiry": c["expiry"].isoformat(), "days_left": days,
                                 "in_the_money": s["price"] > c["strike"]})
            if days <= 7 and s["price"] > c["strike"]:
                row["flags"].append(f"{sym} is above the ${c['strike']:g} strike with {days} days left: let it go, or roll up and out for a credit?")
            if c["now"] <= 0.2 * c["sold_at"]:
                row["flags"].append(f"{sym} ${c['strike']:g} call is worth {100 * c['now'] / c['sold_at']:.0f}% of what you sold it for: buy back and sell a new one?")
            if s["cost"] and s["price"] <= 0.85 * s["cost"]:
                row["flags"].append(f"{sym} is down {100 * (1 - s['price'] / s['cost']):.0f}% from your cost: review (hold, roll down, or exit).")
        covered = sum(c["n"] for c in calls.get(sym, [])) * 100
        if covered > s["qty"]:
            row["flags"].append(f"WARNING: {sym} calls cover {covered} shares but you hold {s['qty']:g} (part is naked).")
        row.update({"premium_kept": premium, "call_value_now": call_now, "call_pnl": premium - call_now,
                    "total_pnl": row["shares_pnl"] + premium - call_now,
                    "if_called_away": called_value if calls.get(sym) else None,
                    "break_even": s["cost"] - premium / s["qty"] if s["qty"] else None})
        rows.append(row)
    return rows


def render(rows, account, today):
    equity = float(account["equity"])
    lines = [f"Covered-call practice, {today:%a %b %d, %Y} (paper account ...{ACCOUNT_SUFFIX}; no orders placed by this email)", ""]
    for r in rows:
        lines.append(f"{r['symbol']}: {r['shares']:g} shares, bought ${r['cost']:,.2f}, now ${r['price']:,.2f}")
        for c in r["calls"]:
            lines.append(f"  Sold {c['n']} x ${c['strike']:g} call ({c['expiry']}, {c['days_left']} days left) at ${c['sold_at']:.2f}; "
                         f"now ${c['now']:.2f}  [{'ABOVE strike' if c['in_the_money'] else 'below strike'}]")
        lines.append(f"  Shares {r['shares_pnl']:+,.0f} | premium kept {r['premium_kept']:,.0f} | calls now cost {r['call_value_now']:,.0f} to buy back "
                     f"| calls {r['call_pnl']:+,.0f} | TOTAL {r['total_pnl']:+,.0f}")
        if r["if_called_away"] is not None:
            lines.append(f"  If called away at expiry: {r['if_called_away']:+,.0f}. Break-even ${r['break_even']:,.2f}.")
        lines += [f"  -> {f}" for f in r["flags"]]
        lines.append("")
    total = sum(r["total_pnl"] for r in rows)
    lines.append(f"All positions: {total:+,.0f}. Account ${equity:,.0f} ({equity - START:+,.0f} since the $100,000 start); cash ${float(account['cash']):,.0f}.")
    lines.append("Log and rules: output/COVERED_CALL_PRACTICE_LOG.md. Research, not advice; you decide every trade.")
    return "\n".join(lines), total


def run(today=None):
    key, secret = credentials()
    account = get("/v2/account", key, secret)
    if not account["account_number"].endswith(ACCOUNT_SUFFIX):
        raise SystemExit("Keys point at a different paper account than ..." + ACCOUNT_SUFFIX)
    today = today or datetime.now(NY).date()
    rows = summarize(get("/v2/positions", key, secret), today)
    body, total = render(rows, account, today)
    OUT.mkdir(parents=True, exist_ok=True)
    hist_path = OUT / "history.json"
    history = json.loads(hist_path.read_text()) if hist_path.exists() else {}
    history[today.isoformat()] = {"equity": float(account["equity"]), "rows": rows}
    hist_path.write_text(json.dumps(history, indent=1, default=str) + "\n")
    return body, total, float(account["equity"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args()
    body, total, equity = run()
    if args.print:
        print(body)
        return
    from research.real_position_alert_v1.monitor import resend_key, send
    today = datetime.now(NY).date().isoformat()
    send(f"Covered-call practice {today}: {total:+,.0f} (account ${equity:,.0f})", body, resend_key(), f"cc-practice|{today}")
    print(json.dumps({"emailed": True, "total": round(total, 2)}))


if __name__ == "__main__":
    main()
