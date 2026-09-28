"""Verification-only probe; never prints or reads credential contents."""
import json
from pathlib import Path
import socket

checks={}
try:
    with Path('/etc/trading-collector/credentials.json').open('rb'):
        checks['credentials_inaccessible']=False
except (PermissionError,FileNotFoundError): checks['credentials_inaccessible']=True
try:
    with socket.create_connection(('1.1.1.1',443),timeout=2): checks['network_disabled']=False
except OSError: checks['network_disabled']=True
try:
    # Opening a fresh marker, never an existing archive file, tests the read-only mount.
    with Path('/var/lib/trading-collector/research-write-probe').open('x'):
        checks['archive_read_only']=False
except (PermissionError,OSError): checks['archive_read_only']=True
print(json.dumps(checks))
if not all(checks.values()): raise SystemExit(1)
