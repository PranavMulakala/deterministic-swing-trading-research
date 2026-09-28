from copy import deepcopy
from datetime import datetime,timedelta
import json
from pathlib import Path
import unittest

from .common import D,NS,nanos,iso,Quotes,screen,inputs,key
from .engine import replay,trade_stop
from .run import audit
from .collect import Client,fetch
from .verify_execution import Source,decimals


def quote(t,bid=99.95,ask=100,bs=100,ask_size=100,**changes):
    return {"t":iso(t),"bp":bid,"ap":ask,"bs":bs,"as":ask_size,"c":["R"],**changes}


def fixture(symbols=("LITE",),days=("2026-01-02",),rvol=3):
    spec,cfg,_=inputs()
    spec["symbols"]=list(symbols)
    prepared,entries,streams={},{},{}
    for day in days:
        prepared[day]={}
        for symbol in symbols:
            t=nanos(day+"T09:45:00-05:00")
            f={"symbol":symbol,"day":day,"status":"eligible","rvol":str(rvol),"dollar_volume":"100000000",
               "pattern":{"status":"signal","time":day+"T09:45:00-05:00","stop":"95","confirmation_close":"100"}}
            prepared[day][symbol]=f
            entry=quote(t+NS//2)
            entries[key(f)]={"rows":[entry]}
            streams[key(f)]={"quotes":{"rows":[entry,quote(nanos(day+"T15:55:00-05:00"),101,101.05)]},"trades":{"rows":[]}}
    return spec,cfg,prepared,entries,streams


def simulate(data,arm="A",bps=10,delay=1): return replay(*data,arm,bps,delay)


class QuoteTests(unittest.TestCase):
    def test_latest_prior_no_future_and_exact_age_boundary(self):
        _,cfg,_=inputs(); t=nanos("2026-01-02T14:45:00Z")
        idx=Quotes([quote(t),quote(t+2*NS,80,81)])
        self.assertEqual(idx.at(t+NS,cfg)["bid"],D("99.95"))
        self.assertEqual(idx.at(t+NS+1,cfg)["status"],"unknown_stale_quote")
        self.assertEqual(idx.at(t-1,cfg)["status"],"unknown_no_quote")

    def test_invalid_latest_does_not_fall_back(self):
        _,cfg,_=inputs(); t=100*NS
        for changes in ({"bp":True},{"ap":float("nan")},{"bs":0},{"bp":101},{"c":["H"]}):
            idx=Quotes([quote(t),quote(t+1,**changes)])
            self.assertNotEqual(idx.at(t+2,cfg)["status"],"valid")

    def test_same_timestamp_conflict_unknown_but_identical_duplicate_valid(self):
        _,cfg,_=inputs(); t=100*NS
        self.assertEqual(Quotes([quote(t),quote(t,98,99)]).at(t,cfg)["status"],"unknown_same_timestamp_conflict")
        self.assertEqual(Quotes([quote(t),quote(t)]).at(t,cfg)["status"],"valid")

    def test_spread_cost_and_price_ceiling_remain_enforced(self):
        spec,cfg,p,_,_=fixture(); f=p["2026-01-02"]["LITE"]; t=100*NS
        q=Quotes([quote(t,99,100)]).at(t,cfg)
        self.assertEqual(screen(f,q,10,spec,cfg)["status"],"reject_spread")
        q=Quotes([quote(t,100.9,101)]).at(t,cfg)
        self.assertEqual(screen(f,q,10,spec,cfg)["status"],"reject_entry_limit")
        f["pattern"]["stop"]="99.9"
        self.assertEqual(screen(f,Quotes([quote(t)]).at(t,cfg),10,spec,cfg)["status"],"reject_cost_to_stop")

    def test_odd_lot_stop_allowed_derivative_and_out_of_sequence_excluded(self):
        _,cfg,_=inputs()
        self.assertTrue(trade_stop([{"p":94,"c":["@","I"]}],D(95),cfg))
        for c in (["@","4","I"],["Z"],["P"],["B"],None):
            self.assertFalse(trade_stop([{"p":94,"c":c}],D(95),cfg))


class LedgerTests(unittest.TestCase):
    def test_daily_loss_halt_blocks_a_later_signal(self):
        data=fixture(symbols=("LITE","COHR")); day="2026-01-02"
        t=nanos(day+"T09:45:10-05:00")
        data[4][day+"_LITE"]["quotes"]["rows"].insert(1,quote(t,50,50.05))
        f=data[2][day]["COHR"]; f["pattern"]["time"]=day+"T09:45:20-05:00"
        data[3][day+"_COHR"]["rows"][0]["t"]=iso(t+10*NS+NS//2)
        r=simulate(data)
        self.assertEqual(r["halt_count"],1)
        self.assertEqual(r["status_counts"]["daily_loss_halt"],1)

    def test_cannot_spend_sale_proceeds_again_same_day(self):
        data=fixture(symbols=("LITE","COHR")); day="2026-01-02"
        data[0]["portfolio"].update(initial_cash=110,risk_fraction_per_entry=1,max_aggregate_planned_risk_fraction=1)
        t=nanos(day+"T09:45:10-05:00")
        data[4][day+"_LITE"]["quotes"]["rows"].insert(1,quote(t,112,112.05))
        f=data[2][day]["COHR"]; f["pattern"]["time"]=day+"T09:45:20-05:00"
        data[3][day+"_COHR"]["rows"][0]["t"]=iso(t+10*NS+NS//2)
        r=simulate(data)
        self.assertEqual(len(r["trades"]),1)
        self.assertEqual(r["status_counts"]["zero_quantity_cash"],1)
        audit(r,*data[:2])

    def test_unfilled_partial_exit_preserves_remaining_basis_and_cash(self):
        data=fixture(); t=nanos("2026-01-02T09:45:10-05:00")
        data[4]["2026-01-02_LITE"]["quotes"]["rows"].insert(1,quote(t,112,112.05,1))
        r=simulate(data)
        self.assertFalse(r["complete"])
        self.assertEqual(r["open_positions"]["LITE"]["qty"],3)
        self.assertEqual(r["partial_exit_fill_count"],1)
        audit(r,*data[:2])

    def test_aggregate_risk_caps_third_position_before_displayed_size(self):
        data=fixture(symbols=("LITE","COHR","CIEN"))
        data[0]["portfolio"]["max_positions"]=3
        r=simulate(data)
        entries=[e for e in r["events"] if e["type"]=="entry"]
        self.assertEqual([e["qty"] for e in entries],[4,4,1])
        audit(r,*data[:2])

    def test_future_only_quote_cannot_create_entry(self):
        data=fixture(); t=nanos("2026-01-02T09:45:01.100000000-05:00")
        data[3]["2026-01-02_LITE"]["rows"][0]["t"]=iso(t)
        self.assertEqual(simulate(data)["status_counts"],{"unknown_no_quote":1})

    def test_time_exit_works_without_any_one_minute_bars(self):
        data=fixture(); r=simulate(data)
        self.assertTrue(r["complete"])
        self.assertEqual(len(r["trades"]),1)
        self.assertEqual(r["trades"][0]["reason"],"time")
        self.assertEqual(r["trades"][0]["entry"],D("100.100"))
        self.assertEqual(r["trades"][0]["qty"],4)
        self.assertTrue(r["stale_mark_intervals"])
        self.assertEqual(audit(r,*data[:2])["status"],"passed")

    def test_stop_quote_triggers_latency_and_gap_price(self):
        data=fixture(); s=data[4]["2026-01-02_LITE"]; t=nanos("2026-01-02T09:45:10-05:00")
        s["quotes"]["rows"].insert(1,quote(t,90,90.05))
        r=simulate(data); ev=[x for x in r["events"] if x["type"]=="exit"][0]
        self.assertEqual(nanos(ev["time"]),t+100000000)
        self.assertEqual(ev["price"],D("89.910"))
        self.assertGreater(-ev["pnl"],25)

    def test_target_can_reverse_during_latency(self):
        data=fixture(); t=nanos("2026-01-02T09:45:10-05:00")
        rows=data[4]["2026-01-02_LITE"]["quotes"]["rows"]
        rows[1:1]=[quote(t,112,112.05),quote(t+50000000,94,94.05)]
        r=simulate(data); ev=[x for x in r["events"] if x["type"]=="exit"][0]
        self.assertEqual(ev["reason"],"target")
        self.assertEqual(ev["price"],D("93.906"))
        self.assertLess(ev["pnl"],0)

    def test_partial_entries_cancel_unfilled_remainder(self):
        data=fixture()
        for obj in (data[3]["2026-01-02_LITE"],data[4]["2026-01-02_LITE"]["quotes"]): obj["rows"][0]["as"]=1
        r=simulate(data)
        self.assertEqual(r["partial_entry_count"],1)
        self.assertEqual(r["trades"][0]["qty"],1)
        self.assertEqual([x for x in r["events"] if x["type"]=="entry"][0]["requested_qty"],4)

    def test_partial_exit_and_ask_only_update_does_not_replenish_bid(self):
        data=fixture(); t=nanos("2026-01-02T09:45:10-05:00")
        rows=data[4]["2026-01-02_LITE"]["quotes"]["rows"]
        rows[1:1]=[quote(t,112,112.05,1),quote(t+200000000,112,112.06,1),quote(t+300000000,112.01,112.06,1),quote(t+400000000,112.02,112.07,5)]
        r=simulate(data)
        exits=[x for x in r["events"] if x["type"]=="exit"]
        self.assertEqual([x["qty"] for x in exits],[1,1,2])
        self.assertNotIn(iso(t+200000000),[x["time"] for x in exits])
        self.assertEqual(r["partial_exit_fill_count"],2)
        audit(r,*data[:2])

    def test_no_fresh_exit_quote_preserves_position_and_unknown_equity(self):
        data=fixture(days=("2026-01-02","2026-01-05"))
        data[4]["2026-01-02_LITE"]["quotes"]["rows"].pop()
        r=simulate(data)
        self.assertFalse(r["complete"])
        self.assertIsNone(r["terminal_equity"])
        self.assertEqual(r["open_positions"]["LITE"]["qty"],4)
        self.assertEqual(r["status_counts"]["not_evaluated_after_unresolved"],1)
        audit(r,*data[:2])

    def test_rvol_only_difference_and_zero_trade_arm_not_winning_evidence(self):
        data=fixture(rvol=1)
        self.assertEqual(len(simulate(data)["trades"]),1)
        b=simulate(data,arm="B")
        self.assertEqual(b["terminal_equity"],D(5000)); self.assertEqual(b["trades"],[])
        data=fixture(rvol=2)
        self.assertEqual(simulate(data)["trades"],simulate(data,arm="B")["trades"])

    def test_same_time_priority_no_future_exit_releases_capacity(self):
        data=fixture(symbols=("LITE","COHR")); data[0]["portfolio"]["max_positions"]=1
        r=simulate(data)
        self.assertEqual(r["trades"][0]["symbol"],"COHR")
        self.assertEqual(r["status_counts"]["position_capacity"],1)

    def test_proceeds_settle_only_on_later_session(self):
        data=fixture(days=("2026-01-02","2026-01-05")); r=simulate(data)
        self.assertEqual(len(r["trades"]),2)
        self.assertEqual(len([x for x in r["events"] if x["type"]=="settle"]),1)
        audit(r,*data[:2])

    def test_same_timestamp_trade_does_not_retroactively_stop_new_entry(self):
        data=fixture(); t=nanos("2026-01-02T09:45:01-05:00")
        data[4]["2026-01-02_LITE"]["trades"]["rows"]=[{"t":iso(t),"p":94,"c":["@","I"]}]
        self.assertEqual(simulate(data)["trades"][0]["reason"],"time")

    def test_same_timestamp_existing_trade_stop_precedes_quote_target(self):
        data=fixture(); t=nanos("2026-01-02T09:45:10-05:00")
        data[4]["2026-01-02_LITE"]["quotes"]["rows"].insert(1,quote(t,112,112.05))
        data[4]["2026-01-02_LITE"]["trades"]["rows"]=[{"t":iso(t),"p":94,"c":["@","I"]}]
        self.assertEqual(simulate(data)["trades"][0]["reason"],"stop")

    def test_unknown_existing_mark_prevents_extra_entry(self):
        data=fixture(symbols=("LITE","COHR"))
        f=data[2]["2026-01-02"]["COHR"]
        f["pattern"]["time"]="2026-01-02T09:46:00-05:00"
        t=nanos(f["pattern"]["time"])+NS//2
        data[3]["2026-01-02_COHR"]["rows"][0]["t"]=iso(t)
        r=simulate(data)
        self.assertEqual(r["status_counts"]["unknown_equity_mark"],1)

    def test_independent_accounting_detects_tampering(self):
        data=fixture(); r=simulate(data); r["events"][0]["qty"]+=1
        with self.assertRaises(AssertionError): audit(r,*data[:2])


class CollectionTests(unittest.TestCase):
    def test_mutations_and_account_paths_never_reach_transport(self):
        client=Client("fake","fake",transport=lambda *a:self.fail("transport"))
        for method,path,data in (("POST","/v2/orders",True),("GET","/v2/account",False),("GET","/v2/stocks/AAPL/quotes",True),("GET","/v2/stocks/LITE/bars",True)):
            with self.assertRaises(ValueError): client._request(method,path,data_api=data)

    def test_null_empty_terminal_and_stalled_pages(self):
        _,cfg,_=inputs(); t=100*NS
        class Empty:
            def _request(self,*a,**kw): return {"symbol":"LITE","quotes":None,"next_page_token":None}
        self.assertEqual(fetch(Empty(),"LITE","quotes",t,t+NS,cfg,pause=lambda _:None)["rows"],[])
        class Stalled:
            def _request(self,*a,**kw): return {"symbol":"LITE","quotes":[quote(t)],"next_page_token":"repeat"}
        with self.assertRaises(ValueError): fetch(Stalled(),"LITE","quotes",t,t+NS,cfg,pause=lambda _:None)

    def test_wrong_symbol_outside_interval_and_page_cap_fail(self):
        _,cfg,_=inputs(); t=100*NS
        for result in ({"symbol":"BAD","quotes":[]},{"symbol":"LITE","quotes":[quote(t+2*NS)]}):
            class Fake:
                def _request(self,*a,**kw): return result
            with self.assertRaises(ValueError): fetch(Fake(),"LITE","quotes",t,t+NS,cfg,pause=lambda _:None)
        cfg["max_pages_per_request"]=1
        class Capped:
            def _request(self,*a,**kw): return {"symbol":"LITE","quotes":[quote(t)],"next_page_token":"more"}
        with self.assertRaises(ValueError): fetch(Capped(),"LITE","quotes",t,t+NS,cfg,pause=lambda _:None)


class SourceVerificationTests(unittest.TestCase):
    def test_raw_source_oracle_uses_first_stop_before_later_target(self):
        _,cfg,_=inputs(); t=100*NS
        source=Source([quote(t),quote(t+2*NS,94,94.05),quote(t+4*NS,120,120.05)],[],cfg)
        self.assertEqual(source.first_trigger(t+NS, D(95),D(110),t+10*NS),(t+2*NS,0,"stop"))

    def test_raw_source_oracle_excludes_pre_entry_trade_and_stale_quote(self):
        _,cfg,_=inputs(); t=100*NS
        source=Source([quote(t)],[{"t":iso(t+NS),"p":90,"c":["I"]}],cfg)
        self.assertIsNone(source.quote(t+NS+1))
        self.assertEqual(source.first_trigger(t+NS,D(95),D(110),t+10*NS),(t+10*NS,2,"time"))

    def test_accounting_decoder_preserves_dates_and_exact_decimal(self):
        value=decimals({"time":"2026-01-02T14:45:00Z","cash":"4909.173342364","qty":2})
        self.assertEqual(value["cash"],D("4909.173342364"))
        self.assertEqual(value["qty"],2)
        self.assertEqual(value["time"],"2026-01-02T14:45:00Z")


if __name__=="__main__": unittest.main()
