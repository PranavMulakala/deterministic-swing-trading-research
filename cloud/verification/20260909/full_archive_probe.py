"""Read-only full page verification and backup-to-live preservation check."""
from pathlib import Path
import gzip,hashlib,json,sqlite3,sys
sys.path.insert(0,'/opt/trading-readiness-stage-20260909/validation')
from cloud.collector import validate,stamp
live=Path('/var/lib/trading-collector/archive.sqlite')
backup=Path('/var/backups/trading-readiness-20260909/archive.sqlite')
db=sqlite3.connect(live.as_uri()+'?mode=ro',uri=True)
db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
db.execute('ATTACH DATABASE ? AS prior',(backup.as_uri()+'?mode=ro',))
assert db.execute('PRAGMA quick_check').fetchall()==[('ok',)]
assert db.execute('PRAGMA prior.quick_check').fetchall()==[('ok',)]
missing=db.execute('''SELECT count(*) FROM prior.pages b LEFT JOIN main.pages a
 ON a.stream=b.stream AND a.start=b.start AND a.page=b.page
 WHERE a.stream IS NULL OR a.end!=b.end OR a.received_at!=b.received_at
 OR a.sha256!=b.sha256 OR a.records!=b.records OR a.payload!=b.payload''').fetchone()[0]
assert missing==0
count=records=0;streams={}
for stream,start,end,page,receipt,digest,total,payload in db.execute('SELECT * FROM main.pages'):
    raw=gzip.decompress(payload)
    assert hashlib.sha256(raw).hexdigest()==digest
    value=json.loads(raw);n,token=validate(stream,value)
    assert n==total and end-start==300 and start%300==0
    stamp(receipt)
    count+=1;records+=total;streams[stream]=streams.get(stream,0)+1
report={'status':'PASS','all_current_pages_hashed_parsed_and_schema_checked':count,
        'raw_records':records,'streams':streams,
        'predeployment_pages_preserved_byte_for_byte':db.execute('SELECT count(*) FROM prior.pages').fetchone()[0],
        'predeployment_pages_changed_or_missing':missing,'backup_integrity':'ok'}
db.close();print(json.dumps(report,indent=2))
