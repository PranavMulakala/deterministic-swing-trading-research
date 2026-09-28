"""Safety boundaries for the untransmitted paper Gateway probe."""
import copy
import tempfile
import time
import unittest
from unittest.mock import patch
from ibapi.client import EClient
from ibapi.common import PROTOBUF_MSG_ID
from ibapi.contract import Contract
from ibapi.message import OUT
from ibapi.order_cancel import OrderCancel
from cloud.ibkr_paper_v1.execution import ACCOUNT, SYMBOL, VERSION, bracket_orders
from cloud.ibkr_paper_v1.staging_probe import Stage


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.journal = tempfile.TemporaryFile(mode='w+')
        self.p = Stage(self.journal)
        self.p.accounts = [ACCOUNT]
        self.c = Contract()
        for key, value in dict(conId=123, symbol='MNQ', localSymbol=SYMBOL,
                secType='FUT', exchange='CME', currency='USD', multiplier='2',
                lastTradeDateOrContractMonth='20261218').items():
            setattr(self.c, key, value)
        orders = bracket_orders(dict(version=VERSION, account=ACCOUNT, contract=SYMBOL,
            quantity=1, direction=1, signal_id='TEST-STAGE', entry_ticks=40000,
            stop_ticks=39990, target_ticks=40020, expires_ns=time.time_ns()+60_000_000_000), 100)
        for order in orders:
            order.transmit = False
            self.p.expected[order.orderId] = copy.deepcopy(order)
        self.orders = orders

    def tearDown(self):
        self.journal.close()

    def test_every_leg_is_durable_before_send_and_not_repeated(self):
        def send(client, oid, contract, order):
            self.journal.seek(0)
            self.assertIn('STAGING_UNKNOWN_BEFORE_SEND', self.journal.read())
            self.assertFalse(order.transmit)
            self.assertTrue(self.p.permitted(OUT.PLACE_ORDER))
        with patch.object(EClient, 'placeOrder', side_effect=send) as mock:
            for order in self.orders:
                self.p.placeOrder(order.orderId, self.c, order)
            self.assertEqual(mock.call_count, 3)
            with self.assertRaises(RuntimeError):
                self.p.placeOrder(100, self.c, self.orders[0])
        self.assertFalse(self.p.permitted(OUT.PLACE_ORDER))

    def test_transmission_account_quantity_and_plan_changes_rejected(self):
        with patch.object(EClient, 'placeOrder') as mock:
            for key, value in [('transmit', True), ('account', 'U123'),
                               ('totalQuantity', 2), ('lmtPrice', 10001), ('whatIf', True)]:
                order = copy.deepcopy(self.orders[0]); setattr(order, key, value)
                with self.assertRaises(RuntimeError):self.p.placeOrder(100, self.c, order)
            self.p.accounts = ['U123']
            with self.assertRaises(RuntimeError):self.p.placeOrder(100, self.c, self.orders[0])
            mock.assert_not_called()

    def test_cancellation_is_owned_and_not_global_or_repeated(self):
        with patch.object(EClient, 'cancelOrder') as cancel:
            with self.assertRaises(RuntimeError):self.p.cancelOrder(100, OrderCancel())
            self.p.attempted.add(100)
            self.p.cancelOrder(100, OrderCancel())
            with self.assertRaises(RuntimeError):self.p.cancelOrder(100, OrderCancel())
            with self.assertRaises(RuntimeError):self.p.cancelOrder(999, OrderCancel())
            self.assertEqual(cancel.call_count, 1)
        for msg in (OUT.PLACE_ORDER, OUT.CANCEL_ORDER, OUT.REQ_GLOBAL_CANCEL):
            with self.assertRaises(RuntimeError):self.p.sendMsg(msg, '')
            with self.assertRaises(RuntimeError):self.p.sendMsgProtoBuf(msg+PROTOBUF_MSG_ID, b'')

    def test_transport_failure_cannot_be_resent(self):
        with patch.object(EClient, 'placeOrder', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):self.p.placeOrder(100, self.c, self.orders[0])
            with self.assertRaises(RuntimeError):self.p.placeOrder(100, self.c, self.orders[0])
        self.assertIn(100, self.p.attempted)
        self.assertFalse(self.p.permitted(OUT.PLACE_ORDER))

    def test_redundant_cancel_requires_owned_terminal_callback(self):
        self.p.cancelled_requests.add(100)
        self.p.error(100, 0, 161, 'not cancellable')
        self.assertEqual(self.p.failure, 'BROKER_ERROR_161')
        self.p.failure = None
        self.p.statuses[100] = 'Cancelled'
        self.p.error(100, 0, 161, 'not cancellable')
        self.assertIsNone(self.p.failure)
        self.p.error(999, 0, 161, 'not cancellable')
        self.assertEqual(self.p.failure, 'BROKER_ERROR_161')
