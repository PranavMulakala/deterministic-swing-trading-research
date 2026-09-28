"""Scheduled, read-only session analysis; no broker connection or order sender.

Only complete recorded sessions can produce candidate strategy signals. An
incomplete preceding calendar session cannot be skipped in favor of older data.
"""
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from cloud.ibkr_paper_v1.execution import SYMBOL, canonical
from cloud.ibkr_paper_v1.operations import NY, calendar_rows, session_for, utcnow
from cloud.ibkr_paper_v1.session_audit import audit_session
from cloud.ibkr_paper_v1.signal_adapter import MinuteStream, NS
from cloud.ibkr_paper_v1.tape_adapter import Tape

VERSION='receipt_session_analysis_v1_candidate'


def revision():
    folder=Path(__file__).parent
    names=('session_analysis.py','signal_adapter.py','session_audit.py','tape_adapter.py',
           'execution.py','operations.py')
    return hashlib.sha256(b''.join(n.encode()+b'\0'+(folder/n).read_bytes() for n in names)).hexdigest()


def bounds(row):
    day=row['date']
    start=datetime.fromisoformat(day+'T'+row['open']).replace(tzinfo=NY)
    end=datetime.fromisoformat(day+'T'+row['close']).replace(tzinfo=NY)
    if end<=start:raise ValueError('invalid_session_bounds')
    return start,end


def bars_from_tape(db,row,prior=None):
    start,end=bounds(row)
    stream=MinuteStream(row['date'],SYMBOL,prior,SYMBOL if prior else None)
    tape=Tape(db,int(start.timestamp())*NS,int(end.timestamp())*NS)
    for event in tape:
        if event['kind']=='trade':
            stream.trade(event['received_ns'],event['price_ticks'],event['size'])
        else:stream.advance(event['received_ns'])
    stream.advance(int(end.timestamp())*NS)
    if not stream.minute_coverage_complete():raise ValueError('minute_stream_incomplete')
    return stream,tape.metadata


def analyze(db,rows,day,now):
    dates=[r['date'] for r in rows]
    if dates!=sorted(set(dates)):raise ValueError('invalid_calendar_order')
    if day not in dates:raise ValueError('not_a_calendar_session')
    index=dates.index(day)
    row=rows[index]
    start,end=bounds(row)
    result={'version':VERSION,'date':day,'generated_at':now.isoformat(),
            'code_sha256':revision(),'calendar_rows_sha256':hashlib.sha256(canonical(rows).encode()).hexdigest(),
            'contract':SYMBOL,'time_basis':'LOCAL_RECEIPT_NS',
            'candidate_signal_count':None,'candidate_signals':None,
            'strategy_evidence_approved':False,'orders_sent':False,
            'broker_execution_evaluated':False,'net_pnl_cents':None}
    lo,hi=int(start.timestamp())*NS,int(end.timestamp())*NS
    result['capture_cutoff_id']=db.execute('SELECT COALESCE(MAX(id),0) FROM events '
                                         'WHERE received_ns>=? AND received_ns<?',(lo,hi)).fetchone()[0]
    current=audit_session(db,day,start,end,now)
    result['coverage']=current
    if current['status']!='OBSERVATION_CHECKS_PASSED':
        return dict(result,status='DATA_BLOCKED',reason='CURRENT_SESSION_INCOMPLETE_OR_INVALID')
    prior_bars=None
    result['previous_session_date']=dates[index-1] if index else None
    if index:
        previous=rows[index-1]
        a,b=bounds(previous)
        coverage=audit_session(db,previous['date'],a,b,now)
        result['previous_coverage']=coverage
        if coverage['status']=='OBSERVATION_CHECKS_PASSED':
            try:
                prior,source=bars_from_tape(db,previous)
                prior_bars=prior.bars
                result['previous_source']=source
            except (ValueError,KeyError,TypeError) as error:
                result['previous_adapter_error']=str(error)
    try:
        stream,source=bars_from_tape(db,row,prior_bars)
    except (ValueError,KeyError,TypeError) as error:
        return dict(result,status='DATA_BLOCKED',reason='CURRENT_TAPE_ADAPTER_REJECTED',adapter_error=str(error))
    result['source']=source
    result['complete_minute_bars']=len(stream.bars)
    if not stream.warmup_ready:
        return dict(result,status='WARMUP_BLOCKED',reason='IMMEDIATE_PREVIOUS_SESSION_NOT_VALIDATED')
    return dict(result,status='CANDIDATE_SIGNALS_EVALUATED',
                candidate_signal_count=len(stream.signals),candidate_signals=stream.signals,
                execution_comparison='PENDING_VERIFIED_FEES_AND_BROKER_EXECUTION')


def atomic_json(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    handle,name=tempfile.mkstemp(prefix='.analysis-',dir=path.parent)
    try:
        with os.fdopen(handle,'w') as file:
            file.write(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')
            file.flush();os.fsync(file.fileno())
        os.replace(name,path)
        folder=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(folder)
        finally:os.close(folder)
    finally:
        if os.path.exists(name):os.unlink(name)


def load_result(state,day):
    # The day originates from the verified calendar; still constrain file access.
    if datetime.fromisoformat(day).date().isoformat()!=day:raise ValueError('invalid_day')
    path=Path(state)/'analysis'/f'{day}.json'
    if not path.exists():return None
    pointer=json.loads(path.read_text())
    filename=pointer['file']
    if Path(filename).name!=filename:raise ValueError('unsafe_analysis_filename')
    raw=(path.parent/filename).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=pointer['sha256']:raise ValueError('analysis_hash_mismatch')
    value=json.loads(raw)
    if value['date']!=day or value['version']!=VERSION:raise ValueError('analysis_identity_mismatch')
    return value


def save_result(state,result):
    folder=Path(state)/'analysis'
    digest=hashlib.sha256(canonical(result).encode()).hexdigest()
    filename=f"{result['date']}-{digest}.json"
    path=folder/filename
    if not path.exists():atomic_json(path,result)
    elif json.loads(path.read_text())!=result:raise ValueError('immutable_analysis_artifact_changed')
    pointer={'file':filename,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    atomic_json(folder/f"{result['date']}.json",pointer)


def cycle(state,references,now=None):
    now=now or utcnow()
    rows=calendar_rows(references,now)
    session=session_for(rows,now)
    if session is None:return {'status':'NO_SESSION_TODAY','orders_sent':False}
    day=now.astimezone(NY).date().isoformat()
    db=sqlite3.connect((Path(state)/'state.sqlite').as_uri()+'?mode=ro',uri=True,timeout=10)
    try:
        db.execute('PRAGMA query_only=ON')
        if now<session[1]+timedelta(minutes=2):
            db.execute('SELECT id FROM events ORDER BY id DESC LIMIT 1').fetchone()
            return {'status':'WAITING_FOR_SESSION_END','date':day,'orders_sent':False,
                    'recording_read_access_verified':True}
        db.execute('BEGIN')  # One consistent read across current and prior sessions.
        old=load_result(state,day)
        cutoff=db.execute('SELECT COALESCE(MAX(id),0) FROM events WHERE received_ns>=? AND received_ns<?',
            (int(session[0].timestamp())*NS,int(session[1].timestamp())*NS)).fetchone()[0]
        if old is not None and (cutoff!=old['capture_cutoff_id'] or old.get('capture_mutation_detected')):
            result=dict(old,status='DATA_BLOCKED',reason='SESSION_CHANGED_AFTER_FIRST_ANALYSIS',
                        candidate_signal_count=None,candidate_signals=None,
                        generated_at=now.isoformat(),capture_cutoff_id=cutoff,capture_mutation_detected=True)
        elif old is not None and old['code_sha256']==revision():
            return {'status':old['status'],'date':day,'cached':True,'orders_sent':False}
        else:result=analyze(db,rows,day,now)
        save_result(state,result)
        return {k:result[k] for k in ('status','date','candidate_signal_count','orders_sent')}
    finally:db.close()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--state',default='/var/lib/ibkr-paper')
    parser.add_argument('--references',default='/var/lib/ibkr-paper/references')
    args=parser.parse_args()
    print(json.dumps(cycle(args.state,args.references)))
