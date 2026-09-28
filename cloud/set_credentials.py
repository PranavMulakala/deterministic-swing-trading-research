"""Run as root on the server. Hidden interactive input; never paste secrets in chat."""
import getpass
import grp
import json
import os
import sys
from pathlib import Path

def main():
    if sys.argv[1:] == ['--stdin']:
        values = json.loads(sys.stdin.read(8192))
        if set(values) != {'key', 'secret'}:
            raise SystemExit('Invalid credential fields')
        key, secret = values['key'].strip(), values['secret'].strip()
    elif not sys.argv[1:]:
        key = getpass.getpass('Fresh Alpaca PAPER key (hidden): ').strip()
        secret = getpass.getpass('Fresh Alpaca PAPER secret (hidden): ').strip()
    else:
        raise SystemExit('Unexpected arguments')
    if not key.startswith('PK') or not secret:
        raise SystemExit('Expected paper key starting PK and nonempty secret; nothing saved')
    folder = Path('/etc/trading-collector')
    tmp = folder / 'credentials.new'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump({'key': key, 'secret': secret}, f)
        f.flush()
        os.fsync(f.fileno())
    os.chown(tmp, 0, grp.getgrnam('trading-collector').gr_gid)
    os.chmod(tmp, 0o640)
    tmp.replace(folder / 'credentials.json')
    print('Paper credentials saved privately. No broker request made.')

if __name__ == '__main__':
    main()
