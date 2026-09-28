"""Always-on paper strategy supervisor, independent of the owner's computer.

Armed does not mean every session is tradable: complete prior-session data,
current-session quality, quotes, fees, margin and durable risk gates must pass.
No forced test trade is classified as a strategy trade. Unknown execution state
pauses entries persistently instead of re-sending an order after restart.
"""
import argparse
from datetime import datetime,timedelta,timezone
import fcntl
import hashlib
import json
import logging
from pathlib import Path
import signal
import sqlite3
import threading
import time

from cloud.ibkr_paper_v1.broker_execution import run_bracket,latest_quote,unresolved,CLIENT
from cloud.ibkr_paper_v1.execution import Ledger,plan,SYMBOL,NS,NY,canonical
from cloud.ibkr_paper_v1.margin_preview import preview
from cloud.ibkr_paper_v1.operations import calendar_rows,session_for,utcnow
from cloud.ibkr_paper_v1.reconciliation import exact_units
from cloud.ibkr_paper_v1.session_analysis import bounds,bars_from_tape,atomic_json
from cloud.ibkr_paper_v1.session_audit import audit_session
from cloud.ibkr_paper_v1.signal_adapter import MinuteStream
from cloud.ibkr_paper_v1.tape_adapter import normalize
from cloud.ibkr_paper_v1.tape_adapter import Tape
from cloud.ibkr_paper_v1.native_simulator import simulate


class Feed:
    """Current-day prefix, replayed causally; old signals are never sent late."""
    def __init__(self,db,rows,day,now):
        dates=[x['date'] for x in rows];i=dates.index(day)
        if i==0:raise ValueError('NO_PREVIOUS_CALENDAR_SESSION')
        previous=rows[i-1];a,b=bounds(previous)
        db.execute('BEGIN')
        try:
            audit=audit_session(db,previous['date'],a,b,now)
            if audit['status']!='OBSERVATION_CHECKS_PASSED':raise ValueError('PREVIOUS_SESSION_INCOMPLETE')
            previous_stream,source=bars_from_tape(db,previous)
        finally:db.rollback()
        self.stream=MinuteStream(day,SYMBOL,previous_stream.bars,SYMBOL)
        self.prior_source=source;self.last_id=0;self.last_received=None;self.last_quote=None
        self.seen_signals=set();self.pending=[];self.halt=None
        self.start=self.stream.start
        self.db=db
        row=db.execute('SELECT MIN(id) FROM events WHERE received_ns>=?',(self.start,)).fetchone()
        if row[0] is not None:self.last_id=row[0]-1
        else:self.last_id=db.execute('SELECT COALESCE(MAX(id),0) FROM events').fetchone()[0]
    def poll(self):
        rows=self.db.execute('SELECT id,received_ns,kind,payload FROM events WHERE id>? ORDER BY id LIMIT 5000',
                             (self.last_id,)).fetchall()
        for eid,received,kind,raw in rows:
            self.last_id=eid
            if received<self.start:continue
            if received>=self.start+390*60*NS:continue
            if self.last_received is not None and received<self.last_received:raise ValueError('RECEIPT_CLOCK_REGRESSION')
            self.last_received=received;p=json.loads(raw)
            if (kind.startswith('invalid_') or kind=='connection'
                    or (kind=='health' and p.get('status')!='COLLECTING_REALTIME')
                    or (kind=='broker_status' and p.get('code') in (1100,1101,1102,1300,10197))):
                raise ValueError('SESSION_FEED_INTERRUPTION')
            if kind not in ('quote','trade'):continue
            e=normalize(eid,received,kind,p)
            if kind=='quote':
                if self.last_quote is None and received-self.start>NS:raise ValueError('OPENING_QUOTES_MISSING')
                if self.last_quote is not None and received-self.last_quote>NS:raise ValueError('QUOTE_GAP_OVER_ONE_SECOND')
                self.last_quote=received;self.stream.advance(received)
            else:self.stream.trade(received,e['price_ticks'],e['size'])
            if self.stream.halt:raise ValueError(self.stream.halt)
        for s in self.stream.signals:
            if s['id'] not in self.seen_signals:
                self.pending.append(s);self.seen_signals.add(s['id'])
        return len(rows)


def ingest(ledger,p,first,value):
    for oid,status in p.statuses.items():
        ledger.record_order_status(oid,status['status'],exact_units(status['filled']),
            exact_units(status['remaining']),status['perm_id'],status['received_ns'])
    for eid,e in p.executions.items():
        leg={first:'entry',first+1:'target',first+2:'stop',first+3:'time_exit'}[e['order_id']]
        f=p.fees.get(eid);fee=None
        if f is not None:
            if f['currency']!='USD':raise ValueError('FEE_CURRENCY_UNSUPPORTED')
            fee=exact_units(f['amount'],100)
        ledger.record_fill(eid,value['signal_id'],leg,exact_units(e['price'],4),fee,
            dict(account=value['account'],contract=SYMBOL,quantity=1,
                 side={'BOT':'BUY','SLD':'SELL'}[e['side']],order_id=e['order_id']))


def write_status(state,status,**values):
    atomic_json(Path(state)/'execution-health.json',dict(status=status,updated_at=utcnow().isoformat(),
        paper_only=True,live_trading_authorized=False,**values))


def qualification(path):
    q=json.loads(Path(path).read_text())
    if (q.get('paper_account')!='DUT109401' or q.get('contract')!=SYMBOL
            or q.get('enable_paper') is not True or q.get('fee_reserve_cents')!=400
            or q.get('cancel_test_passed') is not True or q.get('filled_round_trip_passed') is not True):
        raise ValueError('EXECUTION_QUALIFICATION_REQUIRED')
    if datetime.now(timezone.utc).date().isoformat()>q['review_by']:raise ValueError('EXECUTION_REVIEW_DUE')
    expected={'broker_execution.py','strategy_runtime.py','execution.py','signal_adapter.py',
              'tape_adapter.py','native_simulator.py','reconciliation.py','session_audit.py',
              'collector.py','margin_preview.py'}
    hashes=q.get('code_sha256',{})
    if set(hashes)!=expected:raise ValueError('QUALIFIED_CODE_MANIFEST_REQUIRED')
    for name,wanted in hashes.items():
        if hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()!=wanted:
            raise ValueError('QUALIFIED_CODE_CHANGED')
    return q


def pause(ledger,reason):
    with ledger.atomic():ledger.db.execute('UPDATE portfolio SET paused=COALESCE(paused,?)',(reason,))


def day_margin(state,day):
    path=Path(state)/('margin-'+day+'.json')
    if path.exists():return json.loads(path.read_text())
    r=preview(state)
    e=r.get('estimate') or {}
    if (r.get('failure') or e.get('warning_present') or e.get('rejection_present')
            or e.get('margin_currency')!='USD' or e.get('commission_currency')!='USD'):
        raise ValueError('MARGIN_PREVIEW_NOT_VERIFIED')
    margin=exact_units(e['initial_margin_change'],100)
    fees=exact_units(e['commission_and_fees'],100)*2
    if margin<=0 or not 0<fees<=400:raise ValueError('MARGIN_OR_FEE_RESERVE_INSUFFICIENT')
    value={'initial_margin_cents':margin,'estimated_round_trip_fee_cents':fees,
        'source_sha256':r['sha256'],'estimated_not_guaranteed':True,'date':day}
    atomic_json(path,value);return value


def comparison(db,value,result):
    """Observed tape and actual fees; never call the model an executable price."""
    try:
        end=time.time_ns()
        tape=Tape(db,value['planned_at_ns'],end)
        model=simulate(value,tape,round_trip_fee_cents=result['fees_cents'])
        model['broker_net_pnl_cents']=result['net_pnl_cents']
        model['broker_fill_count']=result['fill_count']
        model['difference_cents']=(result['net_pnl_cents']-model['net_pnl_cents']
            if model['net_pnl_cents'] is not None else None)
        model['source']=tape.metadata
        model['actual_time_exit_semantics']='CANCEL_NATIVE_ORDERS_WAIT_TERMINAL_CONFIRM_POSITION_THEN_MARKET'
        model['comparison_is_execution_equivalence']=False
        return model
    except (ValueError,KeyError,TypeError) as e:
        return {'status':'COMPARISON_DATA_BLOCKED','reason':str(e),'difference_cents':None}


def run(state,qualification_path,stop):
    state=Path(state)
    lock=(state/'strategy.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    ledger=Ledger(state/'strategy-ledger.sqlite')
    db=sqlite3.connect((state/'state.sqlite').as_uri()+'?mode=ro',uri=True,timeout=10)
    db.execute('PRAGMA query_only=ON')
    feed=None;active_day=None;blocked_day=None;last_health=0;last_mark=0
    qualified=qualification(qualification_path)
    source_hash=hashlib.sha256(canonical(qualified).encode()).hexdigest()
    try:
        while not stop.is_set():
            now=utcnow();day=now.astimezone(NY).date().isoformat()
            if day!=active_day:active_day=day;feed=None;blocked_day=None
            try:
                qualification(qualification_path)
                reason=ledger.db.execute('SELECT paused FROM portfolio').fetchone()[0]
                if reason:raise RuntimeError('PERSISTENT_PAUSE:'+reason)
                if unresolved(state/'execution-journals'):raise RuntimeError('UNRESOLVED_EXECUTION_JOURNAL')
                if ledger.db.execute("SELECT 1 FROM intents WHERE phase!='RECONCILED_FLAT'").fetchone():
                    raise RuntimeError('UNRESOLVED_STRATEGY_INTENT')
                rows=calendar_rows(state/'references',now);session=session_for(rows,now)
                if session is None or not session[0]<=now<session[1]:
                    write_status(state,'OUTSIDE_SESSION',paper_armed=True,orders_eligible=False)
                    stop.wait(30);continue
                if blocked_day:raise ValueError(blocked_day)
                if feed is None:feed=Feed(db,rows,day,now)
                while feed.poll()==5000:pass
                if feed.last_quote is None or not 0<=time.time_ns()-feed.last_quote<=NS:
                    raise ValueError('CURRENT_QUOTES_STALE')
                margin=day_margin(state,day)
                if time.monotonic()-last_health>5:
                    write_status(state,'PAPER_ARMED_WAITING_FOR_SIGNAL',paper_armed=True,orders_eligible=True,
                        strategy_candidate=True,signals_observed=len(feed.stream.signals),last_event_id=feed.last_id)
                    last_health=time.monotonic()
                while feed.pending:
                    candidate=feed.pending.pop(0)
                    if time.time_ns()>=candidate['signal_ns']+2*NS:continue
                    info={}
                    def factory(first):
                        # Connecting/preflight may consume the brief entry window.
                        # A missed window is abstention, never a chased entry.
                        while time.time_ns()<candidate['signal_ns']+NS:stop.wait(.01)
                        q=latest_quote(state,NS//4)
                        value=plan(candidate,q,time.time_ns(),400,source_hash)
                        cash=ledger.db.execute('SELECT cash_cents FROM portfolio').fetchone()[0]
                        if margin['initial_margin_cents']+value['planned_risk_cents']+2500>cash:
                            raise ValueError('RESEARCH_ALLOCATION_MARGIN_BUFFER')
                        ledger.reserve(value,first,time.time_ns())
                        info.update(first=first,value=value)
                        return value
                    def before_send(oid):
                        if oid==info['first']+3:
                            with ledger.atomic():
                                ledger.db.execute('INSERT INTO dispatch VALUES(?,?,?,?)',
                                    (oid,info['value']['signal_id'],'time_exit','UNSENT'))
                        ledger.before_send(oid)
                    def risk(p,first,value):
                        nonlocal last_mark,last_health
                        if time.monotonic()-last_mark<.25:return False
                        last_mark=time.monotonic();ingest(ledger,p,first,value)
                        if time.monotonic()-last_health>5:
                            write_status(state,'PAPER_POSITION_MONITORED' if p.executions else 'PAPER_ORDER_PENDING',
                                paper_armed=True,orders_eligible=False,signal_id=value['signal_id'],
                                protection_acknowledged=p.protection_seen)
                            last_health=time.monotonic()
                        if stop.is_set():return True
                        if utcnow().astimezone(NY).hour>=12:return True
                        try:q=latest_quote(state)
                        except ValueError:q={}
                        action=ledger.mark_position(value['signal_id'],q,time.time_ns())['action']
                        return action in ('CLOSE_REQUIRED_WITHOUT_DUPLICATE_EXIT','VERIFY_PROTECTION_AND_RECONCILE')
                    seconds=max(1,(datetime.combine(now.astimezone(NY).date(),datetime.min.time(),NY)
                        .replace(hour=12)-now.astimezone(NY)).total_seconds())
                    write_status(state,'PAPER_ORDER_ACTIVE_OR_RECONCILING',paper_armed=True,orders_eligible=False,
                                 signal_id=candidate['id'])
                    result=run_bracket(state,factory,hold_seconds=seconds,risk_check=risk,before_send=before_send)
                    if 'value' not in info:
                        with ledger.atomic():ledger.db.execute('INSERT INTO audit(kind,payload) VALUES(?,?)',
                            ('ENTRY_ABSTAINED',canonical({'signal':candidate['id'],'result':result})))
                        continue
                    # Reconstruct only validated callbacks from the journal.
                    from cloud.ibkr_paper_v1.broker_execution import Session
                    from cloud.ibkr_paper_v1.execution import bracket_orders
                    from ibapi.contract import Contract
                    import copy
                    s=Session(None);s.contract=Contract();s.contract.conId=0
                    for e in result.get('executions',[]):
                        s.executions[e['execution_id']]=e;s.contract.conId=e['con_id']
                    s.fees={f['execution_id']:f for f in result.get('fees',[])}
                    # Status quantities/IDs are preserved in the durable journal.
                    for line in Path(result['journal']).read_text().splitlines():
                        r=json.loads(line)
                        if r['kind']=='CALLBACK' and r['event']['kind']=='status':
                            s.statuses[r['event']['order_id']]=r['event']
                    ingest(ledger,s,info['first'],info['value'])
                    if not result.get('flat_verified') or result.get('failure'):
                        pause(ledger,'EXECUTION_REVIEW_REQUIRED');raise RuntimeError('EXECUTION_REVIEW_REQUIRED')
                    sid=info['value']['signal_id']
                    if result['fill_count']:
                        ledger.reconcile_flat(sid,0,[],True,{})
                    else:ledger.reconcile_cancelled_unfilled(sid,0,[],True)
                    if result['fees_cents']>400:pause(ledger,'FEE_RESERVE_EXCEEDED')
                    result['comparison']=comparison(db,info['value'],result)
                    atomic_json(state/'strategy-results'/(hashlib.sha256(sid.encode()).hexdigest()+'.json'),result)
                stop.wait(.1)
            except ValueError as e:
                reason=str(e)
                if feed is not None or reason in ('PREVIOUS_SESSION_INCOMPLETE','NO_PREVIOUS_CALENDAR_SESSION'):
                    blocked_day=reason
                write_status(state,'DATA_OR_RISK_BLOCKED',paper_armed=True,orders_eligible=False,reason=reason)
                stop.wait(30)
            except Exception as e:
                reason=str(e) if isinstance(e,RuntimeError) else type(e).__name__
                write_status(state,'ATTENTION_REQUIRED',paper_armed=True,orders_eligible=False,reason=reason)
                stop.wait(30)
    finally:
        write_status(state,'SUPERVISOR_STOPPED',paper_armed=False,orders_eligible=False)
        ledger.close();db.close();lock.close()


if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    p=argparse.ArgumentParser();p.add_argument('--state',default='/var/lib/ibkr-paper')
    p.add_argument('--qualification',default='/etc/ibkr-paper/execution-qualification.json')
    args=p.parse_args();stop=threading.Event()
    signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
    run(args.state,args.qualification,stop)
