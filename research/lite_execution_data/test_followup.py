"""Targeted offline tests of the new data/feasibility work, no real API calls."""
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest

from research.lite_execution_data import collect, quotes, study
from research.lite_reversal_v1 import experiment as e
from research.lite_reversal_v1.test_experiment import bars, config, snapshot


class CollectorTests(unittest.TestCase):
    def test_only_allowlisted_get_reaches_transport(self):
        calls=[]
        client=collect.ReadOnlyClient("fake-key","fake-secret",transport=lambda *a:calls.append(a))
        for method,path,data in (("POST","/v2/orders",False),("DELETE","/v2/orders",False),
            ("PATCH","/v2/account/configurations",False),("GET","/v2/assets/SPY",False),
            ("GET","/v2/account",True),("GET","https://evil.invalid",False)):
            with self.subTest(method=method,path=path),self.assertRaises(ValueError):
                client._request(method,path,data_api=data)
        self.assertEqual(calls,[])
        client._request("GET","/v2/account")
        self.assertEqual(calls[0][0],"GET")
        self.assertEqual(calls[0][1],"https://paper-api.alpaca.markets/v2/account")

    def test_get_with_body_or_mutation_permit_is_rejected(self):
        client=collect.ReadOnlyClient("fake-key","fake-secret",transport=lambda *a:self.fail("transport"))
        with self.assertRaises(ValueError):
            client._request("GET","/v2/account",body={})

    def test_paginated_data_must_finish_or_be_labeled_truncated(self):
        class Fake:
            def __init__(self): self.n=0
            def _request(self,*args,**kwargs):
                self.n+=1
                return {"symbol":"LITE","bars":[{"t":str(self.n)}],"next_page_token":str(self.n)}
        result=collect.paged(Fake(),"/v2/stocks/LITE/bars",{},"bars",max_pages=2)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["rows"]),2)

    def test_repeated_page_token_and_wrong_symbol_fail(self):
        class Fake:
            def _request(self,*args,**kwargs):
                return {"symbol":"LITE","bars":[{}],"next_page_token":"same"}
        with self.assertRaisesRegex(ValueError,"Stalled"):
            collect.paged(Fake(),"/v2/stocks/LITE/bars",{},"bars")
        with self.assertRaisesRegex(ValueError,"symbol"):
            collect.paged(Fake(),"/v2/stocks/SPY/bars",{},"bars")

    def test_probe_allowlist_excludes_account_identity_and_keeps_unknown(self):
        class Fake:
            def _request(self,method,path,**kwargs):
                if path in ("/v2/positions","/v2/orders"): return []
                return {"id":"private-id","account_number":"private-number","name":"private-name",
                        "cash":"500","status":"ACTIVE","fractional_trading":True}
        result=collect.probe(Fake())
        encoded=json.dumps(result)
        for private in ("private-id","private-number","private-name"):
            self.assertNotIn(private,encoded)
        self.assertIsNone(result["checks"]["account"]["data"]["trading_blocked"])
        self.assertTrue(result["checks"]["account_configuration"]["data"]["fractional_trading"])

    def test_output_is_exclusive_and_hashed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"result.json"
            value=collect.save(path,{"ok":True})
            self.assertEqual(value["sha256"],e.digest(path.read_bytes()))
            with self.assertRaises(FileExistsError): collect.save(path,{"ok":False})


class DataAndExecutionTests(unittest.TestCase):
    def write_bars(self,folder,rows=None,**updates):
        source=snapshot(rows)
        payload={"query":{"feed":"sip","adjustment":"raw","timeframe":"5Min"},
                 "path":"/v2/stocks/LITE/bars","rows":source["intraday"]["LITE"],
                 "pages":1,"complete":True}
        payload.update(updates)
        path=Path(folder)/"bars.json"
        path.write_text(json.dumps(payload))
        return path,source["calendar"]

    def test_raw_sip_keeps_honest_semantics(self):
        with tempfile.TemporaryDirectory() as folder:
            path,calendar=self.write_bars(folder)
            included,coverage=study.load_bars(path,"LITE",5,calendar)
            self.assertEqual(len(included),1)
            self.assertEqual(coverage["records"],78)
            self.assertEqual(coverage["sha256"],e.digest(path.read_bytes()))

    def test_incomplete_download_wrong_feed_and_duplicates_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            for updates in ({"complete":False},{"query":{"feed":"iex","adjustment":"raw","timeframe":"5Min"}},
                            {"path":"/v2/stocks/SPY/bars"}):
                path,calendar=self.write_bars(folder,**updates)
                with self.assertRaises(ValueError): study.load_bars(path,"LITE",5,calendar)
            path,calendar=self.write_bars(folder,bars()+[bars()[-1]])
            with self.assertRaises(ValueError): study.load_bars(path,"LITE",5,calendar)

    def test_missing_minute_is_not_filled(self):
        with tempfile.TemporaryDirectory() as folder:
            path,calendar=self.write_bars(folder,bars()[:-1])
            included,coverage=study.load_bars(path,"LITE",5,calendar)
            self.assertEqual(included,{})
            self.assertEqual(coverage["excluded"][0]["missing_minutes"],[955])

    def test_one_minute_replay_resolves_five_minute_ordering(self):
        fives=[replace(b,o=100,h=101,l=99,c=100,vw=100) for b in bars()]
        fives[6]=replace(fives[6],h=103,l=97)
        signal=e.Signal(5,98,102,100)
        intent={"cap":100.2,"qty":1.0,"planned_risk":2.298,"cash_before":500}
        start=fives[6].timestamp
        minutes=[replace(fives[6],timestamp=start+timedelta(minutes=i),o=100,h=101,l=99,c=100) for i in range(360)]
        minutes[0]=replace(minutes[0],h=103)
        minutes[1]=replace(minutes[1],l=97)
        five_trade,_=e.trade_day(fives,signal,intent,config(),10)
        minute_trade,_=study.minute_trade(fives,minutes,signal,intent,config(),10)
        self.assertEqual(five_trade["reason"],"stop")
        self.assertEqual(minute_trade["reason"],"target")
        self.assertEqual(minute_trade["signal_time"],start.isoformat())
        self.assertEqual(minute_trade["exit_time_precision"],"within_one_minute_bar")

    def test_missing_entry_minute_fails_not_next_available_fill(self):
        fives=bars()
        signal=e.Signal(5,98,102,100)
        with self.assertRaises(ValueError):
            study.minute_trade(fives,fives[7:],signal,{},config(),10)

    def test_capital_diagnostic_distinguishes_risk_from_cash(self):
        small=bars()
        for i,b in enumerate(small):
            small[i]=replace(b,o=b.o*4,h=b.h*4,l=b.l*4,c=b.c*4,vw=b.vw*4)
        result=study.capital_diagnostic({"2026-01-05":small},config())
        row=next(r for r in result if r["variant"]=="vwap_retest")
        self.assertEqual(row["whole_share_failures"],["risk"])
        self.assertGreater(row["minimum_equity_one_share"],500)

    def test_market_control_matches_dates_not_unrelated_returns(self):
        result=study.market_controls({"2026-01-05":bars()},{"2026-01-05":bars()},config())
        self.assertEqual(result["all_days"]["mean_lite_minus_spy_return"],0)


class QuoteTests(unittest.TestCase):
    def q(self,t="2026-01-05T15:00:00.999999999Z",**changes):
        return {"t":t,"bp":99,"ap":101,"bs":100,"as":100,"c":["R"],**changes}

    def test_nanoseconds_and_timezone_preserved(self):
        a=quotes.nanos("2026-01-05T15:00:00.999999999Z")
        b=quotes.nanos("2026-01-05T10:00:01-05:00")
        self.assertEqual(b-a,1)
        with self.assertRaises(ValueError): quotes.nanos("2026-01-05T15:00:00")

    def test_future_quote_never_used_even_one_nanosecond_later(self):
        cutoff=quotes.nanos("2026-01-05T15:00:00.999999998Z")
        self.assertEqual(quotes.quote_at([self.q()],cutoff,101)["status"],"UNKNOWN_NO_PRIOR_QUOTE")

    def test_last_quote_not_best_price_in_window(self):
        rows=[self.q(t="2026-01-05T15:00:00Z",ap=100),self.q(ap=102)]
        result=quotes.quote_at(rows,quotes.nanos("2026-01-05T15:00:01Z"),101)
        self.assertFalse(result["ask_within_raw_limit"])
        self.assertEqual(result["ask"],102)

    def test_one_second_freshness_boundary(self):
        row=self.q(t="2026-01-05T15:00:00Z")
        cutoff=quotes.nanos("2026-01-05T15:00:01Z")
        self.assertEqual(quotes.quote_at([row],cutoff,101)["status"],"OBSERVED")
        self.assertEqual(quotes.quote_at([row],cutoff+1,101)["status"],"UNKNOWN_STALE_QUOTE")

    def test_crossed_zero_nonfinite_and_nonregular_quotes_unknown(self):
        cutoff=quotes.nanos("2026-01-05T15:00:01Z")
        for change in ({"bp":102},{"bs":0},{"ap":float("nan")},{"c":["T"]},{"as":True}):
            with self.subTest(change=change):
                self.assertNotEqual(quotes.quote_at([self.q(**change)],cutoff,101)["status"],"OBSERVED")

    def test_conflicting_equal_timestamp_is_not_arbitrarily_sorted(self):
        result=quotes.quote_at([self.q(),self.q(ap=102)],quotes.nanos("2026-01-05T15:00:01Z"),101)
        self.assertEqual(result["status"],"UNKNOWN_SAME_TIMESTAMP_ORDERING")

    def test_out_of_order_quotes_fail(self):
        rows=[self.q(),self.q(t="2026-01-05T15:00:00Z")]
        with self.assertRaises(ValueError): quotes.quote_at(rows,quotes.nanos("2026-01-05T15:00:01Z"),101)

    def test_spread_formula_and_equal_limit(self):
        result=quotes.quote_at([self.q()],quotes.nanos("2026-01-05T15:00:01Z"),101)
        self.assertEqual(result["full_spread_bps"],200)
        self.assertEqual(result["half_spread_bps"],100)
        self.assertTrue(result["ask_within_raw_limit"])


if __name__ == "__main__":
    unittest.main()
