from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parent
manifest=json.loads((root/'RELEASE.json').read_text())
for name,expected in manifest['files'].items():
    p=root/name
    if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
        raise SystemExit('Shadow release integrity failure')
print('Shadow release verified:',manifest['revision'])
