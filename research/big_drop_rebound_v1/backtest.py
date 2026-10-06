"""Backtest of pre-declared test #19 (output/BIG_DROP_REBOUND_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.big_drop_rebound_v1.backtest

Signal at a day's close: the close is >= 10% below the previous close; the previous close is above its 200-day average;
the prior 60 days' average dollar volume is >= $200M. Buy at that close (0.1% cost), sell at +20% (standing limit,
at the open if it gaps above) or at the close of the 10th trading day after. 10% of the account per trade, at most 10
positions, biggest drops first, one position per stock. Each event's outcome doesn't depend on the portfolio, so it is
computed once; the portfolio only decides which events it can take. Research only; no orders.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import statistics

from research.breakout_test_v1.backtest import DATA, load
from research.provenance_v1.provenance import write_manifest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/big-drop-rebound-test-results.json"
START_CASH, SLOT, MAX_POS, MIN_BUY, COST = 100_000.0, 0.10, 10, 1_000.0, 0.001
DROP, TARGET, HOLD, MIN_DVOL, SMA, VOL_WIN = 0.10, 0.20, 10, 200e6, 200, 60
MAIN, STRESS = ("2020-01-02", "2026-09-28"), ("2016-10-03", "2026-09-28")
HALVES = {"main": (("2020-2022", "2020-01-01", "2022-12-31"), ("2023-2026", "2023-01-01", "2026-12-31")),
          "stress": (("2016-2020", "2016-01-01", "2020-12-31"), ("2021-2026", "2021-01-01", "2026-12-31"))}


def prepare(b):
    pc, pdv = [0.0], [0.0]
    for x, y in zip(b["close"], b["volume"]):
        pc.append(pc[-1] + x)
        pdv.append(pdv[-1] + x * y)
    return {**b, "_idx": {d: i for i, d in enumerate(b["date"])}, "_pc": pc, "_pdv": pdv}


def signal(b, i, uptrend=True):
    """The day-i drop (a negative fraction) if day i qualifies at its close, else None."""
    if i < SMA + 1:
        return None
    c = b["close"]
    if c[i] > (1 - DROP) * c[i - 1]:
        return None
    if (b["_pdv"][i] - b["_pdv"][i - VOL_WIN]) / VOL_WIN < MIN_DVOL:          # days i-60 .. i-1
        return None
    if uptrend and c[i - 1] <= (b["_pc"][i] - b["_pc"][i - SMA]) / SMA:       # 200-day average of days i-200 .. i-1
        return None
    return c[i] / c[i - 1] - 1


def outcome(b, i, entry_at="close", target_on=True, cost=COST, last_day=None):
    """How a buy triggered by day i's close ends: entry, exit and the worst dip before the exit."""
    e = i if entry_at == "close" else i + 1
    n = len(b["date"]) if last_day is None else sum(1 for d in b["date"] if d <= last_day)
    if e >= n:
        return None
    raw_entry = b["close"][i] if entry_at == "close" else b["open"][e]
    fill = raw_entry * (1 + cost)
    target, low_seen = fill * (1 + TARGET), fill
    end = i + HOLD
    for j in range(i + 1, min(end, n - 1) + 1):
        gap_ok = not (entry_at == "open" and j == e)                         # bought at that open: no gap fill
        if target_on and gap_ok and b["open"][j] >= target:
            return _result(b, i, e, fill, j, b["open"][j] * (1 - cost), "target_gap", low_seen)
        if target_on and b["high"][j] >= target:
            return _result(b, i, e, fill, j, target * (1 - cost), "target", min(low_seen, b["low"][j]))
        low_seen = min(low_seen, b["low"][j])
    if end <= n - 1:
        return _result(b, i, e, fill, end, b["close"][end] * (1 - cost), "time", low_seen)
    return _result(b, i, e, fill, n - 1, b["close"][n - 1], "open_end", low_seen)


def _result(b, i, e, fill, j, px, reason, low_seen):
    return {"signal_day": b["date"][i], "entry_day": b["date"][e], "fill": fill, "exit_day": b["date"][j],
            "exit": px, "reason": reason, "ret_pct": 100 * (px / fill - 1), "worst_dip_pct": 100 * (low_seen / fill - 1)}


def events(stocks, window, entry_at="close", target_on=True, uptrend=True, cost=COST):
    out = []
    for s, b in stocks.items():
        for i, d in enumerate(b["date"]):
            if not (window[0] <= d <= window[1]):
                continue
            drop = signal(b, i, uptrend)
            if drop is None:
                continue
            res = outcome(b, i, entry_at, target_on, cost, last_day=window[1])
            if res:
                out.append({"symbol": s, "drop": drop, "drop_pct": round(100 * drop, 2), **res})
    return out


def portfolio(evts, stocks, calendar, window, entry_at="close"):
    days = [d for d in calendar if window[0] <= d <= window[1]]
    by_entry = defaultdict(list)
    for e in evts:
        by_entry[e["entry_day"]].append(e)
    cash, equity_prev, held, trades, curve, skipped, last = START_CASH, START_CASH, {}, [], [], Counter(), {}

    def exits(d):
        nonlocal cash
        for s in [s for s, p in held.items() if p["exit_day"] == d and p["reason"] != "open_end"]:
            p = held.pop(s)
            cash += p["shares"] * p["exit"]
            trades.append({**p, "open": False, "pnl": p["shares"] * (p["exit"] - p["fill"])})

    def entries(d):
        nonlocal cash
        for e in sorted(by_entry.get(d, []), key=lambda e: (e["drop"], e["symbol"])):     # exact drop, biggest first
            if e["symbol"] in held:
                skipped["already_held"] += 1
                continue
            value = min(SLOT * equity_prev, cash)
            if len(held) >= MAX_POS or value < MIN_BUY:
                skipped["no_slot_or_cash"] += 1
                continue
            cash -= value
            held[e["symbol"]] = {**e, "shares": value / e["fill"], "cost_basis": value}

    for d in days:
        if entry_at == "open":
            entries(d)                                  # buys at the open, before that day's sales
            exits(d)
        else:
            exits(d)                                    # the +20% fills intraday, time exits at the close
            entries(d)                                  # buys at the close
        for s in held:
            i = stocks[s]["_idx"].get(d)
            if i is not None:
                last[s] = stocks[s]["close"][i]
        equity_prev = cash + sum(p["shares"] * last.get(s, p["fill"]) for s, p in held.items())
        curve.append((d, equity_prev))
    for s, p in held.items():
        mark = last.get(s, p["fill"])
        trades.append({**p, "open": True, "exit": mark, "pnl": p["shares"] * (mark - p["fill"])})
    return trades, curve, skipped


def curve_stats(curve):
    vals = [v for _, v in curve]
    peak, dd = START_CASH, 0.0
    for v in vals:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    years = (date.fromisoformat(curve[-1][0]) - date.fromisoformat(curve[0][0])).days / 365.25
    cagr = (vals[-1] / START_CASH) ** (1 / years) - 1
    return {"final": round(vals[-1]), "total_pct": round(100 * (vals[-1] / START_CASH - 1), 1),
            "cagr_pct": round(100 * cagr, 2), "max_drawdown_pct": round(100 * dd, 1),
            "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None}


def halves(curve, periods):
    value, dates, out = dict(curve), [d for d, _ in curve], {}
    for name, a, b in periods:
        inside = [d for d in dates if a <= d <= b]
        before = [d for d in dates if d < inside[0]]
        out[name] = round(100 * (value[inside[-1]] / (value[before[-1]] if before else START_CASH) - 1), 1)
    return out


def spy_curve(spy, window):
    idx = [i for i, d in enumerate(spy["date"]) if window[0] <= d <= window[1]]
    base = spy["close"][idx[0] - 1]
    return [(spy["date"][i], START_CASH * spy["close"][i] / base) for i in idx]


def evaluate(evts, stocks, calendar, window, periods, spy, entry_at="close"):
    trades, curve, skipped = portfolio(evts, stocks, calendar, window, entry_at)
    pnl = [t["pnl"] for t in trades]
    gp, gl = sum(p for p in pnl if p > 0), -sum(p for p in pnl if p <= 0)
    rets = [100 * (t["exit"] / t["fill"] - 1) for t in trades]
    s, b = curve_stats(curve), curve_stats(spy_curve(spy, window))
    out = {**s, "halves_return_pct": halves(curve, periods), "trades": len(trades),
           "open_at_end": sum(t["open"] for t in trades), "profit_factor_incl_open": round(gp / gl, 2) if gl else None,
           "win_rate_pct": round(100 * sum(p > 0 for p in pnl) / max(len(pnl), 1), 1),
           "avg_return_per_trade_pct": round(statistics.mean(rets), 2) if rets else None,
           "median_return_per_trade_pct": round(statistics.median(rets), 2) if rets else None,
           "hit_plus20_pct": round(100 * sum(t["reason"].startswith("target") for t in trades) / max(len(trades), 1), 1),
           "fell_another_10pct_pct": round(100 * sum(t["worst_dip_pct"] <= -10 for t in trades) / max(len(trades), 1), 1),
           "worst_trade": min(trades, key=lambda t: t["exit"] / t["fill"]) if trades else None,
           "exit_reasons": dict(Counter(t["reason"] if not t["open"] else "open_end" for t in trades)),
           "pnl_by_year": {y: round(v) for y, v in sorted(_by_year(trades).items())},
           "most_traded": Counter(t["symbol"] for t in trades).most_common(10), "skipped": dict(skipped)}
    out["checks"] = {"A1_profit_factor_incl_open_at_least_1.3": (out["profit_factor_incl_open"] or 0) >= 1.3,
                     "A2_profitable_in_both_halves": all(v > 0 for v in out["halves_return_pct"].values()),
                     "A3_max_drawdown_at_most_25pct": out["max_drawdown_pct"] >= -25.0,
                     "B1_drawdown_5pts_smaller_than_spy": out["max_drawdown_pct"] >= b["max_drawdown_pct"] + 5,
                     "B2_cagr_over_dd_beats_spy": (out["cagr_over_dd"] or -9) > b["cagr_over_dd"]}
    out["passes"] = all(out["checks"].values())
    return out, b, trades, curve


def _by_year(trades):
    agg = defaultdict(float)
    for t in trades:
        agg[t["entry_day"][:4]] += t["pnl"]
    return agg


def main():
    stocks = {}
    for path in sorted(DATA.glob("*.csv.gz")):
        s = path.name[:-7]
        if s != "SPY":
            stocks[s] = prepare(load(s))
    spy = load("SPY")
    calendar = spy["date"]
    main_evts = events(stocks, MAIN)
    main_res, spy_main, trades, curve = evaluate(main_evts, stocks, calendar, MAIN, HALVES["main"], spy)
    stress_res, spy_stress, _, _ = evaluate(events(stocks, STRESS), stocks, calendar, STRESS, HALVES["stress"], spy)
    if main_res["passes"]:
        verdict = "PASS (robust)" if stress_res["passes"] else "PASS (post-COVID only)"
    else:
        verdict = "FAIL"
    info = {}
    for name, kw, entry_at in (("buy_next_open", {"entry_at": "open"}, "open"), ("no_plus20_target", {"target_on": False}, "close"),
                               ("no_uptrend_filter", {"uptrend": False}, "close"), ("costs_0.25pct", {"cost": 0.0025}, "close")):
        res, _, _, _ = evaluate(events(stocks, MAIN, **kw), stocks, calendar, MAIN, HALVES["main"], spy, entry_at)
        info[name] = res
    unconstrained = {"events": len(main_evts),
                     "hit_plus20_pct": round(100 * sum(e["reason"].startswith("target") for e in main_evts) / len(main_evts), 1),
                     "fell_another_10pct_pct": round(100 * sum(e["worst_dip_pct"] <= -10 for e in main_evts) / len(main_evts), 1),
                     "avg_ret_pct": round(statistics.mean(e["ret_pct"] for e in main_evts), 2),
                     "median_ret_pct": round(statistics.median(e["ret_pct"] for e in main_evts), 2),
                     "win_rate_pct": round(100 * sum(e["ret_pct"] > 0 for e in main_evts) / len(main_evts), 1)}
    out = {"plan": "output/BIG_DROP_REBOUND_TEST_PLAN_20261005.md", "verdict": verdict, "main": main_res, "spy_main": spy_main,
           "stress": stress_res, "spy_stress": spy_stress, "info": info, "all_events_main_unconstrained": unconstrained,
           "events_main": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.items()} for e in main_evts],
           "trades_main": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in t.items()} for t in trades],
           "curve_main": [[d, round(v, 2)] for d, v in curve]}
    OUT.write_text(json.dumps(out, default=str) + "\n")
    write_manifest(OUT, code=["research/big_drop_rebound_v1/backtest.py"],
                   data=[str(DATA / f"{s}.csv.gz") for s in sorted(stocks)] + [str(DATA / "SPY.csv.gz")],
                   params={"drop": DROP, "target": TARGET, "hold": HOLD, "min_dvol": MIN_DVOL, "sma": SMA, "slot": SLOT,
                           "max_pos": MAX_POS, "cost": COST, "main": MAIN, "stress": STRESS})
    keys = ("final", "cagr_pct", "max_drawdown_pct", "cagr_over_dd", "halves_return_pct", "trades", "profit_factor_incl_open",
            "win_rate_pct", "avg_return_per_trade_pct", "median_return_per_trade_pct", "hit_plus20_pct",
            "fell_another_10pct_pct", "exit_reasons", "pnl_by_year", "most_traded", "skipped", "checks")
    print(json.dumps({"verdict": verdict, "main": {k: main_res[k] for k in keys}, "worst_trade": main_res["worst_trade"],
                      "spy_main": spy_main, "stress": {k: stress_res[k] for k in ("final", "cagr_pct", "max_drawdown_pct",
                                                                                 "profit_factor_incl_open", "passes")},
                      "spy_stress": spy_stress, "unconstrained": unconstrained,
                      "info": {n: {k: v[k] for k in ("final", "cagr_pct", "max_drawdown_pct", "profit_factor_incl_open",
                                                     "trades", "hit_plus20_pct")} for n, v in info.items()}},
                     indent=1, default=str))


if __name__ == "__main__":
    main()
