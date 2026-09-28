import copy
from datetime import datetime, timezone
import gzip
import hashlib
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from cloud.test_research_loop import fixture, save
from cloud.research_runner import execute
from dashboard.remote_snapshot import snapshot
from dashboard.server import Store, handler, verify_host

class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root,cls.archive,cls.output=fixture(Path(cls.tmp.name))
        cls.now=datetime(2026,9,8,20,30,tzinfo=timezone.utc)
        cls.result=execute(cls.root,cls.archive,cls.output,cls.now.timestamp())
        save(cls.archive/'health.json',{'at':cls.now.isoformat(),'records':1,'errors':{},'pending_streams':[]})
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def get(self):return snapshot(self.archive,self.output,self.root,self.now,False)
    def test_real_schema_complete_artifact_and_all_symbols(self):
        s=self.get()
        self.assertEqual(len(s['stocks']),20)
        self.assertEqual(len(s['streams']),14)
        self.assertEqual(len(s['stocks']['LITE']['one']),390)
        self.assertEqual(len(s['stocks']['LITE']['five']),78)
        self.assertEqual(s['session']['close'],'2026-09-08T20:00:00+00:00')
        self.assertTrue(s['verification']['artifact']['latest_results_match'])
        self.assertTrue(s['verification']['artifact']['index_hash_matches'])
        self.assertEqual(len(s['research']['results']['orb']),8)
        self.assertEqual(s['research']['results']['orb_challenger']['status'],'WAITING_FOR_FIRST_PROSPECTIVE_SESSION')
        self.assertEqual(s['agentic_trial']['status'],'NOT_DEPLOYED')
        self.assertEqual(len(s['research']['results']['lite']),4)
        self.assertEqual(s['research']['results']['lite_forward']['capital_arms'],[5000,10000])
        self.assertEqual(len(s['config']['news_context']['symbols']),13)
        self.assertEqual(s['stocks']['LITE']['ticks']['quotes']['last']['bp'],101.2)
    def test_reference_tamper_blocks_read(self):
        p=self.archive/'references/ref.json';old=p.read_bytes()
        try:
            p.write_bytes(old+b' ')
            with self.assertRaisesRegex(ValueError,'Reference hash'):self.get()
        finally:p.write_bytes(old)
    def test_page_tamper_blocks_display(self):
        db=sqlite3.connect(self.archive/'archive.sqlite')
        key=db.execute("SELECT stream,start,page,sha256 FROM pages WHERE stream='bars' LIMIT 1").fetchone()
        try:
            db.execute('UPDATE pages SET sha256=? WHERE stream=? AND start=? AND page=?',('bad',*key[:3]));db.commit()
            with self.assertRaisesRegex(ValueError,'Archive page'):self.get()
        finally:
            db.execute('UPDATE pages SET sha256=? WHERE stream=? AND start=? AND page=?',(key[3],*key[:3]));db.commit();db.close()
    def test_live_missing_data_is_not_manufactured(self):
        db=sqlite3.connect(self.archive/'archive.sqlite')
        row=db.execute("SELECT start,page,payload,sha256 FROM pages WHERE stream='bars' ORDER BY start LIMIT 1").fetchone()
        body=json.loads(gzip.decompress(row[2]));body['bars']['LITE']=body['bars']['LITE'][1:];raw=json.dumps(body).encode()
        try:
            db.execute("UPDATE pages SET payload=?,sha256=? WHERE stream='bars' AND start=? AND page=?",(gzip.compress(raw),hashlib.sha256(raw).hexdigest(),row[0],row[1]));db.commit()
            s=self.get();self.assertEqual(len(s['stocks']['LITE']['one']),389)
            self.assertNotEqual(s['stocks']['LITE']['one'][0]['t'],'2026-09-08T13:30:00Z')
        finally:
            db.execute("UPDATE pages SET payload=?,sha256=? WHERE stream='bars' AND start=? AND page=?",(row[2],row[3],row[0],row[1]));db.commit();db.close()
    def test_stored_ledger_mismatch_is_explicit(self):
        path=self.output/'latest.json';old=path.read_bytes()
        try:
            value=json.loads(old);value['results']['orb']['1s_10bps_A']['complete']=False;save(path,value)
            self.assertFalse(self.get()['verification']['artifact']['latest_results_match'])
        finally:path.write_bytes(old)
    def test_no_remote_writes(self):
        files=[p for base in (self.root,self.archive,self.output) for p in base.rglob('*') if p.is_file() and p.suffix not in ('.sqlite','-wal','-shm')]
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        self.get()
        self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})

class StoreTests(unittest.TestCase):
    def test_failed_refresh_retains_last_data_and_does_not_leak_error(self):
        calls=iter([{'schema_version':1}])
        s=Store(lambda:next(calls));s.refresh();s.refresh()
        self.assertEqual(s.response()['data'],{'schema_version':1})
        self.assertIn('refresh failed',s.response()['connection']['error'])
        s.fetch=lambda:(_ for _ in ()).throw(ValueError('sensitive remote text'))
        s.refresh();self.assertNotIn('sensitive',s.response()['connection']['error'])
    def test_host_mismatch_rejected(self):
        with patch('dashboard.server.subprocess.run') as run:
            run.return_value.stdout='256 SHA256:wrong host (ED25519)'
            with self.assertRaisesRegex(ValueError,'Untrusted'):verify_host(Path('/tmp/test'))

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store=Store(lambda:{'schema_version':1});cls.store.refresh()
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),handler(cls.store))
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close()
    def request(self,path,method='GET',headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port)
        conn.request(method,path,headers=headers or {});response=conn.getresponse();body=response.read();conn.close();return response,body
    def test_only_allowlisted_files_served(self):
        for path in ('/.env','/server.py','/state/known_hosts','/../config/paper_v1.json','/research-notes/../../.env'):
            self.assertEqual(self.request(path)[0].status,404)
        self.assertEqual(self.request('/api/snapshot')[0].status,200)
        self.assertEqual(self.request('/research-notes/operations')[0].status,200)
    def test_mutation_and_cross_origin_denied(self):
        self.assertEqual(self.request('/api/snapshot','POST')[0].status,501)
        self.assertEqual(self.request('/api/snapshot',headers={'Host':'attacker.invalid'})[0].status,403)
        self.assertEqual(self.request('/api/snapshot',headers={'Origin':'https://attacker.invalid'})[0].status,403)
        self.assertEqual(self.request('/api/snapshot',headers={'Sec-Fetch-Site':'cross-site'})[0].status,403)
    def test_private_response_headers(self):
        response,_=self.request('/')
        self.assertEqual(response.getheader('Cache-Control'),'no-store')
        self.assertIn("frame-ancestors 'none'",response.getheader('Content-Security-Policy'))
        self.assertIsNone(response.getheader('Access-Control-Allow-Origin'))

if __name__=='__main__':unittest.main()
