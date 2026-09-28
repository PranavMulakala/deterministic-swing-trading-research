"""Bounded paper-only bracket execution with durable commands and owned cleanup.

One client, one contract, one contract unit. No live endpoint is accepted. A
process crash leaves an unresolved journal and blocks all subsequent entries.
Native protection is retained until owned cancellations are confirmed; a close
order is never sent alongside an order that could still fill.
"""
import copy
from decimal import Decimal
import fcntl
import hashlib
import json
import os
from pathlib import Path
import queue
import sqlite3
import threading
import time

from ibapi.client import EClient
from ibapi.common import PROTOBUF_MSG_ID
from ibapi.contract import Contract
from ibapi.execution import ExecutionFilter
from ibapi.message import OUT
from ibapi.order import Order
from ibapi.order_cancel import OrderCancel
from ibapi.wrapper import EWrapper
from cloud.ibkr_paper_v1.collector import contract_ok
from cloud.ibkr_paper_v1.execution import ACCOUNT, SYMBOL, NS, bracket_orders, canonical
from cloud.ibkr_paper_v1.reconciliation import exact_units
from cloud.ibkr_paper_v1.staging_probe import fields

CLIENT=76
INFO={2104,2106,2107,2108,2158}
TERMINAL={'Cancelled','ApiCancelled','Filled'}
ACTIVE={'PreSubmitted','Submitted'}
READ={OUT.START_API,OUT.REQ_MANAGED_ACCTS,OUT.REQ_CONTRACT_DATA,
      OUT.REQ_POSITIONS,OUT.CANCEL_POSITIONS,OUT.REQ_ALL_OPEN_ORDERS,
      OUT.REQ_EXECUTIONS}


class Wire(EWrapper,EClient):
    def __init__(self):
        EClient.__init__(self,self)
        self.events=queue.Queue()
        self.gate=None
        self.sender=threading.get_ident()
        self.accounts=[]
        self.expected={}
        self.sent=set()
        self.cancelled=set()

    def event(self,kind,**v):self.events.put(dict(kind=kind,received_ns=time.time_ns(),**v))
    def connect(self,host,port,clientId):
        if (host,port,clientId)!=('127.0.0.1',4002,CLIENT):raise ValueError('paper_endpoint_only')
        return super().connect(host,port,clientId)
    def permit(self,kind):
        return kind in READ or (self.gate==kind and threading.get_ident()==self.sender)
    def sendMsg(self,kind,msg):
        if not self.permit(kind):raise ValueError('broker_message_denied')
        return EClient.sendMsg(self,kind,msg)
    def sendMsgProtoBuf(self,kind,msg):
        if not self.permit(kind-PROTOBUF_MSG_ID):raise ValueError('broker_protobuf_denied')
        return EClient.sendMsgProtoBuf(self,kind,msg)
    def placeOrder(self,oid,c,o):
        if (self.accounts!=[ACCOUNT] or not contract_ok(c) or o.account!=ACCOUNT
                or o.totalQuantity!=1 or o.whatIf or oid!=o.orderId
                or oid not in self.expected or fields(o)!=fields(self.expected[oid])
                or oid in self.sent):raise ValueError('unowned_or_repeat_order_denied')
        self.sent.add(oid);self.gate=OUT.PLACE_ORDER
        try:return EClient.placeOrder(self,oid,c,o)
        finally:self.gate=None
    def cancelOrder(self,oid,cancel):
        if self.accounts!=[ACCOUNT] or oid not in self.sent or oid in self.cancelled:
            raise ValueError('unowned_or_repeat_cancel_denied')
        self.cancelled.add(oid);self.gate=OUT.CANCEL_ORDER
        try:return EClient.cancelOrder(self,oid,cancel)
        finally:self.gate=None
    def nextValidId(self,oid):self.event('next_id',order_id=oid)
    def managedAccounts(self,values):
        self.accounts=sorted(x for x in values.split(',') if x)
        self.event('account',verified=self.accounts==[ACCOUNT])
    def contractDetails(self,reqId,details):
        if reqId==301:self.events.put(dict(kind='contract',contract=details.contract,received_ns=time.time_ns()))
    def contractDetailsEnd(self,reqId):self.event('contract_end')
    def openOrder(self,oid,c,o,state):
        self.event('order',order_id=oid,account_ok=o.account==ACCOUNT,contract=c.localSymbol,
            con_id=c.conId,client_id=o.clientId,quantity=str(o.totalQuantity),side=o.action,
            order_type=o.orderType,parent_id=o.parentId,order_ref=o.orderRef,status=state.status,
            limit_price=str(o.lmtPrice),stop_price=str(o.auxPrice),trigger_method=o.triggerMethod)
    def openOrderEnd(self):self.event('orders_end')
    def orderStatus(self,oid,status,filled,remaining,avg,perm,parent,last,client,why,cap):
        self.event('status',order_id=oid,status=status,filled=str(filled),remaining=str(remaining),
                   perm_id=perm,parent_id=parent,client_id=client)
    def position(self,account,c,q,avg):
        self.event('position',account_ok=account==ACCOUNT,contract=c.localSymbol,con_id=c.conId,quantity=str(q))
    def positionEnd(self):self.event('positions_end')
    def execDetails(self,reqId,c,e):
        self.event('execution',execution_id=e.execId,order_id=e.orderId,account_ok=e.acctNumber==ACCOUNT,
            contract=c.localSymbol,con_id=c.conId,client_id=e.clientId,quantity=str(e.shares),
            price=str(e.price),side=e.side,order_ref=e.orderRef,pending=e.pendingPriceRevision)
    def execDetailsEnd(self,reqId):self.event('executions_end')
    def commissionAndFeesReport(self,c):
        self.event('fee',execution_id=c.execId,currency=c.currency,amount=str(c.commissionAndFees))
    def error(self,reqId,errorTime,code,text,advancedOrderRejectJson=''):
        self.event('error',order_id=reqId,code=code)
    def connectionClosed(self):self.event('disconnected')


class Journal:
    def __init__(self,folder,value):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        key=hashlib.sha256(value['signal_id'].encode()).hexdigest()
        self.path=folder/(key+'.jsonl')
        self.file=os.fdopen(os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w')
        self.write('PLAN',plan=value)
    def write(self,kind,**values):
        def encode(value):
            if isinstance(value,Decimal):return str(value)
            raise TypeError('unsupported_journal_value')
        self.file.write(json.dumps(dict(kind=kind,received_ns=time.time_ns(),**values),
            sort_keys=True,separators=(',',':'),allow_nan=False,default=encode)+'\n')
        self.file.flush();os.fsync(self.file.fileno())
    def close(self):self.file.close()


def unresolved(folder):
    for path in Path(folder).glob('*.jsonl'):
        try:
            rows=[json.loads(x) for x in path.read_text().splitlines()]
            if not rows or rows[-1]['kind']!='COMPLETE':return True
        except (ValueError,OSError):return True
    return False


class Session:
    def __init__(self,journal,before_send=None):
        self.w=Wire();self.journal=journal;self.thread=None
        self.next_id=None;self.contracts=[];self.contract=None;self.ends=set()
        self.orders={};self.statuses={};self.executions={};self.fees={};self.positions={}
        self.errors=[];self.failure=None;self.account_verified=False
        self.snapshot_open={};self.querying=False;self.protection_seen=False
        self.before_send=before_send
    def consume(self,e):
        kind=e['kind']
        if kind=='contract':
            self.contracts.append(e['contract']);return
        if self.journal:self.journal.write('CALLBACK',event=e)
        if kind.endswith('_end'):self.ends.add(kind)
        if kind=='next_id':self.next_id=e['order_id']
        elif kind=='account':
            self.account_verified=e['verified']
            if not e['verified']:self.failure='WRONG_ACCOUNT'
        elif kind=='disconnected':self.failure='DISCONNECTED'
        elif kind=='position':
            if not e['account_ok']:self.failure='WRONG_ACCOUNT'
            self.positions[e['con_id']]=e
        elif kind=='order':
            if self.querying:self.snapshot_open[e['order_id']]=e
            self.orders[e['order_id']]=e
            o=self.w.expected.get(e['order_id'])
            if o is None:
                self.failure='UNOWNED_OPEN_ORDER';return
            if (not e['account_ok'] or e['contract']!=SYMBOL or e['client_id']!=CLIENT
                    or (self.contract is not None and e['con_id']!=self.contract.conId)
                    or e['order_ref']!=o.orderRef or e['parent_id']!=o.parentId
                    or e['side']!=o.action or e['order_type']!=o.orderType
                    or exact_units(e['quantity'])!=1):self.failure='ORDER_ACK_MISMATCH'
            if o.orderType=='STP' and (e['trigger_method']!=2 or Decimal(e['stop_price'])!=Decimal(str(o.auxPrice))):
                self.failure='STOP_ACK_MISMATCH'
            if o.orderType=='LMT' and Decimal(e['limit_price'])!=Decimal(str(o.lmtPrice)):
                self.failure='LIMIT_ACK_MISMATCH'
        elif kind=='status':
            oid=e['order_id']
            if oid not in self.w.expected:return
            if e['client_id']!=CLIENT or exact_units(e['filled'])+exact_units(e['remaining'])>1:
                self.failure='STATUS_MISMATCH';return
            previous=self.statuses.get(oid)
            if previous and exact_units(e['filled'])<exact_units(previous['filled']):
                self.failure='STATUS_REGRESSION';return
            self.statuses[oid]=e
        elif kind=='execution':
            oid=e['order_id'];o=self.w.expected.get(oid)
            if o is None:
                # Prior, already reconciled runs share this client. The caller
                # only requests execution recovery for current owned orders.
                return
            if (not e['account_ok'] or e['contract']!=SYMBOL or e['client_id']!=CLIENT
                    or self.contract is None or e['con_id']!=self.contract.conId
                    or e['order_ref']!=o.orderRef or e['pending']
                    or {'BOT':'BUY','SLD':'SELL'}.get(e['side'])!=o.action
                    or exact_units(e['quantity'])!=1):self.failure='EXECUTION_MISMATCH';return
            exact_units(e['price'],4)
            if o.orderType=='LMT' and (Decimal(e['price'])>Decimal(str(o.lmtPrice)) if o.action=='BUY'
                                      else Decimal(e['price'])<Decimal(str(o.lmtPrice))):
                # Retain the owned fill so cleanup can reconcile its quantity.
                self.failure='FILL_OUTSIDE_LIMIT'
            old=self.executions.get(e['execution_id'])
            if old and {k:v for k,v in old.items() if k!='received_ns'}!={k:v for k,v in e.items() if k!='received_ns'}:
                self.failure='EXECUTION_CORRECTION';return
            if old:return  # Preserve the first observed fill time, not query replay time.
            self.executions[e['execution_id']]=e
        elif kind=='fee':
            old=self.fees.get(e['execution_id'])
            if old and (old['amount'],old['currency'])!=(e['amount'],e['currency']):self.failure='FEE_CORRECTION'
            if old:return
            self.fees[e['execution_id']]=e
        elif kind=='error':
            self.errors.append(e)
            oid=e['order_id'];status=self.statuses.get(oid,{}).get('status')
            if e['code'] not in INFO and e['code']!=202:
                if e['code'] in (161,10147,10148) and status in TERMINAL:return
                self.failure='BROKER_ERROR_'+str(e['code'])
    def pump(self,seconds=0):
        deadline=time.monotonic()+seconds
        while True:
            try:e=self.w.events.get(timeout=max(0,min(.1,deadline-time.monotonic())))
            except queue.Empty:
                if time.monotonic()>=deadline:return
                continue
            self.consume(e)
            if time.monotonic()>=deadline and self.w.events.empty():return
    def wait(self,predicate,seconds):
        end=time.monotonic()+seconds
        while not predicate() and time.monotonic()<end:self.pump(.05)
        return predicate()
    def connect(self):
        self.w.connect('127.0.0.1',4002,CLIENT)
        self.thread=threading.Thread(target=self.w.run,daemon=True);self.thread.start()
        if not self.wait(lambda:self.next_id is not None and self.account_verified,10):raise RuntimeError('PAPER_CONNECTION_NOT_READY')
        if self.failure:raise RuntimeError(self.failure)
        c=Contract();c.symbol='MNQ';c.localSymbol=SYMBOL;c.secType='FUT';c.exchange='CME'
        c.currency='USD';c.multiplier='2';c.lastTradeDateOrContractMonth='20261218'
        self.w.reqContractDetails(301,c)
        if not self.wait(lambda:'contract_end' in self.ends,8) or len(self.contracts)!=1 or not contract_ok(self.contracts[0]):
            raise RuntimeError('CONTRACT_NOT_VERIFIED')
        self.contract=self.contracts[0]
    def snapshot(self):
        self.positions={};self.snapshot_open={};self.querying=True
        self.ends.difference_update({'positions_end','orders_end','executions_end'})
        self.w.reqPositions();self.w.reqAllOpenOrders()
        f=ExecutionFilter();f.acctCode=ACCOUNT
        self.w.reqExecutions(201,f)
        complete=self.wait(lambda:{'positions_end','orders_end','executions_end'}<=self.ends,8)
        self.w.cancelPositions();self.pump(.2);self.querying=False
        if not complete:raise RuntimeError('BROKER_SNAPSHOT_INCOMPLETE')
        for p in self.positions.values():
            if not p['account_ok'] or (exact_units(p['quantity'],nonnegative=False)!=0 and p['con_id']!=self.contract.conId):
                raise RuntimeError('UNRELATED_POSITION')
        qty=exact_units(self.positions.get(self.contract.conId,{}).get('quantity','0'),nonnegative=False)
        return qty,dict(self.snapshot_open)
    def send(self,order):
        if self.before_send:self.before_send(order.orderId)
        self.w.expected[order.orderId]=copy.deepcopy(order)
        self.journal.write('SEND_UNKNOWN',order_id=order.orderId,order=fields(order))
        self.w.placeOrder(order.orderId,self.contract,order)
    def terminal(self,oid):return self.statuses.get(oid,{}).get('status') in TERMINAL
    def cancel_owned(self):
        for oid in sorted(self.w.sent):
            if not self.terminal(oid) and oid not in self.w.cancelled:
                self.journal.write('CANCEL_UNKNOWN',order_id=oid)
                self.w.cancelOrder(oid,OrderCancel())
        return self.wait(lambda:all(self.terminal(x) for x in self.w.sent),10)
    def close_owned(self,first,direction):
        # No independent exit can coexist with an original order that might fill.
        if not self.cancel_owned():raise RuntimeError('CANCELLATION_NOT_TERMINAL')
        qty,open_orders=self.snapshot()
        if open_orders:raise RuntimeError('ORDERS_REMAIN_AFTER_CANCELLATION')
        filled=sum((1 if x['side']=='BOT' else -1)*exact_units(x['quantity']) for x in self.executions.values())
        if qty!=filled or qty not in (0,direction):raise RuntimeError('POSITION_EXECUTION_MISMATCH')
        if qty==0:return
        order=Order();order.orderId=first+3;order.account=ACCOUNT;order.totalQuantity=Decimal(1)
        order.action='SELL' if qty==1 else 'BUY';order.orderType='MKT';order.tif='DAY'
        order.transmit=True;order.orderRef=self.w.expected[first].orderRef.replace('-entry','-time_exit')
        self.send(order)
        if not self.wait(lambda:self.terminal(order.orderId),15):raise RuntimeError('EXIT_UNCONFIRMED')
    def finish(self,first,direction):
        self.pump(.5)
        qty,open_orders=self.snapshot()
        if qty!=0 or open_orders:raise RuntimeError('FINAL_ACCOUNT_NOT_FLAT')
        if not all(self.terminal(x) for x in self.w.sent):raise RuntimeError('TERMINAL_ORDER_EVIDENCE_MISSING')
        self.wait(lambda:all(x in self.fees for x in self.executions),5)
        entries=[e for e in self.executions.values() if e['order_id']==first]
        exits=[e for e in self.executions.values() if e['order_id']!=first]
        if len(entries)!=len(exits) or len(entries)>1:raise RuntimeError('EXECUTION_PAIR_MISMATCH')
        fees=0
        for eid in self.executions:
            fee=self.fees.get(eid)
            if fee is None or fee['currency']!='USD':raise RuntimeError('FEES_NOT_VERIFIED')
            fees+=exact_units(fee['amount'],100)
        pnl=0 if not entries else direction*(exact_units(exits[0]['price'],4)-exact_units(entries[0]['price'],4))*50-fees
        return dict(flat_verified=True,fill_count=len(self.executions),fees_cents=fees,net_pnl_cents=pnl,
            protection_acknowledged=self.protection_seen,executions=list(self.executions.values()),
            fees=list(self.fees.values()),status_by_order={str(k):v['status'] for k,v in self.statuses.items()},
            errors=[{'code':e['code'],'order_id':e['order_id']} for e in self.errors])
    def disconnect(self):
        self.w.disconnect()
        if self.thread:self.thread.join(5)


def latest_quote(state,max_age_ns=NS):
    db=sqlite3.connect((Path(state)/'state.sqlite').as_uri()+'?mode=ro',uri=True)
    try:row=db.execute("SELECT received_ns,payload FROM events WHERE kind='quote' ORDER BY id DESC LIMIT 1").fetchone()
    finally:db.close()
    if row is None or not 0<=time.time_ns()-row[0]<=max_age_ns:raise ValueError('STALE_QUOTE')
    value=json.loads(row[1]);value['received_ns']=row[0]
    if value.get('contract')!=SYMBOL or value.get('data_type')!=1:raise ValueError('REALTIME_QUOTE_REQUIRED')
    for key in ('bid_size','ask_size'):value[key]=exact_units(value[key])
    if not 0<=value['ask_ticks']-value['bid_ticks']<=4 or min(value['bid_size'],value['ask_size'])<1:
        raise ValueError('INVALID_BOOK')
    return value


def run_bracket(state,value_factory,hold_seconds=20,risk_check=None,before_send=None):
    """Run one paper plan. Factory executes after connection and flat preflight.

    The factory may return a bounded PLUMBING_ONLY fixture for a supervised test,
    or a validated strategy plan. An unresolved journal prevents any next entry.
    """
    state=Path(state);folder=state/'execution-journals';folder.mkdir(mode=0o700,exist_ok=True)
    lock=(state/'execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    p=Session(None,before_send);journal=None;value=None;result=None;first=None
    try:
        if unresolved(folder):raise RuntimeError('UNRESOLVED_EXECUTION_JOURNAL')
        p.connect();qty,orders=p.snapshot()
        if qty or orders or p.failure:raise RuntimeError('PREFLIGHT_NOT_FLAT_OR_CLEAN')
        first=p.next_id
        value=value_factory(first)
        journal=Journal(folder,value);p.journal=journal
        brackets=bracket_orders(value,first)
        # Register all identities before the final child can transmit the group.
        p.w.expected={o.orderId:copy.deepcopy(o) for o in brackets}
        for order in brackets:
            p.send(order)
        end=time.monotonic()+hold_seconds
        acknowledged_by=time.monotonic()+5
        while time.monotonic()<end:
            p.pump(.05)
            stop=p.orders.get(first+2,{});status=p.statuses.get(first+2,{}).get('status')
            if stop.get('order_type')=='STP' and status in ACTIVE:p.protection_seen=True
            if p.failure:break
            if all(p.terminal(first+i) for i in range(3)):break
            if any(x['order_id']!=first for x in p.executions.values()):break
            if time.monotonic()>acknowledged_by and not p.protection_seen:
                p.failure='PROTECTION_ACK_TIMEOUT';break
            if risk_check and risk_check(p,first,value):break
        p.close_owned(first,value['direction'])
        result=p.finish(first,value['direction'])
        result.update(mode=value.get('mode','STRATEGY_PAPER'),signal_id=value['signal_id'],
                      failure=p.failure,journal=str(journal.path))
        # Even a cleaned-up rejected order is not a passing execution test.
        journal.write('COMPLETE',result=result)
        return result
    except Exception as e:
        # If dispatch began, bounded owned cleanup is attempted. Never replay a
        # bracket or infer an absent old fill from a recent-history query.
        cleanup=None
        if journal and first is not None and p.w.isConnected():
            try:
                p.close_owned(first,value['direction'])
                cleanup=p.finish(first,value['direction'])
            except Exception as cleanup_error:cleanup={'failure':type(cleanup_error).__name__+':'+str(cleanup_error)}
        failure=str(e) if isinstance(e,(ValueError,RuntimeError)) else type(e).__name__
        if journal:journal.write('ATTENTION',failure=failure,cleanup=cleanup)
        return {'failure':failure,'cleanup':cleanup,'journal':str(journal.path) if journal else None,
                'flat_verified':False,'mode':'PAPER_ONLY'}
    finally:
        p.disconnect()
        if journal:journal.close()
        lock.close()
