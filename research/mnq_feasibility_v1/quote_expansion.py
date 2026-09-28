"""Free metadata-only quotes for two fixed, unseen history extensions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

from quote_databento import metadata, load_key, ROOT


def main():
    output=ROOT/'research/mnq_feasibility_v1/runs/expansion-quote-20260909.json'
    if output.exists():raise ValueError('Existing estimate preserved')
    days=[];day=date(2026,8,3)
    while day<=date(2026,8,28):
        if day.weekday()<5:days.append(day.isoformat())
        day+=timedelta(days=1)
    requests=[dict(dataset='GLBX.MDP3',symbols='MNQU6',stype_in='raw_symbol',schema='mbp-1',start=d+'T13:30:00Z',end=d+'T20:00:00Z') for d in days]
    requests += [dict(dataset='GLBX.MDP3',symbols='MNQU6',stype_in='raw_symbol',schema='definition',start='2026-08-03T00:00:00Z',end='2026-08-29T00:00:00Z')]
    key=load_key()
    with ThreadPoolExecutor(max_workers=4) as pool:
        costs=list(pool.map(lambda r:metadata('metadata.get_cost',r,key),requests))
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not Decimal(str(x)).is_finite() or x<0 for x in costs):raise ValueError('Invalid cost')
    rows=[dict(request=r,estimated_usd=str(c)) for r,c in zip(requests,costs)]
    result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),status='QUOTE_ONLY_NO_PURCHASE',
        rationale='No setups in first four evaluated days; extension dates chosen before opening their outcomes, same dated contract.',
        requests=rows,estimated_total_usd=str(sum(Decimal(str(x)) for x in costs)),
        lower_cost_subset=dict(dates='2026-08-24 through 2026-08-28',
            mbp1_estimated_usd=str(sum(Decimal(row['estimated_usd']) for row in rows if row['request']['schema']=='mbp-1' and row['request']['start'][:10]>='2026-08-24'))),
        quote_includes_definitions_for_entire_extension=True,billable_data_requested=False,
        notes=['Prior purchase approval covered only the initial pilot.','Current credit balance and monthly limit not verified.','First newly added session is warmup; do not treat inspected pilot dates as untouched validation.'])
    with output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print('20-session extension estimate USD:',result['estimated_total_usd'])
    print('Five-session MBP-1 subset estimate USD:',result['lower_cost_subset']['mbp1_estimated_usd'])
    print('No new data purchased. Saved:',output)


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Quote stopped:',type(error).__name__,'(details suppressed to protect credentials)');raise SystemExit(1)
