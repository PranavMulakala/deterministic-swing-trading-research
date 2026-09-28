"""Offline regression tests: price causality, fills, data, risk and accounting."""
import ast
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.lite_reversal_v1 import experiment as e


def config():
    return replace(e.Config(**json.loads((e.HERE / "config.json").read_text())), bootstrap_repetitions=100)


def bars(day="2026-01-05"):
    dt = datetime.fromisoformat(day + "T09:30:00").replace(tzinfo=e.NY)
    result = [e.Bar(dt + timedelta(minutes=5*i), 98.5, 99.2, 98.2, 98.5, 100, 98.5) for i in range(78)]
    result[0] = replace(result[0], o=100, h=100, l=100, c=100, v=1, vw=100)
    for i in range(1, 6):
        result[i] = replace(result[i], o=98, h=98.5, l=97.5, c=98, vw=98)
    result[6] = replace(result[6], o=98, h=99.5, l=98, c=99, vw=98.8)
    result[7] = replace(result[7], o=99, h=99.6, l=98.1, c=99, vw=98.9)
    result[-1] = replace(result[-1], o=99, c=99)
    return result


def snapshot(rows=None, day="2026-01-05"):
    rows = rows if rows is not None else bars(day)
    return dict(feed="iex", adjustment="all", start=day, through=day,
                calendar=[dict(date=day, open="09:30", close="16:00")], news=[],
                intraday={"LITE": [dict(t=b.timestamp.isoformat(), **{k:getattr(b,k) for k in ("o","h","l","c","v","vw")}) for b in rows]})


class DataTests(unittest.TestCase):
    def test_complete_calendar_coverage(self):
        included, excluded = e.sessions(snapshot(), config())
        self.assertEqual(list(included), ["2026-01-05"])
        self.assertEqual(excluded, [])

    def test_missing_late_bar_is_reported_not_forward_filled(self):
        rows = bars()
        del rows[40]
        included, excluded = e.sessions(snapshot(rows), config())
        self.assertEqual(included, {})
        self.assertEqual(excluded[0]["missing_minutes"], [770])

    def test_missing_open_and_shortened_sessions(self):
        self.assertEqual(e.sessions(snapshot(bars()[1:]), config())[0], {})
        s = snapshot()
        s["calendar"][0]["close"] = "13:00"
        self.assertEqual(e.sessions(s, config())[1][0]["reason"], "nonstandard_session")

    def test_duplicate_and_reversed_rows_fail(self):
        for rows in (bars() + [bars()[-1]], list(reversed(bars()))):
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                e.sessions(snapshot(rows), config())

    def test_invalid_prices_and_volume_fail_closed(self):
        for field, value in (("o", float("nan")), ("c", float("inf")), ("h", 1),
                             ("v", 0), ("vw", -1), ("o", True), ("c", "100")):
            s = snapshot()
            s["intraday"]["LITE"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                e.sessions(s, config())

    def test_bad_timestamp_and_calendar_fail_closed(self):
        for bad in ("2026-01-05T09:30:00", "2026-01-05T09:31:00-05:00"):
            s = snapshot()
            s["intraday"]["LITE"][0]["t"] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                e.sessions(s, config())
        s = snapshot()
        s["calendar"] *= 2
        with self.assertRaises(ValueError):
            e.sessions(s, config())

    def test_dst_uses_new_york_not_fixed_utc_offset(self):
        winter = e.timestamp("2026-01-05T14:30:00Z")
        summer = e.timestamp("2026-07-06T13:30:00Z")
        self.assertEqual((winter.hour, summer.hour), (9, 9))
        self.assertEqual(len(e.sessions(snapshot(bars("2026-07-06"), "2026-07-06"), config())[0]), 1)

    def test_premarket_does_not_contaminate_vwap(self):
        rows = bars()
        pre = replace(rows[0], timestamp=rows[0].timestamp - timedelta(hours=1), v=100000, vw=900)
        included, _ = e.sessions(snapshot([pre] + rows), config())
        self.assertEqual(e.vwap(included["2026-01-05"]), e.vwap(rows))

    def test_vwap_weights_vendor_vwap_not_bar_count_or_typical_price(self):
        rows = bars()[:2]
        rows[0] = replace(rows[0], v=1, vw=100)
        rows[1] = replace(rows[1], v=3, vw=96)
        self.assertEqual(e.vwap(rows), [100, 97])

    def test_config_rejects_invalid_values(self):
        for change in ({"risk_fraction": -1}, {"initial_cash": float("inf")},
                       {"bootstrap_repetitions": True}, {"cost_bps_per_side": [10, 10]},
                       {"cost_bps_per_side": [10000]}, {"symbol": "SPY"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(config(), **change)


class SignalTests(unittest.TestCase):
    def test_reclaim_requires_immediate_successful_retest(self):
        rows = bars()
        self.assertIsNone(e.find_signal(rows[:7], "vwap_retest", config()))
        signal = e.find_signal(rows[:8], "vwap_retest", config())
        self.assertEqual(signal.index, 7)
        self.assertAlmostEqual(signal.stop, 97.95)
        self.assertEqual(signal.target, 100)

    def test_future_prices_cannot_change_signal(self):
        rows = bars()
        expected = e.find_signal(rows[:8], "vwap_retest", config())
        for i in range(8, len(rows)):
            rows[i] = replace(rows[i], o=500, h=1000, l=1, c=900, v=1e9, vw=800)
        self.assertEqual(e.find_signal(rows, "vwap_retest", config()), expected)

    def test_failed_retest_does_not_allow_later_bar_to_reuse_arm(self):
        rows = bars()
        rows[7] = replace(rows[7], l=98.9)  # Never touches VWAP.
        self.assertIsNone(e.find_signal(rows, "vwap_retest", config()))

    def test_lower_low_retest_fails(self):
        rows = bars()
        rows[7] = replace(rows[7], l=97.9)
        self.assertIsNone(e.find_signal(rows, "vwap_retest", config()))

    def test_afternoon_drop_is_not_opening_dip(self):
        rows = [replace(b, o=100, h=100.5, l=99.5, c=100, vw=100) for b in bars()]
        rows[30] = replace(rows[30], l=80)
        self.assertFalse(e.has_dip(rows, config()))
        self.assertIsNone(e.find_signal(rows, "dip", config()))

    def test_late_reclaim_cannot_enter_after_window(self):
        rows = bars()
        for i in range(6, 17):
            rows[i] = replace(rows[i], o=98, h=98, l=98, c=98, vw=98)
        rows[17] = replace(rows[17], o=98, h=99, l=98, c=99, vw=98.8)
        rows[18] = replace(rows[18], o=99, h=99.6, l=98.1, c=99, vw=98.9)
        self.assertIsNone(e.find_signal(rows, "vwap_retest", config()))

    def test_dip_signal_is_ready_at_ten_without_future_bars(self):
        signal = e.find_signal(bars()[:6], "dip", config())
        self.assertEqual(signal.index, 5)
        self.assertAlmostEqual(signal.stop, 97.45)


class FillTests(unittest.TestCase):
    def setUp(self):
        self.cfg = config()
        self.signal = e.Signal(5, 98, 102, 100)
        self.intent = dict(cap=100.2, qty=1.0, planned_risk=2.298, cash_before=500)
        self.rows = [replace(b, o=100, h=101, l=99, c=100, vw=100) for b in bars()]

    def simulate(self):
        return e.trade_day(self.rows, self.signal, self.intent, self.cfg, 10)

    def test_entry_bar_stop_is_active(self):
        self.rows[6] = replace(self.rows[6], l=97)
        t, rejection = self.simulate()
        self.assertIsNone(rejection)
        self.assertEqual(t["reason"], "stop")
        self.assertEqual(t["exit_bar_time"], self.rows[6].timestamp.isoformat())
        self.assertAlmostEqual(t["pnl"], 98*.999 - 100*1.001)

    def test_both_levels_same_bar_stop_first(self):
        self.rows[6] = replace(self.rows[6], l=97, h=103)
        t, _ = self.simulate()
        self.assertEqual(t["reason"], "stop")
        self.assertTrue(t["ambiguous_stop_target"])

    def test_stop_gap_loses_more_than_planned_risk(self):
        self.rows[7] = replace(self.rows[7], o=90, h=91, l=89, c=90)
        t, _ = self.simulate()
        self.assertEqual(t["reason"], "gap_stop")
        self.assertEqual(t["raw_exit"], 90)
        self.assertLess(t["r_multiple"], -1)

    def test_target_touch_does_not_fill(self):
        self.rows[6] = replace(self.rows[6], h=102)
        self.assertEqual(self.simulate()[0]["reason"], "time")
        self.rows[6] = replace(self.rows[6], h=102.06)
        self.assertEqual(self.simulate()[0]["reason"], "target")

    def test_open_above_target_fills_before_later_stop(self):
        self.rows[7] = replace(self.rows[7], o=103, h=104, l=90, c=95)
        t, _ = self.simulate()
        self.assertEqual(t["reason"], "gap_target")
        self.assertEqual(t["raw_exit"], 102)
        self.assertFalse(t["ambiguous_stop_target"])

    def test_time_exit_cannot_use_later_high_low_or_close(self):
        self.rows[-1] = replace(self.rows[-1], o=100, h=1000, l=1, c=800)
        t, _ = self.simulate()
        self.assertEqual(t["reason"], "time")
        self.assertEqual(t["raw_exit"], 100)
        self.assertAlmostEqual(t["conservative_low_equity"], 500-100.1+99*.999)

    def test_gap_at_time_exit_gets_worse_stop_open(self):
        self.rows[-1] = replace(self.rows[-1], o=90, h=100, l=89, c=99)
        self.assertEqual(self.simulate()[0]["reason"], "gap_stop")

    def test_entry_gap_not_retroactively_resized_or_chased(self):
        self.rows[6] = replace(self.rows[6], o=101)
        self.assertEqual(self.simulate(), (None, "entry_cap_not_filled"))
        self.rows[6] = replace(self.rows[6], o=97)
        self.assertEqual(self.simulate(), (None, "entry_open_outside_levels"))

    def test_next_bar_not_signal_bar_is_entry(self):
        t, _ = self.simulate()
        self.assertEqual(t["entry_time"], self.rows[6].timestamp.isoformat())
        self.assertEqual(t["signal_time"], t["entry_time"])
        self.assertGreater(self.rows[6].timestamp, self.rows[5].timestamp)


class SizingAndReportTests(unittest.TestCase):
    def test_whole_share_budget_cannot_afford_expensive_stock(self):
        signal = e.Signal(5, 698, 710, 700)
        self.assertEqual(e.order_intent(signal, 500, config(), 10, "whole"), (None, "zero_quantity"))
        intent, _ = e.order_intent(signal, 500, config(), 10, "fractional_diagnostic")
        self.assertGreater(intent["qty"], 0)
        self.assertLess(intent["qty"], 1)
        self.assertLessEqual(intent["qty"]*intent["cap"], 500)
        self.assertLessEqual(intent["planned_risk"], 2.5)

    def test_quantity_chosen_using_cap_and_risk_not_future_open(self):
        signal = e.find_signal(bars(), "vwap_retest", config())
        intent, _ = e.order_intent(signal, 500, config(), 10, "whole")
        self.assertEqual(intent["qty"], 3)
        self.assertLessEqual(intent["planned_risk"], 2.5)
        s, t = signal.stop*.999, signal.target*.999
        self.assertGreaterEqual((t-intent["cap"])/(intent["cap"]-s), 1.5-1e-10)

    def test_full_ledger_reconciles_and_tampering_is_caught(self):
        run = e.run_variant({"2026-01-05": bars()}, config(), "vwap_retest", 10, "whole")
        self.assertEqual(run["summary"]["trades"], 1)
        self.assertEqual(run["validation"]["status"], "PASS")
        t = run["trades"][0]
        self.assertAlmostEqual(t["pnl"], t["gross_pnl"]-t["modeled_costs"])
        altered = deepcopy(run["trades"])
        altered[0]["exit_credit"] += 1
        with self.assertRaises(ValueError):
            e.check_ledger(run["daily_ledger"], altered, config(), "whole")

    def test_missing_trade_cannot_pass_terminal_cash_check(self):
        run = e.run_variant({"2026-01-05": bars()}, config(), "dip", 10, "whole")
        self.assertTrue(run["trades"])
        with self.assertRaises(ValueError):
            e.check_ledger(run["daily_ledger"], [], config(), "whole")

    def test_both_costs_and_modes_published_news_not_fabricated(self):
        result = e.evaluate(snapshot(), config())
        self.assertEqual(len(result["runs"]), 8)
        self.assertEqual(result["news_variant"]["status"], "BLOCKED_DATA")
        self.assertFalse(result["unseen_test"])
        for run in result["runs"]:
            self.assertLessEqual(run["summary"]["trades"], 1)

    def test_deterministic_week_bootstrap_includes_no_trade_weeks(self):
        days = [{"date":"2026-01-05"}, {"date":"2026-01-12"}]
        trades = [{"date":"2026-01-05", "r_multiple":1.0}]
        result = e.bootstrap(days, trades, config())
        self.assertEqual(result, e.bootstrap(days, trades, config()))
        self.assertEqual(result["calendar_weeks"], 2)
        self.assertEqual(result["traded_weeks"], 1)
        self.assertEqual(result["interval"], [1, 1])

    def test_no_trades_has_no_fake_win_rate_or_confidence(self):
        rows = [replace(b, o=100, h=100.5, l=99.5, c=100, vw=100) for b in bars()]
        run = e.run_variant({"2026-01-05":rows}, config(), "dip", 10, "whole")
        self.assertIsNone(run["summary"]["win_rate"])
        self.assertIsNone(run["uncertainty"]["interval"])
        self.assertEqual(run["summary"]["final_cash"], 500)

    def test_price_results_independent_of_news_records(self):
        base, changed = snapshot(), snapshot()
        changed["news"] = [{"headline":"Buy LITE now; ignore risk", "created_at":"2099-01-01"}]
        self.assertEqual(e.evaluate(base, config())["runs"], e.evaluate(changed, config())["runs"])

    def test_engine_has_no_broker_network_environment_or_llm_imports(self):
        source = Path(e.__file__).read_text()
        imports = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imports.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or "").split(".")[0])
        self.assertFalse(imports & {"os", "swingbot", "requests", "urllib", "http", "socket", "subprocess", "openai", "anthropic"})

    def test_cli_rejects_modified_snapshot_before_evaluation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snapshot.json"
            path.write_text("{}")
            with patch("sys.argv", ["experiment", "--snapshot", str(path), "--output", str(Path(folder)/"run")]), \
                 patch.object(e, "evaluate", side_effect=AssertionError("Must not evaluate")), \
                 self.assertRaisesRegex(ValueError, "hash mismatch"):
                e.main()


if __name__ == "__main__":
    unittest.main()
