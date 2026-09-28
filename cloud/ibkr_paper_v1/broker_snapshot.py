"""Read-only paper broker snapshot. Retains query boundaries, not invented history."""
import hashlib
import json
import logging
from pathlib import Path
import threading
import time

from ibapi.client import EClient
from ibapi.common import PROTOBUF_MSG_ID
from ibapi.execution import ExecutionFilter
from ibapi.message import OUT
from ibapi.wrapper import EWrapper

from cloud.ibkr_paper_v1.execution import ACCOUNT
from cloud.ibkr_paper_v1.operations import utcnow

ALLOWED=frozenset((OUT.START_API,OUT.REQ_MANAGED_ACCTS,OUT.REQ_POSITIONS,
                  OUT.CANCEL_POSITIONS,OUT.REQ_ALL_OPEN_ORDERS,OUT.REQ_EXECUTIONS,
                  OUT.REQ_ACCOUNT_SUMMARY,OUT.CANCEL_ACCOUNT_SUMMARY))


class Snapshot(EWrapper,EClient):
    def __init__(self):
        EClient.__init__(self,self)
        self.ready,self.accounts_ready=(threading.Event() for _ in range(2))
        self.ends={x:threading.Event() for x in ('positions','orders','executions','summary')}
        self.accounts=[]
        self.records=[]
        self.failure=None
        self.next_order_id=None
        self.errors=[]

    def sendMsg(self,msgId,msg):
        if msgId not in ALLOWED:raise RuntimeError('read_only_snapshot_message_denied')
        return super().sendMsg(msgId,msg)

    def sendMsgProtoBuf(self,msgId,msg):
        if msgId-PROTOBUF_MSG_ID not in ALLOWED:raise RuntimeError('read_only_snapshot_protobuf_denied')
        return super().sendMsgProtoBuf(msgId,msg)

    def add(self,kind,**value):
        self.records.append({'kind':kind,'receipt_ns':time.time_ns(),**value})

    def account_ok(self,value):
        if value!=ACCOUNT:
            self.failure='ACCOUNT_MISMATCH'
            return False
        return True

    def nextValidId(self,orderId):
        self.next_order_id=orderId
        self.ready.set()

    def managedAccounts(self,accountsList):
        self.accounts=sorted(x for x in accountsList.split(',') if x)
        self.accounts_ready.set()

    def position(self,account,contract,position,avgCost):
        if self.account_ok(account):
            self.add('position',contract=contract.localSymbol,con_id=contract.conId,
                     sec_type=contract.secType,quantity=str(position),average_cost=str(avgCost))

    def positionEnd(self):self.ends['positions'].set();self.add('positions_end')

    def openOrder(self,orderId,contract,order,state):
        if self.account_ok(order.account):
            self.add('order',order_id=orderId,perm_id=order.permId,client_id=order.clientId,
                     contract=contract.localSymbol,con_id=contract.conId,quantity=str(order.totalQuantity),
                     side=order.action,order_type=order.orderType,parent_id=order.parentId,
                     order_ref=order.orderRef,status=state.status)

    def openOrderEnd(self):self.ends['orders'].set();self.add('orders_end')

    def execDetails(self,reqId,contract,execution):
        if reqId==201 and self.account_ok(execution.acctNumber):
            self.add('execution',execution_id=execution.execId,order_id=execution.orderId,
                     perm_id=execution.permId,client_id=execution.clientId,
                     contract=contract.localSymbol,con_id=contract.conId,side=execution.side,
                     quantity=str(execution.shares),price=str(execution.price),
                     broker_time=execution.time,order_ref=execution.orderRef,
                     pending_price_revision=execution.pendingPriceRevision)

    def execDetailsEnd(self,reqId):
        if reqId==201:self.ends['executions'].set();self.add('executions_end')

    def commissionAndFeesReport(self,value):
        self.add('commission',execution_id=value.execId,currency=value.currency,
                 commission_and_fees=str(value.commissionAndFees))

    def accountSummary(self,reqId,account,tag,value,currency):
        if reqId==202 and self.account_ok(account):
            self.add('summary',tag=tag,value=value,currency=currency)

    def accountSummaryEnd(self,reqId):
        if reqId==202:self.ends['summary'].set();self.add('summary_end')

    def error(self,reqId,errorTime,errorCode,errorString,advancedOrderRejectJson=''):
        self.errors.append({'request_id':reqId,'code':errorCode})
        if errorCode not in (2104,2106,2107,2108,2158):
            self.failure='BROKER_ERROR_'+str(errorCode)


def capture(folder):
    p=Snapshot()
    started=utcnow().isoformat()
    network=None
    try:
        p.connect('127.0.0.1',4002,clientId=73)
        network=threading.Thread(target=p.run,daemon=True)
        network.start()
        if not p.ready.wait(8):raise RuntimeError('GATEWAY_UNAVAILABLE')
        p.reqManagedAccts()
        if not p.accounts_ready.wait(5) or p.accounts!=[ACCOUNT]:raise RuntimeError('PAPER_ACCOUNT_NOT_VERIFIED')
        p.reqPositions()
        p.reqAllOpenOrders()
        filt=ExecutionFilter();filt.acctCode=ACCOUNT
        p.reqExecutions(201,filt)
        p.reqAccountSummary(202,'All','TotalCashValue,NetLiquidation,AvailableFunds')
        deadline=time.monotonic()+15
        for done in p.ends.values():
            done.wait(max(0,deadline-time.monotonic()))
        if not all(x.is_set() for x in p.ends.values()):p.failure=p.failure or 'QUERY_END_MARKERS_MISSING'
        # Commissions can arrive after execDetailsEnd. No completeness claim is
        # inferred from this bounded grace period; missing fees remain missing.
        threading.Event().wait(2)
        p.cancelPositions();p.cancelAccountSummary(202)
    except Exception as exc:
        p.failure=str(exc) if type(exc) is RuntimeError else type(exc).__name__
    finally:
        p.disconnect()
        if network:network.join(5)
    result={'version':1,'mode':'PAPER_READ_ONLY','started_at':started,'ended_at':utcnow().isoformat(),
            'paper_account_verified':p.accounts==[ACCOUNT],
            'query_end_markers':{k:v.is_set() for k,v in p.ends.items()},
            'failure':p.failure,'errors':p.errors,'records':p.records,
            'execution_history_scope':'BROKER_API_AVAILABLE_WINDOW_NOT_FULL_ACCOUNT_HISTORY',
            'snapshot_is_atomic':False,'orders_sent':False}
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    raw=json.dumps(result,indent=2).encode()
    digest=hashlib.sha256(raw).hexdigest()
    path=folder/(utcnow().strftime('%Y%m%dT%H%M%S')+'-'+digest[:12]+'.json')
    with path.open('xb') as f:f.write(raw)
    path.chmod(0o600)
    counts={k:sum(r['kind']==k for r in p.records) for k in ('position','order','execution','commission','summary')}
    return {'file':str(path),'sha256':digest,'failure':p.failure,
            'paper_account_verified':result['paper_account_verified'],
            'queries_finished':all(result['query_end_markers'].values()),'record_counts':counts,
            'orders_sent':False,'snapshot_is_atomic':False}


if __name__=='__main__':
    import argparse
    logging.disable(logging.CRITICAL)
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='/var/lib/ibkr-paper/broker-snapshots')
    args=parser.parse_args()
    print(json.dumps(capture(args.out),indent=2))
