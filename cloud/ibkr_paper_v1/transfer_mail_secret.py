"""Transfer only the approved report sender key over the pinned personal SSH link.

Never source .env, print secrets, or copy other credentials. The caller must
explicitly authorize the destination and key using the command-line flag.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approve-resend-key-transfer-to-personal-cloud',action='store_true',required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    values=[]
    for line in (root/'.env').read_text().splitlines():
        m=re.fullmatch(r'\s*(?:export\s+)?TRADING_REPORT_RESEND_API_KEY\s*=\s*(.*?)\s*',line)
        if m:values.append(m[1].strip().strip('\"\''))
    if len(values)!=1 or not re.fullmatch(r're_[A-Za-z0-9_-]+',values[0]):
        raise SystemExit('Save one valid TRADING_REPORT_RESEND_API_KEY in .env; nothing transferred.')
    remote="""import json,os,sys,grp
from pathlib import Path
v=json.load(sys.stdin)
assert v['provider']=='resend' and v['api_key'].startswith('re_')
p=Path('/etc/ibkr-paper/smtp.json')
t=p.with_suffix('.tmp')
fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
with os.fdopen(fd,'w') as f: json.dump(v,f); f.flush(); os.fsync(f.fileno())
os.chown(t,0,grp.getgrnam('ibkr-paper').gr_gid)
os.chmod(t,0o640)
os.replace(t,p)
print('Report sender configured; key suppressed.')
"""
    import shlex
    command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',
        '-o','StrictHostKeyChecking=yes',
        '-o','UserKnownHostsFile='+str(root/'research/agentic_shadow_v1/deployment/personal-cloud-known-hosts'),
        '-o','IdentitiesOnly=yes','-i','/Users/pranavmulakala/.ssh/personal_trading_cloud',
        'root@198.211.113.234','python3 -c '+shlex.quote(remote)]
    result=subprocess.run(command,input=json.dumps({'provider':'resend','api_key':values[0]}).encode(),
                          capture_output=True,timeout=30)
    if result.returncode:
        raise SystemExit('Report credential transfer failed; private output suppressed.')
    print('Exactly one report sender key transferred to the verified personal server.')


if __name__=='__main__':main()
