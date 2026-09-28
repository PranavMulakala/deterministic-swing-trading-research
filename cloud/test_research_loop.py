from copy import deepcopy
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cloud import collector as c
from cloud.research_archive import Archive, DataGap, nanos, NS
from cloud.research_runner import execute, references, verify_pins
from cloud.readiness import assess as assess_readiness
from cloud.learning import review

REPO=Path(__file__).resolve().parents[1]

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,sort_keys=True).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def bar(t,o=99,h=110,l=90,cl=100,vol=20000):
    return {'t':t.isoformat().replace('+00:00','Z'),'o':o,'h':h,'l':l,'c':cl,'v':vol,'vw':100,'n':100}

def fixture(folder):
    root=folder/'code'; archive=folder/'archive'; output=folder/'output'
    archive.mkdir(parents=True)
    pins={}
    for name in ('research/orb_comparison_v1/spec.json','research/orb_quote_v2/execution.json',
                 'research/orb_direct_breakout_v1/config.json',
                 'research/lite_reversal_v1/config.json','cloud/research_policy.json',
                 'cloud/news_context_v1.json'):
        pins[name]=save(root/name,json.loads((REPO/name).read_text()))
    prior=[]; day=datetime(2026,9,4)
    while len(prior)<20:
        if day.weekday()<5: prior.append(day.date().isoformat())
        day-=timedelta(days=1)
    prior=sorted(prior)
    sessions={d:[d+'T09:30:00-04:00',d+'T16:00:00-04:00'] for d in prior}
    warm={'sessions':sessions,'bars':{s:{} for s in c.STOCKS}}
    for s in c.STOCKS:
        for d in prior:
            first=datetime.fromisoformat(d+'T13:30:00+00:00')
            warm['bars'][s][d]=[bar(first+timedelta(minutes=5*i)) for i in range(78)]
    pins['warmup.json']=save(root/'warmup.json',warm)
    save(root/'PINS.json',pins)
    calendar=[{'date':d,'open':'09:30','close':'16:00'} for d in prior+['2026-09-08','2026-09-09']]
    ref={'fetched_at':'2026-09-08T06:00:00Z','calendar':calendar,'actions':[{'corporate_actions':{},'next_page_token':None}],
         'query':{'start':'2026-07-01','end':'2026-12-31'}}
    digest=save(archive/'references/ref.json',ref)
    save(archive/'references/latest.json',{'file':'ref.json','sha256':digest})
    db=c.database(archive/'archive.sqlite')
    opening=datetime(2026,9,8,13,30,tzinfo=timezone.utc)
    start=int(opening.timestamp())
    for window in range(start,start+23400,300):
        dt=datetime.fromtimestamp(window,timezone.utc)
        idx=(window-start)//300
        five=bar(dt)
        if idx==0: five=bar(dt,99,100,90,99.5,40000)
        if idx==1: five=bar(dt,100.2,101,100.1,100.8)
        if idx==2: five=bar(dt,100.5,101,99.99,100.6)
        for stream in c.STREAMS:
            value={'next_page_token':None}
            if stream=='bars5': value['bars']={s:[five] for s in c.SYMBOLS}; count=20
            elif stream=='bars': value['bars']={s:[bar(dt+timedelta(minutes=i)) for i in range(5)] for s in c.SYMBOLS}; count=100
            elif stream in ('news','sector_news'):
                value['news']=[{'id':1,'symbols':['LITE'],'created_at':'2026-09-08T13:31:00Z','updated_at':'2026-09-08T13:31:00Z'}] if idx==0 else []
                count=len(value['news'])
            else:
                s,kind=stream.split(':'); value['symbol']=s; value[kind]=[]
                if kind=='quotes' and idx in (3,77):
                    t=dt+timedelta(microseconds=500000) if idx==3 else dt
                    value[kind]=[{'t':t.isoformat().replace('+00:00','Z'),'bp':100.55 if idx==3 else 101.2,'ap':100.6 if idx==3 else 101.25,'bs':100,'as':100,'c':['R']}]
                count=len(value[kind])
            raw=json.dumps(value,sort_keys=True).encode()
            with db:
                db.execute('INSERT INTO pages VALUES (?,?,?,?,?,?,?,?)',(stream,window,window+300,0,c.iso(window+1500),hashlib.sha256(raw).hexdigest(),count,gzip.compress(raw)))
                db.execute('INSERT OR REPLACE INTO checkpoints VALUES (?,?)',(stream,window+300))
                db.execute('INSERT OR REPLACE INTO health VALUES (?,?,?)',(stream,c.iso(window+1500),None))
    db.close()
    return root,archive,output

class LoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root,cls.archive,cls.output=fixture(Path(cls.temp.name))
        cls.asof=datetime(2026,9,8,20,30,tzinfo=timezone.utc).timestamp()
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_before_close_waits_not_fake_cash(self):
        r=execute(self.root,self.archive,self.output,self.asof-3600)
        self.assertEqual(r['status'],'WAITING_FOR_FIRST_COMPLETED_SESSION')
        self.assertNotIn('results',r)

    def test_full_pipeline_and_idempotency(self):
        r=execute(self.root,self.archive,self.output,self.asof)
        self.assertEqual(r['status'],'REPLAY_COMPLETE_RESEARCH_ONLY',r)
        self.assertEqual(len(r['results']['orb']),8)
        self.assertEqual(len(r['results']['lite']),4)
        self.assertEqual(r['results']['lite_forward']['status'],'WAITING_FOR_FIRST_FORWARD_SESSION')
        self.assertEqual(r['results']['lite_forward']['capital_arms'],[5000,10000])
        self.assertEqual(r['results']['lite_forward']['mode'],'whole')
        self.assertEqual(r['results']['lite_forward']['results'],{})
        self.assertEqual(r['results']['news_context_status'],'not_started_prospective')
        self.assertEqual(r['session_readiness']['status'],'READY_FOR_DELAYED_RESEARCH_SESSION')
        self.assertGreater(len(r['results']['orb']['1s_10bps_A']['trades']),0)
        self.assertTrue(all(a['status']=='passed' for a in r['results']['ledger_audits'].values()))
        self.assertEqual(r['learning']['status'],'collecting_evidence_no_improvement_claim')
        again=execute(self.root,self.archive,self.output,self.asof+60)
        self.assertEqual(r['run_id'],again['run_id'])
        with sqlite3.connect(self.output/'memory.sqlite') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM runs').fetchone()[0],1)
        self.assertTrue(all(n['news_items_observed_before_signal']==0 for n in r['results']['news_annotations']))
        self.assertTrue(all(n['context_items_observed_before_signal'] is None for n in r['results']['news_annotations']))

    def test_readiness_blocks_missing_context_stream(self):
        with sqlite3.connect(self.archive/'archive.sqlite') as db:
            old=db.execute("SELECT end FROM checkpoints WHERE stream='sector_news'").fetchone()[0]
            db.execute("DELETE FROM checkpoints WHERE stream='sector_news'")
        try:
            policy=json.loads((self.root/'cloud/research_policy.json').read_text())
            status=assess_readiness(self.archive,policy,self.asof)
            self.assertEqual(status['status'],'BLOCKED')
            self.assertTrue(any(x.startswith('missing_checkpoints:sector_news') for x in status['reasons']))
        finally:
            with sqlite3.connect(self.archive/'archive.sqlite') as db:
                db.execute("INSERT INTO checkpoints VALUES ('sector_news',?)",(old,))

    def test_forward_capital_arms_are_separate_and_prospective(self):
        from cloud.forward_research import capital_replay
        from research.lite_reversal_v1.test_experiment import bars, config
        with tempfile.TemporaryDirectory() as directory:
            policy=json.loads((self.root/'cloud/research_policy.json').read_text())
            forward=capital_replay(config(),{'2026-09-08':bars('2026-09-08'),'2026-09-09':bars('2026-09-09')},
                                   {},['2026-09-08','2026-09-09'],policy['lite_forward'])
            self.assertEqual(forward['status'],'REPLAY_COMPLETE_RESEARCH_ONLY')
            self.assertEqual(len(forward['results']),8)
            self.assertEqual(
                sorted({int(k.split('_',1)[0]) for k in forward['results']}),[5000,10000])
            for label,run in forward['results'].items():
                self.assertEqual(run['summary']['initial_cash'],float(label.split('_',1)[0]))
                self.assertEqual([d['date'] for d in run['daily_ledger']],['2026-09-09'])
            self.assertGreater(forward['results']['5000_dip_10bps']['summary']['trades'],0)

    def test_missing_stream_blocks(self):
        with sqlite3.connect(self.archive/'archive.sqlite') as db:
            old=db.execute("SELECT end FROM checkpoints WHERE stream='bars5'").fetchone()[0]
            db.execute("UPDATE checkpoints SET end=0 WHERE stream='bars5'")
        try:
            r=execute(self.root,self.archive,self.output,self.asof)
            self.assertEqual(r['status'],'BLOCKED_DATA_OR_INTEGRITY')
            self.assertNotIn('results',r)
        finally:
            with sqlite3.connect(self.archive/'archive.sqlite') as db:
                db.execute("UPDATE checkpoints SET end=? WHERE stream='bars5'",(old,))

    def test_future_receipt_rejected(self):
        arc=Archive(self.archive,self.asof-3600)
        try:
            with self.assertRaises(DataGap): arc.bars('LITE',nanos('2026-09-08T19:55:00Z'),nanos('2026-09-08T20:00:00Z'))
        finally: arc.close()

    def test_frozen_code_tamper(self):
        p=self.root/'warmup.json'; raw=p.read_bytes()
        try:
            p.write_bytes(raw+b' ')
            with self.assertRaises(DataGap): verify_pins(self.root)
        finally: p.write_bytes(raw)

    def test_stale_metadata_rejected(self):
        with self.assertRaises(DataGap): references(self.archive,self.asof+172800)

    def test_no_candidate_from_cash_only(self):
        policy=json.loads((self.root/'cloud/research_policy.json').read_text())
        run={'complete':True,'trades':[],'net_return':0}
        orb={f'{d}s_{b}bps_{a}':deepcopy(run) for d in (1,2) for b in (10,25) for a in ('A','B')}
        r=review(orb,{},policy,['2026-09-08']*100,'hash')
        self.assertEqual(r['proposals'],[])
        self.assertTrue(all(p['status']=='insufficient_evidence' for p in r['paired_comparisons']))

    def test_risk_or_promotion_edit_rejected(self):
        policy=json.loads((self.root/'cloud/research_policy.json').read_text())
        policy['review']['promotion']='enabled'
        with self.assertRaises(ValueError): review({}, {}, policy, [], 'x')

    def test_observed_trade_memory_generates_proposal_only(self):
        policy=json.loads((self.root/'cloud/research_policy.json').read_text())
        run={'complete':True,'trades':[{}]*20,'net_return':0.01}
        orb={f'{d}s_{b}bps_{a}':deepcopy(run) for d in (1,2) for b in (10,25) for a in ('A','B')}
        r=review(orb,{},policy,[f'2026-09-{i:02}' for i in range(1,21)],'hash')
        self.assertEqual(len(r['proposals']),1)
        self.assertFalse(r['proposals'][0]['auto_promote'])
        self.assertFalse(r['risk_rules_changed'])

if __name__=='__main__': unittest.main()
