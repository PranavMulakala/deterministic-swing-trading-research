from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from cloud.test_research_loop import fixture, save
from cloud.research_runner import execute


class DirectReplayRegression(unittest.TestCase):
    def test_first_prospective_direct_signal_full_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,archive,output=fixture(Path(tmp))
            days=['2026-09-09','2026-09-10','2026-09-11','2026-09-14','2026-09-15','2026-09-16']
            with sqlite3.connect(archive/'archive.sqlite') as db:
                original=list(db.execute('SELECT * FROM pages'))
                for day in days:
                    delta=(datetime.fromisoformat(day)-datetime(2026,9,8)).days*86400
                    for stream,start,end,page,receipt,_,count,payload in original:
                        raw=gzip.decompress(payload).replace(b'2026-09-08',day.encode())
                        db.execute('INSERT INTO pages VALUES(?,?,?,?,?,?,?,?)',
                            (stream,start+delta,end+delta,page,receipt.replace('2026-09-08',day),hashlib.sha256(raw).hexdigest(),count,gzip.compress(raw)))
                db.execute('UPDATE checkpoints SET end=end+?',(8*86400,))
                db.execute("UPDATE health SET checked_at='2026-09-16T20:29:00Z'")
            ref=json.loads((archive/'references/ref.json').read_text())
            existing={r['date'] for r in ref['calendar']}
            ref['calendar'].extend({'date':d,'open':'09:30','close':'16:00'} for d in days if d not in existing)
            ref['fetched_at']='2026-09-16T06:00:00Z'
            digest=save(archive/'references/ref.json',ref)
            save(archive/'references/latest.json',{'file':'ref.json','sha256':digest})
            at=datetime.fromisoformat('2026-09-16T20:30:00+00:00').timestamp()
            result=execute(root,archive,output,at)
            self.assertEqual(result['status'],'REPLAY_COMPLETE_RESEARCH_ONLY',result)
            challenger=result['results']['orb_challenger']
            self.assertEqual(challenger['status'],'REPLAY_COMPLETE_RESEARCH_ONLY')
            self.assertEqual(challenger['days'],['2026-09-16'])
            self.assertEqual(len(challenger['scenarios']),8)
            self.assertTrue(all(a['status']=='passed' for a in challenger['audits'].values()))
            again=execute(root,archive,output,at+60)
            self.assertEqual(result['results'],again['results'])
            self.assertFalse(result['orders_enabled'])


if __name__=='__main__': unittest.main()
