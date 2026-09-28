"""Minimal allowlisted bundle; no credentials, broker adapters or old experiment code."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

root=Path(__file__).resolve().parents[3]
source=root/'research/agentic_shadow_v1'
out=Path(sys.argv[1]).resolve()
if out.exists(): raise SystemExit('Use a new empty release path')
out.mkdir(parents=True)
for name in ('engine.py','fixtures.py','report.py','run.py','config.json','PROTOCOL.md','FREEZE.json'):
    target=out/'research/agentic_shadow_v1'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source/name,target)
for name in ('safe_paths.py','__init__.py'):
    target=out/'src/swingbot'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(root/'src/swingbot'/name,target)
for name in ('verify_release.py','install.sh','trading-shadow-7500.service','trading-shadow-7500.timer'):
    shutil.copyfile(source/'deployment'/name,out/name)
files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
revision=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
(out/'RELEASE.json').write_text(json.dumps({'revision':revision,'files':files,'orders':False},indent=2)+'\n')
print(revision)
