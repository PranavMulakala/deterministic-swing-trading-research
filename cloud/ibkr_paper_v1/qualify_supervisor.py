"""Reviewed September 21 paper activation; never run automatically by a service."""
import argparse
import grp
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
from ibapi.contract import Contract
from cloud.ibkr_paper_v1.broker_execution import Session,unresolved,CLIENT
from cloud.ibkr_paper_v1.broker_snapshot import capture
from cloud.ibkr_paper_v1.operations import utcnow
from cloud.ibkr_paper_v1.reconciliation import inspect
from cloud.ibkr_paper_v1.strategy_runtime import qualification


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--approve-paper-service',action='store_true',required=True)
    parser.parse_args()
    root=Path('/opt/ibkr-paper-v1/cloud/ibkr_paper_v1')
    folder=Path('/var/lib/ibkr-paper/execution-journals')
    names=['d0512defa10a0f8354cd404b0aae46b589c823b0a22f9560f250344b2c4bb06e.jsonl',
           '15a1834b8dc9df33ffcd61aeeb478fbfb267cf6f41bb617cac607135d3d07434.jsonl']
    proof=[];owned={}
    for name,expected in zip(names,[0,2]):
        raw=(folder/name).read_bytes();rows=[json.loads(x) for x in raw.splitlines()]
        assert rows[0]['plan']['mode']=='PLUMBING_ONLY' and rows[-1]['kind']=='COMPLETE'
        r=rows[-1]['result']
        assert r['failure'] is None and r['flat_verified'] and r['protection_acknowledged'] and r['fill_count']==expected
        s=Session(None);s.contract=Contract();s.contract.conId=815824267
        s.w.expected={row['order_id']:SimpleNamespace(**row['order']) for row in rows if row['kind']=='SEND_UNKNOWN'}
        s.w.sent=set(s.w.expected)
        for oid,o in s.w.expected.items():owned[oid]={'side':o.action,'order_ref':o.orderRef}
        for row in rows:
            if row['kind']=='CALLBACK':s.consume(row['event'])
        assert s.failure is None,s.failure
        proof.append({'file':name,'sha256':hashlib.sha256(raw).hexdigest(),
            'fill_count':r['fill_count'],'fees_cents':r['fees_cents'],'current_callback_validation_passed':True})
    assert not unresolved(folder)
    after=time.time_ns()
    snapshot=capture('/var/lib/ibkr-paper/broker-snapshots')
    full=json.loads(Path(snapshot['file']).read_text())
    observation=inspect(full,owned,815824267,CLIENT,time.time_ns(),after)
    assert observation['status']=='OBSERVED_FLAT' and observation['all_execution_fees_known']
    modules=['broker_execution.py','strategy_runtime.py','execution.py','signal_adapter.py',
        'tape_adapter.py','native_simulator.py','reconciliation.py','session_audit.py','collector.py','margin_preview.py']
    q={'version':1,'paper_account':'DUT109401','contract':'MNQZ6','enable_paper':True,
       'fee_reserve_cents':400,'cancel_test_passed':True,'filled_round_trip_passed':True,
       'review_by':'2026-10-21','qualified_at':utcnow().isoformat(),
       'code_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in modules},
       'proof':proof,'flat_snapshot_sha256':snapshot['sha256'],
       'scope':'EXPERIMENTAL_PAPER_ONLY_NOT_LIVE_READINESS',
       'remaining_evidence':['Complete warmup and prospective sessions','Native stop/target fill examples',
          'Overnight authenticated recovery','Active-position crash recovery remains fail-closed']}
    path=Path('/etc/ibkr-paper/execution-qualification.json');temp=path.with_suffix('.tmp')
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:json.dump(q,f,indent=2);f.flush();os.fsync(f.fileno())
    os.chown(temp,0,grp.getgrnam('ibkr-paper').gr_gid);os.chmod(temp,0o640);os.replace(temp,path)
    qualification(path)
    print(json.dumps({'qualification_verified':True,'proof':proof,'flat_snapshot':snapshot,
        'configuration_sha256':hashlib.sha256(path.read_bytes()).hexdigest()},indent=2))


if __name__=='__main__':main()
