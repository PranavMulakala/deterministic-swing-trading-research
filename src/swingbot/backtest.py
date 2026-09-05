from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .indicators import sma, wilder_atr, wilder_rsi
from .ledger import EventLedger
from .models import BacktestResult, Bar, Position, Signal, Trade
from .risk import RiskManager, RiskPolicy, utc_bar_timestamp
from .strategy import evaluate_entry, recovery_exit


@dataclass(frozen=True)
class Snapshot:
    bar: Bar
    sma20: float | None
    sma200: float | None
    rsi2: float | None
    atr14: float | None


def _snapshots(bars: list[Bar], config: dict[str, Any]) -> dict[date, Snapshot]:
    closes = [bar.close for bar in bars]
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    strategy = config["strategy"]
    sma20_values = sma(closes, int(strategy["recovery_sma_days"]))
    sma200_values = sma(closes, int(strategy["trend_sma_days"]))
    rsi_values = wilder_rsi(closes, int(strategy["rsi_period"]))
    atr_values = wilder_atr(highs, lows, closes, int(strategy["stop_atr_days"]))
    return {
        bar.date: Snapshot(bar, sma20_values[i], sma200_values[i], rsi_values[i], atr_values[i])
        for i, bar in enumerate(bars)
    }


class BacktestEngine:
    def __init__(
        self,
        config: dict[str, Any],
        bars_by_symbol: dict[str, list[Bar]],
        *,
        split: str,
        start_date: date,
        end_date: date,
        run_id: str,
    ):
        self.config = config
        self.split = split
        self.start_date = start_date
        self.end_date = end_date
        self.snapshots = {
            symbol: _snapshots(bars, config) for symbol, bars in bars_by_symbol.items()
        }
        self.calendar = sorted(
            {
                day
                for symbol_data in self.snapshots.values()
                for day in symbol_data
                if start_date <= day <= end_date
            }
        )
        risk_cfg = config["risk"]
        data_cfg = config["data"]
        account_cfg = config["account"]
        self.risk = RiskManager(
            RiskPolicy(
                max_planned_loss_pct=float(risk_cfg["max_planned_loss_pct"]),
                max_aggregate_open_risk_pct=float(risk_cfg["max_aggregate_open_risk_pct"]),
                daily_loss_halt_pct=float(risk_cfg["daily_loss_halt_pct"]),
                quote_max_age_seconds=int(data_cfg["quote_max_age_seconds"]),
                fractional_precision=int(account_cfg["fractional_precision"]),
            )
        )
        self.ledger = EventLedger(run_id)
        self.costs = config["costs"]

    def run(self) -> BacktestResult:
        if not self.calendar:
            raise ValueError(f"no trading dates in {self.split}")
        initial = float(self.config["account"]["initial_equity"])
        cash = initial
        positions: dict[str, Position] = {}
        pending_entries: dict[str, Signal] = {}
        pending_exits: dict[str, tuple[str, date]] = {}
        latest_price: dict[str, float] = {}
        trades: list[Trade] = []
        equity_curve: list[dict[str, object]] = []
        exposure_curve: list[dict[str, object]] = []

        for day in self.calendar:
            today = {
                symbol: symbol_data[day]
                for symbol, symbol_data in self.snapshots.items()
                if day in symbol_data
            }
            for symbol, snapshot in today.items():
                latest_price[symbol] = snapshot.bar.open
            open_equity = self._equity(cash, positions, latest_price)
            self.risk.start_day(day, open_equity)

            # Previously scheduled exits execute at this bar's open.
            for symbol in sorted(list(pending_exits)):
                if symbol not in today or symbol not in positions:
                    continue
                reason, exit_signal_date = pending_exits.pop(symbol)
                cash, trade = self._close(
                    positions, symbol, today[symbol].bar.open, day, exit_signal_date,
                    reason, cash, phase="open",
                )
                trades.append(trade)

            # Previously generated signals execute at the next available open.
            for symbol in sorted(list(pending_entries)):
                signal = pending_entries[symbol]
                if symbol not in today or day <= signal.signal_date:
                    continue
                pending_entries.pop(symbol)
                if symbol in positions:
                    self.ledger.append(day, "order_rejected", phase="open", symbol=symbol,
                                       reason="position_already_open")
                    continue
                snapshot = today[symbol]
                current_equity = self._equity(cash, positions, latest_price)
                stop_reference = snapshot.bar.open - (
                    signal.atr * float(self.config["strategy"]["stop_atr_multiple"])
                )
                if stop_reference <= 0:
                    self.ledger.append(day, "order_rejected", phase="open", symbol=symbol,
                                       reason="invalid_stop_price")
                    continue
                entry_fill = self._buy_fill(snapshot.bar.open)
                stop_fill = self._sell_fill(stop_reference)
                fee_rate = self._fee_rate()
                qty, planned_loss, risk_limit = self.risk.calculate_quantity(
                    current_equity,
                    cash,
                    entry_fill * (1.0 + fee_rate),
                    stop_fill * (1.0 - fee_rate),
                )
                entry_fee = entry_fill * qty * fee_rate
                order_id = f"ENTRY-{symbol}-{signal.signal_date.isoformat()}-{day.isoformat()}"
                timestamp = utc_bar_timestamp(day)
                decision = self.risk.authorize_entry(
                    order_id=order_id,
                    symbol=symbol,
                    equity=current_equity,
                    planned_loss=planned_loss,
                    quote_timestamp=timestamp,
                    decision_timestamp=timestamp,
                )
                if qty <= 0 or not decision.accepted:
                    self.ledger.append(
                        day, "order_rejected", phase="open", symbol=symbol,
                        client_order_id=order_id,
                        reason="zero_quantity" if qty <= 0 else decision.reason,
                        planned_loss=round(planned_loss, 8),
                    )
                    continue
                total_cost = entry_fill * qty + entry_fee
                if total_cost > cash + 1e-8:
                    # Defensive assertion: sizing is cash-capped and this must never happen.
                    raise AssertionError("risk-approved entry exceeds available cash")
                cash -= total_cost
                position = Position(
                    symbol=symbol,
                    signal_date=signal.signal_date,
                    entry_date=day,
                    entry_reference=snapshot.bar.open,
                    entry_fill=entry_fill,
                    entry_fee=entry_fee,
                    quantity=qty,
                    initial_quantity=qty,
                    stop_reference=stop_reference,
                    planned_stop_fill=stop_fill,
                    planned_loss=planned_loss,
                    risk_limit=risk_limit,
                    initial_equity=current_equity,
                    reason=signal.reason,
                    invalidation=signal.invalidation,
                )
                positions[symbol] = position
                self.ledger.append(
                    day, "order_filled", phase="open", symbol=symbol,
                    client_order_id=order_id, side="buy", quantity=qty,
                    reference_price=round(snapshot.bar.open, 8), fill_price=round(entry_fill, 8),
                    fee=round(entry_fee, 8), planned_loss=round(planned_loss, 8),
                    risk_limit=round(risk_limit, 8),
                    equity_at_entry=round(current_equity, 8),
                    aggregate_open_risk_after=round(
                        sum(self.risk.state.open_risk_by_symbol.values()), 8
                    ),
                    protective_stop_status="simulated_native_for_backtest",
                    protective_stop_price=round(stop_reference, 8),
                )
                self.ledger.append(
                    day, "position_changed", phase="open", symbol=symbol,
                    state="opened", quantity=qty,
                )

            # Intraday broker-native stop simulation. Gap-through fills at the open.
            for symbol in sorted(list(positions)):
                if symbol not in today:
                    continue
                position = positions[symbol]
                bar = today[symbol].bar
                if bar.low <= position.stop_reference:
                    reference = bar.open if bar.open <= position.stop_reference else position.stop_reference
                    cash, trade = self._close(
                        positions, symbol, reference, day, None, "protective_stop",
                        cash, phase="intraday",
                    )
                    pending_exits.pop(symbol, None)
                    trades.append(trade)

            # Close marks and signals are computed only after the complete bar.
            for symbol, snapshot in today.items():
                latest_price[symbol] = snapshot.bar.close
            for position in positions.values():
                if position.symbol in today:
                    position.holding_days += 1

            close_equity = self._equity(cash, positions, latest_price)
            gross_market_value = sum(
                position.quantity * latest_price.get(symbol, position.entry_fill)
                for symbol, position in positions.items()
            )
            equity_curve.append({"date": day.isoformat(), "equity": round(close_equity, 8)})
            exposure_curve.append(
                {
                    "date": day.isoformat(),
                    "gross_market_value": round(gross_market_value, 8),
                    "exposure_pct": round(gross_market_value / close_equity * 100, 8)
                    if close_equity > 0 else 0.0,
                    "open_positions": len(positions),
                    "aggregate_planned_risk": round(sum(self.risk.state.open_risk_by_symbol.values()), 8),
                }
            )
            self.ledger.append(
                day, "pnl_mark", equity=round(close_equity, 8), cash=round(cash, 8),
                open_positions=len(positions),
            )

            for symbol in sorted(today):
                snapshot = today[symbol]
                if symbol in positions:
                    position = positions[symbol]
                    if symbol not in pending_exits:
                        if recovery_exit(snapshot.bar.close, snapshot.sma20):
                            pending_exits[symbol] = ("recovery_target", day)
                            self.ledger.append(
                                day, "exit_signal", symbol=symbol, reason="recovery_target",
                                execution="next_available_open",
                            )
                        elif position.holding_days >= int(
                            self.config["strategy"]["time_stop_trading_days"]
                        ):
                            pending_exits[symbol] = ("time_stop", day)
                            self.ledger.append(
                                day, "exit_signal", symbol=symbol, reason="time_stop",
                                execution="next_available_open",
                            )
                    self.ledger.append(
                        day, "entry_rejected", symbol=symbol, reason="position_already_open"
                    )
                    continue
                if symbol in pending_entries:
                    self.ledger.append(
                        day, "entry_rejected", symbol=symbol, reason="entry_already_pending"
                    )
                    continue
                evaluation = evaluate_entry(
                    symbol=symbol,
                    day=day,
                    close=snapshot.bar.close,
                    sma20=snapshot.sma20,
                    sma200=snapshot.sma200,
                    rsi2=snapshot.rsi2,
                    atr14=snapshot.atr14,
                    entry_threshold=float(self.config["strategy"]["rsi_entry_below"]),
                )
                if evaluation.signal is None:
                    self.ledger.append(
                        day, "entry_rejected", symbol=symbol,
                        reason=evaluation.rejection_reason,
                    )
                else:
                    pending_entries[symbol] = evaluation.signal
                    self.ledger.append(
                        day, "entry_signal", symbol=symbol,
                        reason=evaluation.signal.reason,
                        invalidation=evaluation.signal.invalidation,
                        execution="next_available_open",
                    )

        # Deterministic end-of-sample liquidation for comparable terminal equity.
        final_day = self.calendar[-1]
        for symbol in sorted(list(positions)):
            reference = latest_price[symbol]
            cash, trade = self._close(
                positions, symbol, reference, final_day, None,
                "end_of_sample_liquidation", cash, phase="close",
            )
            trades.append(trade)
        final_equity = cash
        if equity_curve:
            equity_curve[-1]["equity"] = round(final_equity, 8)
            exposure_curve[-1]["gross_market_value"] = 0.0
            exposure_curve[-1]["exposure_pct"] = 0.0
            exposure_curve[-1]["open_positions"] = 0
            exposure_curve[-1]["aggregate_planned_risk"] = 0.0
        return BacktestResult(
            split=self.split,
            start_date=self.calendar[0],
            end_date=self.calendar[-1],
            initial_equity=initial,
            final_equity=final_equity,
            trades=trades,
            equity_curve=equity_curve,
            exposure_curve=exposure_curve,
            events=self.ledger.events,
        )

    def _close(
        self,
        positions: dict[str, Position],
        symbol: str,
        reference_price: float,
        exit_date: date,
        exit_signal_date: date | None,
        reason: str,
        cash: float,
        *,
        phase: str,
    ) -> tuple[float, Trade]:
        # In the backtest simulator, the fill is the broker confirmation. Only
        # after constructing that confirmation is local position state removed.
        position = positions[symbol]
        exit_fill = self._sell_fill(reference_price)
        exit_fee = exit_fill * position.quantity * self._fee_rate()
        proceeds = exit_fill * position.quantity - exit_fee
        cost = position.entry_fill * position.quantity + position.entry_fee
        pnl = proceeds - cost
        modeled_execution_cost = position.quantity * (
            (position.entry_fill - position.entry_reference) + (reference_price - exit_fill)
        ) + position.entry_fee + exit_fee
        cash += proceeds
        trade = Trade(
            symbol=symbol,
            signal_date=position.signal_date,
            entry_date=position.entry_date,
            exit_signal_date=exit_signal_date,
            exit_date=exit_date,
            entry_reference=position.entry_reference,
            exit_reference=reference_price,
            entry_fill=position.entry_fill,
            exit_fill=exit_fill,
            quantity=position.quantity,
            entry_fee=position.entry_fee,
            exit_fee=exit_fee,
            modeled_execution_cost=modeled_execution_cost,
            pnl=pnl,
            return_pct_on_equity=pnl / position.initial_equity * 100.0,
            planned_loss=position.planned_loss,
            planned_risk_pct=position.planned_loss / position.initial_equity * 100.0,
            risk_limit=position.risk_limit,
            holding_days=position.holding_days,
            exit_reason=reason,
            qualification=position.reason,
            invalidation=position.invalidation,
        )
        self.ledger.append(
            exit_date, "order_filled", phase=phase, symbol=symbol, side="sell",
            quantity=position.quantity, reference_price=round(reference_price, 8),
            fill_price=round(exit_fill, 8), fee=round(exit_fee, 8), reason=reason,
        )
        del positions[symbol]
        self.risk.close_position(symbol, pnl)
        self.ledger.append(
            exit_date, "position_changed", phase=phase, symbol=symbol,
            state="closed", quantity=0.0, realized_pnl=round(pnl, 8), reason=reason,
        )
        return cash, trade

    def _buy_fill(self, reference: float) -> float:
        return reference * (1.0 + self._execution_bps() / 10000.0)

    def _sell_fill(self, reference: float) -> float:
        return reference * (1.0 - self._execution_bps() / 10000.0)

    def _execution_bps(self) -> float:
        return float(self.costs["half_spread_bps"]) + float(self.costs["slippage_bps"])

    def _fee_rate(self) -> float:
        return float(self.costs["fee_bps_per_side"]) / 10000.0

    @staticmethod
    def _equity(cash: float, positions: dict[str, Position], prices: dict[str, float]) -> float:
        return cash + sum(
            position.quantity * prices.get(symbol, position.entry_fill)
            for symbol, position in positions.items()
        )


def metrics(result: BacktestResult) -> dict[str, object]:
    equities = [float(row["equity"]) for row in result.equity_curve]
    peak = -math.inf
    max_drawdown = 0.0
    for equity in equities:
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    wins = sum(1 for trade in result.trades if trade.pnl > 0)
    winning_pnl = [trade.pnl for trade in result.trades if trade.pnl > 0]
    losing_pnl = [trade.pnl for trade in result.trades if trade.pnl < 0]
    gross_profit = sum(winning_pnl)
    gross_loss = -sum(losing_pnl)
    days = max(1, (result.end_date - result.start_date).days)
    years = days / 365.2425
    cagr = (result.final_equity / result.initial_equity) ** (1 / years) - 1 if result.final_equity > 0 else -1.0
    avg_exposure = (
        sum(float(row["exposure_pct"]) for row in result.exposure_curve) / len(result.exposure_curve)
        if result.exposure_curve else 0.0
    )
    return {
        "split": result.split,
        "start_date": result.start_date.isoformat(),
        "end_date": result.end_date.isoformat(),
        "initial_equity": round(result.initial_equity, 8),
        "final_equity": round(result.final_equity, 8),
        "total_return_pct": round((result.final_equity / result.initial_equity - 1) * 100, 8),
        "cagr_pct": round(cagr * 100, 8),
        "max_drawdown_pct": round(max_drawdown * 100, 8),
        "trade_count": len(result.trades),
        "win_rate_pct": round(wins / len(result.trades) * 100, 8) if result.trades else 0.0,
        "average_win": round(sum(winning_pnl) / len(winning_pnl), 8) if winning_pnl else 0.0,
        "average_loss": round(sum(losing_pnl) / len(losing_pnl), 8) if losing_pnl else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 8) if gross_loss else None,
        "average_trade_pnl": round(sum(t.pnl for t in result.trades) / len(result.trades), 8)
        if result.trades else 0.0,
        "total_modeled_execution_cost": round(
            sum(t.modeled_execution_cost for t in result.trades), 8
        ),
        "average_exposure_pct": round(avg_exposure, 8),
        "max_planned_risk_pct": round(max((t.planned_risk_pct for t in result.trades), default=0.0), 8),
    }


def write_result(result: BacktestResult, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / f"trades_{result.split}.csv", [asdict(t) for t in result.trades])
    _write_csv(output_dir / f"equity_{result.split}.csv", result.equity_curve)
    _write_csv(output_dir / f"exposure_{result.split}.csv", result.exposure_curve)
    EventLedgerWriter(result.events).write(output_dir / f"events_{result.split}.jsonl")
    summary = metrics(result)
    (output_dir / f"metrics_{result.split}.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


class EventLedgerWriter:
    def __init__(self, events: list[dict[str, object]]):
        self.events = events

    def write(self, path: Path) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for event in self.events:
                handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def _csv_value(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.8f}"
    return value


def output_hashes(output_dir: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "artifact_hashes.json"
    }
