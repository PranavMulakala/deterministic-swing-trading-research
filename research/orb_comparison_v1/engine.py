"""Offline Decimal-accounted frozen ORB replay. No broker or network imports."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR
import json
from pathlib import Path
from statistics import median

from . import verify

D = lambda x: Decimal(str(x))
ZERO = Decimal(0)


def at(day, hm):
    return datetime.fromisoformat(f"{day}T{hm}").replace(tzinfo=verify.NY)


def encode(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def load(folder, root=None):
    folder = Path(folder)
    root = Path(root) if root else Path(__file__).resolve().parent
    freeze = json.loads((root / "FREEZE.json").read_text())
    for name, checksum in freeze["files"].items():
        if verify.sha(root / name) != checksum:
            raise ValueError("Frozen implementation or protocol changed")
    if verify.sha(folder / "manifest.json") != freeze["data_manifest_sha256"]:
        raise ValueError("Dataset not the frozen snapshot")
    report = verify.verify(folder)
    spec = json.loads((root / "spec.json").read_text())
    sessions = verify.calendar_sessions(json.loads((folder / "calendar.json").read_text()))
    bars = {}
    for symbol, step in verify.JOBS:
        payload = json.loads((folder / f"{symbol}_{step}Min.json").read_text())
        bars[symbol, step], _ = verify.parse_bars(payload, symbol, step, sessions)
    return spec, sessions, bars, report


def action_dates(payload, symbols):
    q = payload.get("query", {})
    if payload.get("complete") is not True or set(q.get("symbols", "").split(",")) != set(symbols):
        raise ValueError("Unknown corporate action coverage")
    if q.get("start", "9999") > "2025-11-01" or q.get("end", "0000") < "2026-09-04":
        raise ValueError("Corporate action interval incomplete")
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages or pages[-1].get("next_page_token") is not None:
        raise ValueError("Corporate action pagination incomplete")
    assets = payload.get("assets_current_not_point_in_time", {})
    for symbol in symbols:
        a = assets.get(symbol, {})
        if a.get("symbol") != symbol or a.get("class") != "us_equity" or a.get("exchange") not in ("NYSE", "NASDAQ", "AMEX"):
            raise ValueError("Instrument identity unresolved")
    dates = {s: set() for s in symbols}
    for page in pages:
        actions = page.get("corporate_actions")
        if not isinstance(actions, dict):
            raise ValueError("Invalid corporate action data")
        for kind, rows in actions.items():
            if not isinstance(rows, list):
                raise ValueError("Invalid action rows")
            for row in rows:
                if kind == "cash_dividends":
                    continue  # Raw intraday prices; no overnight holding.
                # Fail closed on unknown effective dates or symbol schemas. This
                # handles observed simple cases, not every provider action type.
                symbol = row.get("symbol")
                effective = row.get("ex_date") or row.get("effective_date")
                if symbol not in dates or not isinstance(effective, str):
                    raise ValueError("Action requires explicit reconciliation")
                datetime.strptime(effective, "%Y-%m-%d")
                dates[symbol].add(effective)
    return dates


def full(rows, start, end, step=5):
    return all(start + timedelta(minutes=m) in rows for m in range(0, int((end-start).total_seconds()/60), step))


def daily(rows):
    values = [rows[t] for t in sorted(rows)]
    return {"high": max(D(r["h"]) for r in values), "low": min(D(r["l"]) for r in values),
            "close": D(values[-1]["c"]), "dollar_volume": sum((D(r["v"])*D(r["vw"]) for r in values), ZERO)}


def features(symbol, index, days, sessions, bars, actions, spec):
    day = days[index]
    start, end = sessions[day]
    out = {"symbol": symbol, "day": day, "status": "eligible", "reasons": []}
    cfg = spec["eligibility"]
    lookback = cfg["dollar_volume_sessions"]
    previous = days[max(0, index-lookback):index]
    if end.strftime("%H:%M") != "16:00":
        out["reasons"].append("early_close")
    if len(previous) != lookback or any(not full(bars[symbol, 5][d], *sessions[d]) for d in previous):
        out["reasons"].append("incomplete_lagged_inputs")
    if previous and any(previous[0] <= d <= day for d in actions[symbol]):
        out["reasons"].append("corporate_action_lookback")
    opening = bars[symbol, 5][day].get(start)
    if opening is None:
        out["reasons"].append("missing_opening_range")
    if out["reasons"]:
        out["status"] = "ineligible"
        return out
    history = [daily(bars[symbol, 5][d]) for d in previous]
    close = history[-1]["close"]
    dollar_volume = median(r["dollar_volume"] for r in history)
    n = cfg["atr_sessions"]
    trs = [max(history[i]["high"]-history[i]["low"], abs(history[i]["high"]-history[i-1]["close"]),
               abs(history[i]["low"]-history[i-1]["close"])) for i in range(len(history)-n, len(history))]
    atr = sum(trs, ZERO)/n
    opening_volumes = [D(bars[symbol, 5][d][sessions[d][0]]["v"]) for d in previous[-cfg["rvol_sessions"]:]]
    rvol = D(opening["v"])/(sum(opening_volumes, ZERO)/len(opening_volumes))
    out.update(prior_close=close, dollar_volume=dollar_volume, atr=atr, atr_fraction=atr/close, rvol=rvol,
               high=D(opening["h"]), low=D(opening["l"]), selection_time=start+timedelta(minutes=5),
               gap_fraction=D(opening["o"])/close-1, news="unknown_not_used")
    if close < D(cfg["min_prior_close"]): out["reasons"].append("price_floor")
    if dollar_volume < D(cfg["min_median_dollar_volume"]): out["reasons"].append("dollar_volume_floor")
    if atr/close < D(cfg["min_atr_fraction"]): out["reasons"].append("atr_floor")
    if out["high"] <= out["low"]: out["reasons"].append("invalid_opening_range")
    if out["reasons"]: out["status"] = "ineligible"
    return out


def pattern(feature, rows, spec):
    day, high = feature["day"], feature["high"]
    stop = (high+feature["low"])/2-D("0.01")
    stamp = at(day, spec["selection"]["range_end_exclusive"])
    deadline = at(day, spec["pattern"]["last_confirmation_close"])
    breakout = None
    later = 0
    while stamp+timedelta(minutes=5) <= deadline:
        row = rows.get(stamp)
        if row is None:
            return {"status": "unknown_pattern_gap", "time": stamp}
        if breakout is None:
            if D(row["c"]) > high:
                breakout = stamp
        else:
            later += 1
            if D(row["l"]) <= stop:
                return {"status": "retest_invalidated"}
            if D(row["o"]) > high and D(row["l"]) <= high and D(row["c"]) > high:
                return {"status": "signal", "time": stamp+timedelta(minutes=5), "stop": stop,
                        "confirmation_close": D(row["c"]), "breakout_time": breakout+timedelta(minutes=5)}
            if later == spec["pattern"]["retest_max_later_bars"]:
                return {"status": "retest_expired"}
        stamp += timedelta(minutes=5)
    return {"status": "no_breakout" if breakout is None else "no_retest_before_deadline"}


def prepare(spec, sessions, bars, actions):
    days = list(sessions)
    prepared = {}
    for index, day in enumerate(days):
        if not spec["evaluation_start"] <= day <= spec["evaluation_end"]:
            continue
        prepared[day] = {}
        for symbol in spec["symbols"]:
            f = features(symbol, index, days, sessions, bars, actions, spec)
            if f["status"] == "eligible":
                f["pattern"] = pattern(f, bars[symbol, 5][day], spec)
            prepared[day][symbol] = f
    return prepared


@dataclass
class Portfolio:
    settled: Decimal
    unsettled: Decimal = ZERO
    positions: dict = field(default_factory=dict)
    trades: list = field(default_factory=list)
    events: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)
    deployed_minutes: Decimal = ZERO
    position_minutes: int = 0
    elapsed_minutes: int = 0
    realized_today: Decimal = ZERO
    halted: bool = False
    halt_count: int = 0

    def equity(self):
        return self.settled+self.unsettled+sum((p["mark"]*p["qty"] for p in self.positions.values()), ZERO)

    def settle(self, stamp):
        if self.unsettled:
            self.events.append({"type": "settle", "time": stamp, "amount": self.unsettled})
        self.settled += self.unsettled
        self.unsettled = ZERO
        self.realized_today = ZERO
        self.halted = False

    def close(self, symbol, reference, reason, stamp, slip, fee):
        p = self.positions.pop(symbol)
        price = reference*(1-slip)
        exit_fee = p["qty"]*price*fee
        proceeds = p["qty"]*price-exit_fee
        pnl = proceeds-p["cost"]
        self.unsettled += proceeds
        self.realized_today += pnl
        self.trades.append({**p, "exit_time": stamp, "exit_price": price, "exit_fee": exit_fee, "pnl": pnl, "reason": reason})
        self.events.append({"type": "exit", "symbol": symbol, "time": stamp, "qty": p["qty"],
                            "price": price, "fee": exit_fee, "proceeds": proceeds, "reason": reason})


def open_trade(port, feature, signal, row, stamp, spec, slip, fee, start_equity):
    cfg, proxy = spec["portfolio"], spec["bar_proxy"]
    if port.halted or port.realized_today <= -start_equity*D(cfg["daily_realized_loss_halt_fraction"]):
        if not port.halted: port.halt_count += 1
        port.halted = True
        return "daily_loss_halt"
    if len(port.positions) >= cfg["max_positions"]: return "position_capacity"
    if row is None: return "missing_entry_minute"
    raw_open = D(row["o"])
    stop = signal["stop"]
    entry = raw_open*(1+slip)
    if raw_open <= stop or stop <= 0: return "invalid_entry_geometry"
    if entry > signal["confirmation_close"]*(1+D(spec["pattern"]["entry_limit_fraction_above_confirmation_close"])):
        return "entry_limit_exceeded"
    modeled_cost = entry*2*(slip+fee)
    if modeled_cost > D(proxy["max_modeled_round_trip_cost_to_stop_distance"])*(entry-stop):
        return "cost_to_stop_filter"
    stop_fill = stop*(1-slip)
    risk_per_share = entry-stop_fill+fee*(entry+stop_fill)
    equity = port.equity()
    remaining = equity*D(cfg["max_aggregate_planned_risk_fraction"])-sum((p["planned_risk"] for p in port.positions.values()), ZERO)
    limits = {"cash": port.settled/(entry*(1+fee)), "risk": equity*D(cfg["risk_fraction_per_entry"])/risk_per_share,
              "aggregate": max(ZERO, remaining)/risk_per_share}
    qty = int(min(limits.values()).to_integral_value(rounding=ROUND_FLOOR))
    if qty < 1: return "zero_quantity_"+min(limits, key=limits.get)
    entry_fee = qty*entry*fee
    cost = qty*entry+entry_fee
    port.settled -= cost
    symbol = feature["symbol"]
    p = {"symbol": symbol, "entry_time": stamp, "qty": qty, "entry": entry, "entry_fee": entry_fee, "cost": cost,
         "stop": stop, "target": entry+D(spec["pattern"]["target_r_multiple"])*(entry-stop),
         "planned_risk": qty*risk_per_share, "mark": entry, "entry_equity": equity}
    port.positions[symbol] = p
    port.events.append({"type": "entry", "time": stamp, **p})
    return "filled"


def replay(spec, sessions, bars, prepared, arm, bps, symbols=None, allowed_days=None):
    if arm not in ("A", "B"): raise ValueError("Unknown comparison arm")
    symbols = list(spec["symbols"] if symbols is None else symbols)
    port = Portfolio(D(spec["portfolio"]["initial_cash"]))
    slip, fee = D(bps)/10000, D(spec["bar_proxy"]["additional_fee_bps_per_side"])/10000
    records, daily_rows, unresolved = [], [], None
    for day, candidates in prepared.items():
        start, end = sessions[day]
        day_records = {s: {"day": day, "symbol": s, "eligible": candidates[s]["status"] == "eligible",
                            "status": "not_evaluated_after_unresolved" if unresolved else "pending",
                            "reasons": candidates[s]["reasons"]} for s in symbols}
        records.extend(day_records.values())
        if unresolved: continue
        port.settle(start)
        start_equity = port.equity()
        if allowed_days is not None and day not in allowed_days:
            for r in day_records.values(): r["status"] = "excluded_complete_day_diagnostic"
            daily_rows.append({"day": day, "start_equity": start_equity, "end_equity": start_equity, "return": ZERO, "excluded": True})
            continue
        eligible = [s for s in symbols if candidates[s]["status"] == "eligible"]
        selected = eligible
        if arm == "B":
            selected = sorted((s for s in eligible if candidates[s]["rvol"] >= D(spec["selection"]["rvol_min"])),
                              key=lambda s: (-candidates[s]["rvol"], -candidates[s]["dollar_volume"], s))[:spec["selection"]["max_candidates"]]
        signals = {}
        for symbol in symbols:
            r, f = day_records[symbol], candidates[symbol]
            if symbol not in eligible: r["status"] = "ineligible"; continue
            r["rvol"] = f["rvol"]
            if symbol not in selected: r["status"] = "rvol_filter"; continue
            p = f["pattern"]
            r["status"] = p["status"]
            if p["status"] == "signal": signals.setdefault(p["time"], []).append(symbol)
        stamp = start
        time_exit = end-timedelta(minutes=spec["bar_proxy"]["early_close_exit_minutes_before_close"])
        while stamp < end:
            # An unknown held-position minute taints all subsequent cash/equity.
            missing = [s for s in port.positions if stamp not in bars[s, 1][day]]
            if missing:
                unresolved = {"time": stamp, "symbols": missing, "reason": "missing_held_position_minute"}
                for s in missing: day_records[s]["status"] = "unresolved_open_position"
                for r in day_records.values():
                    if r["status"] == "signal": r["status"] = "not_evaluated_after_unresolved"
                break
            for symbol, p in list(port.positions.items()):
                row = bars[symbol, 1][day][stamp]
                op = D(row["o"])
                if op <= p["stop"]: port.close(symbol, op, "stop_gap", stamp, slip, fee)
                elif op >= p["target"]: port.close(symbol, p["target"], "target_at_open", stamp, slip, fee)
                elif stamp >= time_exit: port.close(symbol, op, "time", stamp, slip, fee)
            for symbol in sorted(signals.get(stamp, []), key=lambda s: (-candidates[s]["dollar_volume"], s)):
                f = candidates[symbol]
                day_records[symbol]["status"] = open_trade(port, f, f["pattern"], bars[symbol, 1][day].get(stamp),
                                                         stamp, spec, slip, fee, start_equity)
            deployed = sum((p["mark"]*p["qty"] for p in port.positions.values()), ZERO)
            port.deployed_minutes += deployed
            port.position_minutes += len(port.positions)
            port.elapsed_minutes += 1
            for symbol, p in list(port.positions.items()):
                row = bars[symbol, 1][day][stamp]
                if D(row["l"]) <= p["stop"]: port.close(symbol, p["stop"], "stop_intraminute", stamp, slip, fee)
                elif D(row["h"]) >= p["target"]: port.close(symbol, p["target"], "target_intraminute", stamp, slip, fee)
                else: p["mark"] = D(row["c"])
            if not port.halted and port.realized_today <= -start_equity*D(spec["portfolio"]["daily_realized_loss_halt_fraction"]):
                port.halted = True
                port.halt_count += 1
            port.equity_curve.append(port.equity())
            if port.settled < 0: raise AssertionError("Negative settled cash")
            stamp += timedelta(minutes=1)
        if unresolved:
            daily_rows.append({"day": day, "start_equity": start_equity, "end_equity": None, "return": None, "unresolved": unresolved})
            continue
        if port.positions: raise AssertionError("Unexpected overnight position")
        equity = port.equity()
        daily_rows.append({"day": day, "start_equity": start_equity, "end_equity": equity, "return": equity/start_equity-1})
    peak = D(spec["portfolio"]["initial_cash"])
    max_drawdown = ZERO
    for equity in port.equity_curve:
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, 1-equity/peak)
    completed_pnl = sum((t["pnl"] for t in port.trades), ZERO)
    final = port.equity() if unresolved is None else None
    if final is not None and final != D(spec["portfolio"]["initial_cash"])+completed_pnl:
        if abs(final-D(spec["portfolio"]["initial_cash"])-completed_pnl) > D("1e-20"):
            raise AssertionError("Ledger PnL does not reconcile")
    return {"arm": arm, "slippage_bps": bps, "complete": unresolved is None, "unresolved": unresolved,
            "initial_cash": D(spec["portfolio"]["initial_cash"]), "terminal_equity": final,
            "net_return": final/D(spec["portfolio"]["initial_cash"])-1 if final is not None else None,
            "partial_realized_pnl": completed_pnl, "settled_cash": port.settled, "unsettled_cash": port.unsettled,
            "open_positions": list(port.positions.values()), "trades": port.trades, "events": port.events,
            "daily": daily_rows, "symbol_days": records, "status_counts": dict(Counter(r["status"] for r in records)),
            "halt_count": port.halt_count, "observed_marked_drawdown": max_drawdown,
            "mean_deployed_dollars_observed": port.deployed_minutes/port.elapsed_minutes if port.elapsed_minutes else ZERO,
            "position_minutes_observed": port.position_minutes, "elapsed_minutes_observed": port.elapsed_minutes,
            "execution_quality": "unvalidated_finalized_bar_proxy"}
