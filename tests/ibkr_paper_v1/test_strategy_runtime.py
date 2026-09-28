from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from cloud.ibkr_paper_v1.strategy_runtime import Feed,qualification,pause,ingest
from cloud.ibkr_paper_v1.execution import Ledger,SYMBOL,NS,plan
from cloud.ibkr_paper_v1.signal_adapter import session_start


class StrategyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.db=sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE events(id INTEGER PRIMARY KEY,received_ns,kind,payload)')
        self.rows=[{'date':'2026-09-21','open':'09:30','close':'16:00'},
                   {'date':'2026-09-22','open':'09:30','close':'16:00'}]
        self.now=datetime(2026,9,22,14,tzinfo=timezone.utc)
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def ready_feed(self):
        bars={i:{'high':10005,'low':9995} for i in range(390)}
        with patch('cloud.ibkr_paper_v1.strategy_runtime.audit_session',return_value={'status':'OBSERVATION_CHECKS_PASSED'}), \
             patch('cloud.ibkr_paper_v1.strategy_runtime.bars_from_tape',return_value=(SimpleNamespace(bars=bars),{'test':True})):
            return Feed(self.db,self.rows,'2026-09-22',self.now)
    def quote(self,at):
        raw=dict(contract=SYMBOL,data_type=1,broker_time_seconds=at//NS,
                 bid_ticks=10000,ask_ticks=10001,bid_size='1',ask_size='1')
        self.db.execute('INSERT INTO events(received_ns,kind,payload) VALUES(?,?,?)',(at,'quote',json.dumps(raw)))
        self.db.commit()
    def test_previous_partial_session_cannot_be_skipped(self):
        with self.assertRaisesRegex(ValueError,'PREVIOUS_SESSION_INCOMPLETE'):
            Feed(self.db,self.rows,'2026-09-22',self.now)
    def test_missing_opening_or_gap_disables_the_day(self):
        f=self.ready_feed();start=session_start('2026-09-22')
        self.quote(start+2*NS)
        with self.assertRaisesRegex(ValueError,'OPENING_QUOTES_MISSING'):f.poll()
        self.db.execute('DELETE FROM events');self.db.commit();f=self.ready_feed()
        self.quote(start+NS//10);f.poll()
        self.quote(start+3*NS)
        with self.assertRaisesRegex(ValueError,'QUOTE_GAP_OVER_ONE_SECOND'):f.poll()
    def test_feed_restart_is_not_treated_as_clean_prefix(self):
        f=self.ready_feed();start=session_start('2026-09-22')
        self.db.execute('INSERT INTO events(received_ns,kind,payload) VALUES(?,?,?)',(start,'connection','{}'))
        self.db.commit()
        with self.assertRaisesRegex(ValueError,'SESSION_FEED_INTERRUPTION'):f.poll()
    def test_risk_pause_survives_restart(self):
        p=self.root/'ledger.sqlite';l=Ledger(p);pause(l,'TEST_DISCONNECT');l.close()
        again=Ledger(p)
        self.assertEqual(again.db.execute('SELECT paused FROM portfolio').fetchone()[0],'TEST_DISCONNECT')
        again.close()
    def test_qualification_cannot_enable_live_or_skip_fill_evidence(self):
        p=self.root/'qualification.json'
        q=dict(paper_account='DUT109401',contract=SYMBOL,enable_paper=True,
               fee_reserve_cents=400,cancel_test_passed=True,filled_round_trip_passed=False,review_by='2099-01-01')
        p.write_text(json.dumps(q))
        with self.assertRaises(ValueError):qualification(p)
        q.update(filled_round_trip_passed=True,paper_account='U123');p.write_text(json.dumps(q))
        with self.assertRaises(ValueError):qualification(p)

    def test_broker_callbacks_reconcile_through_real_durable_strategy_ledger(self):
        l=Ledger(self.root/'flow.sqlite');at=int(self.now.timestamp())*NS
        signal=dict(id='fixture',contract=SYMBOL,direction=1,signal_ns=at,
                    stop_ticks=39990,target_ticks=40060)
        quote=dict(received_ns=at+NS,contract=SYMBOL,data_type=1,
                   bid_ticks=40000,ask_ticks=40001,bid_size=1,ask_size=1)
        value=plan(signal,quote,at+NS,400,'a'*64)
        l.reserve(value,100,at+NS)
        for oid in (100,101,102):l.before_send(oid)
        with l.atomic():l.db.execute('INSERT INTO dispatch VALUES(?,?,?,?)',(103,'fixture','time_exit','UNSENT'))
        l.before_send(103)
        p=SimpleNamespace(statuses={},executions={},fees={})
        for oid in (100,101,102,103):
            filled=1 if oid in (100,103) else 0
            p.statuses[oid]=dict(status='Filled' if filled else 'Cancelled',filled=str(filled),
                remaining=str(1-filled),perm_id=oid+1000,received_ns=at+2*NS)
        for eid,oid,side,price in [('entry',100,'BOT','10000.25'),('exit',103,'SLD','10001')]:
            p.executions[eid]=dict(order_id=oid,side=side,price=price)
            p.fees[eid]=dict(amount='0.61',currency='USD')
        ingest(l,p,100,value);ingest(l,p,100,value)
        self.assertTrue(l.reconcile_flat('fixture',0,[],True,{}))
        self.assertEqual(l.db.execute('SELECT cash_cents FROM portfolio').fetchone()[0],500028)
        self.assertFalse(l.reconcile_flat('fixture',0,[],True,{}))
        l.close()
