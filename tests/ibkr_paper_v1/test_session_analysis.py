from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cloud.ibkr_paper_v1.operations import connect,report_body,reporter_cycle
from cloud.ibkr_paper_v1.session_analysis import analyze,cycle,load_result,save_result,revision
from cloud.ibkr_paper_v1.signal_adapter import NS,MINUTE,session_start


class SessionAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.folder=Path(self.tmp.name)
        self.db=connect(self.folder/'state.sqlite')
        self.rows=[{'date':d,'open':'09:30','close':'16:00'} for d in ('2026-09-18','2026-09-21')]
        self.now=datetime(2026,9,21,20,15,tzinfo=timezone.utc)
        raw=json.dumps({'calendar':self.rows,'fetched_at':self.now.isoformat()}).encode()
        (self.folder/'calendar.json').write_bytes(raw)
        (self.folder/'latest.json').write_text(json.dumps({'file':'calendar.json','sha256':hashlib.sha256(raw).hexdigest()}))

    def tearDown(self):
        self.db.close();self.tmp.cleanup()

    def insert_session(self,day,second=False):
        start=session_start(day)
        def rows():
            for second_index in range(390*60):
                ns=start+second_index*NS
                common={'contract':'MNQZ6','data_type':1,'broker_time_seconds':ns//NS}
                quote=dict(common,bid_ticks=40000,ask_ticks=40001,bid_size='1',ask_size='1')
                yield (ns,'quote',json.dumps(quote))
                minute,s=divmod(second_index,60)
                prices=[40000]
                if not second and minute==5:prices=[39950,40050,40000]
                if second and minute==14:prices=[39951,39940]
                if second and minute==15:prices=[39941,39952]
                if second and minute==16:prices=[39952]
                if 1<=s<=len(prices):
                    payload=dict(common,price_ticks=prices[s-1],size='100' if second and minute in (14,15) else '1000',
                                 tick_type=2,unreported=False,past_limit=False,special_conditions='',exchange='')
                    yield (ns,'trade',json.dumps(payload))
        self.db.executemany('INSERT INTO events(received_ns,kind,payload) VALUES(?,?,?)',rows())
        self.db.commit()

    def test_full_two_session_fixture_evaluates_signal_without_claiming_profit(self):
        self.insert_session('2026-09-18')
        self.insert_session('2026-09-21',True)
        result=analyze(self.db,self.rows,'2026-09-21',self.now)
        self.assertEqual(result['status'],'CANDIDATE_SIGNALS_EVALUATED')
        self.assertEqual(result['previous_session_date'],'2026-09-18')
        self.assertEqual(result['candidate_signal_count'],1)
        self.assertFalse(result['strategy_evidence_approved'])
        self.assertFalse(result['orders_sent'])
        self.assertIsNone(result['net_pnl_cents'])

    def test_missing_warmup_is_unknown_not_zero_signals(self):
        self.insert_session('2026-09-21',True)
        result=analyze(self.db,self.rows,'2026-09-21',self.now)
        self.assertEqual(result['status'],'WARMUP_BLOCKED')
        self.assertIsNone(result['candidate_signal_count'])
        self.assertEqual(result['complete_minute_bars'],390)

    def test_incomplete_current_session_cannot_generate_a_candidate(self):
        result=analyze(self.db,self.rows,'2026-09-21',self.now)
        self.assertEqual(result['status'],'DATA_BLOCKED')
        self.assertIsNone(result['candidate_signals'])

    def test_cycle_caches_verified_artifact_and_latches_post_capture_change(self):
        first=cycle(self.folder,self.folder,self.now)
        self.assertEqual(first['status'],'DATA_BLOCKED')
        cached=cycle(self.folder,self.folder,self.now)
        self.assertTrue(cached['cached'])
        ns=session_start('2026-09-21')
        self.db.execute('INSERT INTO events(received_ns,kind,payload) VALUES(?,?,?)',(ns,'invalid_trade','{}'))
        self.db.commit()
        cycle(self.folder,self.folder,self.now)
        result=load_result(self.folder,'2026-09-21')
        self.assertEqual(result['reason'],'SESSION_CHANGED_AFTER_FIRST_ANALYSIS')
        self.assertTrue(result['capture_mutation_detected'])
        with patch('cloud.ibkr_paper_v1.session_analysis.revision',return_value='changed-code'):
            cycle(self.folder,self.folder,self.now)
        self.assertEqual(load_result(self.folder,'2026-09-21')['reason'],'SESSION_CHANGED_AFTER_FIRST_ANALYSIS')

    def test_artifact_tampering_is_detected(self):
        cycle(self.folder,self.folder,self.now)
        pointer=json.loads((self.folder/'analysis/2026-09-21.json').read_text())
        (self.folder/'analysis'/pointer['file']).write_text('{}')
        with self.assertRaises(ValueError):load_result(self.folder,'2026-09-21')

    def test_report_distinguishes_unknown_from_evaluated_zero(self):
        blocked={'status':'WARMUP_BLOCKED','candidate_signal_count':None,'reason':'MISSING_PRIOR_SESSION'}
        body=report_body(self.db,'post','2026-09-21',self.now,analysis=blocked)
        self.assertIn('UNKNOWN',body)
        evaluated={'status':'CANDIDATE_SIGNALS_EVALUATED','candidate_signal_count':0}
        body=report_body(self.db,'post','2026-09-21',self.now,analysis=evaluated)
        self.assertIn('unapproved receipt-time study: 0',body)
        self.assertIn('Broker orders: DISABLED',body)

    def test_reporter_reads_session_result_without_sending(self):
        cycle(self.folder,self.folder,self.now)
        reporter_cycle(self.folder,self.folder,self.folder/'no-credentials.json',self.now)
        body=self.db.execute("SELECT body FROM outbox WHERE id='2026-09-21:post'").fetchone()[0]
        self.assertIn('Session analysis: DATA_BLOCKED',body)
        self.assertIn('Candidate signal count: UNKNOWN',body)
