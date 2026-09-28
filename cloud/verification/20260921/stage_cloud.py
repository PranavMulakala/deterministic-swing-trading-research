"""Install versioned source directories and smoke-test against copied state only."""
from pathlib import Path
import hashlib
import json
import shutil
import sqlite3
import subprocess
import tarfile

BASE=Path('/var/tmp/trading-repair-20260921')
ROOTS={'research':Path('/opt/trading-research-repair-20260921'),
       'stock':Path('/opt/agentic-stock-free-ops-v3-20260921'),
       'dashboard':Path('/opt/trading-dashboard-repair-20260921')}
EXPECTED={'research':'da3752ebf9da4f4a738f44b39d13ef7d9715a1eb70abebabbab9ac79ce20bf44',
          'stock':'f401d0398fa2ae0c566e89d61fffcb5d2a2671c40d94e908f3e638332c73c050',
          'dashboard':'83c24d2b6cd5425ead519d93ed8358d1ca1d27d94bc7dcb47fd35c08a473f566'}
for name,root in ROOTS.items():
    source=BASE/(name+'.tar.gz')
    assert hashlib.sha256(source.read_bytes()).hexdigest()==EXPECTED[name]
    if root.exists(): raise SystemExit('Release already exists: '+str(root))
    root.mkdir()
    with tarfile.open(source) as tar: tar.extractall(root,filter='data')

stage=BASE/'stock-state'
stage.mkdir()
for name in ('stock.sqlite','runtime.sqlite'):
    src=sqlite3.connect('file:/var/lib/agentic-stock-free-runtime/'+name+'?mode=ro',uri=True)
    dest=sqlite3.connect(stage/name)
    src.backup(dest);dest.close();src.close()
for name in ('latest.json','status.json'):
    shutil.copyfile('/var/lib/agentic-stock-free-input/'+name,BASE/('input-'+name))
def run(args,cwd):
    result=subprocess.run(args,cwd=cwd,text=True,capture_output=True,timeout=600,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
    print(json.dumps({'args':args,'returncode':result.returncode,'output':result.stdout[-8000:],'stderr':result.stderr[-3000:]}),flush=True)
    if result.returncode: raise SystemExit('Staging failed')
run(['/usr/bin/python3','-m','research.agentic_stock_paper_free_v2.freeze'],ROOTS['stock'])
run(['/usr/bin/python3','-m','unittest','cloud.test_stock_runtime_supervisor','cloud.test_free_stock_provider','research.agentic_stock_paper_free_v2.test_runtime','-q'],ROOTS['stock'])
run(['/usr/bin/python3','-m','cloud.stock_runtime_supervisor','--state',str(stage),'--input',str(BASE/'input-latest.json'),'--provider-status',str(BASE/'input-status.json')],ROOTS['stock'])
run(['/usr/bin/python3','-m','cloud.research_runner','--root',str(ROOTS['research']),'--output',str(BASE/'research-output')],ROOTS['research'])
research=json.loads((BASE/'research-output/latest.json').read_text())
assert research['status']=='REPLAY_COMPLETE_RESEARCH_ONLY',research
assert research['results']['days'][-1]=='2026-09-18'
assert all(a['status']=='passed' for a in research['results']['orb_challenger']['audits'].values())
print('STAGING_VERIFIED',flush=True)
