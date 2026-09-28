import hashlib
import json
from pathlib import Path
import tempfile
import threading
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from ibapi.message import OUT
from ibapi.common import PROTOBUF_MSG_ID
from cloud.ibkr_paper_v1.collector import Collector, contract_ok, ticks
from cloud.ibkr_paper_v1.operations import (connect, calendar_rows, due_reports,
    enqueue, deliver, deliver_https, read_health, report_body, write_health, reporter_cycle,execution_status,
    connectivity_watch)
from cloud.ibkr_paper_v1.session_audit import audit_session


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.folder=Path(self.tmp.name)
        self.db=connect(self.folder/'state.sqlite')
        self.now=datetime(2026,9,21,13,15,tzinfo=timezone.utc)
        self.rows=[{'date':'2026-09-18','open':'09:30','close':'16:00'},
                   {'date':'2026-09-21','open':'09:30','close':'16:00'},
                   {'date':'2026-11-27','open':'09:30','close':'13:00'},
                   {'date':'2026-12-01','open':'09:30','close':'16:00'}]

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_schedule_uses_dst_holidays_and_early_close(self):
        self.assertEqual(due_reports(self.rows,self.now)[0][0],'pre')
        self.assertEqual(due_reports(self.rows,self.now+timedelta(minutes=15)),[])
        self.assertEqual(due_reports(self.rows,datetime(2026,9,21,20,15,tzinfo=timezone.utc))[0][0],'post')
        self.assertEqual(due_reports(self.rows,datetime(2026,9,20,13,15,tzinfo=timezone.utc)),[])
        self.assertEqual(due_reports(self.rows,datetime(2026,11,27,18,15,tzinfo=timezone.utc))[0][0],'post')
        self.assertEqual(due_reports(self.rows,datetime(2026,12,1,14,15,tzinfo=timezone.utc))[0][0],'pre')

    def test_calendar_hash_and_staleness_fail_closed(self):
        raw=json.dumps({'fetched_at':self.now.isoformat(),'calendar':self.rows}).encode()
        (self.folder/'calendar.json').write_bytes(raw)
        (self.folder/'latest.json').write_text(json.dumps({'file':'calendar.json','sha256':hashlib.sha256(raw).hexdigest()}))
        self.assertEqual(calendar_rows(self.folder,self.now),self.rows)
        with self.assertRaises(ValueError):
            calendar_rows(self.folder,self.now+timedelta(days=8))
        (self.folder/'calendar.json').write_text('{}')
        with self.assertRaises(ValueError):
            calendar_rows(self.folder,self.now)

    def test_unknown_and_stale_health_never_claims_running(self):
        self.assertEqual(read_health(self.db,self.now)['status'],'NO_COLLECTOR_HEARTBEAT')
        with patch('cloud.ibkr_paper_v1.operations.utcnow',return_value=self.now):
            write_health(self.db,{'status':'COLLECTING_REALTIME'})
        self.assertEqual(read_health(self.db,self.now+timedelta(seconds=91))['status'],'STALE_COLLECTOR_HEARTBEAT')
        body=report_body(self.db,'pre','2026-09-21',self.now)
        self.assertIn('NOT YET MEASURED',body)
        self.assertIn('Broker orders: DISABLED',body)

    def test_paper_supervisor_status_is_separate_from_collector_and_staleness_is_visible(self):
        (self.folder/'execution-health.json').write_text(json.dumps(dict(status='DATA_OR_RISK_BLOCKED',
            updated_at=self.now.isoformat(),paper_only=True,live_trading_authorized=False,
            paper_armed=True,orders_eligible=False,reason='PREVIOUS_SESSION_INCOMPLETE')))
        h=execution_status(self.folder,self.now)
        self.assertEqual(h['status'],'DATA_OR_RISK_BLOCKED')
        body=report_body(self.db,'pre','2026-09-21',self.now,execution=h)
        self.assertIn('Broker orders: PAPER ONLY',body)
        self.assertNotIn('Broker orders: DISABLED',body)
        self.assertEqual(execution_status(self.folder,self.now+timedelta(seconds=91))['status'],
                         'STALE_EXECUTION_SUPERVISOR')

    def test_enqueue_is_durable_idempotent(self):
        for _ in range(2):
            enqueue(self.db,'2026-09-21:pre','subject','body',self.now)
        second=connect(self.folder/'state.sqlite')
        self.assertEqual(second.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],1)
        second.close()

    def test_overnight_outage_survives_reporter_restart_and_recovers_once(self):
        now=datetime(2026,9,22,5,0,tzinfo=timezone.utc)
        bad={'status':'GATEWAY_LOGIN_OR_API_REQUIRED'}
        connectivity_watch(self.db,bad,now)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],0)
        other=connect(self.folder/'state.sqlite')
        try:
            connectivity_watch(other,bad,now+timedelta(minutes=3))
            connectivity_watch(other,bad,now+timedelta(minutes=4))
            self.assertEqual(other.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],1)
            other.execute("UPDATE outbox SET state='accepted_by_email_api'");other.commit()
            healthy={'status':'OUTSIDE_RESEARCH_SESSION'}
            connectivity_watch(other,healthy,now+timedelta(minutes=5))
            self.assertEqual(other.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],1)
            connectivity_watch(other,healthy,now+timedelta(minutes=7))
            connectivity_watch(other,healthy,now+timedelta(minutes=8))
            self.assertEqual(other.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],2)
            body=other.execute("SELECT body FROM outbox WHERE subject LIKE '%recovered'").fetchone()[0]
            self.assertIn('connection recovery only',body)
            self.assertEqual(other.execute('SELECT COUNT(*) FROM connectivity_watch').fetchone()[0],0)
        finally:other.close()

    def test_brief_restart_does_not_send_overnight_alert(self):
        now=datetime(2026,9,22,5,0,tzinfo=timezone.utc)
        connectivity_watch(self.db,{'status':'CONNECTING'},now)
        for minute in (1,3):
            connectivity_watch(self.db,{'status':'OUTSIDE_RESEARCH_SESSION'},now+timedelta(minutes=minute))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],0)

    def test_opening_failure_alerts_immediately_and_unsent_notice_expires_on_recovery(self):
        start=self.now+timedelta(minutes=15)
        session=(start,start+timedelta(hours=6,minutes=30))
        connectivity_watch(self.db,{'status':'OUTSIDE_RESEARCH_SESSION'},start,session)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],1)
        for minute in (1,3):
            connectivity_watch(self.db,{'status':'COLLECTING_REALTIME'},start+timedelta(minutes=minute),session)
        self.assertEqual(self.db.execute('SELECT state FROM outbox').fetchone()[0],'expired')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],1)

    def test_recovery_must_be_continuous_and_recurrence_gets_new_incident(self):
        bad={'status':'STALE_COLLECTOR_HEARTBEAT'}
        good={'status':'OUTSIDE_RESEARCH_SESSION'}
        now=datetime(2026,9,22,5,0,tzinfo=timezone.utc)
        for minute,h in ((0,bad),(3,bad),(4,good),(5,bad),(6,good),(7,good)):
            connectivity_watch(self.db,h,now+timedelta(minutes=minute))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM connectivity_watch').fetchone()[0],1)
        connectivity_watch(self.db,good,now+timedelta(minutes=8))
        for minute in (9,12):connectivity_watch(self.db,bad,now+timedelta(minutes=minute))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],2)

    def test_successful_email_not_sent_twice(self):
        enqueue(self.db,'test','subject','body',self.now)
        sent=[]
        class SMTP:
            def __init__(self,*args,**kwargs): pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def login(self,*args):pass
            def send_message(self,msg,**kwargs):sent.append(kwargs);return {}
        creds={'user':'pranavm1104@gmail.com','password':'test-only'}
        self.assertTrue(deliver(self.db,'test',creds,self.now,SMTP))
        self.assertFalse(deliver(self.db,'test',creds,self.now,SMTP))
        self.assertEqual(len(sent),1)
        self.assertEqual(sent[0]['to_addrs'],['pranavm1104@gmail.com'])

    def test_ambiguous_delivery_is_not_retried(self):
        enqueue(self.db,'test','subject','body',self.now)
        class SMTP:
            def __init__(self,*args,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def login(self,*args):pass
            def send_message(self,*args,**kwargs):raise TimeoutError()
        creds={'user':'pranavm1104@gmail.com','password':'test-only'}
        self.assertFalse(deliver(self.db,'test',creds,self.now,SMTP))
        self.assertEqual(self.db.execute('SELECT state FROM outbox').fetchone()[0],'delivery_unknown')
        self.assertFalse(deliver(self.db,'test',creds,self.now,SMTP))

    def test_collector_blocks_order_protocols(self):
        p=Collector(self.folder/'state.sqlite','DU123',threading.Event())
        try:
            for msg in (OUT.PLACE_ORDER,OUT.CANCEL_ORDER,OUT.REQ_GLOBAL_CANCEL):
                with self.assertRaises(RuntimeError):p.sendMsg(msg,'')
                with self.assertRaises(RuntimeError):p.sendMsgProtoBuf(msg+PROTOBUF_MSG_ID,b'')
        finally:p.db.close()

    def test_tick_validation(self):
        self.assertEqual(ticks(100.25),401)
        for bad in (float('nan'),float('inf'),0,-1,100.1):
            with self.assertRaises(ValueError):ticks(bad)

    def test_callbacks_gate_exact_session_boundaries(self):
        p=Collector(self.folder/'state.sqlite','DU123',threading.Event())
        try:
            p.accept_events=True
            p.capture_window=(100,200)
            for ns,expected in ((99,False),(100,True),(199,True),(200,False)):
                with patch('cloud.ibkr_paper_v1.collector.time.time_ns',return_value=ns):
                    self.assertEqual(p.in_capture_window(),expected)
        finally:p.db.close()

    def test_partial_session_never_counts_as_complete(self):
        start=self.now+timedelta(minutes=15)
        end=start+timedelta(minutes=390)
        result=audit_session(self.db,'2026-09-21',start,end,start+timedelta(hours=1))
        self.assertIn('OPENING_QUOTES_MISSING',result['issues'])
        self.assertIn('SESSION_NOT_FINISHED',result['issues'])
        self.assertFalse(result['strategy_evidence_approved'])

    def test_full_synthetic_observations_and_missing_quote_detection(self):
        start=self.now+timedelta(minutes=15)
        end=start+timedelta(minutes=390)
        lo=int(start.timestamp())*1_000_000_000
        events=[]
        for second in range(390*60):
            ns=lo+second*1_000_000_000+500_000_000
            payload={'contract':'MNQZ6','data_type':1,'broker_time_seconds':ns//1_000_000_000}
            events.append((ns,'quote',json.dumps(payload)))
            if second%60==0:
                events.append((ns,'trade',json.dumps(dict(payload,tick_type=2,unreported=False,past_limit=False,special_conditions=''))))
        self.db.executemany('INSERT INTO events(received_ns,kind,payload) VALUES(?,?,?)',events)
        self.db.commit()
        result=audit_session(self.db,'2026-09-21',start,end,end)
        self.assertEqual(result['status'],'OBSERVATION_CHECKS_PASSED')
        self.assertFalse(result['strategy_evidence_approved'])
        self.db.execute("DELETE FROM events WHERE kind='quote' AND received_ns=?",(lo+120_500_000_000,))
        result=audit_session(self.db,'2026-09-21',start,end,end)
        self.assertIn('QUOTE_GAP_OVER_ONE_SECOND',result['issues'])

    def test_heartbeat_commits_pending_ticks_without_second_writer_deadlock(self):
        p=Collector(self.folder/'state.sqlite','DU123',threading.Event())
        other=sqlite3.connect(self.folder/'state.sqlite',timeout=0.01)
        try:
            p.event('test_tick',{'fixture':True})
            # Reproduce why a separate health connection cannot write this batch.
            with self.assertRaises(sqlite3.OperationalError):
                write_health(other,{'status':'TEST'})
            p.checkpoint({'status':'TEST_HEARTBEAT'})
            self.assertEqual(read_health(other,datetime.now(timezone.utc))['status'],'TEST_HEARTBEAT')
            self.assertEqual(other.execute("SELECT COUNT(*) FROM events WHERE kind='test_tick'").fetchone()[0],1)
        finally:
            other.close()
            p.db.close()

    def test_https_retries_identical_key_and_payload(self):
        enqueue(self.db,'2026-09-21:post','subject','body',self.now)
        requests=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return b'{"id":"test-receipt"}'
        class Opener:
            def open(self,req,**kwargs):
                requests.append(req)
                if len(requests)==1:raise TimeoutError()
                return Response()
        credentials={'provider':'resend','api_key':'re_test_only'}
        self.assertFalse(deliver_https(self.db,'2026-09-21:post',credentials,self.now,Opener()))
        self.assertTrue(deliver_https(self.db,'2026-09-21:post',credentials,self.now,Opener()))
        self.assertEqual(requests[0].data,requests[1].data)
        self.assertEqual(requests[0].headers['Idempotency-key'],requests[1].headers['Idempotency-key'])
        self.assertEqual(requests[0].full_url,'https://api.resend.com/emails')
        self.assertEqual(requests[0].get_header('User-agent'),'mnq-paper-research/1.0')
        self.assertEqual(json.loads(requests[0].data)['to'],['pranavm1104@gmail.com'])

    def test_missed_pre_report_expires_after_open(self):
        raw=json.dumps({'fetched_at':self.now.isoformat(),'calendar':self.rows}).encode()
        (self.folder/'calendar.json').write_bytes(raw)
        (self.folder/'latest.json').write_text(json.dumps({'file':'calendar.json','sha256':hashlib.sha256(raw).hexdigest()}))
        (self.folder/'mail.json').write_text(json.dumps({'provider':'resend','api_key':'re_test_only'}))
        enqueue(self.db,'2026-09-21:pre','subject','body',self.now)
        with patch('cloud.ibkr_paper_v1.operations.deliver_https',return_value=False):
            reporter_cycle(self.folder,self.folder,self.folder/'mail.json',self.now+timedelta(minutes=30))
        self.assertEqual(self.db.execute("SELECT state FROM outbox WHERE id='2026-09-21:pre'").fetchone()[0],'expired')

if __name__=='__main__':unittest.main()
