"""Additional synthetic matrix at roughly $900/share; never forward evidence."""
from dataclasses import replace
import json
from cloud.forward_research import capital_replay
from cloud.test_research_loop import REPO
from research.lite_reversal_v1.test_experiment import bars,config

rows=bars('2026-09-09')
# A feasible post-retest open below the entry cap, without changing any rules.
rows[6]=replace(rows[6],o=97.9,l=97.9)
rows[8]=replace(rows[8],o=98.1,l=98.0)
scaled=[replace(b,**{k:getattr(b,k)*9 for k in ('o','h','l','c','vw')}) for b in rows]
policy=json.loads((REPO/'cloud/research_policy.json').read_text())['lite_forward']
result=capital_replay(config(),{'2026-09-09':scaled},{},['2026-09-09'],policy)
checks=[]
for name,run in result['results'].items():
    assert run['validation']['status']=='PASS'
    assert len(run['trades'])==1,(name,run['summary'])
    t=run['trades'][0];capital=run['summary']['initial_cash']
    assert t['quantity']>=1 and t['quantity'].is_integer()
    assert t['planned_risk']<=capital*.005+1e-8
    assert t['entry_debit']<=capital+1e-8
    checks.append({'scenario':name,'shares':t['quantity'],'planned_risk':t['planned_risk'],
                   'entry_debit':t['entry_debit'],'ledger':'PASS'})
print(json.dumps({'synthetic_only':True,'checks':checks},indent=2))
