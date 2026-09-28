"""Switch only repaired paper services; preserve old releases and database backups."""
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil
import sqlite3
import subprocess

BASE=Path('/var/tmp/trading-repair-20260921')
backup=Path('/var/backups/trading-repair-20260921')
stock=Path('/opt/agentic-stock-free-ops-v3-20260921')
research=Path('/opt/trading-research-repair-20260921')
dashboard=Path('/opt/trading-dashboard-repair-20260921')
stage=json.loads((BASE/'research-output/latest.json').read_text())
assert stage['status']=='REPLAY_COMPLETE_RESEARCH_ONLY'
assert stage['results']['days'][-1]=='2026-09-18'
if backup.exists(): raise SystemExit('Backup exists; inspect before redeployment')
backup.mkdir(mode=0o700)
units=('agentic-stock-free-provider','agentic-stock-free-runtime','trading-research','trading-shadow-7500')
def cmd(*args):
    subprocess.run(args,check=True,timeout=660)
cmd('systemctl','stop',*[u+'.timer' for u in units])
cmd('systemctl','stop',*[u+'.service' for u in units])
for name,folder in (('stock',Path('/var/lib/agentic-stock-free-runtime')),('shadow',Path('/var/lib/private/trading-shadow-7500'))):
    dest=backup/name;dest.mkdir()
    for p in folder.glob('*.sqlite'):
        src=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)
        target=sqlite3.connect(dest/p.name)
        src.backup(target);target.close();src.close()
    for p in folder.glob('*.json'): shutil.copy2(p,dest/p.name)
shutil.copy2('/var/lib/trading-research/latest.json',backup/'research-latest.json')
changes={
 'agentic-stock-free-provider': f'[Service]\nWorkingDirectory={stock}\nEnvironment=PYTHONPATH={stock}\nExecStart=\nExecStart=/usr/bin/python3 {stock}/cloud/free_stock_provider_v3.py\n',
 'agentic-stock-free-runtime': f'[Service]\nWorkingDirectory={stock}\nExecStart=\nExecStart=/usr/bin/python3 -m cloud.stock_runtime_supervisor\n',
 'trading-research': f'[Service]\nWorkingDirectory={research}\n',
 'trading-dashboard': f'[Service]\nWorkingDirectory={dashboard}\nReadOnlyPaths={research} /var/lib/agentic-stock-free-runtime\n',
 'trading-shadow-7500': '[Service]\nCPUQuota=50%\nTimeoutStartSec=120\n',
}
written=[]
try:
    for unit,text in changes.items():
        path=Path('/etc/systemd/system')/(unit+'.service.d')/'90-repair-20260921.conf'
        path.parent.mkdir(exist_ok=True)
        if path.exists(): raise RuntimeError('unexpected existing override')
        (backup/(unit+'.service.before')).write_text(subprocess.check_output(['systemctl','cat',unit+'.service'],text=True))
        path.write_text(text);written.append(path)
    cmd('systemctl','daemon-reload')
    cmd('systemctl','start','trading-shadow-7500.service')
    cmd('systemctl','start','agentic-stock-free-provider.service','agentic-stock-free-runtime.service')
    cmd('systemctl','start','trading-research.service')
    latest=json.loads(Path('/var/lib/trading-research/latest.json').read_text())
    assert latest['status']=='REPLAY_COMPLETE_RESEARCH_ONLY',latest.get('reason')
    cmd('systemctl','restart','trading-dashboard.service')
    cmd('systemctl','start',*[u+'.timer' for u in units])
    print(json.dumps({'status':'DEPLOYED','at':datetime.now(timezone.utc).isoformat(),'backup':str(backup)}),flush=True)
except BaseException:
    for path in written: path.rename(backup/(path.parent.name+'.failed-override'))
    cmd('systemctl','daemon-reload')
    cmd('systemctl','restart','trading-dashboard.service')
    cmd('systemctl','start',*[u+'.timer' for u in units])
    raise
