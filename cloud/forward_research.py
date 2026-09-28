"""Prospective capital comparison and news annotations; no execution capability."""
from dataclasses import replace

from cloud.research_archive import DataGap, nanos
from research.lite_reversal_v1 import experiment as lite_engine


def capital_replay(parent, included, excluded, completed_days, policy):
    expected = {
        'id':'lite-capital-feasibility-v2','evaluation_start':'2026-09-09',
        'parent_rules':'research/lite_reversal_v1/config.json',
        'capital_arms':[5000,10000],'variants':['dip','vwap_retest'],
        'cost_bps':[10,25],'mode':'whole',
        'rule_changes':'capital_only_no_entry_exit_sizing_formula_or_risk_percentage_change',
        'broker_ready':False,'promotion':'disabled',
    }
    if policy != expected or parent.initial_cash != 500:
        raise DataGap('invalid_lite_forward_policy')
    days=[d for d in completed_days if d>=policy['evaluation_start']]
    missing={d:excluded.get(d,'missing_session') for d in days if d not in included or d in excluded}
    result={'id':policy['id'],'evaluation_start':policy['evaluation_start'],
            'mode':'whole','capital_arms':policy['capital_arms'],'broker_ready':False,
            'days':days,'excluded':missing,'results':{},
            'status':'WAITING_FOR_FIRST_FORWARD_SESSION'}
    if not days:
        return result
    if missing:
        result['status']='BLOCKED_INCOMPLETE_FORWARD_DATA'
        return result
    selected={d:included[d] for d in days}
    for capital in policy['capital_arms']:
        config=replace(parent,initial_cash=capital)
        for variant in policy['variants']:
            for cost in policy['cost_bps']:
                result['results'][f'{capital}_{variant}_{cost}bps']=lite_engine.run_variant(
                    selected,config,variant,cost,'whole')
    result['status']='REPLAY_COMPLETE_RESEARCH_ONLY'
    return result


def context_news(archive, context_config, sessions, days):
    first=context_config['collection_start']
    if (first!='2026-09-09T00:00:00Z' or context_config['selection_or_execution_use'] is not False
            or set(context_config['applies_to'])!={'LITE','COHR','CIEN','FN','AAOI'}):
        raise DataGap('invalid_news_context_config')
    for symbols in context_config['applies_to'].values():
        if not set(symbols)<=set(context_config['symbols']):
            raise DataGap('invalid_news_context_mapping')
    evidence={}; statuses={}
    for day in days:
        if day<first[:10]:
            continue
        # UTC midnight includes the full premarket session; article receipt is
        # still required before a signal can count the article as available.
        start=max(nanos(first),nanos(day+'T00:00:00Z'))
        end=nanos(sessions[day][1].isoformat())
        try:
            evidence[day]=archive.news(start,end,'sector_news')
            statuses[day]='metadata_only_not_used_for_selection'
        except DataGap:
            evidence[day]=[]
            statuses[day]='unknown_incomplete_collection_not_neutral'
    return evidence,statuses


def available_context(evidence,statuses,feature,context_config):
    day=feature['day']; status=statuses.get(day,'not_started_prospective')
    count=None
    if status=='metadata_only_not_used_for_selection':
        mapped=set(context_config['applies_to'][feature['symbol']])
        cutoff=nanos(feature['pattern']['time'])
        count=len({(n['article_id'],n['updated_at']) for n in evidence[day]
                   if mapped.intersection(n['symbols']) and nanos(n['first_received_at'])<=cutoff
                   and nanos(n['updated_at'] or n['created_at'])<=cutoff})
    return {'context_items_observed_before_signal':count,'context_status':status,
            'context_source_stream':'sector_news'}
