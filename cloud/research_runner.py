"""Offline scheduled forward research. Frozen rules, delayed data, no network/orders."""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from zoneinfo import ZoneInfo

from cloud.research_archive import Archive, DataGap, nanos, NS
from cloud.learning import review
from cloud.readiness import assess as assess_readiness
from cloud.forward_research import capital_replay, context_news, available_context
from research.orb_comparison_v1 import engine as bar_engine
from research.orb_comparison_v1.run import audit_ledger, stats, paired
from research.orb_quote_v2 import engine as tick_engine
from research.orb_quote_v2.common import key, Quotes, screen, signals, D
from research.orb_quote_v2.run import audit, summary
from research.orb_direct_breakout_v1 import engine as direct_engine
from research.lite_reversal_v1 import experiment as lite_engine

NY=ZoneInfo('America/New_York')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def encoded(value): return json.dumps(value,sort_keys=True,separators=(',',':'),default=bar_engine.encode,allow_nan=False)

def atomic(path, value):
    path=Path(path)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(encoded(value)+'\n')
    tmp.replace(path)

def verify_pins(root):
    pins=json.loads((root/'PINS.json').read_text())
    for name,digest in pins.items():
        path=root/name
        if path.is_symlink() or sha(path)!=digest: raise DataGap('frozen_dependency_changed:'+name)
    return sha(root/'PINS.json')

def references(folder,asof):
    pin=json.loads((folder/'references/latest.json').read_text())
    name=pin['file']
    if Path(name).name!=name: raise DataGap('invalid_reference_path')
    path=folder/'references'/name
    if sha(path)!=pin['sha256']: raise DataGap('reference_hash_mismatch')
    value=json.loads(path.read_text())
    age=asof-nanos(value['fetched_at'])/NS
    if not 0<=age<=36*3600: raise DataGap('stale_reference_data')
    if value['query']['start']>'2026-07-01' or value['query']['end']<'2026-12-31': raise DataGap('reference_interval_incomplete')
    return value,pin['sha256']

def corporate_actions(reference,symbols):
    dates={s:set() for s in symbols}
    pages=reference['actions']
    if not pages or pages[-1].get('next_page_token') is not None: raise DataGap('actions_incomplete')
    for page in pages:
        for kind,rows in page['corporate_actions'].items():
            if not isinstance(rows,list): raise DataGap('invalid_actions')
            if kind=='cash_dividends': continue
            for row in rows:
                symbol=row.get('symbol')
                day=row.get('ex_date') or row.get('effective_date')
                if not symbol or not day: raise DataGap('unsupported_action_schema')
                datetime.strptime(day,'%Y-%m-%d')
                if symbol in dates: dates[symbol].add(day)
    return dates

def grouped(rows,start,end,step):
    result={}
    for row in rows:
        t=datetime.fromisoformat(row['t'].replace('Z','+00:00')).astimezone(NY)
        if not start<=t<end: continue
        if t.second or t.microsecond or t.minute%step: raise DataGap('unaligned_bar')
        for field in ('o','h','l','c','v','vw'):
            x=D(row[field])
            if not x.is_finite() or x<=0: raise DataGap('invalid_bar_value')
        if D(row['h'])<max(D(row['o']),D(row['c'])) or D(row['l'])>min(D(row['o']),D(row['c'])): raise DataGap('invalid_OHLC')
        if t in result and result[t]!=row: raise DataGap('conflicting_bars')
        result[t]=row
    return result

class TickStreams:
    def __init__(self,archive,features,policy):
        self.archive=archive
        self.features={key(f):f for f in signals(features)}
        self.cap=policy['max_selected_tick_rows_per_session']
        self.count=0
        self.day=None
    def __contains__(self,k): return k in self.features
    def __getitem__(self,k):
        f=self.features[k]
        if f['day']!=self.day: self.count=0; self.day=f['day']
        start=nanos(f['pattern']['time'])-NS
        end=nanos(datetime.fromisoformat(f['pattern']['time']).replace(hour=15,minute=56,second=0,microsecond=0).isoformat())+1
        payload={}
        for kind in ('quotes','trades'):
            rows=self.archive.ticks(f['symbol'],kind,start,end,self.cap-self.count)
            self.count+=len(rows)
            if self.count>self.cap: raise DataGap('execution_tick_memory_budget')
            payload[kind]={'rows':rows}
        return payload

def replay_data(root,archive,reference,policy,days):
    parent=json.loads((root/'research/orb_comparison_v1/spec.json').read_text())
    spec=deepcopy(parent)
    spec['evaluation_start']=policy['start']; spec['evaluation_end']=days[-1]
    # Only the evaluation date range changes; all original selection/entry/risk values remain.
    assert {k:v for k,v in spec.items() if not k.startswith('evaluation_')}=={k:v for k,v in parent.items() if not k.startswith('evaluation_')}
    cfg=json.loads((root/'research/orb_quote_v2/execution.json').read_text())
    warm=json.loads((root/'warmup.json').read_text())
    calendar=bar_engine.verify.calendar_sessions(reference['calendar'])
    sessions={d:tuple(datetime.fromisoformat(t) for t in pair) for d,pair in warm['sessions'].items()}
    sessions.update({d:calendar[d] for d in days})
    sessions=dict(sorted(sessions.items()))
    # Ensure the bootstrap and forward span do not hide any intervening session.
    expected=[d for d in calendar if min(sessions)<=d<=days[-1]]
    if expected!=list(sessions): raise DataGap('calendar_warmup_gap')
    bars={(s,m):{} for s in spec['symbols'] for m in (1,5)}
    for s in spec['symbols']:
        for d,rows in warm['bars'][s].items():
            bars[s,5][d]=grouped(rows,*sessions[d],5)
        for d in days:
            start,end=sessions[d]
            for step in (1,5):
                rows=archive.bars(s,nanos(start.isoformat()),nanos(end.isoformat()),step==5)
                bars[s,step][d]=grouped(rows,start,end,step)
    actions=corporate_actions(reference,spec['symbols'])
    prepared=bar_engine.prepare(spec,sessions,bars,actions)
    prepared=json.loads(encoded(prepared))
    entries={}
    for f in signals(prepared):
        t=nanos(f['pattern']['time'])
        entries[key(f)]={'rows':archive.ticks(f['symbol'],'quotes',t-NS,t+2*NS+1,100000)}
    orb={}; summaries={}; audits={}; contrasts={}
    for delay in policy['orb']['delay_seconds']:
        for cost in policy['orb']['cost_bps']:
            pair=[]
            for arm in policy['orb']['arms']:
                label=f'{delay}s_{cost}bps_{arm}'
                streams=TickStreams(archive,prepared,policy)
                result=tick_engine.replay(spec,cfg,prepared,entries,streams,arm,cost,delay)
                audits[label]=audit(result,spec,cfg)
                orb[label]=result
                summaries[label]=summary(result)
                pair.append(result)
            contrasts[f'{delay}s_{cost}bps']=paired(*pair,spec)
    # Retain the earlier bar execution model as a diagnostic, never pool it with tick PnL.
    bar_results={}
    original_prepared=bar_engine.prepare(spec,sessions,bars,actions)
    for cost in policy['orb']['cost_bps']:
        for arm in policy['orb']['arms']:
            result=bar_engine.replay(spec,sessions,bars,original_prepared,arm,cost)
            bar_results[f'{cost}bps_{arm}']={'summary':stats(result),'audit':audit_ledger(result,spec), 'ledger':result}
    challenger_config=json.loads((root/policy['orb_challenger']['config']).read_text())
    if (challenger_config['prospective_start']!=policy['orb_challenger']['start']
            or challenger_config['arms']!=policy['orb_challenger']['arms']
            or challenger_config['delay_seconds']!=policy['orb_challenger']['delay_seconds']
            or challenger_config['cost_bps']!=policy['orb_challenger']['cost_bps']
            or challenger_config['orders_enabled'] is not False
            or challenger_config['promotion_enabled'] is not False):
        raise DataGap('direct_challenger_policy_mismatch')
    # All tick consumers require ISO strings, including the direct challenger.
    # Match the serialization boundary already used for the parent experiment.
    direct_all=direct_engine.prepare(spec,sessions,bars,actions)
    direct_engine.assert_only_pattern_changed(original_prepared,direct_all)
    direct_all=json.loads(encoded(direct_all))
    direct_days=[day for day in days if day>=challenger_config['prospective_start']]
    challenger={
        'id':challenger_config['id'],
        'status':'WAITING_FOR_FIRST_PROSPECTIVE_SESSION',
        'prospective_start':challenger_config['prospective_start'],
        'days':direct_days,
        'rule_change':challenger_config['entry_change_only'],
        'orders_enabled':False,
        'promotion_enabled':False,
        'scenarios':{},
        'summaries':{},
        'audits':{},
        'contrasts':{},
    }
    if direct_days:
        direct_prepared={day:direct_all[day] for day in direct_days}
        direct_entries={}
        for feature in signals(direct_prepared):
            signal=nanos(feature['pattern']['time'])
            direct_entries[key(feature)]={
                'rows':archive.ticks(feature['symbol'],'quotes',signal-NS,signal+2*NS+1,100000)
            }
        scenarios={}; challenger_summaries={}; challenger_audits={}; challenger_contrasts={}
        for delay in policy['orb_challenger']['delay_seconds']:
            for cost in policy['orb_challenger']['cost_bps']:
                pair=[]
                for arm in policy['orb_challenger']['arms']:
                    label=f'{delay}s_{cost}bps_{arm}'
                    streams=TickStreams(archive,direct_prepared,policy)
                    result=tick_engine.replay(spec,cfg,direct_prepared,direct_entries,streams,arm,cost,delay)
                    challenger_audits[label]=audit(result,spec,cfg)
                    scenarios[label]=result
                    challenger_summaries[label]=summary(result)
                    pair.append(result)
                challenger_contrasts[f'{delay}s_{cost}bps']=paired(*pair,spec)
        challenger.update(status='REPLAY_COMPLETE_RESEARCH_ONLY',scenarios=scenarios,
                          summaries=challenger_summaries,audits=challenger_audits,
                          contrasts=challenger_contrasts)
    lite={}; included={}; excluded={}
    for d in days:
        rows=bars['LITE',5][d]
        if not bar_engine.full(rows,*sessions[d]) or sessions[d][1].strftime('%H:%M')!='16:00' or d in actions['LITE']:
            excluded[d]='incomplete_session_or_action'
        else:
            included[d]=[lite_engine.Bar(t,*(float(rows[t][k]) for k in ('o','h','l','c','v','vw'))) for t in sorted(rows)]
    lc=lite_engine.Config(**json.loads((root/'research/lite_reversal_v1/config.json').read_text()))
    if not excluded:
        for variant in policy['lite']['variants']:
            for cost in policy['lite']['cost_bps']:
                lite[f'{variant}_{cost}bps']=lite_engine.run_variant(included,lc,variant,cost,policy['lite']['mode'])
    lite_forward=capital_replay(lc,included,excluded,days,policy['lite_forward'])
    news=[]; news_status='metadata_only_not_used_for_selection'
    try:
        for d in days:
            start,end=sessions[d]
            news.extend(archive.news(nanos(start.isoformat()),nanos(end.isoformat())))
    except DataGap:
        news_status='unknown_incomplete_collection_not_neutral'
    context_config=json.loads((root/policy['news']['context_config']).read_text())
    if context_config['collection_start'][:10]!=policy['news']['context_start'] or context_config['selection_or_execution_use']:
        raise DataGap('invalid_news_context_config')
    context,context_statuses=context_news(archive,context_config,sessions,days)
    context_status=('not_started_prospective' if not context_statuses else
                    'unknown_incomplete_collection_not_neutral' if any(s.startswith('unknown') for s in context_statuses.values())
                    else 'metadata_only_not_used_for_selection')
    annotations=[]
    for f in signals(prepared):
        at_signal=[n for n in news if f['symbol'] in n['symbols'] and nanos(n['first_received_at'])<=nanos(f['pattern']['time'])]
        annotations.append({'day':f['day'],'symbol':f['symbol'],'signal_time':f['pattern']['time'],
                            'news_items_observed_before_signal':len(at_signal) if not news_status.startswith('unknown') else None,
                            **available_context(context,context_statuses,f,context_config),
                            'news_used':False})
    return {'orb':orb,'orb_summaries':summaries,'ledger_audits':audits,'contrasts':contrasts,
            'orb_challenger':challenger,
            'bar_proxy_diagnostic':bar_results,'prepared':prepared,'lite':lite,'lite_forward':lite_forward,'lite_excluded':excluded,
            'lite_input_label':policy['lite']['input_label'],'news_status':news_status,'news_annotations':annotations,
            'news_context_status':context_status,'news_context_days':context_statuses,
            'news_context_versions':{d:len(rows) if not context_statuses[d].startswith('unknown') else None for d,rows in context.items()},
            'etf_swing':{'status':'BLOCKED_DAILY_DATA_PARITY','reason':'No adjusted daily warmup/forward feed equivalence; no fabricated ETF performance'},
            'days':days,'source_digest':archive.source_digest()}

def execute(root, archive_folder, output, asof=None):
    root=Path(root); archive_folder=Path(archive_folder); output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    asof=time.time() if asof is None else asof
    with (output/'runner.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        pins=verify_pins(root)
        policy=json.loads((root/'cloud/research_policy.json').read_text())
        checked=datetime.fromtimestamp(asof,timezone.utc).isoformat()
        readiness=assess_readiness(archive_folder,policy,asof)
        base={'checked_at':checked,'policy':policy['id'],'code_pins_sha256':pins,
              'orders_enabled':False,'promotion_enabled':False,'mode':policy['mode']}
        base['session_readiness']=readiness
        try:
            reference,refhash=references(archive_folder,asof)
            calendar=bar_engine.verify.calendar_sessions(reference['calendar'])
            today=datetime.fromtimestamp(asof,NY).date().isoformat()
            if today>policy['end']: raise DataGap('preregistered_window_expired')
            days=[d for d,(_,end) in calendar.items() if policy['start']<=d<=policy['end'] and end.timestamp()+1200<=asof]
            if not days:
                result={**base,'status':'WAITING_FOR_FIRST_COMPLETED_SESSION',
                        'first_session':policy['start'],'learning':'no_outcomes_no_improvement_claim',
                        'etf_swing':'BLOCKED_DAILY_DATA_PARITY'}
            else:
                arc=Archive(archive_folder,asof)
                try:
                    payload=replay_data(root,arc,reference,policy,days)
                finally: arc.close()
                learning=review(payload['orb'],payload['lite'],policy,days,payload['source_digest'])
                material={'pins':pins,'references':refhash,'source_digest':payload['source_digest'],'days':days}
                run_id=hashlib.sha256(encoded(material).encode()).hexdigest()
                result={**base,'status':'REPLAY_COMPLETE_RESEARCH_ONLY','run_id':run_id,
                        'provenance':material,'results':payload,'learning':learning}
                folder=output/'runs'
                folder.mkdir(exist_ok=True)
                artifact=folder/(run_id+'.json')
                if not artifact.exists():
                    temp=artifact.with_suffix('.tmp')
                    with temp.open('w') as f:
                        f.write(encoded(result)+'\n'); f.flush(); os.fsync(f.fileno())
                    os.link(temp,artifact)
                    temp.unlink()
                else:
                    prior=json.loads(artifact.read_text())
                    if encoded(prior['results'])!=encoded(payload) or prior['learning']!=json.loads(encoded(learning)):
                        raise DataGap('same_inputs_nonreproducible_results')
                memory=sqlite3.connect(output/'memory.sqlite')
                try:
                    memory.executescript('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, last_day TEXT, artifact TEXT, sha256 TEXT); CREATE TABLE IF NOT EXISTS proposals (id TEXT PRIMARY KEY, proposal TEXT);')
                    with memory:
                        memory.execute('INSERT OR IGNORE INTO runs VALUES (?,?,?,?)',(run_id,days[-1],artifact.name,sha(artifact)))
                        for proposal in learning['proposals']:
                            memory.execute('INSERT OR IGNORE INTO proposals VALUES (?,?)',(proposal['id'],encoded(proposal)))
                finally: memory.close()
        except (DataGap,FileNotFoundError,KeyError,ValueError,TypeError) as exc:
            result={**base,'status':'BLOCKED_DATA_OR_INTEGRITY','error_type':type(exc).__name__,
                    'reason':str(exc)[:200],'learning':'no_scored_outcome_from_missing_or_untrusted_data'}
        atomic(output/'latest.json',result)
        print(encoded({k:v for k,v in result.items() if k not in ('results','learning')}),flush=True)
        return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--archive',type=Path,default=Path('/var/lib/trading-collector'))
    p.add_argument('--output',type=Path,default=Path('/var/lib/trading-research'))
    args=p.parse_args()
    execute(args.root,args.archive,args.output)
