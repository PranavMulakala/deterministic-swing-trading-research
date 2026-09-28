"""One-time scoped cloud cutover. Keeps previous code, SQLite backup and artifacts."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, shutil, sqlite3, subprocess

stage=Path('/opt/trading-readiness-stage-20260909')
backup=Path('/var/backups/trading-readiness-20260909')
research=Path('/opt/trading-research-v2-20260909')
dashboard=Path('/opt/trading-dashboard-20260909')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout.strip()
def atomic_copy(source,target):
    target=Path(target);temp=target.with_name(target.name+'.readiness-new')
    if temp.exists():raise RuntimeError('Unexpected pending install file')
    shutil.copyfile(source,temp);os.chmod(temp,0o644);os.replace(temp,target)
def db_backup(source,target):
    src=sqlite3.connect(Path(source).as_uri()+'?mode=ro',uri=True,timeout=30)
    dst=sqlite3.connect(target)
    try:src.backup(dst);assert dst.execute('PRAGMA quick_check').fetchall()==[('ok',)]
    finally:dst.close();src.close()
assert os.getuid()==0
assert json.loads((stage/'STAGING_VERIFIED.json').read_text())['status']=='PASS'
release=json.loads((stage/'RELEASE.json').read_text())
assert all(sha(stage/n)==h for n,h in release['files'].items())
assert sha(Path('/opt/trading-research-v1/PINS.json'))=='251ff7786da9fb96d4e64a61c7afc9886cd640f24b69921bbacef7221798b7f2'
assert sha(Path('/opt/trading-collector/collector.py'))=='ff15a649757feaaf3f4360ee1a4b1b96363511f1f2d1069f8e9d41092c093993'
assert not research.exists() and not dashboard.exists() and not backup.exists()
backup.mkdir(mode=0o700)
units=('trading-research.service','trading-dashboard.service')
for name in units:shutil.copy2('/etc/systemd/system/'+name,backup/name)
shutil.copy2('/opt/trading-collector/collector.py',backup/'collector.py')
run('systemctl','stop','trading-research.timer')
try:
    # Finish any already-running writer before backing up its journal; no kill or reset.
    run('systemctl','start','trading-research.service')
    shutil.copy2('/var/lib/trading-research/latest.json',backup/'latest.json')
    db_backup('/var/lib/trading-collector/archive.sqlite',backup/'archive.sqlite')
    db_backup('/var/lib/trading-research/memory.sqlite',backup/'memory.sqlite')
    hashes={p.name:sha(p) for p in Path('/var/lib/trading-research/runs').glob('*.json')}
    (backup/'artifact_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    with sqlite3.connect((backup/'archive.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        checkpoints=dict(db.execute('SELECT stream,end FROM checkpoints'))
    (backup/'checkpoints.json').write_text(json.dumps(checkpoints,indent=2)+'\n')
    shutil.copytree(stage/'research',research)
    shutil.copytree(stage/'dashboard',dashboard)
    run('systemd-analyze','verify',str(stage/'units/trading-research.service'),str(stage/'units/trading-dashboard.service'))
    run('systemctl','stop','trading-collector.service')
    atomic_copy(stage/'collector/news_context_v1.json','/opt/trading-collector/news_context_v1.json')
    atomic_copy(stage/'collector/collector.py','/opt/trading-collector/collector.py')
    for name in units:atomic_copy(stage/'units'/name,'/etc/systemd/system/'+name)
    run('systemctl','daemon-reload')
    run('systemctl','start','trading-collector.service')
    run('systemctl','enable','--now','trading-research.timer')
    run('systemctl','start','trading-research.service')
    run('systemctl','restart','trading-dashboard.service')
    assert run('systemctl','is-active','trading-collector.service')=='active'
    assert run('systemctl','show','trading-research.service','-p','Result','--value')=='success'
    assert run('systemctl','is-active','trading-dashboard.service')=='active'
    assert all(sha(Path('/var/lib/trading-research/runs')/n)==h for n,h in hashes.items())
    assert sha(research/'PINS.json')==release['pins_sha256']
    (backup/'DEPLOYED.json').write_text(json.dumps({'at':datetime.now(timezone.utc).isoformat(),
        'pins':release['pins_sha256'],'preserved_artifacts':len(hashes),'orders':False},indent=2)+'\n')
    print((backup/'DEPLOYED.json').read_text())
except Exception:
    # Restore known old code and unit definitions; never discard newer archive pages.
    subprocess.run(['systemctl','stop','trading-research.timer'])
    subprocess.run(['systemctl','stop','trading-research.service','trading-collector.service'])
    atomic_copy(backup/'collector.py','/opt/trading-collector/collector.py')
    for name in units:atomic_copy(backup/name,'/etc/systemd/system/'+name)
    run('systemctl','daemon-reload')
    run('systemctl','start','trading-collector.service','trading-research.timer')
    run('systemctl','start','trading-research.service')
    run('systemctl','restart','trading-dashboard.service')
    raise
