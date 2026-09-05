from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from .backtest import _write_csv
from .indicators import sma
from .models import Bar


def _execution_rate(config: dict[str, Any]) -> float:
    costs = config["costs"]
    bps = float(costs["half_spread_bps"]) + float(costs["slippage_bps"])
    return bps / 10000.0


def _fee_rate(config: dict[str, Any]) -> float:
    return float(config["costs"]["fee_bps_per_side"]) / 10000.0


def _summary(name: str, curve: list[dict[str, object]], initial: float) -> dict[str, object]:
    start = date.fromisoformat(str(curve[0]["date"]))
    end = date.fromisoformat(str(curve[-1]["date"]))
    final = float(curve[-1]["equity"])
    peak = -math.inf
    drawdown = 0.0
    for row in curve:
        equity = float(row["equity"])
        peak = max(peak, equity)
        drawdown = max(drawdown, (peak - equity) / peak if peak > 0 else 0.0)
    years = max(1, (end - start).days) / 365.2425
    cagr = (final / initial) ** (1 / years) - 1 if final > 0 else -1.0
    return {
        "benchmark": name,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "initial_equity": round(initial, 8),
        "final_equity": round(final, 8),
        "total_return_pct": round((final / initial - 1) * 100, 8),
        "cagr_pct": round(cagr * 100, 8),
        "max_drawdown_pct": round(drawdown * 100, 8),
    }


def buy_and_hold_spy(
    bars: list[Bar], config: dict[str, Any], start: date, end: date
) -> tuple[list[dict[str, object]], dict[str, object]]:
    selected = [bar for bar in bars if start <= bar.date <= end]
    if not selected:
        raise ValueError("SPY benchmark has no bars in requested window")
    initial = float(config["account"]["initial_equity"])
    execution = _execution_rate(config)
    fee = _fee_rate(config)
    entry = selected[0].open * (1 + execution)
    quantity = initial / (entry * (1 + fee))
    entry_fee = quantity * entry * fee
    curve = [
        {"date": bar.date.isoformat(), "equity": round(quantity * bar.close, 8)}
        for bar in selected
    ]
    exit_fill = selected[-1].close * (1 - execution)
    exit_fee = quantity * exit_fill * fee
    curve[-1]["equity"] = round(quantity * exit_fill * (1 - fee), 8)
    summary = _summary("spy_buy_and_hold", curve, initial)
    summary["total_modeled_execution_cost"] = round(
        quantity * ((entry - selected[0].open) + (selected[-1].close - exit_fill))
        + entry_fee + exit_fee,
        8,
    )
    return curve, summary


def monthly_momentum(
    bars_by_symbol: dict[str, list[Bar]],
    config: dict[str, Any],
    start: date,
    end: date,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    settings = config["momentum_benchmark"]
    lookback = int(settings["lookback_trading_days"])
    trend_days = int(settings["trend_sma_days"])
    top_n = int(settings["top_n"])
    indexed: dict[str, dict[date, tuple[Bar, float | None, float | None]]] = {}
    for symbol, bars in bars_by_symbol.items():
        closes = [bar.close for bar in bars]
        trends = sma(closes, trend_days)
        symbol_index: dict[date, tuple[Bar, float | None, float | None]] = {}
        for i, bar in enumerate(bars):
            momentum = closes[i] / closes[i - lookback] - 1 if i >= lookback else None
            symbol_index[bar.date] = (bar, trends[i], momentum)
        indexed[symbol] = symbol_index

    calendar = sorted(
        {day for rows in indexed.values() for day in rows if start <= day <= end}
    )
    if not calendar:
        raise ValueError("momentum benchmark has no bars in requested window")
    initial = float(config["account"]["initial_equity"])
    cash = initial
    holdings: dict[str, float] = {}
    latest: dict[str, float] = {}
    pending: list[str] | None = None
    execution = _execution_rate(config)
    fee = _fee_rate(config)
    curve: list[dict[str, object]] = []
    rebalance_count = 0
    modeled_execution_cost = 0.0

    for i, day in enumerate(calendar):
        today = {symbol: rows[day] for symbol, rows in indexed.items() if day in rows}
        for symbol, (bar, _, _) in today.items():
            latest[symbol] = bar.open
        if pending is not None:
            for symbol in sorted(list(holdings)):
                if symbol not in today:
                    continue
                reference = today[symbol][0].open
                fill = reference * (1 - execution)
                quantity = holdings.pop(symbol)
                exit_fee = quantity * fill * fee
                modeled_execution_cost += quantity * (reference - fill) + exit_fee
                cash += quantity * fill * (1 - fee)
            selected = [symbol for symbol in pending if symbol in today]
            if selected:
                allocation = cash / len(selected)
                for symbol in selected:
                    reference = today[symbol][0].open
                    fill = reference * (1 + execution)
                    quantity = allocation / (fill * (1 + fee))
                    entry_fee = quantity * fill * fee
                    modeled_execution_cost += quantity * (fill - reference) + entry_fee
                    cash -= quantity * fill * (1 + fee)
                    holdings[symbol] = quantity
            pending = None
            rebalance_count += 1

        for symbol, (bar, _, _) in today.items():
            latest[symbol] = bar.close
        equity = cash + sum(qty * latest[symbol] for symbol, qty in holdings.items())
        curve.append({"date": day.isoformat(), "equity": round(equity, 8)})

        is_month_end = i == len(calendar) - 1 or calendar[i + 1].month != day.month
        if is_month_end and i < len(calendar) - 1:
            candidates: list[tuple[float, str]] = []
            for symbol, (bar, trend, momentum) in today.items():
                if trend is not None and momentum is not None and bar.close > trend and momentum > 0:
                    candidates.append((momentum, symbol))
            candidates.sort(key=lambda item: (-item[0], item[1]))
            pending = [symbol for _, symbol in candidates[:top_n]]

    final_day = calendar[-1]
    for symbol in sorted(list(holdings)):
        if final_day not in indexed[symbol]:
            continue
        reference = indexed[symbol][final_day][0].close
        fill = reference * (1 - execution)
        quantity = holdings.pop(symbol)
        exit_fee = quantity * fill * fee
        modeled_execution_cost += quantity * (reference - fill) + exit_fee
        cash += quantity * fill * (1 - fee)
    curve[-1]["equity"] = round(cash, 8)
    summary = _summary("monthly_top3_126d_momentum", curve, initial)
    summary["rebalance_count"] = rebalance_count
    summary["total_modeled_execution_cost"] = round(modeled_execution_cost, 8)
    return curve, summary


def write_benchmarks(
    bars_by_symbol: dict[str, list[Bar]],
    config: dict[str, Any],
    start: date,
    end: date,
    output_dir: Path,
    split: str,
) -> list[dict[str, object]]:
    spy_curve, spy_metrics = buy_and_hold_spy(bars_by_symbol["SPY"], config, start, end)
    momentum_curve, momentum_metrics = monthly_momentum(bars_by_symbol, config, start, end)
    zero_cost_config = deepcopy(config)
    for cost_name in ("half_spread_bps", "slippage_bps", "fee_bps_per_side"):
        zero_cost_config["costs"][cost_name] = 0.0
    _, zero_cost_spy = buy_and_hold_spy(bars_by_symbol["SPY"], zero_cost_config, start, end)
    _, zero_cost_momentum = monthly_momentum(bars_by_symbol, zero_cost_config, start, end)
    for measured, zero_cost in (
        (spy_metrics, zero_cost_spy), (momentum_metrics, zero_cost_momentum)
    ):
        measured["zero_cost_total_return_pct"] = zero_cost["total_return_pct"]
        measured["modeled_cost_drag_pct_points"] = round(
            float(zero_cost["total_return_pct"]) - float(measured["total_return_pct"]), 8
        )
    _write_csv(output_dir / f"benchmark_spy_{split}.csv", spy_curve)
    _write_csv(output_dir / f"benchmark_momentum_{split}.csv", momentum_curve)
    summaries = [spy_metrics, momentum_metrics]
    (output_dir / f"benchmarks_{split}.json").write_text(
        json.dumps(summaries, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summaries
