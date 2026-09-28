"""Read-only redacted deployment receipt; excludes credentials and quote values."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from datetime import datetime,timezone

root=Path('/opt/ibkr-paper-v1')
manifest=json.loads((root/'manifest.json').read_text())
matched=all((root/p).is_file() and hashlib.sha256((root/p).read_bytes()).hexdigest()==h
            for p,h in manifest.items())
db=sqlite3.connect('file:/var/lib/ibkr-paper/state.sqlite?mode=ro',uri=True)
health=db.execute('SELECT payload FROM health WHERE id=1').fetchone()
value={'at':datetime.now(timezone.utc).isoformat(),'manifest_verified':matched,
       'manifest_files':len(manifest),'health':json.loads(health[0]) if health else None,
       'event_counts':dict(db.execute('SELECT kind,COUNT(*) FROM events GROUP BY kind')),
       'outbox_states':dict(db.execute('SELECT state,COUNT(*) FROM outbox GROUP BY state')),
       'sqlite_integrity':db.execute('PRAGMA quick_check').fetchone()[0],
       'smtp_credentials_present':Path('/etc/ibkr-paper/smtp.json').exists()}
execution=Path('/var/lib/ibkr-paper/execution-health.json')
value['execution_health']=json.loads(execution.read_text()) if execution.exists() else None
units=('ibkr-paper-gateway','ibkr-paper-collector','ibkr-paper-reports.timer',
       'ibkr-paper-calendar.timer','ibkr-paper-analysis.timer',
       'ibkr-paper-analysis.service','ibkr-paper-strategy','trading-collector','trading-dashboard')
value['services']={u:subprocess.check_output(['systemctl','show',u,'-p','ActiveState',
    '-p','SubState','-p','NRestarts','-p','MainPID','-p','UnitFileState'],text=True).splitlines() for u in units}
print(json.dumps(value,indent=2))
