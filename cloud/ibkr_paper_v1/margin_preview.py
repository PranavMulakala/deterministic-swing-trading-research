"""One paper-only IBKR what-if margin/commission preview, never an executable order."""
from decimal import Decimal
import hashlib
import json
import logging
import math
from pathlib import Path
import sqlite3
import threading
import time

from ibapi.client import EClient
from ibapi.common import PROTOBUF_MSG_ID
from ibapi.const import UNSET_DOUBLE
from ibapi.contract import Contract
from ibapi.message import OUT
from ibapi.order import Order
from cloud.ibkr_paper_v1.broker_snapshot import Snapshot,ALLOWED
from cloud.ibkr_paper_v1.collector import contract_ok
from cloud.ibkr_paper_v1.execution import ACCOUNT
from cloud.ibkr_paper_v1.operations import utcnow


def number(value):
    if value in ('',None,UNSET_DOUBLE):return None
    try:
        parsed=Decimal(str(value))
        return str(parsed) if parsed.is_finite() and abs(parsed)<Decimal('1e100') else None
    except Exception:return None


class Preview(Snapshot):
    def __init__(self):
        super().__init__()
        self._preview_sending=False
        self.contracts=[]
        self.contract_end=threading.Event()
        self.preview_end=threading.Event()
        self.preview_result=None

    def permitted(self,msg_id):
        return (msg_id in ALLOWED or msg_id==OUT.REQ_CONTRACT_DATA
                or (msg_id==OUT.PLACE_ORDER and self._preview_sending))

    def sendMsg(self,msgId,msg):
        if not self.permitted(msgId):raise RuntimeError('preview_message_denied')
        return EClient.sendMsg(self,msgId,msg)

    def sendMsgProtoBuf(self,msgId,msg):
        if not self.permitted(msgId-PROTOBUF_MSG_ID):raise RuntimeError('preview_protobuf_denied')
        return EClient.sendMsgProtoBuf(self,msgId,msg)

    def placeOrder(self,orderId,contract,order):
        if (self.accounts!=[ACCOUNT] or not contract_ok(contract)
                or order.account!=ACCOUNT or order.whatIf is not True
                or order.totalQuantity!=Decimal(1) or order.action!='BUY'
                or order.orderType!='LMT' or not math.isfinite(order.lmtPrice)
                or order.lmtPrice<=0 or order.orderId!=orderId
                or order.parentId!=0 or order.transmit is not True):
            raise RuntimeError('only_verified_paper_what_if_allowed')
        if self._preview_sending:raise RuntimeError('concurrent_preview_denied')
        self._preview_sending=True
        try:return EClient.placeOrder(self,orderId,contract,order)
        finally:self._preview_sending=False

    def contractDetails(self,reqId,details):
        if reqId==301:self.contracts.append(details)

    def contractDetailsEnd(self,reqId):
        if reqId==301:self.contract_end.set()

    def openOrder(self,orderId,contract,order,state):
        if orderId!=self.next_order_id:return
        if order.whatIf is not True or order.account!=ACCOUNT:
            self.failure='UNEXPECTED_PREVIEW_RESPONSE';self.preview_end.set();return
        self.preview_result={'commission_and_fees':number(state.commissionAndFees),
            'min_commission_and_fees':number(state.minCommissionAndFees),
            'max_commission_and_fees':number(state.maxCommissionAndFees),
            'commission_currency':state.commissionAndFeesCurrency,
            'initial_margin_change':number(state.initMarginChange),
            'maintenance_margin_change':number(state.maintMarginChange),
            'margin_currency':state.marginCurrency,'status':state.status,
            'warning_present':bool(state.warningText),'rejection_present':bool(state.rejectReason)}
        self.preview_end.set()

    def error(self,reqId,errorTime,errorCode,errorString,advancedOrderRejectJson=''):
        super().error(reqId,errorTime,errorCode,errorString,advancedOrderRejectJson)
        if reqId==self.next_order_id and errorCode not in (2104,2106,2107,2108,2158):
            # Classify the permission boundary without printing account details
            # or arbitrary broker text into a public operational report.
            text=errorString.lower().replace('-',' ')
            reason=('READ_ONLY_API' if 'read only' in text else 'OTHER_BROKER_VALIDATION')
            self.errors[-1]['reason']=reason
            self.preview_end.set()


def preview(state_folder):
    p=Preview();network=None
    started=utcnow().isoformat()
    attempted=False
    try:
        p.connect('127.0.0.1',4002,clientId=74)
        network=threading.Thread(target=p.run,daemon=True);network.start()
        if not p.ready.wait(8):raise RuntimeError('GATEWAY_UNAVAILABLE')
        p.reqManagedAccts()
        if not p.accounts_ready.wait(5) or p.accounts!=[ACCOUNT]:raise RuntimeError('PAPER_ACCOUNT_NOT_VERIFIED')
        c=Contract();c.symbol='MNQ';c.secType='FUT';c.exchange='CME';c.currency='USD'
        c.multiplier='2';c.lastTradeDateOrContractMonth='202612'
        p.reqContractDetails(301,c)
        if not p.contract_end.wait(8) or len(p.contracts)!=1 or not contract_ok(p.contracts[0].contract):
            raise RuntimeError('CONTRACT_NOT_VERIFIED')
        c=p.contracts[0].contract
        db=sqlite3.connect((Path(state_folder)/'state.sqlite').as_uri()+'?mode=ro',uri=True)
        row=db.execute("SELECT received_ns,payload FROM events WHERE kind='quote' ORDER BY id DESC LIMIT 1").fetchone()
        db.close()
        if row is None or not 0<=time.time_ns()-row[0]<=5_000_000_000:
            raise RuntimeError('FRESH_QUOTE_REQUIRED_FOR_PREVIEW')
        quote=json.loads(row[1])
        if quote.get('data_type')!=1 or quote.get('contract')!='MNQZ6':raise RuntimeError('QUOTE_NOT_VERIFIED')
        order=Order();order.orderId=p.next_order_id;order.account=ACCOUNT
        order.action='BUY';order.orderType='LMT';order.totalQuantity=Decimal(1)
        order.lmtPrice=quote['ask_ticks']/4;order.tif='DAY';order.whatIf=True
        order.transmit=True;order.orderRef='paper-margin-preview-only'
        p.placeOrder(order.orderId,c,order);attempted=True
        if not p.preview_end.wait(15):p.failure=p.failure or 'PREVIEW_RESPONSE_MISSING'
    except Exception as exc:
        p.failure=str(exc) if type(exc) is RuntimeError else type(exc).__name__
    finally:
        p.disconnect()
        if network:network.join(5)
    result={'started_at':started,'ended_at':utcnow().isoformat(),
            'mode':'PAPER_WHAT_IF_PREVIEW_ONLY','what_if_requested':attempted,
            'executable_order_requested':False,'failure':p.failure,'errors':p.errors,
            'estimate':p.preview_result,'estimate_is_verified_fee_ceiling':False}
    raw=json.dumps(result,indent=2).encode()
    digest=hashlib.sha256(raw).hexdigest()
    folder=Path(state_folder)/'broker-previews';folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=folder/(utcnow().strftime('%Y%m%dT%H%M%S')+'-'+digest[:12]+'.json')
    with path.open('xb') as file:file.write(raw)
    path.chmod(0o600)
    return dict(result,file=str(path),sha256=digest)


if __name__=='__main__':
    import argparse
    logging.disable(logging.CRITICAL)
    parser=argparse.ArgumentParser()
    parser.add_argument('--state',default='/var/lib/ibkr-paper')
    args=parser.parse_args()
    print(json.dumps(preview(args.state),indent=2))
