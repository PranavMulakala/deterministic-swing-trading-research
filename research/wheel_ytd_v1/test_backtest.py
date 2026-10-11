"""Offline tests for test #33 (plan: output/WHEEL_YTD_SCREEN_TEST_PLAN_20261011.md). Fake providers only; no network.

  PYTHONPATH=src:. .venv/bin/python -m unittest research.wheel_ytd_v1.test_backtest -v
"""
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
import statistics
import tempfile
import threading
import unittest
from unittest import mock

from research.wheel_lite_mu_v1 import backtest as lb
from research.wheel_lite_mu_v1 import data as lm
from research.wheel_lite_mu_v1.test_backtest import BSFake, wavy
from research.wheel_test_v1 import backtest as bt
from research.wheel_test_v1 import data as w29
from research.wheel_test_v1.test_backtest import Fake, at, weekdays
from research.wheel_ytd_v1 import backtest as yb
from research.wheel_ytd_v1 import data as yd

MAIN = yb.MAIN_RULES
RNA = yd.DELISTINGS["RNA"]


class MultiFake(BSFake):
    """BSFake with one close series per ticker (spot = close)."""

    def __init__(self, days, closes_by_ticker, **kw):
        first = next(iter(closes_by_ticker.values()))
        super().__init__(days, dict(first), **kw)
        self.by = closes_by_ticker

    def close(self, t, d):
        return self.by[t][d]

    def spot(self, t, d):
        return self.by[t][d]


def rna_days():
    return weekdays(date(2026, 2, 2), 25)          # Mon Feb 2 .. Fri Mar 6, 2026 (Feb 16 is a weekday here)


def rna_closes(days, before=72.0, after_drop=None, drop_day=None, atrium=14.75):
    """Avidity at `before` (optionally `after_drop` from drop_day) through Feb 26; Atrium from Feb 27."""
    out = {}
    for d in days:
        if d >= RNA["effective"]:
            out[d] = atrium
        elif drop_day is not None and d >= drop_day:
            out[d] = after_drop
        else:
            out[d] = before
    return out


# ---------------------------------------------------------------- the frozen list and the window

class FrozenList(unittest.TestCase):
    def test_list_loads_exactly_as_frozen_in_the_plan(self):
        self.assertEqual(yd.plan_table(), yd.FROZEN)
        self.assertEqual(yd.TICKERS, ("PRAX", "LITE", "RKLB", "RIVN", "HL", "RNA", "AG", "COHR", "STX", "CVNA"))
        self.assertEqual(yb.TICKERS, yd.TICKERS)
        self.assertNotIn("MU", yd.TICKERS)                       # #11, already tested in #32
        self.assertEqual([r[4] for r in yd.FROZEN], sorted((r[4] for r in yd.FROZEN), reverse=True))
        self.assertEqual(set(yd.CIKS), set(yd.TICKERS))

    def test_the_2026_window(self):
        self.assertEqual((yd.START, yd.END, yb.START, yb.END),
                         (date(2026, 1, 2), date(2026, 10, 9), date(2026, 1, 2), date(2026, 10, 9)))
        prov = mock.Mock()
        yd.window_days(prov)
        prov.trading_days.assert_called_once_with(date(2026, 1, 2), date(2026, 10, 9))
        self.assertEqual((yb.SIZE, yb.SMALL), (50_000.0, 25_000.0))

    def test_account_last_day(self):
        days = rna_days()
        self.assertEqual(yd.account_last_day("RNA", days), date(2026, 2, 25))
        self.assertEqual(yd.account_last_day("LITE", days), days[-1])
        self.assertEqual(yd.account_last_day("RNA", days[:3]), days[2])


# ---------------------------------------------------------------- rules and versions

class Settings(unittest.TestCase):
    def test_earnings_skip_is_on_by_default_and_main_is_test32_main_plus_skip(self):
        self.assertTrue(MAIN.skip_earnings)
        self.assertIs(yb.VERSIONS["main"][0], MAIN)
        self.assertEqual(yb.VERSIONS["main"][1], 50_000.0)
        self.assertIsInstance(MAIN, lb.LMRules)
        self.assertEqual(asdict(MAIN), {**asdict(lb.VERSIONS["main"]), "skip_earnings": True})
        self.assertEqual((MAIN.target, MAIN.band, MAIN.early_close, MAIN.basis_floor, MAIN.whole, MAIN.take),
                         (0.30, (0.25, 0.35), True, True, False, 0.50))
        self.assertEqual((bt.EXP_BAND, bt.EXP_TARGET, bt.EXP_FALLBACK, bt.FEE), ((4, 13), 7, (4, 45), 0.03))
        self.assertEqual((yb.WEEKLY_BAR, yb.MIN_PROFITABLE, yb.MAX_MEDIAN_DROP_PCT), (1000.0, 7, -25.0))

    def test_each_information_version_changes_one_thing(self):
        want = {"with_earnings": ({"skip_earnings": False}, 50_000.0),
                "whole_25k": ({"whole": True}, 25_000.0),
                "hold_to_expiry": ({"early_close": False}, 50_000.0)}
        self.assertEqual(list(yb.VERSIONS), ["main", *want])
        base = asdict(MAIN)
        for name, (change, size) in want.items():
            rules, got_size = yb.VERSIONS[name]
            self.assertEqual({k: v for k, v in asdict(rules).items() if base[k] != v}, change, name)
            self.assertEqual(got_size, size, name)
        self.assertEqual(asdict(yb.VERSIONS["with_earnings"][0]), asdict(lb.VERSIONS["main"]))

    def test_settings_reach_the_engine_unchanged(self):
        days = weekdays(date(2026, 3, 2), 30)
        closes = wavy(days)
        earnings = {"LITE": [days[7]], "HL": [days[12]]}
        for name, (rules, size) in yb.VERSIONS.items():
            seen, picks = [], []
            real_pick = bt.pick_contract

            class Rec(lb.LMSleeve):
                def __init__(self, *a, **k):
                    seen.append(a)
                    super().__init__(*a, **k)

            def spy(chain, day, kind, spot, r, rr, floor=None):
                picks.append(rr)
                return real_pick(chain, day, kind, spot, r, rr, floor)
            fake = BSFake(days, closes, rate=0.04)
            with mock.patch.object(lb, "LMSleeve", Rec), mock.patch.object(bt, "pick_contract", spy), \
                    mock.patch.object(bt, "contracts_for", wraps=bt.contracts_for) as cf:
                s, ledger, curve, after = yb.run_account("LITE", rules, size, fake, days, earnings)
            (ticker, r, prov, d, e, sz), = seen
            self.assertEqual((ticker, prov, d, list(e), sz), ("LITE", fake, days, [days[7]], size), name)
            self.assertIs(r, rules, name)
            self.assertTrue(picks and all(p is rules for p in picks), name)
            self.assertTrue(all(c.args[0] is rules for c in cf.call_args_list), name)
            self.assertEqual((s.size, s.rules, after), (size, rules, None), name)
            self.assertEqual(curve, s.curve, name)
            if rules.skip_earnings:
                for t in s.trades:
                    self.assertFalse(date.fromisoformat(t["sale_day"]) <= days[7] <= date.fromisoformat(
                        t["expiration"]), name)

    def test_data_layer_uses_its_own_folder_and_15_dollar_budget(self):
        self.assertEqual(yd.DATA, yd.ROOT / "outputs/wheel_ytd_data")
        self.assertNotIn(yd.DATA, (lm.DATA, w29.DATA))
        self.assertEqual(yd.BUDGET, 15.0)
        self.assertEqual(yd.USER_AGENT, "Pranav Mulakala pmulakala90@gmail.com")
        self.assertIn("outputs/wheel_ytd_data/", (yd.ROOT / ".gitignore").read_text().splitlines())
        self.assertEqual(yd.TB3MS_FROM, yd.ROOT / "outputs/wheel_lite_mu_data/tb3ms.csv")
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(w29, "Provider") as P, \
                mock.patch.object(lm, "ensure_tbill_file") as tb:
            yd.make_provider(data=Path(tmp))
        P.assert_called_once_with(tickers=yd.TICKERS, data=Path(tmp), db=None, budget=15.0)
        tb.assert_called_once_with(Path(tmp), yd.TB3MS_FROM)

    def test_budget_guard_at_15(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = object.__new__(w29.Databento)
            db._key, db.budget, db.data, db.lock = "k", yd.BUDGET, Path(tmp), threading.Lock()
            db.spent_path, db.ledger_path = Path(tmp) / "databento_spent.json", Path(tmp) / "ledger.csv"
            db.spent, db.spent_this_run = 14.80, 0.0
            db._post = lambda path, p: "0.25" if path == "metadata.get_cost" else "a,b\n"
            start = at(date(2026, 3, 2), 15, 45)
            with self.assertRaises(w29.BudgetExceeded):
                db.get("CVNA.OPT", "parent", start, start + timedelta(minutes=1))
            self.assertFalse(db.spent_path.exists())
            db.spent = 14.70
            db.get("CVNA.OPT", "parent", start, start + timedelta(minutes=1))   # exactly $15.00 is allowed
            self.assertAlmostEqual(db.spent, 14.95)


# ---------------------------------------------------------------- earnings, including the 6-K fallback

AG_HEADLINES = {
    "fin": "EX-99.5 6 ag-2026q1financialnrxex995.htm EX-99.5 Document NEWS RELEASE New York - AG May 12, 2026 Toronto "
           "- AG Frankfurt - FMV First Majestic Announces Q1 2026 Financial Results and Increased Quarterly Dividend",
    "prod": "EXHIBIT 99.1 NEWS RELEASE New York - AG April 9, 2026 Toronto - AG Frankfurt - FMV First Majestic "
            "Reports Q1 2026 Production Results Vancouver",
    "prod_old": "NEWS RELEASE New York - AG October 8, 2025 First Majestic Produces 7.7 Million AgEq Ounces in Q3 2025",
    "call": "NEWS RELEASE New York - AG August 7, 2025 First Majestic Second Quarter 2025 Results Conference Call "
            "Details",
    "drill": "NEWS RELEASE New York - AG September 9, 2026 First Majestic Reports High-Grade Drill Results",
}


class Earnings(unittest.TestCase):
    def test_source_detection(self):
        rows = [["2026-02-04T02:12:14.000Z", "2026-02-03", "2.02,9.01"]]
        self.assertEqual(yd.earnings_source(rows, {"8-K": 9, "10-Q": 3}), "8-K Item 2.02")
        self.assertEqual(yd.earnings_source([], {"6-K": 40, "40-F": 2}), "6-K financial results (fallback)")
        old = [["2024-02-04T02:12:14.000Z", "2024-02-03", "2.02"]]
        self.assertEqual(yd.earnings_source(old, {"6-K": 1}), "6-K financial results (fallback)")
        self.assertEqual(yd.earnings_source(old, {"8-K": 3, "10-K": 1}), "none")

    def test_headline_classification_and_release_date(self):
        c = {k: yd.classify_headline(v) for k, v in AG_HEADLINES.items()}
        self.assertEqual(c, {"fin": "financial_results", "prod": "production_results",
                             "prod_old": "production_results", "call": "other", "drill": "other"})
        self.assertEqual(yd.release_date(AG_HEADLINES["fin"]), "2026-05-12")
        self.assertIsNone(yd.release_date("no date here"))

    def test_pick_exhibit(self):
        self.assertEqual(yd.pick_exhibit(["ag-2026q1x6k.htm", "ag-2026q1ceoxex993.htm",
                                          "ag-2026q1financialnrxex995.htm", "x-index.html"]),
                         "ag-2026q1financialnrxex995.htm")
        self.assertEqual(yd.pick_exhibit(["form6k.htm", "exhibit99-2.htm", "exhibit99-1.htm"]), "exhibit99-1.htm")
        self.assertEqual(yd.pick_exhibit(["d1dex991.htm", "d1d6k.htm"]), "d1dex991.htm")
        self.assertIsNone(yd.pick_exhibit(["form6k.htm"]))

    def test_fallback_blocks_acceptance_session_and_release_date(self):
        days = weekdays(date(2026, 5, 4), 15)
        rows = [  # released May 12 (headline), accepted 11:07 ET -> May 12
            {"acceptance_utc": "2026-05-12T15:07:18.000Z", "release_date": "2026-05-12",
             "category": "financial_results"},
            # released May 14 in the headline but accepted after the close: both May 14 and May 15 blocked
            {"acceptance_utc": "2026-05-14T21:30:00.000Z", "release_date": "2026-05-14",
             "category": "financial_results"},
            {"acceptance_utc": "2026-05-06T15:00:00.000Z", "release_date": "2026-05-06",
             "category": "production_results"},
            # before the window: dropped
            {"acceptance_utc": "2026-04-30T15:00:00.000Z", "release_date": "2026-04-30",
             "category": "financial_results"},
        ]
        self.assertEqual(yd.fallback_sessions(rows, days),
                         [date(2026, 5, 12), date(2026, 5, 14), date(2026, 5, 15)])
        sat = [{"acceptance_utc": "2026-05-09T14:00:00.000Z", "release_date": "2026-05-09",
                "category": "financial_results"}]                       # a Saturday release maps to Monday
        self.assertEqual(yd.fallback_sessions(sat, days), [date(2026, 5, 11)])

    def test_index_page_time_and_api_stamp_readings(self):
        # real pairs seen on Oct 11, 2026: STX's file is true UTC, LITE's (like Apple's) is shifted
        self.assertEqual(yd.reading_of("2026-07-28T20:07:21.000Z", "2026-07-28 16:07:21"), "utc")
        self.assertEqual(yd.reading_of("2026-08-12T00:24:11.000Z", "2026-08-11 16:24:11"), "shifted")
        self.assertEqual(yd.reading_of("2026-01-27T21:08:53.000Z", "2026-01-27 16:08:53"), "utc")     # EST
        with self.assertRaises(RuntimeError):
            yd.reading_of("2026-07-28T20:07:21.000Z", "2026-07-28 18:07:21")
        self.assertEqual(yd.et_to_utc_stamp("2026-07-28 16:07:21"), "2026-07-28T20:07:21.000Z")
        self.assertEqual(yd.et_to_utc_stamp("2026-01-27 16:08:53"), "2026-01-27T21:08:53.000Z")
        days = weekdays(date(2026, 7, 27), 5)
        # STX: after the close -> next session; test #32's Apple ("shifted") reading would have said Jul 28
        stx = [{"acceptance_utc": yd.et_to_utc_stamp("2026-07-28 16:07:21")}]
        self.assertEqual(yd.sessions_from(stx, days), [date(2026, 7, 29)])
        self.assertEqual(lm.earnings_session("2026-07-28T20:07:21.000Z", days, shifted=True), date(2026, 7, 28))

    def test_item202_rows_follow_the_test16_rule(self):
        from research.ep_test_v1.fetch_edgar import earnings_rows
        filings = {"rows": [["2026-02-04T02:12:14.000Z", "2026-02-03", "8-K", "2.02,9.01", "a1"],
                            ["2026-02-05T02:12:14.000Z", "2026-02-04", "8-K/A", "2.02", "a2"],
                            ["2026-03-05T02:12:14.000Z", "2026-03-04", "8-K", "5.02, 9.01", "a3"],
                            ["2026-04-05T02:12:14.000Z", "2026-04-04", "8-K", "7.01, 2.02", "a4"],
                            ["2026-04-06T02:12:14.000Z", "2026-04-05", "8-K", "12.02", "a5"]]}
        cols = {"form": [r[2] for r in filings["rows"]], "items": [r[3] for r in filings["rows"]],
                "acceptanceDateTime": [r[0] for r in filings["rows"]], "filingDate": [r[1] for r in filings["rows"]]}
        ours = yd.item202_rows(filings)
        self.assertEqual([r[:3] for r in ours], earnings_rows(cols))
        self.assertEqual([r[3] for r in ours], ["a1", "a4"])

    def test_earnings_dispatch_per_source(self):
        days = weekdays(date(2026, 1, 2), 60)
        f = lambda rows, forms: {"forms": forms, "rows": rows, "name": "x"}
        filings = {
            yd.CIKS["LITE"]: f([["2026-02-04T02:12:14.000Z", "2026-02-03", "8-K", "2.02,9.01", "L1"]], {"8-K": 5}),
            yd.CIKS["STX"]: f([["2026-01-27T21:08:53.000Z", "2026-01-27", "8-K", "2.02,7.01,9.01", "S1"]],
                              {"8-K": 5}),
            yd.CIKS["AG"]: f([], {"6-K": 30, "40-F": 1}),
            yd.CIKS["RNA"]: f([["2025-11-10T21:07:25.000Z", "2025-11-10", "8-K", "2.02,9.01", "R1"]], {"8-K": 9}),
            yd.CIKS["HL"]: f([], {"10-K": 1}),
        }
        accepted = {"L1": "2026-02-03 16:12:14", "S1": "2026-01-27 16:08:53", "G1": "2026-02-19 12:33:37",
                    "G2": "2026-01-15 12:40:05"}
        six = [{"acceptance": "2026-02-19T17:33:37.000Z", "filing_date": "2026-02-19", "release_date": "2026-02-19",
                "category": "financial_results", "form": "6-K/A", "accession": "G1"},
               {"acceptance": "2026-01-15T17:40:05.000Z", "filing_date": "2026-01-15", "release_date": "2026-01-15",
                "category": "production_results", "form": "6-K", "accession": "G2"}]
        with mock.patch.object(lm, "calibrate", return_value={"shifted": True}), \
                mock.patch.object(yd, "fetch_filings", side_effect=lambda cik, data: filings[cik]), \
                mock.patch.object(yd, "fetch_accepted", side_effect=lambda cik, acc, data: accepted[acc]), \
                mock.patch.object(yd, "fetch_6k", return_value=six):
            sessions, cov, cal = yd.earnings(days, tickers=("LITE", "STX", "AG", "RNA", "HL"))
        self.assertEqual(sessions["LITE"], [date(2026, 2, 4)])          # 16:12 ET Feb 3 -> Feb 4
        self.assertEqual(cov["LITE"]["filings_used"][0]["api_stamp_reading"], "shifted")
        self.assertEqual(sessions["STX"], [date(2026, 1, 28)])          # 16:08 ET Jan 27 -> Jan 28
        self.assertEqual(cov["STX"]["filings_used"][0]["api_stamp_reading"], "utc")
        self.assertEqual(cov["STX"]["sessions_with_test32_apple_reading"], ["2026-01-27"])
        self.assertEqual(sessions["AG"], [date(2026, 2, 19)])           # 6-K/A counts; production not used
        self.assertEqual(cov["AG"]["production_release_sessions_not_used"], [date(2026, 1, 15)])
        self.assertEqual(cov["AG"]["source"], "6-K financial results (fallback)")
        self.assertEqual(sessions["RNA"], [])                           # Avidity: none in 2026 (Nov 2025 dropped)
        self.assertEqual(cov["RNA"]["filings_used"], [])
        self.assertEqual(cov["RNA"]["wheel_window_last_session"], "2026-02-25")
        self.assertEqual((sessions["HL"], cov["HL"]["source"]), ([], "none"))
        self.assertIn("cannot be applied", cov["HL"]["flag"])

    def test_cik_check_explains_rna(self):
        rows = {str(i): {"cik_str": c, "ticker": t, "title": t} for i, (t, c) in enumerate(yd.CIKS.items())}
        rows["RNAx"] = {"cik_str": 2093101, "ticker": "RNA", "title": "Atrium Therapeutics, Inc."}
        rows = {k: v for k, v in rows.items() if not (v["ticker"] == "RNA" and v["cik_str"] == 1599901)}
        bad, explained = yd.check_ciks(rows)
        self.assertEqual((bad, explained), ({}, {"RNA": (1599901, 2093101)}))
        rows["0"] = {"cik_str": 1, "ticker": "PRAX", "title": "x"}
        self.assertEqual(yd.check_ciks(rows)[0], {"PRAX": (1689548, 1)})


# ---------------------------------------------------------------- corporate actions

def real_actions():
    """The Alpaca records fetched Oct 11, 2026 (abridged to the fields used)."""
    return {
        "forward_splits": [{"ex_date": "2026-05-08", "new_rate": 5, "old_rate": 1, "symbol": "CVNA",
                            "id": "5a09d820-e471-444e-bff2-63695122060e"}],
        "cash_dividends": [{"ex_date": "2026-03-25", "rate": 0.74, "special": False, "symbol": "STX", "id": "a"},
                           {"ex_date": "2025-12-24", "rate": 0.74, "special": False, "symbol": "STX", "id": "b"}],
        "cash_mergers": [{"acquiree_symbol": "RNAM", "acquirer_symbol": "NVS", "effective_date": "2026-02-27",
                          "rate": 72, "id": "924ad173-9e03-4e63-8067-d57ef37ab24b"},
                         {"acquiree_symbol": "RNAM", "effective_date": "2026-02-27", "payable_date": "2026-03-04",
                          "rate": 72, "id": "90092415-0851-41ab-a3c8-d1621866a790"}],
        "name_changes": [{"new_symbol": "RNAM", "old_symbol": "RNA", "process_date": "2026-02-26",
                          "id": "ef20bdb4-1b98-4f34-8f70-904e4ee88109"}],
        "spin_offs": [{"ex_date": "2026-02-27", "new_rate": 0.1, "new_symbol": "RNA", "source_rate": 1,
                       "source_symbol": "RNAM", "id": "8e1c69a9-37ec-4fc6-975b-b4db8c1d5fbe"}],
    }


class CorporateActions(unittest.TestCase):
    def test_audit_sorts_actions(self):
        aud = yd.audit_corporate_actions(real_actions())
        self.assertEqual(sorted((r["type"], r["symbol"]) for r in aud["handled_by_engine"]),
                         [("cash_dividends", "STX"), ("forward_splits", "CVNA")])
        self.assertEqual(len(aud["handled_here"]), 4)          # 2 merger rows, rename, spin-off
        self.assertEqual((aud["flagged"], aud["outside_window"]), ([], 1))
        ca = real_actions()
        ca["reverse_splits"] = [{"ex_date": "2026-06-01", "symbol": "RIVN", "id": "r"}]
        ca["cash_dividends"].append({"ex_date": "2026-07-01", "rate": 5.0, "special": True, "symbol": "HL", "id": "s"})
        ca["cash_mergers"].append({"acquiree_symbol": "AG", "effective_date": "2026-08-01", "rate": 20, "id": "m"})
        flagged = {(r["type"], r["symbol"]) for r in yd.audit_corporate_actions(ca)["flagged"]}
        self.assertEqual(flagged, {("reverse_splits", "RIVN"), ("cash_dividends", "HL"), ("cash_mergers", "AG")})

    def test_delisting_config_matches_alpaca(self):
        self.assertTrue(yd.check_delisting(real_actions()))
        for path, value in ((("cash_mergers", 0, "rate"), 71), (("spin_offs", 0, "new_rate"), 0.2),
                            (("name_changes", 0, "process_date"), "2026-02-25")):
            ca = real_actions()
            ca[path[0]][path[1]][path[2]] = value
            with self.assertRaises(RuntimeError):
                yd.check_delisting(ca)
        self.assertEqual((RNA["last_session"], RNA["effective"], RNA["cash_per_share"], RNA["spinoff_per_share"]),
                         (date(2026, 2, 25), date(2026, 2, 27), 72.0, 0.1))

    def test_splits_agree(self):
        aud = yd.audit_corporate_actions(real_actions())
        prov = mock.Mock()
        prov.splits.side_effect = lambda t: {date(2026, 5, 8): 5.0} if t == "CVNA" else {}
        self.assertEqual(yb.splits_agree(aud, prov), [("CVNA", "2026-05-08")])
        prov.splits.side_effect = lambda t: {}
        with self.assertRaises(RuntimeError):
            yb.splits_agree(aud, prov)


# ---------------------------------------------------------------- the RNA delisting

class Delisting(unittest.TestCase):
    def test_after_delisting_math(self):
        days = rna_days()
        closes = rna_closes(days)
        fake = MultiFake(days, {"RNA": closes}, rate=0.0365)
        last = date(2026, 2, 25)
        pts, led = yb.after_delisting(10_000.0, 100.0, 72.8, fake, days, last, RNA)
        self.assertEqual([d for d, _ in pts], [d for d in days if d > last])
        feb26 = 10_000.0 * (1 + 0.0365 / 365)
        self.assertAlmostEqual(pts[0][1], feb26 + 100 * 72.8)
        feb27 = feb26 * (1 + 0.0365 / 365) + 100 * (72.0 + 0.1 * 14.75)
        self.assertAlmostEqual(pts[1][1], feb27)
        self.assertEqual(led["conversion_day"], "2026-02-27")
        self.assertAlmostEqual(led["conversion_gain_vs_last_close"], 100 * (73.475 - 72.8))
        self.assertAlmostEqual(pts[-1][1], 10_000 + 100 * 72.8 + led["conversion_gain_vs_last_close"]
                               + led["interest_after_last_session"])

    def test_account_holding_shares_at_the_last_session(self):
        days = rna_days()
        closes = rna_closes(days, after_drop=60.0, drop_day=date(2026, 2, 6))   # first put assigned Feb 6
        fake = MultiFake(days, {"RNA": closes}, rate=0.04)
        s, ledger, curve, after = yb.run_account("RNA", MAIN, yb.SIZE, fake, days, {})
        self.assertEqual(s.days[-1], date(2026, 2, 25))
        self.assertIn("assigned", [t["how"] for t in s.trades])
        self.assertGreater(s.shares, 0)
        self.assertEqual([d for d, _ in curve], days)
        self.assertEqual(after["shares_converted"], s.shares)
        self.assertAlmostEqual(after["value_per_share"], 73.475)
        self.assertAlmostEqual(after["conversion_gain_vs_last_close"], s.shares * (73.475 - 60.0))
        self.assertTrue(all(w[3] <= date(2026, 2, 25) for w in fake.windows))  # nothing fetched after Feb 25
        rep = yb.account_report(s, ledger, curve, after, yb.SIZE)
        self.assertEqual(rep["ending_value"], round(curve[-1][1], 2))
        self.assertEqual(rep["wheel_last_session"], "2026-02-25")
        tt = rep["true_total"]
        self.assertAlmostEqual(sum(v for k, v in tt.items() if k != "equals_total_pnl"), tt["equals_total_pnl"],
                               delta=0.05)
        # after conversion the account is all cash: values rise only by interest
        tail = [v for d, v in curve if d > date(2026, 2, 27)]
        self.assertTrue(all(b >= a for a, b in zip(tail, tail[1:])))

    def test_open_option_at_the_last_session_is_settled_at_its_mid(self):
        days = rna_days()
        closes = rna_closes(days)
        fake = MultiFake(days, {"RNA": closes}, rate=0.0)
        s, ledger, curve, after = yb.run_account("RNA", MAIN, yb.SIZE, fake, days, {})
        last = s.trades[-1]
        if last["how"] == "open_at_end":
            self.assertAlmostEqual(after["open_option_settled_at_last_mid"], last["open_liability"])
        self.assertAlmostEqual(curve[days.index(date(2026, 2, 25))][1], s.curve[-1][1])
        self.assertAlmostEqual(curve[-1][1], s.curve[-1][1] + after["conversion_gain_vs_last_close"])

    def test_holding_rna(self):
        days = rna_days()
        closes = rna_closes(days)
        closes[days[-1]] = 10.0                                          # Atrium on the last day
        fake = MultiFake(days, {"RNA": closes}, rate=0.0)
        h, curve = yb.hold_account("RNA", fake, days)
        shares = 50_000 / 72.0
        self.assertAlmostEqual(h["shares_at_end_of_stock"], shares)
        self.assertAlmostEqual(h["ending_value"], round(shares * 73.475, 2), places=2)
        self.assertAlmostEqual(h["after_delisting"]["info_keeping_the_spinoff_shares_to_the_end_instead_usd"],
                               round(shares * 0.1 * (10.0 - 14.75), 2), places=2)
        self.assertEqual([d for d, _ in curve], days)

    def test_holding_entry_fallback_when_no_1545_bar(self):
        days = weekdays(date(2026, 1, 2), 10)
        fake = Fake(days, spots={days[1]: 50.0}, closes={days[-1]: 300.0}, rate=0.0)   # no spot on day 0
        fb = lambda t, d: {"price": 250.0, "bar_start_utc": "2026-01-02T20:44:00Z", "rule": "close of the last"}
        h, curve = yb.hold_account("PRAX", fake, days, spot_before=fb)
        self.assertEqual(h["entry_price_1545"], 250.0)
        self.assertIn("no 15:45 bar", h["entry_price_source"])
        self.assertAlmostEqual(h["ending_value"], 50_000 / 250.0 * 300.0)
        self.assertEqual(fake.spot("PRAX", days[0]), None)                 # the provider itself is untouched
        fake2 = Fake(days, spots={days[0]: 100.0}, rate=0.0)
        h2, _ = yb.hold_account("PRAX", fake2, days, spot_before=lambda *a: self.fail("fallback used"))
        self.assertEqual(h2["entry_price_source"], "open of the 15:45 SIP 1-minute bar")

    def test_non_delisted_holding_is_test29_hold_scaled(self):
        days = weekdays(date(2026, 3, 2), 12)
        fake = Fake(days, spots={days[0]: 80.0}, closes={days[-1]: 6.0}, splits={days[7]: 20.0}, rate=0.03)
        h, curve = yb.hold_account("CVNA", fake, days)
        ref = lb.hold_scaled("CVNA", fake, days, 50_000)
        self.assertAlmostEqual(h["ending_value"], round(ref["final_value"], 2))
        self.assertIsNone(h["after_delisting"])


# ---------------------------------------------------------------- the typical account and the checks

def per_from(pnls, drops, weekly):
    return {f"T{i}": {"total_pnl": p, "worst_drop_from_high_pct": dd, "avg_per_week": w, "ending_value": 50_000 + p,
                      "median_per_week": w, "weeks_at_least_1000": 0, "premiums_collected": 1.0}
            for i, (p, dd, w) in enumerate(zip(pnls, drops, weekly))}


class Checks(unittest.TestCase):
    def test_pass_edges(self):
        per = per_from([1, 1, 1, 1, 1, 1, 1, -1, -1, -1], [-10] * 5 + [-40] * 5, [1000.0] * 10)
        per["T4"]["worst_drop_from_high_pct"], per["T5"]["worst_drop_from_high_pct"] = -20.0, -30.0  # median -25.0
        c, detail, verdict, words = yb.checks(per)
        self.assertEqual(verdict, "PASS", words)
        self.assertEqual(detail["median_worst_drop_pct"], -25.0)
        self.assertTrue(words.startswith("PASS."))

    def test_each_check_can_fail(self):
        base = lambda: per_from([1] * 7 + [-1] * 3, [-10.0] * 10, [1000.0] * 10)
        per = base()
        per["T0"]["avg_per_week"] = 999.0                               # average 999.9
        self.assertFalse(yb.checks(per)[0]["C1_average_account_at_least_1000_per_week"])
        per = base()
        per["T6"]["total_pnl"] = 0.0                                    # breakeven is not profitable: 6 of 10
        c, detail, verdict, words = yb.checks(per)
        self.assertEqual((c["C2_at_least_7_of_10_profitable"], verdict), (False, "FAIL"))
        self.assertIn("6 of 10", words)
        per = base()
        for i in range(5):
            per[f"T{i}"]["worst_drop_from_high_pct"] = -25.02
        per["T5"]["worst_drop_from_high_pct"] = -25.0                   # median = (-25.02 + -25.0) / 2 < -25
        self.assertFalse(yb.checks(per)[0]["C3_median_account_worst_drop_at_most_25pct"])

    def test_typical_account(self):
        per = per_from([5_000, -2_000, 10_000, 0], [-5, -30, -12, -8], [120, -50, 250, 0])
        t = yb.typical(per)
        self.assertEqual(t["average"]["total_pnl"], 3_250.0)
        self.assertEqual(t["median"]["total_pnl"], 2_500.0)
        self.assertEqual(t["median"]["worst_drop_from_high_pct"], -10.0)
        self.assertEqual((t["best_account"]["ticker"], t["worst_account"]["ticker"]), ("T2", "T1"))
        self.assertEqual(t["profitable_accounts"], 2)
        self.assertEqual(t["average"]["avg_per_week"], statistics.mean([120, -50, 250, 0]))


# ---------------------------------------------------------------- end to end on a fake

class EndToEnd(unittest.TestCase):
    def test_run_all_and_holding(self):
        days = weekdays(date(2026, 2, 2), 45)
        series = {"LITE": wavy(days), "CVNA": wavy(days, amp=20, period=11),
                  "RNA": rna_closes(days, before=72.0)}
        fake = MultiFake(days, series, rate=0.04)
        earnings = {"LITE": [days[10]], "CVNA": [], "RNA": []}
        tickers = ("LITE", "CVNA", "RNA")
        res = yb.run_all(fake, days, earnings, list(yb.VERSIONS), log=lambda s: None, tickers=tickers)
        self.assertEqual(list(res), list(yb.VERSIONS))
        for name, r in res.items():
            rules, size = yb.VERSIONS[name]
            self.assertEqual((r["rules"], r["account_size"]), (asdict(rules), size))
            self.assertEqual(list(r["per_account"]), list(tickers))
            for t, v in r["per_account"].items():
                self.assertEqual(v["dollars"]["start_value"], size)
                self.assertEqual(len(r["curves"][t]), len(days))
                self.assertEqual(v["contracts_opened"], len([x for x in r["trades"] if x["ticker"] == t]))
            self.assertEqual(r["per_account"]["RNA"]["wheel_last_session"], "2026-02-25")
            self.assertIsNotNone(r["per_account"]["RNA"]["after_delisting"])
            self.assertEqual(r["typical_account"]["accounts"], 3)
        self.assertIn(yb.checks(res["main"]["per_account"])[2], ("PASS", "FAIL"))
        h = yb.run_holding(fake, days, tickers=tickers)
        self.assertEqual(list(h["per_account"]), list(tickers))
        self.assertEqual(h["typical_account"]["accounts"], 3)


if __name__ == "__main__":
    unittest.main()
