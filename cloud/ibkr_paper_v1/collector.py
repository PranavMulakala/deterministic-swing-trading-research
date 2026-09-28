"""Paper-account-only continuous IBKR observation. Order messages are denied.

IBKR tick timestamps have second precision. Preserve receipt time separately;
this stream is not labeled equivalent to Databento nanosecond exchange events.
"""
import argparse
import fcntl
import json
import logging
import math
from pathlib import Path
import shutil
import signal
import sqlite3
import threading
import time
from datetime import timedelta

from ibapi.client import EClient
from ibapi.common import PROTOBUF_MSG_ID
from ibapi.contract import Contract
from ibapi.message import OUT
from ibapi.wrapper import EWrapper
from cloud.ibkr_paper_v1.operations import calendar_rows, connect, session_for, utcnow, write_health

ALLOWED = frozenset((OUT.START_API, OUT.REQ_MANAGED_ACCTS, OUT.REQ_CURRENT_TIME,
                    OUT.REQ_CONTRACT_DATA, OUT.REQ_MARKET_DATA_TYPE, OUT.REQ_MKT_DATA,
                    OUT.CANCEL_MKT_DATA, OUT.REQ_TICK_BY_TICK_DATA, OUT.CANCEL_TICK_BY_TICK_DATA))


def contract_ok(c):
    return (c.conId > 0 and c.symbol == 'MNQ' and c.localSymbol == 'MNQZ6'
            and c.secType == 'FUT' and c.exchange == 'CME' and c.currency == 'USD'
            and c.multiplier == '2' and c.lastTradeDateOrContractMonth == '20261218')


def ticks(value):
    if not math.isfinite(value) or value <= 0 or abs(value*4-round(value*4)) > 1e-6:
        raise ValueError('invalid_price')
    return round(value*4)


class Collector(EWrapper, EClient):
    def __init__(self, dbpath, expected, stop):
        EClient.__init__(self,self)
        self.expected, self.stop = expected, stop
        self.ready, self.accounts_ready, self.contract_ready = (threading.Event() for _ in range(3))
        self.accounts, self.contracts = [], []
        self.db = sqlite3.connect(dbpath,check_same_thread=False,timeout=10)
        self.lock = threading.Lock()
        self.pending = 0
        self.quotes = self.trades = 0
        self.last_quote = self.last_trade = 0.0
        self.data_type = None
        self.errors = []
        self.verified = False
        self.accept_events = False
        self.capture_window = None
        self.tick_requests = set()
        self.fatal = False

    def sendMsg(self, msgId, msg):
        if msgId not in ALLOWED:
            raise RuntimeError('outbound_message_denied')
        return super().sendMsg(msgId,msg)

    def sendMsgProtoBuf(self, msgId, msg):
        if msgId-PROTOBUF_MSG_ID not in ALLOWED:
            raise RuntimeError('outbound_protobuf_message_denied')
        return super().sendMsgProtoBuf(msgId,msg)

    def event(self,kind,payload):
        with self.lock:
            self.db.execute('INSERT INTO events(received_ns,kind,payload) VALUES(?,?,?)',
                            (time.time_ns(),kind,json.dumps(payload,separators=(',',':'))))
            self.pending += 1
            if self.pending >= 100:
                self.db.commit()
                self.pending = 0

    def flush(self):
        with self.lock:
            self.db.commit()
            self.pending = 0

    def checkpoint(self,health):
        with self.lock:
            self.db.execute('INSERT INTO events(received_ns,kind,payload) VALUES(?,?,?)',
                            (time.time_ns(),'health',json.dumps(health)))
            write_health(self.db,health)
            self.pending=0

    def in_capture_window(self):
        return (self.accept_events and self.capture_window is not None
                and self.capture_window[0] <= time.time_ns() < self.capture_window[1])

    def nextValidId(self,orderId):
        self.ready.set()

    def managedAccounts(self,accountsList):
        self.accounts=sorted(x.strip() for x in accountsList.split(',') if x.strip())
        self.accounts_ready.set()

    def contractDetails(self,reqId,details):
        if reqId == 101:
            self.contracts.append(details)

    def contractDetailsEnd(self,reqId):
        if reqId == 101:
            self.contract_ready.set()

    def marketDataType(self,reqId,marketDataType):
        if reqId == 102:
            self.data_type=marketDataType

    def error(self,reqId,errorTime,errorCode,errorString,advancedOrderRejectJson=''):
        self.errors=(self.errors+[errorCode])[-20:]
        # A disconnect/data-loss cycle invalidates coverage even if IB reconnects.
        if errorCode in (1100,1101,1102,1300,10197):
            self.fatal=True
        self.event('broker_status',{'code':errorCode,'request_id':reqId})

    def tickByTickBidAsk(self,reqId,stamp,bidPrice,askPrice,bidSize,askSize,attrib):
        if not self.verified or not self.in_capture_window() or reqId != 103:
            return
        try:
            bid,ask=ticks(bidPrice),ticks(askPrice)
            if bid > ask or bidSize < 1 or askSize < 1:
                raise ValueError('invalid_book')
            self.event('quote',{'bid_ticks':bid,'ask_ticks':ask,'bid_size':str(bidSize),
                'ask_size':str(askSize),'broker_time_seconds':stamp,
                'contract':'MNQZ6','data_type':self.data_type})
            self.quotes+=1
            self.last_quote=time.monotonic()
        except ValueError:
            self.event('invalid_quote',{})

    def tickByTickAllLast(self,reqId,tickType,stamp,price,size,attrib,exchange,specialConditions):
        if not self.verified or not self.in_capture_window() or reqId != 104:
            return
        try:
            p=ticks(price)
            if size <= 0:
                raise ValueError('invalid_size')
            self.event('trade',{'price_ticks':p,'size':str(size),'broker_time_seconds':stamp,
                'contract':'MNQZ6','tick_type':tickType,'unreported':bool(attrib.unreported),
                'data_type':self.data_type,
                'past_limit':bool(attrib.pastLimit),'exchange':exchange,
                'special_conditions':specialConditions})
            self.trades+=1
            self.last_trade=time.monotonic()
        except ValueError:
            self.event('invalid_trade',{})


def collect(args,stop):
    dbpath=Path(args.state)/'state.sqlite'
    db=connect(dbpath)
    p=Collector(dbpath,args.account,stop)
    network=None
    h={'status':'CONNECTING','orders_enabled':False,'paper_execution_tested':False,
       'strategy_evaluation_enabled':False,'contract':'MNQZ6'}
    write_health(db,h)
    try:
        p.connect('127.0.0.1',args.port,clientId=72)
        network=threading.Thread(target=p.run,daemon=True)
        network.start()
        if not p.ready.wait(8):
            raise RuntimeError('GATEWAY_LOGIN_OR_API_REQUIRED')
        p.reqManagedAccts()
        if not p.accounts_ready.wait(5) or not args.account.startswith('DU') or p.accounts != [args.account]:
            raise RuntimeError('PAPER_ACCOUNT_NOT_VERIFIED')
        c=Contract()
        c.symbol,c.secType,c.exchange,c.currency,c.multiplier='MNQ','FUT','CME','USD','2'
        c.lastTradeDateOrContractMonth='202612'
        p.reqContractDetails(101,c)
        if not p.contract_ready.wait(8) or len(p.contracts)!=1 or not contract_ok(p.contracts[0].contract):
            raise RuntimeError('CONTRACT_NOT_VERIFIED')
        c=p.contracts[0].contract
        p.verified=True
        p.event('connection',{'contract':c.localSymbol,'con_id':c.conId,
                             'timestamp_basis':'BROKER_SECONDS_AND_LOCAL_RECEIPT_NS'})
        p.reqMarketDataType(1)
        p.reqMktData(102,c,'',False,False,[])
        started=time.monotonic()
        while not stop.wait(5):
            if args.max_seconds and time.monotonic()-started >= args.max_seconds:
                stop.set()
                break
            if not p.isConnected() or p.fatal or not network.is_alive():
                raise RuntimeError('BROKER_DISCONNECTED_OR_SESSION_CONFLICT')
            now=utcnow()
            if now.date().isoformat() >= '2026-12-18':
                raise RuntimeError('CONTRACT_ROLL_REVIEW_REQUIRED')
            if shutil.disk_usage(args.state).free < args.min_free_bytes:
                raise RuntimeError('DISK_RESERVE_REACHED')
            rows=calendar_rows(args.references,now)
            session=session_for(rows,now)
            active=session is not None and session[0] <= now < session[1]
            # Subscribe ahead of the open; callbacks enforce the exact recording
            # interval, avoiding a five-second polling delay at the opening bell.
            subscribe=session is not None and session[0]-timedelta(minutes=15) <= now < session[1]
            p.capture_window=((int(session[0].timestamp()*1e9),int(session[1].timestamp()*1e9))
                              if session else None)
            p.accept_events=subscribe
            if subscribe and not p.tick_requests:
                p.reqTickByTickData(103,c,'BidAsk',0,False)
                p.tick_requests.add(103)
                p.reqTickByTickData(104,c,'AllLast',0,False)
                p.tick_requests.add(104)
            elif not subscribe and p.tick_requests:
                for reqid in sorted(p.tick_requests):
                    p.cancelTickByTickData(reqid)
                p.tick_requests.clear()
                p.last_quote=p.last_trade=0
            age=time.monotonic()-p.last_quote if p.last_quote else None
            trade_age=time.monotonic()-p.last_trade if p.last_trade else None
            status='OUTSIDE_RESEARCH_SESSION'
            if active:
                status=('COLLECTING_REALTIME' if p.data_type==1 and age is not None
                        and trade_age is not None and age<=5 and trade_age<=30
                        else 'WAITING_FOR_REALTIME_TICKS')
            h.update(status=status,market_data_type=p.data_type,quote_age_seconds=age,
                trade_age_seconds=trade_age,connection_quote_count=p.quotes,
                connection_trade_count=p.trades,error_codes=p.errors)
            # Use the stream writer's connection and mutex for its heartbeat.
            # A second writer can otherwise starve behind continuous tick batches.
            p.checkpoint(h)
    except Exception as exc:
        # Provider errors and private account values never enter stdout.
        h.update(status=str(exc) if type(exc) is RuntimeError else type(exc).__name__)
        if isinstance(exc,sqlite3.Error):
            h['sqlite_error_name']=getattr(exc,'sqlite_errorname','unknown')
    finally:
        p.accept_events=False
        if p.isConnected():
            for reqid in sorted(p.tick_requests):
                p.cancelTickByTickData(reqid)
            if p.verified:
                p.cancelMktData(102)
        p.disconnect()
        if network:
            network.join(timeout=5)
        p.flush()
        p.db.close()
        if stop.is_set():
            h['status']='STOPPED'
        write_health(db,h)
        db.close()
    return h['status']


if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    parser=argparse.ArgumentParser()
    parser.add_argument('--account',required=True)
    parser.add_argument('--port',type=int,choices=(4002,7497),default=4002)
    parser.add_argument('--state',default='/var/lib/ibkr-paper')
    parser.add_argument('--references',default='/var/lib/trading-collector/references')
    parser.add_argument('--min-free-bytes',type=int,default=5*1024**3)
    parser.add_argument('--max-seconds',type=int,default=0)
    args=parser.parse_args()
    if not args.account.startswith('DU'):
        parser.error('A verified paper account is required')
    Path(args.state).mkdir(parents=True,exist_ok=True)
    with (Path(args.state)/'collector.lock').open('w') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stop=threading.Event()
        signal.signal(signal.SIGTERM,lambda *_:stop.set())
        signal.signal(signal.SIGINT,lambda *_:stop.set())
        while not stop.is_set():
            print(json.dumps({'status':collect(args,stop)}),flush=True)
            if args.max_seconds or stop.wait(60):
                break
