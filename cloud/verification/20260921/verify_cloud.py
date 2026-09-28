"""Read-only post-deployment checks; no broker access or service changes."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

def read(path):
    return json.loads(Path(path).read_text())

units = ['trading-collector', 'trading-research', 'trading-dashboard',
         'agentic-stock-free-provider', 'agentic-stock-free-runtime',
         'trading-shadow-7500', 'trading-shadow-indicative-producer',
         'agentic-paper-runtime']
states = {}
for unit in units:
    raw = subprocess.check_output(['systemctl','show',unit+'.service',
        '-p','ActiveState','-p','Result','-p','ExecMainStartTimestamp',
        '-p','ExecMainExitTimestamp','-p','ExecMainStatus'],text=True)
    states[unit] = dict(row.split('=',1) for row in raw.splitlines() if '=' in row)
with urlopen('http://127.0.0.1:8766/api/snapshot', timeout=20) as response:
    envelope = json.load(response)
data = envelope['data']
assert data, envelope['connection']
assert envelope['connection']['error'] is None
verification = data['verification']
assert verification['manifest_matches_deployment']
assert not verification['pin_mismatches']
assert verification['artifact']['index_hash_matches']
assert verification['artifact']['latest_results_match']
assert data['stock_trial']['orders_enabled'] is False
latest = read('/var/lib/trading-research/latest.json')
stock = read('/var/lib/agentic-stock-free-runtime/status.json')
provider = read('/var/lib/agentic-stock-free-input/status.json')
combined = read('/var/lib/agentic-paper-runtime/status.json')
output = {
    'checked_at': datetime.now(timezone.utc).isoformat(),
    'services': states,
    'dashboard': {'connection':envelope['connection'],'fetched_at':data['fetched_at'],
                  'verification':verification,'stock_status':data['stock_trial']['status']},
    'collector':data['health'], 'streams':data['streams'],
    'research':{'status':latest['status'],'checked_at':latest.get('checked_at'),
                'days':latest.get('results',{}).get('days'),
                'result_keys':list(latest.get('results',{})),
                'etf_swing':latest.get('results',{}).get('etf_swing'),
                'lite_forward':latest.get('results',{}).get('lite_forward'),
                'news_context_status':latest.get('results',{}).get('news_context_status'),
                'orb':latest.get('results',{}).get('orb_summaries'),
                'challenger':latest.get('results',{}).get('orb_challenger',{}).get('summaries')},
    'stock':stock,'provider':provider,
    'combined': {k:combined.get(k) for k in ('status','reason','reasons','checked_at','orders_enabled')},
}
print(json.dumps(output,sort_keys=True))
