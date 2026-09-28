import copy
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock
from ibapi.client import EClient
from ibapi.message import OUT
from ibapi.common import PROTOBUF_MSG_ID
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_cancel import OrderCancel
from cloud.ibkr_paper_v1.broker_execution import Wire,Session,Journal,unresolved,CLIENT
from cloud.ibkr_paper_v1.execution import ACCOUNT,SYMBOL


def contract():
    c=Contract()
    for k,v in dict(conId=123,symbol='MNQ',localSymbol=SYMBOL,secType='FUT',exchange='CME',
                    currency='USD',multiplier='2',lastTradeDateOrContractMonth='20261218').items():setattr(c,k,v)
    return c


class BrokerTests(unittest.TestCase):
    def order(self,oid=100):
        o=Order();o.orderId=oid;o.account=ACCOUNT;o.action='BUY';o.totalQuantity=Decimal(1)
        o.orderType='LMT';o.lmtPrice=10000;o.orderRef='test-entry';o.transmit=True
        return o

    def test_no_live_endpoint_or_unscoped_wire_commands(self):
        w=Wire()
        for host,port,cid in [('127.0.0.1',7496,CLIENT),('example.com',4002,CLIENT),('127.0.0.1',4002,0)]:
            with self.assertRaises(ValueError):w.connect(host,port,cid)
        for code in (OUT.PLACE_ORDER,OUT.CANCEL_ORDER,OUT.REQ_GLOBAL_CANCEL):
            with self.assertRaises(ValueError):w.sendMsg(code,'')
            with self.assertRaises(ValueError):w.sendMsgProtoBuf(code+PROTOBUF_MSG_ID,b'')

    def test_exact_owned_order_only_and_unknown_submission_is_not_retried(self):
        w=Wire();w.accounts=[ACCOUNT];o=self.order();w.expected[100]=copy.deepcopy(o)
        with patch.object(EClient,'placeOrder',side_effect=TimeoutError) as send:
            bad=copy.deepcopy(o);bad.totalQuantity=2
            with self.assertRaises(ValueError):w.placeOrder(100,contract(),bad)
            with self.assertRaises(TimeoutError):w.placeOrder(100,contract(),o)
            with self.assertRaises(ValueError):w.placeOrder(100,contract(),o)
            self.assertEqual(send.call_count,1)
        self.assertIsNone(w.gate)

    def test_other_account_even_matching_expected_is_denied(self):
        w=Wire();w.accounts=['U123'];o=self.order();o.account='U123';w.expected[100]=copy.deepcopy(o)
        with patch.object(EClient,'placeOrder') as send:
            with self.assertRaises(ValueError):w.placeOrder(100,contract(),o)
            send.assert_not_called()

    def test_cancel_never_targets_unowned_or_repeats(self):
        w=Wire();w.accounts=[ACCOUNT];w.sent={100}
        with patch.object(EClient,'cancelOrder') as cancel:
            with self.assertRaises(ValueError):w.cancelOrder(999,OrderCancel())
            w.cancelOrder(100,OrderCancel())
            with self.assertRaises(ValueError):w.cancelOrder(100,OrderCancel())
            self.assertEqual(cancel.call_count,1)

    def test_crash_or_duplicate_signal_blocks_entry(self):
        with tempfile.TemporaryDirectory() as root:
            j=Journal(root,{'signal_id':'once'})
            self.assertTrue(unresolved(root))
            with self.assertRaises(FileExistsError):Journal(root,{'signal_id':'once'})
            j.write('SEND_UNKNOWN',order_id=100);j.close()
            self.assertTrue(unresolved(root))
            with Path(j.path).open('a') as f:f.write('{broken')
            self.assertTrue(unresolved(root))

    def test_actual_sdk_order_can_be_durably_recorded_before_socket(self):
        with tempfile.TemporaryDirectory() as root:
            j=Journal(root,{'signal_id':'serialization'})
            s=Session(j);s.w.accounts=[ACCOUNT];s.contract=contract()
            def send(client,oid,c,o):
                text=j.path.read_text()
                self.assertIn('SEND_UNKNOWN',text)
                self.assertIn('"totalQuantity":"1"',text)
            with patch.object(EClient,'placeOrder',side_effect=send):s.send(self.order())
            j.close()

    def test_close_does_not_send_until_every_old_order_is_terminal(self):
        s=Session(MagicMock());s.cancel_owned=MagicMock(return_value=False);s.send=MagicMock()
        with self.assertRaises(RuntimeError):s.close_owned(100,1)
        s.send.assert_not_called()

    def test_cancel_fill_race_with_flat_snapshot_never_sends_second_exit(self):
        s=Session(MagicMock());s.cancel_owned=MagicMock(return_value=True)
        s.executions={'entry':{'side':'BOT','quantity':'1'},'stop':{'side':'SLD','quantity':'1'}}
        s.snapshot=MagicMock(return_value=(0,{}));s.send=MagicMock()
        s.close_owned(100,1);s.send.assert_not_called()

    def test_exit_requires_position_and_executions_to_agree(self):
        s=Session(MagicMock());s.cancel_owned=MagicMock(return_value=True)
        s.snapshot=MagicMock(return_value=(1,{}));s.send=MagicMock()
        with self.assertRaises(RuntimeError):s.close_owned(100,1)
        s.send.assert_not_called()

    def test_close_is_one_owned_opposite_contract_after_terminal_cleanup(self):
        s=Session(MagicMock());s.cancel_owned=MagicMock(return_value=True)
        s.snapshot=MagicMock(return_value=(1,{}));s.executions={'entry':{'side':'BOT','quantity':'1'}}
        s.w.expected[100]=self.order();s.send=MagicMock();s.wait=MagicMock(return_value=True)
        s.close_owned(100,1)
        o=s.send.call_args.args[0]
        self.assertEqual((o.orderId,o.account,o.action,o.totalQuantity,o.orderType),(103,ACCOUNT,'SELL',1,'MKT'))

    def test_invalid_stop_ack_requires_cleanup(self):
        s=Session(None);o=self.order(102);o.action='SELL';o.orderType='STP';o.auxPrice=9990;o.triggerMethod=2
        s.w.expected[102]=o
        s.consume(dict(kind='order',received_ns=1,order_id=102,account_ok=True,contract=SYMBOL,
            con_id=123,client_id=CLIENT,quantity='1',side='SELL',order_type='STP',parent_id=0,
            order_ref=o.orderRef,status='PreSubmitted',stop_price='9991',trigger_method=2))
        self.assertEqual(s.failure,'STOP_ACK_MISMATCH')

    def test_inactive_is_not_enough_to_send_an_independent_exit(self):
        s=Session(None);s.statuses[100]={'status':'Inactive'}
        self.assertFalse(s.terminal(100))

    def test_execution_query_replay_preserves_first_observed_fill_time(self):
        s=Session(None);s.contract=contract();s.w.expected[100]=self.order()
        event=dict(kind='execution',received_ns=10,execution_id='same',order_id=100,
            account_ok=True,contract=SYMBOL,con_id=123,client_id=CLIENT,quantity='1',
            price='10000',side='BOT',order_ref='test-entry',pending=False)
        s.consume(event);s.consume(dict(event,received_ns=999))
        self.assertEqual(s.executions['same']['received_ns'],10)
        s.consume(dict(event,price='10000.25',received_ns=1000))
        self.assertEqual(s.failure,'EXECUTION_CORRECTION')

    def test_limit_violation_keeps_owned_fill_for_cleanup_and_blocks_success(self):
        s=Session(None);s.contract=contract();s.w.expected[100]=self.order()
        s.consume(dict(kind='execution',received_ns=10,execution_id='outside',order_id=100,
            account_ok=True,contract=SYMBOL,con_id=123,client_id=CLIENT,quantity='1',
            price='10001',side='BOT',order_ref='test-entry',pending=False))
        self.assertEqual(s.failure,'FILL_OUTSIDE_LIMIT')
        self.assertIn('outside',s.executions)

    def test_missing_or_fractional_cent_fees_cannot_be_called_zero(self):
        s=Session(None);s.pump=MagicMock();s.snapshot=MagicMock(return_value=(0,{}));s.wait=MagicMock()
        s.executions={'a':{'order_id':100,'price':'10000'},'b':{'order_id':101,'price':'10001'}}
        with self.assertRaises(RuntimeError):s.finish(100,1)
        s.fees={'a':{'amount':'0.601','currency':'USD'},'b':{'amount':'0.61','currency':'USD'}}
        with self.assertRaises(ValueError):s.finish(100,1)
