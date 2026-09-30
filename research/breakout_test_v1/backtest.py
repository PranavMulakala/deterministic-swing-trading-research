"""Backtest of the pre-declared TikTok breakout rules (output/BREAKOUT_TEST_PLAN_20260929.md). Research only.

  PYTHONPATH=src:. .venv/bin/python -m research.breakout_test_v1.backtest

Reads outputs/breakout_data/<SYMBOL>.csv.gz (research/breakout_test_v1/fetch.py) and writes
output/breakout-test-results.json. Plain Python; every rule below maps to a numbered rule in the plan.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/breakout_data"
START_EQUITY, SLIP, RISK, MAX_WEIGHT, MAX_POSITIONS = 100_000.0, 0.001, 0.01, 0.25, 10
MIN_PRICE, MIN_DOLLAR_VOLUME, MIN_VOLUME, LEADER_PCT = 10.0, 20_000_000.0, 750_000.0, 0.70
RUNUP_DAYS, RUNUP_MIN, BASE_DAYS, BASE_MAX_RANGE, MAX_PULLBACK = 60, 0.30, 10, 0.12, 0.25
VOLUME_MULT, STOP_MIN, STOP_MAX = 1.5, 0.005, 0.10
HALVES = (("2016-2020", "2016-01-01", "2020-12-31"), ("2021-2026", "2021-01-01", "2026-12-31"))


def load(symbol):
    text = gzip.decompress((DATA / f"{symbol}.csv.gz").read_bytes()).decode()
    rows = [line.split(",") for line in text.splitlines()[1:] if line]
    return {"date": [r[0] for r in rows], "open": [float(r[1]) for r in rows], "high": [float(r[2]) for r in rows],
            "low": [float(r[3]) for r in rows], "close": [float(r[4]) for r in rows], "volume": [float(r[5]) for r in rows]}


def sma(values, n):
    out, total = [None] * len(values), 0.0
    for i, v in enumerate(values):
        total += v
        if i >= n:
            total -= values[i - n]
        if i >= n - 1:
            out[i] = total / n
    return out


def market_filter(spy):
    """Rule 1, by date."""
    close = spy["close"]
    s10, s20, s50 = sma(close, 10), sma(close, 20), sma(close, 50)
    ok = {}
    for i, day in enumerate(spy["date"]):
        if i < 55 or s50[i] is None:
            ok[day] = False
            continue
        ok[day] = (close[i] > s10[i] > s20[i] > s50[i] and s10[i] > s10[i - 5] and s20[i] > s20[i - 5]
                   and s50[i] > s50[i - 5])
    return ok


def scan(bars):
    """Rules 2, 4 and 5 for one stock: liquid-day 21-day returns and breakout candidates."""
    c, h, l, v = bars["close"], bars["high"], bars["low"], bars["volume"]
    dollar = sma([a * b for a, b in zip(c, v)], 20)
    avg_volume = sma(v, 20)
    liquid, candidates = {}, []
    for t in range(RUNUP_DAYS + 1, len(c)):
        if c[t] < MIN_PRICE or dollar[t] < MIN_DOLLAR_VOLUME or avg_volume[t] < MIN_VOLUME:
            continue
        ret21 = c[t] / c[t - 21] - 1
        liquid[bars["date"][t]] = ret21
        prior_volume = avg_volume[t - 1]
        base_high = max(h[t - BASE_DAYS:t])
        if not (c[t] > base_high and prior_volume and v[t] >= VOLUME_MULT * prior_volume):
            continue
        if not STOP_MIN <= (c[t] - l[t]) / c[t] <= STOP_MAX:
            continue
        base_low = min(l[t - BASE_DAYS:t])
        if (base_high - base_low) / base_high > BASE_MAX_RANGE:
            continue
        window = c[t - RUNUP_DAYS:t]
        peak_at = max(range(len(window)), key=lambda i: window[i])
        peak, low_before = window[peak_at], min(window[:peak_at + 1])
        if peak < (1 + RUNUP_MIN) * low_before or base_low < (1 - MAX_PULLBACK) * peak:
            continue
        candidates.append({"date": bars["date"][t], "close": c[t], "low": l[t], "ret21": ret21})
    return liquid, candidates


def percentile(values, q):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def simulate(days, market_ok, leaders_cut, candidates, series):
    """Rules 6-10: a cash account taking signals at the close and managing exits daily."""
    index = {day: i for i, day in enumerate(days)}
    cash, positions, trades, curve = START_EQUITY, {}, [], []
    last_close = {}

    def bar(symbol, day):
        s = series[symbol]
        i = s["at"].get(day)
        return None if i is None else (s["open"][i], s["low"][i], s["close"][i], s["sma10"][i])

    def sell(symbol, shares, price, day, reason):
        nonlocal cash
        p = positions[symbol]
        cash += shares * price * (1 - SLIP)
        p["proceeds"] += shares * price * (1 - SLIP)
        p["shares"] -= shares
        p["exits"].append(reason)
        if p["shares"] <= 1e-9:
            trades.append({"symbol": symbol, "entry_date": p["entry_date"], "exit_date": day, "cost": p["cost"],
                           "pnl": p["proceeds"] - p["cost"], "return_pct": (p["proceeds"] / p["cost"] - 1) * 100,
                           "days": index[day] - p["entry_index"], "exits": p["exits"]})
            del positions[symbol]

    for day in days:
        for symbol in list(positions):
            b = bar(symbol, day)
            if b is None:
                continue
            opening, low, close, s10 = b
            p = positions[symbol]
            last_close[symbol] = close
            n = index[day] - p["entry_index"]
            if n <= 0:
                continue
            if opening <= p["stop"]:
                sell(symbol, p["shares"], opening, day, "stop_gap")
                continue
            if low <= p["stop"]:
                sell(symbol, p["shares"], p["stop"], day, "stop")
                continue
            if n >= 3 and p["trims"] == 0:
                sell(symbol, round(0.3 * p["original"], 6), close, day, "trim_day3")
                p["stop"], p["trims"] = p["entry"], 1
            if symbol in positions and n >= 5 and p["trims"] == 1:
                sell(symbol, round(0.2 * p["original"], 6), close, day, "trim_day5")
                p["trims"] = 2
            if symbol in positions and n >= 5 and s10 is not None and close < s10:
                sell(symbol, p["shares"], close, day, "below_10sma")
        equity = cash + sum(p["shares"] * last_close.get(s, p["entry"]) for s, p in positions.items())
        if market_ok.get(day) and day in candidates:
            cut = leaders_cut.get(day)
            picks = sorted((x for x in candidates[day] if cut is not None and x["ret21"] >= cut
                            and x["symbol"] not in positions), key=lambda x: -x["ret21"])
            for x in picks:
                if len(positions) >= MAX_POSITIONS:
                    break
                entry = x["close"] * (1 + SLIP)
                risk_per_share = entry - x["low"]
                if risk_per_share <= 0:
                    continue
                shares = math.floor(min(RISK * equity / risk_per_share, MAX_WEIGHT * equity / entry, cash / entry))
                if shares < 1:
                    continue
                cash -= shares * entry
                positions[x["symbol"]] = {"entry": entry, "stop": x["low"], "shares": shares, "original": shares,
                                          "cost": shares * entry, "proceeds": 0.0, "trims": 0, "exits": [],
                                          "entry_date": day, "entry_index": index[day]}
                last_close[x["symbol"]] = x["close"]
        equity = cash + sum(p["shares"] * last_close.get(s, p["entry"]) for s, p in positions.items())
        curve.append((day, equity, len(positions)))
    return trades, curve, positions


def report(trades, curve, spy, market_ok):
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gain, loss = sum(t["pnl"] for t in wins), -sum(t["pnl"] for t in losses)
    peak, worst = START_EQUITY, 0.0
    for _, equity, _ in curve:
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1)
    value = {day: equity for day, equity, _ in curve}
    days = [d for d, _, _ in curve]

    def change(a, b):
        inside = [d for d in days if a <= d <= b]
        start = value[max([d for d in days if d < inside[0]], default=inside[0])]
        return value[inside[-1]] / start - 1

    spy_close = dict(zip(spy["date"], spy["close"]))
    years = (len(days) / 252)
    by_year = defaultdict(float)
    for t in trades:
        by_year[t["exit_date"][:4]] += t["pnl"]
    halves = {name: round(change(a, b) * 100, 1) for name, a, b in HALVES}
    final = curve[-1][1]
    result = {
        "trades": len(trades), "trades_per_year": round(len(trades) / years, 1),
        "win_rate_pct": round(100 * len(wins) / max(len(trades), 1), 1),
        "avg_win_pct": round(sum(t["return_pct"] for t in wins) / max(len(wins), 1), 2),
        "avg_loss_pct": round(sum(t["return_pct"] for t in losses) / max(len(losses), 1), 2),
        "avg_hold_days": round(sum(t["days"] for t in trades) / max(len(trades), 1), 1),
        "profit_factor": round(gain / loss, 2) if loss else None,
        "final_equity": round(final), "total_return_pct": round((final / START_EQUITY - 1) * 100, 1),
        "cagr_pct": round(((final / START_EQUITY) ** (1 / years) - 1) * 100, 1),
        "max_drawdown_pct": round(worst * 100, 1), "halves_return_pct": halves,
        "spy_buy_hold_return_pct": round((spy_close[days[-1]] / spy_close[days[0]] - 1) * 100, 1),
        "spy_buy_hold_halves_pct": {name: round((spy_close[[d for d in days if d <= b][-1]] /
                                                  spy_close[max([d for d in days if d < a], default=days[0])] - 1) * 100, 1)
                                    for name, a, b in HALVES},
        "market_filter_on_pct": round(100 * sum(market_ok.get(d, False) for d in days) / len(days), 1),
        "pnl_by_exit_year": {y: round(v) for y, v in sorted(by_year.items())},
        "best_trade": max(trades, key=lambda t: t["return_pct"], default=None),
        "worst_trade": min(trades, key=lambda t: t["return_pct"], default=None),
    }
    checks = {"1_profit_factor_at_least_1.3": (result["profit_factor"] or 0) >= 1.3,
              "2_profitable_in_both_halves": all(v > 0 for v in halves.values()),
              "3_max_drawdown_at_most_25pct": result["max_drawdown_pct"] >= -25.0}
    result["pre_declared_checks"] = checks
    result["works"] = all(checks.values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/breakout-test-results.json")
    args = parser.parse_args()
    symbols = json.loads((DATA / "universe.json").read_text())
    spy = load("SPY")
    days = [d for d in spy["date"] if d >= "2016-04-01"]
    market_ok = market_filter(spy)
    liquid_by_day, candidates, series = defaultdict(list), defaultdict(list), {}
    for n, symbol in enumerate(symbols, 1):
        path = DATA / f"{symbol}.csv.gz"
        if symbol == "SPY" or not path.exists():
            continue
        bars = load(symbol)
        if len(bars["close"]) <= RUNUP_DAYS + 1:
            continue
        liquid, found = scan(bars)
        for day, r in liquid.items():
            liquid_by_day[day].append(r)
        if found:
            for x in found:
                candidates[x["date"]].append({**x, "symbol": symbol})
            series[symbol] = {"at": {d: i for i, d in enumerate(bars["date"])}, "open": bars["open"],
                              "low": bars["low"], "close": bars["close"], "sma10": sma(bars["close"], 10)}
        if n % 500 == 0:
            print(json.dumps({"scanned": n, "of": len(symbols)}), flush=True)
    leaders_cut = {day: percentile(values, LEADER_PCT) for day, values in liquid_by_day.items() if values}
    trades, curve, still_open = simulate(days, market_ok, leaders_cut, candidates, series)
    result = report(trades, curve, spy, market_ok)
    result.update({"symbols_in_universe": len(symbols), "symbols_with_candidates": len(series),
                   "candidate_signals": sum(len(v) for v in candidates.values()), "open_at_end": len(still_open),
                   "first_day": days[0], "last_day": days[-1]})
    Path(args.output).write_text(json.dumps({**result, "trade_list": trades,
                                             "equity_curve": [[d, round(e, 2), n] for d, e, n in curve]}, indent=1) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
