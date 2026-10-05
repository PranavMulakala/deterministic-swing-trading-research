"""Backtest of pre-declared test #15: the unchanged Plan B dip rule on many stocks (output/DIP_RULE_MANY_STOCKS_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.dip_many_test_v1.backtest

Rule: at 10:00, if the 9:30-10:00 bar's low <= open * 0.99 and its close < open, buy at close * 1.001; sell with a
standing limit at entry * 1.02 (later 30-min bars that day, then each day's open/high; gap above fills at the open).
No stop; one position per stock. Portfolio: $100k, $10k per buy, max 10 open, biggest morning dip first. Research only.
"""
from __future__ import annotations

from collections import defaultdict
import gzip
import json
from pathlib import Path
import statistics

from research.dip_many_test_v1.fetch import HERE, path_for
from research.provenance_v1.provenance import write_manifest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/dip-many-test-results.json"
START_CASH, SLOT, MAX_POS, DIP, TARGET, BUY_BUF, SELL_COST = 100_000.0, 10_000.0, 10, 0.01, 0.02, 0.001, 0.0005
HALVES = (("2022-2023", "2022-01-01", "2023-12-31"), ("2024-2026", "2024-01-01", "2026-12-31"))


def load(symbol):
    with gzip.open(path_for(symbol), "rt") as f:
        rows = json.load(f)
    days = defaultdict(list)
    for d, m, o, h, l, c in rows:
        days[d].append({"m": m, "o": o, "h": h, "l": l, "c": c})
    return {d: sorted(v, key=lambda b: b["m"]) for d, v in days.items()}


def signal(day_bars):
    """(entry_price, dip) if the 9:30 bar qualifies, else None."""
    first = day_bars[0] if day_bars and day_bars[0]["m"] == 570 else None
    if not first:
        return None
    o, l, c = first["o"], first["l"], first["c"]
    if l <= o * (1 - DIP) and c < o:
        return c * (1 + BUY_BUF), (o - l) / o
    return None


def exit_price(day_bars, target, entry_day):
    """Price the +2% limit fills at on this day, or None. On the entry day only bars after 10:00 count."""
    bars = [b for b in day_bars if b["m"] >= 600] if entry_day else day_bars
    if not bars:
        return None
    if not entry_day and bars[0]["o"] >= target:
        return bars[0]["o"]
    for b in bars:
        if b["h"] >= target:
            return target
    return None


def per_stock_trades(days):
    """Unconstrained: every signal taken when not already holding this stock."""
    trades, pos = [], None
    for d in sorted(days):
        bars = days[d]
        if pos:
            px = exit_price(bars, pos["target"], False)
            if px:
                trades.append({**pos, "exit_date": d, "exit": px * (1 - SELL_COST), "open": False})
                pos = None
        if not pos:
            sig = signal(bars)
            if sig:
                entry = sig[0]
                pos = {"entry_date": d, "entry": entry, "target": entry * (1 + TARGET)}
                px = exit_price(bars, pos["target"], True)
                if px:
                    trades.append({**pos, "exit_date": d, "exit": px * (1 - SELL_COST), "open": False})
                    pos = None
        last_close = bars[-1]["c"]
    if pos:
        trades.append({**pos, "exit_date": sorted(days)[-1], "exit": last_close, "open": True})
    return trades


def portfolio(data, calendar):
    cash, positions, trades, curve, last_close = START_CASH, {}, [], [], {}
    for d in calendar:
        for sym in list(positions):
            bars = data[sym].get(d)
            if not bars:
                continue
            p = positions[sym]
            px = exit_price(bars, p["target"], False)
            if px:
                cash += p["shares"] * px * (1 - SELL_COST)
                trades.append({**p, "symbol": sym, "exit_date": d, "exit": px * (1 - SELL_COST), "open": False})
                del positions[sym]
        cands = []
        for sym, days in data.items():
            if sym in positions or d not in days:
                continue
            sig = signal(days[d])
            if sig:
                cands.append((sig[1], sym, sig[0]))
        for dip, sym, entry in sorted(cands, reverse=True):
            if len(positions) >= MAX_POS or cash < SLOT:
                break
            positions[sym] = {"entry_date": d, "entry": entry, "target": entry * (1 + TARGET), "shares": SLOT / entry,
                              "dip": round(dip, 4)}
            cash -= SLOT
            px = exit_price(data[sym][d], positions[sym]["target"], True)
            if px:
                p = positions.pop(sym)
                cash += p["shares"] * px * (1 - SELL_COST)
                trades.append({**p, "symbol": sym, "exit_date": d, "exit": px * (1 - SELL_COST), "open": False})
        for sym, days in data.items():
            if d in days:
                last_close[sym] = days[d][-1]["c"]
        equity = cash + sum(p["shares"] * last_close.get(p_sym, p["entry"]) for p_sym, p in positions.items())
        curve.append((d, equity))
    for sym, p in positions.items():
        trades.append({**p, "symbol": sym, "exit_date": calendar[-1], "exit": last_close[sym], "open": True})
    return trades, curve


def curve_stats(curve, start=START_CASH):
    vals = [v for _, v in curve]
    peak, dd = start, 0.0
    for v in vals:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    years = len(vals) / 252
    cagr = (vals[-1] / start) ** (1 / years) - 1
    return {"final": round(vals[-1]), "total_return_pct": round((vals[-1] / start - 1) * 100, 1),
            "cagr_pct": round(cagr * 100, 2), "max_drawdown_pct": round(dd * 100, 1),
            "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None}


def halves(curve):
    value, dates, out = dict(curve), [d for d, _ in curve], {}
    for name, a, b in HALVES:
        inside = [d for d in dates if a <= d <= b]
        before = [d for d in dates if d < inside[0]]
        out[name] = round((value[inside[-1]] / (value[before[-1]] if before else START_CASH) - 1) * 100, 1)
    return out


def trade_stats(trades, calendar):
    idx = {d: i for i, d in enumerate(calendar)}
    pnl = [(t["exit"] / t["entry"] - 1) * SLOT for t in trades]
    gains, losses = sum(p for p in pnl if p > 0), -sum(p for p in pnl if p <= 0)
    held = [idx.get(t["exit_date"], 0) - idx.get(t["entry_date"], 0) for t in trades]
    stuck = [t for t in trades if t["open"]]
    closed = [h for h, t in zip(held, trades) if not t["open"]]
    return {"trades": len(trades), "closed": len(trades) - len(stuck), "still_open_at_end": len(stuck),
            "profit_factor_incl_open": round(gains / losses, 2) if losses else None,
            "win_rate_pct": round(100 * sum(p > 0 for p in pnl) / max(len(pnl), 1), 1),
            "median_days_held_closed": statistics.median(closed) if closed else None,
            "max_days_held_closed": max(closed) if closed else None,
            "open_positions_loss_usd": round(sum((t["exit"] / t["entry"] - 1) * SLOT for t in stuck)),
            "worst_trade_pct": round(min((t["exit"] / t["entry"] - 1) * 100 for t in trades), 1) if trades else None,
            "worst_trade": min(trades, key=lambda t: t["exit"] / t["entry"]) if trades else None}


def run(symbols, spy_curve, calendar_all):
    data = {s: load(s) for s in symbols if path_for(s).exists()}
    calendar = [d for d in calendar_all]
    trades, curve = portfolio(data, calendar)
    stats = {**curve_stats(curve), "halves_return_pct": halves(curve), **trade_stats(trades, calendar),
             "stocks_in_universe": len(data)}
    spy = curve_stats(spy_curve)
    checks = {"A1_profit_factor_incl_open_at_least_1.3": (stats["profit_factor_incl_open"] or 0) >= 1.3,
              "A2_profitable_in_both_halves": all(v > 0 for v in stats["halves_return_pct"].values()),
              "A3_max_drawdown_at_most_25pct": stats["max_drawdown_pct"] >= -25.0,
              "B1_drawdown_5pts_smaller_than_spy": stats["max_drawdown_pct"] >= spy["max_drawdown_pct"] + 5,
              "B2_cagr_over_dd_beats_spy": (stats["cagr_over_dd"] or -9) > spy["cagr_over_dd"]}
    per_stock = {}
    for s, days in data.items():
        tr = per_stock_trades(days)
        pnl = [(t["exit"] / t["entry"] - 1) * 100 for t in tr]
        per_stock[s] = {"trades": len(tr), "avg_pct": round(statistics.mean(pnl), 2) if pnl else None,
                        "sum_pct": round(sum(pnl), 1), "stuck_at_end": sum(t["open"] for t in tr),
                        "stuck_loss_pct": round(sum(p for p, t in zip(pnl, tr) if t["open"]), 1)}
    profitable = sum(1 for v in per_stock.values() if v["trades"] and v["sum_pct"] > 0)
    return {"portfolio": stats, "checks": checks, "passes": all(checks.values()), "spy": spy,
            "stocks_profitable_unconstrained": f"{profitable} of {len(per_stock)}", "per_stock": per_stock,
            "trade_list": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in t.items()} for t in trades],
            "curve": [[d, round(v)] for d, v in curve]}


def main():
    u = json.loads((HERE / "universe.json").read_text())
    spy_days = load("SPY")
    calendar = sorted(spy_days)
    import urllib.parse  # noqa: F401  (SPY benchmark with dividends from Alpaca daily adjusted closes)
    from research.lite_buy_timing_v1.run import bars as alpaca_bars
    from research.lite_paper_bot_v1.bot import credentials
    key, secret = credentials()
    daily = {r["t"][:10]: r["c"] for r in alpaca_bars("SPY", "1Day", "2021-12-31T00:00:00Z", "2026-10-01T00:00:00Z",
                                                      key, secret, adjustment="all")}
    base = daily[max(d for d in daily if d < calendar[0])]
    spy_curve = [(d, START_CASH * daily[d] / base) for d in calendar if d in daily]
    out = {"plan": "output/DIP_RULE_MANY_STOCKS_TEST_PLAN_20261005.md", "first": calendar[0], "last": calendar[-1],
           "main_hindsight_free": run([r["symbol"] for r in u["main"]], spy_curve, calendar),
           "info_hindsight_lite_like": run(u["hindsight"], spy_curve, calendar)}
    out["verdict_pass"] = out["main_hindsight_free"]["passes"]
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
    write_manifest(OUT, code=["research/dip_many_test_v1/backtest.py", "research/dip_many_test_v1/universe.py",
                              "research/dip_many_test_v1/fetch.py"],
                   data=[str(path_for(s)) for s in sorted({r["symbol"] for r in u["main"]} | set(u["hindsight"]) | {"SPY"})
                         if path_for(s).exists()],
                   params={"slot": SLOT, "max_pos": MAX_POS, "dip": DIP, "target": TARGET})
    for k in ("main_hindsight_free", "info_hindsight_lite_like"):
        r = out[k]
        print(k, json.dumps({"portfolio": {x: y for x, y in r["portfolio"].items() if x != "worst_trade"},
                             "checks": r["checks"], "spy": r["spy"], "profitable": r["stocks_profitable_unconstrained"],
                             "worst_trade": r["portfolio"]["worst_trade"]}, indent=1, default=str))
    print("VERDICT", out["verdict_pass"])


if __name__ == "__main__":
    main()
