from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from .indicators import sma, wilder_atr, wilder_rsi
from .models import Bar
from .paper_models import LiveSignal
from .strategy import evaluate_entry, recovery_exit


@dataclass(frozen=True)
class LiveSignalDecision:
    symbol: str
    bar_date: date | None
    signal: LiveSignal | None
    rejection_reason: str | None


def latest_entry_decision(
    bars: list[Bar], *, session_date: date, strategy_config: dict[str, Any]
) -> LiveSignalDecision:
    """Evaluate only the latest daily bar completed before this trading session."""
    completed = [bar for bar in bars if bar.date < session_date]
    symbol = bars[0].symbol if bars else ""
    if not completed:
        return LiveSignalDecision(symbol, None, None, "no_completed_daily_bar")
    closes = [bar.close for bar in completed]
    highs = [bar.high for bar in completed]
    lows = [bar.low for bar in completed]
    strategy = strategy_config["strategy"]
    sma20 = sma(closes, int(strategy["recovery_sma_days"]))[-1]
    sma200 = sma(closes, int(strategy["trend_sma_days"]))[-1]
    rsi2 = wilder_rsi(closes, int(strategy["rsi_period"]))[-1]
    atr14 = wilder_atr(highs, lows, closes, int(strategy["stop_atr_days"]))[-1]
    latest = completed[-1]
    evaluation = evaluate_entry(
        symbol=latest.symbol,
        day=latest.date,
        close=latest.close,
        sma20=sma20,
        sma200=sma200,
        rsi2=rsi2,
        atr14=atr14,
        entry_threshold=float(strategy["rsi_entry_below"]),
    )
    if evaluation.signal is None:
        return LiveSignalDecision(
            latest.symbol, latest.date, None, evaluation.rejection_reason
        )
    signal = evaluation.signal
    return LiveSignalDecision(
        latest.symbol,
        latest.date,
        LiveSignal(
            symbol=signal.symbol,
            signal_date=signal.signal_date,
            close=Decimal(str(signal.close)),
            sma20=Decimal(str(signal.sma20)),
            sma200=Decimal(str(signal.sma200)),
            rsi2=Decimal(str(signal.rsi2)),
            atr14=Decimal(str(signal.atr)),
            reason=signal.reason,
            invalidation=signal.invalidation,
        ),
        None,
    )


def latest_exit_reason(
    bars: list[Bar],
    *,
    session_date: date,
    entry_date: date,
    strategy_config: dict[str, Any],
) -> str | None:
    completed = [bar for bar in bars if bar.date < session_date]
    if not completed:
        return None
    closes = [bar.close for bar in completed]
    period = int(strategy_config["strategy"]["recovery_sma_days"])
    latest_sma20 = sma(closes, period)[-1]
    if recovery_exit(completed[-1].close, latest_sma20):
        return "recovery_target"
    held_sessions = sum(entry_date <= bar.date <= completed[-1].date for bar in completed)
    if held_sessions >= int(strategy_config["strategy"]["time_stop_trading_days"]):
        return "time_stop"
    return None
