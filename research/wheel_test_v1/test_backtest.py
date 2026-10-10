"""Offline tests for test #29 (plan: output/WHEEL_TEST_PLAN_20261010.md). Fake providers only; no network.

  PYTHONPATH=src:. .venv/bin/python -m unittest research.wheel_test_v1.test_backtest -v
"""
from datetime import date, datetime, time as dtime, timedelta
import json
import math
from pathlib import Path
import tempfile
import threading
import unittest
from zoneinfo import ZoneInfo

from research.cc_spy_test_v1.backtest import bs_call
from research.spy_put_spread_backtest_v1.backtest import bs_put
from research.wheel_test_v1 import backtest as bt
from research.wheel_test_v1 import data as dt

NY = ZoneInfo("America/New_York")
MON = date(2024, 3, 4)  # a Monday


def weekdays(first, n):
    out, d = [], first
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def at(d, h, m):
    return datetime.combine(d, dtime(h, m), NY)


def bs_chain(day, spot, iv=0.40, r=0.0, expirations=None, half_spread=0.05):
    """A chain priced with Black-Scholes at one vol, so each strike's mid implies exactly that vol."""
    exps = expirations or [day + timedelta(days=k) for k in range(1, 46) if (day + timedelta(days=k)).weekday() == 4]
    chain = {}
    for e in exps:
        t = ((e - day).days + bt.HOURS_LEFT / 24) / 365
        for i in range(140, 261):         # strikes 70%..130% of the stock in 0.5% steps (70, 70.5 .. 130 at $100)
            k = round(spot * i / 200, 6)
            for kind in "PC":
                px = (bs_put if kind == "P" else bs_call)(spot, k, t, r, iv, q=0.0)[0]
                if px - half_spread > 0:
                    chain[(e, kind, k)] = (round(px - half_spread, 6), round(px + half_spread, 6))
    return chain


class Fake:
    """In-memory provider. closes/spots default to 100; chains are Black-Scholes unless given; quotes are keyed by
    (kind, expiration, strike) and clipped to the requested window."""

    def __init__(self, days, closes=None, spots=None, quotes=None, splits=None, divs=None, rate=0.0, chains=None,
                 iv=0.40):
        self.days, self.closes, self.spots = days, closes or {}, spots
        self._quotes, self._splits, self._divs, self._rate = quotes or {}, splits or {}, divs or {}, rate
        self._chains, self.iv = chains, iv
        self.chain_calls, self.windows = [], []

    def close(self, t, d):
        return self.closes.get(d, 100.0)

    def spot(self, t, d):
        return self.spots.get(d) if self.spots is not None else self.close(t, d)

    def chain(self, t, d, spot):
        self.chain_calls.append(d)
        if self._chains is not None:
            return self._chains.get(d, {})
        return bs_chain(d, spot, self.iv, self._rate)

    def quotes(self, t, kind, exp, strike, sale_day, last_day):
        self.windows.append((kind, exp, strike, sale_day, last_day))
        lo, hi = at(sale_day, 15, 46), at(last_day, 16, 0)
        return [q for q in self._quotes.get((kind, exp, strike), []) if lo <= q[0] < hi]

    def splits(self, t):
        return dict(self._splits)

    def dividends(self, t):
        return dict(self._divs)

    def rate(self, d):
        return self._rate


def first_pick(day=MON, spot=100.0, kind="P", rules=bt.Rules(), iv=0.40):
    pick, why = bt.pick_contract(bs_chain(day, spot, iv), day, kind, spot, 0.0, rules)
    assert pick, why
    return pick


def quarter(sale):
    """25% of the sale price rounded DOWN to 0.0001, so it is a qualifying ask."""
    return math.floor(0.25 * sale * 10_000) / 10_000


def run(fake, rules=bt.Rules()):
    return bt.Sleeve("TEST", rules, fake, fake.days).run()


class ExpirationChoice(unittest.TestCase):
    def test_closest_to_seven_days_within_4_to_13(self):
        exps = [MON + timedelta(days=k) for k in (2, 4, 11, 18)]
        self.assertEqual(bt.choose_expiration(exps, MON), (MON + timedelta(days=4), False))  # 4 (off 3) beats 11 (off 4)
        exps = [MON + timedelta(days=k) for k in (5, 10)]
        self.assertEqual(bt.choose_expiration(exps, MON), (MON + timedelta(days=5), False))

    def test_tie_goes_to_the_later_expiration(self):
        exps = [MON + timedelta(days=6), MON + timedelta(days=8)]
        self.assertEqual(bt.choose_expiration(exps, MON), (MON + timedelta(days=8), False))
        exps = [MON + timedelta(days=4), MON + timedelta(days=10)]
        self.assertEqual(bt.choose_expiration(exps, MON), (MON + timedelta(days=10), False))

    def test_band_edges_inclusive(self):
        self.assertEqual(bt.choose_expiration([MON + timedelta(days=13)], MON), (MON + timedelta(days=13), False))
        self.assertEqual(bt.choose_expiration([MON + timedelta(days=4)], MON), (MON + timedelta(days=4), False))

    def test_fallback_nearest_within_4_to_45(self):
        exps = [MON + timedelta(days=k) for k in (1, 3, 17, 31, 46)]
        self.assertEqual(bt.choose_expiration(exps, MON), (MON + timedelta(days=17), True))
        self.assertEqual(bt.choose_expiration([MON + timedelta(days=45)], MON), (MON + timedelta(days=45), True))
        self.assertEqual(bt.choose_expiration([MON + timedelta(days=k) for k in (3, 46)], MON), (None, False))

    def test_fallback_trade_is_counted(self):
        days = weekdays(MON, 3)
        monthly = MON + timedelta(days=30)
        fake = Fake(days, chains={days[0]: bs_chain(days[0], 100.0, expirations=[monthly])})
        s = run(fake)
        self.assertEqual(s.trades[0]["expiration"], monthly.isoformat())
        self.assertTrue(s.trades[0]["fallback_expiration"])
        self.assertEqual(bt.sleeve_report(s, fake)["fallback_expirations"], 1)


class DeltaPick(unittest.TestCase):
    def deltas(self, kind, spot=100.0, iv=0.40, day=MON):
        exp = day + timedelta(days=4)  # 4-day Friday is the pick from Monday (see ExpirationChoice)
        t = (4 + bt.HOURS_LEFT / 24) / 365
        fn = bs_put if kind == "P" else bs_call
        return {i / 2: fn(spot, i / 2, t, 0.0, iv, q=0.0)[1] for i in range(140, 261)}, exp

    def test_put_closest_to_minus_035_below_the_stock(self):
        d, exp = self.deltas("P")
        ok = {k: v for k, v in d.items() if k < 100 and 0.25 <= abs(v) <= 0.45}
        want = min(ok, key=lambda k: abs(abs(d[k]) - 0.35))
        p = first_pick(kind="P")
        self.assertEqual((p["expiration"], p["strike"]), (exp, want))
        self.assertAlmostEqual(p["delta"], d[want], places=4)
        self.assertLess(p["strike"], 100)

    def test_call_closest_to_plus_035_above_the_stock(self):
        d, exp = self.deltas("C")
        ok = {k: v for k, v in d.items() if k > 100 and 0.25 <= v <= 0.45}
        want = min(ok, key=lambda k: abs(d[k] - 0.35))
        self.assertEqual(first_pick(kind="C")["strike"], want)

    def test_band_limits_skip_the_day(self):
        # strikes whose deltas are all outside 0.25-0.45: only far out-of-the-money and in-the-money ones
        chain = {k: v for k, v in bs_chain(MON, 100.0).items() if k[2] <= 85 or k[2] >= 100}
        pick, why = bt.pick_contract(chain, MON, "P", 100.0, 0.0, bt.Rules())
        self.assertIsNone(pick)
        self.assertEqual(why, "no_strike_in_delta_band")
        d, _ = self.deltas("P")
        inside = [k for k in d if k < 100 and 0.25 <= abs(d[k]) <= 0.45]
        self.assertTrue(inside and all(85 < k < 100 for k in inside))

    def test_info_bands(self):
        d, _ = self.deltas("P")
        for rules in (bt.VERSIONS["delta_25"], bt.VERSIONS["delta_45"]):
            lo, hi = rules.band
            ok = {k: v for k, v in d.items() if k < 100 and lo <= abs(v) <= hi}
            want = min(ok, key=lambda k: abs(abs(d[k]) - rules.target))
            self.assertEqual(first_pick(kind="P", rules=rules)["strike"], want)

    def test_zero_bid_and_at_the_money_strikes_excluded(self):
        p = first_pick(kind="P")
        chain = bs_chain(MON, 100.0)
        chain[(p["expiration"], "P", p["strike"])] = (0.0, 0.10)
        again, _ = bt.pick_contract(chain, MON, "P", 100.0, 0.0, bt.Rules())
        self.assertNotEqual(again["strike"], p["strike"])
        # spot exactly on a strike: that strike is neither below (put) nor above (call)
        for kind in "PC":
            pk, _ = bt.pick_contract(chain, MON, kind, 100.0, 0.0, bt.Rules(band=(0.0, 1.0), target=0.5))
            self.assertNotEqual(pk["strike"], 100.0)

    def test_basis_floor_rejects_calls_below_the_assignment_price(self):
        plain = first_pick(kind="C")
        pick, why = bt.pick_contract(bs_chain(MON, 100.0), MON, "C", 100.0, 0.0, bt.Rules(), floor=plain["strike"] + 1)
        self.assertTrue(pick is None or pick["strike"] >= plain["strike"] + 1)
        pick, why = bt.pick_contract(bs_chain(MON, 100.0), MON, "C", 100.0, 0.0, bt.Rules(), floor=125)
        self.assertEqual((pick, why), (None, "no_strike_in_delta_band"))


class Buyback(unittest.TestCase):
    def test_first_minute_at_or_below_25pct(self):
        q = [(1, 0.8, 0.9), (2, 0.0, 0.0), (3, 0.45, 0.50), (4, 0.3, 0.4)]
        self.assertEqual(bt.first_buyback(q, 2.00), 2)            # 0.50 = exactly 25% of 2.00 counts
        self.assertIsNone(bt.first_buyback(q[:2], 2.00))          # an ask of 0 is no offer, not a fill

    def scenario(self, minute, rules=bt.Rules()):
        days = weekdays(MON, 5)
        p = first_pick()
        sale = p["bid"]
        q = [(at(days[1], 10, 0), 0, round(0.30 * sale, 4)), (minute(days), 0, quarter(sale)),
             (at(days[1], 15, 58), 0, round(0.10 * sale, 4))]
        fake = Fake(days, quotes={("P", p["expiration"], p["strike"]): q})
        return run(fake, rules), p, sale, days, fake

    def test_buyback_before_1545_resells_same_day(self):
        s, p, sale, days, _ = self.scenario(lambda ds: at(ds[1], 10, 1))
        t0 = s.trades[0]
        self.assertEqual(t0["how"], "closed_early_75pct")
        self.assertAlmostEqual(t0["close_price"], quarter(sale))
        self.assertEqual(t0["close_minute"], at(days[1], 10, 1).isoformat())
        self.assertAlmostEqual(t0["close_cost"], t0["contracts"] * 100 * quarter(sale))
        self.assertAlmostEqual(t0["close_fees"], t0["contracts"] * 0.03)
        self.assertEqual(s.trades[1]["sale_day"], days[1].isoformat())

    def test_buyback_at_or_after_1545_resells_next_day(self):
        for hm in ((15, 45), (15, 50)):
            s, *_, days, _ = self.scenario(lambda ds: at(ds[1], *hm))
            self.assertEqual(s.trades[0]["how"], "closed_early_75pct")
            self.assertEqual(s.trades[1]["sale_day"], days[2].isoformat())

    def test_hold_to_expiry_ignores_the_buyback(self):
        s, p, *_ = self.scenario(lambda ds: at(ds[1], 10, 1), rules=bt.VERSIONS["hold_to_expiry"])
        self.assertEqual(s.trades[0]["how"], "expired_worthless")
        self.assertEqual(s.trades[0]["end_day"], p["expiration"].isoformat())

    def test_sale_fill_is_bid_minus_three_cents(self):
        s, p, sale, *_ = self.scenario(lambda ds: at(ds[1], 10, 1))
        t0 = s.trades[0]
        self.assertAlmostEqual(t0["premium"], t0["contracts"] * 100 * p["bid"])
        self.assertAlmostEqual(t0["sale_fees"], t0["contracts"] * 0.03)


class Expiration(unittest.TestCase):
    def test_settle_rules_including_close_equal_strike(self):
        self.assertEqual(bt.settle("P", 95, 94.99), "assigned")
        self.assertEqual(bt.settle("P", 95, 95.0), "expired_worthless")
        self.assertEqual(bt.settle("C", 105, 105.01), "called_away")
        self.assertEqual(bt.settle("C", 105, 105.0), "expired_worthless")

    def wheel(self, put_close, call_close, rate=0.0):
        days = weekdays(MON, 15)  # Mon Mar 4 .. Fri Mar 22
        p = first_pick()
        closes = {p["expiration"]: put_close(p["strike"])}
        fake = Fake(days, closes=closes, rate=rate)
        c = first_pick(day=days[5], kind="C")      # Monday Mar 11 call at spot 100
        closes[c["expiration"]] = call_close(c["strike"])
        return run(fake), fake, p, c, days

    def test_assignment_then_call_away(self):
        s, fake, p, c, days = self.wheel(lambda k: k - 5, lambda k: k + 5)
        put, call = s.trades[0], s.trades[1]
        n = 40_000 / (p["strike"] * 100)
        self.assertEqual(put["how"], "assigned")
        self.assertAlmostEqual(put["contracts"], n)
        self.assertAlmostEqual(put["share_cash"], -n * 100 * p["strike"])
        self.assertAlmostEqual(put["shares_after"], n * 100)
        self.assertEqual((call["kind"], call["sale_day"]), ("C", days[5].isoformat()))  # next trading day after Fri
        self.assertAlmostEqual(call["contracts"], put["shares_after"] / 100)
        self.assertEqual(call["how"], "called_away")
        self.assertAlmostEqual(call["share_cash"], n * 100 * c["strike"])
        self.assertEqual(call["shares_after"], 0.0)
        self.assertEqual(s.trades[2]["kind"], "P")
        rep = bt.sleeve_report(s, fake)  # asserts the trade list adds up to the final value
        self.assertEqual((rep["times_assigned"], rep["times_called_away"]), (1, 1))
        self.assertAlmostEqual(rep["given_up_when_called_away_vs_expiration_close"], 5 * n * 100, places=2)
        self.assertAlmostEqual(rep["share_pnl"], n * 100 * (c["strike"] - p["strike"]), places=2)

    def test_close_equal_strike_expires_worthless(self):
        s, *_ = self.wheel(lambda k: k, lambda k: k)
        self.assertEqual(s.trades[0]["how"], "expired_worthless")
        self.assertEqual(s.trades[1]["kind"], "P")
        self.assertEqual(s.shares, 0.0)

    def test_trade_list_adds_up_with_interest(self):
        s, fake, *_ = self.wheel(lambda k: k - 5, lambda k: k + 5, rate=0.05)
        rep = bt.sleeve_report(s, fake)   # asserts trades + dividends + interest = final value
        self.assertGreater(rep["interest"], 0)

    def test_interest_paid_on_collateral(self):
        days = weekdays(MON, 2)
        s = run(Fake(days, rate=0.05))    # no quotes: the option's mark stays put, so the change is interest only
        t = s.trades[0]
        first_night = (40_000 + t["premium"] - t["sale_fees"]) * 0.05 / 365
        self.assertAlmostEqual(s.curve[1][1] - s.curve[0][1], first_night)


class SplitAndDividend(unittest.TestCase):
    def setup(self, divs=None):
        days = weekdays(MON, 12)        # Mar 4 .. Mar 19
        p = first_pick()
        ex = days[7]                    # Wed Mar 13; eve = Tue Mar 12
        closes = {p["expiration"]: 50.0, ex: 5.0}
        for d in days[8:]:
            closes[d] = 5.0
        c = first_pick(day=days[5], kind="C")
        q = {("C", c["expiration"], c["strike"]): [(at(days[6], 15, 59), 1.00, 1.20)]}
        fake = Fake(days, closes=closes, quotes=q, splits={ex: 20.0}, divs=divs or {})
        return run(fake), fake, p, c, days, ex

    def test_split_while_holding_shares(self):
        s, fake, p, c, days, ex = self.setup()
        put, call, nxt = s.trades[:3]
        self.assertEqual(put["how"], "assigned")
        self.assertEqual(call["how"], "closed_before_split_at_mid")
        self.assertEqual(call["end_day"], days[6].isoformat())                # the trading day before the ex-date
        self.assertAlmostEqual(call["close_cost"], call["contracts"] * 100 * 1.10)
        self.assertIn(("C", c["expiration"], c["strike"], days[5], days[6]), fake.windows)  # window stops at the eve
        self.assertNotIn(days[6], fake.chain_calls)                            # no new sale on the eve
        self.assertEqual(nxt["sale_day"], ex.isoformat())
        self.assertEqual(nxt["kind"], "C")
        self.assertAlmostEqual(nxt["contracts"], 20 * call["contracts"])
        self.assertAlmostEqual(nxt["contracts"] * 100, 20 * put["shares_after"])
        self.assertAlmostEqual(s.basis if s.shares else p["strike"] / 20, p["strike"] / 20)
        bt.sleeve_report(s, fake)

    def test_dividend_credit_on_ex_date_for_shares_held(self):
        days = weekdays(MON, 12)
        s, fake, p, c, days, ex = self.setup(divs={days[6]: 0.50})
        shares = s.trades[0]["shares_after"]
        self.assertAlmostEqual(s.dividends, shares * 0.50)
        rep = bt.sleeve_report(s, fake)
        self.assertAlmostEqual(rep["dividends"], shares * 0.50, places=2)

    def test_no_dividend_without_shares(self):
        days = weekdays(MON, 3)
        s = run(Fake(days, divs={days[1]: 1.0}))
        self.assertEqual(s.dividends, 0.0)

    def test_holding_comparison(self):
        days = weekdays(MON, 12)
        fake = Fake(days, spots={days[0]: 80.0}, closes={days[-1]: 6.0}, splits={days[7]: 20.0},
                    divs={days[2]: 0.5, days[9]: 0.05}, rate=0.0)
        h = bt.hold("X", fake, days)
        shares = 40_000 / 80.0
        self.assertAlmostEqual(h["dividends"], shares * 0.5 + shares * 20 * 0.05)
        self.assertAlmostEqual(h["shares_end"], shares * 20)
        self.assertAlmostEqual(h["final_value"], shares * 20 * 6.0 + h["dividends"])


class Sizing(unittest.TestCase):
    def test_fractional_and_whole(self):
        main, whole = bt.Rules(), bt.VERSIONS["whole_contracts"]
        self.assertAlmostEqual(bt.contracts_for(main, "P", 40_000, 0, 1800), 40_000 / 180_000)
        self.assertAlmostEqual(bt.contracts_for(main, "C", 0, 22.2222, 1900), 0.222222)
        self.assertEqual(bt.contracts_for(whole, "P", 40_000, 0, 1800), 0)
        self.assertEqual(bt.contracts_for(whole, "P", 40_000, 0, 130), 3)
        self.assertEqual(bt.contracts_for(whole, "C", 0, 300.0, 140), 3)

    def test_sleeve_uses_all_cash_as_collateral(self):
        days = weekdays(MON, 2)
        s = run(Fake(days))
        t = s.trades[0]
        self.assertAlmostEqual(t["contracts"] * t["strike"] * 100, 40_000)

    def test_whole_contracts_sit_in_tbills_when_unaffordable(self):
        days = weekdays(MON, 3)
        fake = Fake(days, closes={d: 1000.0 for d in days}, rate=0.05)
        s = run(fake, bt.VERSIONS["whole_contracts"])
        self.assertEqual(s.trades, [])
        self.assertEqual(fake.chain_calls, [])
        self.assertEqual(s.skips["cannot_afford_one_contract"], 3)
        self.assertAlmostEqual(s.curve[-1][1], 40_000 * (1 + 0.05 / 365) ** 2)

    def test_whole_contracts_round_down(self):
        days = weekdays(MON, 2)
        s = run(Fake(days), bt.VERSIONS["whole_contracts"])
        t = s.trades[0]
        self.assertEqual(t["contracts"], math.floor(40_000 / (t["strike"] * 100)))


class Accounting(unittest.TestCase):
    def test_open_at_end_valued_at_last_mid(self):
        days = weekdays(MON, 2)
        p = first_pick()
        q = {("P", p["expiration"], p["strike"]): [(at(days[1], 15, 0), 0.9, 1.1), (at(days[1], 15, 30), 0.0, 0.0)]}
        fake = Fake(days, quotes=q)
        s = run(fake)
        t = s.trades[-1]
        self.assertEqual(t["how"], "open_at_end")
        self.assertAlmostEqual(t["open_liability"], t["contracts"] * 100 * 1.0)
        self.assertAlmostEqual(s.curve[-1][1], s.cash - t["open_liability"])
        self.assertEqual(fake.windows[0][4], days[-1])
        bt.sleeve_report(s, fake)

    def test_dollar_summary_weeks_and_halves(self):
        days = weekdays(date(2022, 12, 26), 10)
        curve = [(d, 200_000 + 600 * i) for i, d in enumerate(days)]
        s = bt.dollar_summary(curve, 200_000)
        self.assertEqual(s["weeks"], 2)
        self.assertEqual(s["pnl_by_half"]["2020-2022"], 2400.0)
        self.assertEqual(s["pnl_by_half"]["2023-2026"], 5400 - 2400.0)
        self.assertEqual(s["share_of_weeks_at_least_1000_pct"], 100.0)

    def test_checks(self):
        main = {"summary": {"final_value": 300, "pnl_by_half": {"a": 1, "b": 2}, "worst_drop_from_high_pct": -20}}
        hold = {"summary": {"final_value": 299}}
        self.assertEqual(bt.checks(main, hold)[1], "PASS")
        main["summary"]["worst_drop_from_high_pct"] = -25.01
        self.assertEqual(bt.checks(main, hold)[1], "FAIL")


class DataHelpers(unittest.TestCase):
    def test_osi_round_trip_and_fb_root(self):
        s = dt.osi("AMZN", date(2024, 8, 16), "P", 160)
        self.assertEqual(s, "AMZN  240816P00160000")
        self.assertEqual(dt.parse_osi(s), ("AMZN", date(2024, 8, 16), "P", 160.0))
        self.assertEqual(dt.parse_osi("AMZN1 220617C00105000")[0], "AMZN1")
        self.assertEqual(dt.option_root("META", date(2022, 6, 8)), "FB")
        self.assertEqual(dt.option_root("META", date(2022, 6, 9)), "META")

    def test_meta_contract_across_the_rename_is_two_pieces(self):
        seg = dt.quote_segments("META", date(2022, 6, 6), date(2022, 6, 10))
        self.assertEqual([s[0] for s in seg], ["FB", "META"])
        self.assertEqual(seg[0][1], datetime(2022, 6, 6, 15, 46, tzinfo=NY))
        self.assertEqual(seg[1][2], datetime(2022, 6, 10, 16, 0, tzinfo=NY))
        self.assertEqual(len(dt.quote_segments("META", date(2022, 6, 9), date(2022, 6, 17))), 1)

    def test_budget_guard_refuses_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = object.__new__(dt.Databento)
            db._key, db.budget, db.data, db.lock = "k", 1.0, Path(tmp), threading.Lock()
            db.spent_path, db.ledger_path = Path(tmp) / "databento_spent.json", Path(tmp) / "ledger.csv"
            db.spent, db.spent_this_run = 0.70, 0.0
            calls = []
            db._post = lambda path, p: (calls.append(path), "0.25" if path == "metadata.get_cost" else "a,b\n")[1]
            start = datetime(2024, 1, 2, 15, 45, tzinfo=NY)
            db.get("AMZN.OPT", "parent", start, start + timedelta(minutes=1))
            self.assertAlmostEqual(json.loads(db.spent_path.read_text())["spent_dollars"], 0.95)
            with self.assertRaises(dt.BudgetExceeded):
                db.get("AMZN.OPT", "parent", start, start + timedelta(minutes=1))
            self.assertEqual(calls, ["metadata.get_cost", "timeseries.get_range", "metadata.get_cost"])
            self.assertAlmostEqual(json.loads(db.spent_path.read_text())["spent_dollars"], 0.95)

    def test_rates_extend_with_fred(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tb3ms.csv").write_text("observation_date,TB3MS\n2025-12-01,9.99\n2026-01-01,3.60\n2026-02-01,.\n")
            r = dt.load_rates(Path(tmp))
            self.assertAlmostEqual(r["2025-12"], 0.0368)   # shared CSV kept where it has data
            self.assertAlmostEqual(r["2026-01"], 0.036)
            self.assertNotIn("2026-02", r)


if __name__ == "__main__":
    unittest.main()
