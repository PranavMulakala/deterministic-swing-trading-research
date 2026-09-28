"""Copy only the hash-verified public calendar reference into paper isolation."""
import hashlib
import json
from pathlib import Path
import os

source=Path('/var/lib/trading-collector/references')
target=Path('/var/lib/ibkr-paper/references')
index=json.loads((source/'latest.json').read_text())
name=index['file']
if Path(name).name != name:
    raise ValueError('unsafe_reference_name')
raw=(source/name).read_bytes()
if hashlib.sha256(raw).hexdigest()!=index['sha256']:
    raise ValueError('reference_hash_mismatch')
data=json.loads(raw)
# Do not copy unrelated corporate actions or credentials.
content=(json.dumps({'calendar':data['calendar'],'fetched_at':data['fetched_at']},sort_keys=True)+'\n').encode()
digest=hashlib.sha256(content).hexdigest()
target.mkdir(mode=0o755,parents=True,exist_ok=True)
(target/(digest+'.json')).write_bytes(content)
os.chmod(target/(digest+'.json'),0o644)
tmp=target/'latest.tmp'
tmp.write_text(json.dumps({'file':digest+'.json','sha256':digest})+'\n')
os.chmod(tmp,0o644)
tmp.replace(target/'latest.json')
print('Public research calendar mirrored; no credentials copied.')
