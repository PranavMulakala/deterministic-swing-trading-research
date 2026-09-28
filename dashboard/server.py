"""Loopback-only research dashboard. Browser has no SSH or broker credentials."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from dashboard.catalog import catalog, NOTES, REPO

ROOT=Path(__file__).resolve().parent
HOST='198.211.113.234'
FINGERPRINT='SHA256:fy4i90RRjUZAz1pCNrkMDqFlKL1cydddD3ub5rlw7MI'
STATE=ROOT/'state'

def verify_host(path):
    result=subprocess.run(['ssh-keygen','-lf',str(path)],capture_output=True,text=True,timeout=5,check=True)
    fingerprints=[line.split()[1] for line in result.stdout.splitlines()]
    if fingerprints != [FINGERPRINT]: raise ValueError('Untrusted SSH host fingerprint')

def fetch_snapshot(known_hosts, key):
    verify_host(known_hosts)
    cmd=['ssh','-F','/dev/null','-i',str(key),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
         '-o','UserKnownHostsFile='+str(known_hosts),'-o','ConnectTimeout=12','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2',
         'root@'+HOST,'python3 -']
    proc=subprocess.run(cmd,input=(ROOT/'remote_snapshot.py').read_bytes(),capture_output=True,timeout=90)
    if proc.returncode: raise RuntimeError('SSH read failed; check connectivity and trusted host access')
    if len(proc.stdout)>64*1024*1024: raise ValueError('Snapshot exceeds dashboard size limit')
    result=json.loads(proc.stdout)
    if result.get('schema_version')!=1: raise ValueError('Unsupported snapshot schema')
    return result

class Store:
    def __init__(self, fetch, interval=60):
        self.fetch=fetch; self.interval=interval; self.lock=threading.Lock(); self.stop=threading.Event()
        self.data=None; self.error=None; self.attempt=None
    def refresh(self):
        try:
            data=self.fetch()
            with self.lock:self.data=data; self.error=None
        except Exception as exc:
            # Only error class; arbitrary remote output and secrets never enter browser responses.
            with self.lock:self.error=type(exc).__name__+': refresh failed. Last successful snapshot retained.'
        finally:
            with self.lock:self.attempt=datetime.now(timezone.utc).isoformat()
    def run(self):
        while not self.stop.is_set():
            self.refresh(); self.stop.wait(self.interval)
    def response(self):
        with self.lock:return {'data':self.data,'connection':{'error':self.error,'last_attempt':self.attempt,'refresh_seconds':self.interval}}

def handler(store):
    local_catalog=catalog()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
                self.send_error(403);return
            if self.headers.get('Sec-Fetch-Site')=='cross-site':self.send_error(403);return
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
                self.send_error(403);return
            path=self.path.split('?',1)[0]
            if path=='/api/snapshot':
                raw=json.dumps(store.response(),allow_nan=False).encode(); content='application/json'
            elif path=='/api/catalog':
                raw=json.dumps(local_catalog,allow_nan=False).encode();content='application/json'
            elif path.startswith('/research-notes/') and path.removeprefix('/research-notes/') in NOTES:
                raw=(REPO/NOTES[path.removeprefix('/research-notes/')]).read_bytes();content='text/plain'
            elif path in ('/','/app.js','/style.css'):
                file={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
                raw=(ROOT/'static'/file).read_bytes();content={'/':'text/html','/app.js':'text/javascript','/style.css':'text/css'}[path]
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',content+'; charset=utf-8')
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def log_message(self,*args):pass
    return Handler

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--known-hosts',type=Path,default=STATE/'known_hosts')
    parser.add_argument('--key',type=Path,default=Path.home()/'.ssh/personal_trading_cloud')
    parser.add_argument('--cloud-local',action='store_true',help='Read existing research files on this host; no SSH or credentials')
    args=parser.parse_args()
    if args.cloud_local:
        from dashboard.remote_snapshot import snapshot
        store=Store(snapshot)
    else:
        verify_host(args.known_hosts)
        store=Store(lambda:fetch_snapshot(args.known_hosts,args.key))
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(store))
    threading.Thread(target=store.run,daemon=True).start()
    print(f'Research dashboard: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:store.stop.set();server.server_close()

if __name__=='__main__':main()
