"""Backtest of pre-declared test #16: Qullamaggie's episodic pivot (output/EP_EARNINGS_GAP_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.ep_test_v1.backtest

Main rule: an 8-K with Item 2.02 accepted from the previous session's 16:00 close to 10:30 ET on the gap day; open >=
1.10 x previous close; 20-day average dollar volume >= $20M; 9:30-10:00 volume >= 1.0 x the 20-day average daily volume;
buy the first 5-minute bar from 10:30 to 15:55 that trades above the 9:30-10:30 high, at max(ORH, bar open) + 0.1%;
stop = the day's low before the entry bar; skip if the stop is wider than the 20-day average daily range; risk 1% of
equity, cap 25% of equity, cash only; sell half at the close of the 3rd trading day after entry and move the stop to
break-even; sell the rest at the first close below the 10-day average. Research only; no orders.

Each position's exits don't depend on the portfolio, so they are computed once per event (lifecycle) and the portfolio
only decides which events it can afford and when cash comes back: a stop at the open frees cash before that day's
entries; any other sale frees it after them.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import gzip
import json
from pathlib import Path
import statistics
from zoneinfo import ZoneInfo

from research.breakout_test_v1.backtest import DATA, load as load_daily
from research.ep_test_v1.candidates import GAP, LOOKBACK, MIN_ADV_USD, OUT_DIR, START
from research.ep_test_v1.fetch_intraday import path_for
from research.provenance_v1.provenance import write_manifest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/ep-test-results.json"
NY = ZoneInfo("America/New_York")
START_CASH, RISK, CAP, MIN_BUY, COST = 100_000.0, 0.01, 0.25, 1_000.0, 0.001
VOL_MULT, OR_END, LAST_ENTRY, HALF_DAY, TRAIL, SCALE_TOL = 1.0, 630, 955, 3, 10, 0.05
HALVES = (("2016-2020", "2016-01-01", "2020-12-31"), ("2021-2026", "2021-01-01", "2026-12-31"))


# ---------- the rule, as pure functions (unit-tested) ----------

def prior_stats(b, i):
    """20 trading days before day i: average share volume, average dollar volume, average daily range (fraction)."""
    w = range(i - LOOKBACK, i)
    adv = sum(b["volume"][j] for j in w) / LOOKBACK
    adv_usd = sum(b["close"][j] * b["volume"][j] for j in w) / LOOKBACK
    adr = sum((b["high"][j] - b["low"][j]) / b["close"][j - 1] for j in w) / LOOKBACK
    return adv, adv_usd, adr


def acceptance_times(rows):
    return sorted(datetime.fromisoformat(r[0].replace("Z", "+00:00")).astimezone(NY) for r in rows)


def earnings_ok(accepted, prev_day, day):
    """An Item 2.02 8-K accepted from the previous session's 16:00 close up to (not including) 10:30 ET on the gap day."""
    lo = datetime.fromisoformat(f"{prev_day}T16:00:00").replace(tzinfo=NY)
    hi = datetime.fromisoformat(f"{day}T10:30:00").replace(tzinfo=NY)
    return any(lo <= t < hi for t in accepted)


def earnings_later_that_day(accepted, day):
    hi = datetime.fromisoformat(f"{day}T10:30:00").replace(tzinfo=NY)
    return any(t >= hi and t.date().isoformat() == day for t in accepted)


def entry_signal(bars, adv, adr, cost=COST, flip=False):
    """(entry, reason) from the gap day's 5-minute bars [[minute, o, h, l, c, v], ...] (regular session, sorted)."""
    if not any(x[0] < OR_END for x in bars):
        return None, "no_intraday"
    if sum(x[5] for x in bars if x[0] < 600) < VOL_MULT * adv:
        return None, "low_volume"
    orh = max(x[2] for x in bars if x[0] < OR_END)
    k = next((n for n, x in enumerate(bars) if OR_END <= x[0] <= LAST_ENTRY and x[2] > orh), None)
    if k is None:
        return None, "no_breakout"
    bar = bars[k]
    fill = max(orh, bar[1]) * (1 + cost)
    stop = min(x[3] for x in bars[:k])            # the day's low before the entry bar
    ambiguous = bar[3] <= stop                     # the entry bar also traded at/below that low: order unknown
    if ambiguous and flip:
        stop = bar[3]                              # flip: assume the low came first, then the breakout
    if (fill - stop) / fill > adr:
        return None, "stop_wider_than_adr"
    return {"k": k, "minute": bar[0], "fill": fill, "stop": stop, "ambiguous": ambiguous, "orh": orh}, "ok"


def lifecycle(b, i, bars, sig, cost=COST, trail=TRAIL, flip=False):
    """Exit parts [(date, price after costs, fraction of the position, kind)] for one position bought on day i."""
    day, stop, fill, parts = b["date"][i], sig["stop"], sig["fill"], []
    if sig["ambiguous"] and not flip:
        return [(day, stop * (1 - cost), 1.0, "stop_entry_bar")]
    for x in bars[sig["k"] + 1:]:
        if x[1] <= stop:
            return [(day, x[1] * (1 - cost), 1.0, "stop_entry_day")]
        if x[3] <= stop:
            return [(day, stop * (1 - cost), 1.0, "stop_entry_day")]
    left, c = 1.0, b["close"]
    for j in range(i + 1, len(b["date"])):
        d = b["date"][j]
        if b["open"][j] <= stop:
            return parts + [(d, b["open"][j] * (1 - cost), left, "stop_open")]
        if b["low"][j] <= stop:
            return parts + [(d, stop * (1 - cost), left, "stop")]
        if j - i == HALF_DAY:
            parts.append((d, c[j] * (1 - cost), left / 2, "half_day3"))
            left /= 2
            stop = max(stop, fill)                 # break-even on the rest
        if c[j] < sum(c[j - trail + 1:j + 1]) / trail:
            return parts + [(d, c[j] * (1 - cost), left, "trail")]
    return parts + [(b["date"][-1], c[-1], left, "open_end")]   # marked at the last close, no sale


def size(equity_prev, cash, fill, stop):
    """Dollars to spend: 1% of equity at risk, capped at 25% of equity and by cash; 0 if under $1,000."""
    value = min(RISK * equity_prev / (fill - stop) * fill, CAP * equity_prev, cash)
    return value if value >= MIN_BUY else 0.0


# ---------- data ----------

def load_all():
    cands = json.loads((OUT_DIR / "candidates.json").read_text())["by_date"]
    edgar = json.loads((OUT_DIR / "edgar_item_202.json").read_text())
    spy = load_daily("SPY")
    end = spy["date"][-1]
    syms = sorted({s for v in cands.values() for s in v})
    daily = {}
    for s in syms:
        b = load_daily(s)
        n = sum(1 for d in b["date"] if d <= end)
        daily[s] = {k: v[:n] for k, v in b.items()}
    intraday = {}
    for day in cands:
        p = path_for(day)
        if p.exists():
            with gzip.open(p, "rt") as f:
                for s, rows in json.load(f).items():
                    intraday[(s, day)] = rows
    accepted = {s: acceptance_times(rows) for s, rows in edgar["rows"].items()}
    return cands, daily, intraday, accepted, spy, edgar


def build_events(cands, daily, intraday, accepted, earnings=True, cost=COST, trail=TRAIL, flip=False):
    """Every qualifying event with its lifecycle, plus the reason each candidate day was or wasn't taken."""
    events, reasons, later = [], {}, 0
    for day, syms in cands.items():
        for s in syms:
            b = daily[s]
            try:
                i = b["date"].index(day)
            except ValueError:
                reasons[(s, day)] = "no_daily_bar"
                continue
            if i < LOOKBACK + 1:
                reasons[(s, day)] = "warmup"
                continue
            adv, adv_usd, adr = prior_stats(b, i)
            if adv_usd < MIN_ADV_USD:
                reasons[(s, day)] = "low_liquidity"
                continue
            if b["open"][i] < GAP * b["close"][i - 1]:
                reasons[(s, day)] = "no_gap"
                continue
            acc = accepted.get(s, [])
            if earnings and not earnings_ok(acc, b["date"][i - 1], day):
                reasons[(s, day)] = "no_cik" if s not in accepted else "no_earnings_in_window"
                later += earnings_later_that_day(acc, day)
                continue
            bars = intraday.get((s, day)) or []
            if bars and bars[0][0] < 600 and abs(bars[0][1] / b["open"][i] - 1) > SCALE_TOL:
                reasons[(s, day)] = "scale_mismatch"      # e.g. a split between the daily and intraday downloads
                continue
            sig, why = entry_signal(bars, adv, adr, cost=cost, flip=flip)
            reasons[(s, day)] = why
            if not sig:
                continue
            parts = lifecycle(b, i, bars, sig, cost=cost, trail=trail, flip=flip)
            prior63 = b["close"][i - 1] / b["close"][i - 64] - 1 if i >= 64 else None
            events.append({"symbol": s, "day": day, "minute": sig["minute"], "gap": b["open"][i] / b["close"][i - 1] - 1,
                           "fill": sig["fill"], "stop": sig["stop"], "ambiguous": sig["ambiguous"], "adv_usd": adv_usd,
                           "prior63": prior63, "parts": parts,
                           "ret_pct": 100 * (sum(p[1] * p[2] for p in parts) / sig["fill"] - 1)})
    events.sort(key=lambda e: (e["day"], e["minute"], -e["gap"]))
    return events, reasons, later


# ---------- portfolio ----------

def portfolio(events, daily, calendar):
    by_day = defaultdict(list)
    for e in events:
        by_day[e["day"]].append(e)
    cash, equity_prev, held, trades, curve, skipped, last_close = START_CASH, START_CASH, {}, [], [], Counter(), {}
    entered = 0

    def settle(p, d, at_open_only):
        """Cash from this position's parts dated d; returns (cash, fully exited)."""
        got = 0.0
        for part in p["parts"]:
            if part[0] == d and part[3] != "open_end" and ((part[3] == "stop_open") == at_open_only):
                got += p["shares"] * part[1] * part[2]
                p["left"] -= part[2]
                p["exit_date"], p["exit_kind"] = d, part[3]
        p["proceeds"] += got
        return got, p["left"] <= 1e-9

    for d in calendar:
        later, gone = 0.0, []
        for s, p in list(held.items()):            # 1. stops at today's open free cash before entries
            got, done = settle(p, d, True)
            cash += got
            if done:
                trades.append(finish(held.pop(s), open_=False))
        for e in by_day.get(d, []):                # 2. entries in breakout-time order
            if e["symbol"] in held:
                skipped["already_held"] += 1
                continue
            value = size(equity_prev, cash, e["fill"], e["stop"])
            if not value:
                skipped["no_cash"] += 1
                continue
            cash -= value
            entered += 1
            held[e["symbol"]] = {**e, "shares": value / e["fill"], "left": 1.0, "cost_basis": value, "proceeds": 0.0}
        for s, p in list(held.items()):            # 3. every other sale today frees cash after entries
            got, done = settle(p, d, False)
            later += got
            if done:
                gone.append(s)
        cash += later
        for s in gone:
            trades.append(finish(held.pop(s), open_=False))
        for s in held:
            b = daily[s]
            if b["date"] and d in b.get("_idx", {}):
                last_close[s] = b["close"][b["_idx"][d]]
        equity = cash + sum(p["shares"] * p["left"] * last_close.get(s, p["fill"]) for s, p in held.items())
        curve.append((d, equity))
        equity_prev = equity
    for s, p in held.items():
        trades.append(finish(p, open_=True, mark=last_close.get(s, p["fill"])))
    assert len(trades) == entered, f"{entered} positions entered but {len(trades)} trades recorded"
    return trades, curve, skipped


def finish(p, open_, mark=None):
    """P&L from the sales actually processed, plus what's left marked at the last close if still open."""
    proceeds = p["proceeds"] + (p["shares"] * p["left"] * mark if open_ else 0.0)
    risk = p["shares"] * (p["fill"] - p["stop"])
    pnl = proceeds - p["cost_basis"]
    return {"symbol": p["symbol"], "entry_date": p["day"], "minute": p["minute"], "fill": round(p["fill"], 4),
            "stop": round(p["stop"], 4), "shares": round(p["shares"], 4), "cost_basis": round(p["cost_basis"], 2),
            "pnl": round(pnl, 2), "r": round(pnl / risk, 3) if risk > 0 else None, "open": open_,
            "exit_date": None if open_ else p.get("exit_date"), "exit_kind": "open_end" if open_ else p.get("exit_kind"),
            "gap": round(p["gap"], 4), "adv_usd": round(p["adv_usd"]), "prior63": p["prior63"],
            "ambiguous": p["ambiguous"]}


# ---------- statistics ----------

def curve_stats(curve, start=START_CASH):
    vals = [v for _, v in curve]
    peak, dd = start, 0.0
    for v in vals:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    years = len(vals) / 252
    cagr = (vals[-1] / start) ** (1 / years) - 1
    return {"final": round(vals[-1]), "total_return_pct": round((vals[-1] / start - 1) * 100, 1),
            "cagr_pct": round(cagr * 100, 2), "max_drawdown_pct": round(dd * 100, 1),
            "cagr_over_dd": round(cagr / abs(dd), 3) if dd else None}


def halves(curve, start=START_CASH):
    value, dates, out = dict(curve), [d for d, _ in curve], {}
    for name, a, b in HALVES:
        inside = [d for d in dates if a <= d <= b]
        before = [d for d in dates if d < inside[0]]
        out[name] = round((value[inside[-1]] / (value[before[-1]] if before else start) - 1) * 100, 1)
    return out


def trade_stats(trades, calendar):
    idx = {d: n for n, d in enumerate(calendar)}
    pnl = [t["pnl"] for t in trades]
    gp, gl = sum(p for p in pnl if p > 0), -sum(p for p in pnl if p <= 0)
    rs = [t["r"] for t in trades if t["r"] is not None]
    wins, losses = [r for r in rs if r > 0], [r for r in rs if r <= 0]
    top = sorted(pnl, reverse=True)[:max(1, len(pnl) // 10)]
    closed = [t for t in trades if not t["open"]]
    hold = [idx[t["exit_date"]] - idx[t["entry_date"]] for t in closed if t["exit_date"] in idx]
    by_year = defaultdict(lambda: [0, 0.0])
    for t in trades:
        by_year[t["entry_date"][:4]][0] += 1
        by_year[t["entry_date"][:4]][1] += t["pnl"]
    return {"trades": len(trades), "closed": len(closed), "open_at_end": len(trades) - len(closed),
            "profit_factor_incl_open": round(gp / gl, 2) if gl else None,
            "win_rate_pct": round(100 * len(wins) / max(len(rs), 1), 1),
            "avg_win_r": round(statistics.mean(wins), 2) if wins else None,
            "avg_loss_r": round(statistics.mean(losses), 2) if losses else None,
            "median_r": round(statistics.median(rs), 2) if rs else None,
            "top10pct_share_of_gross_profit_pct": round(100 * sum(p for p in top if p > 0) / gp, 1) if gp else None,
            "median_days_held": statistics.median(hold) if hold else None, "max_days_held": max(hold) if hold else None,
            "exit_kinds": dict(Counter(t["exit_kind"] for t in trades)),
            "ambiguous_entries": sum(t["ambiguous"] for t in trades),
            "by_entry_year": {y: [c, round(v)] for y, (c, v) in sorted(by_year.items())}}


def split_stats(trades, key):
    vals = [t for t in trades if t[key] is not None]
    if not vals:
        return None
    med = statistics.median(t[key] for t in vals)
    out = {"median": round(med, 4)}
    for name, group in (("below_median", [t for t in vals if t[key] < med]), ("at_or_above", [t for t in vals if t[key] >= med])):
        gp = sum(t["pnl"] for t in group if t["pnl"] > 0)
        gl = -sum(t["pnl"] for t in group if t["pnl"] <= 0)
        out[name] = {"trades": len(group), "pnl": round(sum(t["pnl"] for t in group)),
                     "profit_factor": round(gp / gl, 2) if gl else None,
                     "avg_r": round(statistics.mean(t["r"] for t in group if t["r"] is not None), 3) if group else None}
    return out


def evaluate(events, daily, calendar, spy_curve):
    trades, curve, skipped = portfolio(events, daily, calendar)
    stats = {**curve_stats(curve), "halves_return_pct": halves(curve), **trade_stats(trades, calendar),
             "skipped": dict(skipped), "qualifying_events": len(events)}
    spy = curve_stats(spy_curve)
    checks = {"A1_profit_factor_incl_open_at_least_1.3": (stats["profit_factor_incl_open"] or 0) >= 1.3,
              "A2_profitable_in_both_halves": all(v > 0 for v in stats["halves_return_pct"].values()),
              "A3_max_drawdown_at_most_25pct": stats["max_drawdown_pct"] >= -25.0,
              "B1_drawdown_5pts_smaller_than_spy": stats["max_drawdown_pct"] >= spy["max_drawdown_pct"] + 5,
              "B2_cagr_over_dd_beats_spy": (stats["cagr_over_dd"] or -9) > spy["cagr_over_dd"]}
    return {"portfolio": stats, "checks": checks, "passes": all(checks.values()), "spy": spy}, trades, curve


def main():
    cands, daily, intraday, accepted, spy, edgar = load_all()
    for b in daily.values():
        b["_idx"] = {d: n for n, d in enumerate(b["date"])}
    calendar = [d for d in spy["date"] if d >= START]
    base = spy["close"][spy["date"].index(calendar[0]) - 1]
    spy_curve = [(d, START_CASH * spy["close"][n] / base) for n, d in enumerate(spy["date"]) if d >= START]

    events, reasons, later = build_events(cands, daily, intraday, accepted)
    main_res, trades, curve = evaluate(events, daily, calendar, spy_curve)
    main_res["splits"] = {"prior_3_month_return": split_stats(trades, "prior63"),
                          "dollar_volume": split_stats(trades, "adv_usd")}
    amb = [e for e in events if e["ambiguous"]]
    flip_events, _, _ = build_events(cands, daily, intraday, accepted, flip=True)
    flip_by_key = {(e["symbol"], e["day"]): e for e in flip_events}
    flipped = sum(1 for e in amb if (e["symbol"], e["day"]) in flip_by_key and flip_by_key[(e["symbol"], e["day"])]["ret_pct"] > 0)
    main_res["same_bar_ambiguity"] = {"events": len(events), "ambiguous": len(amb),
                                      "rate_pct": round(100 * len(amb) / max(len(events), 1), 1),
                                      "ambiguous_that_win_if_flipped": flipped}
    info = {}
    for name, kw in (("all_catalysts", {"earnings": False}), ("trail_20_day", {"trail": 20}),
                     ("costs_0.25pct", {"cost": 0.0025}), ("same_bar_flip", {"flip": True})):
        ev = flip_events if name == "same_bar_flip" else build_events(cands, daily, intraday, accepted, **kw)[0]
        res, _, _ = evaluate(ev, daily, calendar, spy_curve)
        info[name] = res
    reason_counts = Counter(reasons.values())
    out = {"plan": "output/EP_EARNINGS_GAP_TEST_PLAN_20261005.md", "first": calendar[0], "last": calendar[-1],
           "candidate_days": sum(len(v) for v in cands.values()), "reasons_main": dict(reason_counts),
           "earnings_8k_later_on_gap_day_not_counted": later, "stocks_without_sec_cik": len(edgar["no_cik"]),
           "main": main_res, "verdict_pass": main_res["passes"], "info": info,
           "trade_list": trades, "curve": [[d, round(v)] for d, v in curve],
           "events_main": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.items()} for e in events],
           "rejected_sample": sorted([[s, d, r] for (s, d), r in reasons.items() if r != "ok"])}
    OUT.write_text(json.dumps(out, default=str) + "\n")
    data_files = [str(OUT_DIR / "candidates.json"), str(OUT_DIR / "edgar_item_202.json")] + \
                 [str(path_for(d)) for d in cands if path_for(d).exists()] + \
                 [str(DATA / f"{s}.csv.gz") for s in sorted(daily)] + [str(DATA / "SPY.csv.gz")]
    write_manifest(OUT, code=["research/ep_test_v1/backtest.py", "research/ep_test_v1/candidates.py",
                              "research/ep_test_v1/fetch_intraday.py", "research/ep_test_v1/fetch_edgar.py"],
                   data=data_files, params={"risk": RISK, "cap": CAP, "cost": COST, "gap": GAP, "vol_mult": VOL_MULT,
                                            "or_end": OR_END, "half_day": HALF_DAY, "trail": TRAIL})
    show = {k: v for k, v in main_res["portfolio"].items() if k not in ("by_entry_year",)}
    print(json.dumps({"reasons": dict(reason_counts), "later_8k": later, "main": show, "checks": main_res["checks"],
                      "spy": main_res["spy"], "splits": main_res["splits"], "ambiguity": main_res["same_bar_ambiguity"],
                      "by_year": main_res["portfolio"]["by_entry_year"],
                      "info": {k: {"final": v["portfolio"]["final"], "cagr": v["portfolio"]["cagr_pct"],
                                   "dd": v["portfolio"]["max_drawdown_pct"], "pf": v["portfolio"]["profit_factor_incl_open"],
                                   "trades": v["portfolio"]["trades"], "passes": v["passes"]} for k, v in info.items()}},
                     indent=1, default=str))
    print("VERDICT", main_res["passes"])


if __name__ == "__main__":
    main()
