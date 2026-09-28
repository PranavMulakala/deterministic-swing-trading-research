"""Executed over pinned SSH via stdin. Reads only research files and SQLite.
No broker imports, credential reads, server writes, or strategy execution.
"""
import gzip
import hashlib
import json
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SYMBOLS = 'SPY QQQ IWM DIA XLB XLE XLF XLI XLK XLP XLRE XLU XLV XLY XLC LITE COHR CIEN FN AAOI'.split()
STOCKS = SYMBOLS[-5:]
EXPECTED_PIN = 'ec9ad04fc8908d66b036c3ae6f3cb0de6dc16e822a2c2a5a2ed1496feec05cfb'

def read_json(path):
    with Path(path).open('rb') as f:
        raw = f.read(64 * 1024 * 1024 + 1)
    if len(raw) > 64 * 1024 * 1024:
        raise ValueError('Research artifact exceeds dashboard read limit')
    return json.loads(raw), hashlib.sha256(raw).hexdigest()

def utc(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()

def snapshot(archive=Path('/var/lib/trading-collector'), research=Path('/var/lib/trading-research'), code=Path('/opt/trading-research-repair-20260921'), now=None, services=True, agentic=Path('/var/lib/agentic-paper-runtime')):
    now = now or datetime.now(timezone.utc)
    health, _ = read_json(archive / 'health.json')
    latest, latest_sha = read_json(research / 'latest.json')
    policy, _ = read_json(code / 'cloud/research_policy.json')
    context, _ = read_json(code / 'cloud/news_context_v1.json')
    pins, pins_sha = read_json(code / 'PINS.json')
    pin_bad = [p for p,h in pins.items() if (code/p).is_symlink() or hashlib.sha256((code/p).read_bytes()).hexdigest() != h]
    rp, _ = read_json(archive / 'references/latest.json')
    if Path(rp['file']).name != rp['file']:
        raise ValueError('Invalid reference path')
    ref, ref_sha = read_json(archive / 'references' / rp['file'])
    if ref_sha != rp['sha256']:
        raise ValueError('Reference hash mismatch')
    today = now.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    sessions = [s for s in ref['calendar'] if policy['start'] <= s['date'] <= today]
    session = max(sessions, key=lambda s:s['date']) if sessions else None
    start = datetime.fromisoformat(session['date']+'T'+session['open']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp() if session else now.timestamp()
    end = datetime.fromisoformat(session['date']+'T'+session['close']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp() if session else now.timestamp()
    cutoff = min(now.timestamp(), end)
    series = {s:{'one':{},'five':{},'ticks':{}} for s in SYMBOLS}
    news = {}; conflicts=[]; verified=set()
    db = sqlite3.connect((archive/'archive.sqlite').resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    db.execute('PRAGMA query_only=ON'); db.execute('BEGIN')
    try:
        checkpoints = dict(db.execute('SELECT stream,end FROM checkpoints'))
        streams=[]
        for stream, cp in sorted(checkpoints.items()):
            count, records = db.execute('SELECT count(*),coalesce(sum(records),0) FROM pages WHERE stream=?',(stream,)).fetchone()
            streams.append({'name':stream,'through':utc(cp),'pages':count,'records':records,'backlog_seconds':max(0,int((now.timestamp()-1200)//300*300)-cp)})
        for stream in ('bars','bars5','news','sector_news'):
            window_start=(int(datetime.fromisoformat(session['date']+'T00:00:00+00:00').timestamp())
                          if session and stream in ('news','sector_news') else int(start)//300*300-300)
            rows=db.execute('SELECT start,page,received_at,sha256,payload FROM pages WHERE stream=? AND start>=? AND start<? ORDER BY start,page',(stream,window_start,int(cutoff)))
            for window,page,received,digest,payload in rows:
                raw=gzip.decompress(payload)
                if hashlib.sha256(raw).hexdigest()!=digest: raise ValueError('Archive page hash mismatch')
                verified.add((stream,window,page)); body=json.loads(raw)
                if stream in ('news','sector_news'):
                    for row in body.get('news') or []:
                        ident=(row['id'],row.get('updated_at'))
                        if ident not in news:
                            news[ident]={k:row.get(k) for k in ('id','headline','source','url','created_at','updated_at','symbols')}
                            news[ident]['first_received_at']=received
                            news[ident]['source_streams']=[]
                        news[ident]['first_received_at']=min(received,news[ident]['first_received_at'])
                        if stream not in news[ident]['source_streams']:
                            news[ident]['source_streams'].append(stream)
                    continue
                for symbol, bars in (body.get('bars') or {}).items():
                    if symbol not in series: continue
                    target=series[symbol]['one' if stream=='bars' else 'five']
                    for row in bars:
                        t=datetime.fromisoformat(row['t'].replace('Z','+00:00')).timestamp()
                        step=60 if stream=='bars' else 300
                        if not start<=t or t+step>min(end,checkpoints.get(stream,0)): continue
                        clean={k:row.get(k) for k in ('t','o','h','l','c','v','vw')}
                        if row['t'] in target and target[row['t']]!=clean:
                            conflicts.append({'symbol':symbol,'time':row['t'],'stream':stream})
                        target[row['t']]=clean
        for symbol in SYMBOLS:
            for interval in ('one','five'):
                series[symbol][interval]=[v for _,v in sorted(series[symbol][interval].items())]
        for symbol in STOCKS:
            for kind in ('quotes','trades'):
                stream=symbol+':'+kind
                row=db.execute('SELECT start,page,sha256,payload,received_at FROM pages WHERE stream=? AND records>0 ORDER BY start DESC,page DESC LIMIT 1',(stream,)).fetchone()
                if not row: continue
                window,page,digest,payload,receipt=row
                raw=gzip.decompress(payload)
                if hashlib.sha256(raw).hexdigest()!=digest: raise ValueError('Tick display page hash mismatch')
                verified.add((stream,window,page))
                rows=json.loads(raw).get(kind) or []
                if rows:
                    last=max(rows,key=lambda r:r['t'])
                    same=[r for r in rows if r['t']==last['t']]
                    fields=('t','bp','ap','bs','as') if kind=='quotes' else ('t','p','s')
                    conflict=kind=='quotes' and any(any(r.get(k)!=last.get(k) for k in fields) for r in same)
                    series[symbol]['ticks'][kind]={'last':{k:last.get(k) for k in fields} if not conflict else None,'conflicting':conflict,'received_at':receipt}
        # Displayed pages only: this is not a full execution/archive integrity audit.
        news_rows=sorted(news.values(),key=lambda n:n.get('created_at') or '',reverse=True)
    finally: db.close()
    artifacts=[]
    mem=research/'memory.sqlite'
    if mem.exists():
        connection=sqlite3.connect(mem.resolve().as_uri()+'?mode=ro',uri=True)
        try:
            artifacts=[dict(zip(('run_id','last_day','file','sha256'),row)) for row in connection.execute('SELECT id,last_day,artifact,sha256 FROM runs ORDER BY last_day DESC,id LIMIT 100')]
        finally: connection.close()
    artifact_check=None
    if latest.get('run_id'):
        run=latest['run_id']
        if len(run)!=64 or any(c not in '0123456789abcdef' for c in run): raise ValueError('Invalid run identity')
        stored, digest=read_json(research/'runs'/(run+'.json'))
        indexed=next((r for r in artifacts if r['run_id']==run),None)
        matches=stored.get('results')==latest.get('results') and stored.get('provenance')==latest.get('provenance') and stored.get('learning')==latest.get('learning')
        artifact_check={'sha256':digest,'index_hash_matches':bool(indexed and indexed['sha256']==digest),'latest_results_match':matches}
    agentic_path=agentic/'status.json'
    agentic_status=(read_json(agentic_path)[0] if agentic_path.is_file() else {
        'status':'NOT_DEPLOYED','reason':'No paper lifecycle status is available',
        'orders_enabled':False,'broker_enabled':False,'completed_session_counted':False,
    })
    stock_path=Path('/var/lib/agentic-stock-free-runtime/status.json')
    stock_status=read_json(stock_path)[0] if services and stock_path.is_file() else {'status':'NOT_DEPLOYED'}
    if stock_status.get('checked_at'):
        stock_age=(now-datetime.fromisoformat(stock_status['checked_at'])).total_seconds()
        if not 0 <= stock_age <= 600:
            stock_status={**stock_status,'status':'STALE_STATUS','reason':'Stock supervisor has not refreshed within ten minutes'}
    states={}
    if services:
        fields=['ActiveState','SubState','Result','ExecMainStartTimestamp','ExecMainExitTimestamp','ExecMainStatus','UnitFileState','NextElapseUSecRealtime','LastTriggerUSec','PrivateNetwork','ReadOnlyPaths','InaccessiblePaths']
        for unit in ('trading-collector.service','trading-research.service','trading-references.service','trading-research.timer','trading-references.timer','agentic-paper-runtime.service','agentic-paper-runtime.timer','agentic-stock-free-provider.timer','agentic-stock-free-runtime.timer','trading-shadow-7500.service'):
            args=['systemctl','show',unit]+['--property='+f for f in fields]
            result=subprocess.run(args,capture_output=True,text=True,timeout=8,check=True)
            states[unit]=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    usage=shutil.disk_usage(archive)
    orb,_=read_json(code/'research/orb_comparison_v1/spec.json')
    lite,_=read_json(code/'research/lite_reversal_v1/config.json')
    return {'schema_version':1,'fetched_at':now.isoformat(),'health':health,'research':latest,'policy':policy,
            'session':{'date':session['date'],'open':utc(start),'close':utc(end),'earliest_replay':utc(end+1200)} if session else None,
            'stocks':series,'streams':streams,'news':news_rows[:100],'news_versions_in_window':len(news_rows),
            'bar_conflicts':conflicts,'services':states,'disk':{'free':usage.free,'total':usage.total},
            'verification':{'display_pages_hashed':len(verified),'scope':'Displayed session bar/news pages and latest nonempty tick pages; not a full archive or execution audit',
                'pins_sha256':pins_sha,'manifest_matches_deployment':pins_sha==EXPECTED_PIN,'pinned_files':len(pins),'pin_mismatches':pin_bad,
                'reference_sha256':ref_sha,'reference_fetched_at':ref['fetched_at'],'latest_sha256':latest_sha,'artifact':artifact_check},
            'artifacts':artifacts,'agentic_trial':agentic_status,'stock_trial':stock_status,
            'config':{'orb':orb,'lite':lite,'news_context':context},'source':'Personal cloud collector; delayed SIP/raw data'}

if __name__=='__main__':
    print(json.dumps(snapshot(),separators=(',',':'),allow_nan=False))
