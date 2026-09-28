"""Read-only archive verification; never opens credentials."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

def verify(folder):
    path = Path(folder).resolve() / 'archive.sqlite'
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        db.execute('BEGIN')  # One consistent snapshot while the collector is writing.
        integrity = db.execute('PRAGMA quick_check').fetchall()
        if integrity != [('ok',)]:
            raise ValueError('SQLite integrity check failed')
        checked = 0
        for digest, payload in db.execute('SELECT sha256,payload FROM pages ORDER BY start DESC LIMIT 200'):
            raw = gzip.decompress(payload)
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError('Source hash mismatch')
            json.loads(raw)
            checked += 1
        checkpoints = dict(db.execute('SELECT stream,end FROM checkpoints'))
        for stream, end in checkpoints.items():
            windows = list(db.execute('SELECT start,end,count(*),min(page),max(page) FROM pages WHERE stream=? GROUP BY start,end ORDER BY start', (stream,)))
            previous = None
            for start, stop, count, first, last in windows:
                if stop - start != 300 or first != 0 or count != last + 1 or (previous is not None and start != previous):
                    raise ValueError('Non-contiguous archive')
                previous = stop
            if previous != end:
                raise ValueError('Checkpoint differs from last committed window')
        return {'integrity': 'ok', 'recent_page_hashes_verified': checked,
                'checkpoints': checkpoints,
                'records_by_stream': dict(db.execute('SELECT stream,sum(records) FROM pages GROUP BY stream'))}
    finally:
        db.close()

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('folder')
    args = p.parse_args()
    print(json.dumps(verify(args.folder), indent=2))
