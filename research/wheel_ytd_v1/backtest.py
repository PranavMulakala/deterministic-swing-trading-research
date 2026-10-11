"""Backtest of pre-declared test #33: the weekly wheel ("pot 2") on the ten stocks screened as of Dec 31, 2025 -
ten separate $50,000 accounts, Jan 2 - Oct 9, 2026, vs holding each stock. Plan (the spec):
output/WHEEL_YTD_SCREEN_TEST_PLAN_20261011.md. Research only; no orders. Dollars first; no SPY line.

Engine: test #32's code (research/wheel_lite_mu_v1/backtest.py) with test #29's conventions (research/wheel_test_v1/
backtest.py), both imported and NOT modified. Reused unchanged: LMRules (main = test #32 main + skip_earnings=True),
LMSleeve (sell / manage / earnings veto / stuck days), sleeve_report (asserts every opened contract is recorded and
the ledger adds up to the final value), hold_scaled, and test #29's dollar_summary / period_changes / sum_curves.
Nothing is copied from the engine. Added here:
- configuration: the frozen list, the 2026 window, $50k accounts, the four versions, the plan's checks;
- the "typical account" (average and median of the ten accounts, best and worst);
- the RNA delisting (Avidity Biosciences, acquired for $72.00 cash + 0.1 Atrium share per share, effective Feb 27,
  2026; see data.py): the account wheels through Feb 25, 2026 (the last session its stock and options traded as RNA),
  with the engine's end-of-run convention there (an open option valued at its last mid). After that the account is
  cash: shares still held are valued at the Feb 25 close until Feb 27, then converted to $72.00 + 0.1 x Atrium's
  Feb 27 close per share; cash earns T-bills (the engine's rate) through Oct 9. Holding RNA gets the same treatment.
  A second ledger check covers the part after the last session.

  PYTHONPATH=src:. .venv/bin/python -m research.wheel_ytd_v1.backtest     # full run (buys Databento data, $15 stop)
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
from pathlib import Path
import statistics

from research.wheel_lite_mu_v1 import backtest as lb
from research.wheel_test_v1 import backtest as bt
from research.wheel_ytd_v1 import data as yd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/wheel-ytd-test-results.json"
PLAN = yd.PLAN
TICKERS = yd.TICKERS
START, END = yd.START, yd.END
SIZE, SMALL = 50_000.0, 25_000.0
WEEKLY_BAR = 1_000.0          # C1: the average account makes >= $1,000 a week
MIN_PROFITABLE = 7            # C2: at least 7 of the 10 accounts profitable
MAX_MEDIAN_DROP_PCT = -25.0   # C3: the median account's worst drop is at most 25%

MAIN_RULES = lb.LMRules(skip_earnings=True)          # test #32's main rules, earnings skipped
VERSIONS = OrderedDict([                             # name -> (rules, account size)
    ("main", (MAIN_RULES, SIZE)),
    ("with_earnings", (lb.LMRules(), SIZE)),                                   # test #32's main exactly
    ("whole_25k", (lb.LMRules(skip_earnings=True, whole=True), SMALL)),
    ("hold_to_expiry", (lb.LMRules(skip_earnings=True, early_close=False), SIZE)),
])
TOL = 1e-6


def _close_enough(a, b):
    return abs(a - b) < TOL * max(1.0, abs(a), abs(b))


# ---------------------------------------------------------------- the RNA delisting

def after_delisting(cash, shares, last_close, provider, days, last_session, cfg):
    """Continue an account from the day after its last session. cash: cash with any open option already settled at
    its last mid. Shares are valued at last_close until cfg['effective'], then converted to cfg['cash_per_share'] +
    cfg['spinoff_per_share'] x the spin-off's close that day. Cash earns T-bills like the engine (rate of the prior
    day x calendar days / 365). Returns (curve points, ledger)."""
    prev, interest, conv, pts = last_session, 0.0, None, []
    for d in (x for x in days if x > last_session):
        earned = cash * provider.rate(prev) * (d - prev).days / 365
        cash += earned
        interest += earned
        prev = d
        if conv is None and d >= cfg["effective"]:
            spin_close = provider.close(cfg["spinoff_symbol"], d)
            per_share = cfg["cash_per_share"] + cfg["spinoff_per_share"] * spin_close
            conv = {"conversion_day": d.isoformat(), "shares_converted": shares,
                    "cash_per_share": cfg["cash_per_share"], "spinoff_per_share": cfg["spinoff_per_share"],
                    "spinoff_symbol": cfg["spinoff_symbol"], "spinoff_close": spin_close,
                    "value_per_share": per_share, "last_close": last_close,
                    "conversion_gain_vs_last_close": shares * (per_share - last_close)}
            cash += shares * per_share
            shares = 0.0
        pts.append((d, cash + shares * last_close))
    if conv is None:
        raise AssertionError("the delisting's effective date is after the test's last day")
    return pts, {**conv, "interest_after_last_session": interest, "last_session": last_session.isoformat()}


# ---------------------------------------------------------------- one account

def run_account(ticker, rules, size, provider, days, earnings):
    """(sleeve, engine ledger, full-window curve, after-delisting ledger or None). The engine runs on the account's
    days (cut at a delisting); sleeve_report asserts every opened contract is recorded and the ledger adds up."""
    last = yd.account_last_day(ticker, days)
    sub = [d for d in days if d <= last]
    s = lb.LMSleeve(ticker, rules, provider, sub, earnings.get(ticker, ()), size).run()
    ledger = lb.sleeve_report(s, provider)
    curve, after = list(s.curve), None
    if sub[-1] != days[-1]:
        liability = s.trades[-1]["open_liability"] if s.trades and s.trades[-1]["how"] == "open_at_end" else 0.0
        cash0, close_last = s.cash - liability, provider.close(ticker, sub[-1])
        assert _close_enough(cash0 + s.shares * close_last, s.curve[-1][1]), f"{ticker}: value before delisting"
        pts, after = after_delisting(cash0, s.shares, close_last, provider, days, sub[-1], yd.DELISTINGS[ticker])
        after["open_option_settled_at_last_mid"] = liability
        curve += pts
        expect = s.curve[-1][1] + after["conversion_gain_vs_last_close"] + after["interest_after_last_session"]
        assert _close_enough(curve[-1][1], expect), f"{ticker}: after-delisting ledger {expect} != {curve[-1][1]}"
    assert [d for d, _ in curve] == list(days), f"{ticker}: curve does not cover the window"
    return s, ledger, curve, after


def weeks_at_least(curve, start_value, bar=WEEKLY_BAR):
    weeks = bt.period_changes(curve, start_value, lambda d: tuple(d.isocalendar()[:2]))
    return sum(x[2] >= bar for x in weeks)


def account_report(s, ledger, curve, after, size):
    d = bt.dollar_summary(curve, size)
    d.pop("pnl_by_half", None)          # test #29's 2020-2022 / 2023-2026 halves mean nothing in a 2026-only test
    final = curve[-1][1]
    tt = dict(ledger["true_total"])
    tt.pop("equals_total_pnl")
    if after:
        tt["after_delisting_conversion_vs_last_close"] = round(after["conversion_gain_vs_last_close"], 2)
        tt["after_delisting_interest"] = round(after["interest_after_last_session"], 2)
    tt["equals_total_pnl"] = round(final - size, 2)
    assert abs(sum(v for k, v in tt.items() if k != "equals_total_pnl") - tt["equals_total_pnl"]) < 0.01 * len(tt), \
        f"{s.ticker}: true total does not add up {tt}"
    return {
        "ending_value": round(final, 2), "total_pnl": round(final - size, 2),
        "avg_per_week": d["avg_per_week"], "median_per_week": d["median_per_week"], "weeks": d["weeks"],
        "weeks_at_least_1000": weeks_at_least(curve, size),
        "share_of_weeks_at_least_1000_pct": d["share_of_weeks_at_least_1000_pct"],
        "worst_week": d["worst_week"], "worst_month": d["worst_month"],
        "worst_drop_from_high_pct": d["worst_drop_from_high_pct"],
        "worst_drop_from_high_usd": d["worst_drop_from_high_usd"],
        "premiums_collected": ledger["premiums_collected"], "true_total": tt,
        "times_assigned": ledger["times_assigned"], "times_called_away": ledger["times_called_away"],
        "stuck_holding_shares_no_call_allowed": ledger["stuck_holding_shares_no_call_allowed"],
        "contracts_opened": ledger["contracts_opened"], "wheel_last_session": s.days[-1].isoformat(),
        "dollars": d, "ledger": ledger, "after_delisting": after,
    }


# ---------------------------------------------------------------- the typical account and the checks

TYPICAL_METRICS = ("ending_value", "total_pnl", "avg_per_week", "median_per_week", "weeks_at_least_1000",
                   "worst_drop_from_high_pct", "premiums_collected")


def typical(per, metrics=TYPICAL_METRICS):
    """Average and median of the accounts (median of 10 = average of the 5th and 6th), best and worst by P&L."""
    def brief(t):
        v = per[t]
        return {"ticker": t, **{m: v[m] for m in ("ending_value", "total_pnl", "avg_per_week",
                                                   "worst_drop_from_high_pct") if m in v}}
    have = [m for m in metrics if all(m in v for v in per.values())]
    return {"accounts": len(per),
            "average": {m: round(statistics.mean(v[m] for v in per.values()), 2) for m in have},
            "median": {m: round(statistics.median(v[m] for v in per.values()), 2) for m in have},
            "best_account": brief(max(per, key=lambda t: per[t]["total_pnl"])),
            "worst_account": brief(min(per, key=lambda t: per[t]["total_pnl"])),
            "profitable_accounts": sum(v["total_pnl"] > 0 for v in per.values())}


def checks(per):
    """C1 average account >= $1,000/week; C2 >= 7 of 10 profitable; C3 median account worst drop <= 25%."""
    avg_week = statistics.mean(v["avg_per_week"] for v in per.values())
    profitable = [t for t, v in per.items() if v["total_pnl"] > 0]
    median_drop = statistics.median(v["worst_drop_from_high_pct"] for v in per.values())
    c = {"C1_average_account_at_least_1000_per_week": avg_week >= WEEKLY_BAR,
         "C2_at_least_7_of_10_profitable": len(profitable) >= MIN_PROFITABLE,
         "C3_median_account_worst_drop_at_most_25pct": median_drop >= MAX_MEDIAN_DROP_PCT}
    verdict = "PASS" if all(c.values()) else "FAIL"
    held = lambda k: "held" if c[k] else "missed"
    words = (f"{verdict}. C1 {held('C1_average_account_at_least_1000_per_week')}: the average $50k account made "
             f"${avg_week:,.0f} a week (bar $1,000). C2 {held('C2_at_least_7_of_10_profitable')}: "
             f"{len(profitable)} of {len(per)} accounts profitable (bar 7). "
             f"C3 {held('C3_median_account_worst_drop_at_most_25pct')}: the median account's worst drop was "
             f"{-median_drop:.1f}% (bar 25%).")
    detail = {"average_account_avg_per_week": round(avg_week, 2), "profitable_accounts": profitable,
              "median_worst_drop_pct": round(median_drop, 2),
              "worst_drop_by_account_pct": {t: v["worst_drop_from_high_pct"] for t, v in per.items()}}
    return c, detail, verdict, words


# ---------------------------------------------------------------- versions, holding, run

def iso_curve(curve):
    return lb.iso_curve(curve)


def run_version(name, provider, days, earnings, tickers=TICKERS):
    rules, size = VERSIONS[name]
    with ThreadPoolExecutor(max_workers=len(tickers)) as pool:
        runs = list(pool.map(lambda t: run_account(t, rules, size, provider, days, earnings), tickers))
    per = OrderedDict((s.ticker, account_report(s, led, curve, after, size)) for s, led, curve, after in runs)
    return {"rules": asdict(rules), "account_size": size, "per_account": per, "typical_account": typical(per),
            "trades": [x for s, *_ in runs for x in s.trades],
            "curves": {s.ticker: iso_curve(curve) for s, _, curve, _ in runs}}


def run_all(provider, days, earnings, names, log=print, tickers=TICKERS):
    results = OrderedDict()
    if "main" in names:   # main first, so the $15 hard stop can only ever cut an information version short
        results["main"] = run_version("main", provider, days, earnings, tickers)
        log(json.dumps({"version_done": "main", "databento_spent_total": round(provider.db.spent, 4)}))
    rest = [n for n in names if n != "main"]
    if rest:
        with ThreadPoolExecutor(max_workers=len(rest)) as pool:
            results.update(zip(rest, pool.map(lambda n: run_version(n, provider, days, earnings, tickers), rest)))
        log(json.dumps({"versions_done": rest, "databento_spent_total": round(provider.db.spent, 4)}))
    return results


class EntrySpot:
    """Provider proxy that answers one (ticker, day) 15:45 price from a fallback; everything else is delegated."""

    def __init__(self, base, ticker, day, price):
        self.base, self.ticker, self.day, self.price = base, ticker, day, price

    def spot(self, t, d):
        return self.price if (t, d) == (self.ticker, self.day) else self.base.spot(t, d)

    def __getattr__(self, name):
        return getattr(self.base, name)


def hold_account(ticker, provider, days, size=SIZE, spot_before=None):
    """$50k of the stock at the Jan 2, 2026 15:45 price (test #29's hold, scaled), with the delisting treatment. If
    the stock has no 15:45 bar that day, the entry is the close of the last 1-minute bar before 15:45 (recorded)."""
    last = yd.account_last_day(ticker, days)
    sub = [d for d in days if d <= last]
    entry_source = "open of the 15:45 SIP 1-minute bar"
    if provider.spot(ticker, sub[0]) is None:
        fb = (spot_before or yd.fetch_spot_before)(ticker, sub[0])
        provider = EntrySpot(provider, ticker, sub[0], fb["price"])
        entry_source = f"no 15:45 bar; {fb['rule']} (bar starting {fb['bar_start_utc']})"
    h = lb.hold_scaled(ticker, provider, sub, size)
    curve, after = list(h["curve"]), None
    if sub[-1] != days[-1]:
        close_last = provider.close(ticker, sub[-1])
        cash0 = h["final_value"] - h["shares_end"] * close_last
        pts, after = after_delisting(cash0, h["shares_end"], close_last, provider, days, sub[-1],
                                     yd.DELISTINGS[ticker])
        curve += pts
        cfg = yd.DELISTINGS[ticker]
        spin_shares = h["shares_end"] * cfg["spinoff_per_share"]
        after["info_keeping_the_spinoff_shares_to_the_end_instead_usd"] = round(
            spin_shares * (provider.close(cfg["spinoff_symbol"], days[-1]) - after["spinoff_close"]), 2)
        expect = h["final_value"] + after["conversion_gain_vs_last_close"] + after["interest_after_last_session"]
        assert _close_enough(curve[-1][1], expect), f"{ticker}: holding after-delisting ledger"
    d = bt.dollar_summary(curve, size)
    d.pop("pnl_by_half", None)
    return {"ending_value": round(curve[-1][1], 2), "total_pnl": round(curve[-1][1] - size, 2),
            "avg_per_week": d["avg_per_week"], "median_per_week": d["median_per_week"],
            "weeks_at_least_1000": weeks_at_least(curve, size),
            "worst_week": d["worst_week"], "worst_month": d["worst_month"],
            "worst_drop_from_high_pct": d["worst_drop_from_high_pct"],
            "worst_drop_from_high_usd": d["worst_drop_from_high_usd"],
            "entry_price_1545": h["entry_price"], "entry_price_source": entry_source,
            "shares_at_end_of_stock": h["shares_end"],
            "dividends": round(h["dividends"], 2), "interest_before_delisting": round(h["interest"], 2),
            "after_delisting": after, "dollars": d}, curve


def run_holding(provider, days, tickers=TICKERS, size=SIZE):
    per, curves = OrderedDict(), {}
    for t in tickers:
        per[t], c = hold_account(t, provider, days, size)
        curves[t] = iso_curve(c)
    return {"account_size": size, "per_account": per, "typical_account": typical(per), "curves": curves}


def splits_agree(audit, provider):
    """Every forward split in the window (from the all-types file) is in the engine's split list, and vice versa."""
    want = {(r["symbol"], r["day"]) for r in audit["handled_by_engine"] if r["type"] == "forward_splits"}
    have = {(t, d.isoformat()) for t in TICKERS for d in provider.splits(t) if START <= d <= END}
    if want != have:
        raise RuntimeError(f"forward splits disagree: all-types file {sorted(want)} vs engine {sorted(have)}")
    return sorted(have)


def main():
    from research.provenance_v1.provenance import write_manifest
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default=str(OUT))
    ap.add_argument("--versions", default=",".join(VERSIONS))
    args = ap.parse_args()
    names = args.versions.split(",")
    unknown = [n for n in names if n not in VERSIONS]
    if unknown:
        raise SystemExit(f"unknown versions {unknown}")
    provider = yd.make_provider()
    days = yd.window_days(provider)
    if (days[0], days[-1]) != (START, END):
        raise SystemExit(f"window is {days[0]}..{days[-1]}, plan says {START}..{END}")
    ca = yd.fetch_all_corporate_actions()
    yd.check_delisting(ca)
    audit = yd.audit_corporate_actions(ca)
    if audit["flagged"]:
        raise SystemExit("unhandled corporate actions: " + json.dumps(audit["flagged"], default=str))
    splits = splits_agree(audit, provider)
    sessions, coverage, cal = yd.earnings(days)
    results = run_all(provider, days, sessions, names, log=lambda s: print(s, flush=True))
    holding = run_holding(provider, days)
    out = {"plan": PLAN, "first": days[0].isoformat(), "last": days[-1].isoformat(), "trading_days": len(days),
           "account_size": SIZE, "tickers": list(TICKERS),
           "frozen_list": [dict(zip(("ticker", "name_in_plan", "price_dec31_2025", "return_2025_pct",
                                     "volatility_pct"), r)) for r in yd.FROZEN]}
    if "main" in results:
        main_per = results["main"]["per_account"]
        for t, v in main_per.items():
            h = holding["per_account"][t]
            v["holding_same_stock"] = {k: h[k] for k in ("ending_value", "total_pnl", "avg_per_week",
                                                         "worst_drop_from_high_pct")}
        c, detail, verdict, words = checks(main_per)
        out.update({"checks": c, "check_detail": detail, "verdict": verdict, "verdict_in_words": words,
                    "typical_account": results["main"]["typical_account"]})
    out["holding"] = holding
    out["versions"] = results
    out["earnings_sessions"] = {t: [d.isoformat() for d in v] for t, v in sessions.items()}
    out["earnings_coverage"] = coverage
    out["edgar_time_base"] = cal
    out["corporate_actions"] = {"engine_forward_splits": splits, "audit": audit,
                                "delistings": {t: {k: (v.isoformat() if hasattr(v, "isoformat") else v)
                                                   for k, v in cfg.items()} for t, cfg in yd.DELISTINGS.items()}}
    out["databento_spent_total_dollars"] = round(provider.db.spent, 4)
    Path(args.output).write_text(json.dumps(out, indent=1, default=str) + "\n")
    data_files = sorted(str(p) for p in yd.DATA.rglob("*") if p.is_file() and not p.name.endswith(".tmp")
                        and p.name not in ("databento_ledger.csv", "databento_spent.json"))
    write_manifest(args.output,
                   code=["research/wheel_ytd_v1/backtest.py", "research/wheel_ytd_v1/data.py",
                         "research/wheel_lite_mu_v1/backtest.py", "research/wheel_lite_mu_v1/data.py",
                         "research/wheel_test_v1/backtest.py", "research/wheel_test_v1/data.py",
                         "research/ep_test_v1/fetch_edgar.py", "research/spy_put_spread_backtest_v1/backtest.py",
                         "research/cc_spy_test_v1/backtest.py", PLAN],
                   data=data_files + ["research/spy_put_spread_backtest_v1/tbill_3m_monthly.csv"],
                   params={"versions": {k: {"rules": asdict(r), "account_size": s} for k, (r, s) in VERSIONS.items()},
                           "fee": bt.FEE, "start": START.isoformat(), "end": END.isoformat(),
                           "expiration_band": bt.EXP_BAND, "expiration_fallback": bt.EXP_FALLBACK,
                           "weekly_bar": WEEKLY_BAR, "min_profitable": MIN_PROFITABLE,
                           "max_median_drop_pct": MAX_MEDIAN_DROP_PCT, "databento_budget": yd.BUDGET})
    print(json.dumps({"verdict": out.get("verdict"), "spent": out["databento_spent_total_dollars"]}), flush=True)


if __name__ == "__main__":
    main()
