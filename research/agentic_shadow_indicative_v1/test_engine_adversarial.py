"""Fresh review regressions, distinct from implementation-time examples."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

from .engine import Ledger, stamp
from .fixtures import packet, resign


class AdversarialTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.db=Ledger(self.root/'ledger.sqlite')
    def tearDown(self):
        self.db.close();self.tmp.cleanup()

    def test_fill_uses_revised_earlier_close(self):
        self.db.step(packet())
        p=packet('2026-09-14T14:00:02+00:00')
        p['calendar']['close']='2026-09-14T15:00:00+00:00';resign(p['calendar'])
        result=self.db.step(p)
        self.assertEqual(stamp(result['state']['deterministic']['position']['close_at']),stamp(p['calendar']['close']))

    def test_open_exposure_adopts_earlier_session_close(self):
        self.db.step(packet());self.db.step(packet('2026-09-14T14:00:02+00:00'))
        p=packet('2026-09-14T14:45:00+00:00')
        p['calendar']['close']='2026-09-14T15:00:00+00:00';resign(p['calendar'])
        result=self.db.step(p)
        self.assertIsNotNone(result['state']['deterministic']['pending'])
        self.assertEqual(result['state']['deterministic']['pending']['reason'],'session_exit')

    def test_exit_must_have_verified_open_session(self):
        self.db.step(packet());self.db.step(packet('2026-09-14T14:00:02+00:00'))
        self.db.step(packet('2026-09-14T16:00:03+00:00'))
        result=self.db.step(packet('2026-09-14T21:00:00+00:00'))
        self.assertIsNotNone(result['state']['deterministic']['position'])
        self.assertEqual(result['state']['deterministic']['pending']['side'],'sell')

    def test_malformed_provenance_keeps_indicative_report_alive(self):
        from .run import main
        p={'event_id':'bad-provenance','kind':'indicative','purpose':'plumbing_only','orders_enabled':False,
           'observed_at':datetime.now(timezone.utc).isoformat(),'provenance':None}
        inp=self.root/'packet.json'; inp.write_text(json.dumps([p])); state=self.root/'observed'
        with patch('sys.argv',['shadow','--kind','indicative','--state',str(state),'--input',str(inp)]), contextlib.redirect_stdout(io.StringIO()):main()
        report=json.loads((state/'report.json').read_text())
        self.assertIn('BLOCKED',report['real_data_readiness'])
        self.assertIsNotNone(report['ingestion_error'])

    def test_invalid_proposal_container_never_silently_accepts(self):
        for value in (False,[],0,''):
            with self.subTest(value=value),self.assertRaises(ValueError):self.db.step(packet(),proposals=value)

    def test_bearish_signal_selects_long_put(self):
        p=packet()
        for b,v in zip(p['bars'],(504000,503000,502000)):
            b['close_mills']=v;resign(b)
        c=p['chain']['contracts'][0]['contract'];c['right']='P';c['symbol']=c['symbol'].replace('C005','P005');resign(c)
        q=p['chain']['contracts'][0]['quote'];q['symbol']=c['symbol'];resign(q);resign(p['chain'])
        result=self.db.step(p)
        self.assertEqual(result['candidate']['contract']['right'],'P')
        self.assertEqual(result['candidate']['quantity'],1)

    def test_model_veto_cannot_modify_baseline_inputs(self):
        from .engine import mock_proposal,digest
        p=packet();a=mock_proposal('analyst',digest(p));a['action']='abstain'
        result=self.db.step(p,proposals={'analyst':a})
        self.assertEqual(result['decisions']['deterministic']['verdict'],'accepted')
        self.assertIsNone(result['state']['analyst']['pending'])

if __name__=='__main__':unittest.main()
