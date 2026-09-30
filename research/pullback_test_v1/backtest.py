"""Backtest of the pre-declared course pullback rules (output/PULLBACK_TEST_PLAN_20260929.md). Research only.

  PYTHONPATH=src:. .venv/bin/python -m research.pullback_test_v1.backtest

Reads the daily bars already saved by research/breakout_test_v1/fetch.py and writes output/pullback-test-results.json.
The short side reuses the long code on mirrored prices (high <-> -low, close -> -close), so every rule is written once.
Buffers and slippage are added on absolute price, which keeps them pointing the right way in both mirrors.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

from research.breakout_test_v1.backtest import DATA, HALVES, load, sma

START_EQUITY, SLIP, BUFFER, RISK, MAX_WEIGHT, MAX_POSITIONS = 100_000.0, 0.001, 0.001, 0.01, 0.25, 10
MIN_PRICE, MIN_DOLLAR_VOLUME, LOOKBACK, MIN_PULLBACK_DAYS, MAX_HOLD = 10.0, 20_000_000.0, 20, 3, 60


def mirror(bars):
    """Short side: a falling real price is a rising mirrored price."""
    return {"date": bars["date"], "open": [-x for x in bars["open"]], "high": [-x for x in bars["low"]],
            "low": [-x for x in bars["high"]], "close": [-x for x in bars["close"]]}


def up(x, frac):
    return x + frac * abs(x)


def down(x, frac):
    return x - frac * abs(x)


def scan(prices, real):
    """Rules 1-6 on (possibly mirrored) prices; liquidity is always judged on real prices."""
    o, h, l, c = prices["open"], prices["high"], prices["low"], prices["close"]
    dollar = sma([a * b for a, b in zip(real["close"], real["volume"])], 20)
    s50, s200 = sma(c, 50), sma(c, 200)
    last_turn, signals = [-1] * len(c), []
    for k in range(1, len(c)):
        last_turn[k] = k if c[k] > h[k - 1] else last_turn[k - 1]
    for t in range(200, len(c)):
        if real["close"][t] < MIN_PRICE or dollar[t] is None or dollar[t] < MIN_DOLLAR_VOLUME:
            continue
        if not (s50[t] > s200[t] and s50[t] > s50[t - 10]):
            continue
        if not c[t] > h[t - 1]:
            continue
        window = h[t - LOOKBACK:t]
        peak = t - LOOKBACK + max(i for i in range(len(window)) if window[i] == max(window))
        if t - peak < MIN_PULLBACK_DAYS or last_turn[t - 1] > peak:
            continue
        entry = up(h[t], BUFFER)
        stop = down(min(l[peak + 1:t + 1]), BUFFER)
        target = down(max(c[t - LOOKBACK:t]), BUFFER)
        if not (target > entry and target - entry >= entry - stop):
            continue
        signals.append({"date": prices["date"][t], "peak_date": prices["date"][peak], "entry": entry, "stop": stop,
                        "target": target, "dollar_volume": dollar[t]})
    return signals


def simulate(days, signals, series, side="long"):
    """Rules 7-12. `series` holds the same (possibly mirrored) prices the signals came from."""
    index = {d: i for i, d in enumerate(days)}
    sign = 1 if side == "long" else -1
    realized, positions, pending, trades, curve, last_exit = 0.0, {}, {}, [], [], {}

    def bar(symbol, day):
        s = series[symbol]
        i = s["at"].get(day)
        return None if i is None else (s["open"][i], s["high"][i], s["low"][i], s["close"][i])

    def close_out(symbol, price, day, reason):
        nonlocal realized
        p = positions.pop(symbol)
        exit_px = down(price, SLIP)
        pnl = p["shares"] * (exit_px - p["fill"])
        realized += pnl
        last_exit[symbol] = day
        trades.append({"symbol": symbol, "side": side, "signal_date": p["signal_date"], "entry_date": p["entry_date"],
                       "exit_date": day, "shares": p["shares"], "entry": round(sign * p["fill"], 4),
                       "stop": round(sign * p["stop"], 4), "target": round(sign * p["target"], 4),
                       "exit": round(sign * exit_px, 4), "reason": reason, "pnl": pnl,
                       "return_pct": pnl / (p["shares"] * abs(p["fill"])) * 100,
                       "r_multiple": pnl / (p["shares"] * p["planned_risk"]),
                       "days": index[day] - p["entry_index"]})

    for day in days:
        marks = {}
        for symbol, order in list(pending.items()):
            del pending[symbol]
            b = bar(symbol, day)
            if b is None:
                continue
            opening, high, low, close = b
            if opening >= order["entry"]:
                price = opening
            elif high >= order["entry"]:
                price = order["entry"]
            else:
                continue
            positions[symbol] = {**order, "fill": up(price, SLIP), "entry_date": day, "entry_index": index[day]}
            if low <= order["stop"]:
                close_out(symbol, order["stop"], day, "stop")
            elif high >= order["target"]:
                close_out(symbol, order["target"], day, "target")
            else:
                marks[symbol] = close
        for symbol, p in list(positions.items()):
            if p["entry_date"] == day:
                continue
            b = bar(symbol, day)
            if b is None:
                continue
            opening, high, low, close = b
            if opening <= p["stop"]:
                close_out(symbol, opening, day, "stop_gap")
            elif opening >= p["target"]:
                close_out(symbol, opening, day, "target_gap")
            elif low <= p["stop"]:
                close_out(symbol, p["stop"], day, "stop")
            elif high >= p["target"]:
                close_out(symbol, p["target"], day, "target")
            elif index[day] - p["entry_index"] >= MAX_HOLD:
                close_out(symbol, close, day, "time")
            else:
                marks[symbol] = close
        for symbol, p in positions.items():
            p["mark"] = marks.get(symbol, p.get("mark", p["fill"]))
        equity = START_EQUITY + realized + sum(p["shares"] * (p["mark"] - p["fill"]) for p in positions.values())
        in_use = sum(p["shares"] * abs(p["fill"]) for p in positions.values())
        free = START_EQUITY + realized - in_use
        todays = sorted((x for x in signals.get(day, []) if x["symbol"] not in positions
                         and x["peak_date"] > last_exit.get(x["symbol"], "")), key=lambda x: -x["dollar_volume"])
        for x in todays:
            if len(positions) + len(pending) >= MAX_POSITIONS:
                break
            risk = x["entry"] - x["stop"]
            size = abs(x["entry"])
            shares = math.floor(min(RISK * equity / risk, MAX_WEIGHT * equity / size, max(free, 0) / size))
            if shares < 1:
                continue
            free -= shares * size
            pending[x["symbol"]] = {"shares": shares, "entry": x["entry"], "stop": x["stop"], "target": x["target"],
                                    "planned_risk": risk, "signal_date": day}
        curve.append((day, equity, len(positions)))
    return trades, curve, positions


def summarize(trades, curve, spy):
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gain, loss = sum(t["pnl"] for t in wins), -sum(t["pnl"] for t in losses)
    peak, worst = START_EQUITY, 0.0
    for _, equity, _ in curve:
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1)
    value = {d: e for d, e, _ in curve}
    days = [d for d, _, _ in curve]

    def change(a, b):
        inside = [d for d in days if a <= d <= b]
        start = value[max([d for d in days if d < inside[0]], default=inside[0])]
        return value[inside[-1]] / start - 1

    years = len(days) / 252
    by_year = defaultdict(float)
    for t in trades:
        by_year[t["exit_date"][:4]] += t["pnl"]
    avg_win = gain / len(wins) if wins else 0.0
    avg_loss = loss / len(losses) if losses else 0.0
    p = len(wins) / len(trades) if trades else 0.0
    final = curve[-1][1]
    spy_close = dict(zip(spy["date"], spy["close"]))
    halves = {name: round(change(a, b) * 100, 1) for name, a, b in HALVES}
    result = {
        "trades": len(trades), "trades_per_year": round(len(trades) / years, 1),
        "first_trade": min((t["entry_date"] for t in trades), default=None),
        "win_rate_pct": round(100 * p, 1),
        "avg_win_usd": round(avg_win), "avg_loss_usd": round(avg_loss),
        "avg_win_pct": round(sum(t["return_pct"] for t in wins) / max(len(wins), 1), 2),
        "avg_loss_pct": round(sum(t["return_pct"] for t in losses) / max(len(losses), 1), 2),
        "avg_r_multiple": round(sum(t["r_multiple"] for t in trades) / max(len(trades), 1), 3),
        "video_expectancy": round((1 + avg_win / avg_loss) * p - 1, 3) if avg_loss else None,
        "avg_hold_days": round(sum(t["days"] for t in trades) / max(len(trades), 1), 1),
        "exit_reasons": dict(Counter(t["reason"] for t in trades)),
        "profit_factor": round(gain / loss, 2) if loss else None,
        "final_equity": round(final), "total_return_pct": round((final / START_EQUITY - 1) * 100, 1),
        "cagr_pct": round(((final / START_EQUITY) ** (1 / years) - 1) * 100, 1),
        "max_drawdown_pct": round(worst * 100, 1), "halves_return_pct": halves,
        "avg_positions_open": round(sum(n for _, _, n in curve) / len(curve), 2),
        "pnl_by_exit_year": {y: round(v) for y, v in sorted(by_year.items())},
        "best_trade": max(trades, key=lambda t: t["return_pct"], default=None),
        "worst_trade": min(trades, key=lambda t: t["return_pct"], default=None),
        "spy_buy_hold_return_pct": round((spy_close[days[-1]] / spy_close[days[0]] - 1) * 100, 1),
    }
    checks = {"1_profit_factor_at_least_1.3": (result["profit_factor"] or 0) >= 1.3,
              "2_profitable_in_both_halves": all(v > 0 for v in halves.values()),
              "3_max_drawdown_at_most_25pct": result["max_drawdown_pct"] >= -25.0}
    result["pre_declared_checks"] = checks
    result["works"] = all(checks.values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/pullback-test-results.json")
    args = parser.parse_args()
    symbols = json.loads((DATA / "universe.json").read_text())
    spy = load("SPY")
    days = list(spy["date"])
    signals = {"long": defaultdict(list), "short": defaultdict(list)}
    series = {"long": {}, "short": {}}
    for n, symbol in enumerate(symbols, 1):
        path = DATA / f"{symbol}.csv.gz"
        if symbol == "SPY" or not path.exists():
            continue
        real = load(symbol)
        if len(real["close"]) <= 210:
            continue
        for side, prices in (("long", real), ("short", mirror(real))):
            found = scan(prices, real)
            if found:
                for x in found:
                    signals[side][x["date"]].append({**x, "symbol": symbol})
                series[side][symbol] = {"at": {d: i for i, d in enumerate(prices["date"])}, "open": prices["open"],
                                        "high": prices["high"], "low": prices["low"], "close": prices["close"]}
        if n % 500 == 0:
            print(json.dumps({"scanned": n, "of": len(symbols)}), flush=True)
    output, headline = {}, {}
    for side in ("long", "short"):
        trades, curve, still_open = simulate(days, signals[side], series[side], side)
        result = summarize(trades, curve, spy)
        result.update({"signals": sum(len(v) for v in signals[side].values()), "open_at_end": len(still_open)})
        headline[side] = {k: v for k, v in result.items() if k not in ("best_trade", "worst_trade")}
        output[side] = {**result, "trade_list": trades, "equity_curve": [[d, round(e, 2), n] for d, e, n in curve]}
    output["verdict_counts_long_side_only"] = output["long"]["works"]
    Path(args.output).write_text(json.dumps(output, indent=1) + "\n")
    print(json.dumps(headline, indent=2))


if __name__ == "__main__":
    main()
