"""Build only this isolated service, its tests and the previously installed SDK."""
import hashlib
import json
from pathlib import Path
import tarfile

root=Path(__file__).resolve().parents[2]
output=root/'outputs/paper/ibkr-cloud'
output.mkdir(parents=True,exist_ok=True)
files=[]
for folder in ('cloud/ibkr_paper_v1','tests/ibkr_paper_v1'):
    for p in sorted((root/folder).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            files.append((p,str(p.relative_to(root))))
for name in ('engine.py','config.json','PROTOCOL.md'):
    files.append((root/'research/mnq_feasibility_v1'/name,'vendor/reference_mnq/'+name))
sdk=root/'outputs/tmp/ibkr-sdk-1050.02/IBJts/source/pythonclient'
for p in sorted(sdk.rglob('*')):
    if p.is_file() and '__pycache__' not in p.parts and '.egg-info' not in str(p):
        files.append((p,'vendor/pythonclient/'+str(p.relative_to(sdk))))
manifest={name:hashlib.sha256(p.read_bytes()).hexdigest() for p,name in files}
(output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(output/'release.tar.gz','w:gz') as tar:
    for p,name in files:tar.add(p,arcname=name)
    tar.add(output/'manifest.json',arcname='manifest.json')
print(json.dumps({'files':len(files),'archive_sha256':hashlib.sha256((output/'release.tar.gz').read_bytes()).hexdigest()}))
