"""Offline capital diagnosis. No network, account, credential or order capability."""
import argparse
from dataclasses import asdict, replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from research.lite_reversal_v1 import experiment as e
from research.lite_execution_data import study

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CAPITALS=(500,5000,10000)
VARIANTS=('dip','vwap_retest')
COSTS=(10,25)
def D(value):
    result=Decimal(str(value))
    if not result.is_finite():raise ValueError('Nonfinite accounting value')
    return result

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def close(a,b):
    if not a.is_finite() or not b.is_finite() or abs(a-b)>Decimal('0.0000001'):
        raise ValueError('Independent accounting mismatch')

def audit(run,capital,risk_fraction):
    """No call to the engine validator; reconstruct every debit, credit and day."""
    cash=D(capital);indexed={t['date']:t for t in run['trades']}
    days=[r['date'] for r in run['daily_ledger']]
    if len(indexed)!=len(run['trades']) or days!=sorted(set(days)) or set(indexed)-set(days):
        raise ValueError('Duplicate, unordered or orphan ledger records')
    for row in run['daily_ledger']:
        trade=indexed.get(row['date'])
        if (row['status']=='filled')!=(trade is not None):raise ValueError('Missing trade/status')
        if trade:
            qty=D(trade['quantity']);debit=qty*D(trade['entry_all_in']);credit=qty*D(trade['exit_net'])
            cost=D(run['cost_bps_per_side'])/D(10000)
            if not qty.is_finite() or qty<=0 or qty!=qty.to_integral_value():raise ValueError('Whole shares required')
            if D(trade['planned_risk'])<=0 or D(trade['entry_all_in'])>D(trade['entry_cap'])+D('0.0000001'):
                raise ValueError('Invalid planned risk or entry cap')
            close(D(trade['entry_all_in']),D(trade['raw_entry'])*(1+cost))
            close(D(trade['exit_net']),D(trade['raw_exit'])*(1-cost))
            close(D(trade['planned_risk']),qty*(D(trade['entry_cap'])-D(trade['stop'])*(1-cost)))
            if debit>cash+Decimal('0.0000001') or D(trade['planned_risk'])>cash*D(risk_fraction)+Decimal('0.0000001'):
                raise ValueError('Cash or planned-risk breach')
            close(D(trade['equity_before']),cash)
            close(D(trade['entry_debit']),debit);close(D(trade['exit_credit']),credit)
            close(D(trade['pnl']),credit-debit)
            close(D(trade['gross_pnl']),qty*(D(trade['raw_exit'])-D(trade['raw_entry'])))
            close(D(trade['modeled_costs']),D(trade['gross_pnl'])-D(trade['pnl']))
            cash+=credit-debit
            close(D(trade['equity_after']),cash);close(D(row['pnl']),D(trade['pnl']))
        else:close(D(row['pnl']),D(0))
        close(D(row['equity']),cash)
    close(D(run['summary']['final_cash']),cash)
    close(D(run['summary']['net_pnl']),cash-D(capital))
    if run['summary']['trades']!=len(indexed):raise ValueError('Trade count mismatch')
    return {'status':'PASS','days_checked':len(days),'trades_checked':len(indexed),'ending_cash':str(cash)}

def capital_config(parent,capital):
    if type(capital) is not int or capital not in CAPITALS:raise ValueError('Outside fixed capital matrix')
    cfg=replace(parent,initial_cash=capital)
    if {k:v for k,v in asdict(cfg).items() if k!='initial_cash'}!={k:v for k,v in asdict(parent).items() if k!='initial_cash'}:
        raise ValueError('Unexpected rule change')
    return cfg

def matrix(fives,minutes,parent):
    if list(fives)!=sorted(fives) or not fives:raise ValueError('Missing/unsorted sessions')
    if minutes is not None and list(fives)!=list(minutes):raise ValueError('Unmatched execution dates')
    results={}
    for capital in CAPITALS:
        cfg=capital_config(parent,capital)
        for variant in VARIANTS:
            for cost in COSTS:
                run=(e.run_variant(fives,cfg,variant,cost,'whole') if minutes is None else
                     study.run_minute(fives,minutes,cfg,variant,cost,'whole'))
                run['independent_accounting']=audit(run,capital,cfg.risk_fraction)
                run['initial_cash']=capital
                results[f'{capital}_{variant}_{cost}bps']=run
    return results

def render(result):
    lines=['# Historical LITE capital diagnosis','',
           '**Research-only. Previously studied 2026 data; no live-trading approval.**','',
           'Only starting capital changes. Whole shares, original rules, every cost/style shown.','']
    for label,runs in result['scenarios'].items():
        lines += ['## '+label,'','| Scenario | Sessions | Trades | Ending cash | Net P&L | Win rate |',
                  '|---|---:|---:|---:|---:|---:|']
        for name,run in runs.items():
            s=run['summary'];win='unknown' if s['win_rate'] is None else f"{s['win_rate']:.1%}"
            lines.append(f"| {name} | {len(run['daily_ledger'])} | {s['trades']} | ${s['final_cash']:,.2f} | ${s['net_pnl']:,.2f} | {win} |")
        lines.append('')
    lines += ['## Interpretation boundaries','',
              'Matched one-/five-minute cases use the identical date intersection. Full and matched periods must not be conflated.',
              'More capital removes some sizing failures; it does not repair negative expectancy or unknown live fills.',
              'All ledgers independently reconcile. This is accounting verification, not proof of a profitable strategy.',
              'No parameters were searched or promoted. September 9 forward portfolios and cloud services are untouched.','']
    return '\n'.join(lines)

def run(output):
    output=Path(output)
    if output.exists():raise FileExistsError('Choose a new immutable output directory')
    pins=json.loads((HERE/'INPUT_PINS.json').read_text())
    for name,h in pins.items():
        if (ROOT/name).is_symlink() or sha(ROOT/name)!=h:raise ValueError('Frozen input changed: '+name)
    parent=e.Config(**json.loads((e.HERE/'config.json').read_text()))
    original=json.loads((ROOT/'research/lite_2026/snapshot.json').read_text())
    calendar=original['calendar']
    if calendar[0]['date']!='2026-01-02' or calendar[-1]['date']!='2026-09-04' or len(calendar)!=170:
        raise ValueError('Unexpected diagnostic period')
    data=ROOT/'research/lite_execution_data/runs/sip-bars-01'
    five,c5=study.load_bars(data/'LITE_5Min.json','LITE',5,calendar)
    one,c1=study.load_bars(data/'LITE_1Min.json','LITE',1,calendar)
    joint={d:five[d] for d in five if d in one}
    minutes={d:one[d] for d in joint}
    if len(five)!=170 or len(joint)!=140:raise ValueError('Unexpected pinned coverage')
    result={'id':'lite-historical-capital-diagnosis-v1','unseen_test':False,'broker_orders':False,
            'changes':'initial_cash_only','capital_arms':list(CAPITALS),'live_pilot_verdict':'NO_GO',
            'live_pilot_blockers':['historical_development_data_not_unseen','live_fill_and_latency_not_validated'],
            'coverage':{'five':c5,'one':c1,'matched_dates':list(joint)},
            'provenance':{'inputs':pins,'protocol_sha256':sha(HERE/'PROTOCOL.md'),'runner_sha256':sha(Path(__file__))},
            'scenarios':{'full_5min':matrix(five,None,parent),'matched_5min':matrix(joint,None,parent),
                         'matched_1min':matrix(joint,minutes,parent)}}
    # Confirm source files did not change while evaluation was running.
    if any(sha(ROOT/n)!=h for n,h in pins.items()):raise ValueError('Inputs changed during run')
    raw=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n'
    report=render(result)
    output.mkdir(parents=True,exist_ok=False)
    with (output/'results.json').open('x') as f:f.write(raw)
    with (output/'REPORT.md').open('x') as f:f.write(report)
    with (output/'MANIFEST.json').open('x') as f:json.dump({n:sha(output/n) for n in ('results.json','REPORT.md')},f,indent=2)
    print(json.dumps({'output':str(output),'scenarios':sum(len(r) for r in result['scenarios'].values()),
                      'days_checked':sum(r['independent_accounting']['days_checked'] for v in result['scenarios'].values() for r in v.values()),
                      'trades_checked':sum(r['independent_accounting']['trades_checked'] for v in result['scenarios'].values() for r in v.values()),
                      'sha256':sha(output/'results.json')}))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
