from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from cloud import collector as c
from cloud.forward_research import capital_replay, context_news, available_context
from cloud.research_archive import Archive, DataGap, nanos
from cloud.research_runner import execute
from cloud.readiness import assess
from cloud.test_research_loop import fixture, save, REPO
from cloud.test_collector import Fake
from research.lite_reversal_v1.test_experiment import bars, config

POLICY=json.loads((REPO/'cloud/research_policy.json').read_text())
CONTEXT=json.loads((REPO/'cloud/news_context_v1.json').read_text())


def second_day(archive):
    """Extend the synthetic archive to the actual prospective date, never the freeze."""
    db=sqlite3.connect(archive/'archive.sqlite')
    for row in list(db.execute('SELECT stream,start,end,page,received_at,sha256,records,payload FROM pages')):
        stream,start,end,page,receipt,_,count,payload=row
        raw=gzip.decompress(payload).replace(b'2026-09-08',b'2026-09-09')
        body=json.loads(raw)
        if stream=='bars5':
            for b in body['bars']['LITE']:
                idx=(c.stamp(b['t'])-c.stamp('2026-09-09T13:30:00Z'))//300
                desired=bars('2026-09-09')[idx]
                b.update({k:getattr(desired,k) for k in ('o','h','l','c','v','vw')})
            raw=json.dumps(body).encode()
        db.execute('INSERT INTO pages VALUES (?,?,?,?,?,?,?,?)',
                   (stream,start+86400,end+86400,page,receipt.replace('2026-09-08','2026-09-09'),
                    hashlib.sha256(raw).hexdigest(),count,gzip.compress(raw)))
    # Complete context-news coverage from midnight, including premarket.
    for window in range(c.stamp('2026-09-09T00:00:00Z'),c.stamp('2026-09-09T13:30:00Z'),300):
        raw=json.dumps({'news':[], 'next_page_token':None}).encode()
        db.execute('INSERT INTO pages VALUES (?,?,?,?,?,?,?,?)',('sector_news',window,window+300,0,
                   c.iso(window+1500),hashlib.sha256(raw).hexdigest(),0,gzip.compress(raw)))
    db.execute('UPDATE checkpoints SET end=end+86400')
    db.execute("UPDATE health SET checked_at='2026-09-09T20:29:00Z'")
    db.commit();db.close()
    ref=json.loads((archive/'references/ref.json').read_text())
    ref['fetched_at']='2026-09-09T06:00:00Z'
    digest=save(archive/'references/ref.json',ref)
    save(archive/'references/latest.json',{'file':'ref.json','sha256':digest})


class CapitalTests(unittest.TestCase):
    def run_arm(self,included,excluded,days):
        return capital_replay(config(),included,excluded,days,POLICY['lite_forward'])

    def test_missing_first_forward_day_blocks_without_zero_results(self):
        r=self.run_arm({}, {'2026-09-09':'incomplete'},['2026-09-08','2026-09-09'])
        self.assertEqual(r['status'],'BLOCKED_INCOMPLETE_FORWARD_DATA')
        self.assertFalse(r['results'])

    def test_missing_parent_day_does_not_poison_new_capital_portfolio(self):
        r=self.run_arm({'2026-09-09':bars('2026-09-09')},{'2026-09-08':'incomplete'},['2026-09-08','2026-09-09'])
        self.assertEqual(len(r['results']),8)
        self.assertEqual(r['days'],['2026-09-09'])

    def test_two_capitals_trade_with_unchanged_signals_and_risk_percent(self):
        r=self.run_arm({'2026-09-09':bars('2026-09-09')},{},['2026-09-09'])
        a=r['results']['5000_dip_10bps'];b=r['results']['10000_dip_10bps']
        self.assertGreater(a['summary']['trades'],0)
        self.assertEqual(a['trades'][0]['entry_time'],b['trades'][0]['entry_time'])
        self.assertGreater(b['trades'][0]['quantity'],a['trades'][0]['quantity'])
        for value in (a,b):
            self.assertEqual(value['validation']['status'],'PASS')
            self.assertLessEqual(value['trades'][0]['planned_risk'],value['summary']['initial_cash']*config().risk_fraction+1e-8)

    def test_frozen_date_mode_and_capital_edits_rejected(self):
        for change in ({'evaluation_start':'2026-09-08'},{'mode':'fractional_diagnostic'},
                       {'capital_arms':[5000]},{'broker_ready':True},{'promotion':'enabled'}):
            with self.subTest(change=change),self.assertRaises(DataGap):
                capital_replay(config(),{}, {},[],{**POLICY['lite_forward'],**change})


class NewsTests(unittest.TestCase):
    def test_nonempty_sector_news_is_committed_without_price_fields(self):
        db=c.database(':memory:')
        body={'news':[{'id':9,'symbols':['GLW','VZ'],'created_at':'2026-09-09T10:01:00Z',
                       'updated_at':'2026-09-09T10:01:00Z'}],'next_page_token':None}
        start=c.stamp('2026-09-09T10:00:00Z')
        try:
            self.assertEqual(c.collect_window(db,Fake([body]),'sector_news',start,start+300),1)
            self.assertEqual(db.execute('SELECT end FROM checkpoints').fetchone()[0],start+300)
        finally:db.close()

    def test_premarket_receipt_cutoff_and_same_day_isolation(self):
        class Source:
            def news(self,start,end,stream):
                self.query=(start,end,stream)
                return [dict(article_id=i,updated_at='2026-09-09T11:00:00Z',created_at='2026-09-09T11:00:00Z',
                             symbols=['GLW'],first_received_at=receipt) for i,receipt in
                        [(1,'2026-09-09T11:25:00Z'),(2,'2026-09-09T14:26:00Z')]]
        source=Source();sessions={'2026-09-09':(datetime.fromisoformat('2026-09-09T09:30:00-04:00'),datetime.fromisoformat('2026-09-09T16:00:00-04:00'))}
        data,status=context_news(source,CONTEXT,sessions,['2026-09-09'])
        self.assertEqual(source.query[0],nanos('2026-09-09T00:00:00Z'))
        f={'day':'2026-09-09','symbol':'LITE','pattern':{'time':'2026-09-09T10:05:00-04:00'}}
        self.assertEqual(available_context(data,status,f,CONTEXT)['context_items_observed_before_signal'],1)
        f['day']='2026-09-08'
        self.assertIsNone(available_context(data,status,f,CONTEXT)['context_items_observed_before_signal'])

    def test_incomplete_context_never_becomes_neutral_zero(self):
        class Source:
            def news(self,*args): raise DataGap('missing')
        sessions={'2026-09-09':(None,datetime.fromisoformat('2026-09-09T16:00:00-04:00'))}
        data,status=context_news(Source(),CONTEXT,sessions,['2026-09-09'])
        f={'day':'2026-09-09','symbol':'LITE','pattern':{'time':'2026-09-09T10:05:00-04:00'}}
        result=available_context(data,status,f,CONTEXT)
        self.assertIsNone(result['context_items_observed_before_signal'])
        self.assertTrue(result['context_status'].startswith('unknown'))


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root,self.archive,self.output=fixture(Path(self.tmp.name))
        second_day(self.archive)
        self.asof=c.stamp('2026-09-09T20:30:00Z')
    def tearDown(self):self.tmp.cleanup()

    def test_actual_september_nine_pipeline_trades_and_repeats_identically(self):
        with redirect_stdout(io.StringIO()):
            result=execute(self.root,self.archive,self.output,self.asof)
            again=execute(self.root,self.archive,self.output,self.asof+30)
        self.assertEqual(result['status'],'REPLAY_COMPLETE_RESEARCH_ONLY',result)
        forward=result['results']['lite_forward']
        self.assertEqual(len(forward['results']),8)
        self.assertEqual(forward['days'],['2026-09-09'])
        self.assertGreater(forward['results']['5000_dip_10bps']['summary']['trades'],0)
        self.assertEqual(result['run_id'],again['run_id'])
        self.assertEqual(result['results'],again['results'])
        self.assertEqual(result['results']['news_context_status'],'metadata_only_not_used_for_selection')
        self.assertEqual(result['session_readiness']['status'],'READY_FOR_DELAYED_RESEARCH_SESSION')
        challenger=result['results']['orb_challenger']
        self.assertEqual(challenger['status'],'WAITING_FOR_FIRST_PROSPECTIVE_SESSION')
        self.assertEqual(challenger['prospective_start'],'2026-09-16')
        self.assertEqual(challenger['days'],[])
        self.assertFalse(challenger['scenarios'])
        self.assertFalse(challenger['orders_enabled'])

    def test_readiness_rejects_future_and_stale_health_and_low_disk(self):
        with sqlite3.connect(self.archive/'archive.sqlite') as db:
            db.execute("UPDATE health SET checked_at='2026-09-09T20:35:00Z' WHERE stream='bars'")
        self.assertEqual(assess(self.archive,POLICY,self.asof)['status'],'BLOCKED')
        with sqlite3.connect(self.archive/'archive.sqlite') as db:
            db.execute("UPDATE health SET checked_at='2026-09-09T19:00:00Z' WHERE stream='bars'")
        self.assertEqual(assess(self.archive,POLICY,self.asof)['status'],'BLOCKED')
        with patch('cloud.readiness.shutil.disk_usage') as usage:
            usage.return_value.free=1000
            self.assertIn('disk_reserve_breached',assess(self.archive,POLICY,self.asof)['reasons'])

    def test_future_checkpoint_is_not_caught_up(self):
        with sqlite3.connect(self.archive/'archive.sqlite') as db:
            db.execute('UPDATE checkpoints SET end=end+86400')
        result=assess(self.archive,POLICY,self.asof)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertTrue(any(r.startswith('invalid_checkpoint:') for r in result['reasons']))

    def test_malformed_checkpoint_blocks_without_crashing(self):
        with sqlite3.connect(self.archive/'archive.sqlite') as db:
            db.execute("UPDATE checkpoints SET end='invalid' WHERE stream='bars'")
        result=assess(self.archive,POLICY,self.asof)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('invalid_checkpoint:bars',result['reasons'])


if __name__=='__main__':unittest.main()
