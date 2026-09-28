"""Build a minimal offline source bundle plus verified warmup; never credentials."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from research.orb_comparison_v1 import engine as e

ROOT = Path(__file__).resolve().parents[1]
FILES = [
 'research/orb_comparison_v1/engine.py', 'research/orb_comparison_v1/verify.py',
 'research/orb_comparison_v1/run.py', 'research/orb_comparison_v1/spec.json',
 'research/orb_quote_v2/common.py', 'research/orb_quote_v2/engine.py',
 'research/orb_quote_v2/run.py', 'research/orb_quote_v2/execution.json',
 'research/orb_direct_breakout_v1/__init__.py', 'research/orb_direct_breakout_v1/engine.py',
 'research/orb_direct_breakout_v1/config.json', 'research/orb_direct_breakout_v1/PROTOCOL.md',
 'research/orb_direct_breakout_v1/FREEZE.json',
 'research/lite_execution_data/quotes.py', 'research/lite_reversal_v1/experiment.py',
 'research/lite_reversal_v1/config.json', 'cloud/research_policy.json',
 'cloud/news_context_v1.json', 'cloud/research_archive.py', 'cloud/readiness.py', 'cloud/forward_research.py',
 'cloud/research_runner.py', 'cloud/learning.py', 'cloud/SEPTEMBER9_FREEZE.md']

def build(target):
    target = Path(target)
    target.mkdir(parents=True,exist_ok=False)
    folder = ROOT/'research/orb_comparison_v1/runs/sip-20260907-02'
    spec, sessions, bars, _ = e.load(folder)
    days = list(sessions)[-20:]
    value = {'sessions':{d:[t.isoformat() for t in sessions[d]] for d in days},
             'bars':{s:{d:[bars[s,5][d][t] for t in sorted(bars[s,5][d])] for d in days} for s in spec['symbols']},
             'source_manifest_sha256':e.verify.sha(folder/'manifest.json'), 'label':'verified_frozen_warmup_only'}
    pins={}
    for name in FILES:
        dest=target/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest)
        pins[name]=hashlib.sha256(dest.read_bytes()).hexdigest()
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
    (target/'warmup.json').write_bytes(raw)
    pins['warmup.json']=hashlib.sha256(raw).hexdigest()
    (target/'PINS.json').write_text(json.dumps(pins,sort_keys=True,indent=2)+'\n')
    archive=target.with_suffix('.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:
        for path in sorted(target.rglob('*')):
            if path.is_file(): tar.add(path,arcname=path.relative_to(target))
    print(json.dumps({'archive':str(archive),'files':len(pins),'warmup_sessions':len(days)}))

if __name__ == '__main__':
    import sys
    build(sys.argv[1])
