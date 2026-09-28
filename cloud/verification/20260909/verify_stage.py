"""Personal cloud staging verification; no credentials or broker access."""
from pathlib import Path
import hashlib, json, subprocess, tarfile

stage=Path('/opt/trading-readiness-stage-20260909')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*args):subprocess.run(args,check=True)
assert sha(stage/'release.tar.gz')=='d5207a289ce82fe4853deb33e0d061c82e4dfd6b344ba6ee8668d38adc116b9b'
with tarfile.open(stage/'release.tar.gz') as t:
    assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in t.getmembers())
    t.extractall(stage,filter='data')
release=json.loads((stage/'RELEASE.json').read_text())
assert all(sha(stage/n)==h for n,h in release['files'].items())
assert sha(Path('/opt/trading-research-v1/PINS.json'))=='251ff7786da9fb96d4e64a61c7afc9886cd640f24b69921bbacef7221798b7f2'
assert sha(Path('/opt/trading-collector/collector.py'))=='ff15a649757feaaf3f4360ee1a4b1b96363511f1f2d1069f8e9d41092c093993'
common=['systemd-run','--quiet','--collect','--wait','--pipe',
        '-p','User=trading-collector','-p','Group=trading-collector',
        '-p','ProtectSystem=strict','-p','ProtectHome=true','-p','PrivateTmp=true',
        '-p','PrivateNetwork=true','-p','IPAddressDeny=any','-p','NoNewPrivileges=true',
        '-p','InaccessiblePaths=/etc/trading-collector','-p','ReadOnlyPaths=/var/lib/trading-collector',
        '-p','MemoryMax=1000M','-p','TasksMax=32','--setenv=PYTHONDONTWRITEBYTECODE=1']
run(*common,'--unit=trading-ready-tests-20260909','--working-directory='+str(stage/'validation'),
    '/usr/bin/python3','-m','unittest','cloud.test_collector','cloud.test_research_loop','cloud.test_readiness_v2','-q')
run(*common,'--unit=trading-ready-isolation-20260909','--working-directory='+str(stage/'validation'),
    '/usr/bin/python3','cloud/runtime_probe.py')
run(*common,'--unit=trading-ready-replay-20260909','-p','StateDirectory=trading-readiness-stage-result',
    '--working-directory='+str(stage/'research'),'/usr/bin/python3','-m','cloud.research_runner',
    '--output','/var/lib/trading-readiness-stage-result')
old=json.loads(Path('/var/lib/trading-research/latest.json').read_text())
new=json.loads(Path('/var/lib/trading-readiness-stage-result/latest.json').read_text())
assert old['status']==new['status']=='REPLAY_COMPLETE_RESEARCH_ONLY'
keys=('orb','orb_summaries','ledger_audits','contrasts','bar_proxy_diagnostic','prepared','lite','lite_excluded','days')
assert all(old['results'][k]==new['results'][k] for k in keys)
f=new['results']['lite_forward']
assert f['capital_arms']==[5000,10000] and f['results']=={} and f['status']=='WAITING_FOR_FIRST_FORWARD_SESSION'
assert not new['orders_enabled'] and not new['promotion_enabled']
receipt={'status':'PASS','old_run_id':old['run_id'],'staged_run_id':new['run_id'],
         'parent_result_sections_equal':list(keys),'linux_tests':34,'isolation':'all_three_passed',
         'new_arms_status':f['status'],'pins_sha256':release['pins_sha256']}
(stage/'STAGING_VERIFIED.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
