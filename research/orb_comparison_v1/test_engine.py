"""Synthetic path, causality, cash and failure regression tests; offline."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import unittest

from . import engine as e, run, actions, execution_evidence as evidence


def spec():
    return json.loads((Path(__file__).parent/"spec.json").read_text())


def row(o=103, h=104, l=102, c=103, v=100):
    return dict(o=o, h=h, l=l, c=c, v=v, vw=o)


def scenario(symbols=("LITE",), days=("2026-01-02",), rvol=3):
    cfg = spec()
    cfg["symbols"] = list(symbols)
    sessions, bars, prepared = {}, {}, {}
    for day in days:
        start, end = e.at(day, "09:30"), e.at(day, "16:00")
        sessions[day] = (start, end)
        prepared[day] = {}
        for symbol in symbols:
            for step in (1, 5):
                bars[symbol, step] = bars.get((symbol, step), {})
                bars[symbol, step][day] = {start+timedelta(minutes=m): row() for m in range(0, 390, step)}
            prepared[day][symbol] = {"symbol": symbol, "day": day, "status": "eligible", "reasons": [], "rvol": e.D(rvol),
                                    "dollar_volume": e.D(100000000), "high": e.D(102), "low": e.D(98),
                                    "pattern": {"status": "signal", "time": e.at(day,"09:45"), "stop": e.D("99.99"), "confirmation_close": e.D(103)}}
    return cfg, sessions, bars, prepared


def simulate(data, **kwargs):
    return e.replay(*data, kwargs.pop("arm", "A"), kwargs.pop("bps", 10), **kwargs)


class PatternTests(unittest.TestCase):
    def setup_pattern(self):
        cfg, sessions, bars, prepared = scenario()
        f = prepared["2026-01-02"]["LITE"]
        rows = bars["LITE",5]["2026-01-02"]
        rows[e.at(f["day"],"09:35")] = row()
        rows[e.at(f["day"],"09:40")] = row(l=102)
        return f, rows, cfg

    def test_later_exact_touch_and_next_minute_entry(self):
        f, rows, cfg = self.setup_pattern()
        result = e.pattern(f, rows, cfg)
        self.assertEqual(result["time"], e.at(f["day"],"09:45"))
        self.assertEqual(result["stop"], e.D("99.99"))
        self.assertEqual(result["breakout_time"], e.at(f["day"],"09:40"))

    def test_cannot_retest_on_breakout_candle(self):
        f, rows, cfg = self.setup_pattern()
        for t in rows: rows[t] = row(l=102.5)
        rows[e.at(f["day"],"09:35")] = row(l=101)
        self.assertEqual(e.pattern(f, rows, cfg)["status"], "retest_expired")

    def test_stop_touch_invalidates_and_no_second_cycle(self):
        f, rows, cfg = self.setup_pattern()
        rows[e.at(f["day"],"09:40")]["l"] = 99.99
        self.assertEqual(e.pattern(f, rows, cfg)["status"], "retest_invalidated")

    def test_missing_pattern_unknown_not_no_breakout(self):
        f, rows, cfg = self.setup_pattern()
        del rows[e.at(f["day"],"09:40")]
        self.assertEqual(e.pattern(f, rows, cfg)["status"], "unknown_pattern_gap")

    def test_retest_open_must_be_strictly_above(self):
        f, rows, cfg = self.setup_pattern()
        rows[e.at(f["day"],"09:40")]["o"] = 102
        self.assertEqual(e.pattern(f, rows, cfg)["time"], e.at(f["day"],"09:50"))

    def test_late_confirmation_not_allowed(self):
        f, rows, cfg = self.setup_pattern()
        for t in rows: rows[t] = row(o=101,h=102,l=100,c=101)
        rows[e.at(f["day"],"10:55")] = row()
        rows[e.at(f["day"],"11:00")] = row()
        self.assertEqual(e.pattern(f, rows, cfg)["status"], "no_retest_before_deadline")


class LedgerTests(unittest.TestCase):
    def test_whole_shares_costs_time_exit_and_independent_ledger(self):
        result = simulate(scenario())
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["trades"]), 1)
        trade = result["trades"][0]
        self.assertEqual(trade["qty"], 7)
        self.assertEqual(trade["entry"], e.D("103.103"))
        self.assertEqual(trade["exit_price"], e.D("102.897"))
        self.assertEqual(trade["reason"], "time")
        self.assertEqual(trade["exit_time"], e.at("2026-01-02","15:55"))
        expected = 7*(e.D("102.897")*(1-e.D(".0001"))-e.D("103.103")*(1+e.D(".0001")))
        self.assertEqual(trade["pnl"], expected)
        self.assertEqual(result["terminal_equity"], 5000+expected)
        self.assertEqual(run.audit_ledger(result)["status"], "passed")

    def test_same_minute_both_levels_stop_first(self):
        data = scenario()
        data[2]["LITE",1]["2026-01-02"][e.at("2026-01-02","09:45")] = row(h=120,l=90)
        result = simulate(data)
        self.assertEqual(result["trades"][0]["reason"], "stop_intraminute")

    def test_target_gap_at_open_precedes_later_stop(self):
        data = scenario()
        data[2]["LITE",1]["2026-01-02"][e.at("2026-01-02","09:46")] = row(o=120,h=121,l=90,c=100)
        result = simulate(data)
        self.assertEqual(result["trades"][0]["reason"], "target_at_open")

    def test_gap_loss_not_capped_at_planned_risk(self):
        data = scenario()
        data[2]["LITE",1]["2026-01-02"][e.at("2026-01-02","09:46")] = row(o=50,h=51,l=49,c=50)
        result = simulate(data)
        trade = result["trades"][0]
        self.assertGreater(-trade["pnl"], trade["planned_risk"])
        self.assertEqual(trade["exit_price"], e.D("49.95"))
        self.assertEqual(result["halt_count"], 1)

    def test_time_exit_does_not_look_at_later_intraminute_stop(self):
        data = scenario()
        data[2]["LITE",1]["2026-01-02"][e.at("2026-01-02","15:55")] = row(l=90)
        self.assertEqual(simulate(data)["trades"][0]["reason"], "time")

    def test_missing_entry_rejects_and_never_searches_later(self):
        data = scenario()
        del data[2]["LITE",1]["2026-01-02"][e.at("2026-01-02","09:45")]
        result = simulate(data)
        self.assertTrue(result["complete"])
        self.assertEqual(result["trades"], [])
        self.assertEqual(result["status_counts"], {"missing_entry_minute": 1})

    def test_missing_held_minute_preserves_position_and_taints_future(self):
        data = scenario(days=("2026-01-02", "2026-01-05"))
        del data[2]["LITE",1]["2026-01-02"][e.at("2026-01-02","09:46")]
        result = simulate(data)
        self.assertFalse(result["complete"])
        self.assertIsNone(result["terminal_equity"])
        self.assertEqual(len(result["open_positions"]), 1)
        self.assertEqual(result["status_counts"]["not_evaluated_after_unresolved"], 1)
        self.assertEqual(run.audit_ledger(result)["open_positions_preserved"], 1)

    def test_identical_strategy_only_rvol_changes(self):
        data = scenario(rvol=1)
        a, b = simulate(data), simulate(data, arm="B")
        self.assertEqual(len(a["trades"]), 1)
        self.assertEqual(b["status_counts"], {"rvol_filter": 1})
        data = scenario(rvol=2)
        a, b = simulate(data), simulate(data, arm="B")
        self.assertEqual(a["trades"], b["trades"])

    def test_simultaneous_priority_and_no_intraminute_capacity_lookahead(self):
        data = scenario(symbols=("LITE","COHR"))
        data[0]["portfolio"]["max_positions"] = 1
        for symbol in data[0]["symbols"]:
            data[2][symbol,1]["2026-01-02"][e.at("2026-01-02","09:45")] = row(l=90)
        result = simulate(data)
        self.assertEqual(result["trades"][0]["symbol"], "COHR")
        self.assertEqual(result["status_counts"]["position_capacity"], 1)

    def test_sale_proceeds_cannot_be_reused_same_day(self):
        data = scenario(symbols=("LITE","COHR"))
        data[0]["portfolio"].update(initial_cash=110, risk_fraction_per_entry=1, max_aggregate_planned_risk_fraction=1)
        data[3]["2026-01-02"]["COHR"]["pattern"]["time"] = e.at("2026-01-02","09:47")
        data[2]["LITE",1]["2026-01-02"][e.at("2026-01-02","09:46")] = row(o=120,h=121,l=119,c=120)
        result = simulate(data)
        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["status_counts"]["zero_quantity_cash"], 1)
        self.assertGreater(result["unsettled_cash"], e.D("103.2"))

    def test_proceeds_settle_next_session(self):
        data = scenario(days=("2026-01-02", "2026-01-05"))
        result = simulate(data)
        self.assertEqual(len(result["trades"]), 2)
        self.assertEqual(len([x for x in result["events"] if x["type"] == "settle"]), 1)
        run.audit_ledger(result)

    def test_entry_limit_cost_gate_and_zero_share_rejections(self):
        data = scenario()
        data[2]["LITE",1]["2026-01-02"][e.at("2026-01-02","09:45")]["o"] = 104
        self.assertEqual(simulate(data)["status_counts"], {"entry_limit_exceeded": 1})
        data = scenario()
        data[3]["2026-01-02"]["LITE"]["pattern"]["stop"] = e.D("102.9")
        self.assertEqual(simulate(data)["status_counts"], {"cost_to_stop_filter": 1})
        data = scenario()
        data[0]["portfolio"]["initial_cash"] = 50
        self.assertEqual(simulate(data)["trades"], [])

    def test_daily_loss_halt_prevents_later_entry(self):
        data = scenario(symbols=("LITE","COHR"))
        data[3]["2026-01-02"]["COHR"]["pattern"]["time"] = e.at("2026-01-02","09:47")
        data[2]["LITE",1]["2026-01-02"][e.at("2026-01-02","09:46")] = row(o=50,h=51,l=49,c=50)
        self.assertEqual(simulate(data)["status_counts"]["daily_loss_halt"], 1)


class InputAndStatisticsTests(unittest.TestCase):
    def test_empty_provider_window_is_distinct_from_missing_key(self):
        class Fake:
            def _request(self,*a,**kw): return {"symbol":"COHR","bars":None,"next_page_token":None}
        start=e.at("2026-01-07","11:53")
        result=evidence.window(Fake(),"COHR","bars",start,start+timedelta(seconds=59),pause=lambda _:None)
        self.assertTrue(result["terminal_collection_was_null"])
        self.assertEqual(result["rows"],[])
        class Invalid:
            def _request(self,*a,**kw): return {"symbol":"COHR","next_page_token":None}
        with self.assertRaises(ValueError): evidence.window(Invalid(),"COHR","bars",start,start,pause=lambda _:None)

    def test_quote_window_rejects_future_data_outside_bounds(self):
        class Fake:
            def _request(self,*a,**kw): return {"symbol":"COHR","quotes":[{"t":"2026-01-07T12:00:00-05:00"}],"next_page_token":None}
        start=e.at("2026-01-07","11:53")
        with self.assertRaises(ValueError): evidence.window(Fake(),"COHR","quotes",start,start,pause=lambda _:None)

    def test_evidence_client_does_not_allow_account_or_order_paths(self):
        client=evidence.EvidenceClient("fake","fake",transport=lambda *a:self.fail("transport reached"))
        for method,path,data in (("POST","/v2/orders",False),("GET","/v2/account",False),("GET","/v2/stocks/AAPL/quotes",True)):
            with self.assertRaises(ValueError): client._request(method,path,data_api=data)

    def test_features_use_only_past_days_not_today_full_coverage(self):
        cfg = spec()
        days = [(e.at("2025-12-01","09:30")+timedelta(days=i)).date().isoformat() for i in range(21)]
        cfg, sessions, bars, _ = scenario(days=days)
        cfg["eligibility"]["min_median_dollar_volume"] = 1
        for d in days:
            for r in bars["LITE",5][d].values(): r.update(h=110,l=90)
        result = e.features("LITE",20,days,sessions,bars,{"LITE":set()},cfg)
        self.assertEqual(result["status"], "eligible")
        self.assertEqual(result["atr"], e.D(20))
        day = days[-1]
        del bars["LITE",5][day][e.at(day,"15:55")]
        self.assertEqual(e.features("LITE",20,days,sessions,bars,{"LITE":set()},cfg),result)
        del bars["LITE",5][days[0]][e.at(days[0],"15:55")]
        self.assertIn("incomplete_lagged_inputs",e.features("LITE",20,days,sessions,bars,{"LITE":set()},cfg)["reasons"])

    def test_action_window_and_unknown_action_coverage(self):
        payload = {"complete":True,"query":{"symbols":"LITE","start":"2025-10-01","end":"2026-09-07"},
                   "pages":[{"corporate_actions":{},"next_page_token":None}],
                   "assets_current_not_point_in_time":{"LITE":{"symbol":"LITE","class":"us_equity","exchange":"NASDAQ"}}}
        self.assertEqual(e.action_dates(payload,["LITE"]),{"LITE":set()})
        payload["pages"][0]["corporate_actions"]={"forward_splits":[{"symbol":"LITE","ex_date":"2026-01-01"}]}
        self.assertEqual(e.action_dates(payload,["LITE"]),{"LITE":{"2026-01-01"}})
        payload["pages"][0]["corporate_actions"]={"unknown":[{}]}
        with self.assertRaises(ValueError): e.action_dates(payload,["LITE"])

    def test_action_client_cannot_read_accounts_or_mutate(self):
        calls=[]
        client=actions.ActionClient("fake","fake",transport=lambda *a:calls.append(a))
        for method,path,data in (("POST","/v2/orders",False),("GET","/v2/account",False),("GET","/v2/assets/AAPL",False),
                                 ("GET","/v1/corporate-actions",False)):
            with self.assertRaises(ValueError): client._request(method,path,data_api=data)
        self.assertEqual(calls,[])

    def test_bootstrap_reproducible_paired_and_unavailable_if_tainted(self):
        cfg=spec()
        cfg["uncertainty"]["resamples"]=100
        a={"complete":True,"net_return":e.D(0),"daily":[{"day":str(i),"return":e.D(0)} for i in range(10)]}
        b={"complete":True,"net_return":e.D(".1"),"daily":[{"day":str(i),"return":e.D(".01")} for i in range(10)]}
        self.assertEqual(run.paired(a,b,cfg),run.paired(a,b,cfg))
        self.assertEqual(run.paired(a,b,cfg)["mean_daily_difference_ci"],[.01,.01])
        b["complete"]=False
        self.assertIsNone(run.paired(a,b,cfg)["mean_daily_difference_ci"])

    def test_independent_ledger_detects_corruption(self):
        result=simulate(scenario())
        result["events"][0]["cost"] += 1
        with self.assertRaises(AssertionError): run.audit_ledger(result)


if __name__ == "__main__":
    unittest.main()
