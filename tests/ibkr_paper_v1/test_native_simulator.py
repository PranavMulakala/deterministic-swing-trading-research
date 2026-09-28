"""Invented tapes test semantics; their profits are never strategy evidence."""
from datetime import datetime,timezone
import unittest
from cloud.ibkr_paper_v1.execution import plan,SYMBOL,NS
from cloud.ibkr_paper_v1.native_simulator import simulate


class NativeSimulationTests(unittest.TestCase):
    def setUp(self):
        self.start=int(datetime(2026,9,22,14,0,tzinfo=timezone.utc).timestamp())*NS
        signal={'id':'SYNTHETIC','contract':SYMBOL,'direction':1,'signal_ns':self.start,
                'stop_ticks':39990,'target_ticks':40060}
        quote={'received_ns':self.start+NS,'contract':SYMBOL,'data_type':1,
               'bid_ticks':40000,'ask_ticks':40001,'bid_size':1,'ask_size':1}
        self.value=plan(signal,quote,self.start+NS,400,'a'*64)

    def quote(self,millis,bid=40000,ask=None):
        return {'received_ns':self.start+millis*1_000_000,'event_id':millis,
                'kind':'quote','contract':SYMBOL,'data_type':1,'bid_ticks':bid,
                'ask_ticks':bid+1 if ask is None else ask,'bid_size':1,'ask_size':1}

    def trade(self,millis,price):
        return {'received_ns':self.start+millis*1_000_000,'event_id':millis,
                'kind':'trade','contract':SYMBOL,'data_type':1,'price_ticks':price,
                'size':1,'eligible':True}

    def test_entry_limit_never_fills_beyond_price_cap(self):
        r=simulate(self.value,[self.quote(1000),self.quote(1100,40004),self.quote(2000,40004)])
        self.assertEqual(r['status'],'NO_MODELED_FILL')
        self.assertIsNone(r['entry'])

    def test_target_touch_is_not_assumed_to_fill(self):
        r=simulate(self.value,[self.quote(1000),self.quote(1100),self.trade(1200,40060)])
        self.assertEqual(r['status'],'OPEN_POSITION_UNRESOLVED')
        r=simulate(self.value,[self.quote(1000),self.quote(1100),self.trade(1200,40061)],400)
        self.assertEqual(r['status'],'MODELED_ROUND_TRIP')
        self.assertEqual(r['net_pnl_cents'],2550)
        self.assertFalse(r['broker_execution_verified'])

    def test_stop_uses_last_trade_and_preserves_gap_loss(self):
        r=simulate(self.value,[self.quote(1000),self.quote(1100),self.quote(1200,39900)])
        self.assertEqual(r['status'],'OPEN_POSITION_UNRESOLVED')
        r=simulate(self.value,[self.quote(1000),self.quote(1100),self.trade(1200,39989),self.quote(1300,39900)],400)
        self.assertEqual(r['exit']['price_ticks'],39898)
        self.assertLess(r['net_pnl_cents'],-self.value['planned_risk_cents'])

    def test_stop_latency_is_not_filled_at_trigger(self):
        r=simulate(self.value,[self.quote(1000),self.quote(1100),self.trade(1200,39989),
                               self.quote(1250,39985),self.quote(1300,39970)],400)
        self.assertEqual(r['exit']['at_ns'],self.start+1_300_000_000)
        self.assertEqual(r['exit']['price_ticks'],39968)

    def test_unknown_fees_do_not_become_zero(self):
        r=simulate(self.value,[self.quote(1000),self.quote(1100),self.trade(1200,40061)])
        self.assertIsNotNone(r['gross_pnl_cents'])
        self.assertIsNone(r['net_pnl_cents'])

    def test_bad_data_blocks_economic_result(self):
        r=simulate(self.value,[self.quote(1000),self.quote(1100),self.trade(3000,40061)])
        self.assertEqual(r['status'],'DATA_QUALITY_BLOCKED')
        self.assertIsNone(r['net_pnl_cents'])
        with self.assertRaises(ValueError):simulate(self.value,[self.quote(1100),self.quote(1000)])
        with self.assertRaises(ValueError):simulate(self.value,[dict(self.quote(1000),data_type=3)])

    def test_first_quote_at_expiry_cannot_fill(self):
        r=simulate(self.value,[self.quote(1000,40004),self.quote(2000,40000)])
        self.assertEqual(r['status'],'NO_MODELED_FILL')

    def test_short_stop_buys_ask_and_short_target_uses_trade_through(self):
        signal={'id':'SYNTHETIC-SHORT','contract':SYMBOL,'direction':-1,'signal_ns':self.start,
                'stop_ticks':40010,'target_ticks':39940}
        value=plan(signal,dict(self.quote(1000),received_ns=self.start+NS),self.start+NS,400,'a'*64)
        r=simulate(value,[self.quote(1000),self.quote(1100),self.trade(1200,39939)],400)
        self.assertEqual(r['net_pnl_cents'],2600)
        r=simulate(value,[self.quote(1000),self.quote(1100),self.trade(1200,40011),self.quote(1300,40100)],400)
        self.assertEqual(r['exit']['price_ticks'],40103)
        self.assertLess(r['net_pnl_cents'],0)

if __name__=='__main__':unittest.main()
