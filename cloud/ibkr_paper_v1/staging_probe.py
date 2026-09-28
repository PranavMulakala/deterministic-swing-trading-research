"""One supervised paper bracket staging/cancellation probe.

All three legs have transmit=False. This tests the Gateway's order interface,
not fills or strategy performance. It never transmits a bracket to the broker.
"""
import argparse
import copy
import json
import logging
import os
from pathlib import Path
import sqlite3
import threading
import time
import uuid

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.message import OUT
from ibapi.order_cancel import OrderCancel
from cloud.ibkr_paper_v1.broker_snapshot import ALLOWED
from cloud.ibkr_paper_v1.collector import contract_ok
from cloud.ibkr_paper_v1.execution import ACCOUNT,SYMBOL,VERSION,bracket_orders
from cloud.ibkr_paper_v1.margin_preview import Preview


def fields(value):
    """Compare SDK value objects structurally, including SoftDollarTier."""
    if hasattr(value,'__dict__'):
        return {key:fields(item) for key,item in vars(value).items()}
    if isinstance(value,(list,tuple)):
        return [fields(item) for item in value]
    if isinstance(value,dict):
        return {key:fields(item) for key,item in value.items()}
    return value


class Stage(Preview):
    def __init__(self,journal):
        super().__init__()
        self.journal=journal
        self.journal_lock=threading.Lock()
        self.expected={}
        self.attempted=set()
        self.cancelled_requests=set()
        self.acks=set()
        self.statuses={}
        self.observed_open=set()
        self.request_flag=None
        self.unexpected_fill=False

    def record(self,kind,**payload):
        with self.journal_lock:
            self.journal.write(json.dumps({'kind':kind,'received_ns':time.time_ns(),**payload})+'\n')
            self.journal.flush();os.fsync(self.journal.fileno())

    def permitted(self,msg_id):
        return (msg_id in ALLOWED or msg_id in (OUT.REQ_CONTRACT_DATA,OUT.REQ_OPEN_ORDERS)
                or (msg_id in (OUT.PLACE_ORDER,OUT.CANCEL_ORDER) and self.request_flag==msg_id))

    def placeOrder(self,orderId,contract,order):
        expected=self.expected.get(orderId)
        if (self.accounts!=[ACCOUNT] or not contract_ok(contract) or expected is None
                or order.transmit is not False or order.whatIf is not False
                or order.account!=ACCOUNT or order.totalQuantity!=1
                or fields(order)!=fields(expected) or orderId in self.attempted):
            raise RuntimeError('only_exact_untransmitted_paper_stage_allowed')
        self.record('STAGING_UNKNOWN_BEFORE_SEND',order_id=orderId,transmit=False)
        self.attempted.add(orderId)
        self.request_flag=OUT.PLACE_ORDER
        try:return EClient.placeOrder(self,orderId,contract,order)
        finally:self.request_flag=None

    def cancelOrder(self,orderId,orderCancel):
        if self.accounts!=[ACCOUNT] or orderId not in self.attempted or orderId in self.cancelled_requests:
            raise RuntimeError('only_owned_stage_cancellation_allowed')
        self.record('CANCELLATION_REQUESTED',order_id=orderId)
        self.cancelled_requests.add(orderId)
        self.request_flag=OUT.CANCEL_ORDER
        try:return EClient.cancelOrder(self,orderId,orderCancel)
        finally:self.request_flag=None

    def openOrder(self,orderId,contract,order,state):
        self.observed_open.add(orderId)
        expected=self.expected.get(orderId)
        if (expected is None or order.account!=ACCOUNT or contract.localSymbol!=SYMBOL
                or order.transmit is not False or order.orderRef!=expected.orderRef
                or order.totalQuantity!=1 or order.parentId!=expected.parentId):
            self.failure='UNEXPECTED_OR_TRANSMITTED_ORDER';return
        self.acks.add(orderId)
        self.record('STAGED_ORDER_CALLBACK',order_id=orderId,status=state.status,
                    parent_id=order.parentId,transmit=order.transmit)

    def orderStatus(self,orderId,status,filled,remaining,avgFillPrice,permId,parentId,
                    lastFillPrice,clientId,whyHeld,mktCapPrice):
        if orderId not in self.expected:return
        self.statuses[orderId]=status
        if filled!=0:self.unexpected_fill=True;self.failure='UNEXPECTED_FILL'
        self.record('ORDER_STATUS',order_id=orderId,status=status,filled=str(filled),remaining=str(remaining))

    def execDetails(self,reqId,contract,execution):
        self.unexpected_fill=True;self.failure='UNEXPECTED_EXECUTION'
        self.record('UNEXPECTED_EXECUTION',order_id=execution.orderId)

    def error(self,reqId,errorTime,errorCode,errorString,advancedOrderRejectJson=''):
        # Ignore a redundant-cancel 161 only after this owned leg is confirmed
        # Cancelled. An empty open-order query alone cannot prove cleanup:
        # untransmitted orders are not returned by IBKR's open-order API.
        self.errors.append({'request_id':reqId,'code':errorCode})
        self.record('BROKER_CODE',request_id=reqId,code=errorCode)
        redundant_cancel=(errorCode==161 and reqId in self.cancelled_requests
                          and self.statuses.get(reqId)=='Cancelled')
        if errorCode not in (2104,2106,2107,2108,2158,202,10147,10148) and not redundant_cancel:
            self.failure='BROKER_ERROR_'+str(errorCode)

    def open_orders(self):
        self.observed_open.clear();self.ends['orders'].clear()
        self.reqOpenOrders()
        if not self.ends['orders'].wait(5):raise RuntimeError('OWNER_OPEN_ORDER_QUERY_INCOMPLETE')
        return set(self.observed_open)


def run(state_folder):
    folder=Path(state_folder)/'broker-staging'
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    run_id=uuid.uuid4().hex
    path=folder/(run_id+'.jsonl')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    network=None
    staged=False
    cleanup=False
    with os.fdopen(fd,'w') as journal:
        p=Stage(journal)
        try:
            p.connect('127.0.0.1',4002,clientId=75)
            network=threading.Thread(target=p.run,daemon=True);network.start()
            if not p.ready.wait(8):raise RuntimeError('GATEWAY_NOT_READY')
            p.reqManagedAccts()
            if not p.accounts_ready.wait(5) or p.accounts!=[ACCOUNT]:raise RuntimeError('PAPER_ACCOUNT_NOT_VERIFIED')
            if p.open_orders():raise RuntimeError('PREEXISTING_OWNER_ORDERS')
            if p.failure:raise RuntimeError(p.failure)
            c=Contract();c.symbol='MNQ';c.localSymbol=SYMBOL;c.secType='FUT'
            c.exchange='CME';c.currency='USD';c.multiplier='2';c.lastTradeDateOrContractMonth='202612'
            p.reqContractDetails(301,c)
            if not p.contract_end.wait(8) or len(p.contracts)!=1 or not contract_ok(p.contracts[0].contract):
                raise RuntimeError('CONTRACT_NOT_VERIFIED')
            c=p.contracts[0].contract
            db=sqlite3.connect((Path(state_folder)/'state.sqlite').as_uri()+'?mode=ro',uri=True)
            row=db.execute("SELECT received_ns,payload FROM events WHERE kind='quote' ORDER BY id DESC LIMIT 1").fetchone()
            db.close()
            if row is None or not 0<=time.time_ns()-row[0]<=5_000_000_000:
                raise RuntimeError('FRESH_QUOTE_REQUIRED')
            quote=json.loads(row[1])
            if quote.get('contract')!=SYMBOL or quote.get('data_type')!=1:raise RuntimeError('REALTIME_QUOTE_REQUIRED')
            entry=quote['bid_ticks']-40
            value={'version':VERSION,'account':ACCOUNT,'contract':SYMBOL,'direction':1,'quantity':1,
                   'signal_id':'PLUMBING_ONLY-'+run_id,'entry_ticks':entry,
                   'stop_ticks':entry-10,'target_ticks':entry+20,'expires_ns':time.time_ns()+60_000_000_000}
            orders=bracket_orders(value,p.next_order_id)
            for order in orders:
                order.transmit=False
                p.expected[order.orderId]=copy.deepcopy(order)
            p.record('PROBE_STARTED',mode='PAPER_UNTRANSMITTED_STAGING_ONLY',order_ids=list(p.expected))
            for order in orders:
                if p.failure:raise RuntimeError(p.failure)
                p.placeOrder(order.orderId,c,order)
            p.open_orders()
            staged=p.acks==set(p.expected) and p.failure is None
        except Exception as error:
            p.failure=p.failure or (str(error) if type(error) is RuntimeError else type(error).__name__)
        finally:
            if p.isConnected() and p.accounts==[ACCOUNT]:
                for oid in sorted(p.attempted,reverse=True):
                    try:p.cancelOrder(oid,OrderCancel())
                    except Exception:p.failure=p.failure or 'CANCELLATION_REQUEST_FAILED'
                # IBKR does not expose untransmitted orders in open-order queries.
                # Require a terminal callback for every attempted leg as well.
                try:
                    deadline=time.monotonic()+8
                    while True:
                        visible=p.open_orders()
                        terminals=bool(p.attempted) and all(p.statuses.get(x)=='Cancelled' for x in p.attempted)
                        if not visible and terminals:cleanup=True;break
                        if time.monotonic()>=deadline:break
                        threading.Event().wait(0.25)
                except Exception:p.failure=p.failure or 'CLEANUP_QUERY_FAILED'
            p.disconnect()
            if network:network.join(5)
        result={'mode':'PAPER_UNTRANSMITTED_STAGING_ONLY','three_stage_acknowledgements':staged,
                'attempted_legs':len(p.attempted),'all_attempted_legs_cancelled':cleanup,
                'untransmitted_order_visibility':'NOT_AVAILABLE_THROUGH_OPEN_ORDER_API',
                'cancelled_leg_count':sum(p.statuses.get(x)=='Cancelled' for x in p.attempted),
                'unexpected_fill':p.unexpected_fill,'failure':p.failure,'errors':p.errors,
                'broker_fill_testing_complete':False,'strategy_evidence':False,'journal':str(path)}
        p.record('PROBE_ENDED',**result)
    return result


if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    parser=argparse.ArgumentParser()
    parser.add_argument('--approve-paper-staging',action='store_true',required=True)
    parser.add_argument('--state',default='/var/lib/ibkr-paper')
    args=parser.parse_args()
    print(json.dumps(run(args.state),indent=2))
