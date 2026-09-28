"""Offline LITE experiment. No broker, environment, credential or network access.

Run: .venv/bin/python -m research.lite_reversal_v1.experiment --output /tmp/lite-run
The output directory must not exist. See SPEC.md for assumptions and limitations.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import mean
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
NY = ZoneInfo("America/New_York")
MINUTES = tuple(range(570, 960, 5))


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def number(value, name: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return float(value)


@dataclass(frozen=True)
class Config:
    version: str
    snapshot_sha256: str
    symbol: str
    initial_cash: float
    risk_fraction: float
    opening_drop_fraction: float
    stop_buffer_fraction: float
    minimum_reward_risk: float
    maximum_entry_gap_fraction: float
    cost_bps_per_side: list[int]
    target_penetration_bps: float
    bootstrap_repetitions: int
    bootstrap_seed: int

    def __post_init__(self):
        if self.symbol != "LITE" or not self.version:
            raise ValueError("This experiment only supports LITE")
        if len(self.snapshot_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.snapshot_sha256):
            raise ValueError("Invalid snapshot hash")
        for key in ("initial_cash", "risk_fraction", "opening_drop_fraction",
                    "stop_buffer_fraction", "minimum_reward_risk",
                    "maximum_entry_gap_fraction", "target_penetration_bps"):
            number(getattr(self, key), key)
        for key in ("risk_fraction", "opening_drop_fraction", "stop_buffer_fraction",
                    "maximum_entry_gap_fraction"):
            if getattr(self, key) >= 1:
                raise ValueError(f"{key} must be below one")
        if not isinstance(self.cost_bps_per_side, list) or not self.cost_bps_per_side:
            raise ValueError("Missing cost scenarios")
        if len(set(self.cost_bps_per_side)) != len(self.cost_bps_per_side):
            raise ValueError("Duplicate cost scenarios")
        for cost in self.cost_bps_per_side + [self.target_penetration_bps]:
            if number(cost, "basis points") >= 10000:
                raise ValueError("Invalid basis points")
        if type(self.bootstrap_repetitions) is not int or not 100 <= self.bootstrap_repetitions <= 100000:
            raise ValueError("Invalid bootstrap count")
        if type(self.bootstrap_seed) is not int:
            raise ValueError("Invalid bootstrap seed")


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    o: float
    h: float
    l: float
    c: float
    v: float
    vw: float

    @property
    def minute(self):
        return self.timestamp.hour * 60 + self.timestamp.minute


@dataclass(frozen=True)
class Signal:
    index: int
    stop: float
    target: float
    close: float


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Naive bar timestamp")
    return parsed.astimezone(NY)


def sessions(snapshot: dict, cfg: Config):
    if snapshot.get("feed") != "iex" or snapshot.get("adjustment") != "all":
        raise ValueError("Unexpected snapshot price/feed semantics")
    start, end = date.fromisoformat(snapshot["start"]), date.fromisoformat(snapshot["through"])
    if start > end:
        raise ValueError("Inverted date range")
    calendar = snapshot["calendar"]
    dates = [row["date"] for row in calendar]
    if not dates or dates != sorted(set(dates)):
        raise ValueError("Calendar must be nonempty, ordered and unique")
    if any(not start <= date.fromisoformat(day) <= end for day in dates):
        raise ValueError("Calendar outside snapshot period")
    known = set(dates)
    groups = defaultdict(list)
    previous = None
    for row in snapshot["intraday"][cfg.symbol]:
        dt = timestamp(row["t"])
        if previous is not None and dt <= previous:
            raise ValueError("Duplicate or out-of-order bar")
        previous = dt
        if not start <= dt.date() <= end:
            raise ValueError("Bar outside snapshot period")
        minute = dt.hour * 60 + dt.minute
        if not 570 <= minute < 960:
            continue  # Extended hours deliberately do not contribute to VWAP.
        if dt.date().isoformat() not in known:
            raise ValueError("Regular-hours bar on unknown calendar date")
        if dt.second or dt.microsecond or minute not in MINUTES:
            raise ValueError("Off-grid bar timestamp")
        vals = {key: number(row[key], key) for key in ("o", "h", "l", "c", "v", "vw")}
        if not vals["l"] <= min(vals["o"], vals["c"]) <= max(vals["o"], vals["c"]) <= vals["h"]:
            raise ValueError("Inconsistent OHLC")
        groups[dt.date().isoformat()].append(Bar(dt, **vals))
    included, excluded = {}, []
    for row in calendar:
        day = row["date"]
        if row["open"] != "09:30" or row["close"] != "16:00":
            excluded.append(dict(date=day, reason="nonstandard_session"))
        elif tuple(bar.minute for bar in groups[day]) != MINUTES:
            missing = sorted(set(MINUTES) - {bar.minute for bar in groups[day]})
            excluded.append(dict(date=day, reason="incomplete_regular_session", missing_minutes=missing))
        else:
            included[day] = groups[day]
    return included, excluded


def vwap(bars: list[Bar]) -> list[float]:
    total_pv = total_volume = 0.0
    result = []
    for bar in bars:
        total_pv += bar.vw * bar.v
        total_volume += bar.v
        result.append(total_pv / total_volume)
    return result


def has_dip(bars: list[Bar], cfg: Config) -> bool:
    return len(bars) >= 6 and min(b.l for b in bars[:6]) <= bars[0].o * (1 - cfg.opening_drop_fraction)


def find_signal(bars: list[Bar], variant: str, cfg: Config) -> Signal | None:
    """May be called on a prefix; never requires future prices or a future pivot."""
    if variant not in ("dip", "vwap_retest"):
        raise ValueError("Unknown strategy variant")
    if not has_dip(bars, cfg):
        return None
    opening = bars[0].o
    buffer = opening * cfg.stop_buffer_fraction
    if variant == "dip":
        return Signal(5, min(b.l for b in bars[:6]) - buffer, opening, bars[5].c)
    averages = vwap(bars[:17])
    arm = None
    for i in range(6, min(len(bars), 17)):
        bar = bars[i]
        if arm is not None:
            if bar.l <= averages[i] < bar.c < opening and bar.l >= bars[arm].l:
                return Signal(i, min(bar.l, bars[arm].l) - buffer, opening, bar.c)
            arm = None
        if bars[i - 1].c <= averages[i - 1] and averages[i] < bar.c < opening:
            arm = i
    return None


def order_intent(signal: Signal, cash: float, cfg: Config, cost_bps: float, mode: str):
    if mode not in ("whole", "fractional_diagnostic"):
        raise ValueError("Unknown share mode")
    c = cost_bps / 10000
    if not 0 < signal.stop < signal.close < signal.target:
        return None, "invalid_signal_levels"
    stop_net, target_net = signal.stop * (1 - c), signal.target * (1 - c)
    cap = min(signal.close * (1 + cfg.maximum_entry_gap_fraction),
              (target_net + cfg.minimum_reward_risk * stop_net) / (1 + cfg.minimum_reward_risk))
    if cap <= signal.stop or cap <= stop_net:
        return None, "invalid_entry_cap"
    capacity = min(cash / cap, cash * cfg.risk_fraction / (cap - stop_net))
    granularity = 1 if mode == "whole" else 1000000
    qty = math.floor(capacity * granularity) / granularity
    if qty <= 0:
        return None, "zero_quantity"
    return dict(cap=cap, qty=qty, planned_risk=qty * (cap - stop_net),
                cash_before=cash), None


def exit_fill(bar: Bar, stop: float, target: float, cfg: Config, cost_bps: float):
    """Raw execution reference, reason, ambiguity. Caller applies selling costs."""
    penetration = target * (1 + cfg.target_penetration_bps / 10000)
    if bar.o <= stop:
        return bar.o, "gap_stop", False
    if bar.minute == 955:
        return bar.o, "time", False
    if bar.o > penetration:
        return target, "gap_target", False
    stop_hit, target_hit = bar.l <= stop, bar.h > penetration
    if stop_hit:
        return stop, "stop", target_hit
    if target_hit:
        return target, "target", False
    return None


def trade_day(bars: list[Bar], signal: Signal, intent: dict, cfg: Config, cost_bps: float):
    c = cost_bps / 10000
    entry_index = signal.index + 1
    entry_bar = bars[entry_index]
    raw_entry = entry_bar.o
    if not signal.stop < raw_entry < signal.target:
        return None, "entry_open_outside_levels"
    entry = raw_entry * (1 + c)
    if entry > intent["cap"]:
        return None, "entry_cap_not_filled"
    qty, cash = intent["qty"], intent["cash_before"]
    debit = qty * entry
    low_equity = cash - debit + qty * raw_entry * (1 - c)
    for i in range(entry_index, len(bars)):
        bar = bars[i]
        outcome = exit_fill(bar, signal.stop, signal.target, cfg, cost_bps)
        if outcome is None:
            low_equity = min(low_equity, cash - debit + qty * bar.l * (1 - c))
            continue
        raw_exit, reason, ambiguous = outcome
        credit = qty * raw_exit * (1 - c)
        # At time/gap exits only the open is observable before exit. At an intrabar
        # exit use a conservative lower mark; OHLC cannot order post-exit lows.
        mark = min(raw_exit, bar.l) if reason == "target" else raw_exit
        low_equity = min(low_equity, cash - debit + qty * mark * (1 - c))
        pnl = credit - debit
        result = dict(date=bar.timestamp.date().isoformat(),
                      signal_time=(bars[signal.index].timestamp + timedelta(minutes=5)).isoformat(),
                      entry_time=entry_bar.timestamp.isoformat(),
                      exit_bar_time=bar.timestamp.isoformat(),
                      exit_time_precision="exact_bar_open" if reason in ("time", "gap_stop", "gap_target") else "within_five_minute_bar",
                      quantity=qty, entry_cap=intent["cap"], stop=signal.stop, target=signal.target,
                      raw_entry=raw_entry, raw_exit=raw_exit, entry_all_in=entry,
                      exit_net=raw_exit * (1 - c), entry_debit=debit, exit_credit=credit,
                      planned_risk=intent["planned_risk"], pnl=pnl,
                      gross_pnl=qty * (raw_exit - raw_entry), modeled_costs=qty * c * (raw_entry + raw_exit),
                      r_multiple=pnl / intent["planned_risk"], reason=reason,
                      ambiguous_stop_target=ambiguous, equity_before=cash,
                      equity_after=cash + pnl, conservative_low_equity=low_equity)
        return result, None
    raise ValueError("No session exit: incomplete input must not be simulated")


def check_ledger(days: list[dict], trades: list[dict], cfg: Config, mode: str):
    balance = cfg.initial_cash
    trade_by_day = {t["date"]: t for t in trades}
    if len(trade_by_day) != len(trades) or len({d["date"] for d in days}) != len(days):
        raise ValueError("Duplicate trade/session")
    if not set(trade_by_day) <= {d["date"] for d in days}:
        raise ValueError("Orphan trade")
    for day in days:
        trade = trade_by_day.get(day["date"])
        if (day["status"] == "filled") != (trade is not None):
            raise ValueError("Trade/status mismatch")
        if trade:
            if trade["quantity"] <= 0 or (mode == "whole" and not trade["quantity"].is_integer()):
                raise ValueError("Invalid share quantity")
            if trade["entry_debit"] > balance + 1e-8 or trade["planned_risk"] > balance * cfg.risk_fraction + 1e-8:
                raise ValueError("Cash/risk invariant failed")
            if trade["entry_all_in"] > trade["entry_cap"] + 1e-8:
                raise ValueError("Entry limit invariant failed")
            if not math.isclose(trade["equity_before"], balance, abs_tol=1e-8):
                raise ValueError("Beginning balance mismatch")
            for a, b in ((trade["pnl"], trade["exit_credit"] - trade["entry_debit"]),
                         (trade["pnl"], trade["gross_pnl"] - trade["modeled_costs"]),
                         (trade["entry_debit"], trade["quantity"] * trade["entry_all_in"]),
                         (trade["exit_credit"], trade["quantity"] * trade["exit_net"])):
                if not math.isclose(a, b, abs_tol=1e-8):
                    raise ValueError("P&L reconciliation failed")
            balance -= trade["entry_debit"]
            balance += trade["exit_credit"]
            if not math.isclose(trade["equity_after"], balance, abs_tol=1e-8):
                raise ValueError("Ending trade balance mismatch")
        if not math.isfinite(balance) or balance < 0 or not math.isclose(day["equity"], balance, abs_tol=1e-8):
            raise ValueError("Equity ledger mismatch")
    return dict(status="PASS", sessions_checked=len(days), trades_checked=len(trades),
                replayed_final_cash=balance)


def bootstrap(days: list[dict], trades: list[dict], cfg: Config):
    weeks = defaultdict(list)
    for day in days:
        dt = date.fromisoformat(day["date"])
        weeks[dt - timedelta(days=dt.weekday())]
    for trade in trades:
        dt = date.fromisoformat(trade["date"])
        weeks[dt - timedelta(days=dt.weekday())].append(trade["r_multiple"])
    blocks = list(weeks.values())
    if not trades or len(blocks) < 2:
        return dict(interval=None, reason="insufficient_data")
    rng = random.Random(cfg.bootstrap_seed)
    stats = []
    for _ in range(cfg.bootstrap_repetitions):
        sample = [value for _ in blocks for value in rng.choice(blocks)]
        if sample:
            stats.append(mean(sample))
    stats.sort()
    return dict(interval=[stats[int((len(stats)-1)*0.025)], stats[int((len(stats)-1)*0.975)]],
                unit="mean_net_R_per_trade", method="calendar_week_block_percentile",
                valid_resamples=len(stats), calendar_weeks=len(blocks),
                traded_weeks=sum(bool(block) for block in blocks),
                warning="Exploratory; interval does not account for strategy/cohort selection")


def run_variant(included: dict, cfg: Config, variant: str, cost: float, mode: str):
    cash, days, trades = cfg.initial_cash, [], []
    peak = cash
    closed_dd = low_dd = 0.0
    for day, bars in included.items():
        signal = find_signal(bars, variant, cfg)
        status = "no_dip" if not has_dip(bars, cfg) else "no_signal"
        trade = None
        if signal is not None:
            intent, status = order_intent(signal, cash, cfg, cost, mode)
            if intent is not None:
                trade, status = trade_day(bars, signal, intent, cfg, cost)
            if trade:
                status = "filled"
                trades.append(trade)
                cash = trade["equity_after"]
                low_dd = max(low_dd, 1 - trade["conservative_low_equity"] / peak)
        peak = max(peak, cash)
        closed_dd = max(closed_dd, 1 - cash / peak)
        days.append(dict(date=day, status=status, signal=signal is not None, equity=cash,
                         pnl=trade["pnl"] if trade else 0.0))
    invariant = check_ledger(days, trades, cfg, mode)
    pnls = [t["pnl"] for t in trades]
    gains, losses = sum(p for p in pnls if p > 0), -sum(p for p in pnls if p < 0)
    monthly = {}
    for month in sorted({d["date"][:7] for d in days}):
        rows = [t for t in trades if t["date"][:7] == month]
        monthly[month] = dict(trades=len(rows), net_pnl=sum(t["pnl"] for t in rows))
    return dict(variant=variant, cost_bps_per_side=cost, share_mode=mode,
                summary=dict(initial_cash=cfg.initial_cash, final_cash=cash,
                             net_pnl=cash-cfg.initial_cash, trades=len(trades),
                             signals=sum(d["signal"] for d in days),
                             status_counts=dict(Counter(d["status"] for d in days)),
                             win_rate=sum(p > 0 for p in pnls)/len(pnls) if pnls else None,
                             profit_factor=gains/losses if losses else None,
                             profit_factor_note="undefined_without_losses" if not losses else None,
                             mean_net_r=mean(t["r_multiple"] for t in trades) if trades else None,
                             worst_trade=min(pnls) if pnls else None,
                             modeled_costs=sum(t["modeled_costs"] for t in trades),
                             max_closed_equity_drawdown=closed_dd,
                             max_low_mark_decline_from_prior_closed_peak=low_dd,
                             ambiguous_exits=sum(t["ambiguous_stop_target"] for t in trades)),
                uncertainty=bootstrap(days, trades, cfg), monthly=monthly,
                validation=invariant, trades=trades, daily_ledger=days)


def references(included: dict, cfg: Config):
    result = {}
    for cost in cfg.cost_bps_per_side:
        c = cost / 10000
        for subset in ("all_covered_days", "opening_dip_days"):
            values = [bars[77].o*(1-c)/(bars[6].o*(1+c))-1 for bars in included.values()
                      if subset == "all_covered_days" or has_dip(bars, cfg)]
            result[f"{subset}_{cost}bps"] = dict(n=len(values),
                mean_return=mean(values) if values else None,
                positive_fraction=sum(v > 0 for v in values)/len(values) if values else None,
                label="10:00 to 15:55 open return; not risk-matched or a portfolio")
    return result


def evaluate(snapshot: dict, cfg: Config):
    included, excluded = sessions(snapshot, cfg)
    if not included:
        raise ValueError("No complete sessions")
    runs = [run_variant(included, cfg, variant, cost, mode)
            for variant in ("dip", "vwap_retest")
            for cost in cfg.cost_bps_per_side
            for mode in ("whole", "fractional_diagnostic")]
    return dict(status="RESEARCH_ONLY", unseen_test=False,
                coverage=dict(calendar_sessions=len(snapshot["calendar"]), included=len(included),
                              excluded=excluded, warning="Retrospective full-session completeness selection"),
                data=dict(feed=snapshot["feed"], adjustment=snapshot["adjustment"],
                          through=snapshot["through"], fetched_at=snapshot.get("fetched_at")),
                news_variant=dict(status="BLOCKED_DATA", records=len(snapshot.get("news", [])),
                    reason="No original text/headlines or historical first-received timestamps; sentiment not tested"),
                references=references(included, cfg), runs=runs)


def render_report(result: dict) -> str:
    coverage = result["coverage"]
    lines = ["# LITE reversal v1 — measured exploratory results", "",
             "Status: **RESEARCH_ONLY. No unseen validation and no automated trading enabled.**", "",
             f"Coverage: {coverage['included']} of {coverage['calendar_sessions']} calendar sessions. "
             "Excluded days are listed in results.json, not assigned zero returns.", "",
             "Conditional $500 compounding ledgers; adjusted IEX bars, idealized fills, "
             "retrospective completeness selection. Fractional rows are diagnostics, not broker-feasibility claims.", "",
             "| Variant | Shares | Cost / side | Trades | Final cash | Net P&L | Win rate | Mean R |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for run in result["runs"]:
        s = run["summary"]
        win = f"{s['win_rate']:.1%}" if s["win_rate"] is not None else "N/A"
        r = f"{s['mean_net_r']:.3f}" if s["mean_net_r"] is not None else "N/A"
        lines.append(f"| {run['variant']} | {run['share_mode']} | {run['cost_bps_per_side']} bps | "
                     f"{s['trades']} | ${s['final_cash']:.2f} | ${s['net_pnl']:+.2f} | {win} | {r} |")
    lines += ["", "## Checks and rejected orders", ""]
    for run in result["runs"]:
        name = f"{run['variant']}/{run['share_mode']}/{run['cost_bps_per_side']}bps"
        lines += [f"- {name}: {json.dumps(run['summary']['status_counts'], sort_keys=True)}; "
                  f"ledger {run['validation']['status']}; week-bootstrap mean-R interval "
                  f"{run['uncertainty']['interval']}."]
    lines += ["", "## Interpretation", "",
              "The practical whole-share result and the fractional price-pattern diagnostic answer different "
              "questions. Few fills or an unchanged balance do not prove a strategy is low-risk or profitable. "
              "All variations are published; no historical winner is promoted.", "",
              "News variant: **BLOCKED_DATA**. Original headlines/text and historical delivery evidence "
              "are missing. Article links/timestamps have not been relabeled as sentiment.", "",
              "No result here establishes an edge. A frozen unseen evaluation, raw consolidated execution "
              "data, actual broker feasibility, and realistic fill/latency checks remain necessary.", "",
              "See SPEC.md for fixed rules and limitations. results.json contains every trade, daily "
              "equity row, exclusion, monthly result, cost, bootstrap interval and provenance hash.", "",
              "## Provenance", "", "```json", json.dumps(result["provenance"], indent=2), "```", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=HERE.parent / "lite_2026" / "snapshot.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw_config = (HERE / "config.json").read_bytes()
    cfg = Config(**json.loads(raw_config))
    raw_snapshot = args.snapshot.read_bytes()  # No network or credential fallback.
    if digest(raw_snapshot) != cfg.snapshot_sha256:
        raise ValueError("Snapshot hash mismatch: preserve the original or declare a new experiment")
    if args.output.exists():
        raise FileExistsError("Output already exists; choose a new directory to preserve earlier runs")
    result = evaluate(json.loads(raw_snapshot), cfg)
    result["provenance"] = dict(snapshot_sha256=digest(raw_snapshot),
        config_sha256=digest(raw_config), engine_sha256=digest(Path(__file__).read_bytes()),
        spec_sha256=digest((HERE / "SPEC.md").read_bytes()), config=json.loads(raw_config))
    report = render_report(result)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (args.output / "REPORT.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
