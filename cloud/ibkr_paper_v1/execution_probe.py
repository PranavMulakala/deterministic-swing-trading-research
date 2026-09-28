"""Explicitly authorized one-contract simulated execution qualification.

Forced plumbing trades never count as strategy signals or performance evidence.
At most two supervised probes per New York day. No live account is supported.
"""
import argparse
from datetime import datetime,timezone
import json
import logging
from pathlib import Path
import time
from cloud.ibkr_paper_v1.broker_execution import run_bracket,latest_quote
from cloud.ibkr_paper_v1.execution import ACCOUNT,SYMBOL,VERSION,NY,NS
from cloud.ibkr_paper_v1.operations import calendar_rows,session_for


def run(state,kind):
    now=datetime.now(timezone.utc)
    day=now.astimezone(NY).date().isoformat()
    rows=calendar_rows(Path(state)/'references',now)
    session=session_for(rows,now)
    if session is None or not session[0]<=now<session[1]:raise ValueError('REGULAR_SESSION_REQUIRED')
    files=list((Path(state)/'execution-journals').glob('*.jsonl'))
    count=0
    for path in files:
        journal=[json.loads(x) for x in path.read_text().splitlines()]
        first=journal[0]
        if (first['plan'].get('mode')=='PLUMBING_ONLY' and first['plan'].get('day')==day
                and any(x['kind']=='SEND_UNKNOWN' for x in journal)):count+=1
    if count>=2:raise ValueError('TWO_PROBES_PER_DAY_MAXIMUM')
    def factory(first):
        q=latest_quote(state)
        entry=q['bid_ticks']-40 if kind=='cancel' else q['ask_ticks']+2
        return dict(version=VERSION,account=ACCOUNT,contract=SYMBOL,direction=1,quantity=1,
            signal_id='PLUMBING_ONLY-'+day+'-'+kind+'-'+str(time.time_ns()),mode='PLUMBING_ONLY',
            day=day,entry_ticks=entry,stop_ticks=entry-10,target_ticks=entry+20,
            expires_ns=time.time_ns()+10*NS,planned_risk_cents=1000,
            planning_fee_reserve_cents=400,performance_evidence=False)
    return run_bracket(state,factory,hold_seconds=3 if kind=='cancel' else 20)


if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    p=argparse.ArgumentParser()
    p.add_argument('--approve-paper-execution',action='store_true',required=True)
    p.add_argument('--kind',choices=('cancel','fill'),required=True)
    p.add_argument('--state',default='/var/lib/ibkr-paper')
    args=p.parse_args()
    print(json.dumps(run(args.state,args.kind),indent=2))
