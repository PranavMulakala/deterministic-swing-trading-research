"""Synthetic order-lifecycle tests; no broker socket or real/paper fills."""
from datetime import datetime,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from decimal import Decimal

from cloud.ibkr_paper_v1.execution import ACCOUNT,SYMBOL,NS,Ledger,plan,bracket_orders
from cloud.ibkr_paper_v1.broker_snapshot import Snapshot
from ibapi.message import OUT
from ibapi.common import PROTOBUF_MSG_ID
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
from cloud.ibkr_paper_v1.margin_preview import Preview,number


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'ledger.sqlite'
        self.ledger=Ledger(self.path)
        self.stamp=int(datetime(2026,9,22,14,0,tzinfo=timezone.utc).timestamp())*NS
        self.signal={'id':'SYNTHETIC-1','contract':SYMBOL,'direction':1,
                     'signal_ns':self.stamp,'stop_ticks':39990,'target_ticks':40060}
        self.quote={'received_ns':self.stamp+NS,'contract':SYMBOL,'data_type':1,
                    'bid_ticks':40000,'ask_ticks':40001,'bid_size':1,'ask_size':1}
        self.value=plan(self.signal,self.quote,self.stamp+NS,400,'a'*64)

    def tearDown(self):
        self.ledger.close();self.tmp.cleanup()

    def reserve(self):
        self.ledger.reserve(self.value,100,self.stamp+NS)

    def raw(self,leg,order_id):
        return {'account':ACCOUNT,'contract':SYMBOL,'quantity':1,
                'side':'BUY' if leg=='entry' else 'SELL','order_id':order_id}

    def test_native_bracket_links_and_expiration(self):
        orders=bracket_orders(self.value,100)
        self.assertEqual([x.transmit for x in orders],[False,False,True])
        self.assertEqual([x.parentId for x in orders],[0,100,100])
        self.assertEqual([x.account for x in orders],[ACCOUNT]*3)
        self.assertEqual([x.orderType for x in orders],['LMT','LMT','STP'])
        self.assertEqual(orders[2].triggerMethod,2)
        self.assertEqual(orders[0].goodTillDate,'20260922 14:00:02 UTC')
        self.assertEqual(orders[2].tif,'GTC')

    def test_snapshot_cannot_transmit_or_cancel_orders(self):
        snapshot=Snapshot()
        for message in (OUT.PLACE_ORDER,OUT.CANCEL_ORDER,OUT.REQ_GLOBAL_CANCEL,OUT.REQ_AUTO_OPEN_ORDERS):
            with self.assertRaises(RuntimeError):snapshot.sendMsg(message,'')
            with self.assertRaises(RuntimeError):snapshot.sendMsgProtoBuf(message+PROTOBUF_MSG_ID,b'')

    def test_snapshot_rejects_other_accounts(self):
        snapshot=Snapshot()
        self.assertFalse(snapshot.account_ok('U123'))
        self.assertEqual(snapshot.failure,'ACCOUNT_MISMATCH')
        self.assertEqual(snapshot.records,[])

    def test_preview_never_allows_executable_or_other_account_order(self):
        p=Preview();p.accounts=[ACCOUNT]
        c=Contract();c.conId=123;c.symbol='MNQ';c.localSymbol=SYMBOL;c.secType='FUT'
        c.exchange='CME';c.currency='USD';c.multiplier='2';c.lastTradeDateOrContractMonth='20261218'
        order=Order();order.orderId=1;order.account=ACCOUNT;order.action='BUY'
        order.totalQuantity=Decimal(1);order.orderType='LMT';order.lmtPrice=10000
        order.whatIf=True;order.transmit=True
        with patch.object(EClient,'placeOrder') as submit:
            p.placeOrder(1,c,order)
            self.assertEqual(submit.call_count,1)
            order.whatIf=False
            with self.assertRaises(RuntimeError):p.placeOrder(1,c,order)
            order.whatIf=True;order.account='U123'
            with self.assertRaises(RuntimeError):p.placeOrder(1,c,order)
            self.assertEqual(submit.call_count,1)
        with self.assertRaises(RuntimeError):p.sendMsg(OUT.PLACE_ORDER,'')
        with self.assertRaises(RuntimeError):p.sendMsgProtoBuf(OUT.PLACE_ORDER+PROTOBUF_MSG_ID,b'')
        self.assertIsNone(number(float('nan')))
        self.assertIsNone(number(1.7976931348623157e308))

    def test_risk_fees_clock_and_delayed_quotes_fail_closed(self):
        self.assertEqual(self.value['planned_risk_cents'],1150)
        for patch in ({'received_ns':self.stamp},{'data_type':3},{'data_type':True},{'bid_size':0},{'contract':'MNQU6'}):
            with self.assertRaises(ValueError):
                plan(self.signal,dict(self.quote,**patch),self.stamp+NS,400,'a'*64)
        with self.assertRaises(ValueError):plan(self.signal,self.quote,self.stamp+NS,600,'a'*64)
        with self.assertRaises(ValueError):plan(self.signal,self.quote,self.stamp+2*NS,400,'a'*64)
        with self.assertRaises(ValueError):plan(self.signal,self.quote,self.stamp+NS,0,'')

    def test_changed_plan_cannot_lower_risk_to_bypass_reservation(self):
        with self.assertRaises(ValueError):
            self.ledger.reserve(dict(self.value,planned_risk_cents=1),100,self.stamp+NS)
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM intents').fetchone()[0],0)

    def test_reservation_is_unique_across_process_restarts(self):
        self.reserve();self.ledger.close();self.ledger=Ledger(self.path)
        with self.assertRaises(ValueError):self.reserve()
        with self.assertRaises(ValueError):self.ledger.before_send(100)

    def test_persist_uncertainty_before_send_and_never_retry(self):
        self.reserve()
        with self.assertRaises(ValueError):self.ledger.before_send(102)
        self.ledger.before_send(100)
        self.assertEqual(self.ledger.db.execute('SELECT state FROM dispatch WHERE order_id=100').fetchone()[0],'SUBMISSION_UNKNOWN')
        with self.assertRaises(ValueError):self.ledger.before_send(100)
        self.ledger.transport_failed(self.value['signal_id'])
        with self.assertRaises(ValueError):self.ledger.before_send(101)

    def test_pending_intent_blocks_second_signal(self):
        self.reserve()
        second=plan(dict(self.signal,id='SYNTHETIC-2'),self.quote,self.stamp+NS,400,'a'*64)
        with self.assertRaises(ValueError):self.ledger.reserve(second,103,self.stamp+NS)

    def test_only_confirmed_cancelled_unfilled_intent_can_release_block(self):
        self.reserve();sid=self.value['signal_id']
        with self.assertRaises(ValueError):self.ledger.reconcile_cancelled_unfilled(sid,0,[],True)
        for oid in (100,101,102):
            self.ledger.record_order_status(oid,'Cancelled',0,0,10000+oid,self.stamp+3*NS)
        self.assertTrue(self.ledger.reconcile_cancelled_unfilled(sid,0,[],True))
        self.assertEqual(self.ledger.db.execute('SELECT attempts FROM days').fetchone()[0],1)

    def test_two_cancelled_attempts_exhaust_daily_allowance(self):
        for index in range(2):
            value=plan(dict(self.signal,id='SYNTHETIC-'+str(index)),self.quote,self.stamp+NS,400,'a'*64)
            oid=100+index*3
            self.ledger.reserve(value,oid,self.stamp+NS)
            for x in range(oid,oid+3):self.ledger.record_order_status(x,'Cancelled',0,0,10000+x,self.stamp+3*NS)
            self.ledger.reconcile_cancelled_unfilled(value['signal_id'],0,[],True)
        value=plan(dict(self.signal,id='SYNTHETIC-THIRD'),self.quote,self.stamp+NS,400,'a'*64)
        with self.assertRaises(ValueError):self.ledger.reserve(value,106,self.stamp+NS)

    def test_real_account_wrong_quantity_and_unknown_order_rejected(self):
        self.reserve()
        for bad in ({'account':'U123'},{'quantity':2},{'quantity':True},{'order_id':999},{'side':'SELL'}):
            with self.assertRaises(ValueError):
                self.ledger.record_fill('exec1',self.value['signal_id'],'entry',40003,None,dict(self.raw('entry',100),**bad))

    def test_fill_dedup_missing_fees_and_exact_pnl(self):
        self.reserve()
        sid=self.value['signal_id']
        self.assertTrue(self.ledger.record_fill('exec1',sid,'entry',40003,None,self.raw('entry',100)))
        self.assertFalse(self.ledger.record_fill('exec1',sid,'entry',40003,None,self.raw('entry',100)))
        self.ledger.record_fill('exec2',sid,'target',40060,None,self.raw('target',101))
        with self.assertRaises(ValueError):self.ledger.reconcile_flat(sid,0,[],True,{})
        with self.assertRaises(ValueError):self.ledger.reconcile_flat(sid,0,[102],True,{'exec1':200,'exec2':200})
        self.assertTrue(self.ledger.reconcile_flat(sid,0,[],True,{'exec1':200,'exec2':200}))
        self.assertEqual(self.ledger.db.execute('SELECT cash_cents FROM portfolio').fetchone()[0],502450)
        self.assertFalse(self.ledger.reconcile_flat(sid,0,[],True,{}))
        self.assertFalse(self.ledger.record_fill('exec1',sid,'entry',40003,None,self.raw('entry',100)))

    def test_gap_loss_pauses_day_durably(self):
        self.reserve();sid=self.value['signal_id']
        self.ledger.record_fill('exec1',sid,'entry',40003,200,self.raw('entry',100))
        # Deliberately large synthetic gap through the stop, not a risk guarantee.
        self.ledger.record_fill('exec2',sid,'stop',39900,200,self.raw('stop',102))
        self.ledger.reconcile_flat(sid,0,[],True,{})
        self.ledger.close();self.ledger=Ledger(self.path)
        second=plan(dict(self.signal,id='SYNTHETIC-2'),self.quote,self.stamp+NS,400,'a'*64)
        with self.assertRaises(ValueError):self.ledger.reserve(second,103,self.stamp+NS)
        self.assertEqual(self.ledger.db.execute('SELECT paused FROM days').fetchone()[0],'DAILY_LOSS')

    def test_unrealized_daily_loss_pause_survives_price_recovery(self):
        self.reserve();sid=self.value['signal_id']
        self.ledger.record_fill('exec1',sid,'entry',40003,200,self.raw('entry',100))
        loss=dict(self.quote,bid_ticks=39960,ask_ticks=39961)
        mark=self.ledger.mark_position(sid,loss,self.stamp+NS)
        self.assertEqual(mark['day_pause'],'DAILY_LOSS')
        self.ledger.close();self.ledger=Ledger(self.path)
        mark=self.ledger.mark_position(sid,self.quote,self.stamp+NS)
        self.assertEqual(mark['day_pause'],'DAILY_LOSS')
        self.assertEqual(mark['action'],'CLOSE_REQUIRED_WITHOUT_DUPLICATE_EXIT')

    def test_unrealized_high_water_and_missing_quote_never_assume_flat(self):
        self.reserve();sid=self.value['signal_id']
        self.ledger.record_fill('exec1',sid,'entry',40003,200,self.raw('entry',100))
        high=dict(self.quote,bid_ticks=40500,ask_ticks=40501)
        self.ledger.mark_position(sid,high,self.stamp+NS)
        low=dict(self.quote,bid_ticks=39950,ask_ticks=39951)
        mark=self.ledger.mark_position(sid,low,self.stamp+NS)
        self.assertEqual(mark['portfolio_pause'],'HIGH_WATER_DRAWDOWN')
        unknown=self.ledger.mark_position(sid,{},self.stamp+NS)
        self.assertIsNone(unknown['marked_equity_cents'])
        self.assertEqual(unknown['position'],'UNRESOLVED')
        self.assertEqual(self.ledger.db.execute("SELECT COUNT(*) FROM audit WHERE kind='RISK_MARK_BLOCKED'").fetchone()[0],1)


if __name__=='__main__':unittest.main()
