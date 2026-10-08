"""Backtest of pre-declared test #27: ~1-week MU calls bought at 10:00 ET on mornings MU opens down 2%+
(plan: output/MU_DIP_WEEKLY_CALLS_TEST_PLAN_20261008.md). Research only; no orders. Dollars only, no SPY line.

  PYTHONPATH=src:. .venv/bin/python -m research.mu_dip_calls_v1.fetch      # data (Alpaca + Databento, approved)
  PYTHONPATH=src:. .venv/bin/python -m research.mu_dip_calls_v1.backtest   # results
"""
from __future__ import annotations

import csv
from datetime import date
import gzip
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/mu_dip_calls_data"
OUT = ROOT / "output/mu-dip-weekly-calls-test-results.json"
STAKE, FEE, LAST = 1_000.0, 0.03, "2026-10-07"
WEEK, TWO_WEEK = (4, 11, 7), (11, 18, 14)
HALVES = (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2026", "2023-01-01", "2026-12-31"))


def parse_osi(symbol):
    """'MU    200313C00045000' -> (expiration, 'C'/'P', strike), else None."""
    s = symbol.replace(" ", "")
    if not s.startswith("MU") or len(s) != 17:
        return None
    return date(2000 + int(s[2:4]), int(s[4:6]), int(s[6:8])), s[8], int(s[9:17]) / 1000


def osi(exp, strike):
    return f"MU    {exp:%y%m%d}C{round(strike * 1000):08d}"


def pick_contract(chain, day, spot, dte=WEEK):
    """chain: {(exp, strike): (bid, ask)} calls. Expiration closest to dte[2] days within dte[0]-dte[1] (ties: later);
    strike closest to spot (ties: higher); needs bid > 0 and ask > 0. Returns (exp, strike, bid, ask) or None."""
    lo, hi, target = dte
    exps = sorted({e for (e, k), (b, a) in chain.items() if lo <= (e - day).days <= hi and b > 0 and a > 0})
    if not exps or spot is None:
        return None
    exp = min(exps, key=lambda e: (abs((e - day).days - target), -e.toordinal()))
    strikes = [(k, q) for (e, k), q in chain.items() if e == exp and q[0] > 0 and q[1] > 0]
    k, (b, a) = min(strikes, key=lambda x: (abs(x[0] - spot), -x[0]))
    return exp, k, b, a


def exit_scan(quotes, entry_ask, multiple, expiry_close, strike):
    """quotes: [(ts, bid, ask)] after entry, in time order. First bid >= multiple x entry_ask -> sell at that bid;
    else intrinsic at the expiration-day close. Returns (exit_price, how, ts)."""
    if multiple is not None:
        for ts, bid, ask in quotes:
            if bid >= multiple * entry_ask:
                return bid, "target", ts
    return max(expiry_close - strike, 0.0), "expiration", None


def trade_pnl(entry_ask, exit_price, how):
    """$1,000 per trade with fractional contracts; $0.03 a contract in, and out when sold at the target."""
    per_contract_cost = entry_ask * 100 + FEE
    n = STAKE / per_contract_cost
    proceeds = n * (exit_price * 100 - (FEE if how == "target" else 0.0))
    return proceeds - STAKE, n


def load_chain(day):
    chain = {}
    with gzip.open(DATA / "chain" / f"{day}.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            chain[(date.fromisoformat(r["expiration"]), float(r["strike"]))] = (float(r["bid"]), float(r["ask"]))
    return chain


def load_quotes(day, symbol):
    p = DATA / "hold" / f"{day}_{symbol.replace(' ', '')}.csv.gz"
    if not p.exists():
        return None
    with gzip.open(p, "rt") as f:
        return [(r["ts"], float(r["bid"]), float(r["ask"])) for r in csv.DictReader(f)]


def run_trades(days, meta, dte=WEEK, multiple=2.0):
    trades, skipped = [], {}
    for day in days:
        m = meta[day]
        d = date.fromisoformat(day)
        pick = pick_contract(load_chain(day), d, m["spot10"], dte)
        if pick is None:
            skipped["no_contract"] = skipped.get("no_contract", 0) + 1
            continue
        exp, k, bid, ask = pick
        if exp.isoformat() > LAST:
            skipped["expires_after_last_date"] = skipped.get("expires_after_last_date", 0) + 1
            continue
        quotes = load_quotes(day, osi(exp, k))
        close = meta.get("closes", {}).get(exp.isoformat()) or m.get("exp_closes", {}).get(exp.isoformat())
        if quotes is None or close is None:
            skipped["missing_data"] = skipped.get("missing_data", 0) + 1
            continue
        price, how, ts = exit_scan(quotes, ask, multiple, close, k)
        pnl, n = trade_pnl(ask, price, how)
        trades.append({"day": day, "gap_pct": m["gap_pct"], "spot10": m["spot10"], "expiration": exp.isoformat(),
                       "strike": k, "entry_ask": ask, "entry_bid": bid, "contract_cost": round(ask * 100 + FEE, 2),
                       "exit": round(price, 4), "how": how, "exit_ts": ts, "contracts": round(n, 4), "pnl": round(pnl, 2)})
    return trades, skipped


def stats(trades, halves=HALVES):
    if not trades:
        return {"trades": 0}
    pnl = [t["pnl"] for t in trades]
    streak = worst_streak = 0
    for p in pnl:
        streak = streak + 1 if p < 0 else 0
        worst_streak = max(worst_streak, streak)
    by_year = {}
    for t in trades:
        by_year[t["day"][:4]] = round(by_year.get(t["day"][:4], 0) + t["pnl"], 2)
    return {"trades": len(trades), "total_pnl": round(sum(pnl), 2), "avg_per_trade": round(statistics.mean(pnl), 2),
            "median_per_trade": round(statistics.median(pnl), 2), "win_pct": round(100 * sum(p > 0 for p in pnl) / len(pnl), 1),
            "hit_target_pct": round(100 * sum(t["how"] == "target" for t in trades) / len(trades), 1),
            "expired_worthless_pct": round(100 * sum(t["how"] == "expiration" and t["exit"] == 0 for t in trades) / len(trades), 1),
            "best_trade": max(pnl), "worst_trade": min(pnl), "longest_losing_streak": worst_streak,
            "avg_contract_cost": round(statistics.mean(t["contract_cost"] for t in trades), 2),
            "by_year": by_year,
            "halves": {n: round(sum(t["pnl"] for t in trades if a <= t["day"] <= b), 2) for n, a, b in halves}}


def main():
    meta = json.loads((DATA / "days.json").read_text())
    days, closes = meta["days"], meta["closes"]
    for d in days.values():
        d["exp_closes"] = closes
    signal = sorted(d for d, m in days.items() if m["signal"])
    base = sorted(d for d, m in days.items() if m["baseline"])
    main_t, main_skip = run_trades(signal, days)
    base_t, base_skip = run_trades(base, days)
    m, b = stats(main_t), stats(base_t)
    checks = {"C1_total_pnl_positive": m["total_pnl"] > 0,
              "C2_both_halves_profitable": all(v > 0 for v in m["halves"].values()),
              "C3_beats_ordinary_mornings": m["avg_per_trade"] > b["avg_per_trade"]}
    info = {}
    for name, sel, dte, mult in (("target_50", signal, WEEK, 1.5), ("no_target", signal, WEEK, None),
                                 ("gap_3pct", [d for d in signal if days[d]["gap_pct"] <= -3.0], WEEK, 2.0),
                                 ("two_week", signal, TWO_WEEK, 2.0)):
        t, s = run_trades(sel, days, dte, mult)
        info[name] = {**stats(t), "skipped": s}
    out = {"plan": "output/MU_DIP_WEEKLY_CALLS_TEST_PLAN_20261008.md", "verdict": "PASS" if all(checks.values()) else "FAIL",
           "checks": checks, "main": {**m, "skipped": main_skip}, "ordinary_mornings": {**b, "skipped": base_skip},
           "info": info, "main_trades": main_t, "baseline_trades": base_t}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("verdict", "checks", "main", "ordinary_mornings")}, indent=1))
    print(json.dumps({k: {x: v.get(x) for x in ("trades", "total_pnl", "avg_per_trade", "win_pct", "hit_target_pct", "expired_worthless_pct", "halves")}
                      for k, v in info.items()}, indent=1))


if __name__ == "__main__":
    main()
