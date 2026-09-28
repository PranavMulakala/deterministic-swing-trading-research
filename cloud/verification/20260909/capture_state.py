"""Read current deployment evidence; no secret reads or broker requests."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,http.client,json,sqlite3,subprocess,sys,time
sys.path.insert(0,'/opt/trading-research-v2-20260909')
sys.path.insert(0,'/opt/trading-readiness-stage-20260909/validation')
from cloud.readiness import assess
from cloud.check_archive import verify

research=Path('/opt/trading-research-v2-20260909')
dashboard=Path('/opt/trading-dashboard-20260909')
archive=Path('/var/lib/trading-collector')
out=Path('/var/lib/trading-research')
backup=Path('/var/backups/trading-readiness-20260909')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def properties(unit):
    names=['ActiveState','Result','ExecMainStartTimestamp','ExecMainExitTimestamp','ExecMainStatus',
           'LastTriggerUSec','UnitFileState','WorkingDirectory','PrivateNetwork','InaccessiblePaths',
           'ReadOnlyPaths','NRestarts','MemoryCurrent','MemoryMax']
    raw=subprocess.check_output(['systemctl','show',unit]+['-p'+n for n in names],text=True)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
pins=read(research/'PINS.json');manifest=read(dashboard/'MANIFEST.json')
assert all(sha(research/n)==h for n,h in pins.items())
assert all(sha(dashboard/n)==h for n,h in manifest.items())
release=read(Path('/opt/trading-readiness-stage-20260909/RELEASE.json'))
assert sha(research/'PINS.json')==release['pins_sha256']
assert sha(Path('/opt/trading-collector/collector.py'))==release['files']['collector/collector.py']
assert sha(Path('/opt/trading-collector/news_context_v1.json'))==pins['cloud/news_context_v1.json']
oldhashes=read(backup/'artifact_hashes.json')
assert all(sha(out/'runs'/n)==h for n,h in oldhashes.items())
policy=read(research/'cloud/research_policy.json')
readiness=assess(archive,policy,time.time())
integrity=verify(archive)
health=read(archive/'health.json');latest=read(out/'latest.json')
with sqlite3.connect((archive/'archive.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    context=dict(zip(('first_window','last_window_end','pages','records'),db.execute("SELECT min(start),max(end),count(*),sum(records) FROM pages WHERE stream='sector_news'").fetchone()))
    context['committed_first_receipt']=db.execute("SELECT min(received_at) FROM pages WHERE stream='sector_news'").fetchone()[0]
refpin=read(archive/'references/latest.json')
reference=read(archive/'references'/refpin['file'])
assert sha(archive/'references'/refpin['file'])==refpin['sha256']
session=next(s for s in reference['calendar'] if s['date']=='2026-09-09')
assert session['open']=='09:30' and session['close']=='16:00'
states={u:properties(u) for u in ('trading-collector.service','trading-research.service',
        'trading-research.timer','trading-references.timer','trading-dashboard.service')}
conn=http.client.HTTPConnection('127.0.0.1',8766,timeout=15)
conn.request('GET','/api/snapshot');response=conn.getresponse();snap=json.loads(response.read());conn.close()
assert response.status==200 and response.getheader('Cache-Control')=='no-store'
data=snap['data'];assert not snap['connection']['error']
v=data['verification']
assert v['manifest_matches_deployment'] and not v['pin_mismatches']
assert v['artifact']['index_hash_matches'] and v['artifact']['latest_results_match']
forward=latest['results']['lite_forward']
assert forward['capital_arms']==[5000,10000] and forward['evaluation_start']=='2026-09-09'
assert forward['status']=='WAITING_FOR_FIRST_FORWARD_SESSION' and not forward['results']
assert not latest['orders_enabled'] and not latest['promotion_enabled']
parent=read(backup/'latest.json')
preserved_sections=('orb','orb_summaries','ledger_audits','contrasts','bar_proxy_diagnostic','prepared','lite','lite_excluded','days')
assert all(parent['results'][k]==latest['results'][k] for k in preserved_sections)
with sqlite3.connect((out/'memory.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    distinct_sessions=db.execute('SELECT count(DISTINCT last_day) FROM runs').fetchone()[0]
report={'checked_at':datetime.now(timezone.utc).isoformat(),'direct_readiness':readiness,
        'latest_research_readiness':latest['session_readiness'],'health':health,'services':states,
        'pin_manifest':release['pins_sha256'],'pinned_files_verified':len(pins),
        'dashboard_files_verified':len(manifest),'preserved_old_artifacts':len(oldhashes),
        'calendar_session':session,'reference_fetched_at':reference['fetched_at'],
        'sector_news':context,'archive_integrity':integrity,
        'latest_run':latest['run_id'],'latest_checked_at':latest['checked_at'],
        'parent_result_sections_unchanged':list(preserved_sections),'distinct_completed_session_dates':distinct_sessions,
        'forward_capital_arms':forward,'dashboard':{'snapshot_at':data['fetched_at'],
            'streams':len(data['streams']),'artifact_and_source_verified':True,
            'research_checked_at':data['research']['checked_at'],'research_run_id':data['research']['run_id'],
            'context_symbols':data['config']['news_context']['symbols'],
            'capital_arms':data['policy']['lite_forward']['capital_arms']},'orders_enabled':False}
print(json.dumps(report,indent=2))
