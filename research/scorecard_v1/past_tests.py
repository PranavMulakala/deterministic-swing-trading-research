"""Dollars-first scorecards for the strategies already tested (owner's request, Oct 7, 2026). Re-reads each test's saved
daily account values (or rebuilds them with the test's own committed code) and reports money per week, $1,000 weeks,
the worst week and month, and what SPY made over the same dates. Nothing here changes any test's verdict.

  PYTHONPATH=src:. .venv/bin/python -m research.scorecard_v1.past_tests
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from research.scorecard_v1.scorecard import load_spy, scorecard, spy_curve

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/dollars-first-scorecards-20261007.json"
POST_COVID = "2020-01-02"


def j(path):
    p = ROOT / path
    if p.suffix == ".gz":
        with gzip.open(p, "rt") as f:
            return json.load(f)
    return json.loads(p.read_text())


def since(curve, first=POST_COVID, money=100_000.0):
    """The part of a curve from `first`, rescaled so the account holds `money` just before it (every test then starts
    2020 with the same $100,000)."""
    before = [v for d, v in curve if d < first]
    part = [(d, v) for d, v in curve if d >= first]
    base = before[-1] if before else part[0][1]
    return [(d, v * money / base) for d, v in part], money


def plan_b_lite():
    """The Plan B LITE dip rule's replay ($60,000 per buy, one position at a time): P&L on $60,000."""
    from research.lite_dip_history_v1.run import FIRST, LAST, PAPER, cached, fetch, history, regular, replay
    from research.lite_paper_bot_v1.bot import credentials, evaluate, mornings
    key, secret = credentials()
    calendar = cached(f"calendar_{FIRST}_{LAST}.json.gz",
                      lambda: fetch(f"{PAPER}/v2/calendar?start={FIRST}&end={LAST}", key, secret))
    closes = {row["date"]: row["close"] for row in calendar if row["open"] == "09:30"}
    days = sorted(closes)
    sip = regular(history("sip", key, secret, "LITE", FIRST, LAST), closes)
    signals = {d: evaluate(b, []) for d, b in mornings(history("iex", key, secret, "LITE", FIRST, LAST)).items()
               if d in closes}
    out = {}
    for name, a, b in (("2025 to Sep 2026 (the boom)", "2025-01-01", LAST), ("2022-2024 (the bust)", "2022-01-01", "2024-12-31")):
        window = [d for d in days if a <= d <= b]
        daily = replay(signals, sip, window)["daily"]
        out[name] = [(r["day"], 60_000 + float(r["equity"])) for r in daily]
    return out


def lev_trend():
    """Test #14's rule (2x the market above its 200-day average, else T-bills) on the Ken French daily data."""
    from datetime import date, timedelta
    from research.lev_trend_test_v1.run import SMA_DAYS, load_french, run_strategy, signals
    dates, mkt, rf = load_french()
    level, levels = 1.0, []
    for m in mkt:
        level *= 1 + m
        levels.append(level)
    sig = signals(levels)
    curve, _, _ = run_strategy(mkt, rf, sig, 2, True, SMA_DAYS)
    ds = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in dates[SMA_DAYS:]]
    return [(d, 100_000 * v) for d, v in zip(ds, curve)]


def main():
    spy = load_spy()
    cards = {}

    def add(name, test, curve, start, note=""):
        card = scorecard(curve, start, spy=spy_curve(curve, start, spy))
        card.update({"test": test, "note": note})
        cards[name] = card

    for name, curve in plan_b_lite().items():
        add(f"Plan B LITE dip rule, {name}", "Plan B (live paper bot)", curve, 60_000, "$60,000 per buy; P&L on $60,000")
    add("SPY, just holding it", "benchmark", [(d, 100_000 * spy[d] / spy["2019-12-31"]) for d in sorted(spy)
                                              if POST_COVID <= d <= "2026-09-28"], 100_000)
    c, s = since(lev_trend())
    add("2x market above its 200-day, else T-bills", "#14 (the one pass)", c, s, "Ken French market data, ends mid-2026")
    r = j("output/csp-spy-test-results.json")
    c, s = since([tuple(x) for x in r["curve_main_delta30_bid"]])
    add("Sell a SPY put every month", "#10", c, s, "option data ends Dec 2025")
    r = j("output/short-dated-calls-test-results.json")
    add("Buy a ~7-day SPY call every week", "#24", [tuple(x) for x in r["main_curve"]], 100_000,
        "2% of the account a week; option data ends Dec 2025")
    add("RFK (range, fakeout, killshot)", "#23", [tuple(x) for x in j("outputs/orb_play_data/rfk_detail.json.gz")["curve_main"]], 100_000)
    add("Stocks in Play opening-range breakout", "#21", [tuple(x) for x in j("outputs/orb_play_data/results_detail_1min.json.gz")["main_curve"]], 100_000,
        "1-minute re-check, long only, cash")
    add("Revenue acceleration ('LITE fingerprint') top 20", "#20", [tuple(x) for x in j("output/revenue-acceleration-test-results.json")["curve_main"]], 100_000)
    add("Buy big drops in strong stocks", "#19", [tuple(x) for x in j("output/big-drop-rebound-test-results.json")["curve_main"]], 100_000)
    add("Top 5 LITE-like momentum stocks", "#17", [tuple(x) for x in j("output/lite-like-momentum-test-results.json")["curve_main"]], 100_000)
    c, s = since([tuple(x) for x in j("output/ep-test-results.json")["curve"]])
    add("Qullamaggie earnings gap-up (EP)", "#16", c, s)
    c, s = since([(x[0], x[1]) for x in j("output/sma50-test-results.json")["equity_curve"]])
    add("SPY only above its 50-day average", "#5", c, s)
    c, s = since([(x[0], x[1]) for x in j("output/breakout-test-results.json")["equity_curve"]])
    add("Breakouts (TikTok/Qullamaggie style)", "#3", c, s)
    OUT.write_text(json.dumps(cards, indent=1) + "\n")
    for name, c in cards.items():
        print(f"{name[:48]:48s} {c['from']}..{c['to']}  profit {c['profit']:>9,}  /wk {c['avg_per_week']:>6,}  "
              f"up-wks {c['weeks_up_pct']:>5}%  $1k-wks {c['weeks_at_or_above_1000']:>3}/{c['weeks']}  "
              f"worst wk {c['worst_week']:>8,}  worst mo {c['worst_month']:>8,}  drop {c['worst_drop_dollars']:>9,}  "
              f"| SPY profit {c['spy_same_dates']['profit']:>9,}")


if __name__ == "__main__":
    main()
