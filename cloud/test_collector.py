import gzip
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
try:
    from cloud import collector as c
except ModuleNotFoundError:
    import collector as c

class Fake:
    def __init__(self, replies):
        self.replies = iter(replies)
    def get(self, *args):
        x = next(self.replies)
        if isinstance(x, Exception):
            raise x
        return json.dumps(x).encode()

class Tests(unittest.TestCase):
    def setUp(self):
        self.db = c.database(':memory:')
    def tearDown(self):
        self.db.close()
    def test_scope(self):
        self.assertEqual(len(c.SYMBOLS),20)
        self.assertEqual(len(c.STREAMS),14)
        for s in ('orders', '../orders', 'AAPL:quotes'):
            with self.assertRaises(ValueError): c.request_spec(s,0,300)
    def test_endpoint(self):
        path,q = c.request_spec('bars',0,300)
        self.assertEqual(path,'/v2/stocks/bars')
        self.assertEqual(q['feed'],'sip')
        self.assertEqual(q['adjustment'],'raw')
    def test_prospective_context_news_scope(self):
        path,q=c.request_spec('sector_news',0,300)
        self.assertEqual(path,'/v1beta1/news')
        self.assertEqual(q['symbols'],','.join(c.CONTEXT_SYMBOLS))
        self.assertNotIn('LITE',c.CONTEXT_SYMBOLS)
        self.assertFalse(c.NEWS_CONTEXT['selection_or_execution_use'])
        db=c.database(':memory:')
        try:
            with patch.object(c,'space_ok',return_value=True):
                c.cycle(db,Fake([]),0,c.stamp(c.NEWS_CONTEXT['collection_start'])-1,'.')
            self.assertIsNone(db.execute("SELECT end FROM checkpoints WHERE stream='sector_news'").fetchone())
        finally: db.close()
    def test_commit_and_compression(self):
        f = Fake([{'symbol':'LITE','quotes':[{'t':'2026-09-08T00:00:00Z'}], 'next_page_token':'a'},
                  {'symbol':'LITE','quotes':[], 'next_page_token':None}])
        self.assertEqual(c.collect_window(self.db,f,'LITE:quotes',0,300),1)
        self.assertEqual(self.db.execute('select end from checkpoints').fetchone()[0],300)
        raw = gzip.decompress(self.db.execute('select payload from pages limit 1').fetchone()[0])
        self.assertEqual(json.loads(raw)['symbol'],'LITE')
    def test_failure_rolls_back(self):
        f=Fake([{'symbol':'LITE','quotes':[], 'next_page_token':'a'}, OSError()])
        with self.assertRaises(OSError): c.collect_window(self.db,f,'LITE:quotes',0,300)
        self.assertEqual(self.db.execute('select count(*) from pages').fetchone()[0],0)
        self.assertEqual(self.db.execute('select count(*) from checkpoints').fetchone()[0],0)
    def test_repeat_token(self):
        r={'symbol':'LITE','quotes':[], 'next_page_token':'a'}
        with self.assertRaises(ValueError): c.collect_window(self.db,Fake([r,r]),'LITE:quotes',0,300)
        self.assertEqual(self.db.execute('select count(*) from pages').fetchone()[0],0)
    def test_invalid_response(self):
        for r in ({}, {'symbol':'WRONG','quotes':[]}, {'symbol':'LITE','quotes':'oops'}):
            with self.assertRaises(ValueError): c.validate('LITE:quotes',r)
    def test_delayed_window(self):
        with patch.object(c,'space_ok',return_value=True):
            self.assertEqual(c.cycle(self.db,Fake([]),0,1499,'.'),{})
    def test_no_redirect(self):
        with self.assertRaises(ValueError): c.NoRedirect().redirect_request(None,None,302,'',{},'https://evil.test')
    def test_disk_reserve(self):
        with patch.object(c,'space_ok',return_value=False):
            c.cycle(self.db,Fake([]),0,1500,'.')
        self.assertEqual(self.db.execute('select count(*) from checkpoints').fetchone()[0],0)
        self.assertEqual(len(c.status(self.db,0)['errors']),13)
    def test_timezone(self):
        with self.assertRaises(ValueError): c.stamp('2026-09-08T00:00:00')

    def test_archive_verifier(self):
        try:
            from cloud.check_archive import verify
        except ModuleNotFoundError:
            from check_archive import verify
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            db = c.database(Path(directory) / 'archive.sqlite')
            f = Fake([{'symbol':'LITE','quotes':[], 'next_page_token':None}])
            c.collect_window(db, f, 'LITE:quotes', 0, 300)
            self.assertEqual(verify(directory)['recent_page_hashes_verified'],1)
            with db:
                db.execute("UPDATE pages SET sha256='bad'")
            with self.assertRaises(ValueError): verify(directory)
            db.close()

if __name__ == '__main__':
    unittest.main()
