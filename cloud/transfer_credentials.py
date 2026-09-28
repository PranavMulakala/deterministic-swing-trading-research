"""Owner-authorized transfer of exactly two local paper secrets over pinned SSH."""
import json
import os
from pathlib import Path
import subprocess
from swingbot.paper_cli import _load_env

def main():
    names = ('ALPACA_PAPER_API_KEY', 'ALPACA_PAPER_API_SECRET')
    for name in names:
        os.environ.pop(name, None)
    _load_env(Path(__file__).resolve().parents[1] / '.env')
    values = dict(zip(('key', 'secret'), (os.environ.get(n, '') for n in names)))
    if not values['key'].startswith('PK') or not values['secret']:
        raise SystemExit('Missing local paper credentials; nothing transferred')
    command = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
               '-o', 'StrictHostKeyChecking=yes',
               '-o', 'UserKnownHostsFile=/private/tmp/trading-cloud-verified-host',
               '-o', 'IdentitiesOnly=yes', '-i',
               '/Users/pranavmulakala/.ssh/personal_trading_cloud',
               'root@198.211.113.234',
               'python3 /opt/trading-collector/set_credentials.py --stdin']
    result = subprocess.run(command, input=json.dumps(values).encode(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if result.returncode:
        raise SystemExit('Credential transfer failed; remote output suppressed')
    print('Exactly two paper credentials transferred over verified SSH; values suppressed.')

if __name__ == '__main__':
    main()
