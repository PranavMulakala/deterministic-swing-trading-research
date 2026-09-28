from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parent
manifest=json.loads((root/'RELEASE.json').read_text())
actual_revision=hashlib.sha256(json.dumps(manifest['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
if actual_revision != manifest['revision'] or manifest.get('orders') is not False:
    raise SystemExit('Shadow manifest identity failure')
for name,expected in manifest['files'].items():
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise SystemExit('Invalid release path')
    p=root/name
    if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
        raise SystemExit('Shadow release integrity failure')
print('Shadow release verified:',manifest['revision'])
