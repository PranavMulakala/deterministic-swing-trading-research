"""Offline raw SIP replication and capital diagnostics; v1 remains frozen."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
from statistics import mean, median

from research.lite_reversal_v1 import experiment as e

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "lite_2026" / "snapshot.json"


def load_bars(path, symbol, step, calendar):
    raw = path.read_bytes()
    data = json.loads(raw)
    q = data["query"]
    if data["complete"] is not True or q.get("feed") != "sip" or q.get("adjustment") != "raw" or q.get("timeframe") != f"{step}Min":
        raise ValueError("Incomplete or wrong feed/adjustment/timeframe")
    if data["path"] != f"/v2/stocks/{symbol}/bars":
        raise ValueError("Wrong symbol")
    known = {d["date"] for d in calendar}
    groups, previous = defaultdict(list), None
    for row in data["rows"]:
        dt = e.timestamp(row["t"])
        if previous is not None and dt <= previous:
            raise ValueError("Duplicate or out-of-order historical bar")
        previous = dt
        minute = dt.hour*60 + dt.minute
        if not 570 <= minute < 960:
            continue
        if dt.date().isoformat() not in known or minute % step or dt.second or dt.microsecond:
            raise ValueError("Unknown session or off-grid timestamp")
        vals = {key:e.number(row[key], key) for key in ("o", "h", "l", "c", "v", "vw")}
        if not vals["l"] <= min(vals["o"], vals["c"]) <= max(vals["o"], vals["c"]) <= vals["h"]:
            raise ValueError("Malformed OHLC")
        groups[dt.date().isoformat()].append(e.Bar(dt, **vals))
    included, excluded = {}, []
    for session in calendar:
        day = session["date"]
        if session["open"] != "09:30" or session["close"] != "16:00":
            excluded.append({"date":day, "reason":"nonstandard_session"})
        elif tuple(b.minute for b in groups[day]) != tuple(range(570, 960, step)):
            excluded.append({"date":day, "reason":"missing_bars", "missing_minutes":sorted(set(range(570,960,step))-{b.minute for b in groups[day]})})
        else:
            included[day] = groups[day]
    return included, {"sha256":e.digest(raw), "records":len(data["rows"]), "pages":data["pages"],
                      "complete_sessions":len(included), "excluded":excluded}


def minute_trade(five_bars, minute_bars, signal, intent, cfg, cost):
    when = five_bars[signal.index].timestamp + timedelta(minutes=5)
    after = [bar for bar in minute_bars if bar.timestamp >= when]
    if not after or after[0].timestamp != when:
        raise ValueError("Missing exact entry minute")
    # The first element is the genuine completed 5-minute signal bar. All later
    # elements are 1-minute execution bars. The frozen fill function reads only
    # subsequent OHLC and the clock; it does not derive new signals from them.
    stream = [five_bars[signal.index]] + after
    trade, reason = e.trade_day(stream, replace(signal, index=0), intent, cfg, cost)
    if trade and trade["exit_time_precision"] == "within_five_minute_bar":
        trade["exit_time_precision"] = "within_one_minute_bar"
    return trade, reason


def run_minute(fives, minutes, cfg, variant, cost, mode):
    cash, days, trades = cfg.initial_cash, [], []
    for day, bars in fives.items():
        signal = e.find_signal(bars, variant, cfg)
        status = "no_dip" if not e.has_dip(bars, cfg) else "no_signal"
        trade = None
        if signal:
            intent, status = e.order_intent(signal, cash, cfg, cost, mode)
            if intent:
                trade, status = minute_trade(bars, minutes[day], signal, intent, cfg, cost)
            if trade:
                trades.append(trade)
                cash = trade["equity_after"]
                status = "filled"
        days.append(dict(date=day, status=status, signal=signal is not None,
                         equity=cash, pnl=trade["pnl"] if trade else 0.0))
    return dict(variant=variant, cost_bps_per_side=cost, share_mode=mode,
                execution_resolution="1Min", summary=dict(final_cash=cash,
                    net_pnl=cash-cfg.initial_cash, trades=len(trades),
                    signals=sum(d["signal"] for d in days), status_counts=dict(Counter(d["status"] for d in days)),
                    win_rate=sum(t["pnl"]>0 for t in trades)/len(trades) if trades else None),
                trades=trades, daily_ledger=days,
                validation=e.check_ledger(days,trades,cfg,mode))


def capital_diagnostic(included, cfg):
    results = []
    for variant in ("dip", "vwap_retest"):
        for day, bars in included.items():
            signal = e.find_signal(bars, variant, cfg)
            if not signal:
                continue
            intent, reason = e.order_intent(signal, 500, cfg, 10, "fractional_diagnostic")
            if intent is None:
                results.append(dict(date=day, variant=variant, status=reason))
                continue
            risk_per_share = intent["cap"] - signal.stop*.999
            failures = []
            if intent["cap"] > 500:
                failures.append("cash")
            if risk_per_share > 500*cfg.risk_fraction:
                failures.append("risk")
            results.append(dict(date=day, variant=variant, status="valid_signal",
                signal_time=(bars[signal.index].timestamp+timedelta(minutes=5)).isoformat(),
                cap=intent["cap"], raw_limit=intent["cap"]/1.001,
                risk_per_whole_share=risk_per_share,
                minimum_equity_one_share=max(intent["cap"],risk_per_share/cfg.risk_fraction),
                whole_share_failures=failures,
                hypothetical_fractional_quantity=intent["qty"]))
    return results


def market_controls(lite, spy, cfg):
    groups = defaultdict(list)
    for day, bars in lite.items():
        if day not in spy:
            continue
        lret = bars[77].o/bars[6].o-1
        sret = spy[day][77].o/spy[day][6].o-1
        groups["all_days"].append(lret-sret)
        if e.has_dip(bars, cfg):
            groups["opening_dip_days"].append(lret-sret)
    return {k:dict(n=len(v), mean_lite_minus_spy_return=mean(v),
                   label="10:00-15:55 endpoint excess return, before costs, not a risk-matched portfolio") for k,v in groups.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve earlier results: choose a new directory")
    cfg = e.Config(**json.loads((e.HERE/"config.json").read_text()))
    original = OLD.read_bytes()
    if e.digest(original) != cfg.snapshot_sha256:
        raise ValueError("Original calendar snapshot changed")
    calendar = json.loads(original)["calendar"]
    five, cov5 = load_bars(args.data/"LITE_5Min.json", "LITE", 5, calendar)
    one, cov1 = load_bars(args.data/"LITE_1Min.json", "LITE", 1, calendar)
    spy, covspy = load_bars(args.data/"SPY_5Min.json", "SPY", 5, calendar)
    joint = {day:rows for day,rows in five.items() if day in one}
    scenarios = [(v,c,m) for v in ("dip","vwap_retest") for c in cfg.cost_bps_per_side
                 for m in ("whole","fractional_diagnostic")]
    five_runs = [e.run_variant(five,cfg,*s) for s in scenarios]
    joint_five = [e.run_variant(joint,cfg,*s) for s in scenarios]
    minute_runs = [run_minute(joint,one,cfg,*s) for s in scenarios]
    capital = capital_diagnostic(five,cfg)
    windows = []
    for row in capital:
        if row["variant"] == "vwap_retest" and row["status"] == "valid_signal":
            when = datetime.fromisoformat(row["signal_time"])
            windows.append({"start":(when-timedelta(seconds=2)).isoformat(), "end":(when+timedelta(seconds=8)).isoformat()})
    result = dict(status="RESEARCH_ONLY", strategy_parameters_changed=False, unseen_test=False,
        provenance={"study_sha256":e.digest(Path(__file__).read_bytes()), "original_engine_sha256":e.digest(Path(e.__file__).read_bytes()),
                    "original_config_sha256":e.digest((e.HERE/"config.json").read_bytes()),
                    "method_sha256":e.digest((HERE/"METHOD.md").read_bytes())},
        coverage={"LITE_5Min":cov5,"LITE_1Min":cov1,"SPY_5Min":covspy,"matched_sessions":len(joint)},
        full_sip_five_minute=five_runs, matched_five_minute=joint_five,
        matched_one_minute=minute_runs, capital_diagnostics=capital,
        market_controls=market_controls(five,spy,cfg), quote_windows=windows)
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    (args.output/"quote_windows.json").write_text(json.dumps(windows,indent=2)+"\n")
    print(json.dumps({"coverage":result["coverage"],
        "scenarios":{name:[{k:r[k] for k in ("variant","cost_bps_per_side","share_mode","summary")} for r in result[name]]
                     for name in ("full_sip_five_minute","matched_five_minute","matched_one_minute")},
        "vwap_capital":[r for r in capital if r["variant"]=="vwap_retest"],
        "quote_windows":len(windows), "market_controls":result["market_controls"]},indent=2))


if __name__ == "__main__":
    main()
