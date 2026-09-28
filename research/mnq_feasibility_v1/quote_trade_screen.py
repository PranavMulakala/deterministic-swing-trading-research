"""Free cost comparison for a staged fixed-rule study. No data purchase."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import json
from quote_databento import ROOT, load_key, metadata


def main():
    output=ROOT/'research/mnq_feasibility_v1/runs/trade-screen-quote-20260909.json'
    if output.exists():raise ValueError('Existing quote preserved')
    prior=json.loads((ROOT/'research/mnq_feasibility_v1/runs/expansion-quote-20260909.json').read_text())
    requests=[dict(q['request'],schema='trades') for q in prior['requests'] if q['request']['schema']=='mbp-1']
    key=load_key()
    with ThreadPoolExecutor(max_workers=4) as pool:
        costs=list(pool.map(lambda p:metadata('metadata.get_cost',p,key),requests))
    if any(isinstance(c,bool) or not isinstance(c,(int,float)) or not Decimal(str(c)).is_finite() or c<0 for c in costs):raise ValueError('Invalid estimate')
    definition_cost=sum(Decimal(q['estimated_usd']) for q in prior['requests'] if q['request']['schema']=='definition')
    result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),status='QUOTE_ONLY_NO_PURCHASE',
        requests=[dict(request=p,estimated_usd=str(c)) for p,c in zip(requests,costs)],
        trade_only_estimated_usd=str(sum(Decimal(str(c)) for c in costs)),
        estimated_with_previously_quoted_definitions_usd=str(sum(Decimal(str(c)) for c in costs)+definition_cost),
        all_mbp1_prior_estimated_usd=prior['estimated_total_usd'],
        limitations=['Trade-only data can find fixed-rule patterns but cannot verify executable quotes or costs.',
            'Buy quotes for every day with qualifying signals, not selected winners; the second-stage cost is not yet known.',
            'Buying trades and then MBP-1 duplicates the trade component; staged total can exceed MBP-1 alone if many days contain signals.',
            'No new data purchased or downloaded by this script.'])
    with output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print('20 sessions, trades-only estimate USD:',result['trade_only_estimated_usd'])
    print('Including prior definition estimate USD:',result['estimated_with_previously_quoted_definitions_usd'])
    print('Saved:',output)


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Quote stopped:',type(error).__name__,'(details suppressed)');raise SystemExit(1)
