from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math

from .models import Signal


@dataclass(frozen=True)
class StrategyEvaluation:
    signal: Signal | None
    rejection_reason: str | None


def evaluate_entry(
    *,
    symbol: str,
    day: date,
    close: float,
    sma20: float | None,
    sma200: float | None,
    rsi2: float | None,
    atr14: float | None,
    entry_threshold: float,
) -> StrategyEvaluation:
    if None in (sma20, sma200, rsi2, atr14):
        return StrategyEvaluation(None, "insufficient_history")
    assert sma20 is not None and sma200 is not None and rsi2 is not None and atr14 is not None
    if not all(
        math.isfinite(value)
        for value in (close, sma20, sma200, rsi2, atr14, entry_threshold)
    ):
        return StrategyEvaluation(None, "invalid_numeric_input")
    if close <= 0 or sma20 <= 0 or sma200 <= 0 or atr14 <= 0:
        return StrategyEvaluation(None, "invalid_numeric_input")
    if close <= sma200:
        return StrategyEvaluation(None, "trend_filter_failed")
    if rsi2 >= entry_threshold:
        return StrategyEvaluation(None, "pullback_filter_failed")
    reason = (
        f"close {close:.4f} > SMA200 {sma200:.4f}; "
        f"RSI2 {rsi2:.4f} < {entry_threshold:.4f}"
    )
    invalidation = (
        "first of broker-native protective stop, completed close at/above SMA20 "
        "followed by next-open exit, or 20-session time stop"
    )
    return StrategyEvaluation(
        Signal(symbol, day, atr14, close, sma20, sma200, rsi2, reason, invalidation),
        None,
    )


def recovery_exit(close: float, sma20: float | None) -> bool:
    return (
        sma20 is not None
        and math.isfinite(close)
        and math.isfinite(sma20)
        and close > 0
        and sma20 > 0
        and close >= sma20
    )
