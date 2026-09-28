import json
import sqlite3
import unittest

from cloud.ibkr_paper_v1.tape_adapter import Tape, normalize, whole_size
from cloud.ibkr_paper_v1.execution import NS, SYMBOL


class TapeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE events(id INTEGER PRIMARY KEY,received_ns INTEGER,kind TEXT,payload TEXT)')
        self.at = 1_790_000_000 * NS
        self.quote = {'contract': SYMBOL, 'data_type': 1, 'broker_time_seconds': self.at//NS,
                      'bid_ticks': 10000, 'ask_ticks': 10001, 'bid_size': '1', 'ask_size': '2.0'}
        self.trade = {'contract': SYMBOL, 'data_type': 1, 'broker_time_seconds': self.at//NS,
                      'price_ticks': 10001, 'size': '2', 'tick_type': 2,
                      'unreported': False, 'past_limit': False,
                      'special_conditions': '', 'exchange': 'CME'}

    def tearDown(self):
        self.db.close()

    def add(self, at, kind, payload):
        self.db.execute('INSERT INTO events(received_ns,kind,payload) VALUES(?,?,?)',
                        (at, kind, json.dumps(payload)))

    def test_recorder_decimal_strings_normalize_without_rounding(self):
        self.assertEqual(normalize(1,self.at,'quote',self.quote)['ask_size'],2)
        self.assertTrue(normalize(2,self.at,'trade',self.trade)['eligible'])
        blank=normalize(2,self.at,'trade',dict(self.trade,exchange=''))
        self.assertEqual(blank['exchange_label'],'')
        self.assertEqual(blank['venue_basis'],'RECORDER_VERIFIED_CONTRACT')
        for value in ('1.5','NaN','Infinity','0',True,1.0):
            with self.assertRaises(ValueError): whole_size(value)

    def test_missing_flags_delayed_quotes_and_bad_clock_fail_closed(self):
        for changes in ({'unreported':None},{'past_limit':True},{'exchange':'OTHER'},
                        {'special_conditions':'X'},{'tick_type':True}):
            with self.assertRaises(ValueError):
                normalize(1,self.at,'trade',dict(self.trade,**changes))
        for changes in ({'data_type':True},{'data_type':3},{'broker_time_seconds':self.at//NS-6}):
            with self.assertRaises(ValueError):
                normalize(1,self.at,'quote',dict(self.quote,**changes))

    def test_insertion_order_preserves_clock_regression(self):
        self.add(self.at+NS,'quote',self.quote)
        self.add(self.at,'trade',self.trade)
        tape=Tape(self.db,self.at,self.at+2*NS)
        with self.assertRaises(ValueError): list(tape)
        self.assertIsNone(tape.metadata)

    def test_original_rows_are_hashed_and_interval_is_exclusive(self):
        self.add(self.at,'quote',self.quote)
        self.add(self.at+NS,'trade',self.trade)
        tape=Tape(self.db,self.at,self.at+NS)
        self.assertEqual(len(list(tape)),1)
        self.assertEqual(tape.metadata['counts'],{'quote':1,'trade':0,'other':0})
        self.assertFalse(tape.metadata['strategy_evidence_approved'])
        with self.assertRaises(ValueError): list(tape)
        digest=tape.metadata['source_sha256']
        self.db.execute('UPDATE events SET payload=? WHERE id=1',(json.dumps(dict(self.quote,bid_size='3')),))
        changed=Tape(self.db,self.at,self.at+NS);list(changed)
        self.assertNotEqual(digest,changed.metadata['source_sha256'])

    def test_connection_and_invalid_events_cannot_disappear_from_replay(self):
        for kind,payload in (('connection',{}),('invalid_trade',{}),
                             ('broker_status',{'code':1101}),('health',{'status':'STALE'})):
            self.db.execute('DELETE FROM events')
            self.add(self.at,kind,payload)
            with self.assertRaises(ValueError):list(Tape(self.db,self.at,self.at+NS))
