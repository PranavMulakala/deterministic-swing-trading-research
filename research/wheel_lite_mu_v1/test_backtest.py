"""Offline tests for test #32 (plan: output/WHEEL_LITE_MU_TEST_PLAN_20261010.md). Fake providers only; no network.

  PYTHONPATH=src:. .venv/bin/python -m unittest research.wheel_lite_mu_v1.test_backtest -v
"""
from dataclasses import asdict, fields
from datetime import date, timedelta
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from research.cc_spy_test_v1.backtest import bs_call
from research.spy_put_spread_backtest_v1.backtest import bs_put
from research.wheel_lite_mu_v1 import backtest as lb
from research.wheel_lite_mu_v1 import data as lm
from research.wheel_test_v1 import backtest as bt
from research.wheel_test_v1 import data as w29
from research.wheel_test_v1.test_backtest import MON, Fake, at, bs_chain, weekdays

MAIN = lb.VERSIONS["main"]


def pick(day=MON, spot=100.0, kind="P", rules=MAIN, iv=0.40, floor=None):
    p, why = bt.pick_contract(bs_chain(day, spot, iv), day, kind, spot, 0.0, rules, floor)
    assert p, why
    return p


def half(sale):
    """50% of the sale price rounded DOWN to 0.0001, so it is a qualifying ask."""
    return math.floor(0.50 * sale * 10_000) / 10_000


def run(fake, rules=MAIN, earnings=(), size=lb.SIZE, ticker="TEST"):
    return lb.LMSleeve(ticker, rules, fake, fake.days, earnings, size).run()


class StubDB:
    spent = 0.0


class BSFake(Fake):
    """Quotes are generated: one minute a day at 12:00 (15:50 on the sale day), priced with Black-Scholes at that
    day's close, so contracts decay, get bought back, assigned and called away naturally."""

    def __init__(self, days, closes, **kw):
        super().__init__(days, closes=closes, spots=dict(closes), **kw)
        self.db = StubDB()

    def quotes(self, t, kind, exp, strike, sale_day, last_day):
        self.windows.append((kind, exp, strike, sale_day, last_day))
        out = []
        for d in self.days:
            if not sale_day <= d <= last_day:
                continue
            ts = at(d, 15, 50) if d == sale_day else at(d, 12, 0)
            tt = max((exp - d).days + 0.25 / 24, 0.01) / 365
            px = (bs_put if kind == "P" else bs_call)(self.close(t, d), strike, tt, 0.0, self.iv, q=0.0)[0]
            out.append((ts, round(max(px - 0.05, 0.0), 4), round(px + 0.05, 4)))
        return out


def wavy(days, amp=12.0, period=17):
    return {d: round(100 + amp * math.sin(2 * math.pi * i / period), 2) for i, d in enumerate(days)}


# ---------------------------------------------------------------- 50% buyback

class Buyback50(unittest.TestCase):
    def scenario(self, minute, ask_frac=None, rules=MAIN):
        days = weekdays(MON, 5)
        p = pick()
        sale = p["bid"]
        ask = half(sale) if ask_frac is None else round(ask_frac * sale, 4)
        q = [(at(days[1], 10, 0), 0, round(0.51 * sale, 4)), (minute(days), 0, ask),
             (at(days[1], 15, 58), 0, round(0.10 * sale, 4))]
        fake = Fake(days, quotes={("P", p["expiration"], p["strike"]): q})
        return run(fake, rules), p, sale, days, fake

    def test_first_minute_at_or_below_half_of_the_sale_price(self):
        s, p, sale, days, fake = self.scenario(lambda ds: at(ds[1], 10, 1))
        t0 = s.trades[0]
        self.assertEqual(t0["how"], "closed_early_50pct")
        self.assertAlmostEqual(t0["close_price"], half(sale))
        self.assertEqual(t0["close_minute"], at(days[1], 10, 1).isoformat())   # 51% at 10:00 did not trigger
        self.assertAlmostEqual(t0["close_cost"], t0["contracts"] * 100 * half(sale))
        self.assertAlmostEqual(t0["close_fees"], t0["contracts"] * 0.03)
        self.assertEqual(s.trades[1]["sale_day"], days[1].isoformat())          # before 15:45: resold same day
        lb.sleeve_report(s, fake)

    def test_exactly_half_counts_and_test29_level_would_not(self):
        days = weekdays(MON, 5)
        p = pick()
        q = {("P", p["expiration"], p["strike"]): [(at(days[1], 10, 0), 0, 0.5 * p["bid"])]}
        self.assertEqual(run(Fake(days, quotes=q)).trades[0]["how"], "closed_early_50pct")
        # the same ask under test #29's 25% level is not a buyback: the put runs to expiration
        self.assertEqual(run(Fake(days, quotes=q), lb.LMRules(take=0.25)).trades[0]["how"], "expired_worthless")

    def test_zero_ask_is_not_a_fill(self):
        s, *_ = self.scenario(lambda ds: at(ds[1], 10, 1), ask_frac=0.0)
        self.assertEqual(s.trades[0]["how"], "closed_early_50pct")            # the 15:58 ask (10%) is the fill
        self.assertEqual(s.trades[0]["close_minute"][11:16], "15:58")

    def test_at_or_after_1545_resells_next_day(self):
        for hm in ((15, 45), (15, 50)):
            s, *_, days, _ = self.scenario(lambda ds: at(ds[1], *hm))
            self.assertEqual(s.trades[0]["how"], "closed_early_50pct")
            self.assertEqual(s.trades[1]["sale_day"], days[2].isoformat())

    def test_hold_to_expiry_ignores_the_buyback(self):
        s, p, *_ = self.scenario(lambda ds: at(ds[1], 10, 1), rules=lb.VERSIONS["hold_to_expiry"])
        self.assertEqual(s.trades[0]["how"], "expired_worthless")
        self.assertEqual(s.trades[0]["end_day"], p["expiration"].isoformat())

    def test_labels(self):
        self.assertEqual(lb.early_label(0.25), "closed_early_75pct")
        self.assertEqual(lb.early_label(0.50), "closed_early_50pct")


# ---------------------------------------------------------------- call strike floor (rule 6)

class StrikeFloor(unittest.TestCase):
    def assigned_then(self, call_day_spots, rules=MAIN):
        """Put sold Monday at 100, assigned Friday; then the given spots on the following days."""
        days = weekdays(MON, 15)
        p = pick()
        closes = {d: 100.0 for d in days}
        closes[p["expiration"]] = p["strike"] - 5
        after = [d for d in days if d > p["expiration"]]
        for d, spot in zip(after, call_day_spots):
            closes[d] = spot
        fake = Fake(days, closes=closes, spots=dict(closes))
        return run(fake, rules), fake, p, after

    def test_nothing_qualifies_day_sells_nothing_and_keeps_the_shares(self):
        s, fake, p, after = self.assigned_then([80.0, 100.0])
        put, call = s.trades[0], s.trades[1]
        self.assertEqual(put["how"], "assigned")
        self.assertEqual(s.blocked_days, [after[0]])                     # day 1 at $80: calls in band all < basis
        self.assertEqual(s.skips["no_call_at_or_above_basis"], 1)
        self.assertEqual(call["kind"], "C")
        self.assertEqual(call["sale_day"], after[1].isoformat())          # day 2 at $100: a call qualifies
        self.assertGreaterEqual(call["strike"], p["strike"])
        self.assertAlmostEqual(call["contracts"] * 100, put["shares_after"])
        rep = lb.sleeve_report(s, fake)
        st = rep["stuck_holding_shares_no_call_allowed"]
        self.assertEqual((st["days_no_call_allowed"], st["weeks_stuck_no_call_allowed"]), (1, 1))

    def test_no_basis_floor_sells_below_the_price_paid(self):
        s, _, p, after = self.assigned_then([80.0, 100.0], rules=lb.VERSIONS["no_basis_floor"])
        call = s.trades[1]
        self.assertEqual(call["sale_day"], after[0].isoformat())
        self.assertLess(call["strike"], p["strike"])
        self.assertEqual(s.blocked_days, [])

    def test_floor_is_inclusive_and_filters_below(self):
        plain = pick(kind="C")
        self.assertEqual(pick(kind="C", floor=plain["strike"])["strike"], plain["strike"])   # strike == basis is OK
        p2, _ = bt.pick_contract(bs_chain(MON, 100.0), MON, "C", 100.0, 0.0, MAIN, plain["strike"] + 0.01)
        self.assertTrue(p2 is None or p2["strike"] >= plain["strike"] + 0.01)

    def test_a_day_with_no_call_in_the_band_at_all_is_not_counted_as_stuck(self):
        days = weekdays(MON, 15)
        p = pick()
        closes = {d: 100.0 for d in days}
        closes[p["expiration"]] = p["strike"] - 5
        after = [d for d in days if d > p["expiration"]]
        chains = {MON: bs_chain(MON, 100.0)}
        far = {k: v for k, v in bs_chain(after[0], 100.0).items() if k[1] == "C" and k[2] >= 120}  # deltas ~0
        chains[after[0]] = far
        fake = Fake(days, closes=closes, spots=dict(closes), chains=chains)
        s = run(fake)
        self.assertEqual(s.skips["no_strike_in_delta_band"], 1)
        self.assertEqual(s.blocked_days, [])

    def test_longest_stuck_stretch(self):
        s, fake, p, after = self.assigned_then([80.0, 80.0, 80.0, 100.0])
        st = lb.sleeve_report(s, fake)["stuck_holding_shares_no_call_allowed"]
        self.assertEqual(st["days_no_call_allowed"], 3)
        self.assertEqual(st["longest_stuck_stretch_trading_days"], 3)


# ---------------------------------------------------------------- earnings skip

class Earnings(unittest.TestCase):
    def test_session_definition(self):
        days = weekdays(date(2024, 8, 12), 10)     # Mon Aug 12 .. Fri Aug 23, 2024 (EDT, UTC-4)
        f = lambda s: lm.earnings_session(s, days)
        self.assertEqual(f("2024-08-14T11:58:00.000Z"), date(2024, 8, 14))   # 07:58 ET pre-market -> that day
        self.assertEqual(f("2024-08-14T19:59:00.000Z"), date(2024, 8, 14))   # 15:59 ET in session -> that day
        self.assertEqual(f("2024-08-14T20:00:00.000Z"), date(2024, 8, 15))   # 16:00 ET -> next session
        self.assertEqual(f("2024-08-14T20:07:33.000Z"), date(2024, 8, 15))   # LITE-style after close
        self.assertEqual(f("2024-08-16T20:30:00.000Z"), date(2024, 8, 19))   # Friday after close -> Monday
        self.assertEqual(f("2024-08-18T14:00:00.000Z"), date(2024, 8, 19))   # Sunday -> Monday
        self.assertEqual(f("2024-08-15T01:10:00.000Z"), date(2024, 8, 15))   # 21:10 ET Aug 14 -> Aug 15
        self.assertEqual(f("2024-08-23T21:00:00.000Z"), date(2024, 8, 26))   # past the list: next weekday
        winter = weekdays(date(2024, 12, 16), 5)   # EST, UTC-5
        self.assertEqual(lm.earnings_session("2024-12-18T21:00:20.000Z", winter), date(2024, 12, 19))  # MU 16:00 ET
        self.assertEqual(lm.earnings_session("2024-12-18T20:59:00.000Z", winter), date(2024, 12, 18))  # 15:59 ET

    def test_shifted_time_base_and_calibration(self):
        # Apple 16:30 ET (EDT) is 20:30Z true UTC; the "shifted" stamp for the same filing is 00:30Z the next day
        self.assertEqual(lm.acceptance_ny("2026-07-30T20:30:28.000Z").strftime("%Y-%m-%d %H:%M"), "2026-07-30 16:30")
        self.assertEqual(lm.acceptance_ny("2026-07-31T00:30:28.000Z", shifted=True).strftime("%Y-%m-%d %H:%M"),
                         "2026-07-30 16:30")
        self.assertEqual(lm.acceptance_ny("2026-01-30T02:30:33.000Z", shifted=True).strftime("%Y-%m-%d %H:%M"),
                         "2026-01-29 16:30")                                  # winter (EST)
        true_utc = [["2026-07-30T20:30:28.000Z", "", ""], ["2026-01-29T21:30:33.000Z", "", ""]] * 3
        shifted = [["2026-07-31T00:30:28.000Z", "", ""], ["2026-01-30T02:30:33.000Z", "", ""]] * 3
        self.assertFalse(lm.calibrate(rows=true_utc)["shifted"])
        self.assertTrue(lm.calibrate(rows=shifted)["shifted"])
        with self.assertRaises(RuntimeError):
            lm.calibrate(rows=[["2026-07-30T15:00:00.000Z", "", ""]] * 4)   # neither reading gives 16:30 ET
        days = weekdays(date(2026, 7, 27), 10)
        self.assertEqual(lm.earnings_session("2026-07-31T00:30:28.000Z", days, shifted=True), date(2026, 7, 31))
        self.assertEqual(lm.changed_sessions([["2026-07-31T00:30:28.000Z", "", ""]], days, True), [])
        # 21:30Z: 17:30 ET read as UTC (next session) but 13:30 ET read as shifted (same day): reported as a change
        self.assertEqual(len(lm.changed_sessions([["2026-07-29T21:30:00.000Z", "", ""]], days, False)), 1)

    def test_filing_before_the_test_is_dropped(self):
        days = weekdays(date(2020, 1, 2), 5)
        self.assertIsNone(lm.earnings_session("2019-12-18T21:00:40.000Z", days))  # MU Dec 18, 2019 after close
        self.assertEqual(lm.earnings_sessions([["2019-12-18T21:00:40.000Z", "", ""]], days), [])

    def test_sessions_from_rows(self):
        days = weekdays(date(2024, 8, 12), 10)
        rows = [["2024-08-14T20:07:33.000Z", "2024-08-14", "2.02,9.01"],
                ["2024-08-15T12:00:00.000Z", "2024-08-15", "2.02"]]
        self.assertEqual(lm.earnings_sessions(rows, days), [date(2024, 8, 15)])

    def test_life_is_sale_day_through_expiration_inclusive(self):
        s = lb.LMSleeve("T", lb.VERSIONS["skip_earnings"], Fake(weekdays(MON, 3)), weekdays(MON, 3),
                        earnings=[MON + timedelta(days=4)])
        self.assertTrue(s.earnings_in_life(MON, MON + timedelta(days=4)))         # on expiration day
        self.assertTrue(s.earnings_in_life(MON + timedelta(days=4), MON + timedelta(days=11)))  # on the sale day
        self.assertFalse(s.earnings_in_life(MON, MON + timedelta(days=3)))        # expires the day before
        self.assertFalse(s.earnings_in_life(MON + timedelta(days=5), MON + timedelta(days=12)))  # already past

    def test_skip_until_a_contract_avoids_the_session(self):
        days = weekdays(MON, 10)
        e = days[2]                                          # Wednesday
        fake = Fake(days)
        s = run(fake, lb.VERSIONS["skip_earnings"], earnings=[e])
        self.assertEqual(s.skips["contract_life_includes_earnings"], 3)   # Mon, Tue (Fri expiry), Wed (sale day = E)
        first = s.trades[0]
        self.assertEqual(first["sale_day"], days[3].isoformat())          # Thursday: next Friday, no session inside
        for t in s.trades:
            self.assertFalse(date.fromisoformat(t["sale_day"]) <= e <= date.fromisoformat(t["expiration"]))
        plain = run(Fake(days), MAIN, earnings=[e])                       # main ignores earnings
        self.assertEqual(plain.trades[0]["sale_day"], MON.isoformat())

    def test_skip_applies_to_calls_too(self):
        days = weekdays(MON, 15)
        p = pick()
        closes = {d: 100.0 for d in days}
        closes[p["expiration"]] = p["strike"] - 5
        after = [d for d in days if d > p["expiration"]]
        s = run(Fake(days, closes=closes, spots=dict(closes)), lb.VERSIONS["skip_earnings"], earnings=[after[1]])
        calls = [t for t in s.trades if t["kind"] == "C"]
        self.assertEqual(calls[0]["sale_day"], after[2].isoformat())
        self.assertEqual(s.skips["contract_life_includes_earnings"], 2)


# ---------------------------------------------------------------- settings reach the engine unchanged

class Settings(unittest.TestCase):
    def test_main_rules_match_the_plan(self):
        self.assertIsInstance(MAIN, bt.Rules)
        self.assertEqual((MAIN.target, MAIN.band, MAIN.early_close, MAIN.basis_floor, MAIN.whole, MAIN.take,
                          MAIN.skip_earnings), (0.30, (0.25, 0.35), True, True, False, 0.50, False))
        self.assertEqual((lb.SIZE, lb.START, lb.END, lb.RECENT, lb.TICKERS),
                         (100_000.0, date(2020, 1, 2), date(2026, 10, 9), date(2025, 1, 2), ("LITE", "MU")))
        self.assertEqual((bt.EXP_BAND, bt.EXP_TARGET, bt.EXP_FALLBACK, bt.FEE), ((4, 13), 7, (4, 45), 0.03))

    def test_each_information_version_changes_one_thing(self):
        want = {"no_basis_floor": {"basis_floor": False}, "delta_20": {"target": 0.20, "band": (0.15, 0.25)},
                "hold_to_expiry": {"early_close": False}, "skip_earnings": {"skip_earnings": True},
                "whole_contracts": {"whole": True}}
        self.assertEqual(list(lb.VERSIONS), ["main", *want])
        base = asdict(MAIN)
        for name, change in want.items():
            diff = {k: v for k, v in asdict(lb.VERSIONS[name]).items() if base[k] != v}
            self.assertEqual(diff, change, name)

    def test_rules_object_and_basis_reach_pick_contract(self):
        days = weekdays(MON, 15)
        p = pick()
        closes = {d: 100.0 for d in days}
        closes[p["expiration"]] = 90.0              # every version's put (strikes in the 90s) is assigned
        for name, rules in lb.VERSIONS.items():
            seen = []
            real = bt.pick_contract
            def spy(chain, day, kind, spot, r, rr, floor=None):
                seen.append((kind, rr, floor))
                return real(chain, day, kind, spot, r, rr, floor)
            with mock.patch.object(bt, "pick_contract", spy), \
                    mock.patch.object(bt, "contracts_for", wraps=bt.contracts_for) as cf:
                s = run(Fake(days, closes=dict(closes), spots=dict(closes)), rules)
            self.assertTrue(seen and all(rr is rules for _, rr, _ in seen), name)
            calls = [(k, f) for k, _, f in seen if k == "C"]
            self.assertTrue(calls, name)
            for _, f in calls:
                self.assertEqual(s.trades[0]["how"], "assigned", name)
                self.assertEqual(f, s.trades[0]["strike"] if rules.basis_floor else None, name)  # == assignment price
            self.assertTrue(all(c.args[0] is rules for c in cf.call_args_list), name)
            self.assertEqual(s.size, 100_000.0)

    def test_subclass_reproduces_the_test29_engine_exactly(self):
        """With test #29's settings and size, the copied sell/manage give the engine's trades and curve, bit for bit."""
        days = weekdays(MON, 60)
        for floor in (False, True):
            closes = wavy(days)
            a = bt.Sleeve("T", bt.Rules(basis_floor=floor), BSFake(days, closes, rate=0.04), days).run()
            same = lb.LMRules(target=0.35, band=(0.25, 0.45), basis_floor=floor, take=0.25)
            b = lb.LMSleeve("T", same, BSFake(days, closes, rate=0.04), days, size=40_000).run()
            self.assertGreater(len(a.trades), 8)
            hows = {t["how"] for t in a.trades}
            self.assertTrue({"closed_early_75pct", "assigned"} <= hows, hows)
            self.assertEqual(a.trades, b.trades)
            self.assertEqual(a.curve, b.curve)
            self.assertEqual(dict(a.skips), {k: v for k, v in b.skips.items() if k != "no_call_at_or_above_basis"}
                             | ({"no_strike_in_delta_band": b.skips["no_strike_in_delta_band"]
                                 + b.skips["no_call_at_or_above_basis"]}
                                if b.skips["no_call_at_or_above_basis"] else {}))

    def test_data_layer_uses_its_own_folder_and_budget(self):
        self.assertEqual(lm.DATA, lm.ROOT / "outputs/wheel_lite_mu_data")
        self.assertNotEqual(lm.DATA, w29.DATA)
        self.assertEqual(lm.BUDGET, 12.0)
        self.assertEqual(lm.CIKS, {"LITE": 1633978, "MU": 723125})
        self.assertEqual(lm.USER_AGENT, "Pranav Mulakala pmulakala90@gmail.com")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.csv"
            src.write_text("observation_date,TB3MS\n2026-01-01,3.60\n")
            dest = lm.ensure_tbill_file(Path(tmp) / "d", src)
            self.assertEqual(dest.read_text(), src.read_text())
            with mock.patch.object(w29, "Provider") as P:
                lm.make_provider(data=Path(tmp) / "d")
            P.assert_called_once_with(tickers=("LITE", "MU"), data=Path(tmp) / "d", db=None, budget=12.0)

    def test_budget_guard_at_12(self):
        with tempfile.TemporaryDirectory() as tmp:
            import threading
            db = object.__new__(w29.Databento)
            db._key, db.budget, db.data, db.lock = "k", lm.BUDGET, Path(tmp), threading.Lock()
            db.spent_path, db.ledger_path = Path(tmp) / "databento_spent.json", Path(tmp) / "ledger.csv"
            db.spent, db.spent_this_run = 11.80, 0.0
            db._post = lambda path, p: "0.25" if path == "metadata.get_cost" else "a,b\n"
            start = at(MON, 15, 45)
            with self.assertRaises(w29.BudgetExceeded):
                db.get("MU.OPT", "parent", start, start + timedelta(minutes=1))
            self.assertFalse(db.spent_path.exists())


# ---------------------------------------------------------------- accounting and report

class Accounting(unittest.TestCase):
    def test_ledger_adds_up_and_unrecorded_contract_is_caught(self):
        days = weekdays(MON, 60)
        fake = BSFake(days, wavy(days), rate=0.04, divs={days[20]: 0.10})
        s = run(fake)
        rep = lb.sleeve_report(s, fake)
        self.assertEqual(rep["contracts_opened"], len(s.trades))
        tt = rep["true_total"]
        self.assertAlmostEqual(sum(v for k, v in tt.items() if k != "equals_total_pnl"), tt["equals_total_pnl"],
                               delta=0.05)
        s.trades.pop(0)
        with self.assertRaises(AssertionError):
            lb.sleeve_report(s, fake)

    def test_holding_is_test29_hold_scaled_to_100k(self):
        days = weekdays(MON, 12)
        fake = Fake(days, spots={days[0]: 80.0}, closes={days[-1]: 6.0}, splits={days[7]: 20.0},
                    divs={days[2]: 0.5, days[9]: 0.05}, rate=0.03)
        h = lb.hold_scaled("X", fake, days)
        shares = 100_000 / 80.0
        self.assertAlmostEqual(h["shares_end"], shares * 20)
        self.assertAlmostEqual(h["dividends"], shares * 0.5 + shares * 20 * 0.05)
        self.assertAlmostEqual(h["share_pnl"], shares * 20 * 6.0 - 100_000)
        self.assertAlmostEqual(h["final_value"], h["curve"][-1][1])
        self.assertAlmostEqual(h["final_value"], 100_000 + h["share_pnl"] + h["dividends"] + h["interest"], places=6)

    def test_slice_summary_measures_from_the_day_before(self):
        days = weekdays(date(2024, 12, 23), 10)
        curve = [(d, 150_000 + 500 * i) for i, d in enumerate(days)]
        s = lb.slice_summary(curve, date(2025, 1, 2))
        start = [v for d, v in curve if d < date(2025, 1, 2)][-1]
        self.assertEqual(s["account_value_at_start"], start)
        self.assertEqual(s["total_pnl"], curve[-1][1] - start)
        self.assertIsNone(lb.slice_summary(curve, days[0]))

    def test_checks(self):
        def acct(h1, h2, dd):
            return {"dollars": {"pnl_by_half": {"2020-2022": h1, "2023-2026": h2}, "worst_drop_from_high_pct": dd,
                                "worst_drop_from_high_usd": -1.0}}
        main = {"combined": {"dollars": {"avg_per_week": 1000.0}},
                "per_account": {"LITE": acct(5, 6, -24.9), "MU": acct(1, 2, -25.0)}}
        c, detail, verdict, words = lb.checks(main)
        self.assertEqual(verdict, "PASS")
        self.assertTrue(words.startswith("PASS."))
        main["combined"]["dollars"]["avg_per_week"] = 999.99
        self.assertEqual(lb.checks(main)[2], "FAIL")
        main["combined"]["dollars"]["avg_per_week"] = 2000
        main["per_account"]["MU"] = acct(-1, 50, -10)
        c, detail, verdict, words = lb.checks(main)
        self.assertEqual((verdict, detail["C2_by_account"]), ("FAIL", {"LITE": True, "MU": False}))
        self.assertIn("MU: C2 missed", words)
        main["per_account"]["MU"] = acct(1, 2, -25.01)
        c, detail, *_ = lb.checks(main)
        self.assertEqual(detail["C3_by_account"], {"LITE": True, "MU": False})
        main["per_account"]["MU"] = acct(None, 2, -5)
        self.assertFalse(lb.checks(main)[0]["C2_each_account_profitable_in_both_halves"])

    def test_run_all_end_to_end_on_a_fake(self):
        days = weekdays(date(2022, 11, 1), 70)            # crosses into 2023 so both halves exist
        fake = BSFake(days, wavy(days), rate=0.04)
        res = lb.run_all(fake, days, {"LITE": [days[30]], "MU": []}, list(lb.VERSIONS), log=lambda s: None)
        self.assertEqual(list(res), list(lb.VERSIONS))
        m = res["main"]
        self.assertEqual(set(m["per_account"]), {"LITE", "MU"})
        self.assertEqual(m["combined"]["dollars"]["start_value"], 200_000.0)
        self.assertAlmostEqual(m["combined"]["dollars"]["final_value"],
                               sum(v["dollars"]["final_value"] for v in m["per_account"].values()), places=1)
        for name, r in res.items():
            self.assertEqual(r["rules"], asdict(lb.VERSIONS[name]))
        self.assertTrue(lb.checks(m)[2] in ("PASS", "FAIL"))
        h = lb.run_holding(fake, days)
        self.assertEqual(h["combined"]["dollars"]["start_value"], 200_000.0)
        fresh = lb.recent_fresh(fake, days, {}, first=date(2023, 1, 3))
        self.assertEqual(fresh["first"], "2023-01-03")
        self.assertEqual(fresh["main_rules"]["combined"]["dollars"]["start_value"], 200_000.0)


if __name__ == "__main__":
    unittest.main()
