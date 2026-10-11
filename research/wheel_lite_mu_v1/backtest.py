"""Backtest of pre-declared test #32: the weekly wheel on LITE and MU (0.30 delta, ~7 days, buy back at 50% of the
sale price, calls never below the assignment price), two $100,000 accounts, Jan 2, 2020 - Oct 9, 2026, vs holding.
Plan (the spec): output/WHEEL_LITE_MU_TEST_PLAN_20261010.md. Research only; no orders. Dollars first; no SPY line.

Engine: test #29's code (research/wheel_test_v1/backtest.py, committed in ef5e22b) is imported and NOT modified.
Reused unchanged: Rules (subclassed, new defaults), Sleeve.__init__/run/record/window_end/settle_day/next_day,
choose_expiration, pick_contract, bs_delta, contracts_for, settle, hold (scaled linearly to $100k), dollar_summary,
sum_curves, drawdown. Copied into this file because the engine hard-codes them (noted at each one):
- Sleeve.manage: the engine's buyback threshold is the module constant TAKE = 0.25; here it is rules.take (0.50).
- Sleeve.sell: two additions only, (a) a day when a call exists in the delta band but none at/above the assignment
  price is counted as "no_call_at_or_above_basis" (rule 6 "stuck" days), (b) the skip_earnings veto.
- sleeve_report / combine: the engine's ledger check uses the module constant SLEEVE = 40,000; here the account size.
A unit test runs this subclass with test #29's settings and checks it reproduces the engine's trades exactly.

  PYTHONPATH=src:. .venv/bin/python -m research.wheel_lite_mu_v1.backtest     # full run (buys Databento data, $12 stop)
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date
import json
import math
from pathlib import Path
import statistics

from research.wheel_test_v1 import backtest as bt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/wheel-lite-mu-test-results.json"
PLAN = "output/WHEEL_LITE_MU_TEST_PLAN_20261010.md"
TICKERS = ("LITE", "MU")
START, END = date(2020, 1, 2), date(2026, 10, 9)
RECENT = date(2025, 1, 2)
SIZE = 100_000.0
WEEKLY_BAR = 1_000.0
MAX_DROP_PCT = -25.0
EPS = bt.EPS
HALVES = bt.HALVES          # ("2020-2022", 2020-01-01..2022-12-31), ("2023-2026", 2023-01-01..2026-10-09)
assert bt.START == START and bt.END == END, "test #29 engine dates changed"


@dataclass(frozen=True)
class LMRules(bt.Rules):
    """test #29's Rules with this plan's defaults, plus the buyback level and the earnings switch."""
    target: float = 0.30
    band: tuple = (0.25, 0.35)
    early_close: bool = True
    basis_floor: bool = True     # rule 6: calls only at or above the price paid for the shares
    whole: bool = False
    take: float = 0.50           # rule 4: buy back when the ask is at or below 50% of the sale price
    skip_earnings: bool = False


VERSIONS = OrderedDict([
    ("main", LMRules()),
    ("no_basis_floor", LMRules(basis_floor=False)),
    ("delta_20", LMRules(target=0.20, band=(0.15, 0.25))),
    ("hold_to_expiry", LMRules(early_close=False)),
    ("skip_earnings", LMRules(skip_earnings=True)),
    ("whole_contracts", LMRules(whole=True)),
])


def early_label(take):
    """0.25 -> 'closed_early_75pct' (test #29's label), 0.50 -> 'closed_early_50pct'."""
    return f"closed_early_{round(100 * (1 - take))}pct"


class LMSleeve(bt.Sleeve):
    """One account. earnings: sorted earnings sessions (data.earnings_session) used only when rules.skip_earnings."""

    def __init__(self, ticker, rules, provider, days, earnings=(), size=SIZE):
        super().__init__(ticker, rules, provider, days)
        self.size = self.cash = float(size)
        self.earnings = sorted(earnings)
        self.label = early_label(rules.take)
        self.opened = 0
        self.blocked_days = []          # shares held, a call in the delta band existed, none at/above the basis

    def earnings_in_life(self, sale_day, expiration):
        """True if an earnings session falls on any day from the sale day through expiration (both included)."""
        i = bisect.bisect_left(self.earnings, sale_day)
        return i < len(self.earnings) and self.earnings[i] <= expiration

    # Copy of bt.Sleeve.sell (ef5e22b) with the two additions marked "ADDED".
    def sell(self, d):
        spot = self.p.spot(self.ticker, d)
        if spot is None:
            self.skips["no_1545_stock_price"] += 1
            return False
        kind = "C" if self.shares > EPS else "P"
        if kind == "P" and self.rules.whole and math.floor(self.cash / (0.70 * spot * 100) + EPS) < 1:
            self.skips["cannot_afford_one_contract"] += 1
            return False
        if kind == "C" and self.rules.whole and math.floor(self.shares / 100 + EPS) < 1:
            self.skips["fewer_than_100_shares"] += 1
            return False
        chain = self.p.chain(self.ticker, d, spot)
        if not chain:
            self.skips["no_chain_quotes"] += 1
            return False
        floor = self.basis if (kind == "C" and self.rules.basis_floor) else None
        pick, why = bt.pick_contract(chain, d, kind, spot, self.p.rate(d), self.rules, floor)
        if pick is None:
            # ADDED (a): name the rule-6 day: a call in the band exists, but none at or above the price paid
            if floor is not None and why == "no_strike_in_delta_band" and \
                    bt.pick_contract(chain, d, kind, spot, self.p.rate(d), self.rules, None)[0] is not None:
                why = "no_call_at_or_above_basis"
                self.blocked_days.append(d)
            self.skips[why] += 1
            return False
        # ADDED (b): skip_earnings never sells a contract whose life (sale day .. expiration) has an earnings session
        if self.rules.skip_earnings and self.earnings_in_life(d, pick["expiration"]):
            self.skips["contract_life_includes_earnings"] += 1
            return False
        n = bt.contracts_for(self.rules, kind, self.cash, self.shares, pick["strike"])
        if n <= 0:
            self.skips["cannot_afford_one_contract"] += 1
            return False
        last, why_end = self.window_end(d, pick["expiration"])
        quotes = self.p.quotes(self.ticker, kind, pick["expiration"], pick["strike"], d, last)
        premium, fees = n * 100 * pick["bid"], n * bt.FEE
        self.cash += premium - fees
        self.opt = {**pick, "n": n, "sale_day": d, "spot": spot, "sale_price": pick["bid"], "premium": premium,
                    "sale_fees": fees, "last_day": last, "end_reason": why_end, "quotes": quotes, "qi": 0,
                    "mark": (pick["bid"] + pick["ask"]) / 2, "mark_day": d}
        self.opened += 1
        if not quotes:
            self.flags["contract_with_no_quotes"] += 1
        return True

    # Copy of bt.Sleeve.manage (ef5e22b); the only change: rules.take instead of the constant TAKE, and the label.
    def manage(self, d, close):
        o = self.opt
        quotes = o["quotes"]
        while o["qi"] < len(quotes) and quotes[o["qi"]][0].date() <= d:
            ts, bid, ask = quotes[o["qi"]]
            o["qi"] += 1
            if ts.date() < d:
                continue
            if self.rules.early_close and 0 < ask <= self.rules.take * o["sale_price"] + EPS:
                self.record(d, self.label, ask, ts)
                self.resell_from = d if ts.time() < bt.DECIDE else self.next_day(d)
                return
            if ask > 0 and ask >= bid:
                o["mark"], o["mark_day"] = (bid + ask) / 2, d
        if d != o["last_day"] or o["end_reason"] == "end_of_test":
            return
        if o["end_reason"] == "split":
            if o["mark_day"] != d:
                self.flags["split_close_used_stale_mid"] += 1
            self.record(d, "closed_before_split_at_mid", o["mark"], None)
            self.resell_from = self.next_day(d)
            return
        how = bt.settle(o["kind"], o["strike"], close)
        n, k = o["n"], o["strike"]
        share_cash = 0.0
        if how == "assigned":
            share_cash = -n * 100 * k
            self.shares += n * 100
            self.basis = k
        elif how == "called_away":
            share_cash = n * 100 * k
            self.shares -= n * 100
            if abs(self.shares) < 1e-7:
                self.shares, self.basis = 0.0, None
        self.cash += share_cash
        self.record(d, how, 0.0, None, close_cash=0.0, fee=False, share_cash=share_cash, settle_close=close)
        self.resell_from = self.next_day(d)


# ---------------------------------------------------------------- reporting (dollars first)

def outcome_keys(label):
    return (label, "expired_worthless", "assigned", "called_away", "closed_before_split_at_mid", "open_at_end")


def stuck_summary(s):
    """Rule 6: days/weeks with shares held and no call allowed (a call existed in the band, none at/above basis)."""
    days = s.blocked_days
    weeks = {tuple(d.isocalendar()[:2]) for d in days}
    longest = run = 0
    prev = None
    for d in days:
        run = run + 1 if prev is not None and s.index[d] == s.index[prev] + 1 else 1
        longest, prev = max(longest, run), d
    return {"days_no_call_allowed": len(days), "weeks_stuck_no_call_allowed": len(weeks),
            "longest_stuck_stretch_trading_days": longest,
            "first_day": days[0].isoformat() if days else None, "last_day": days[-1].isoformat() if days else None}


def sleeve_report(s, provider):
    """Copy of bt.sleeve_report (account size instead of the constant SLEEVE) plus the opened-contract count and the
    stuck days. Asserts every opened contract is recorded and the ledger adds up to the final value."""
    t = s.trades
    end, close = s.days[-1], provider.close(s.ticker, s.days[-1])
    final = s.curve[-1][1]
    assert s.opened == len(t), f"{s.ticker}: {s.opened} contracts opened but {len(t)} recorded"
    assert all(x["how"] != "open_at_end" for x in t[:-1]), "open_at_end must be last"
    assert (s.opt is None), f"{s.ticker}: an option is still open after the run"
    option_net = sum(x["option_pnl"] for x in t)
    share_pnl = sum(x["share_cash"] for x in t) + s.shares * close
    from_trades = s.size + option_net + share_pnl + s.dividends + s.interest
    assert abs(from_trades - final) < 1e-6 * max(1.0, abs(final)), f"{s.ticker}: ledger {from_trades} != value {final}"
    later = {}
    for x in t:
        if x["how"] == "called_away":
            d = date.fromisoformat(x["end_day"])
            later[id(x)] = close * math.prod(r for ex, r in s.split_ratio.items() if d < ex <= end)
    counts = Counter(x["how"] for x in t)
    n = max(len(t), 1)
    premiums = sum(x["premium"] for x in t)
    sale_fees = sum(x["sale_fees"] for x in t)
    buybacks = sum(x["close_cost"] + x["close_fees"] for x in t)
    open_mid = sum(x["open_liability"] for x in t)
    return {
        "final_value": round(final, 2), "total_pnl": round(final - s.size, 2),
        "premiums_collected": round(premiums, 2),
        "true_total": {   # premiums - fees - buybacks - open option + share gains/losses + dividends + interest
            "premiums_collected": round(premiums, 2), "minus_sale_fees": round(-sale_fees, 2),
            "minus_buybacks_incl_fees": round(-buybacks, 2), "minus_open_option_at_mid": round(-open_mid, 2),
            "share_gains_and_losses": round(share_pnl, 2), "dividends": round(s.dividends, 2),
            "interest": round(s.interest, 2), "equals_total_pnl": round(final - s.size, 2)},
        "sale_fees": round(sale_fees, 2), "buybacks_incl_fees": round(buybacks, 2),
        "open_option_at_mid": round(open_mid, 2), "option_net": round(option_net, 2), "share_pnl": round(share_pnl, 2),
        "dividends": round(s.dividends, 2), "interest": round(s.interest, 2),
        "contracts_opened": s.opened, "contracts_sold": len(t), "puts_sold": sum(x["kind"] == "P" for x in t),
        "calls_sold": sum(x["kind"] == "C" for x in t),
        "times_assigned": counts["assigned"], "times_called_away": counts["called_away"],
        "stuck_holding_shares_no_call_allowed": stuck_summary(s),
        "given_up_when_called_away_vs_expiration_close": round(sum(
            (x["settle_close"] - x["strike"]) * x["contracts"] * 100 for x in t if x["how"] == "called_away"), 2),
        "given_up_when_called_away_vs_oct9_2026_price": round(sum(
            max(later[id(x)] - x["strike"], 0.0) * x["contracts"] * 100 for x in t if x["how"] == "called_away"), 2),
        "outcomes": dict(counts),
        "hit_rates_pct": {k: round(100 * counts[k] / n, 1) for k in outcome_keys(s.label)},
        "fallback_expirations": sum(x["fallback_expiration"] for x in t),
        "shares_at_end": s.shares, "cash_at_end": round(s.cash, 2),
        "skipped_days": dict(s.skips), "flags": dict(s.flags),
        "median_delta": statistics.median(abs(x["delta"]) for x in t) if t else None,
        "median_days_to_expiration": statistics.median(
            (date.fromisoformat(x["expiration"]) - date.fromisoformat(x["sale_day"])).days for x in t) if t else None,
    }


def combine(per_account, label):
    keys = ("premiums_collected", "sale_fees", "buybacks_incl_fees", "open_option_at_mid", "option_net", "share_pnl",
            "dividends", "interest", "contracts_sold", "times_assigned", "times_called_away",
            "given_up_when_called_away_vs_expiration_close", "given_up_when_called_away_vs_oct9_2026_price",
            "fallback_expirations")
    out = {k: round(sum(v[k] for v in per_account.values()), 2) for k in keys}
    out["true_total"] = {k: round(sum(v["true_total"][k] for v in per_account.values()), 2)
                         for k in next(iter(per_account.values()))["true_total"]}
    for k in ("days_no_call_allowed", "weeks_stuck_no_call_allowed"):
        out[k] = sum(v["stuck_holding_shares_no_call_allowed"][k] for v in per_account.values())
    counts = Counter()
    for v in per_account.values():
        counts.update(v["outcomes"])
    n = max(sum(counts.values()), 1)
    out["outcomes"] = dict(counts)
    out["hit_rates_pct"] = {k: round(100 * counts[k] / n, 1) for k in outcome_keys(label)}
    return out


def slice_summary(curve, first):
    """Dollar summary of a curve from `first` on, measured from the value at the last day before it."""
    before = [v for d, v in curve if d < first]
    part = [(d, v) for d, v in curve if d >= first]
    if not before or not part:
        return None
    return {"account_value_at_start": round(before[-1], 2), **bt.dollar_summary(part, before[-1])}


def iso_curve(curve):
    return [[d.isoformat(), round(v, 2)] for d, v in curve]


def run_sleeves(rules, provider, days, earnings, tickers=TICKERS, size=SIZE):
    with ThreadPoolExecutor(max_workers=len(tickers)) as pool:
        return list(pool.map(lambda tk: LMSleeve(tk, rules, provider, days, earnings.get(tk, ()), size).run(),
                             tickers))


def report_sleeves(rules, sleeves, provider, size=SIZE, recent=RECENT):
    label = early_label(rules.take)
    per = OrderedDict()
    for s in sleeves:
        per[s.ticker] = {"dollars": bt.dollar_summary(s.curve, size), "ledger": sleeve_report(s, provider),
                         "recent_view_slice": slice_summary(s.curve, recent)}
    curve = bt.sum_curves([s.curve for s in sleeves])
    combined = {"dollars": bt.dollar_summary(curve, size * len(sleeves)),
                "ledger": combine({k: v["ledger"] for k, v in per.items()}, label),
                "recent_view_slice": slice_summary(curve, recent)}
    return {"rules": asdict(rules), "per_account": per, "combined": combined,
            "trades": [x for s in sleeves for x in s.trades],
            "curves": {s.ticker: iso_curve(s.curve) for s in sleeves}, "combined_curve": iso_curve(curve)}


def run_version(name, provider, days, earnings, tickers=TICKERS):
    rules = VERSIONS[name]
    return report_sleeves(rules, run_sleeves(rules, provider, days, earnings, tickers), provider)


def hold_scaled(ticker, provider, days, size=SIZE):
    """test #29's hold() at $40,000, scaled to `size` (everything in it is proportional to the starting amount)."""
    h = bt.hold(ticker, provider, days)
    f = size / bt.SLEEVE
    return {"curve": [(d, v * f) for d, v in h["curve"]], "shares_end": h["shares_end"] * f,
            "entry_price": h["entry_price"], "dividends": h["dividends"] * f, "interest": h["interest"] * f,
            "share_pnl": h["share_pnl"] * f, "final_value": h["final_value"] * f}


def run_holding(provider, days, tickers=TICKERS, size=SIZE, recent=RECENT):
    held = {t: hold_scaled(t, provider, days, size) for t in tickers}
    per = OrderedDict()
    for t, h in held.items():
        per[t] = {"dollars": bt.dollar_summary(h["curve"], size),
                  "ledger": {"final_value": round(h["final_value"], 2), "total_pnl": round(h["final_value"] - size, 2),
                             "share_pnl": round(h["share_pnl"], 2), "dividends": round(h["dividends"], 2),
                             "interest": round(h["interest"], 2), "entry_price_1545": h["entry_price"],
                             "shares_at_end": h["shares_end"]},
                  "recent_view_slice": slice_summary(h["curve"], recent)}
    curve = bt.sum_curves([h["curve"] for h in held.values()])
    return {"per_account": per, "combined": {"dollars": bt.dollar_summary(curve, size * len(tickers)),
                                             "recent_view_slice": slice_summary(curve, recent)},
            "curves": {t: iso_curve(h["curve"]) for t, h in held.items()}}


def checks(main):
    """C1 combined avg >= $1,000/week; C2 each account profitable in both halves; C3 each account worst drop <= 25%."""
    comb = main["combined"]["dollars"]
    per = {t: v["dollars"] for t, v in main["per_account"].items()}
    c2 = {t: all(v is not None and v > 0 for v in d["pnl_by_half"].values()) for t, d in per.items()}
    c3 = {t: d["worst_drop_from_high_pct"] >= MAX_DROP_PCT for t, d in per.items()}
    c = {"C1_combined_avg_at_least_1000_per_week": comb["avg_per_week"] >= WEEKLY_BAR,
         "C2_each_account_profitable_in_both_halves": all(c2.values()),
         "C3_each_account_worst_drop_at_most_25pct": all(c3.values())}
    verdict = "PASS" if all(c.values()) else "FAIL"
    words = [f"C1 {'held' if c['C1_combined_avg_at_least_1000_per_week'] else 'missed'}: the two accounts together "
             f"averaged ${comb['avg_per_week']:,.0f} a week (bar $1,000)."]
    for t, d in per.items():
        halves = ", ".join(f"{k} ${v:,.0f}" if v is not None else f"{k} n/a" for k, v in d["pnl_by_half"].items())
        words.append(f"{t}: C2 {'held' if c2[t] else 'missed'} ({halves}); C3 {'held' if c3[t] else 'missed'} "
                     f"(worst drop {d['worst_drop_from_high_pct']:.1f}%, ${d['worst_drop_from_high_usd']:,.0f}).")
    detail = {"C2_by_account": c2, "C3_by_account": c3}
    return c, detail, verdict, f"{verdict}. " + " ".join(words)


def run_all(provider, days, earnings, names, log=print):
    results = OrderedDict()
    if "main" in names:   # main first, so the $12 hard stop can only ever cut an information version short
        results["main"] = run_version("main", provider, days, earnings)
        log(json.dumps({"version_done": "main", "databento_spent_total": round(provider.db.spent, 4)}))
    rest = [n for n in names if n != "main"]
    if rest:
        with ThreadPoolExecutor(max_workers=len(rest)) as pool:
            results.update(zip(rest, pool.map(lambda n: run_version(n, provider, days, earnings), rest)))
        log(json.dumps({"versions_done": rest, "databento_spent_total": round(provider.db.spent, 4)}))
    return results


def recent_fresh(provider, days, earnings, first=RECENT):
    """Information: main rules started fresh with $100,000 per account on Jan 2, 2025 (and holding from then)."""
    sub = [d for d in days if d >= first]
    rules = VERSIONS["main"]
    out = report_sleeves(rules, run_sleeves(rules, provider, sub, earnings), provider, recent=first)
    for part in [out["combined"], *out["per_account"].values()]:
        part.pop("recent_view_slice", None)
    hold = run_holding(provider, sub, recent=first)
    for part in [hold["combined"], *hold["per_account"].values()]:
        part.pop("recent_view_slice", None)
    return {"first": sub[0].isoformat(), "last": sub[-1].isoformat(), "main_rules": out, "holding": hold}


def main():
    from research.provenance_v1.provenance import write_manifest
    from research.wheel_lite_mu_v1 import data as lm
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default=str(OUT))
    ap.add_argument("--versions", default=",".join(VERSIONS))
    ap.add_argument("--no-recent-fresh", action="store_true", help="skip the fresh Jan 2, 2025 information run")
    args = ap.parse_args()
    provider = lm.make_provider()
    days = provider.trading_days(START, END)
    rows = {t: lm.fetch_earnings(t) for t in TICKERS}
    cal = lm.calibrate()
    earnings = {t: lm.earnings_sessions(r, days, cal["shifted"]) for t, r in rows.items()}
    other_reading_changes = {t: lm.changed_sessions(r, days, cal["shifted"]) for t, r in rows.items()}
    names = args.versions.split(",")
    unknown = [n for n in names if n not in VERSIONS]
    if unknown:
        raise SystemExit(f"unknown versions {unknown}")
    results = run_all(provider, days, earnings, names, log=lambda s: print(s, flush=True))
    holding = run_holding(provider, days)
    out = {"plan": PLAN, "first": days[0].isoformat(), "last": days[-1].isoformat(), "trading_days": len(days),
           "account_size": SIZE, "tickers": list(TICKERS)}
    if "main" in results:
        c, detail, verdict, words = checks(results["main"])
        out.update({"checks": c, "check_detail": detail, "verdict": verdict, "verdict_in_words": words})
    out["holding"] = holding
    out["versions"] = results
    if not args.no_recent_fresh:
        out["recent_view_fresh_start"] = recent_fresh(provider, days, earnings)
        print(json.dumps({"recent_fresh_done": True, "databento_spent_total": round(provider.db.spent, 4)}), flush=True)
    out["earnings_sessions"] = {t: [d.isoformat() for d in v] for t, v in earnings.items()}
    out["earnings_filings"] = rows
    out["edgar_time_base"] = {**cal, "filings_whose_session_differs_under_the_other_reading": other_reading_changes}
    out["databento_spent_total_dollars"] = round(provider.db.spent, 4)
    Path(args.output).write_text(json.dumps(out, indent=1, default=str) + "\n")
    data_files = sorted(str(p) for p in lm.DATA.rglob("*") if p.is_file() and not p.name.endswith(".tmp")
                        and p.name not in ("databento_ledger.csv", "databento_spent.json"))
    write_manifest(args.output,
                   code=["research/wheel_lite_mu_v1/backtest.py", "research/wheel_lite_mu_v1/data.py",
                         "research/wheel_test_v1/backtest.py", "research/wheel_test_v1/data.py",
                         "research/ep_test_v1/fetch_edgar.py", "research/spy_put_spread_backtest_v1/backtest.py",
                         "research/cc_spy_test_v1/backtest.py"],
                   data=data_files + ["research/spy_put_spread_backtest_v1/tbill_3m_monthly.csv"],
                   params={"versions": {k: asdict(v) for k, v in VERSIONS.items()}, "fee": bt.FEE, "account_size": SIZE,
                           "start": START.isoformat(), "end": END.isoformat(), "recent_view_from": RECENT.isoformat(),
                           "expiration_band": bt.EXP_BAND, "expiration_fallback": bt.EXP_FALLBACK,
                           "weekly_bar": WEEKLY_BAR, "max_drop_pct": MAX_DROP_PCT, "databento_budget": lm.BUDGET})
    print(json.dumps({"verdict": out.get("verdict"), "spent": out["databento_spent_total_dollars"]}), flush=True)


if __name__ == "__main__":
    main()
